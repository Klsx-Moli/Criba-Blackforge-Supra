"""CB-03: Journey E2E sin modelo (Shadow -> CRIBA -> dossier -> SUPRA -> disco
-> GET/LIST -> Shadow -> reinicio -> recuperación).

ARNÉS DETERMINISTA, SIN LLM. No invoca ningún proveedor real: el intérprete es
sintético (cumple el mismo InterpreterPort y devuelve InterpretationResult reales
con estado PROPUESTA/ABSTENCIÓN). El servidor SUPRA es el real del launcher
(criba_shadow_main.SupraServer) sobre almacenamiento aislado temporal. El resto
del recorrido —Shadow, actions, inventar, dossier, SupraClient, storage— es la
ruta de producción, sin bypass.

Cada frontera se registra como ENTERED/RETURNED/FAILED/NOT_REACHED con tipo y
tamaño de payload (sin credenciales ni contenido crudo del modelo). Al terminar
imprime el PRIMER borde roto, o "ninguno" si todos pasan.

Uso:
    python verification/journey_e2e_no_model.py <directorio-aislado>

Salida: JSON de traza en <dir>/journey_trace.json. Exit 0 = GREEN, 1 = RED
(con PRIMER_BORDE_PROBLEMATICO), 2 = uso incorrecto.
"""

from __future__ import annotations

import json
import os
import subprocess
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
    operation_id: str, boundary: str, payload: Any = None, detail: str = ""
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


def _normalizar_native(path: Path) -> Path:
    """Convierte una ruta MSYS '/c/...' en la forma nativa 'C:/...'.

    Path.resolve() en Python nativo transforma '/c/Users/x' en 'C:\\c\\Users\\x'
    (una ruta inexistente), mientras os.path.isdir('/c/...') devuelve True. Esa
    asimetría hace que un artefacto escrito por el proceso "exista" para él y
    desaparezca para cualquier otro lector. Este helper elimina la ambigüedad
    antes de que la ruta se propague a variables de entorno y a la escritura.
    """
    s = str(path)
    if len(s) >= 3 and s[0] == "/" and s[2] == "/" and s[1].isalpha():
        drive = s[1].upper()
        return Path(f"{drive}:/{s[3:]}")
    return path


def _build_fake_interpreter_module(tmp_dir: Path) -> str:
    """Crea un módulo intérprete sintético determinista en el dir aislado."""
    mod_path = tmp_dir / "_fake_interpreter.py"
    mod_path.write_text(
        '''"""Intérprete sintético determinista para el journey E2E sin modelo."""
from __future__ import annotations

import hashlib
import json
import sys
import time

from criba.interprete.puerto import (
    InterpretationResult,
    Provenance,
    ESTADO_PROPUESTA,
    ESTADO_PENDIENTE,
)


def _sha(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _provenance() -> Provenance:
    return Provenance(
        interpreter_backend="e2e_determinista",
        provider="sintetico_sin_red",
        model_requested="e2e-deterministico-v1",
        model_reported="e2e-deterministico-v1",
        endpoint="http://127.0.0.1:0/v1",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z",
        duration_ms=0,
        prompt_version="e2e-v1",
        schema_version="propuesta-1",
        request_id="e2e-" + uuid_hex()[:16],
        fallback_used=False,
        raw_output_sha256="",
    )


def uuid_hex() -> str:
    import uuid
    return uuid.uuid4().hex


def _critica() -> dict:
    return {
        "pertinente": True,
        "mecanismo_especifico": True,
        "falsable": True,
        "fiel_evidencia": True,
        "restricciones_respetadas": True,
        "discrimina_alternativas": True,
        "intercambio_tecnicas_generico": False,
        "objeciones": [],
        "incertidumbre": "Critica sintetica; no es validacion experimental.",
        "respuestas_epistemologicas": {
            f"Q{i}": "Eje no demostrado experimentalmente; requiere verificacion."
            for i in range(1, 12)
        },
    }


def _prueba() -> dict:
    return {
        "metrica": "porcentaje de citas con retorno",
        "baseline": "cien citas sin comprobacion previa",
        "umbral": "al menos 10 puntos porcentuales menos de retornos",
        "condicion_fracaso": "reduccion inferior a 10 puntos porcentuales",
        "alternativa_explicativa": "Los retornos dependen de disponibilidad.",
        "resultado_favorable_mecanismo": "Retornos bajan >=10 puntos.",
        "resultado_favorable_alternativa": "Retornos no bajan.",
    }


class InterpreteSintetico:
    backend = "e2e_determinista"
    provider = "sintetico_sin_red"
    model = "e2e-deterministico-v1"

    def __init__(self) -> None:
        self.calls = 0

    def operativo(self) -> tuple[bool, str]:
        return True, "interprete sintetico determinista (sin red)"

    def proponer(self, query, idea, domain=None, evidence=None):
        self.calls += 1
        n = self.calls
        # Primer candidato -> PROPUESTA válida; segundo -> abstención honesta
        # (no es ERROR: demuestra que ABSTENER correcto se distingue).
        if n == 2:
            motivo = "Sin mecanismo defendible para este candidato; se abstiene."
            result = InterpretationResult(
                estado=ESTADO_PENDIENTE,
                error=motivo,
                provenance=_provenance(),
                raw_output=json.dumps({"abstencion": motivo}),
                finish_reason="stop",
            )
            result.provenance = Provenance(
                **{**result.provenance.as_dict(),
                   "raw_output_sha256": _sha(result.raw_output)}
            )
            return result
        hipotesis = f"Revisar el registro de riego #{n} antes de confirmar reduce segundas visitas."
        mecanismo = (
            f"La comprobacion previa #{n} detecta campos ausentes antes de confirmar "
            "la cita, permite corregir el registro y evita retornos por datos incompletos."
        )
        payload = {
            "hipotesis": hipotesis,
            "mecanismo": mecanismo,
            "aportacion_por_tecnica": ["Detectar ausencias antes de confirmar."],
            "supuestos": ["Los retornos se deben a datos incompletos."],
            "prueba_concreta": "Comparar cien citas por grupo y contar retornos.",
        }
        raw = json.dumps(payload, ensure_ascii=False)
        return InterpretationResult(
            estado=ESTADO_PROPUESTA,
            hipotesis=hipotesis,
            mecanismo=mecanismo,
            aportacion_por_tecnica=payload["aportacion_por_tecnica"],
            supuestos=payload["supuestos"],
            prueba_concreta=payload["prueba_concreta"],
            prueba=_prueba(),
            cadena_causal=[
                "Comprobar campos detecta ausencias.",
                "Corregir ausencias evita retornos.",
            ],
            incertidumbre="Se desconoce la fraccion atribuible al registro.",
            novedad="Antecedentes sin buscar; no se afirma novedad.",
            critica={
                "evaluation_status": "CRITIQUED",
                "respuesta": _critica(),
                "independent_validation": False,
            },
            provenance=Provenance(
                **{**_provenance().as_dict(), "raw_output_sha256": _sha(raw)}
            ),
            raw_output=raw,
            finish_reason="stop",
            completion_tokens=321,
        )
''',
        encoding="utf-8",
    )
    return str(mod_path)


