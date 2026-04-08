from __future__ import annotations

from pathlib import Path

from debugagent.agent.planner import ContextBundle
from debugagent.llm.base import LLMBackend
from debugagent.schemas.models import PromptPatch
from debugagent.utils.code_utils import strip_fences


class RepairGenerator:
    def __init__(self, llm: LLMBackend, prompts_dir: str = "./prompts"):
        self.llm = llm
        self.prompts_dir = Path(prompts_dir)
        self.system_prompt = (self.prompts_dir / "repair_system.txt").read_text(encoding="utf-8")
        self.user_template = (self.prompts_dir / "repair_user.txt").read_text(encoding="utf-8")

    def generate(self, context: ContextBundle, prompt_patch: PromptPatch | None) -> tuple[str, int]:
        temperature = 0.7 if (prompt_patch and prompt_patch.temperature_escalate) else 0.2
        user_prompt = self.user_template.format(
            buggy_code=context.buggy_code,
            test_suite=context.test_suite,
            error_class=context.error_class,
            error_message=context.error_message,
            attempt_history=context.attempt_history,
            memory_context=context.memory_context,
            prompt_patch=context.prompt_patch,
            constraints=context.constraints,
        )
        raw_output, tokens = self.llm.complete(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=4096,
        )
        return strip_fences(raw_output), tokens
