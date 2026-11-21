"""M4 - Test de contrato discriminante (roundtrip CRIBA -> dossier -> SUPRA -> GET).

Valida las invariantes del gate cientifico dirigido:
- dossier discriminante completo se envia a SUPRA y persiste (servidor real).
- campo rival (alternativa_explicativa) sobrevive serializacion, transporte y
  persistencia -> GET tras restart real (cache != durable truth).
- NOT_EXECUTED no se promueve a EXECUTED.
- provenance/lineage preservado trazable.
- candidate_id identico tras roundtrip.

NO usa mocks del servidor: _RealSupra servidor hijo con uvicorn en disco,
dossier construido por activate() -> preparar_dossier_desde_idea() (CRIBA real).

Camino real siguiendo el patron de M2/M3.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

REPO = Path(__file__).resolve().parents[2]
SUPRA_SRC = REPO.parent / "supra" / "src"
CRIBA_SRC = REPO / "src"

# SUPRA es un componente con su propio entorno; el servidor corre bajo el
# intérprete que realmente posee su paquete.
SUPRA_PYTHON = Path(
    os.getenv("SUPRA_E2E_PYTHON")
    or (REPO.parent / "supra" / ".venv" / "Scripts" / "python.exe")
)
if not SUPRA_PYTHON.is_file():  # pragma: no cover - guard de entorno
    pytest.skip(
        "venv de SUPRA ausente: el componente real no se puede lanzar",
        allow_module_level=True,
    )

if str(CRIBA_SRC) not in sys.path:
    sys.path.insert(0, str(CRIBA_SRC))
if str(SUPRA_SRC) not in sys.path:
    sys.path.insert(0, str(SUPRA_SRC))

from criba.engine import activate  # noqa: E402
from criba.integrations.supra_client import (  # noqa: E402
    SupraClient,
    SupraClientConfig,
)
from criba.supra_dossier import preparar_dossier_desde_idea  # noqa: E402


PROBLEM = (
    "Reducir el número de permisos excesivos concedidos a un agente sin perder "
    "trazabilidad de las decisiones."
)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _RealSupra:
    """Servicio SUPRA real como proceso hijo, con storage en disco propio."""

    def __init__(self, storage: Path) -> None:
        self.storage = storage
        self.port = _free_port()
        self.endpoint = f"http://127.0.0.1:{self.port}"
        self.log_path = storage.parent / "astra-m4-uvicorn.log"
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        self.log_path.write_text("", encoding="utf-8")
        handle = open(self.log_path, "a", encoding="utf-8")
        self.proc = subprocess.Popen(
            [
                str(SUPRA_PYTHON), "-m", "uvicorn", "supra_agentic.service:app",
                "--host", "127.0.0.1", "--port", str(self.port), "--log-level", "warning",
            ],
            cwd=str(REPO.parent / "supra"),
            stdout=handle, stderr=subprocess.STDOUT,
            env={
                **os.environ,
                "PYTHONPATH": str(SUPRA_SRC),
                "SUPRA_STORAGE_DIR": str(self.storage),
                "SUPRA_USE_MODEL": "false",
            },
        )
        for _ in range(90):
            try:
                if httpx.get(f"{self.endpoint}/health", timeout=3.0).status_code == 200:
                    return
            except Exception:
                pass
            if self.proc.poll() is not None:
                break
            time.sleep(1.0)
        raise AssertionError(
            "el servidor SUPRA real no respondio /health: "
            + self.log_path.read_text(encoding="utf-8")[-2000:]
        )

    def stop(self) -> None:
        if self.proc is None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=20)
        except subprocess.TimeoutExpired:  # pragma: no cover - cleanup guard
            self.proc.kill()
        self.proc = None

    def restart(self) -> None:
        """Reinicio REAL: mata el proceso y arranca otro con el mismo disco."""
        self.stop()
        self.start()

    def create(self, payload: dict) -> httpx.Response:
        return httpx.post(f"{self.endpoint}/api/v1/projects", json=payload, timeout=120.0)

    def get(self, project_id: str) -> httpx.Response:
        return httpx.get(f"{self.endpoint}/api/v1/projects/{project_id}", timeout=30.0)


def _exact_create_payload(objective: str, project_id: str, dossier: dict) -> dict:
    """Captura el payload exacto que SupraClient envia, sin replicar su logica.

    run_project calcula el envelope CRIBA (integration_version y
    payload_fingerprint). Interceptamos el POST con MockTransport y capturamos
    el cuerpo real; luego ese mismo cuerpo se envia por HTTP de verdad contra
    el servidor en subproceso. El camino de red queda intacto: solo la CAPTURA
    es sintetica.
    """
    from criba.integrations.supra_client import SupraClient, SupraClientConfig

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "status": "success",
                "stage": "RECEIVED",
                "project_id": project_id,
                "posture": {"project_id": project_id, "stage": "RECEIVED"},
            },
        )

    with SupraClient(
        SupraClientConfig(endpoint="https://capture.invalid"), transport=httpx.MockTransport(handler),
    ) as client:
        try:
            client.run_project(
                objective=objective, domain="criba_blackforge", project_id=project_id,
                criba_dossier=dossier,
            )
        except Exception:
            pass
    assert captured, "no se capturo el payload de creacion"
    return captured


@pytest.fixture
def supra(tmp_path: Path) -> "_RealSupra":
    server = _RealSupra(tmp_path / "supra_state_m4")
    server.storage.mkdir(parents=True, exist_ok=True)
    server.start()
    try:
        yield server
    finally:
        server.stop()


def _real_dossier() -> dict:
    """Dossier CRIBA real: activate() -> preparar_dossier_desde_idea().

    Camino real del test M2. No inventa entry, no rellena campos.
    """
    idea = activate(PROBLEM)["innovation"]["ideas"][0]
    dossier = preparar_dossier_desde_idea(idea, PROBLEM)

    # Invariantes del gate epistemologico sobre el schema vivo.
    # El causal_claim se valida sobre la idea real (input de CRIBA), no sobre
    # el dossier: preparar_dossier no expone causal_claim en su raiz verificada
    # por inspeccion estatica de supra_dossier.py:347-367.
    assert idea["causal_claim"] == "MECHANISM_PROPOSED_UNVALIDATED"
    assert dossier["candidate_id"] == idea["id"]
    assert dossier["estado"] == "SUPRA_EJECUCION_PENDIENTE"
    prueba = dossier["prueba_discriminante"]
    assert prueba["estado_prueba"] == "NO_EJECUTADA"
    assert prueba["alternativa_explicativa"] == idea["broken_assumption"].strip()
    assert prueba["alternativa_explicativa"], "rival/alternative no debe ser vacio"
    return dossier


# ---------------------------------------------------------------------------
# Test principal M4: discriminant dossier survives SUPRA roundtrip
# ---------------------------------------------------------------------------
def test_discriminant_dossier_survives_supra_roundtrip(supra: _RealSupra) -> None:
    """dossier CRIBA real -> SUPRA HTTP -> persiste -> GET tras restart -> campos identicos."""
    dossier = _real_dossier()

    # CRIBA -> SUPRA -> persistencia (real, disco) via cliente HTTP real.
    with SupraClient(SupraClientConfig(endpoint=supra.endpoint)) as client:
        client.run_project(
            objective=dossier["hipotesis"],
            domain="criba_blackforge",
            project_id=dossier["candidate_id"],
            criba_dossier=dossier,
        )

    # GET tras restart real (proceso muerto y relanzado, cache vacia).
    supra.restart()
    with SupraClient(SupraClientConfig(endpoint=supra.endpoint)) as client:
        lookup = client.get_project(dossier["candidate_id"])

    receipt = lookup.posture.criba_dossier_receipt
    assert receipt is not None, "dossier receipt perdido en persistencia"

    receipt_dict = receipt.model_dump()

    # candidate_id y lineage identicos (no sobreescritos por duplicate).
    assert receipt_dict["criba_candidate_id"] == dossier["candidate_id"]
    assert receipt_dict["criba_dossier_id"] == dossier["dossier_id"]
    assert receipt_dict["claim_id"] == dossier["claim_id"]
    assert receipt_dict["mechanism_version"] == dossier["mechanism_version"]
    assert receipt_dict["protocol_version"] == dossier["protocol_version"]

    # rival/alternative sobrevive serializacion + transporte + persistencia.
    assert receipt_dict["alternativa_explicativa"] == dossier["prueba_discriminante"]["alternativa_explicativa"], (
        "rival/alternative se perdio o muto en el roundtrip"
    )

    # Campos discriminantes identicos campo a campo.
    prueba = dossier["prueba_discriminante"]
    for campo in [
        "intervencion_prueba",
        "observable",
        "resultado_favorable_mecanismo",
        "resultado_favorable_alternativa",
        "regla_decision",
        "condicion_fracaso",
    ]:
        assert receipt_dict[campo] == prueba[campo], f"{campo} mutado en roundtrip"

    # NOT_EXECUTED no se promueve a EXECUTED (PERSISTED != EXECUTED).
    assert receipt.execution_status == "NOT_EXECUTED", (
        "NOT_EXECUTED promovido a estado distinto"
    )
    assert receipt.scientific_status == "NOT_VALIDATED"

    # Estado del dossier preservado.
    assert lookup.scientific_status == "NOT_VALIDATED", "scientific_status promovido"


def test_m4_rejects_duplicate_id_different_payload(supra: _RealSupra) -> None:
    """same ID / different objective -> rechazo explicito (409, no sobreescritura)."""
    dossier_a = _real_dossier()
    with SupraClient(SupraClientConfig(endpoint=supra.endpoint)) as client:
        client.run_project(
            objective=dossier_a["hipotesis"],
            domain="criba_blackforge",
            project_id=dossier_a["candidate_id"],
            criba_dossier=dossier_a,
        )

    # El mismo project_id con objective DIFERENTE debe dar 409 sin sobrescribir.
    resp = supra.create(_exact_create_payload(
        "Objetivo distinto que no debe reemplazar al primero",
        dossier_a["candidate_id"],
        dossier_a,
    ))
    assert resp.status_code == 409, resp.text[:400]

    # El payload original sigue intacto tras el rechazo.
    after = supra.get(dossier_a["candidate_id"]).json()
    assert after["posture"]["objective"] == dossier_a["hipotesis"], (
        "sobreescribio el payload original tras duplicate ID"
    )


def test_m4_temporal_order_does_not_leak(supra: _RealSupra) -> None:
    """Un dossier posterior no contamina el anterior (no leakage)."""
    earlier = _real_dossier()
    earlier["candidate_id"] = "candidate-earlier-m4"
    later = _real_dossier()
    later["candidate_id"] = "candidate-later-m4"

    with SupraClient(SupraClientConfig(endpoint=supra.endpoint)) as client:
        client.run_project(
            objective=earlier["hipotesis"],
            domain="criba_blackforge",
            project_id=earlier["candidate_id"],
            criba_dossier=earlier,
        )
        client.run_project(
            objective=later["hipotesis"],
            domain="criba_blackforge",
            project_id=later["candidate_id"],
            criba_dossier=later,
        )

    recovered = supra.get(earlier["candidate_id"]).json()
    blob = json.dumps(recovered)
    assert "candidate-later-m4" not in blob, "leakage: dossier posterior en el anterior"
    receipt = recovered["posture"]["criba_dossier_receipt"]
    assert receipt["criba_dossier_id"] == earlier["dossier_id"]