def _recovery_worker_source() -> Path:
    """Ruta al worker de recuperación (archivo físico, sin f-string)."""
    return Path(__file__).resolve().parent / "recovery_reader.py"


def main() -> int:
    if len(sys.argv) != 2:
        print("uso: journey_e2e_no_model.py <directorio-aislado>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    # Normalizar a ruta NATIVA Windows. En MSYS, '/c/Users/...' resuelve por
    # os.path a un path válido, pero Path.resolve() nativo lo convierte en
    # 'C:\\c\\Users\\...' (inexistente). Si SUPRA_STORAGE_DIR apunta a esa forma,
    # el artefacto .tmp se escribe en un path fantasma: el proceso que escribió
    # "ve" el archivo (mismo path deformado) pero ningún otro lector lo halla.
    # Es un éxito falso de persistencia inducido por el arnés, no por el producto.
    # _normalizar_native deja el path como 'C:/Users/...'.
    root = _normalizar_native(root)
    os.makedirs(root, exist_ok=True)
    # CRÍTICO (antes de importar nada de supra_agentic): el state_manager de SUPRA
    # es un SINGLETON a nivel de módulo (state.py:731). Si se importa antes de
    # fijar estas variables, se congela con el storage por defecto (LOCALAPPDATA en
    # Windows) y las variables puestas después NO surten efecto: el journey
    # "pasaría" leyendo de la máquina del operador en vez del almacenamiento
    # aislado, un éxito falso. Fijarlas primero es lo único que hace el test
    # reproducible y aislado.
    os.environ["SUPRA_STORAGE_DIR"] = str(root / "supra_state")
    os.environ["CRIBASHADOW_HOME"] = str(root)
    os.environ["CRIBA_MODEL_CONFIG"] = str(root / "models.json")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    operation_id = uuid.uuid4().hex[:16]
    server = None
    win = None

    criba_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(criba_root))
    sys.path.insert(0, str(criba_root / "shadow_ui"))

    # Intérprete sintético: mismo puerto, cero red.
    fake_mod_path = _build_fake_interpreter_module(root)
    sys.path.insert(0, str(root))
    import criba.interprete.seleccion as seleccion  # noqa: E402

    _fake = __import__(Path(fake_mod_path).stem)

    def _construir(backend=None):
        return _fake.InterpreteSintetico()

    seleccion.construir_interprete = _construir

    import criba_shadow_main as launcher  # noqa: E402

    launcher.wire_import_paths()
    trace_path = root / "journey_trace.json"

    try:
        import criba.ui.actions as actions  # noqa: E402
        from PySide6.QtWidgets import QApplication  # noqa: E402
        from shadow_window import ShadowWindow  # noqa: E402

        app = QApplication.instance() or QApplication(sys.argv)
        server = launcher.SupraServer(
            "http://127.0.0.1:8791",
            root / "supra_state",
            root / "logs" / "journey.log",
        )
        ok, endpoint = server.start(wait_s=90.0)
        if not ok:
            raise RuntimeError(endpoint)

        win = ShadowWindow(database=str(root / "criba.sqlite3"))
        win.show()
        app.processEvents()

        _entered(operation_id, "UI_ACTION", "Nueva idea -> problema del usuario")
        actions.on_nueva_idea_no_dialog(win, PROBLEM)
        assert win.problem == PROBLEM, f"problema no aplicado: {win.problem!r}"
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
        entries = sheet.get("entries", [])
        if not entries:
            raise RuntimeError("sin entradas interpretadas")
        _returned(
            operation_id,
            "INTERPRETER_RAW",
            {"entry_count": len(entries)},
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
        abstained = [
            item
            for item in entries
            if item.get("estado_interpretacion") != "PROPUESTA"
        ]
        if not proposals:
            raise RuntimeError("cero propuestas válidas del intérprete sintético")
        _returned(
            operation_id,
            "PARSER_SCHEMA",
            {"validas": len(proposals), "abstenciones": len(abstained)},
            f"propuestas_validas={len(proposals)}/{len(entries)} "
            f"abstenciones_honestas={len(abstained)}",
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
            [{"project_id": r.get("project_id"), "status": r.get("status")} for r in runs],
            f"endpoint={endpoint}",
        )

        _entered(operation_id, "HTTP_RESPONSE")
        if any(not r.get("project_id") for r in runs):
            raise RuntimeError("respuesta SUPRA sin project_id")
        _returned(
            operation_id,
            "HTTP_RESPONSE",
            [r.get("read") for r in runs],
            "POST y respuesta contractual recibidos",
        )

        _entered(operation_id, "PERSISTENCE")
        project_ids = [str(r["project_id"]) for r in runs]
        artifacts = [root / "supra_state" / f"{pid}.json" for pid in project_ids]
        missing = [str(p) for p in artifacts if not p.is_file()]
        # Instrumentación de diagnóstico (no cambia el veredicto): si falta el
        # artefacto, decir DÓNDE escribió realmente el state_manager.
        diag: dict[str, Any] = {}
        try:
            from supra_agentic.state import state_manager as _sm

            diag = {
                "storage_dir": str(_sm.storage_dir),
                "storage_mode": _sm.storage_mode,
                "memory_keys": sorted(_sm._projects.keys()),
                "env_SUPRA_STORAGE_DIR": os.getenv("SUPRA_STORAGE_DIR"),
                "expected_root": str(root / "supra_state"),
            }
            _record(
                operation_id, "PERSISTENCE", "DIAG",
                payload=diag, detail="estado real del state_manager",
            )
        except Exception as exc:  # noqa: BLE001
            _record(
                operation_id, "PERSISTENCE", "DIAG_FAILED",
                detail=f"{type(exc).__name__}: {exc}",
            )
        if missing:
            raise RuntimeError(
                f"artefactos SUPRA ausentes en disco: {missing} | diag={json.dumps(diag)}"
            )
        _returned(
            operation_id,
            "PERSISTENCE",
            [str(p) for p in artifacts],
            f"artefactos persistidos en disco ({len(artifacts)})",
        )

        _entered(operation_id, "GET_READBACK")
        reads = [r.get("read") for r in runs]
        if any(not isinstance(r, dict) for r in reads):
            raise RuntimeError("falta GET/readback en uno o más runs")
        _returned(
            operation_id,
            "GET_READBACK",
            reads,
            "; ".join(
                f"{r.get('status_source')}/{r.get('persisted_artifact_status')}"
                for r in reads
            ),
        )

        _entered(operation_id, "SHADOW_RENDER")
        supra_text = win.candidates.supra_output.toPlainText()
        if not supra_text.strip():
            raise RuntimeError("el GET no se representó en Shadow")
        for pid in project_ids:
            if pid not in supra_text:
                raise RuntimeError(f"Shadow no muestra project_id {pid}")
        _returned(
            operation_id,
            "SHADOW_RENDER",
            {"supra_chars": len(supra_text)},
            "Shadow representa el GET durable",
        )

        _entered(operation_id, "CLEAN_SHUTDOWN")
        win.close()
        app.processEvents()
        server.stop()
        server = None
        _returned(operation_id, "CLEAN_SHUTDOWN", detail="ventana y SUPRA detenidos")

        # REINICIO REAL DE PROCESO. state_manager es un singleton a nivel de
        # módulo: relanzar SupraServer como hilo en ESTE proceso reutiliza la
        # memoria ya poblada y serviría IN_PROCESS_MEMORY_CACHE, lo que NO acredita
        # recuperación desde disco. CB-03 exige "reinicio tras escritura", así que
        # el lector se ejecuta en un subproceso Python nuevo con memoria vacía.
        _entered(
            operation_id,
            "RESTART_PROCESS",
            "subproceso nuevo (memoria limpia) sobre el mismo storage",
        )
        recovery_script = _recovery_worker_source()
        proc = subprocess.run(
            [sys.executable, str(recovery_script), str(root), endpoint],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "lector de recuperación falló: "
                f"rc={proc.returncode} stderr={proc.stderr[-1200:]}"
            )
        recovered = json.loads(proc.stdout.strip().splitlines()[-1])
        _returned(
            operation_id,
            "RESTART_PROCESS",
            recovered,
            f"subproceso pid nuevo; source={recovered.get('status_source')}",
        )

        _entered(operation_id, "REOPEN_RELOAD", "recuperación desde disco por GET/LIST")
        recovered_id = str(recovered.get("project_id") or "")
        if not recovered_id:
            raise RuntimeError("tras restart real no hay proyecto persistido en disco")
        if recovered_id not in project_ids:
            raise RuntimeError(f"restart recuperó un project_id ajeno al run: {recovered_id}")
        recovered_read = recovered.get("read") or {}
        initial_read = next(
            r["read"] for r in runs if str(r["project_id"]) == recovered_id
        )
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
        # El invariante central de CB-03: tras reinicio real de proceso, la fuente
        # DEBE ser el artefacto en disco, no la caché de memoria del proceso previo.
        if recovered.get("status_source") != "PERSISTED_STATE":
            raise RuntimeError(
                "recuperación no provino del disco: "
                f"status_source={recovered.get('status_source')!r} "
                f"(se esperaba PERSISTED_STATE tras reinicio real de proceso)"
            )
        _returned(
            operation_id,
            "REOPEN_RELOAD",
            recovered,
            f"project_id={recovered_id} source={recovered_read.get('status_source')} "
            f"artifact={recovered.get('persisted_artifact_status')}",
        )

        _entered(operation_id, "SHADOW_RECOVERY")
        # Shadow necesita un SUPRA vivo para recargar por HTTP. El servidor se
        # detuvo en CLEAN_SHUTDOWN y el worker de recuperación detuvo el suyo al
        # salir, así que se relanza sobre el MISMO storage durable. La prueba de
        # que la verdad viene del disco (PERSISTED_STATE) ya la hizo el subproceso
        # de memoria limpia; aquí solo hace falta endpoint vivo para que Shadow
        # muestre la verdad recuperada por la misma ruta de UI.
        server = launcher.SupraServer(
            endpoint,
            root / "supra_state",
            root / "logs" / "journey-recovery.log",
        )
        ok_r, endpoint_r = server.start(wait_s=90.0)
        if not ok_r:
            raise RuntimeError(endpoint_r)
        # Reabrir Shadow y volcar la verdad recuperada por la misma ruta de UI.
        win = ShadowWindow(database=str(root / "criba.sqlite3"))
        win.show()
        app.processEvents()
        # _load_latest_supra solo trae el report; quien lo pinta en el panel
        # supra_output es _on_supra_restore_done (el arnés no pasa por el worker).
        report = actions._load_latest_supra()
        if report.get("empty"):
            raise RuntimeError("Shadow reabierto no recuperó el proyecto del disco")
        actions._on_supra_restore_done(win, report)
        app.processEvents()
        recovered_text = win.candidates.supra_output.toPlainText()
        shadow_id = str(report.get("project_id") or "")
        if (
            not recovered_text.strip()
            or recovered_id not in recovered_text
            or shadow_id != recovered_id
        ):
            raise RuntimeError(
                "Shadow no mostró la verdad recuperada tras restart: "
                f"shadow_report_id={shadow_id!r} recovered_id={recovered_id!r} "
                f"supra_chars={len(recovered_text)} "
                f"shadow_has_recovered={recovered_id in recovered_text}"
            )
        _returned(
            operation_id,
            "SHADOW_RECOVERY",
            {"project_id": recovered_id, "supra_chars": len(recovered_text)},
            "reopen/reload mostró GET durable en Shadow",
        )
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
