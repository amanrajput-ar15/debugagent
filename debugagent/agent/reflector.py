from __future__ import annotations

import json
from pathlib import Path

from debugagent.llm.base import LLMBackend
from debugagent.schemas.models import Attempt, BugTask, ErrorClass, PromptPatch


class ReflectionEngine:
    def __init__(self, llm: LLMBackend, prompts_dir: str = "./prompts"):
        self.llm = llm
        self.prompts_dir = Path(prompts_dir)
        self.system_prompt = (self.prompts_dir / "reflect_system.txt").read_text(encoding="utf-8")
        self.user_template = (self.prompts_dir / "reflect_user.txt").read_text(encoding="utf-8")

    def diagnose(
        self,
        task: BugTask,
        attempt: Attempt,
        attempt_history: list[Attempt],
        similar_failures: list[dict],
    ) -> tuple[PromptPatch, int]:
        history = "\n".join(
            f"iter={a.iteration} class={a.eval_result.error_class.value} msg={a.eval_result.error_message}"
            for a in attempt_history[-5:]
        ) or "None"

        memory = "\n".join(
            f"class={m.get('metadata', {}).get('error_class', 'UNKNOWN')} sim={m.get('similarity', 0):.3f}"
            for m in similar_failures[:3]
        ) or "None"

        user_prompt = self.user_template.format(
            buggy_code=task.buggy_code,
            test_suite=task.test_suite,
            repaired_code=attempt.repaired_code,
            error_class=attempt.eval_result.error_class.value,
            error_message=attempt.eval_result.error_message,
            score=attempt.eval_result.score,
            attempt_history=history,
            memory_context=memory,
        )

        raw, tokens = self.llm.complete(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=512,
        )

        try:
            data = json.loads(raw)
            patch = PromptPatch(
                root_cause=data.get("root_cause", "Unknown root cause"),
                fix_strategy=data.get("fix_strategy", "Try a different localized fix"),
                specific_hint=data.get("specific_hint", "Inspect failing assertion and boundary conditions"),
                error_class=ErrorClass(data.get("error_class", attempt.eval_result.error_class.value)),
                temperature_escalate=bool(data.get("temperature_escalate", False)),
                confidence=float(data.get("confidence", 0.6)),
            )
            return patch, tokens
        except Exception:
            patch, fallback_tokens = self._fallback_patch(attempt.eval_result.error_class)
            return patch, tokens + fallback_tokens

    def _fallback_patch(self, error_class: ErrorClass) -> tuple[PromptPatch, int]:
        if error_class == ErrorClass.INDEX_ERROR:
            hint = "Check list/string bounds and empty-input guards."
        elif error_class == ErrorClass.KEY_ERROR:
            hint = "Use dict.get or guard for missing keys before access."
        elif error_class == ErrorClass.TYPE_ERROR:
            hint = "Validate argument types and conversions before operations."
        elif error_class == ErrorClass.ASSERTION_ERROR:
            hint = "Align return value with expected assertions and edge cases."
        elif error_class == ErrorClass.IMPORT_ERROR:
            hint = "Fix module import path or missing dependency usage."
        else:
            hint = "Focus on minimal local fix around failing code path."

        patch = PromptPatch(
            root_cause="Reflection JSON parse failed; using rule-based fallback.",
            fix_strategy="Apply targeted fix for current error class.",
            specific_hint=hint,
            error_class=error_class,
            temperature_escalate=False,
            confidence=0.4,
        )
        return patch, 0
