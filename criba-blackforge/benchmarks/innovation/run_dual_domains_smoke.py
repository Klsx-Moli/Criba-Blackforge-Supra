"""Smoke offline dual-domain: CRIBA + BLACKFORGE reales, sin modelo/red.

Este runner NO concluye superioridad (§48/§53). Genera evidencia funcional:
- C_CRIBA usa el pipeline interpretado compartido (lotería + selector).
- D_BLACKFORGE usa la lotería + selector sobre su catálogo real.
- A/B_DIRECT usan un stub determinista para validar schema/métricas.
Ejecución:
    .venv\\Scripts\\python.exe benchmarks/innovation/run_dual_domains_smoke.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from benchmarks.innovation.blackforge_adapter import blackforge_fn  # noqa: E402
from benchmarks.innovation.criba_adapter import run_criba_selection  # noqa: E402
from benchmarks.innovation.harness import exportar, run_smoke  # noqa: E402


def _direct_stub(prompt: str, seed: int | None = None) -> list[dict[str, Any]]:
    """Stub determinista: solo valida el schema, nunca simula un modelo."""
    del seed
    text = prompt.split(":", 1)[-1].strip()
    return [
        {
            "idea_id": f"direct-{index:02d}",
            "title": f"Respuesta directa stub {index + 1}",
            "description": f"Stub para {text[:80]}",
            "score": 0.5,
            "family": "direct_stub",
            "methods": ["direct_prompt"],
            "classes": ["stub"],
            "genome": {"mechanism": ["stub"], "classes": ["stub"]},
        }
        for index in range(3)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    default_out = ROOT / "benchmarks" / "innovation" / "smoke_dual_domains.json"
    parser.add_argument("--out", default=str(default_out))
    args = parser.parse_args()

    def criba_with_report(problem: str, seed: int, n: int) -> Any:
        return run_criba_selection(problem, seed, n)

    report = run_smoke(
        _direct_stub,
        seed=7,
        criba_fn=criba_with_report,
        blackforge_fn=blackforge_fn,
    )
    out = Path(args.out)
    exportar(report, out)
    summary = {
        "n_problemas": report["n_problemas"],
        "conditions": report["conditions"],
        "runs": len(report["runs"]),
        "status_counts": {
            status: sum(1 for run in report["runs"] if run["status"] == status)
            for status in {"OK", "UNAVAILABLE"}
        },
        "criba_ok": sum(
            1 for run in report["runs"] if run["condition"] == "C_CRIBA" and run["status"] == "OK"
        ),
        "blackforge_ok": sum(
            1
            for run in report["runs"]
            if run["condition"] == "D_BLACKFORGE" and run["status"] == "OK"
        ),
        "direct_ok": sum(
            1 for run in report["runs"] if run["condition"] == "A_DIRECT" and run["status"] == "OK"
        ),
        "strong_ok": sum(
            1
            for run in report["runs"]
            if run["condition"] == "B_STRONG_PROMPT" and run["status"] == "OK"
        ),
        "advertencia": report["advertencia"],
        "output": str(out),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
