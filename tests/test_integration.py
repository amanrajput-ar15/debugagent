import pytest

from debugagent.config import AgentConfig
from debugagent.schemas.models import BugTask


@pytest.mark.skip(reason="Integration test requires external dependencies and keys")
def test_integration_placeholder():
    config = AgentConfig.from_env(no_trace=True)
    task = BugTask(
        task_id="abc123",
        buggy_code="def add(a,b):\n    return a-b\n",
        test_suite="from solution import add\n\ndef test_add():\n    assert add(2,1)==3\n",
        max_retries=1,
    )
    assert config.max_retries >= 1
    assert task.task_id == "abc123"
