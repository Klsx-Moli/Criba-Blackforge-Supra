"""Runtime status or fixed-bank evaluation; never substitutes synthetic responses."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from criba.interprete.banco import evaluar_banco  # noqa: E402
from criba.interprete.seleccion import construir_interprete, estado_interprete  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend", choices=["openai_compatible", "local_llama"], default="openai_compatible"
    )
    parser.add_argument(
        "--evaluate", action="store_true", help="evaluar el banco con llamadas reales"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    interpreter = construir_interprete(args.backend)
    report = estado_interprete(interpreter)
    if args.evaluate and report["conectado"]:
        report["bank"] = report.get("admission_report") or evaluar_banco(interpreter.proponer)
    raw = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw + "\n", encoding="utf-8")
    print(raw)
    return 0 if report["conectado"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
