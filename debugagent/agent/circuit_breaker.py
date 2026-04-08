from __future__ import annotations

import hashlib
from collections import deque
from dataclasses import dataclass

from debugagent.schemas.models import Attempt


@dataclass(slots=True)
class CBStatus:
    tripped: bool
    reason: str
    can_escalate: bool


class CircuitBreaker:
    def __init__(self, window: int = 3):
        self.window = window
        self._recent_hashes: deque[str] = deque(maxlen=window)
        self._recent_errors: deque[str] = deque(maxlen=window)
        self._escalated = False

    def check(self, attempt: Attempt) -> CBStatus:
        code_hash = hashlib.sha256(attempt.repaired_code.encode("utf-8")).hexdigest()
        error_sig = f"{attempt.eval_result.error_class.value}::{attempt.eval_result.error_message}"
        self._recent_hashes.append(code_hash)
        self._recent_errors.append(error_sig)

        identical_code = len(self._recent_hashes) == self.window and len(set(self._recent_hashes)) == 1
        identical_error = len(self._recent_errors) == self.window and len(set(self._recent_errors)) == 1

        if identical_code:
            return CBStatus(True, f"Identical code generated {self.window} times", not self._escalated)
        if identical_error:
            return CBStatus(True, f"Same error repeated {self.window} times", not self._escalated)
        return CBStatus(False, "", True)

    def reset(self) -> None:
        self._recent_hashes.clear()
        self._recent_errors.clear()
        self._escalated = True
