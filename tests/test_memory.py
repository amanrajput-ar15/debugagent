import pytest

chromadb = pytest.importorskip("chromadb")

from debugagent.memory.episodic import EpisodicMemory
from debugagent.schemas.models import Attempt, ErrorClass, EvalResult


class FakeEmbedder:
    def encode(self, text):
        return [0.1] * 384


def _attempt(i: int) -> Attempt:
    return Attempt(
        attempt_id=f"attempt-{i}",
        task_id="task-1",
        iteration=i,
        repaired_code="print('x')",
        eval_result=EvalResult(
            score=0.0,
            passed_tests=0,
            failed_tests=1,
            total_tests=1,
            error_class=ErrorClass.KEY_ERROR,
            error_message="KeyError: missing",
            raw_output="",
        ),
        prompt_patch=None,
        tokens_used=0,
        latency_ms=0.0,
        code_hash="hash",
    )


def test_memory_store_and_retrieve(tmp_path):
    memory = EpisodicMemory(persist_dir=str(tmp_path / "chroma"))
    memory._embedder = FakeEmbedder()

    memory.store_failure(_attempt(1))
    memory.store_failure(_attempt(2))
    memory.store_success(_attempt(3))

    assert memory.collection.count() == 3
    hits = memory.retrieve("missing key in dict", k=5)
    assert isinstance(hits, list)
    assert len(hits) == 3


def test_memory_cold_start(tmp_path):
    memory = EpisodicMemory(persist_dir=str(tmp_path / "empty"))
    hits = memory.retrieve("nothing", k=3)
    assert hits == []
