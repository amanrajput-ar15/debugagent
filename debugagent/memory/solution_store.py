from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class SolutionStore:
    def __init__(self, sqlite_path: str = "./debugagent.db"):
        self.sqlite_path = sqlite_path
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.sqlite_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS solution_store (
                    task_id TEXT PRIMARY KEY,
                    accepted_code TEXT NOT NULL,
                    iterations_needed INTEGER NOT NULL,
                    session_date REAL NOT NULL,
                    error_class TEXT
                )
                """
            )

    def save(self, task_id: str, accepted_code: str, iterations_needed: int, error_class: str = "UNKNOWN") -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO solution_store (task_id, accepted_code, iterations_needed, session_date, error_class)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(task_id)
                DO UPDATE SET
                  accepted_code=excluded.accepted_code,
                  iterations_needed=excluded.iterations_needed,
                  session_date=excluded.session_date,
                  error_class=excluded.error_class
                """,
                (task_id, accepted_code, iterations_needed, time.time(), error_class),
            )

    def lookup(self, task_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT accepted_code FROM solution_store WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return row[0] if row else None
