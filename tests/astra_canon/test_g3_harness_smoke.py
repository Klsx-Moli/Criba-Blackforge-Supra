"""Smoke and adversarial tests for the local G3 verification harness."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from criba.anti_goodhart.trace import seal_public_packet, sealed_trace_record

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts" / "anti_goodhart_g3_probe.py"
WORKER = ROOT / "scripts" / "anti_goodhart_g3_worker.py"


def _load_probe():
    spec = importlib.util.spec_from_file_location("criba_g3_probe_under_test", PROBE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    trace = seal_public_packet({"activation_id": "g3-smoke"})
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


def test_g3_worker_latency_is_inside_elapsed_measurement(tmp_path: Path) -> None:
    trace = seal_public_packet({"activation_id": "g3-latency"})
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
            str(tmp_path / "observer-latency"),
            "--perturbation",
            "latency",
            "--latency-ms",
            "300",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["elapsed_ms"] >= 250.0


def test_g3_probe_subprocess_is_bounded_by_timeout(monkeypatch, tmp_path: Path) -> None:
    probe = _load_probe()

    def fake_run(*args, **kwargs):
        timeout = kwargs.get("timeout")
        assert timeout is not None and timeout > 0
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=timeout)

    monkeypatch.setattr(probe.subprocess, "run", fake_run)
    result = probe._worker(
        trace_path=tmp_path / "trace.json",
        observer_root=tmp_path / "observer",
        perturbation="normal",
        latency_ms=0,
    )
    assert result["worker_error_type"] == "VERIFICATION_WORKER_TIMEOUT"


def test_g3_probe_rejects_noop_perturbation_execution(
    monkeypatch,
    tmp_path: Path,
) -> None:
    probe = _load_probe()
    stable = {
        "activation_id": "stable-run",
        "decision": {"pipeline_action": "PROTOTIPAR"},
    }

    monkeypatch.setattr(probe, "_run_d", lambda _query: (stable, 1.0))

    def noop_worker(**kwargs):
        return {
            "worker_exit": 0,
            "perturbation": kwargs["perturbation"],
            "inserted_diagnostics": 0,
            "duplicate_diagnostics": 0,
            "failures": [],
            "elapsed_ms": 0.0,
            "verification_only": True,
            "standard_release_changed": False,
        }

    monkeypatch.setattr(probe, "_worker", noop_worker)
    output = tmp_path / "noop-report.json"
    monkeypatch.setattr(sys, "argv", [str(PROBE), "--output", str(output)])

    assert probe.main() == 2
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["probe_complete"] is False
    assert any(row["perturbation_ok"] is False for row in report["rows"])


def test_g3_probe_executes_every_local_perturbation_end_to_end(tmp_path: Path) -> None:
    output = tmp_path / "g3-report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(PROBE),
            "--iterations",
            "2",
            "--latency-ms",
            "20",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "NOT_VERIFIED"
    assert report["probe_complete"] is True
    assert len(report["rows"]) == 7
    assert all(row["perturbation_ok"] is True for row in report["rows"])
