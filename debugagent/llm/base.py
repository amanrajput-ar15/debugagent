from __future__ import annotations

from abc import ABC, abstractmethod


class LLMBackend(ABC):
    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> tuple[str, int]:
        raise NotImplementedError
