from __future__ import annotations

import hashlib


def bug_signature(buggy_code: str) -> str:
    return hashlib.sha256(buggy_code.encode("utf-8")).hexdigest()[:12]


def code_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()
