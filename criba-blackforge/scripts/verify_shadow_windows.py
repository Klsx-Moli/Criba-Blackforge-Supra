"""Isolated *real Windows executable* startup smoke; no GUI acceptance claim.

Run on a Windows desktop after building the onedir bundle:
    python scripts/verify_shadow_windows.py dist/CribaShadow/CribaShadow.exe

This never touches the user's normal database, never starts BLACKFORGE, and
does not call an LLM. Qt's isVisible flag is NOT proof a human saw a window.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


def assess_startup_trace(lines: list[str], process_alive: bool) -> dict[str, Any]:
    """Fail closed if startup, backend, window or restore did not all run."""
    backend = "supra:ready" in lines
    opened = "qt:window-created" in lines
    shown = any(
        row.startswith("qt:window-shown visible=True") and "minimized=False" in row
        for row in lines
    )
    restored = "qt:restore-started" in lines
    ready = bool(process_alive and backend and opened and shown and restored)
    return {
        "status": "STARTUP_SMOKE_PASS" if ready else "STARTUP_SMOKE_FAIL",
        "backend_ready_observed": backend,
        "qt_window_created_observed": opened,
        "qt_visible_flag_observed": shown,
        "restore_started_observed": restored,
        "process_alive_observed": bool(process_alive),
        "desktop_visual_acceptance": "NOT_VERIFIED",
        "exe_functional_end_to_end_acceptance": "NOT_VERIFIED",
    }


def smoke(exe: Path, *, timeout_s: float = 90.0) -> dict[str, Any]:
    if os.name != "nt":
        raise ValueError("Windows desktop executable smoke requires Windows")
    if not exe.is_file() or exe.suffix.lower() != ".exe":
        raise ValueError(f"CribaShadow.exe not found: {exe}")
    if exe.name.lower() != "cribashadow.exe":
        raise ValueError("Only the canonical CribaShadow.exe can be tested")

    with tempfile.TemporaryDirectory(prefix="criba-shadow-release-") as base:
        home = Path(base) / "isolated-state"
        trace = home / "logs" / "launcher-startup.log"
        environment = os.environ.copy()
        environment["CRIBASHADOW_HOME"] = str(home)
        environment.pop("SUPRA_ENDPOINT", None)
        environment.pop("QT_QPA_PLATFORM", None)
        process = subprocess.Popen([str(exe.resolve())], cwd=str(exe.parent.resolve()), env=environment)
        try:
            deadline = time.monotonic() + timeout_s
            lines: list[str] = []
            while time.monotonic() < deadline and process.poll() is None:
                if trace.is_file():
                    lines = trace.read_text(encoding="utf-8", errors="replace").splitlines()
                    report = assess_startup_trace(lines, process_alive=True)
                    if report["status"] == "STARTUP_SMOKE_PASS":
                        # The process must still survive after the initial startup.
                        time.sleep(1.0)
                        report = assess_startup_trace(lines, process_alive=process.poll() is None)
                        break
                time.sleep(0.25)
            else:
                report = assess_startup_trace(lines, process_alive=process.poll() is None)
            report["process_exit_code_before_cleanup"] = process.poll()
            report["trace"] = lines[-25:]
            report["isolated_state_used"] = True
            return report
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if not (1 <= args.timeout <= 300):
            raise ValueError("timeout must be 1..300 seconds")
        report = smoke(args.exe, timeout_s=args.timeout)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        report = {"status": "STARTUP_SMOKE_FAIL", "error": str(exc),
                  "desktop_visual_acceptance": "NOT_VERIFIED"}
    formatted = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(formatted, encoding="utf-8")
    else:
        print(formatted, end="")
    return 0 if report["status"] == "STARTUP_SMOKE_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
