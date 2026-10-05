"""Reproducible trace of the real CRIBA Shadow -> SUPRA journey.

This diagnostic harness drives the same callbacks as the visible UI, uses the
selected interpreter, the canonical SupraClient and a real SUPRA HTTP server.
Every boundary is recorded under one operation_id as ENTERED / RETURNED /
FAILED / NOT_REACHED, with payload type and size but without credentials or raw
model content.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any

TRACE: list[dict[str, Any]] = []
PROBLEM = "reducir el consumo de agua en el riego agricola sin perder rendimiento"
BOUNDARIES = (
    "UI_ACTION",
    "GENERATION_CALLBACK",
    "GENERATION_OUTPUT",
    "INTERPRETER_RAW",
    "PARSER_SCHEMA",
    "DOSSIER",
    "SUPRA_CLIENT_POST",
    "HTTP_RESPONSE",
    "PERSISTENCE",
    "GET_READBACK",
    "SHADOW_RENDER",
    "CLEAN_SHUTDOWN",
    "RESTART_PROCESS",
    "REOPEN_RELOAD",
    "SHADOW_RECOVERY",
)


def _size_of(value: Any) -> tuple[str, int]:
    try:
        raw = json.dumps(value, ensure_ascii=False, default=str).encode()
        return type(value).__name__, len(raw)
    except Exception:
        return type(value).__name__, 0


def _record(
    operation_id: str,
    boundary: str,
    state: str,
    *,
    payload: Any = None,
    detail: str = "",
    exception: str = "",
) -> None:
    payload_type, payload_size = _size_of(payload)
    event: dict[str, Any] = {
        "operation_id": operation_id,
        "boundary": boundary,
        "state": state,
        "payload_type": payload_type,
        "payload_size": payload_size,
        "detail": detail[:600],
    }
    if exception:
        event["exception"] = exception[-1800:]
    TRACE.append(event)
    print(
        f"[{operation_id}] {boundary:<24} {state:<12} "
        f"{payload_type:<18} size={payload_size} {detail[:120]}"
    )


def _entered(operation_id: str, boundary: str, detail: str = "") -> None:
    _record(operation_id, boundary, "ENTERED", detail=detail)


def _returned(
    operation_id: str,
    boundary: str,
    payload: Any = None,
    detail: str = "",
) -> None:
    _record(operation_id, boundary, "RETURNED", payload=payload, detail=detail)


def _failed(operation_id: str, boundary: str, exc: BaseException) -> None:
    _record(
        operation_id,
        boundary,
        "FAILED",
        detail=f"{type(exc).__name__}: {exc}",
        exception=traceback.format_exc(),
    )


def _mark_remaining_not_reached(operation_id: str, after: str, reason: str) -> None:
    start = BOUNDARIES.index(after) + 1
    already = {event["boundary"] for event in TRACE if event["operation_id"] == operation_id}
    for boundary in BOUNDARIES[start:]:
        if boundary not in already:
            _record(operation_id, boundary, "NOT_REACHED", detail=reason)


def _wait_for_workers(app: Any, win: Any, timeout_s: float, label: str) -> None:
    deadline = time.monotonic() + timeout_s
    while getattr(win, "_live_workers", []):
        app.processEvents()
        if time.monotonic() >= deadline:
            raise TimeoutError(f"{label}: workers siguen activos tras {timeout_s:.0f}s")
        time.sleep(0.05)
    app.processEvents()


def _first_problem() -> dict[str, Any] | None:
    for event in TRACE:
        if event["state"] in {"FAILED", "NOT_REACHED"}:
            return event
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print("uso: journey_harness.py <directorio-aislado>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    os.environ["CRIBASHADOW_HOME"] = str(root)
    # CRIBA_MODEL_CONFIG is a separate path and does not follow CRIBASHADOW_HOME.
    # Keep optional idea-generation models inside this isolated run instead of
    # loading the user's enabled GGUF profile from LOCALAPPDATA.
    os.environ["CRIBA_MODEL_CONFIG"] = str(root / "models.json")
    operation_id = uuid.uuid4().hex[:16]
    server = None
    win = None

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import criba_shadow_main as launcher

    launcher.wire_import_paths()
    trace_path = root / "harness_trace.json"

    try:
        import criba.ui.actions as actions
        from PySide6.QtWidgets import QApplication
        from shadow_window import ShadowWindow

        app = QApplication.instance() or QApplication(sys.argv)
        server = launcher.SupraServer(
            "http://127.0.0.1:8791",
            root / "supra_state",
            root / "logs" / "harness.log",
        )
        ok, endpoint = server.start(wait_s=90.0)
        if not ok:
            raise RuntimeError(endpoint)

        win = ShadowWindow(database=str(root / "criba.sqlite3"))
        win.show()
        app.processEvents()

        _entered(operation_id, "UI_ACTION", "Nueva idea -> problema del usuario")
        actions.on_nueva_idea_no_dialog(win, PROBLEM)
        assert win.problem == PROBLEM
        _returned(operation_id, "UI_ACTION", PROBLEM, "problema aplicado a Shadow")

        _entered(operation_id, "GENERATION_CALLBACK", "clic Generar ideas")
        actions.on_generar(win)
        _wait_for_workers(app, win, 180.0, "generación")
        _returned(
            operation_id,
            "GENERATION_CALLBACK",
            getattr(win, "packet", None),
            "callback y worker terminaron",
        )

        packet = getattr(win, "packet", None)
        _entered(operation_id, "GENERATION_OUTPUT")
        if not isinstance(packet, dict):
            raise RuntimeError("Generar no dejó packet dict")
        ideas = packet.get("innovation", {}).get("ideas", [])
        if not ideas:
            raise RuntimeError("Generar devolvió cero ideas")
        _returned(operation_id, "GENERATION_OUTPUT", ideas, f"ideas={len(ideas)}")

        _entered(operation_id, "INTERPRETER_RAW", "clic Inventar")
        actions.on_inventar(win)
        _wait_for_workers(app, win, 480.0, "interpretación")
        sheet = getattr(win, "invent_sheet", None)
        if not isinstance(sheet, dict):
            raise RuntimeError("Inventar terminó sin invent_sheet")
        raw_text = win.candidates.raw_output.toPlainText()
        entries = sheet.get("entries", [])
        raw_sizes = [len(str(item.get("interpretacion_raw_output") or "")) for item in entries]
        if not raw_text.strip() or not any(raw_sizes):
            raise RuntimeError("la salida bruta no llegó al panel visible")
        _returned(
            operation_id,
            "INTERPRETER_RAW",
            {"entry_count": len(entries), "raw_sizes": raw_sizes},
            f"provider={sheet.get('interpreter', {}).get('provider')} "
            f"model={sheet.get('interpreter', {}).get('model_requested')}",
        )

        _entered(operation_id, "PARSER_SCHEMA")
        proposals = [
            item
            for item in entries
            if item.get("estado_interpretacion") == "PROPUESTA"
            and str(item.get("mecanismo") or "").strip()
        ]
        if not proposals:
            reasons = sorted({str(item.get("interpretacion_error") or "") for item in entries})
            raise RuntimeError(f"cero propuestas válidas: {reasons}")
        interpreted_text = win.candidates.interpretation_output.toPlainText()
        first_title = str(entries[0].get("title") or "")
        expected_position = f"Interpretación 1 de {len(entries)}"
        if (
            not interpreted_text.strip()
            or sheet.get("query") != PROBLEM
            or first_title not in interpreted_text
            or win.candidates.interpreter_position.text() != expected_position
        ):
            raise RuntimeError("la interpretación visible no pertenece al run actual")
        _returned(
            operation_id,
            "PARSER_SCHEMA",
            proposals,
            f"propuestas_validas={len(proposals)}/{len(entries)}",
        )

        _entered(operation_id, "DOSSIER", "clic Desarrollar con SUPRA")
        actions.on_desarrollar_supra(win)
        dossier_text = win.candidates.dossier_output.toPlainText()
        if not dossier_text.strip():
            raise RuntimeError("el dossier no se renderizó antes del POST")
        dossiers = json.loads(dossier_text)
        _returned(operation_id, "DOSSIER", dossiers, f"dossiers={len(dossiers)}")

        _entered(operation_id, "SUPRA_CLIENT_POST")
        _wait_for_workers(app, win, 240.0, "SUPRA POST+GET")
        runs = sheet.get("supra_runs", [])
        if not runs:
            raise RuntimeError("SupraClient no dejó run tras el POST")
        _returned(
            operation_id,
            "SUPRA_CLIENT_POST",
            [{"project_id": run.get("project_id"), "status": run.get("status")} for run in runs],
            f"endpoint={endpoint}",
        )

        _entered(operation_id, "HTTP_RESPONSE")
        if any(not run.get("project_id") for run in runs):
            raise RuntimeError("respuesta SUPRA sin project_id")
        _returned(
            operation_id,
            "HTTP_RESPONSE",
            [run.get("read") for run in runs],
            "POST y respuesta contractual recibidos",
        )

        _entered(operation_id, "PERSISTENCE")
        project_ids = [str(run["project_id"]) for run in runs]
        artifacts = [root / "supra_state" / f"{project_id}.json" for project_id in project_ids]
        missing = [str(path) for path in artifacts if not path.is_file()]
        if missing:
            raise RuntimeError(f"artefactos SUPRA ausentes: {missing}")
        _returned(
            operation_id,
            "PERSISTENCE",
            [str(path) for path in artifacts],
            "artefactos persistidos en almacenamiento aislado",
        )

        _entered(operation_id, "GET_READBACK")
        reads = [run.get("read") for run in runs]
        if any(not isinstance(read, dict) for read in reads):
            raise RuntimeError("falta GET/readback en uno o más runs")
        _returned(
            operation_id,
            "GET_READBACK",
            reads,
            "; ".join(
                f"{read.get('status_source')}/{read.get('persisted_artifact_status')}"
                for read in reads
            ),
        )

        _entered(operation_id, "SHADOW_RENDER")
        supra_text = win.candidates.supra_output.toPlainText()
        if not supra_text.strip():
            raise RuntimeError("el GET no se representó en Shadow")
        for project_id in project_ids:
            if project_id not in supra_text:
                raise RuntimeError(f"Shadow no muestra project_id {project_id}")
        _returned(
            operation_id,
            "SHADOW_RENDER",
            {
                "raw_chars": len(raw_text),
                "interpreted_chars": len(interpreted_text),
                "dossier_chars": len(dossier_text),
                "supra_chars": len(supra_text),
            },
            "los cuatro paneles pertenecen a la operación actual",
        )

        _entered(operation_id, "CLEAN_SHUTDOWN")
        win.close()
        app.processEvents()
        server.stop()
        server = None
        _returned(operation_id, "CLEAN_SHUTDOWN", detail="ventana y SUPRA detenidos")

        _entered(operation_id, "RESTART_PROCESS", "nuevo proceso SUPRA sobre el mismo storage")
        server = launcher.SupraServer(
            endpoint,
            root / "supra_state",
            root / "logs" / "harness-restart.log",
        )
        ok, restarted_endpoint = server.start(wait_s=90.0)
        if not ok:
            raise RuntimeError(restarted_endpoint)
        _returned(
            operation_id,
            "RESTART_PROCESS",
            {"endpoint_before": endpoint, "endpoint_after": restarted_endpoint},
            "proceso nuevo arrancado con storage durable existente",
        )

        _entered(operation_id, "REOPEN_RELOAD", "nueva ventana y recuperación por LIST+GET")
        win = ShadowWindow(database=str(root / "criba.sqlite3"))
        win.show()
        app.processEvents()
        report = actions._load_latest_supra()
        if report.get("empty"):
            raise RuntimeError("tras restart no hay proyecto persistido que recuperar")
        recovered_id = str(report.get("project_id") or "")
        if recovered_id not in project_ids:
            raise RuntimeError(
                f"restart recuperó un project_id ajeno al run: {recovered_id}"
            )
        initial_read = next(
            run["read"] for run in runs if str(run["project_id"]) == recovered_id
        )
        recovered_read = report.get("read") or {}
        for key in (
            "status",
            "status_scope",
            "completion_status",
            "workflow_status",
            "verification_status",
            "scientific_status",
            "criba_planning_receipt_status",
            "criba_mechanism_execution_status",
            "stage",
        ):
            if recovered_read.get(key) != initial_read.get(key):
                raise RuntimeError(
                    f"restart alteró {key}: "
                    f"antes={initial_read.get(key)!r} después={recovered_read.get(key)!r}"
                )
        initial_receipt = initial_read.get("receipt") or {}
        recovered_receipt = recovered_read.get("receipt") or {}
        for key in (
            "candidate_id",
            "claim_id",
            "mechanism_version",
            "protocol_version",
            "execution_id",
        ):
            if key in initial_receipt and recovered_receipt.get(key) != initial_receipt.get(key):
                raise RuntimeError(
                    f"restart alteró identidad {key}: "
                    f"antes={initial_receipt.get(key)!r} después={recovered_receipt.get(key)!r}"
                )
        _returned(
            operation_id,
            "REOPEN_RELOAD",
            report,
            f"project_id={recovered_id} source={recovered_read.get('status_source')} "
            f"artifact={recovered_read.get('persisted_artifact_status')}",
        )

        _entered(operation_id, "SHADOW_RECOVERY")
        actions._on_supra_restore_done(win, report)
        recovered_text = win.candidates.supra_output.toPlainText()
        if not recovered_text.strip() or recovered_id not in recovered_text:
            raise RuntimeError("Shadow no mostró la verdad recuperada tras restart")
        _returned(
            operation_id,
            "SHADOW_RECOVERY",
            {
                "project_id": recovered_id,
                "supra_chars": len(recovered_text),
                "status": recovered_read.get("status"),
                "status_source": recovered_read.get("status_source"),
                "persisted_artifact_status": recovered_read.get(
                    "persisted_artifact_status"
                ),
            },
            "reopen/reload mostró GET durable en Shadow",
        )

        _entered(operation_id, "CLEAN_SHUTDOWN")
        win.close()
        app.processEvents()
        server.stop()
        server = None
        _returned(operation_id, "CLEAN_SHUTDOWN", detail="ventana y SUPRA detenidos")
    except Exception as exc:  # noqa: BLE001 - el arnés registra el borde exacto
        active = next(
            (
                event["boundary"]
                for event in reversed(TRACE)
                if event["operation_id"] == operation_id and event["state"] == "ENTERED"
            ),
            "UI_ACTION",
        )
        _failed(operation_id, active, exc)
        _mark_remaining_not_reached(operation_id, active, str(exc))
    finally:
        if win is not None:
            try:
                win.close()
            except Exception:
                pass
        if server is not None:
            server.stop()
        trace_path.write_text(
            json.dumps(TRACE, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    problem = _first_problem()
    print(f"TRAZA={trace_path}")
    print(f"OPERATION_ID={operation_id}")
    if problem:
        print(
            "PRIMER_BORDE_PROBLEMATICO="
            f"{problem['boundary']}:{problem['state']}:{problem['detail']}"
        )
        return 1
    print("PRIMER_BORDE_PROBLEMATICO=ninguno")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
