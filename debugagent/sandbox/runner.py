from __future__ import annotations

from debugagent.sandbox.base import SandboxBackend
from debugagent.sandbox.subprocess_backend import SubprocessSandbox
from debugagent.schemas.models import SandboxResult


class SandboxRunner:
    def __init__(self, backend: str = "subprocess"):
        if backend != "subprocess":
            raise ValueError(f"Unsupported sandbox backend: {backend}")
        self.backend: SandboxBackend = SubprocessSandbox()

    def run(self, repaired_code: str, test_suite: str, timeout_s: int = 30) -> SandboxResult:
        return self.backend.run(repaired_code=repaired_code, test_suite=test_suite, timeout_s=timeout_s)
