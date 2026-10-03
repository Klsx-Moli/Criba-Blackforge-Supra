"""E2E del circuito de interpretación con el intérprete externo real.

Shadow -> generación -> interpretación externa -> contrato -> dossier ->
SupraClient -> POST a SUPRA -> persistencia -> GET -> readback.

Usa el proxy Hermes de verdad (sin llave en el cliente) y un SUPRA real en
proceso. Si algo del circuito no se alcanza, el test lo dice por borde y no
pasa por alto el hueco.

Variables de entorno opcionales:
  CRIBA_EXTERNAL_BASE_URL, CRIBA_EXTERNAL_MODEL, CRIBA_E2E_PROBLEM
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.integration


def _externa_configurada() -> tuple[bool, str]:
    base = os.getenv("CRIBA_EXTERNAL_BASE_URL", "http://127.0.0.1:8642/v1")
    model = os.getenv("CRIBA_EXTERNAL_MODEL", "hermes-agent")
    try:
        resp = httpx.get(
            f"{base}/models", timeout=6.0, headers={"Authorization": "Bearer sin-credencial"}
        )
        if resp.status_code != 200:
            return False, f"/models respondio HTTP {resp.status_code} en {base}"
        ids = [m.get("id") for m in resp.json().get("data", [])]
        if model not in ids:
            return False, f"el modelo {model!r} no esta en el catalogo de {base}"
        return True, f"{base} con {model}"
    except Exception as exc:  # noqa: BLE001
        return False, f"no hay interprete externo en {base}: {type(exc).__name__}"


@pytest.fixture(scope="module")
def interprete_externo():
    listo, motivo = _externa_configurada()
    if not listo:
        pytest.skip(f"interprete externo no disponible: {motivo}")
    from criba.interprete.seleccion import construir_interprete

    interprete = construir_interprete("openai_compatible")
    operativo, por_que = interprete.operativo()
    assert operativo, f"el interprete deberia estar operativo: {por_que}"
    return interprete


def test_interprete_externo_produce_una_propuesta_real(interprete_externo):
    """BORDE 1: el intérprete se llama y devuelve PROPUESTA con mecanismo."""
    idea = {
        "title": "cruce prueba",
        "method1": "principio de contradiccion",
        "method2": "separacion temporal",
        "description": "d",
    }
    resultado = interprete_externo.proponer(
        "reducir el consumo de agua en el riego agricola", idea, {"title": "agricultura"}, []
    )

    assert resultado.es_propuesta, (
        f"no hubo PROPUESTA: estado={resultado.estado} error={resultado.motivo_real()}"
    )
    assert resultado.mecanismo.strip(), "una PROPUESTA sin mecanismo no es propuesta"
    prov = resultado.provenance
    assert prov is not None and prov.request_id
    assert prov.duration_ms > 0
    assert prov.raw_output_sha256
    assert prov.endpoint.startswith("http"), "el endpoint debe quedar registrado"
    assert "Bearer" not in prov.sin_secretos()["endpoint"]


def test_servicio_inventar_llega_a_dossier_desarrollable(interprete_externo, tmp_path):
    """BORDE 2->3: con interprete alcanzable hay PROPUESTAS y dossier posible."""
    from criba.inventar import invent

    sheet = invent("reducir el consumo de agua en el riego agricola")
    entries = sheet.get("entries", [])
    assert entries, "invent no produjo entradas"
    propuestas = [e for e in entries if e.get("estado_interpretacion") == "PROPUESTA"]
    assert propuestas, "cero propuestas desarrollables: " + str(
        {e.get("interpretacion_error") for e in entries}
    )
    assert all(e.get("mecanismo") for e in propuestas), "PROPUESTA sin mecanismo"
    # El ledger lo anexa la capa de UI (actions._run_inventar), no invent().
    assert sheet.get("totals"), "la ficha debe traer sus totales"


def test_dossier_post_persistencia_y_get_con_supra_real(interprete_externo, tmp_path):
    """BORDE 4->8: dossier -> SupraClient -> POST -> persistencia -> GET.

    SUPRA corre como SUBPROCESO con su propio interprete, igual que en el E2E
    de M2: cada componente se levanta bajo el Python que es dueño de su paquete.
    No hay TestClient ni MockTransport: el dossier que se lee es el que cruzo
    la red de verdad.
    """
    import socket
    import subprocess
    import time

    from criba.integrations.supra_client import (
        SupraClient,
        SupraClientConfig,
        objective_from_dossier,
    )
    from criba.inventar import invent
    from criba.supra_dossier import guardar_dossier, preparar_dossier

    repo = Path(__file__).resolve().parents[2]
    supra_src = repo.parent / "supra" / "src"
    supra_python = repo.parent / "supra" / ".venv" / "Scripts" / "python.exe"
    if not supra_python.is_file():
        pytest.skip("venv de SUPRA ausente: el componente real no se puede lanzar")

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    endpoint = f"http://127.0.0.1:{port}"
    storage = tmp_path / "supra_state"
    storage.mkdir(parents=True, exist_ok=True)
    log = (tmp_path / "uvicorn.log").open("a", encoding="utf-8")

    proc = subprocess.Popen(
        [
            str(supra_python),
            "-m",
            "uvicorn",
            "supra_agentic.service:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(repo.parent / "supra"),
        stdout=log,
        stderr=subprocess.STDOUT,
        env={
            **os.environ,
            "PYTHONPATH": str(supra_src),
            "SUPRA_STORAGE_DIR": str(storage),
            "SUPRA_USE_MODEL": "false",
        },
    )
    try:
        for _ in range(90):
            try:
                if httpx.get(f"{endpoint}/health", timeout=3).status_code == 200:
                    break
            except Exception:
                pass
            if proc.poll() is not None:
                pytest.fail(
                    "el proceso de SUPRA murio al arrancar:\n"
                    + (tmp_path / "uvicorn.log").read_text(encoding="utf-8")[-1500:]
                )
            time.sleep(1.0)
        else:
            pytest.fail("SUPRA real no respondio /health")

        os.environ["SUPRA_STORAGE_DIR"] = str(storage)
        sheet = invent("reducir el consumo de agua en el riego agricola")
        propuestas = [
            e for e in sheet.get("entries", []) if e.get("estado_interpretacion") == "PROPUESTA"
        ]
        assert propuestas, "sin propuestas: el dossier no se puede construir"

        # BORDE 4: dossier real a partir de una propuesta real
        dossier = preparar_dossier(
            propuestas[0],
            sheet["query"],
            ficha_bloqueo={"title": "agricultura"},
        )
        assert isinstance(dossier, dict) and dossier
        ruta = guardar_dossier(dossier, tmp_path / "dossiers")
        assert Path(ruta).is_file(), "el dossier no se guardo en disco"

        # BORDE 5+6: SupraClient -> POST real
        cliente = SupraClient(SupraClientConfig(endpoint=endpoint))
        proyecto = cliente.run_project(
            objective=objective_from_dossier(dossier),
            domain="criba_blackforge",
            allow_disruptive=True,
            criba_dossier=dossier,
        )
        project_id = proyecto.project_id
        assert project_id, f"la creacion no devolvio project_id: {proyecto!r}"

        # BORDE 7: persistencia real en SUPRA
        listado = cliente.list_projects()
        assert any(p.get("project_id") == project_id for p in listado.projects), (
            "el proyecto no aparece en la lista de SUPRA: no se persistio"
        )

        # BORDE 8: GET / readback
        leido = cliente.get_project(project_id)
        volcado = leido.model_dump()
        assert volcado, "el readback vino vacio"
        assert leido.project_id == project_id
        assert leido.status_source in {"PERSISTED_STATE", "IN_PROCESS_MEMORY_CACHE"}
        assert leido.persisted_artifact_status in {
            "VERIFIED_FROM_ARTIFACT",
            "MATCHES_CACHE",
        }

        # Y el artefacto existe en disco, no solo en memoria
        artefactos = list(storage.glob(f"{project_id}.json"))
        assert artefactos, f"no hay artefacto persistido para {project_id} en {storage}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:  # pragma: no cover - cleanup guard
            proc.kill()
        log.close()
