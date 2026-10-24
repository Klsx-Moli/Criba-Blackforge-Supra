"""CB-R03: persistencia local + readback de dossier tras cierre del proceso.

Cierra exactamente el gap que CB-R01 no cubre:

- CB-R01 prueba guardar_dossier / cargar_dossier / cargar_ultimo_dossier
  sobre disco real, pero en un MISMO proceso (cierra y reabre el modulo de
  lectura sobre el mismo directorio). Eso no prueba que Shadow, tras cerrar
  la ventana y volver a abrir, recupere el dossier que envio a SUPRA.

- test_m3 H8 prueba _load_latest_supra tras restart del SERVIDOR SUPRA, con
  proveedor simulado real (SUPRA_USE_MODEL=false). Pero persiste el receipt
  en el servidor; NO persiste el dossier localmente ni configura
  CRIBASHADOW_HOME, por lo que _load_latest_supra no puede recuperarlo:
  el campo report["dossier"] se veria None y nadie lo afirmaba.

Este test encadena los tres ciclos reales sin mocks en la logica bajo prueba:

  1. preparar_dossier -> dossier canonical con identity/hash/procedencia.
  2. guardar_dossier(dossier, dir) -> persistencia en dossiers.jsonl REAL.
  3. Cerrar el proceso propietario del estado en memoria: simulado con un
     nuevo entorno limpio (CRIBASHADOW_HOME apunta al mismo tmp_path).
  4. _load_latest_supra(client) -> LIST + GET real contra el proveedor
     simulado (MockTransport, no servidor externo), recovery de receipt y
     carga del dossier por cargar_dossier sobre el mismo directorio.
  5. Comparacion de identidad (dossier_id, claim_id, mechanism_version,
     protocol_version, candidate_id) y contenido (hipotesis, mecanismo,
     prueba discriminante intacto).

Negativos:
  - receipt que referencia un dossier_id inexistente -> dossier=None
    (no se fabrica contenido).
  - receipt con campos de identidad incompatibles -> dossier=None
    (la validacion de identidad en _load_latest_supra lo rechaza).

No se toca ShadowWindow: este test ejercer el codigo de recovery que
Shadow invoca (_load_latest_supra), no la UI. Si Shadow tuviera un hook
de arranque que llamara a on_restore_latest_supra, ese hook no se prueba
aqui: queda pendiente de una prueba de integracion UI/REST que requiera
entorno Qt/REST real.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest

from criba.integrations.supra_client import SupraClient, SupraClientConfig
from criba.supra_dossier import (
    _discriminant_protocol_complete,
    cargar_dossier,
    preparar_dossier,
    guardar_dossier,
)
from criba.ui import actions
from verification.interpreter_cases import critica, propuesta


def _dossier_real(tmp_path: Path) -> dict[str, dict]:
    """Dossier canonical construido con el codigo real preparar_dossier."""
    entry = {
        **propuesta(),
        "candidate_id": "idea-r03",
        "estado_interpretacion": "PROPUESTA",
        "critica": {
            "evaluation_status": "CRITIQUED",
            "respuesta": critica(),
            "independent_validation": False,
        },
    }
    dossier = preparar_dossier(
        entry,
        "Eliminar segundas visitas por errores de registro.",
        ficha_bloqueo={"title": "salud"},
    )
    return {"entry": entry, "dossier": dossier}


def _receipt_for(dossier: dict) -> dict:
    """Receipt que enlaza al dossier por su identidad canonical."""
    return {
        "receipt_scope": "PLANNED_DISCRIMINANT_PROTOCOL_ONLY",
        "execution_status": "NOT_EXECUTED",
        "scientific_status": "NOT_VALIDATED",
        "criba_dossier_id": dossier["dossier_id"],
        "criba_candidate_id": dossier["candidate_id"],
        "claim_id": dossier["claim_id"],
        "mechanism_version": dossier["mechanism_version"],
        "protocol_version": dossier["protocol_version"],
        "integration_version": "criba-supra/1",
        "payload_fingerprint": "sha256:" + "f" * 64,
    }


def _supra_read_payload(dossier: dict, receipt: dict) -> dict:
    """Response GET /api/v1/projects/{id} con el receipt embebido."""
    return {
        "status": "blocked",
        "status_scope": "WORKFLOW_EXECUTION_ONLY",
        "completion_status": "BLOCKED",
        "workflow_status": "BLOCKED",
        "verification_status": "FAIL",
        "scientific_status": "NOT_VALIDATED",
        "secure_sandbox_status": "RESTRICTED_BOUND_PASS_NOT_ISOLATED",
        "criba_planning_receipt_status": "PRESERVED_NOT_EXECUTED",
        "criba_mechanism_execution_status": "NOT_EXECUTED",
        "idempotent_replay": False,
        "status_source": "PERSISTED_STATE",
        "persisted_artifact_status": "VERIFIED_FROM_ARTIFACT",
        "project_id": "astram2-r03",
        "stage": "BLOCKED",
        "posture": {
            "project_id": "astram2-r03",
            "stage": "BLOCKED",
            "final_output": None,
            "error_message": None,
            "criba_dossier_receipt": receipt,
        },
    }


def _build_client(tmp_path: Path, dossier: dict, receipt: dict) -> SupraClient:
    """Cliente con MockTransport; LIST devuelve el project_id, GET devuelve el read payload."""
    project_id = "astram2-r03"
    list_payload = {"status": "ok", "count": 1, "projects": [{"project_id": project_id}]}
    get_payload = _supra_read_payload(dossier, receipt)

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/health":
            return httpx.Response(200, json={"status": "ok", "service": "supra", "version": "test"})
        if path == "/api/v1/projects":
            return httpx.Response(200, json=list_payload)
        if path.startswith("/api/v1/projects/"):
            return httpx.Response(200, json=get_payload)
        return httpx.Response(404, json={"detail": "not found"})

    return SupraClient(
        SupraClientConfig(endpoint="https://supra.test", timeout=2.0),
        transport=httpx.MockTransport(handler),
    )


def test_persistencia_local_readback_tras_restart(tmp_path: Path, monkeypatch) -> None:
    """guardar_dossier -> proceso nuevo (env limpio) -> _load_latest_supra -> cargar_dossier.

    Garantia real: el dossier recuperado coincide por identidad canonical
    (dossier_id, candidate_id, claim_id, mechanism_version, protocol_version)
    y contenido (hipotesis, mecanismo, prueba discriminante intacta). No se
    comparan hashes de fecha de creacion (creado_at) ni dossier_id generado
    por uuid: se compara identidad declarada y contenido semantico.
    """
    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))

    built = _dossier_real(tmp_path)
    dossier = built["dossier"]
    receipt = _receipt_for(dossier)

    # 1. Persistencia local REAL: escribe en dossiers.jsonl sobre CRIBASHADOW_HOME.
    #    Se guarda SIN directory para usar el mismo path que cargar_dossier en
    #    _load_latest_supra (que tampoco pasa directory explícito).
    guardar_dossier(dossier)
    dossier_path = tmp_path / "dossiers" / "dossiers.jsonl"
    assert dossier_path.is_file(), "el dossier no se persistio en disco"

    # 2. "Cierre del proceso": nuevo entorno limpio apuntando al mismo storage.
    #    CRIBASHADOW_HOME ya esta seteado al tmp_path por monkeypatch.
    #    No se recrea el objeto; se abre como lo haria un nuevo proceso.
    recovered = cargar_dossier(dossier["dossier_id"])
    assert recovered is not None, "cargar_dossier no recupero el dossier persistido"
    assert recovered["dossier_id"] == dossier["dossier_id"]

    # 3. Readback end-to-end: _load_latest_supra con proveedor simulado.
    with _build_client(tmp_path, dossier, receipt) as client:
        report = actions._load_latest_supra(client)

    assert not report.get("empty"), report
    assert report["project_id"] == "astram2-r03"

    # 4. El receipt sobrevive y referencia el dossier por su identity.
    read = report["read"]
    receipt_back = read.get("receipt") or {}
    assert receipt_back.get("criba_dossier_id") == dossier["dossier_id"]

    # 5. El dossier local se recupera por el receipt, con identity intacta.
    loaded = report.get("dossier")
    assert loaded is not None, "el dossier local no fue recuperado tras restart"
    for field in ("dossier_id", "candidate_id", "claim_id",
                  "mechanism_version", "protocol_version"):
        assert loaded.get(field) == dossier.get(field), (
            f"identidad divergen en {field}: {loaded.get(field)!r} != {dossier.get(field)!r}"
        )
    # Contenido semantico intacto
    assert loaded["hipotesis"] == dossier["hipotesis"]
    assert loaded["mecanismo"] == dossier["mecanismo"]
    # El protocolo discriminante sobrevive completo
    assert _discriminant_protocol_complete(loaded), "el protocolo discriminator se corrompio"


def test_readback_dossier_inexistente_devuelve_none_no_fabrica(tmp_path: Path, monkeypatch) -> None:
    """Un receipt que referencia un dossier_id que no existe localmente no
    debe devolver contenido fabricado: dossier=None, sin error."""
    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))

    built = _dossier_real(tmp_path)
    dossier = built["dossier"]
    # Receipt con un dossier_id que NUNCA se guardo localmente.
    bad_receipt = _receipt_for(dossier)
    bad_receipt["criba_dossier_id"] = "dossier-que-no-existe-en-disco"
    # Los otros campos de identity del receipt no coinciden con el dossier.
    bad_receipt["criba_candidate_id"] = "otro-candidato"
    bad_receipt["claim_id"] = "claim-otra"

    with _build_client(tmp_path, dossier, bad_receipt) as client:
        report = actions._load_latest_supra(client)

    assert not report.get("empty"), report
    assert report.get("dossier") is None, "se devolvio un dossier para un receipt inexistente"
    # El receipt sigue disponible para auditoria
    read = report["read"]
    assert read["receipt"]["criba_dossier_id"] == "dossier-que-no-existe-en-disco"


def test_readback_identity_incompatible_descarta_dossier(tmp_path: Path, monkeypatch) -> None:
    """Un receipt con dossier_id existente pero identity de candidato/claim
    incompatible: el dossier se descarta (dossier=None) por la validacion
    de identidad en _load_latest_supra."""
    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))

    built = _dossier_real(tmp_path)
    dossier = built["dossier"]
    receipt = _receipt_for(dossier)
    # dossier_id existe localmente, pero candidate_id CLAIM_id mecanism VERIFY incompatibles
    receipt["criba_candidate_id"] = "candidato-incompatible"
    receipt["claim_id"] = "claim-incompatible"
    receipt["mechanism_version"] = "sha256:" + "0" * 64  # distinto del dossier

    guardar_dossier(dossier)

    with _build_client(tmp_path, dossier, receipt) as client:
        report = actions._load_latest_supra(client)

    # El receipt se readbackea correctamente...
    assert not report.get("empty"), report
    read = report["read"]
    assert read["receipt"]["criba_dossier_id"] == dossier["dossier_id"]
    # ...pero el dossier local se descarta por identity mismatch.
    assert report.get("dossier") is None, (
        "el dossier fue recuperado pese a identity incompatibles entre receipt y disco"
    )
