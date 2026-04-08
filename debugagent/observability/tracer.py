from __future__ import annotations

from dataclasses import dataclass

from debugagent.schemas.models import Attempt, BugTask, SessionResult


@dataclass(slots=True)
class _NoopTrace:
    trace_id: str = "noop"

    def span(self, **_: object) -> None:
        return None

    def update(self, **_: object) -> None:
        return None


class AgentTracer:
    def __init__(self, host: str, public_key: str, secret_key: str, enabled: bool = True):
        self.enabled = enabled
        self.client = None
        if enabled:
            try:
                from langfuse import Langfuse

                self.client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
            except Exception:
                self.enabled = False
                self.client = None

    def start_session(self, task: BugTask):
        if not self.enabled or self.client is None:
            return _NoopTrace()
        return self.client.trace(
            name="debug_session",
            metadata={
                "task_id": task.task_id,
                "max_retries": task.max_retries,
                "constraints": task.constraints,
            },
        )

    def log_iteration(self, trace, attempt: Attempt) -> None:
        if not self.enabled:
            return
        trace.span(
            name=f"iteration_{attempt.iteration}",
            metadata={
                "iteration": attempt.iteration,
                "score": attempt.eval_result.score,
                "error_class": attempt.eval_result.error_class.value,
                "error_message": attempt.eval_result.error_message,
                "tokens_used": attempt.tokens_used,
                "latency_ms": attempt.latency_ms,
                "code_hash": attempt.code_hash,
                "prompt_patch": attempt.prompt_patch.model_dump() if attempt.prompt_patch else None,
            },
        )

    def end_session(self, trace, result: SessionResult) -> None:
        if not self.enabled or self.client is None:
            return
        trace.update(
            output={
                "status": result.status.value,
                "total_attempts": result.total_attempts,
                "total_tokens": result.total_tokens,
                "final_score": result.final_score,
                "improvement_from_memory": result.improvement_from_memory,
                "final_error_class": result.final_error_class.value,
            }
        )
        self.client.flush()
