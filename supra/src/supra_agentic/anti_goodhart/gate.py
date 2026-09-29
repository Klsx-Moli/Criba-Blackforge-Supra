"""Binary scope-bound activation gate for observational STANDARD."""

from __future__ import annotations

import collections.abc
import dataclasses
import enum
import hashlib
import json

STANDARD_RELEASE_STATE = "DISABLED"


class ObserverMode(str, enum.Enum):
    OFF = "OFF"
    STANDARD = "STANDARD"


class StandardDisabledError(RuntimeError):
    """Raised only in the external observer when STANDARD is not accredited."""


@dataclasses.dataclass(frozen=True, slots=True)
class GateEvidence:
    scope_fingerprint: str
    g1_pass: bool
    g2_pass: bool
    g3_pass: bool
    g4_pass: bool
    all_applicable_rows_executed: bool
    sensitivity_controls_pass: bool
    deployment_scope_matches: bool

    def allows(self, current_scope_fingerprint: str) -> bool:
        return bool(
            self.scope_fingerprint
            and self.scope_fingerprint == current_scope_fingerprint
            and self.g1_pass
            and self.g2_pass
            and self.g3_pass
            and self.g4_pass
            and self.all_applicable_rows_executed
            and self.sensitivity_controls_pass
            and self.deployment_scope_matches
        )


def gate_evidence_satisfies(
    evidence: GateEvidence | None,
    *,
    current_scope_fingerprint: str,
) -> bool:
    """Validate G1-G4 evidence without granting product activation."""

    return bool(evidence and evidence.allows(current_scope_fingerprint))


def standard_allowed(
    evidence: GateEvidence | None,
    *,
    current_scope_fingerprint: str,
) -> bool:
    """Product activation requires evidence AND an explicit versioned release."""

    return bool(
        STANDARD_RELEASE_STATE == "ALLOWED"
        and gate_evidence_satisfies(
            evidence,
            current_scope_fingerprint=current_scope_fingerprint,
        )
    )


def scope_fingerprint(
    *,
    runtime_version: str,
    export_schema: str,
    detector_versions: collections.abc.Sequence[str],
    isolation_profile: str,
) -> str:
    payload = {
        "runtime_version": runtime_version,
        "export_schema": export_schema,
        "detector_versions": list(detector_versions),
        "isolation_profile": isolation_profile,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
