from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from debugagent.schemas.models import SessionResult


class ImprovementLog:
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
                CREATE TABLE IF NOT EXISTS improvement_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total_attempts INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    final_score REAL NOT NULL,
                    final_error_class TEXT NOT NULL,
                    session_duration_s REAL NOT NULL,
                    session_date REAL NOT NULL
                )
                """
            )

    def log_session(self, result: SessionResult) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO improvement_log (
                    task_id, status, total_attempts, total_tokens, final_score,
                    final_error_class, session_duration_s, session_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.task_id,
                    result.status.value,
                    result.total_attempts,
                    result.total_tokens,
                    result.final_score,
                    result.final_error_class.value,
                    result.session_duration_s,
                    time.time(),
                ),
            )

    def get_improvement_curve(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    final_error_class,
                    COUNT(*) as total_sessions,
                    AVG(total_attempts) as avg_retries,
                    AVG(CASE WHEN total_attempts = 1 THEN 100.0 ELSE 0.0 END) as one_shot_pct
                FROM improvement_log
                GROUP BY final_error_class
                ORDER BY total_sessions DESC
                """
            ).fetchall()

        return [
            {
                "error_class": row[0],
                "total_sessions": int(row[1]),
                "avg_retries": float(row[2]),
                "one_shot_pct": float(row[3]),
            }
            for row in rows
        ]

    def export_chart_data(self, output_path: str) -> None:
        data = self.get_improvement_curve()
        Path(output_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
