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


def _worker_timeout_seconds(latency_ms: int) -> float:
    return max(10.0, max(0, latency_ms) / 1000.0 + 5.0)


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
    try:
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
            timeout=_worker_timeout_seconds(latency_ms),
        )
    except subprocess.TimeoutExpired:
        return {
            "worker_exit": None,
            "worker_error_type": "VERIFICATION_WORKER_TIMEOUT",
            "perturbation": perturbation,
        }

    if proc.returncode != 0:
        return {
            "worker_exit": proc.returncode,
            "worker_error_type": "VERIFICATION_WORKER_FAILED",
            "perturbation": perturbation,
        }
    try:
        decoded = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "worker_exit": 0,
            "worker_error_type": "VERIFICATION_WORKER_INVALID_JSON",
            "perturbation": perturbation,
        }
    if not isinstance(decoded, dict):
        return {
            "worker_exit": 0,
            "worker_error_type": "VERIFICATION_WORKER_INVALID_PAYLOAD",
            "perturbation": perturbation,
        }
    decoded.setdefault("worker_exit", 0)
    return decoded


def _count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _perturbation_ok(
    perturbation: str,
    worker: dict[str, Any],
    *,
    latency_ms: int,
) -> bool:
    if worker.get("worker_exit") != 0:
        return False
    if worker.get("perturbation") != perturbation:
        return False
    if worker.get("verification_only") is not True:
        return False
    if worker.get("standard_release_changed") is not False:
        return False

    inserted = _count(worker.get("inserted_diagnostics"))
    duplicates = _count(worker.get("duplicate_diagnostics"))
    failures = worker.get("failures")
    elapsed_ms = _number(worker.get("elapsed_ms"))
    if inserted is None or duplicates is None or not isinstance(failures, list):
        return False

    if perturbation == "normal":
        return inserted >= 1 and not failures
    if perturbation == "duplicate":
        return inserted >= 1 and duplicates >= 1 and not failures
    if perturbation == "volume100":
        return inserted == 100 and not failures
    if perturbation == "detector_exception":
        return inserted == 0 and "g3_broken:RuntimeError" in failures
    if perturbation == "storage_failure":
        return (
            inserted == 0
            and bool(failures)
            and all(item == "observer_store:OSError" for item in failures)
        )
    if perturbation == "latency":
        return (
            inserted >= 1
            and not failures
            and elapsed_ms is not None
            and elapsed_ms >= latency_ms * 0.8
        )
    if perturbation == "restart":
        return inserted >= 1 and duplicates >= 1 and not failures
    return False


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

    if args.iterations < 2:
        raise ValueError("iterations must be >= 2")
    if args.latency_ms < 0:
        raise ValueError("latency-ms must be >= 0")

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
    probe_complete = True

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
            perturbation_ok = _perturbation_ok(
                perturbation,
                worker,
                latency_ms=args.latency_ms,
            )
            probe_complete = probe_complete and perturbation_ok

            after, after_ms = _run_d(args.query)
            normalized_after = _normalized(after)
            before_digest = _digest(normalized_before)
            after_digest = _digest(normalized_after)
            semantic_equal = bool(
                control_stable
                and before_digest == reference_digest
                and after_digest == reference_digest
            )
            if control_stable and not semantic_equal:
                semantic_interference = True
            rows.append(
                {
                    "perturbation": perturbation,
                    "perturbation_ok": perturbation_ok,
                    "semantic_equal": semantic_equal,
                    "before_digest": before_digest,
                    "after_digest": after_digest,
                    "control_digest": reference_digest,
                    "before_duration_ms": round(before_ms, 3),
                    "after_duration_ms": round(after_ms, 3),
                    "duration_delta_ms": round(after_ms - before_ms, 3),
                    "timing_claim": "DESCRIPTIVE_ONLY_NOT_G3_RESOURCE_ISOLATION",
                    "worker": worker,
                }
            )

    contaminated = copy.deepcopy(control_packets[0])
    contaminated.setdefault("decision", {})["pipeline_action"] = "G3_SENSITIVITY_MUTATION"
    sensitivity_control_pass = _digest(contaminated) != reference_digest

    if semantic_interference or not sensitivity_control_pass:
        status = "FAIL"
        reason = "semantic_interference_or_failed_sensitivity_control"
    elif not control_stable:
        status = "NOT_VERIFIED"
        reason = "unstable_control_trajectory"
    elif not probe_complete:
        status = "NOT_VERIFIED"
        reason = "local_probe_incomplete"
    else:
        status = "NOT_VERIFIED"
        reason = "same_host_subprocess_does_not_prove_separate_resource_domain"

    report = {
        "schema_version": 1,
        "gate": "G3",
        "target": "CRIBA_BLACKFORGE",
        "status": status,
        "reason": reason,
        "topology": "LOCAL_SAME_HOST_SUBPROCESS",
        "probe_complete": probe_complete,
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
    if status == "FAIL":
        return 1
    if not probe_complete or not control_stable:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
