from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable


class JobStore:
    """Tiny persistent job runner with complete retry semantics.

    Repairs the implementation against README_TASK.md without changing the
    public contract (run(job_id, payload, handler) -> Any).
    """

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    payload_hash TEXT NOT NULL,
                    result_json TEXT,
                    state TEXT NOT NULL DEFAULT 'pending'
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

        1. If (job_id, payload_hash) exists -> replay result.
        2. If job_id exists but payload_hash differs -> ValueError (identity clash).
        3. If new -> execute handler, then INSERT atomically (UNIQUE constraint
           prevents double-execution in a race).
        """
        payload_hash = self._payload_hash(payload)

        while True:
            # Try to claim the job by inserting a pending row atomically.
            try:
                with self._connect() as conn:
                    conn.execute(
                        """
                        INSERT INTO jobs (job_id, payload_hash, result_json, state)
                        VALUES (?, ?, NULL, 'pending')
                        """,
                        (job_id, payload_hash),
                    )
                break  # We claimed the job.
            except sqlite3.IntegrityError:
                # Someone else inserted this job_id first. Inspect what they did.
                row = self._lookup(job_id)
                if row is None:
                    # Row was deleted (handler failed). Loop and try to claim.
                    time.sleep(0.005)
                    continue
                if row["payload_hash"] != payload_hash:
                    raise ValueError(
                        f"job_id '{job_id}' already exists with different payload"
                    )
                if row["state"] == "completed":
                    return json.loads(row["result_json"])
                # Row is pending — another caller is still executing the handler.
                # Poll until it completes or is deleted.
                time.sleep(0.01)

        # We own the job. Execute the handler.
        try:
            result = handler(payload)
        except Exception:
            # Handler failed — remove the pending row so a retry can claim it.
            with self._connect() as conn:
                conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
            raise

        # Persist the result by transitioning pending -> completed.
        result_json = json.dumps(result, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET result_json = ?, state = 'completed' WHERE job_id = ?",
                (result_json, job_id),
            )
        return result

    def _lookup(self, job_id: str) -> sqlite3.Row | None:
        """Return the row for job_id, or None if it doesn't exist."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_hash, result_json, state FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return row
