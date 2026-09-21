"""Smoke tests for the local SUPRA G3 verification harness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from supra_agentic.anti_goodhart.trace import seal_public_posture, sealed_trace_record

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts" / "anti_goodhart_g3_probe.py"
WORKER = ROOT / "scripts" / "anti_goodhart_g3_worker.py"


def test_g3_probe_help_and_no_auto_activation_contract() -> None:
    proc = subprocess.run(
        [sys.executable, str(PROBE), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0

    source = PROBE.read_text(encoding="utf-8")
    assert '"NOT_VERIFIED"' in source
    assert '"automatic_activation_permitted": False' in source
    assert 'STANDARD_RELEASE_STATE = "ALLOWED"' not in source
    assert '"PASS"' not in source


def test_g3_worker_requires_verification_guard() -> None:
    env = dict(os.environ)
    env.pop("ASTRA_G3_VERIFICATION", None)
    proc = subprocess.run(
        [sys.executable, str(WORKER), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert proc.returncode != 0
    assert "ASTRA_G3_VERIFICATION=1 is required" in (proc.stdout + proc.stderr)


def test_g3_worker_executes_synthetic_trace_without_product_release(
    tmp_path: Path,
) -> None:
    trace = seal_public_posture({"project_id": "g3-smoke", "stage": "COMPLETED"})
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(sealed_trace_record(trace), sort_keys=True),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["ASTRA_G3_VERIFICATION"] = "1"
    proc = subprocess.run(
        [
            sys.executable,
            str(WORKER),
            "--trace",
            str(trace_path),
            "--observer-root",
            str(tmp_path / "observer"),
            "--perturbation",
            "normal",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["verification_only"] is True
    assert payload["standard_release_changed"] is False
    assert payload["perturbation"] == "normal"
