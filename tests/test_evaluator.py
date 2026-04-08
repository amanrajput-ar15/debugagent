from debugagent.agent.evaluator import Evaluator
from debugagent.schemas.models import ErrorClass, SandboxResult


def test_timeout_classification():
    evaluator = Evaluator()
    result = evaluator.score(
        SandboxResult(exit_code=-1, stdout="", stderr="timeout", timed_out=True, execution_time_ms=1000)
    )
    assert result.error_class == ErrorClass.TIMEOUT


def test_all_pass_score():
    evaluator = Evaluator()
    result = evaluator.score(
        SandboxResult(
            exit_code=0,
            stdout="2 passed in 0.01s",
            stderr="",
            timed_out=False,
            execution_time_ms=1,
        )
    )
    assert result.score == 1.0
    assert result.passed_tests == 2


def test_key_error_mapping():
    evaluator = Evaluator()
    result = evaluator.score(
        SandboxResult(
            exit_code=1,
            stdout="1 failed",
            stderr='KeyError: "price"',
            timed_out=False,
            execution_time_ms=1,
        )
    )
    assert result.error_class == ErrorClass.KEY_ERROR
