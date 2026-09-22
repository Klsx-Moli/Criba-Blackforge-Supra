"""Typed observational records without decisional authority."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

DiagnosticStatus = Literal["OBSERVED", "UNKNOWN", "NOT_EVALUATED", "CONFLICT"]


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


@dataclass(frozen=True, slots=True)
class Diagnostic:
    detector_id: str
    detector_version: str
    trace_sha256: str
    kind: str
    status: DiagnosticStatus
    message: str
    details: dict[str, Any]

    @property
    def diagnostic_id(self) -> str:
        payload = {
            "detector_id": self.detector_id,
            "detector_version": self.detector_version,
            "trace_sha256": self.trace_sha256,
            "kind": self.kind,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }
        return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()

    def to_record(self) -> dict[str, Any]:
        return {
            "diagnostic_id": self.diagnostic_id,
            "detector_id": self.detector_id,
            "detector_version": self.detector_version,
            "trace_sha256": self.trace_sha256,
            "kind": self.kind,
            "status": self.status,
            "message": self.message,
            "details": json.loads(_canonical_json(self.details)),
        }


@dataclass(frozen=True, slots=True)
class ObserverFailure:
    trace_sha256: str
    detector_id: str
    error_type: str

    def to_record(self) -> dict[str, str]:
        return {
            "trace_sha256": self.trace_sha256,
            "detector_id": self.detector_id,
            "error_type": self.error_type,
        }
