from debugagent.schemas.models import BugTask, ErrorClass, EvalResult, PromptPatch


def test_bugtask_defaults():
    task = BugTask(task_id="abc123", buggy_code="print('x')", test_suite="def test_x():\n    assert True")
    assert task.max_retries == 5
    assert task.constraints == []


def test_eval_result_score_range():
    result = EvalResult(
        score=0.5,
        passed_tests=1,
        failed_tests=1,
        total_tests=2,
        error_class=ErrorClass.UNKNOWN,
        error_message="",
        raw_output="",
    )
    assert result.score == 0.5


def test_prompt_patch_enum():
    patch = PromptPatch(
        root_cause="x",
        fix_strategy="y",
        specific_hint="z",
        error_class=ErrorClass.KEY_ERROR,
    )
    assert patch.error_class == ErrorClass.KEY_ERROR
