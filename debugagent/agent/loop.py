from __future__ import annotations

import json
import time
from pathlib import Path
from uuid import uuid4

from debugagent.agent.circuit_breaker import CircuitBreaker
from debugagent.agent.evaluator import Evaluator
from debugagent.agent.planner import Planner
from debugagent.agent.reflector import ReflectionEngine
from debugagent.agent.repair import RepairGenerator
from debugagent.config import AgentConfig
from debugagent.llm.gemini_client import GeminiClient
from debugagent.memory.episodic import EpisodicMemory
from debugagent.memory.improvement_log import ImprovementLog
from debugagent.memory.solution_store import SolutionStore
from debugagent.observability.tracer import AgentTracer
from debugagent.sandbox.runner import SandboxRunner
from debugagent.schemas.models import AgentStatus, Attempt, BugTask, ErrorClass, EvalResult, PromptPatch, SessionResult
from debugagent.utils.code_utils import ast_validate
from debugagent.utils.context_budget import ContextBudget
from debugagent.utils.hash_utils import code_hash


class AgentLoop:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm = GeminiClient(config.gemini_api_key, verbose=config.verbose)
        self.sandbox = SandboxRunner(backend="subprocess")
        self.evaluator = Evaluator()
        self.repair = RepairGenerator(self.llm)
        self.reflector = ReflectionEngine(self.llm)
        self.memory = EpisodicMemory(persist_dir=config.chroma_dir)
        self.solutions = SolutionStore(sqlite_path=config.sqlite_path)
        self.improvement_log = ImprovementLog(sqlite_path=config.sqlite_path)
        self.cb = CircuitBreaker(window=3)
        self.tracer = AgentTracer(
            host=config.langfuse.host,
            public_key=config.langfuse.public_key,
            secret_key=config.langfuse.secret_key,
            enabled=config.langfuse.enabled,
        )
        self.budget = ContextBudget(max_tokens=900_000)
        self.planner = Planner(budget=self.budget)

    def run(self, task: BugTask) -> SessionResult:
        started = time.monotonic()
        session_trace = self.tracer.start_session(task)

        cached = self.solutions.lookup(task.task_id)
        if cached:
            result = SessionResult(
                task_id=task.task_id,
                status=AgentStatus.SUCCESS,
                total_attempts=0,
                total_tokens=0,
                final_score=1.0,
                accepted_fix=cached,
                improvement_from_memory=False,
                session_duration_s=time.monotonic() - started,
                final_error_class=ErrorClass.UNKNOWN,
            )
            self.tracer.end_session(session_trace, result)
            self._persist_session(task, [], result)
            return result

        similar_failures = self.memory.retrieve(query=task.buggy_code + "\n" + task.description, k=3)
        improvement_from_memory = len(similar_failures) > 0

        attempts: list[Attempt] = []
        prompt_patch: PromptPatch | None = None
        total_tokens = 0

        for i in range(task.max_retries):
            context = self.planner.build_context(task, attempts, similar_failures, prompt_patch)
            repaired_code, tokens_repair = self.repair.generate(context, prompt_patch=prompt_patch)
            total_tokens += tokens_repair

            syntax_error = ast_validate(repaired_code)
            if syntax_error:
                eval_result = self._syntax_eval_result(syntax_error)
            else:
                sandbox_result = self.sandbox.run(
                    repaired_code=repaired_code,
                    test_suite=task.test_suite,
                    timeout_s=self.config.sandbox_timeout_s,
                )
                eval_result = self.evaluator.score(sandbox_result)

            attempt = Attempt(
                attempt_id=str(uuid4()),
                task_id=task.task_id,
                iteration=i,
                repaired_code=repaired_code,
                eval_result=eval_result,
                prompt_patch=prompt_patch,
                tokens_used=tokens_repair,
                latency_ms=0.0,
                code_hash=code_hash(repaired_code),
            )
            attempts.append(attempt)
            self.tracer.log_iteration(session_trace, attempt)

            if eval_result.score == 1.0:
                self.solutions.save(
                    task_id=task.task_id,
                    accepted_code=repaired_code,
                    iterations_needed=i + 1,
                    error_class=eval_result.error_class.value,
                )
                self.memory.store_success(attempt)
                result = SessionResult(
                    task_id=task.task_id,
                    status=AgentStatus.SUCCESS,
                    total_attempts=i + 1,
                    total_tokens=total_tokens,
                    final_score=1.0,
                    accepted_fix=repaired_code,
                    improvement_from_memory=improvement_from_memory,
                    session_duration_s=time.monotonic() - started,
                    final_error_class=eval_result.error_class,
                )
                self.improvement_log.log_session(result)
                self.tracer.end_session(session_trace, result)
                self._persist_session(task, attempts, result)
                return result

            cb_status = self.cb.check(attempt)
            if cb_status.tripped:
                if cb_status.can_escalate:
                    prompt_patch = PromptPatch(
                        root_cause="Circuit breaker detected repetition",
                        fix_strategy="Try a meaningfully different strategy",
                        specific_hint="Change approach; avoid repeating same patch.",
                        error_class=attempt.eval_result.error_class,
                        temperature_escalate=True,
                        confidence=0.7,
                    )
                    self.cb.reset()
                else:
                    self.memory.store_failure(attempt)
                    result = SessionResult(
                        task_id=task.task_id,
                        status=AgentStatus.CIRCUIT_BROKEN,
                        total_attempts=i + 1,
                        total_tokens=total_tokens,
                        final_score=attempt.eval_result.score,
                        accepted_fix=None,
                        improvement_from_memory=improvement_from_memory,
                        session_duration_s=time.monotonic() - started,
                        final_error_class=attempt.eval_result.error_class,
                    )
                    self.improvement_log.log_session(result)
                    self.tracer.end_session(session_trace, result)
                    self._persist_session(task, attempts, result)
                    return result

            prompt_patch, tokens_reflect = self.reflector.diagnose(
                task=task,
                attempt=attempt,
                attempt_history=attempts,
                similar_failures=similar_failures,
            )
            total_tokens += tokens_reflect
            self.memory.store_failure(attempt)

        final_error = attempts[-1].eval_result.error_class if attempts else ErrorClass.UNKNOWN
        final_score = attempts[-1].eval_result.score if attempts else 0.0
        result = SessionResult(
            task_id=task.task_id,
            status=AgentStatus.FAILED,
            total_attempts=len(attempts),
            total_tokens=total_tokens,
            final_score=final_score,
            accepted_fix=None,
            improvement_from_memory=improvement_from_memory,
            session_duration_s=time.monotonic() - started,
            final_error_class=final_error,
        )
        self.improvement_log.log_session(result)
        self.tracer.end_session(session_trace, result)
        self._persist_session(task, attempts, result)
        return result

    def _syntax_eval_result(self, syntax_error: str) -> EvalResult:
        return EvalResult(
            score=0.0,
            passed_tests=0,
            failed_tests=0,
            total_tests=0,
            error_class=ErrorClass.SYNTAX_ERROR,
            error_message=syntax_error,
            raw_output=syntax_error,
        )

    def _persist_session(self, task: BugTask, attempts: list[Attempt], result: SessionResult) -> None:
        payload = {
            "task": task.model_dump(),
            "attempts": [a.model_dump() for a in attempts],
            "result": result.model_dump(),
        }
        timestamp = int(time.time())
        session_file = Path(self.config.session_dir) / f"{task.task_id}_{timestamp}.json"
        session_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
