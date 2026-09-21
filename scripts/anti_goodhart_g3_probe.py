#!/usr/bin/env python3
"""Local G3 evidence probe for CRIBA/BLACKFORGE.

A same-host subprocess cannot establish deployment isolation. Therefore this
probe emits FAIL on semantic interference and otherwise NOT_VERIFIED. It never
edits gate evidence or STANDARD_RELEASE_STATE.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from criba import engine
from criba.anti_goodhart.trace import seal_public_packet, sealed_trace_record

PERTURBATIONS = (
    "normal",
    "duplicate",
    "volume100",
    "detector_exception",
    "storage_failure",
    "latency",
    "restart",
)


def _normalized(packet: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(packet)
    value.pop("activation_id", None)
    value.pop("timestamp", None)
    return value


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _run_d(query: str) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    packet = engine.activate(query)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return packet, elapsed_ms


def _worker(
    *,
    trace_path: Path,
    observer_root: Path,
    perturbation: str,
    latency_ms: int,
) -> dict[str, Any]:
    worker = Path(__file__).with_name("anti_goodhart_g3_worker.py")
    env = dict(os.environ)
    env["ASTRA_G3_VERIFICATION"] = "1"
    proc = subprocess.run(
        [
            sys.executable,
            str(worker),
            "--trace",
            str(trace_path),
            "--observer-root",
            str(observer_root),
            "--perturbation",
            perturbation,
            "--latency-ms",
            str(latency_ms),
        ],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        return {
            "worker_exit": proc.returncode,
            "worker_error_type": "VERIFICATION_WORKER_FAILED",
        }
    decoded = json.loads(proc.stdout)
    if not isinstance(decoded, dict):
        raise ValueError("worker output must be a JSON object")
    return decoded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--query",
        default="¿Cómo proteger APIs de ataques de inyección?",
    )
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--latency-ms", type=int, default=250)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.iterations < 1:
        raise ValueError("iterations must be >= 1")

    control_packets: list[dict[str, Any]] = []
    control_durations: list[float] = []
    for _ in range(args.iterations):
        packet, duration = _run_d(args.query)
        control_packets.append(_normalized(packet))
        control_durations.append(duration)
    control_digests = [_digest(item) for item in control_packets]
    control_stable = len(set(control_digests)) == 1
    reference_digest = control_digests[0]

    rows: list[dict[str, Any]] = []
    semantic_interference = False

    with tempfile.TemporaryDirectory(prefix="astra-g3-criba-") as tmp:
        root = Path(tmp)
        for perturbation in PERTURBATIONS:
            before, before_ms = _run_d(args.query)
            normalized_before = _normalized(before)
            trace = seal_public_packet(before)
            trace_path = root / f"{perturbation}-trace.json"
            trace_path.write_text(
                json.dumps(sealed_trace_record(trace), sort_keys=True),
                encoding="utf-8",
            )
            observer_root = root / f"{perturbation}-observer"
            worker = _worker(
                trace_path=trace_path,
                observer_root=observer_root,
                perturbation=perturbation,
                latency_ms=args.latency_ms,
            )
            after, after_ms = _run_d(args.query)
            normalized_after = _normalized(after)
            before_digest = _digest(normalized_before)
            after_digest = _digest(normalized_after)
            semantic_equal = (
                control_stable
                and before_digest == reference_digest
                and after_digest == reference_digest
            )
            semantic_interference = semantic_interference or not semantic_equal
            rows.append(
                {
                    "perturbation": perturbation,
                    "semantic_equal": semantic_equal,
                    "before_digest": before_digest,
                    "after_digest": after_digest,
                    "control_digest": reference_digest,
                    "before_duration_ms": round(before_ms, 3),
                    "after_duration_ms": round(after_ms, 3),
                    "duration_delta_ms": round(after_ms - before_ms, 3),
                    "worker": worker,
                }
            )

    contaminated = copy.deepcopy(control_packets[0])
    contaminated.setdefault("decision", {})["pipeline_action"] = "G3_SENSITIVITY_MUTATION"
    sensitivity_control_pass = _digest(contaminated) != reference_digest

    status = (
        "FAIL"
        if semantic_interference or not control_stable or not sensitivity_control_pass
        else "NOT_VERIFIED"
    )
    report = {
        "schema_version": 1,
        "gate": "G3",
        "target": "CRIBA_BLACKFORGE",
        "status": status,
        "reason": (
            "semantic_interference_or_failed_sensitivity_control"
            if status == "FAIL"
            else "same_host_subprocess_does_not_prove_separate_resource_domain"
        ),
        "topology": "LOCAL_SAME_HOST_SUBPROCESS",
        "control_stable": control_stable,
        "control_digest": reference_digest,
        "control_durations_ms": [round(item, 3) for item in control_durations],
        "rows": rows,
        "sensitivity_control_pass": sensitivity_control_pass,
        "standard_release_state": "DISABLED",
        "automatic_activation_permitted": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "output": str(args.output)}, sort_keys=True))
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
