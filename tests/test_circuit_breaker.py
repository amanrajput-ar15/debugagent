from debugagent.agent.circuit_breaker import CircuitBreaker
from debugagent.schemas.models import Attempt, ErrorClass, EvalResult


def _attempt(iteration: int, code: str, err: str) -> Attempt:
    return Attempt(
        attempt_id=f"a{iteration}",
        task_id="t1",
        iteration=iteration,
        repaired_code=code,
        eval_result=EvalResult(
            score=0.0,
            passed_tests=0,
            failed_tests=1,
            total_tests=1,
            error_class=ErrorClass.RUNTIME_ERROR,
            error_message=err,
            raw_output="",
        ),
        prompt_patch=None,
        tokens_used=10,
        latency_ms=5,
        code_hash="h",
    )


def test_trip_on_identical_code():
    cb = CircuitBreaker(window=3)
    cb.check(_attempt(0, "x=1", "e1"))
    cb.check(_attempt(1, "x=1", "e2"))
    status = cb.check(_attempt(2, "x=1", "e3"))
    assert status.tripped
    assert status.can_escalate


def test_trip_on_identical_error():
    cb = CircuitBreaker(window=3)
    cb.check(_attempt(0, "x=1", "same"))
    cb.check(_attempt(1, "x=2", "same"))
    status = cb.check(_attempt(2, "x=3", "same"))
    assert status.tripped
