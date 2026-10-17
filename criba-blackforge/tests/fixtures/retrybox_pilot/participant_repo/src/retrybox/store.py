from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Callable


class JobStore:
    """Tiny persistent job runner with intentionally incomplete retry semantics."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    payload_hash TEXT NOT NULL,
                    result_json TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _payload_hash(payload: Any) -> str:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def run(
        self,
        job_id: str,
        payload: Any,
        handler: Callable[[Any], Any],
    ) -> Any:
        """Run or recover a job.

        Known behavior is deliberately incomplete. Repair the implementation
        against README_TASK.md; do not change the public contract.
        """
        payload_hash = self._payload_hash(payload)

        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_hash, result_json FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()

        if row is not None:
            # BUG: same identity with different content is not rejected.
            return json.loads(row["result_json"])

        # BUG: check -> execute -> insert is not atomic across concurrent callers.
        result = handler(payload)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO jobs(job_id, payload_hash, result_json)
                VALUES (?, ?, ?)
                """,
                (job_id, payload_hash, json.dumps(result, ensure_ascii=False)),
            )
        return result
