"""Run a two-process *packaged EXE* GUI->CRIBA->SUPRA->disk->restore acceptance.

Automation operates only on TemporaryDirectory; screenshots come from Qt's
paint buffer and are not evidence of a human-visible interactive desktop.
The frozen application is not modified or mocked during either phase.

Windows: python scripts/verify_shadow_bundle_journey.py dist/CribaShadow/CribaShadow.exe \
    --artifacts bundle-verification
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

PHASES = {"journey": "BUNDLED_JOURNEY_PASS", "restore": "BUNDLED_RESTORE_PASS"}


def summarize(journey: dict[str, Any], restore: dict[str, Any]) -> dict[str, Any]:
    """Do not promote a success if identity, evidence or either phase is absent."""
    identity = (
        journey.get("project_id") and journey.get("project_id") == restore.get("project_id")
    )
    success = bool(
        journey.get("status") == PHASES["journey"]
        and restore.get("status") == PHASES["restore"]
        and identity
        and journey.get("http_get_status") == restore.get("http_get_status") == 200
        and journey.get("artifact_exists") is True
        and restore.get("artifact_exists") is True
        and journey.get("receipt_execution_status") == restore.get("receipt_execution_status") == "NOT_EXECUTED"
        and journey.get("receipt_scientific_status") == restore.get("receipt_scientific_status") == "NOT_VALIDATED"
        and all(
            item.get(f"image_{key}", {}).get("sampled_distinct_colors", 0) >= 14
            for item, key in (
                (journey, "initial"), (journey, "generated"), (journey, "supra"),
                (restore, "initial"), (restore, "restored")
            )
        )
    )
    return {
        "status": "BUNDLED_E2E_PASS" if success else "BUNDLED_E2E_FAIL",
        "bundle_real_qt_callbacks": bool(success),
        "real_supra_http_readback": bool(success),
        "durable_state_restored_after_full_process_restart": bool(success),
        "project_id": journey.get("project_id") if identity else None,
        "screenshots_source": "QWidget.grab() paint buffer",
        "desktop_human_visual_review": "NOT_VERIFIED",
        "external_llm_baseline": "NOT_EXECUTED",
        "scientific_advantage": "NOT_ESTABLISHED",
        "journey": journey,
        "restore": restore,
    }


def _launch(exe: Path, home: Path, mode: str, *, expected: str = "", timeout_s: float = 185.0) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["CRIBASHADOW_HOME"] = str(home)
    environment["CRIBA_MODEL_CONFIG"] = str(home / "models.json")
    environment["CRIBASHADOW_BUNDLE_PROBE"] = mode
    environment["CRIBASHADOW_EXPECTED_PROJECT_ID"] = expected
    environment.pop("SUPRA_ENDPOINT", None)
    environment.pop("QT_QPA_PLATFORM", None)
    report_path = home / "bundle-verification" / f"{mode}-report.json"
    process = subprocess.Popen(
        [str(exe.resolve())], cwd=str(exe.parent.resolve()), env=environment,
    )
    try:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            exited = process.poll()
            if exited is not None:
                if report_path.is_file():
                    report = json.loads(report_path.read_text(encoding="utf-8"))
                    report["actual_exit_code"] = exited
                    if exited != 0:
                        report["status"] = "BUNDLED_JOURNEY_FAIL"
                    return report
                raise RuntimeError(f"{mode}: EXE exited {exited} without producing a bundle probe report")
            time.sleep(0.3)
        raise TimeoutError(f"{mode}: EXE exceeded {timeout_s}s")
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=12)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--artifacts", type=Path, default=Path("bundle-verification"))
    args = parser.parse_args(argv)
    result: dict[str, Any] = {
        "status": "BUNDLED_E2E_FAIL", "desktop_human_visual_review": "NOT_VERIFIED",
    }
    try:
        if os.name != "nt":
            raise RuntimeError("EXE end-to-end acceptance requires Windows")
        if args.exe.name.lower() != "cribashadow.exe" or not args.exe.is_file():
            raise RuntimeError("Expected a built CribaShadow.exe file")
        with tempfile.TemporaryDirectory(prefix="criba-shadow-release-") as temp:
            home = Path(temp) / "isolated-state"
            journey = _launch(args.exe, home, "journey")
            if journey.get("status") == "BUNDLED_JOURNEY_PASS":
                restore = _launch(args.exe, home, "restore", expected=journey["project_id"])
                result = summarize(journey, restore)
            else:
                result = {"status": "BUNDLED_E2E_FAIL", "journey": journey,
                          "restore": {"status": "NOT_EXECUTED"},
                          "desktop_human_visual_review": "NOT_VERIFIED"}
            source = home / "bundle-verification"
            args.artifacts.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                for path in source.iterdir():
                    if path.is_file() and path.suffix.lower() in {".png", ".json"}:
                        shutil.copy2(path, args.artifacts / path.name)
    except (RuntimeError, ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    args.artifacts.mkdir(parents=True, exist_ok=True)
    (args.artifacts / "bundle-e2e-result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        k: value for k, value in result.items() if k not in {"journey", "restore"}
    }, ensure_ascii=False))
    return 0 if result["status"] == "BUNDLED_E2E_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
