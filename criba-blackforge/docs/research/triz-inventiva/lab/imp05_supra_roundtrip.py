"""Laboratorio aislado IMP-05 — round-trip SUPRA de un dossier derivado de la
campaña ACADEMICO-TRIZ-INVENTIVA.

ALCANCE (steer 2026-10-28, punto E):
  - IMP-05 queda LIMITADO a especificaciones, propuesta de diff y pruebas
    aisladas. NO ejecuta runtime productivo, NO usa red real, NO escribe en
    bases/dossiers/configuraciones productivas.
  - Transporte: httpx.MockTransport (loopback en memoria, sin socket).
  - Almacenamiento: tmp_path de pytest (temporal exclusivo de la campaña).

"Transporte doble identificado" = el envelope que el cliente ya emite y que
SUPRA devuelve en el receipt:
  - criba_integration_version  ("criba-supra/1")
  - criba_payload_fingerprint  (sha256 del contenido semantico)
El laboratorio verifica que ambos sobreviven el round-trip sin promover el
receipt mas alla de PLANNED_DISCRIMINANT_PROTOCOL_ONLY / NOT_EXECUTED.

El dossier canónico se deriva de la campaña (objective + mecanismo/protocolo
con sha256) para que el fingerprint sea reproducible. No se envía el payload
completo de la campaña: se construye un dossier CRIBA mínimo que cumple el
contrato de lineage del cliente.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx

from criba.integrations.supra_client import (
    SupraClient,
    SupraClientConfig,
    _dossier_payload_fingerprint,
    objective_from_dossier,
)


# --- Derivación reproducible del dossier canónico de la campaña ---

def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_campaign_dossier() -> dict[str, Any]:
    """Construye un dossier CRIBA mínimo con lineage completo.

    No es el payload de la campaña; es un dossier que cumple el contrato de
    lineage del cliente (dossier_id/candidate_id/claim_id/mechanism_version/
    protocol_version) para ejercitar el round-trip en laboratorio.
    """
    mechanism_text = "ACADEMICO-TRIZ-INVENTIVA: transferencia de operacion"
    protocol_text = "ACADEMICO-TRIZ-INVENTIVA: prueba discriminante"
    return {
        "dossier_id": "ACADEMICO-TRIZ-INVENTIVA-20261028",
        "candidate_id": "criba-triz-candidate",
        "claim_id": "claim-triz-inventiva",
        "mechanism_version": _sha256(mechanism_text),
        "protocol_version": _sha256(protocol_text),
        "problema": "¿La transferencia de operación inventiva reduce omisiones?",
        "hipotesis": "Sí, por reencuadre del dominio fuente.",
        "mecanismo": "operacion transferida + limite de ruptura",
        "prueba_discriminante": {
            "intervencion_prueba": "aplicar operador TRIZ en caso objetivo",
            "observable": "omisiones cercanas a cero",
            "regla_decision": "si omisiones < rival, la transferencia gana",
            "condicion_fracaso": "si omisiones >= rival, no discrimina",
        },
    }


def _mock_transport(expected_fingerprint: str) -> httpx.MockTransport:
    """Transporte en memoria que simula el contrato de escritura de SUPRA.

    Devuelve un posture con criba_dossier_receipt que refleja el lineage
    recibido (doble identificado). No ejecuta nada: el estado del receipt es
    PLANNED_DISCRIMINANT_PROTOCOL_ONLY / NOT_EXECUTED / NOT_VALIDATED.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/projects"
        body = json.loads(request.content)
        # El doble identificado debe estar presente en la petición.
        assert body.get("criba_integration_version") == "criba-supra/1"
        assert body.get("criba_payload_fingerprint") == expected_fingerprint
        receipt = {
            "receipt_scope": "PLANNED_DISCRIMINANT_PROTOCOL_ONLY",
            "execution_status": "NOT_EXECUTED",
            "scientific_status": "NOT_VALIDATED",
            "criba_dossier_id": body["criba_dossier"]["dossier_id"],
            "criba_candidate_id": body["criba_dossier"]["candidate_id"],
            "claim_id": body["criba_dossier"]["claim_id"],
            "mechanism_version": body["criba_dossier"]["mechanism_version"],
            "protocol_version": body["criba_dossier"]["protocol_version"],
            "integration_version": "criba-supra/1",
            "payload_fingerprint": expected_fingerprint,
        }
        payload = {
            "status": "success",
            "completion_status": "COMPLETED",
            "workflow_status": "COMPLETED",
            "verification_status": "COMPLETED",
            "stage": "COMPLETED",
            "secure_sandbox_status": "NOT_REPORTED",
            "project_id": "proj-triz-lab",
            "posture": {"criba_dossier_receipt": receipt},
        }
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


def run_roundtrip(tmp_path) -> dict[str, Any]:
    """Ejecuta el round-trip en laboratorio y devuelve el receipt validado.

    tmp_path: directorio temporal exclusivo (pytest). Se usa solo para registrar
    el dossier enviado como evidencia; no toca ninguna base productiva.
    """
    dossier = build_campaign_dossier()
    fingerprint = _dossier_payload_fingerprint(dossier)

    # Evidencia en directorio temporal exclusivo de la campaña.
    evidence = tmp_path / "triz_supra_lab"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "dossier_sent.json").write_text(
        json.dumps(dossier, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    client = SupraClient(
        SupraClientConfig(endpoint="http://127.0.0.1:8000"),
        transport=_mock_transport(fingerprint),
    )
    result = client.run_project(
        objective=objective_from_dossier(dossier),
        criba_dossier=dossier,
    )
    client.close()

    receipt = result.posture["criba_dossier_receipt"]
    receipt["_expected_fingerprint"] = fingerprint
    receipt["_dossier_id_sent"] = dossier["dossier_id"]
    return receipt


def main() -> None:
    """Ejecución standalone (sin pytest): escribe evidencia en ./_lab_evidence."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="triz_supra_lab_") as d:
        from pathlib import Path

        receipt = run_roundtrip(Path(d))
        print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
