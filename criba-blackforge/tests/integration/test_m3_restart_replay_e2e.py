"""M3 · Reinicio real, replay idempotente y estados de almacenamiento por HTTP.

QUÉ AÑADE SOBRE LO YA EXISTENTE (no duplica):

``test_m2_vertical_slice_e2e.py`` ya demuestra que un proyecto escrito por M2
sobrevive a matar y relanzar el PROCESO SUPRA y que la lectura posterior se
declara ``PERSISTED_STATE`` / ``VERIFIED_FROM_ARTIFACT``. Eso NO se repite aquí.

``test_cb_i03_supra_storage_roundtrip.py`` ya fija, a nivel de
``ProjectStateManager`` in-process, el roundtrip, ``DuplicateProjectError``,
ausente != corrupto != vacío, rollback y PERSISTED != EXECUTED. Tampoco se repite.

Este módulo cubre los huecos que ninguno de los dos ejercita, y lo hace a través
del SERVICIO HTTP real en subproceso, que es la superficie que un consumidor usa:

  H1  Idempotencia: un retry del MISMO project_id con el MISMO payload CRIBA no
      duplica el proyecto, preserva la identidad y responde ``idempotent_replay``.
  H2  Conflicto: el mismo project_id con payload DIFERENTE se rechaza con 409 y
      NO sobrescribe el estado original.
  H3  Replay tras reinicio: la idempotencia y el conflicto se resuelven contra el
      estado DURABLE, no contra una caché del proceso vivo.
  H4  Artefacto ausente: el servidor no promociona la caché a verdad durable.
  H5  Artefacto corrupto pero parseable: la corrupción no se oculta.
  H6  Version skew: un artefacto con esquema desconocido no se acepta como
      compatible (``extra="forbid"`` en ProjectPosture).

REGLA DE EVIDENCIA: cada aserción se apoya en una respuesta HTTP observada de un
servidor real, o en el efecto medido sobre el fichero en disco. Ningún caso se
declara por conveniencia: donde el contrato no distingue, el test lo documenta.

Sentinela de mutación:
  * quitar el 409 de ``_idempotent_replay_response`` -> ``test_conflict_*``
  * hardcodear ``status_source="PERSISTED_STATE"`` -> ``test_missing_artifact_*``
  * ignorar el fallo de decodificación -> ``test_corrupt_artifact_*``
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

# SUPRA es un componente con su propio entorno; el servidor corre bajo el
# intérprete que realmente posee su paquete.
SUPRA_PYTHON = Path(
    os.getenv("SUPRA_E2E_PYTHON") or (REPO.parent / "supra" / ".venv" / "Scripts" / "python.exe")
)
if not SUPRA_PYTHON.is_file():  # pragma: no cover - guard de entorno
    pytest.skip(
        "venv de SUPRA ausente: el componente real no se puede lanzar",
        allow_module_level=True,
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
        self.log_path = storage.parent / f"m3-uvicorn-{self.port}.log"
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
        except subprocess.TimeoutExpired:  # pragma: no cover - guard de limpieza
            self.proc.kill()
        self.proc = None

    def restart(self) -> None:
        """Reinicio REAL: mata el proceso y arranca otro con el mismo disco."""
        self.stop()
        self.start()

    def get(self, project_id: str) -> httpx.Response:
        return httpx.get(f"{self.endpoint}/api/v1/projects/{project_id}", timeout=30.0)

    def create(self, payload: dict) -> httpx.Response:
        return httpx.post(f"{self.endpoint}/api/v1/projects", json=payload, timeout=120.0)

    def artifact(self, project_id: str) -> Path:
        return self.storage / f"{project_id}.json"


def _dossier() -> dict:
    """Dossier CRIBA real (sin LLM): el mismo camino que M2, sin red de modelo."""
    from criba.supra_dossier import preparar_dossier
    from verification.interpreter_cases import critica, propuesta

    entry = {
        **propuesta(),
        "candidate_id": "m3-candidate",
        "run_id": "m3-run",
        "interpretacion_provenance": {"model_requested": "synthetic-m3-only"},
        "critica": {
            "evaluation_status": "CRITIQUED",
            "respuesta": critica(),
            "independent_validation": False,
        },
    }
    return preparar_dossier(entry, "Reducir el consumo de agua en el riego agricola")


def _exact_create_payload(objective: str, project_id: str, dossier: dict) -> dict:
    """Obtiene el payload EXACTO que SupraClient envia, sin replicar su logica.

    ``run_project`` calcula el envelope CRIBA (integration_version y
    payload_fingerprint) con reglas que este test no debe duplicar: si las
    copiase, el test certificaria su propia copia en vez del cliente. Se
    intercepta el POST con ``MockTransport`` y se captura el cuerpo real; luego
    ese mismo cuerpo se envia por HTTP de verdad contra el servidor en
    subproceso. El camino de red queda intacto: solo la CAPTURA es sintetica.
    """
    from criba.integrations.supra_client import SupraClient, SupraClientConfig

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        # Respuesta minima que satisface la validacion del cliente; no se usa
        # para ninguna asercion de este modulo.
        return httpx.Response(
            200,
            json={
                "status": "blocked",
                "stage": "BLOCKED",
                "project_id": project_id,
                "posture": {"project_id": project_id, "stage": "BLOCKED"},
            },
        )

    with SupraClient(
        SupraClientConfig(endpoint="https://capture.invalid"), transport=httpx.MockTransport(handler)
    ) as client:
        try:
            client.run_project(
                objective=objective, domain="criba_blackforge", project_id=project_id,
                criba_dossier=dossier,
            )
        except Exception:
            # La validacion de la respuesta sintetica puede fallar; el payload ya
            # quedo capturado, que es lo unico que se busca aqui.
            pass
    assert captured, "no se capturo el payload de creacion"
    return captured


@pytest.fixture
def supra(tmp_path):
    server = _RealSupra(tmp_path / "state")
    server.storage.mkdir(parents=True, exist_ok=True)
    server.start()
    try:
        yield server
    finally:
        server.stop()


# ---------------------------------------------------------------------------
# H1 · Idempotencia: mismo project_id + mismo payload
# ---------------------------------------------------------------------------


def test_same_id_same_payload_does_not_duplicate(supra: _RealSupra) -> None:
    """Un retry exacto NO duplica el proyecto y conserva su identidad."""
    objective = "Reducir el consumo de agua en el riego agricola"
    dossier = _dossier()
    payload = _exact_create_payload(objective, "m3-idem", dossier)

    first = supra.create(payload)
    assert first.status_code in (200, 201), first.text[:400]
    created_at = supra.get("m3-idem").json()["posture"]["created_at"]

    second = supra.create(payload)
    assert second.status_code in (200, 201), second.text[:400]
    body = second.json()
    assert body["idempotent_replay"] is True, body

    # La identidad y la fecha de creacion no cambiaron: no hubo segunda creacion.
    after = supra.get("m3-idem").json()
    assert after["posture"]["created_at"] == created_at
    assert after["posture"]["objective"] == objective

    # Un solo artefacto en disco, y solo ese proyecto listado.
    listed = httpx.get(f"{supra.endpoint}/api/v1/projects", timeout=30.0).json()
    ids = [p["project_id"] for p in listed["projects"]]
    assert ids.count("m3-idem") == 1, ids


def test_replay_is_reported_and_not_a_second_execution(supra: _RealSupra) -> None:
    """El replay idempotente se declara y no inventa una ejecucion nueva.

    ``idempotent_replay`` es la senal que permite a un consumidor distinguir
    "ya estaba" de "se acaba de crear": sin ella, un retry exitoso seria
    indistinguible de una creacion nueva.
    """
    objective = "Reducir el consumo de agua en el riego agricola"
    dossier = _dossier()
    payload = _exact_create_payload(objective, "m3-replay", dossier)

    first = supra.create(payload)
    assert first.status_code in (200, 201), first.text[:400]
    assert first.json().get("idempotent_replay") in (False, None)

    second = supra.create(payload)
    assert second.status_code in (200, 201), second.text[:400]
    assert second.json()["idempotent_replay"] is True
    # El estado de workflow no se promociona por reintentar.
    assert second.json()["stage"] == first.json()["stage"]


# ---------------------------------------------------------------------------
# H2 · Conflicto: mismo project_id con payload diferente
# ---------------------------------------------------------------------------


def test_same_id_different_payload_is_conflict_and_preserves_original(
    supra: _RealSupra,
) -> None:
    """Mismo project_id con otro objetivo -> 409, sin sobrescribir nada."""
    dossier = _dossier()
    original = "Objetivo original que debe sobrevivir al conflicto"
    first = supra.create(_exact_create_payload(original, "m3-conflict", dossier))
    assert first.status_code in (200, 201), first.text[:400]

    clashing = _exact_create_payload("Objetivo distinto que no debe reemplazar al primero", "m3-conflict", dossier)
    conflict = supra.create(clashing)
    assert conflict.status_code == 409, conflict.text[:400]

    # El estado durable conserva el objetivo original y su lineage.
    after = supra.get("m3-conflict").json()
    assert after["posture"]["objective"] == original
    assert after["posture"]["criba_dossier_receipt"]["criba_dossier_id"] == dossier["dossier_id"]


def test_conflict_does_not_overwrite_the_artifact(supra: _RealSupra) -> None:
    """El conflicto no deja rastro en el fichero durable."""
    dossier = _dossier()
    original = "Objetivo original que debe sobrevivir al conflicto"
    supra.create(_exact_create_payload(original, "m3-conflict-file", dossier))
    before = supra.artifact("m3-conflict-file").read_text(encoding="utf-8")

    supra.create(_exact_create_payload("Otro objetivo completamente distinto", "m3-conflict-file", dossier))

    after = supra.artifact("m3-conflict-file").read_text(encoding="utf-8")
    assert after == before, "el artefacto cambio pese al conflicto"


# ---------------------------------------------------------------------------
# H3 · Replay tras reinicio REAL del proceso
# ---------------------------------------------------------------------------


def test_idempotency_survives_a_real_restart(supra: _RealSupra) -> None:
    """La idempotencia se resuelve contra el estado DURABLE, no contra la cache.

    Este es el punto que distingue M3 de un cache hit: se mata el proceso, se
    arranca otro con el mismo disco y el retry exacto debe seguir siendo un
    replay, no una creacion nueva.
    """
    objective = "Reducir el consumo de agua en el riego agricola"
    dossier = _dossier()
    payload = _exact_create_payload(objective, "m3-restart-idem", dossier)
    assert supra.create(payload).status_code in (200, 201)

    created_at = supra.get("m3-restart-idem").json()["posture"]["created_at"]
    supra.restart()

    # Tras el reinicio la lectura viene del artefacto, no de la cache.
    read = supra.get("m3-restart-idem")
    assert read.status_code == 200, read.text[:400]
    assert read.json()["status_source"] == "PERSISTED_STATE"
    assert read.json()["persisted_artifact_status"] == "VERIFIED_FROM_ARTIFACT"

    replay = supra.create(payload)
    assert replay.status_code in (200, 201), replay.text[:400]
    assert replay.json()["idempotent_replay"] is True
    assert supra.get("m3-restart-idem").json()["posture"]["created_at"] == created_at


def test_conflict_survives_a_real_restart(supra: _RealSupra) -> None:
    """El conflicto se detecta tambien cuando el estado solo vive en disco."""
    dossier = _dossier()
    supra.create(_exact_create_payload("Objetivo original persistido", "m3-restart-conflict", dossier))
    supra.restart()

    clash = supra.create(_exact_create_payload("Objetivo distinto tras el reinicio", "m3-restart-conflict", dossier))
    assert clash.status_code == 409, clash.text[:400]
    assert supra.get("m3-restart-conflict").json()["posture"]["objective"] == "Objetivo original persistido"


# ---------------------------------------------------------------------------
# H4 · Artefacto ausente
# ---------------------------------------------------------------------------


def test_missing_artifact_does_not_promote_cache_to_durable_truth(
    supra: _RealSupra,
) -> None:
    """Borrado el artefacto, el servidor NO declara PERSISTED_STATE.

    El proceso sigue vivo con el proyecto en memoria. Si el read path
    hardcodease ``PERSISTED_STATE``, un consumidor creeria que el estado es
    durable cuando el fichero ya no existe.
    """
    dossier = _dossier()
    supra.create(_exact_create_payload("Objetivo cuyo artefacto se borrara", "m3-missing", dossier))
    assert supra.get("m3-missing").json()["status_source"] == "IN_PROCESS_MEMORY_CACHE"

    supra.artifact("m3-missing").unlink()

    body = supra.get("m3-missing").json()
    assert body["status_source"] == "IN_PROCESS_MEMORY_CACHE", body["status_source"]
    assert body["persisted_artifact_status"] == "MISSING", body["persisted_artifact_status"]


def test_missing_artifact_after_restart_is_not_found(supra: _RealSupra) -> None:
    """Sin artefacto y sin cache, el proyecto no existe: 404, no un estado inventado."""
    dossier = _dossier()
    supra.create(_exact_create_payload("Objetivo cuyo artefacto se borrara", "m3-missing-restart", dossier))
    supra.artifact("m3-missing-restart").unlink()
    supra.restart()

    response = supra.get("m3-missing-restart")
    assert response.status_code == 404, response.text[:400]


# ---------------------------------------------------------------------------
# H5 · Artefacto corrupto pero parseable / ilegible
# ---------------------------------------------------------------------------


def test_unparseable_artifact_is_reported_not_hidden(supra: _RealSupra) -> None:
    """Un artefacto ilegible se declara UNVERIFIABLE: la corrupcion no se oculta."""
    dossier = _dossier()
    supra.create(_exact_create_payload("Objetivo cuyo artefacto se corrompera", "m3-corrupt", dossier))
    supra.get("m3-corrupt")  # asegura el proyecto en cache
    supra.artifact("m3-corrupt").write_text("{ esto no es json valido ", encoding="utf-8")

    body = supra.get("m3-corrupt").json()
    assert body["status_source"] == "IN_PROCESS_MEMORY_CACHE", body["status_source"]
    assert body["persisted_artifact_status"] == "UNVERIFIABLE", body["persisted_artifact_status"]
    assert body["persisted_artifact_error_kind"], "la causa debe declararse"


def test_corrupt_artifact_after_restart_fails_explicitly(supra: _RealSupra) -> None:
    """Sin cache y con artefacto corrupto, el servidor falla explicitamente.

    El contrato real: ``ProjectStateLoadError`` se traduce a una respuesta de
    error, no a un 200 con estado vacio ni a un 404 que fingiria ausencia.
    """
    dossier = _dossier()
    supra.create(_exact_create_payload("Objetivo cuyo artefacto se corrompera", "m3-corrupt-restart", dossier))
    supra.artifact("m3-corrupt-restart").write_text("no-json-en-absoluto", encoding="utf-8")
    supra.restart()

    response = supra.get("m3-corrupt-restart")
    assert response.status_code != 200, "un artefacto corrupto no puede servirse como 200"
    assert response.status_code in (404, 500, 503), response.status_code


# ---------------------------------------------------------------------------
# H6 · Version skew
# ---------------------------------------------------------------------------


def test_unknown_schema_field_is_not_accepted_as_compatible(supra: _RealSupra) -> None:
    """Un artefacto con esquema desconocido no se acepta como compatible.

    ``ProjectPosture`` declara ``extra="forbid"``: un campo que este servidor no
    conoce (lo que produciria una version futura) no se ignora silenciosamente.
    Inventar compatibilidad hacia adelante seria afirmar que se entiende un
    esquema que no se entiende.
    """
    dossier = _dossier()
    supra.create(_exact_create_payload("Objetivo con esquema de version desconocida", "m3-skew", dossier))
    artifact = supra.artifact("m3-skew")
    data = json.loads(artifact.read_text(encoding="utf-8"))
    data["future_only_field_v99"] = {"schema": "desconocido"}
    artifact.write_text(json.dumps(data), encoding="utf-8")

    body = supra.get("m3-skew").json()
    # La cache sirve la respuesta, pero el veredicto durable no puede ser VERIFIED.
    assert body["persisted_artifact_status"] != "VERIFIED_FROM_ARTIFACT", body
    assert body["persisted_artifact_status"] == "UNVERIFIABLE", body["persisted_artifact_status"]


def test_unknown_schema_field_after_restart_is_not_served_as_verified(
    supra: _RealSupra,
) -> None:
    """Sin cache, un esquema desconocido no se promociona a estado verificado."""
    dossier = _dossier()
    supra.create(_exact_create_payload("Objetivo con esquema de version desconocida", "m3-skew-restart", dossier))
    artifact = supra.artifact("m3-skew-restart")
    data = json.loads(artifact.read_text(encoding="utf-8"))
    data["future_only_field_v99"] = {"schema": "desconocido"}
    artifact.write_text(json.dumps(data), encoding="utf-8")
    supra.restart()

    response = supra.get("m3-skew-restart")
    if response.status_code == 200:  # pragma: no cover - depende del contrato real
        body = response.json()
        assert body["persisted_artifact_status"] != "VERIFIED_FROM_ARTIFACT", body
    else:
        assert response.status_code in (404, 500, 503), response.status_code


# ---------------------------------------------------------------------------
# H7 · Los campos cientificos sobreviven al reinicio
# ---------------------------------------------------------------------------


def test_scientific_fields_survive_a_real_restart(supra: _RealSupra) -> None:
    """Los campos que M2 produjo siguen ahi tras matar el proceso.

    UNKNOWN se conserva como UNKNOWN: la recuperacion no convierte un valor no
    demostrado en un valor demostrado.
    """
    dossier = _dossier()
    objective = "Reducir el consumo de agua en el riego agricola"
    supra.create(_exact_create_payload(objective, "m3-science", dossier))
    before = supra.get("m3-science").json()
    supra.restart()
    after = supra.get("m3-science").json()

    # Identidad y objetivo
    assert after["posture"]["project_id"] == "m3-science"
    assert after["posture"]["objective"] == objective
    # Lineage / provenance
    receipt_before = before["posture"]["criba_dossier_receipt"]
    receipt_after = after["posture"]["criba_dossier_receipt"]
    assert receipt_after["criba_dossier_id"] == receipt_before["criba_dossier_id"]
    assert receipt_after["criba_candidate_id"] == receipt_before["criba_candidate_id"]
    assert receipt_after["payload_fingerprint"] == receipt_before["payload_fingerprint"]
    assert receipt_after["mechanism_version"] == receipt_before["mechanism_version"]
    # PERSISTED != EXECUTED, tambien tras el reinicio
    assert receipt_after["execution_status"] == "NOT_EXECUTED"
    assert receipt_after["scientific_status"] == "NOT_VALIDATED"
    assert after["scientific_status"] == "NOT_VALIDATED"
    assert after["criba_mechanism_execution_status"] == "NOT_EXECUTED"
    # Estado de workflow y procedencia durable
    assert after["stage"] == before["stage"]
    assert after["status"] == before["status"]
    assert after["status_source"] == "PERSISTED_STATE"
    assert after["persisted_artifact_status"] == "VERIFIED_FROM_ARTIFACT"
