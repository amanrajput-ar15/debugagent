from __future__ import annotations

from typing import Any

from debugagent.schemas.models import Attempt


class EpisodicMemory:
    COLLECTION_NAME = "debug_attempts"
    EMBED_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, persist_dir: str = "./chroma_db"):
        import chromadb
        from chromadb.config import Settings

        self.client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._embedder = None

    def _get_embedder(self):
        if self._embedder is None:
            print("Downloading embedding model (one-time, ~80MB)...")
            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer(self.EMBED_MODEL)
        return self._embedder

    @staticmethod
    def _to_vector(value: Any) -> list[float]:
        if hasattr(value, "tolist"):
            return value.tolist()
        return list(value)

    def _embed_attempt_text(self, attempt: Attempt) -> str:
        return (
            f"ERROR: {attempt.eval_result.error_class.value}\n"
            f"MESSAGE: {attempt.eval_result.error_message}\n"
            f"CODE_SNIPPET: {attempt.repaired_code[:500]}\n"
        )

    def retrieve(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        count = self.collection.count()
        n_results = min(k, count)
        if n_results == 0:
            return []

        embedder = self._get_embedder()
        query_embedding = self._to_vector(embedder.encode(query))

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        memories: list[dict[str, Any]] = []
        for i in range(len(results["ids"][0])):
            memories.append(
                {
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity": 1 - results["distances"][0][i],
                }
            )
        return memories

    def store_failure(self, attempt: Attempt) -> None:
        self._store(attempt, outcome="FAILURE")

    def store_success(self, attempt: Attempt) -> None:
        self._store(attempt, outcome="SUCCESS")

    def _store(self, attempt: Attempt, outcome: str) -> None:
        text = self._embed_attempt_text(attempt)
        embedder = self._get_embedder()
        embedding = self._to_vector(embedder.encode(text))

        self.collection.add(
            ids=[attempt.attempt_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[
                {
                    "task_id": attempt.task_id,
                    "error_class": attempt.eval_result.error_class.value,
                    "error_message": attempt.eval_result.error_message,
                    "score": attempt.eval_result.score,
                    "outcome": outcome,
                    "iteration": attempt.iteration,
                    "timestamp": str(attempt.timestamp),
                }
            ],
        )
