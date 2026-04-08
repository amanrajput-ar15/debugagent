from __future__ import annotations

import time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ErrorClass(str, Enum):
    SYNTAX_ERROR = "SYNTAX_ERROR"
    TYPE_ERROR = "TYPE_ERROR"
    VALUE_ERROR = "VALUE_ERROR"
    INDEX_ERROR = "INDEX_ERROR"
    KEY_ERROR = "KEY_ERROR"
    ASSERTION_ERROR = "ASSERTION_ERROR"
    IMPORT_ERROR = "IMPORT_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"


class AgentStatus(str, Enum):
    PLANNING = "PLANNING"
    REPAIRING = "REPAIRING"
    EXECUTING = "EXECUTING"
    EVALUATING = "EVALUATING"
    REFLECTING = "REFLECTING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CIRCUIT_BROKEN = "CIRCUIT_BROKEN"


class BugTask(BaseModel):
    task_id: str
    buggy_code: str
    test_suite: str
    description: str = ""
    constraints: list[str] = Field(default_factory=list)
    max_retries: int = 5
    created_at: float = Field(default_factory=time.time)

    @field_validator("max_retries")
    @classmethod
    def validate_max_retries(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("max_retries must be > 0")
        return value


class SandboxResult(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    execution_time_ms: float


class EvalResult(BaseModel):
    score: float
    passed_tests: int
    failed_tests: int
    total_tests: int
    error_class: ErrorClass
    error_message: str
    error_line: Optional[int] = None
    raw_output: str

    @field_validator("score")
    @classmethod
    def validate_score(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0")
        return value


class PromptPatch(BaseModel):
    root_cause: str
    fix_strategy: str
    specific_hint: str
    error_class: ErrorClass
    temperature_escalate: bool = False
    confidence: float = 0.8

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value


class Attempt(BaseModel):
    attempt_id: str
    task_id: str
    iteration: int
    repaired_code: str
    eval_result: EvalResult
    prompt_patch: Optional[PromptPatch]
    tokens_used: int
    latency_ms: float
    code_hash: str
    timestamp: float = Field(default_factory=time.time)


class SessionResult(BaseModel):
    task_id: str
    status: AgentStatus
    total_attempts: int
    total_tokens: int
    final_score: float
    accepted_fix: Optional[str]
    improvement_from_memory: bool
    session_duration_s: float
    final_error_class: ErrorClass = ErrorClass.UNKNOWN
