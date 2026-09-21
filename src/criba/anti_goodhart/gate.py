"""Binary activation gate for observational STANDARD mode."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ObserverMode(str, Enum):
    OFF = "OFF"
    STANDARD = "STANDARD"


class StandardDisabledError(RuntimeError):
    """Raised by the external observer when STANDARD is not accredited."""


@dataclass(frozen=True, slots=True)
class GateEvidence:
    """Evidence for one versioned deployment scope.

    A boolean here is not a scientific result. It records whether the named
    non-interference gate was executed and passed for the exact scope
    fingerprint. Missing/false values keep STANDARD disabled.
    """

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


def standard_allowed(
    evidence: GateEvidence | None,
    *,
    current_scope_fingerprint: str,
) -> bool:
    """Return the binary ASTRA activation decision for STANDARD."""

    return bool(evidence and evidence.allows(current_scope_fingerprint))
