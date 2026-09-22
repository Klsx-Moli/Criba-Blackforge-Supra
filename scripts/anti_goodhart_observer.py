#!/usr/bin/env python3
"""External post-run Anti-Goodhart observer.

This process consumes an already sealed public trace. It is intentionally not
called by CRIBA's decisional runtime.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from criba.anti_goodhart.gate import GateEvidence, ObserverMode
from criba.anti_goodhart.observer import observe_trace
from criba.anti_goodhart.store import ObserverStore
from criba.anti_goodhart.trace import load_sealed_trace


def _gate_evidence(path: Path | None) -> GateEvidence | None:
    if path is None:
        return None
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("gate evidence must be a JSON object")
    return GateEvidence(
        scope_fingerprint=str(raw.get("scope_fingerprint") or ""),
        g1_pass=raw.get("g1_pass") is True,
        g2_pass=raw.get("g2_pass") is True,
        g3_pass=raw.get("g3_pass") is True,
        g4_pass=raw.get("g4_pass") is True,
        all_applicable_rows_executed=raw.get("all_applicable_rows_executed") is True,
        sensitivity_controls_pass=raw.get("sensitivity_controls_pass") is True,
        deployment_scope_matches=raw.get("deployment_scope_matches") is True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--observer-root", type=Path, required=True)
    parser.add_argument("--mode", choices=("OFF", "STANDARD"), default="OFF")
    parser.add_argument("--gate-evidence", type=Path)
    parser.add_argument("--scope-fingerprint", default="")
    args = parser.parse_args()

    raw = json.loads(args.trace.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("sealed trace file must contain a JSON object")
    trace = load_sealed_trace(raw)
    result = observe_trace(
        trace,
        store=ObserverStore(args.observer_root),
        mode=ObserverMode(args.mode),
        gate_evidence=_gate_evidence(args.gate_evidence),
        current_scope_fingerprint=args.scope_fingerprint,
    )
    print(
        json.dumps(
            {
                "mode": result.mode.value,
                "trace_sha256": result.trace_sha256,
                "inserted_diagnostics": result.inserted_diagnostics,
                "duplicate_diagnostics": result.duplicate_diagnostics,
                "failures": list(result.failures),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
