from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ContextBudget:
    max_tokens: int = 900_000

    @staticmethod
    def estimate_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    def _trim_attempts(self, attempt_history: str, keep: int = 2) -> str:
        chunks = [c for c in attempt_history.split("\n---\n") if c.strip()]
        if len(chunks) <= keep:
            return attempt_history
        return "\n---\n".join(chunks[-keep:])

    def _trim_memories(self, memory_context: str, keep: int = 2) -> str:
        chunks = [c for c in memory_context.split("\n\n") if c.strip()]
        if len(chunks) <= keep:
            return memory_context
        return "\n\n".join(chunks[:keep])

    def build_repair_context(self, *, base_context: dict[str, str]) -> dict[str, str]:
        context = dict(base_context)

        while self.estimate_tokens("\n".join(context.values())) > self.max_tokens:
            before = "\n".join(context.values())
            context["attempt_history"] = self._trim_attempts(context.get("attempt_history", ""), keep=2)
            context["memory_context"] = self._trim_memories(context.get("memory_context", ""), keep=2)
            context["buggy_code"] = context.get("buggy_code", "")[:200_000]
            context["test_suite"] = context.get("test_suite", "")[:200_000]
            after = "\n".join(context.values())
            if after == before:
                break

        return context
