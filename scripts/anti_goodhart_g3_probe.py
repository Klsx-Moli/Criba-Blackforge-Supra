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

from supra_agentic.anti_goodhart.trace import (
    project_public_posture,
    seal_public_posture,
    sealed_trace_record,
)
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


def _normalized_public(posture: dict[str, Any]) -> dict[str, Any]:
    value = project_public_posture(posture)
    normalized = copy.deepcopy(value)
    normalized["project_id"] = "<PROJECT>"
    selected = normalized.get("selected_candidate")
    if isinstance(selected, dict):
        selected["candidate_id"] = "<CANDIDATE>"
    executions = normalized.get("restricted_execution_results")
    if isinstance(executions, list):
        for item in executions:
            if not isinstance(item, dict):
                continue
            for key in (
                "execution_id",
                "candidate_id",
                "mechanism_version",
                "claim_id",
                "protocol_version",
            ):
                item[key] = f"<{key.upper()}>"
            item["duration_ms"] = None
    checkpoints = normalized.get("checkpoints")
    if isinstance(checkpoints, list):
        for item in checkpoints:
            if isinstance(item, dict):
                item["checkpoint_id"] = "<CHECKPOINT>"
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
    parser.add_argument("--objective", default="Design a bounded deterministic service")
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--latency-ms", type=int, default=250)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.iterations < 1:
        raise ValueError("iterations must be >= 1")

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
            after, after_ms = _run_d(
                args.objective,
                root / f"{perturbation}-after",
                f"g3-{index}-after",
            )
            normalized_after = _normalized_public(after)
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

        contaminated = copy.deepcopy(control_values[0])
        contaminated["stage"] = "G3_SENSITIVITY_MUTATION"
        sensitivity_control_pass = _digest(contaminated) != reference_digest

        status = (
            "FAIL"
            if semantic_interference or not control_stable or not sensitivity_control_pass
            else "NOT_VERIFIED"
        )
        report = {
            "schema_version": 1,
            "gate": "G3",
            "target": "SUPRA",
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
