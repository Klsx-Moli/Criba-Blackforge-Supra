#!/usr/bin/env python3
"""Local G3 evidence probe for SUPRA.

Uses deterministic use_model=False workflow runs in temporary storage. A
same-host subprocess cannot establish deployment isolation, so the maximum
automatic result is NOT_VERIFIED.
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

from supra_agentic.anti_goodhart.trace import seal_public_posture, sealed_trace_record
from supra_agentic.runner import TaskmasterRunner
from supra_agentic.state import state_manager

PERTURBATIONS = (
    "normal",
    "duplicate",
    "volume100",
    "detector_exception",
    "storage_failure",
    "latency",
    "restart",
)

_VOLATILE_KEYS = {
    "project_id",
    "created_at",
    "updated_at",
    "timestamp",
    "task_id",
    "candidate_id",
    "selected_candidate_id",
    "report_id",
    "execution_id",
    "checkpoint_id",
    "audit_sha256",
    "duration_ms",
    "mechanism_version",
    "output_log",
    "summary",
    "evidence_summary",
    "restricted_execution_ids",
}

_VOLATILE_CONTAINERS = {"evidence_provenance"}


def _semantic_value(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if key in _VOLATILE_KEYS or key in _VOLATILE_CONTAINERS:
                continue
            normalized[key] = _semantic_value(item)
        return normalized
    if isinstance(value, list):
        return [_semantic_value(item) for item in value]
    return copy.deepcopy(value)


def _normalized_public(posture: dict[str, Any]) -> dict[str, Any]:
    """Normalize complete decisional semantics while removing run-ephemeral data."""

    normalized = _semantic_value(posture)
    if not isinstance(normalized, dict):
        raise TypeError("normalized SUPRA posture must be an object")
    return normalized


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _run_d(objective: str, storage_root: Path, project_id: str) -> tuple[dict[str, Any], float]:
    storage_root.mkdir(parents=True, exist_ok=True)
    state_manager.storage_dir = storage_root
    state_manager.storage_mode = "CONFIGURED_FILESYSTEM"
    state_manager._projects.clear()
    runner = TaskmasterRunner()
    started = time.perf_counter()
    posture = runner.run_golden_path(
        objective,
        project_id=project_id,
        max_retries=0,
        use_model=False,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return posture.model_dump(mode="json"), elapsed_ms


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
    parser.add_argument("--objective", default="Design a bounded deterministic service")
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--latency-ms", type=int, default=250)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.iterations < 2:
        raise ValueError("iterations must be >= 2")
    if args.latency_ms < 0:
        raise ValueError("latency-ms must be >= 0")

    with tempfile.TemporaryDirectory(prefix="astra-g3-supra-") as tmp:
        root = Path(tmp)
        control_values: list[dict[str, Any]] = []
        control_durations: list[float] = []
        for index in range(args.iterations):
            posture, duration = _run_d(
                args.objective,
                root / f"control-{index}",
                f"g3-control-{index}",
            )
            control_values.append(_normalized_public(posture))
            control_durations.append(duration)

        control_digests = [_digest(item) for item in control_values]
        control_stable = len(set(control_digests)) == 1
        reference_digest = control_digests[0]
        rows: list[dict[str, Any]] = []
        semantic_interference = False
        probe_complete = True

        for index, perturbation in enumerate(PERTURBATIONS):
            before, before_ms = _run_d(
                args.objective,
                root / f"{perturbation}-before",
                f"g3-{index}-before",
            )
            normalized_before = _normalized_public(before)
            trace = seal_public_posture(before)
            trace_path = root / f"{perturbation}-trace.json"
            trace_path.write_text(
                json.dumps(sealed_trace_record(trace), sort_keys=True),
                encoding="utf-8",
            )
            worker = _worker(
                trace_path=trace_path,
                observer_root=root / f"{perturbation}-observer",
                perturbation=perturbation,
                latency_ms=args.latency_ms,
            )
            perturbation_ok = _perturbation_ok(
                perturbation,
                worker,
                latency_ms=args.latency_ms,
            )
            probe_complete = probe_complete and perturbation_ok

            after, after_ms = _run_d(
                args.objective,
                root / f"{perturbation}-after",
                f"g3-{index}-after",
            )
            normalized_after = _normalized_public(after)
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

        contaminated = copy.deepcopy(control_values[0])
        contaminated["stage"] = "G3_SENSITIVITY_MUTATION"
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
            "target": "SUPRA",
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
