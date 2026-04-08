from __future__ import annotations

import ast
import difflib
import re
from typing import Optional


def strip_fences(raw_output: str) -> str:
    return re.sub(r"```python\n?|```", "", raw_output).strip()


def ast_validate(code: str) -> Optional[str]:
    try:
        ast.parse(code)
        return None
    except SyntaxError as exc:
        return f"SyntaxError: {exc.msg}"


def diff_code(original: str, updated: str | None) -> str:
    if not updated:
        return ""
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile="original.py",
        tofile="fixed.py",
    )
    return "".join(diff)
