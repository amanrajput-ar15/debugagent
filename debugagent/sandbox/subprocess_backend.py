from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from debugagent.sandbox.base import SandboxBackend
from debugagent.schemas.models import SandboxResult


class SubprocessSandbox(SandboxBackend):
    def _build_env(self, workdir: Path) -> dict[str, str]:
        safe_env: dict[str, str] = {}
        blocked_fragments = ("KEY", "TOKEN", "SECRET", "PASSWORD")

        for key, value in os.environ.items():
            if any(fragment in key.upper() for fragment in blocked_fragments):
                continue
            safe_env[key] = value

        safe_env["PYTHONPATH"] = str(workdir)
        safe_env["HOME"] = str(workdir)
        safe_env["USERPROFILE"] = str(workdir)
        safe_env["TMP"] = str(workdir)
        safe_env["TEMP"] = str(workdir)
        return safe_env

    def run(self, repaired_code: str, test_suite: str, timeout_s: int = 30) -> SandboxResult:
        workdir = Path(tempfile.mkdtemp(prefix="debugagent_"))
        start = time.monotonic()

        try:
            (workdir / "solution.py").write_text(repaired_code, encoding="utf-8")
            (workdir / "test_solution.py").write_text(test_suite, encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "test_solution.py",
                    "--tb=short",
                    "--no-header",
                    "-q",
                    "--timeout=10",
                    "--json-report",
                    "--json-report-file=report.json",
                ],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=self._build_env(workdir),
            )

            return SandboxResult(
                exit_code=result.returncode,
                stdout=result.stdout[:8000],
                stderr=result.stderr[:4000],
                timed_out=False,
                execution_time_ms=(time.monotonic() - start) * 1000,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {timeout_s}s",
                timed_out=True,
                execution_time_ms=timeout_s * 1000,
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
