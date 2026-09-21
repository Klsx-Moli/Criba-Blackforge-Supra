"""Persistence owned exclusively by the observer domain O."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, cast

from .records import Diagnostic, ObserverFailure


class ObserverStore:
    """Append-only O-domain store with stable diagnostic deduplication.

    The store path is supplied by the external observer deployment. Product
    runtime code never imports or constructs this class.
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self._lock = threading.Lock()

    @property
    def diagnostics_path(self) -> Path:
        return self.root / "diagnostics.jsonl"

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

    def read_diagnostics(self) -> list[dict[str, Any]]:
        return self._read_records(self.diagnostics_path)

    def read_failures(self) -> list[dict[str, Any]]:
        return self._read_records(self.failures_path)

    def append_diagnostic(self, diagnostic: Diagnostic) -> bool:
        """Append once; duplicate delivery of the same event is idempotent."""

        with self._lock:
            existing = {
                str(item.get("diagnostic_id") or "")
                for item in self._read_records(self.diagnostics_path)
            }
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
        with self._lock:
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
