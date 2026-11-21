"""Synthetic lab executor for broker tests.

NOTHING here performs a real probe. Every operation returns a labelled
fixture whose `synthetic` marker is True, so a test can never present a
fixture as an execution of record. The point is to exercise the broker's
authorisation, idempotence and recovery logic with a controllable failure
surface, not to prove any finding.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


class SyntheticLabExecutor:
    """Typed, in-memory, explicitly synthetic."""

    def __init__(self, *, fail_on: str | None = None, crash_on: str | None = None) -> None:
        self.fail_on = fail_on
        self.crash_on = crash_on
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def available_operations(self) -> Sequence[str]:
        from criba.blackforge_broker import TYPED_OPERATIONS

        return sorted(TYPED_OPERATIONS)

    def execute(self, kind: str, target: str, params: Mapping[str, Any]) -> dict[str, Any]:
        self.calls.append((kind, target, dict(params)))
        if self.crash_on and self.crash_on == kind:
            raise RuntimeError(
                f"caida simulada tras posible efecto en {kind} (laboratorio sintetico)"
            )
        if self.fail_on and self.fail_on == kind:
            return {
                "synthetic": True,
                "status": "REJECTED_BY_LAB",
                "kind": kind,
                "target": target,
            }
        return {
            "synthetic": True,
            "status": "FIXTURE_ONLY_NOT_A_REAL_PROBE",
            "kind": kind,
            "target": target,
            "params": dict(params),
        }


class CountingExecutor(SyntheticLabExecutor):
    """Records dispatch count so double-dispatch can be observed, not inferred."""

    def __init__(self) -> None:
        super().__init__()
        self.dispatch_count = 0

    def execute(self, kind: str, target: str, params: Mapping[str, Any]) -> dict[str, Any]:
        self.dispatch_count += 1
        return super().execute(kind, target, params)