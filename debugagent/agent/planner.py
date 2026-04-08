from __future__ import annotations

from dataclasses import dataclass

from debugagent.schemas.models import Attempt, BugTask, PromptPatch
from debugagent.utils.context_budget import ContextBudget


@dataclass(slots=True)
class ContextBundle:
    buggy_code: str
    test_suite: str
    error_class: str
    error_message: str
    attempt_history: str
    memory_context: str
    prompt_patch: str
    constraints: str


class Planner:
    def __init__(self, budget: ContextBudget):
        self.budget = budget

    def build_context(
        self,
        task: BugTask,
        attempts: list[Attempt],
        similar_failures: list[dict],
        prompt_patch: PromptPatch | None,
    ) -> ContextBundle:
        attempt_lines: list[str] = []
        for attempt in attempts[-5:]:
            attempt_lines.append(
                (
                    f"Iteration {attempt.iteration}: "
                    f"{attempt.eval_result.error_class.value} | "
                    f"{attempt.eval_result.error_message}"
                )
            )
        attempt_history = "\n---\n".join(attempt_lines) if attempt_lines else "None"

        memory_lines: list[str] = []
        for memory in similar_failures[:3]:
            metadata = memory.get("metadata", {})
            memory_lines.append(
                (
                    f"similarity={memory.get('similarity', 0):.3f} | "
                    f"error_class={metadata.get('error_class', 'UNKNOWN')} | "
                    f"message={metadata.get('error_message', '')}"
                )
            )
        memory_context = "\n\n".join(memory_lines) if memory_lines else "None"

        patch_text = (
            f"Root cause: {prompt_patch.root_cause}\n"
            f"Fix strategy: {prompt_patch.fix_strategy}\n"
            f"Specific hint: {prompt_patch.specific_hint}"
            if prompt_patch
            else "None"
        )

        current_error_class = attempts[-1].eval_result.error_class.value if attempts else "UNKNOWN"
        current_error_message = attempts[-1].eval_result.error_message if attempts else "Initial attempt"

        base_context = {
            "buggy_code": task.buggy_code,
            "test_suite": task.test_suite,
            "error_class": current_error_class,
            "error_message": current_error_message,
            "attempt_history": attempt_history,
            "memory_context": memory_context,
            "prompt_patch": patch_text,
            "constraints": ", ".join(task.constraints) if task.constraints else "None",
        }
        trimmed = self.budget.build_repair_context(base_context=base_context)

        return ContextBundle(
            buggy_code=trimmed["buggy_code"],
            test_suite=trimmed["test_suite"],
            error_class=trimmed["error_class"],
            error_message=trimmed["error_message"],
            attempt_history=trimmed["attempt_history"],
            memory_context=trimmed["memory_context"],
            prompt_patch=trimmed["prompt_patch"],
            constraints=trimmed["constraints"],
        )
