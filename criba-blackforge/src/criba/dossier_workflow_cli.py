"""CLI surface of the shared product workflow; no implicit model use/autostart."""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from .dossier_workflow import DossierWorkflow, WorkflowError


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Se requiere objeto JSON.")
    return value


def emit(value: dict[str, Any], output: Path | None = None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if output is None:
        print(text, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            handle.write(text)


def make_workflow(endpoint: str | None) -> DossierWorkflow:
    def factory() -> Any:
        from .integrations.supra_client import SupraClient, SupraClientConfig
        config = SupraClientConfig.from_env()
        return SupraClient(replace(config, endpoint=endpoint) if endpoint else config)
    return DossierWorkflow(client_factory=factory)


def main(argv: Sequence[str] | None = None, *,
         workflow_factory: Callable[[str | None], DossierWorkflow] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="criba dossier")
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--home", type=Path, default=None)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--entry", type=Path, required=True)
    prepare.add_argument("--problem", required=True)
    send = commands.add_parser("send")
    send.add_argument("--dossier-id", required=True)
    send.add_argument("--project-id", default=None)
    send.add_argument("--use-model", action="store_true", help="Opt-in con autorización de coste/scope")
    send.add_argument("--provider", default=None)
    send.add_argument("--model", default=None)
    send.add_argument("--domain", default="criba_blackforge")
    send.add_argument("--no-disruptive", action="store_true")
    recover = commands.add_parser("recover")
    choose = recover.add_mutually_exclusive_group(required=True)
    choose.add_argument("--project-id")
    choose.add_argument("--latest", action="store_true")
    export = commands.add_parser("export")
    export.add_argument("--project-id", required=True)
    importing = commands.add_parser("import")
    importing.add_argument("--file", type=Path, required=True)
    for command in [prepare, send, recover, export, importing]:
        command.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.output and args.output.exists():
        print("Salida existente: no se sobrescribe.", file=sys.stderr)
        return 2
    old_home = os.environ.get("CRIBASHADOW_HOME")
    if args.home is not None:
        os.environ["CRIBASHADOW_HOME"] = str(args.home)
    try:
        with (workflow_factory or make_workflow)(args.endpoint) as workflow:
            if args.command == "prepare":
                result = workflow.prepare(read_object(args.entry), args.problem)
            elif args.command == "send":
                result = workflow.submit(workflow.load_local(args.dossier_id), args.project_id,
                    use_model=args.use_model, provider=args.provider, model=args.model,
                    domain=args.domain, allow_disruptive=not args.no_disruptive).report()
                result["operation_status"] = "CONFIRMED_PLANNING_DELIVERY"
            elif args.command == "recover":
                result = (workflow.recover_latest() if args.latest else workflow.recover(args.project_id)).report()
            elif args.command == "export":
                result = workflow.export_bundle(args.project_id)
            else:
                result = workflow.import_bundle(read_object(args.file))
            emit(result, args.output)
        return 0
    except WorkflowError as exc:
        emit({"operation_status": "WORKFLOW_ERROR", "error": exc.to_dict()}, args.output)
        return 2
    except (OSError, ValueError) as exc:
        emit({"operation_status": "INPUT_OR_IO_ERROR", "error_type": type(exc).__name__})
        return 2
    finally:
        if args.home is not None:
            if old_home is None:
                os.environ.pop("CRIBASHADOW_HOME", None)
            else:
                os.environ["CRIBASHADOW_HOME"] = old_home


if __name__ == "__main__":
    raise SystemExit(main())
