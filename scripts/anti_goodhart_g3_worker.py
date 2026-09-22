#!/usr/bin/env python3
"""G3 verification worker for SUPRA.

Verification-only: exercises the private O-domain core and cannot enable the
product STANDARD release latch.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from supra_agentic.anti_goodhart.detectors import DetectorSpec
from supra_agentic.anti_goodhart.observer import _observe_trace_after_gate
from supra_agentic.anti_goodhart.records import Diagnostic
from supra_agentic.anti_goodhart.store import ObserverStore
from supra_agentic.anti_goodhart.trace import load_sealed_trace


def _require_verification_mode() -> None:
    if os.getenv("ASTRA_G3_VERIFICATION") != "1":
        raise SystemExit("ASTRA_G3_VERIFICATION=1 is required")


def main() -> int:
    _require_verification_mode()
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--observer-root", type=Path, required=True)
    parser.add_argument(
        "--perturbation",
        choices=(
            "normal",
            "duplicate",
            "volume100",
            "detector_exception",
            "storage_failure",
            "latency",
            "restart",
        ),
        default="normal",
    )
    parser.add_argument("--latency-ms", type=int, default=200)
    args = parser.parse_args()

    if args.latency_ms < 0:
        raise ValueError("latency-ms must be >= 0")

    raw = json.loads(args.trace.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("trace record must be a JSON object")
    trace = load_sealed_trace(raw)

    class BrokenStore(ObserverStore):
        def append_diagnostic(self, diagnostic):
            raise OSError("G3_VERIFICATION_STORAGE_FAILURE")

    def broken_detector(_trace):
        raise RuntimeError("G3_VERIFICATION_DETECTOR_FAILURE")

    def volume_detector(current_trace):
        return [
            Diagnostic(
                detector_id="g3_volume",
                detector_version="1",
                trace_sha256=current_trace.payload_sha256,
                kind=f"volume-{index}",
                status="OBSERVED",
                message="G3 verification diagnostic",
                details={"index": index},
            )
            for index in range(100)
        ]

    store: ObserverStore = (
        BrokenStore(args.observer_root)
        if args.perturbation == "storage_failure"
        else ObserverStore(args.observer_root)
    )
    detectors = None
    if args.perturbation == "detector_exception":
        detectors = (DetectorSpec("g3_broken", "1", broken_detector),)
    elif args.perturbation == "volume100":
        detectors = (DetectorSpec("g3_volume", "1", volume_detector),)

    started = time.perf_counter()
    if args.perturbation == "latency":
        time.sleep(args.latency_ms / 1000.0)

    kwargs = {"trace": trace, "store": store}
    if detectors is not None:
        kwargs["detectors"] = detectors
    result = _observe_trace_after_gate(**kwargs)

    if args.perturbation == "duplicate":
        duplicate = _observe_trace_after_gate(**kwargs)
        duplicate_count = duplicate.duplicate_diagnostics
    else:
        duplicate_count = result.duplicate_diagnostics

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    print(
        json.dumps(
            {
                "perturbation": args.perturbation,
                "trace_sha256": trace.payload_sha256,
                "inserted_diagnostics": result.inserted_diagnostics,
                "duplicate_diagnostics": duplicate_count,
                "failures": list(result.failures),
                "elapsed_ms": round(elapsed_ms, 3),
                "injected_latency_ms": args.latency_ms if args.perturbation == "latency" else 0,
                "worker_pid": os.getpid(),
                "verification_only": True,
                "standard_release_changed": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
