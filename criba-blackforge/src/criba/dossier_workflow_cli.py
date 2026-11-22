"""CLI surface of the shared product workflow; no implicit model use/autostart."""
from __future__ import annotations

import argparse
import hashlib
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



def _send_one_journal_bound(
    workflow: DossierWorkflow, args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """One explicitly authorized FIRST CLI dispatch, never a blind retry.

    CLI does not have the atomic batch-orchestration capability to submit a
    multi-dossier batch. Do not reserve part of that batch: that would make
    all remaining originals permanently unsendable. Reject standalone drafts
    rather than constructing a new run identity for a repeat POST.
    """
    from . import dossier_batch as journal
    from .dossier_batch_recovery import reconciliar_lote_por_get

    dossier = workflow.load_local(args.dossier_id)
    run_id, problem = dossier.get("run_id"), dossier.get("problema")
    if not journal._exact(run_id) or not journal._exact(problem):
        raise WorkflowError(
            "CLI_JOURNAL_LINEAGE_REQUIRED", "preflight",
            "CLI send exige run_id y problema exactos en un PREPARED original.",
        )
    found = journal.buscar_lote_por_sesion(run_id, problem)
    if (found is None or not found["committed"]
            or found["dossiers"] != [args.dossier_id]):
        raise WorkflowError(
            "CLI_SINGLE_BATCH_REQUIRED", "preflight",
            "CLI send solo admite un PREPARED committed de un dossier; "
            "para lotes múltiples usar Shadow y recuperar por GET.",
        )
    if found["remote_state"] != "NOT_ATTEMPTED":
        raise WorkflowError(
            "CLI_REMOTE_ALREADY_RESERVED", "preflight",
            "Lote reservado previamente: no repetir POST; recuperar por GET.",
            remote_unknown=found["remote_state"] != "READBACK_OBSERVED",
        )
    if not args.confirm_first_send:
        raise WorkflowError(
            "CLI_CONFIRMATION_REQUIRED", "preflight",
            "Repetir con --confirm-first-send para autorizar su primer POST.",
        )
    expected_project = (
        "astram2-" + hashlib.sha256(
            args.dossier_id.encode("utf-8")
        ).hexdigest()[:32]
    )
    if args.project_id is not None and args.project_id != expected_project:
        raise WorkflowError(
            "CLI_PROJECT_ID_MISMATCH", "preflight",
            "El project_id debe ser el ID determinista del dossier original.",
        )
    # The caller cannot choose a new mutable POST payload or a new identity.
    client = workflow.http()
    origin = journal._endpoint_identity(client.config.endpoint)
    try:
        reservation = journal.reservar_primer_envio_preparado(
            found["batch_id"], run_id, problem, endpoint=origin,
        )
    except (ValueError, OSError) as exc:
        # Another process may already have reserved the batch. Caller cannot
        # use a stale preflight to justify POST or a new identity.
        raise WorkflowError(
            "CLI_FIRST_RESERVATION_REJECTED", "reserve",
            "Reserva original no confirmada; comprobar journal y usar GET.",
            remote_unknown=True,
        ) from exc
    payloads = reservation["dossiers"]
    if len(payloads) != 1 or payloads[0]["dossier_id"] != args.dossier_id:
        raise WorkflowError(
            "CLI_JOURNAL_CHANGED", "reserve",
            "La reserva no coincide con el dossier original; GET-only.",
            remote_unknown=True,
        )
    # Marker persists before even health. A crash here leaves UNKNOWN,
    # never NOT_ATTEMPTED and never authorizes an automatic POST retry.
    try:
        original_payloads = journal.reclamar_inicio_envio_remoto(
            reservation["batch_id"], payloads, endpoint=origin,
        )
    except (ValueError, OSError) as exc:
        raise WorkflowError(
            "CLI_DISPATCH_CLAIM_UNCONFIRMED", "dispatch",
            "El lote permanece UNKNOWN; no repetir POST, consultar por GET.",
            remote_unknown=True,
        ) from exc
    if len(original_payloads) != 1:
        raise WorkflowError(
            "CLI_JOURNAL_CHANGED", "dispatch",
            "La reclamación no conserva el lote original.",
            remote_unknown=True,
        )
    try:
        result = workflow.submit(
            original_payloads[0], expected_project,
            use_model=args.use_model, provider=args.provider, model=args.model,
            domain=args.domain, allow_disruptive=not args.no_disruptive,
            expected_endpoint=origin,
            batch_dispatch_id=reservation["batch_id"],
        )
    except WorkflowError as exc:
        # A worker acquired its durable claim; even a local validation failure
        # cannot make that same batch safely POSTable again.
        exc.remote_unknown = True
        exc.retryable = False
        raise
    except Exception as exc:
        raise WorkflowError(
            "CLI_POST_OUTCOME_UNKNOWN", "send",
            "Envío reclamado: no reintentar; recuperar exclusivamente por GET.",
            remote_unknown=True,
        ) from exc
    # Successful POST and workflow-local GET are insufficient to declare a
    # journaled receipt. Reconcile through independent strict v2 GET checks.
    try:
        verified = reconciliar_lote_por_get(
            reservation["batch_id"], client, registrar=True,
            expected_run_id=run_id, expected_problem=problem,
        )
    except Exception:
        return ({
            "operation_status": "REMOTE_UNKNOWN_READBACK_UNCONFIRMED",
            "batch_id": reservation["batch_id"], "project_id": expected_project,
            "remote_outcome_unknown": True, "authorizes_retry": False,
            "scientific_status": "NOT_VALIDATED",
            "mechanism_execution": "NOT_EXECUTED",
        }, 2)
    if (verified.get("status") != "READBACK_OBSERVED"
            or verified.get("fresh_get_status") != "VERIFIED_FROM_ARTIFACT"
            or verified.get("journal_recorded") is not True):
        return ({
            "operation_status": "REMOTE_UNKNOWN_READBACK_UNCONFIRMED",
            "batch_id": reservation["batch_id"], "project_id": expected_project,
            "remote_outcome_unknown": True, "authorizes_retry": False,
            "scientific_status": "NOT_VALIDATED",
            "mechanism_execution": "NOT_EXECUTED",
        }, 2)
    report = result.report()
    report.update({
        "operation_status": "PLANNING_RECEIPT_JOURNALED_ONLY",
        "batch_id": reservation["batch_id"], "remote_outcome_unknown": False,
        "authorizes_retry": False,
        "scientific_status": "NOT_VALIDATED",
        "mechanism_execution": "NOT_EXECUTED",
    })
    return report, 0


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
    send.add_argument(
        "--confirm-first-send", action="store_true",
        help="Autoriza EXCLUSIVAMENTE el primer POST de un lote local de un dossier.",
    )
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
                result, return_code = _send_one_journal_bound(workflow, args)
            elif args.command == "recover":
                result = (workflow.recover_latest() if args.latest else workflow.recover(args.project_id)).report()
            elif args.command == "export":
                result = workflow.export_bundle(args.project_id)
            else:
                result = workflow.import_bundle(read_object(args.file))
            emit(result, args.output)
        return return_code if args.command == "send" else 0
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
