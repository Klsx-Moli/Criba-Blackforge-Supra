"""Pruebas aisladas de IMP-05 — preservación de fichas en SUPRA.

ALCANCE (steer + tarjeta IMP-05, risk_profile LAB):
  - Ejercitan funciones EXISTENTES del producto (supra_dossier, supra_client)
    sobre storage TEMPORAL de laboratorio y un transport httpx mock.
  - NO tocan SUPRA real, no abren red, no invocan modelos ni BLACKFORGE.
  - NO acreditan SUPRA real ni un reinicio del producto: una prueba de disco
    local solo verifica el contrato de serialización/lectura del cliente.

No se aplica ningún parche de runtime: el adaptador ficha->dossier se propone
en SPEC.md y NO se integra aquí.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from criba import supra_dossier
from criba.integrations.supra_client import (
    SupraClient,
    SupraClientConfig,
    SupraClientError,
    _dossier_payload_fingerprint,
)


# ---------------------------------------------------------------------------
# Helpers de laboratorio
# ---------------------------------------------------------------------------

def _canonical_sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _minimal_entry(candidate_id: str = "AC-06-001") -> dict:
    """Entry mínimo que preparar_dossier puede convertir en un dossier válido.

    No es una ficha AC-06 cruda: una ficha académica NO es auto-suficiente
    para un dossier SUPRA (le faltan problema, candidate_id, evidencia). Ese
    envolvente de campaña es exactamente lo que el adaptador propuesto en
    SPEC.md debe aportar. Aquí lo aportamos directamente para probar el
    contrato de preservación, no la conversión de ficha.
    """
    return {
        "candidate_id": candidate_id,
        "hipotesis": "la transferencia relacional reduce omisiones cercanas",
        "mecanismo": (
            "un mecanismo de separacion por contraste discrimina el fallo "
            "antes de construir un prototipo costoso"
        ),
        "prueba_concreta": "contrastar el rival con la predicción del mecanismo",
        "observable": "los ejes declarados cambian de valor bajo la intervención",
        "condicion_fracaso": "si los ejes no cambian, la alternativa gana",
        "supuestos": ["ruptura del supuesto de cobertura cercana"],
        "interpretacion_provenance": {"interpreter_backend": "deterministic_core"},
    }


def _make_client(transport: httpx.BaseTransport) -> SupraClient:
    return SupraClient(
        SupraClientConfig(endpoint="http://supra.test", api_key="", timeout=5.0),
        transport=transport,
    )


def _ok_project_response(*, envelope_version: str, dossier: dict) -> httpx.Response:
    """Construye la respuesta 200 que un SUPRA que respeta el contrato devolvería.

    El payload_fingerprint del receipt debe coincidir con lo que el cliente
    calculó en el write path: un servidor que devuelve otro fingerprint es un
    servidor que no preserva el contenido semántico.
    """
    fingerprint = _dossier_payload_fingerprint(dossier)
    body = {
        "status": "success",
        "completion_status": "COMPLETED",
        "workflow_status": "COMPLETED",
        "verification_status": "PASS",
        "secure_sandbox_status": "ISOLATED_BOUND_PASS",
        "criba_planning_receipt_status": "PRESERVED_NOT_EXECUTED",
        "criba_mechanism_execution_status": "NOT_EXECUTED",
        "project_id": "astram2-test",
        "stage": "COMPLETED",
        "posture": {
            "project_id": "astram2-test",
            "stage": "COMPLETED",
            "criba_dossier_receipt": {
                "receipt_scope": "PLANNED_DISCRIMINANT_PROTOCOL_ONLY",
                "execution_status": "NOT_EXECUTED",
                "scientific_status": "NOT_VALIDATED",
                "criba_dossier_id": dossier["dossier_id"],
                "criba_candidate_id": dossier["candidate_id"],
                "claim_id": dossier["claim_id"],
                "mechanism_version": dossier["mechanism_version"],
                "protocol_version": dossier["protocol_version"],
                "integration_version": envelope_version,
                "payload_fingerprint": fingerprint,
            },
        },
    }
    return httpx.Response(200, json=body)


# ---------------------------------------------------------------------------
# AC: preservación por disco (guardar/cargar) — no sobrescribir
# ---------------------------------------------------------------------------

def test_roundtrip_preserves_semantic_object(tmp_path: Path):
    """Guardar y cargar conserva el objeto semántico y el estado no-ejecutado."""
    dossier = supra_dossier.preparar_dossier(_minimal_entry(), problema="reducir omisiones")
    path = supra_dossier.guardar_dossier(dossier, directory=tmp_path)
    assert path.exists()

    loaded = supra_dossier.cargar_dossier(dossier["dossier_id"], directory=tmp_path)
    assert loaded is not None
    # Objeto semántico conservado (excluye metadata no-semántica creado_at).
    assert supra_dossier._contexto(loaded) == supra_dossier._contexto(dossier)
    # Estado no promovido: persistir/leer NO ejecuta ni valida la hipótesis.
    assert loaded["estado"] == "SUPRA_EJECUCION_PENDIENTE"
    assert loaded["prueba_discriminante"]["estado_prueba"] == "NO_EJECUTADA"


def test_same_id_same_payload_is_not_overwritten(tmp_path: Path):
    """Mismo ID + mismo payload: se conserva, NO se duplica la línea en disco."""
    dossier = supra_dossier.preparar_dossier(_minimal_entry(), problema="reducir omisiones")
    supra_dossier.guardar_dossier(dossier, directory=tmp_path)
    supra_dossier.guardar_dossier(dossier, directory=tmp_path)  # segundo guardado

    lines = [ln for ln in (tmp_path / "dossiers.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1, "un mismo ID/payload no debe duplicar el registro"


def test_same_id_different_payload_is_rejected_not_overwritten(tmp_path: Path):
    """Mismo ID + payload distinto: error de ambigüedad, NO sobrescritura silenciosa."""
    dossier = supra_dossier.preparar_dossier(_minimal_entry(), problema="reducir omisiones")
    supra_dossier.guardar_dossier(dossier, directory=tmp_path)

    other = json.loads(json.dumps(dossier))
    other["hipotesis"] = "hipótesis distinta que cambia el contenido"
    with pytest.raises(ValueError, match="ambiguo"):
        supra_dossier.guardar_dossier(other, directory=tmp_path)

    # El registro original sigue intacto y único.
    lines = [ln for ln in (tmp_path / "dossiers.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["hipotesis"] == dossier["hipotesis"]


def test_corrupted_dossier_line_is_ignored_on_read(tmp_path: Path):
    """Una línea corrupta en el historial no rompe la lectura (contrato de robustez)."""
    dossier = supra_dossier.preparar_dossier(_minimal_entry(), problema="reducir omisiones")
    supra_dossier.guardar_dossier(dossier, directory=tmp_path)
    (tmp_path / "dossiers.jsonl").open("a", encoding="utf-8").write("not-json-at-all\n")

    loaded = supra_dossier.cargar_dossier(dossier["dossier_id"], directory=tmp_path)
    assert loaded is not None
    assert loaded["dossier_id"] == dossier["dossier_id"]


# ---------------------------------------------------------------------------
# AC: rechazo de versión desconocida del envelope (contrato del cliente)
# ---------------------------------------------------------------------------

def test_client_rejects_unknown_envelope_version():
    """Un receipt con integration_version desconocido se rechaza, no se acepta."""
    dossier = supra_dossier.preparar_dossier(_minimal_entry(), problema="reducir omisiones")
    transport = httpx.MockTransport(lambda req: _ok_project_response(envelope_version="criba-supra/99", dossier=dossier))
    client = _make_client(transport)
    with pytest.raises((SupraClientError, ValueError)):
        client.run_project(
            objective="evaluar dossier de preservación de ficha",
            criba_dossier=dossier,
        )


def test_client_accepts_canonical_envelope_version():
    """Con el envelope version canónico y lineage coincidente, el receipt se preserva."""
    dossier = supra_dossier.preparar_dossier(_minimal_entry(), problema="reducir omisiones")
    transport = httpx.MockTransport(lambda req: _ok_project_response(envelope_version="criba-supra/1", dossier=dossier))
    client = _make_client(transport)
    result = client.run_project(
        objective="evaluar dossier de preservación de ficha",
        criba_dossier=dossier,
    )
    receipt = result.posture["criba_dossier_receipt"]
    assert receipt["integration_version"] == "criba-supra/1"
    assert receipt["execution_status"] == "NOT_EXECUTED"
    assert receipt["scientific_status"] == "NOT_VALIDATED"


def test_client_rejects_lineage_mismatch():
    """Un receipt que devuelve lineage distinto al enviado se rechaza (no se preserva)."""
    dossier = supra_dossier.preparar_dossier(_minimal_entry(), problema="reducir omisiones")

    def handler(req: httpx.Request) -> httpx.Response:
        body = _ok_project_response(envelope_version="criba-supra/1", dossier=dossier).json()
        body["posture"]["criba_dossier_receipt"]["criba_candidate_id"] = "candidato-ALTERADO"
        return httpx.Response(200, json=body)

    client = _make_client(httpx.MockTransport(handler))
    with pytest.raises(SupraClientError):
        client.run_project(
            objective="evaluar dossier de preservación de ficha",
            criba_dossier=dossier,
        )


def test_client_does_not_send_model_by_default():
    """El write path no invoca un modelo: use_model=False y no se adjunta provider."""
    seen: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode("utf-8"))
        seen["body"] = body
        if not req.url.path.endswith("/projects"):
            return httpx.Response(200, json={"status": "ok"})
        dossier = body["criba_dossier"]
        return _ok_project_response(envelope_version="criba-supra/1", dossier=dossier)

    dossier = supra_dossier.preparar_dossier(_minimal_entry(), problema="reducir omisiones")
    client = _make_client(httpx.MockTransport(handler))
    client.run_project(objective="evaluar dossier de preservación de ficha", criba_dossier=dossier)
    assert seen["body"].get("use_model") is False
    assert "provider" not in seen["body"]
    assert "model" not in seen["body"]
