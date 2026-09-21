"""Out-of-band STANDARD observer runner.

No function in this module is called by CRIBA's decisional runtime.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .detectors import DEFAULT_DETECTORS, DetectorSpec
from .gate import GateEvidence, ObserverMode, StandardDisabledError, standard_allowed
from .records import ObserverFailure
from .store import ObserverStore
from .trace import SealedTrace


@dataclass(frozen=True, slots=True)
class ObserverRun:
    mode: ObserverMode
    trace_sha256: str
    inserted_diagnostics: int
    duplicate_diagnostics: int
    failures: tuple[str, ...]


def observe_trace(
    trace: SealedTrace,
    *,
    store: ObserverStore,
    mode: ObserverMode,
    gate_evidence: GateEvidence | None = None,
    current_scope_fingerprint: str = "",
    detectors: Sequence[DetectorSpec] = DEFAULT_DETECTORS,
) -> ObserverRun:
    """Observe a sealed trace without any callback into decisional state."""

    if mode is ObserverMode.OFF:
        return ObserverRun(
            mode=mode,
            trace_sha256=trace.payload_sha256,
            inserted_diagnostics=0,
            duplicate_diagnostics=0,
            failures=(),
        )

    if not standard_allowed(
        gate_evidence,
        current_scope_fingerprint=current_scope_fingerprint,
    ):
        raise StandardDisabledError(
            "STANDARD_DISABLED: G1-G4/deployment scope evidence is incomplete or stale"
        )

    inserted = 0
    duplicates = 0
    failures: list[str] = []

    for detector in detectors:
        try:
            diagnostics = detector.run(trace)
        except Exception as exc:  # noqa: BLE001 - observer failure is confined to O
            error_type = type(exc).__name__
            failures.append(f"{detector.detector_id}:{error_type}")
            try:
                store.append_failure(
                    ObserverFailure(
                        trace_sha256=trace.payload_sha256,
                        detector_id=detector.detector_id,
                        error_type=error_type,
                    )
                )
            except Exception as store_exc:  # noqa: BLE001 - storage failure is also O-only
                failures.append(f"observer_store:{type(store_exc).__name__}")
            continue

        for diagnostic in diagnostics:
            try:
                if store.append_diagnostic(diagnostic):
                    inserted += 1
                else:
                    duplicates += 1
            except Exception as exc:  # noqa: BLE001 - no propagation into D
                failures.append(f"observer_store:{type(exc).__name__}")

    return ObserverRun(
        mode=mode,
        trace_sha256=trace.payload_sha256,
        inserted_diagnostics=inserted,
        duplicate_diagnostics=duplicates,
        failures=tuple(failures),
    )
