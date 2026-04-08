from __future__ import annotations

from abc import ABC, abstractmethod

from debugagent.schemas.models import SandboxResult


class SandboxBackend(ABC):
    @abstractmethod
    def run(self, repaired_code: str, test_suite: str, timeout_s: int = 30) -> SandboxResult:
        raise NotImplementedError
