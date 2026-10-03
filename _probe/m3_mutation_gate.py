"""Mutation gate for the M3 provenance contract.

Reverts each part of the fix in memory, one at a time, and reports which tests
go red. A sentinel that cannot fail protects nothing, so this is measured,
not asserted.

Run:  python _probe/m3_mutation_gate.py
Exit != 0 if any mutation survived.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUPRA = REPO / "supra"
STATE = SUPRA / "src" / "supra_agentic" / "state.py"
SERVICE = SUPRA / "src" / "supra_agentic" / "service.py"
TESTS = [
    "tests/test_m3_restart_provenance_contract.py",
    "tests/test_b03_replay_restart_contract.py",
    "tests/astra_canon/test_state_corruption.py",
    "tests/test_state.py",
]
PYTHON = SUPRA / ".venv" / "Scripts" / "python.exe"

MUTATIONS: list[tuple[str, Path, str, str]] = [
    (
        "M1 · read path vuelve a hardcodear PERSISTED_STATE",
        SERVICE,
        '"status_source": source,',
        '"status_source": "PERSISTED_STATE",',
    ),
    (
        "M2 · el veredicto del artefacto se borra del read path",
        SERVICE,
        '"persisted_artifact_status": artifact_status,',
        '"persisted_artifact_status": "MATCHES_CACHE",',
    ),
    (
        "M3 · el listado vuelve a saltarse los artefactos ya cacheados",
        STATE,
        "                cached = self._projects.get(pid)\n"
        "                if cached is not None:",
        "                cached = self._projects.get(pid)\n"
        "                if False:",
    ),
]


def run_suite() -> tuple[int, str]:
    proc = subprocess.run(
        [str(PYTHON), "-m", "pytest", *TESTS, "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=str(SUPRA),
        capture_output=True,
        text=True,
        timeout=900,
    )
    return proc.returncode, proc.stdout + proc.stderr


def failed_count(output: str) -> int:
    for line in output.splitlines():
        if " failed" in line and ("passed" in line or "error" in line):
            for token in line.replace(",", " ").split():
                if token.isdigit():
                    head = output.splitlines()
                    idx = head.index(line) if line in head else -1
                    if idx > 0 and "failed" in head[idx - 1]:
                        return int(token)
    return 0


def main() -> int:
    print("baseline (sin mutación):", flush=True)
    code, out = run_suite()
    print("  exit", code, "·", out.strip().splitlines()[-1] if out.strip() else "", flush=True)
    if code != 0:
        print("FALLO: la suite no está verde de partida; la mutación no significaría nada")
        return 2

    survivors: list[str] = []
    for label, target, old, new in MUTATIONS:
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak")
        backup.close()
        shutil.copy2(target, backup.name)
        try:
            text = target.read_text(encoding="utf-8")
            assert old in text, f"ancla no encontrada para {label}: {old!r}"
            target.write_text(text.replace(old, new, 1), encoding="utf-8")
            code, out = run_suite()
            red = code != 0
            print(f"\n{label}", flush=True)
            print("  tests rojos" if red else "  NADIE SE PUDO", flush=True)
            if red:
                for line in out.splitlines():
                    if line.startswith("FAILED") or " failed" in line:
                        print("   ", line.strip(), flush=True)
                        break
            else:
                survivors.append(label)
        finally:
            shutil.copy2(backup.name, target)
            Path(backup.name).unlink(missing_ok=True)

    code, out = run_suite()
    print("\nrestaurado: exit", code, "·", out.strip().splitlines()[-1] if out.strip() else "")
    if survivors:
        print("\nMUTACIONES QUE SOBREVIVIERON (el sentinel no protege):")
        for item in survivors:
            print("  -", item)
        return 1
    print("\nGATE DE MUTACIÓN CERRADO: cada mutación fue detectada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())