from __future__ import annotations

import re

from debugagent.schemas.models import ErrorClass, EvalResult, SandboxResult


class Evaluator:
    EXIT_ALL_PASS = 0
    EXIT_SOME_FAIL = 1
    EXIT_INTERRUPT = 2
    EXIT_NO_TESTS = 5

    def score(self, sandbox: SandboxResult) -> EvalResult:
        output = (sandbox.stdout or "") + "\n" + (sandbox.stderr or "")

        if sandbox.timed_out:
            return EvalResult(
                score=0.0,
                passed_tests=0,
                failed_tests=0,
                total_tests=0,
                error_class=ErrorClass.TIMEOUT,
                error_message="Execution timed out",
                raw_output=output[:4000],
            )

        if sandbox.exit_code == self.EXIT_ALL_PASS:
            passed = self._parse_passed_count(output)
            return EvalResult(
                score=1.0,
                passed_tests=passed,
                failed_tests=0,
                total_tests=passed,
                error_class=ErrorClass.UNKNOWN,
                error_message="",
                raw_output=output[:4000],
            )

        if sandbox.exit_code == self.EXIT_NO_TESTS:
            return EvalResult(
                score=0.0,
                passed_tests=0,
                failed_tests=0,
                total_tests=0,
                error_class=ErrorClass.SYNTAX_ERROR,
                error_message="No tests collected - test file has syntax/import issues",
                raw_output=output[:4000],
            )

        passed, failed, total = self._parse_test_counts(output)
        score = passed / total if total else 0.0
        error_class, error_message = self._classify_error(output)

        return EvalResult(
            score=score,
            passed_tests=passed,
            failed_tests=failed,
            total_tests=total,
            error_class=error_class,
            error_message=error_message,
            raw_output=output[:4000],
        )

    def _parse_passed_count(self, output: str) -> int:
        match = re.search(r"(\d+)\s+passed", output)
        return int(match.group(1)) if match else 0

    def _parse_test_counts(self, output: str) -> tuple[int, int, int]:
        passed_match = re.search(r"(\d+)\s+passed", output)
        failed_match = re.search(r"(\d+)\s+failed", output)
        error_match = re.search(r"(\d+)\s+error", output)

        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        errors = int(error_match.group(1)) if error_match else 0
        total = passed + failed + errors

        if total == 0 and ("failed" in output.lower() or "error" in output.lower()):
            total = 1
            failed = 1

        return passed, failed + errors, total

    def _classify_error(self, output: str) -> tuple[ErrorClass, str]:
        checks = [
            (r"SyntaxError", ErrorClass.SYNTAX_ERROR),
            (r"TypeError", ErrorClass.TYPE_ERROR),
            (r"ValueError", ErrorClass.VALUE_ERROR),
            (r"IndexError", ErrorClass.INDEX_ERROR),
            (r"KeyError", ErrorClass.KEY_ERROR),
            (r"AssertionError", ErrorClass.ASSERTION_ERROR),
            (r"ModuleNotFoundError|ImportError", ErrorClass.IMPORT_ERROR),
            (r"RuntimeError|ZeroDivisionError|AttributeError|NameError", ErrorClass.RUNTIME_ERROR),
        ]

        for pattern, cls in checks:
            match = re.search(rf"({pattern}[^\n]*)", output)
            if match:
                return cls, self._normalize_error(match.group(1))

        if "timed out" in output.lower():
            return ErrorClass.TIMEOUT, "Execution timed out"

        return ErrorClass.UNKNOWN, "Unknown failure"

    def _normalize_error(self, error: str) -> str:
        error = re.sub(r'File "[^"]*"', 'File "<file>"', error)
        error = re.sub(r", line \d+", "", error)
        error = re.sub(r"0x[0-9a-fA-F]+", "0x...", error)
        return error.strip()[:200]
