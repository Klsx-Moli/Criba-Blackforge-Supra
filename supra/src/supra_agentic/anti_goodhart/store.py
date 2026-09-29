"""Persistence owned exclusively by the observer domain O."""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from .records import Diagnostic, DiagnosticStatus, ObserverFailure

_DIAGNOSTIC_STATUSES = {"OBSERVED", "UNKNOWN", "NOT_EVALUATED", "CONFLICT"}
_PROCESS_LOCK_RETRY_SECONDS = 0.01


@contextmanager
def _interprocess_file_lock(path: Path) -> Iterator[None]:
    """Serialize store mutations across independent observer processes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\\0")
            handle.flush()
        handle.seek(0)

        if os.name == "nt":
            import msvcrt

            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(_PROCESS_LOCK_RETRY_SECONDS)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)  # type: ignore[attr-defined]
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]


class ObserverStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self._lock = threading.Lock()

    @property
    def diagnostics_path(self) -> Path:
        return self.root / "diagnostics.jsonl"

    @property
    def lock_path(self) -> Path:
        return self.root / ".observer_store.lock"

    @property
    def failures_path(self) -> Path:
        return self.root / "observer_failures.jsonl"

    def _read_records(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                decoded = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                records.append(cast(dict[str, Any], decoded))
        return records

    @staticmethod
    def _validated_diagnostic(item: dict[str, Any]) -> Diagnostic | None:
        string_fields = (
            "diagnostic_id",
            "detector_id",
            "detector_version",
            "trace_sha256",
            "kind",
            "status",
            "message",
        )
        if not all(isinstance(item.get(key), str) for key in string_fields):
            return None
        status = item["status"]
        details = item.get("details")
        if status not in _DIAGNOSTIC_STATUSES or not isinstance(details, dict):
            return None
        try:
            diagnostic = Diagnostic(
                detector_id=item["detector_id"],
                detector_version=item["detector_version"],
                trace_sha256=item["trace_sha256"],
                kind=item["kind"],
                status=cast(DiagnosticStatus, status),
                message=item["message"],
                details=cast(dict[str, Any], details),
            )
            diagnostic_id = diagnostic.diagnostic_id
        except (TypeError, ValueError):
            return None
        if diagnostic_id != item["diagnostic_id"]:
            return None
        return diagnostic

    def read_diagnostics(self) -> list[dict[str, Any]]:
        return [
            item
            for item in self._read_records(self.diagnostics_path)
            if self._validated_diagnostic(item) is not None
        ]

    def read_failures(self) -> list[dict[str, Any]]:
        return self._read_records(self.failures_path)

    def append_diagnostic(self, diagnostic: Diagnostic) -> bool:
        with self._lock, _interprocess_file_lock(self.lock_path):
            existing = {str(item.get("diagnostic_id") or "") for item in self.read_diagnostics()}
            if diagnostic.diagnostic_id in existing:
                return False
            self.root.mkdir(parents=True, exist_ok=True)
            with self.diagnostics_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        diagnostic.to_record(),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
            return True

    def append_failure(self, failure: ObserverFailure) -> None:
        with self._lock, _interprocess_file_lock(self.lock_path):
            self.root.mkdir(parents=True, exist_ok=True)
            with self.failures_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        failure.to_record(),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
