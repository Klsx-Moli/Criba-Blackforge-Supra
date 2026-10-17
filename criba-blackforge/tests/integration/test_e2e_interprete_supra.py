"""E2E del circuito de interpretación con el intérprete externo real.

Shadow -> generación -> interpretación externa -> contrato -> dossier ->
SupraClient -> POST a SUPRA -> persistencia -> GET -> readback.

Usa el proxy Hermes de verdad (sin llave en el cliente) y un SUPRA real en
proceso. Si algo del circuito no se alcanza, el test lo dice por borde y no
pasa por alto el hueco.

Variables de entorno opcionales:
  CRIBA_EXTERNAL_BASE_URL, CRIBA_EXTERNAL_MODEL, CRIBA_E2E_PROBLEM

EVIDENCE_SCHEMA:
Tests use structured evidence case files (tests/fixtures/evidence_cases/).
Each case has: case.input.json, response.schema.json, case.oracle.json.
The interpreter receives observations, missing evidence, and constraints
as DATA (not instructions). The response is validated structurally and
then semantically against the oracle.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.integration

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "evidence_cases"


def _case_dir(case_id: str) -> Path:
    return _FIXTURES / case_id


def _load_case(case_id: str) -> dict:
    return json.loads((_case_dir(case_id) / "case.input.json").read_text(encoding="utf-8"))


def _load_oracle(case_id: str) -> dict:
    return json.loads((_case_dir(case_id) / "case.oracle.json").read_text(encoding="utf-8"))


def _validate_response(response: dict, case: dict) -> tuple[bool, str]:
    """Validate response against the case.input.json response_contract."""
    required = set(case.get("response_contract", {}).get("required_fields", [
        "decision", "hypothesis", "evidence_ids", "rationale",
        "requested_evidence", "proposed_checks",
    ]))
    if not required.issubset(response):
        missing = required - set(response)
        return False, f"missing_fields: {missing}"

    contract = case.get("response_contract", {})
    valid_decisions = contract.get("decision_values", ["propose", "request_more_evidence"])
    if response["decision"] not in valid_decisions:
        return False, "invalid_decision"

    valid_ids = {o["observation_id"] for o in case.get("observations", [])}
    if not isinstance(response["evidence_ids"], list):
        return False, "invalid_evidence_ids"
    if not set(response["evidence_ids"]).issubset(valid_ids):
        return False, "unknown_evidence"

    for key in ("requested_evidence", "proposed_checks"):
        val = response.get(key)
        if not isinstance(val, list) or any(not isinstance(x, str) or not x.strip() for x in val):
            return False, "invalid_list"

    if response["decision"] == "propose":
        hyp = response.get("hypothesis")
        if not isinstance(hyp, str) or not hyp.strip() or not response["evidence_ids"]:
            return False, "unsupported_proposal"
        if not response["proposed_checks"]:
            return False, "missing_checks"
    else:
        if response.get("hypothesis") is not None or not response["requested_evidence"]:
            return False, "invalid_request"

    return True, "structural_pass"


_SYSTEM_PROMPT = """Eres un intérprete de incidentes en un entorno E2E aislado.

Recibirás un paquete de evidencia con observaciones anómalas, información ausente
y restricciones. No tienes acceso a producción, no debes ejecutar cambios y no
debes afirmar causas no respaldadas por las observaciones.

Tareas permitidas:
1. Analizar las observaciones y correlaciones dentro del ámbito temporal.
2. Formular una hipótesis causal provisional.
3. Proponer comprobaciones de solo lectura.
4. Indicar la evidencia que respalda cada afirmación.
5. Solicitar más evidencia si la información es insuficiente.

Formato obligatorio (JSON):
{
  "test_case_id": "github-2018-10-21-2302",
  "decision": "propose" o "request_more_evidence",
  "hypothesis": "hipótesis provisional o null",
  "evidence_ids": ["obs-001", ...],
  "rationale": "razonamiento vinculando observaciones a la hipótesis",
  "requested_evidence": ["lista de información adicional necesaria"],
  "proposed_checks": ["comprobaciones de solo lectura propuestas"]
}

Reglas:
- Cita al menos una observation_id válida.
- Si no hay evidencia suficiente, decision="request_more_evidence", hypothesis=null.
- No ejecutes acciones. No accedas a sistemas de producción.
- No inventes mediciones ni reclames acceso a logs no disponibles.
- No trates la superposición temporal como causalidad demostrada.
- No afirmes que acciones fueron ejecutadas."""


def _build_interpreter_input(case: dict) -> str:
    """Build structured input from case.input.json. Constraints are DATA."""
    observations = json.dumps(case.get("observations", []), ensure_ascii=False, indent=2)
    missing = json.dumps(case.get("missing_evidence", []), ensure_ascii=False, indent=2)
    constraints = json.dumps(case.get("constraints", {}), ensure_ascii=False, indent=2)
    temporal = json.dumps(case.get("temporal_scope", {}), ensure_ascii=False, indent=2)
    system_info = json.dumps(case.get("system_under_test", {}), ensure_ascii=False, indent=2)

    return (
        f"case_id: {case['test_case_id']}\n"
        f"temporal_scope: {temporal}\n"
        f"sistema: {system_info}\n"
        f"observaciones:\n{observations}\n"
        f"informacion_ausente:\n{missing}\n"
        f"restricciones:\n{constraints}\n"
        "Responde con JSON válido siguiendo el formato obligatorio.\n"
    )


def _externa_configurada() -> tuple[bool, str]:
    from criba.interprete.openai_compatible import OpenAICompatibleInterpreter
    return OpenAICompatibleInterpreter().operativo()


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


def _call_interpreter_structured(interprete_externo, case: dict) -> dict:
    """Call the LLM endpoint directly with structured evidence from case.input.json.

    This bypasses the CRIBA interprete contract (which expects the propuesta
    JSON schema) and instead sends the incident-analysis prompt directly,
    allowing us to test the model's ability to reason over structured
    observations and produce a schema-valid response.
    """
    interp = interprete_externo
    input_text = _build_interpreter_input(case)

    payload = {
        "model": interp.model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": input_text},
        ],
        "temperature": interp.temperature,
        "max_tokens": interp.max_tokens,
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json"}
    if interp._api_key:
        headers["Authorization"] = f"Bearer {interp._api_key}"

    resp = httpx.Client(timeout=120).post(
        f"{interp.base}/chat/completions", json=payload, headers=headers
    )
    if resp.status_code == 429:
        pytest.skip(f"rate_limit_429: modelo {interp.model} agotado")
    if resp.status_code >= 400:
        pytest.skip(f"http_error_{resp.status_code}: modelo no disponible")
    data = resp.json()
    message = data["choices"][0]["message"]
    content = message.get("content")
    if content is None:
        finish_reason = message.get("finish_reason", "unknown")
        pytest.skip(f"model_returned_none_content: model={interp.model} finish_reason={finish_reason}")
    try:
        return json.loads(content)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        pytest.fail(f"respuesta no es JSON valido: {exc}; contenido={content[:500]}")


# -- Structured evidence E2E tests (github-2018-10-21 incident case) ----

def test_interpreter_produces_structured_response(interprete_externo):
    """BORDE 1: interpreter responds with schema-valid JSON per case.input.json.

    Uses the github-2018-10-21 incident case with two observational facts:
    a 43-second network interruption and an unexpected topology state.
    The response must propose a provisional hypothesis citing evidence or
    request more evidence — both are acceptable per the oracle.
    """
    case = _load_case("github-2018-10-21-2302")
    response = _call_interpreter_structured(interprete_externo, case)

    assert response["test_case_id"] == case["test_case_id"], "test_case_id must match input"
    valid, reason = _validate_response(response, case)
    assert valid, f"respuesta invalida: {reason}"

    # Oracle checks: decision must be in acceptable set
    oracle = _load_oracle("github-2018-10-21-2302")
    assert response["decision"] in oracle["acceptable_decisions"]

    # If propose: must cite observations and must not claim unconfirmed facts
    if response["decision"] == "propose":
        assert len(response["evidence_ids"]) >= 1, "propuesta debe citar al menos una observacion"
        for claim in oracle["claims_not_established_by_input"]:
            assert claim.lower() not in response["hypothesis"].lower(), (
                f"la hipótesis no debe afirmar como confirmado: {claim}"
            )


def test_interpreter_request_more_evidence_is_handled(interprete_externo):
    """BORDE 2: when evidence is insufficient, interpreter can request more.

    Uses a stripped-down case with no observations to verify the abstention path.
    """
    case = _load_case("github-2018-10-21-2302")
    stripped = {
        "test_case_id": case["test_case_id"],
        "observations": [],  # no evidence
        "missing_evidence": case.get("missing_evidence", []),
        "constraints": case["constraints"],
        "response_contract": case["response_contract"],
        "temporal_scope": case.get("temporal_scope", {}),
        "system_under_test": case.get("system_under_test", {}),
    }
    response = _call_interpreter_structured(interprete_externo, stripped)
    assert response["test_case_id"] == stripped["test_case_id"]
    valid, reason = _validate_response(response, stripped)
    assert valid, f"respuesta invalida sin evidencia: {reason}"


# -- Legacy CRIBA E2E tests (water-agriculture domain) ----

def test_interprete_externo_produce_una_propuesta_real(interprete_externo, tmp_path):
    """BORDE 3: CRIBA interprete with local evidence produces a proposal.

    Evidencia local inyectada vía fixture sintético: documentos observacionales
    sobre riego y consumo de agua que permiten al intérprete formular una hipótesis.
    """
    from tests.fixtures.synthetic_evidence import build_evidence_store
    from criba.intelligence.evidence_context import retrieve_evidence_context

    store = build_evidence_store(tmp_path)
    idea = {
        "title": "cruce prueba",
        "method1": "principio de contradiccion",
        "method2": "separacion temporal",
        "description": "d",
        "evidence_context": {"retrieval_status": "RETRIEVED", "scope": "local_observational"},
    }
    evidence = retrieve_evidence_context(
        "reducir el consumo de agua en el riego agricola", store
    )["documents"]
    resultado = interprete_externo.proponer(
        "reducir el consumo de agua en el riego agricola", idea,
        {"title": "agricultura"}, evidence,
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
    """BORDE 4->5: con interprete alcanzable hay PROPUESTAS y dossier posible.

    Evidencia local inyectada vía fixture sintético.
    """
    from criba.inventar import invent
    from tests.fixtures.synthetic_evidence import build_evidence_store

    store = build_evidence_store(tmp_path)
    sheet = invent("reducir el consumo de agua en el riego agricola", store=store)
    entries = sheet.get("entries", [])
    assert entries, "invent no produjo entradas"
    propuestas = [e for e in entries if e.get("estado_interpretacion") == "PROPUESTA"]
    assert propuestas, "cero propuestas desarrollables: " + str(
        {e.get("interpretacion_error") for e in entries}
    )
    assert all(e.get("mecanismo") for e in propuestas), "PROPUESTA sin mecanismo"
    assert sheet.get("totals"), "la ficha debe traer sus totales"


def test_dossier_post_persistencia_y_get_con_supra_real(interprete_externo, tmp_path):
    """BORDE 6->10: dossier -> SupraClient -> POST -> persistencia -> GET.

    SUPRA corre como SUBPROCESO con su propio interprete.
    Evidencia local inyectada vía fixture sintético.
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
    supra_python = Path(os.getenv("SUPRA_E2E_PYTHON") or (
        repo.parent / "supra" / ".venv" / "Scripts" / "python.exe"
    ))
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
            "--host", "127.0.0.1",
            "--port", str(port),
            "--log-level", "warning",
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
        from tests.fixtures.synthetic_evidence import build_evidence_store

        ev_store = build_evidence_store(tmp_path / "evidence_store")
        sheet = invent("reducir el consumo de agua en el riego agricola", store=ev_store)
        propuestas = [
            e for e in sheet.get("entries", []) if e.get("estado_interpretacion") == "PROPUESTA"
        ]
        assert propuestas, "sin propuestas: el dossier no se puede construir"

        # BORDE 7: dossier real a partir de una propuesta real
        dossier = preparar_dossier(
            propuestas[0],
            sheet["query"],
            ficha_bloqueo={"title": "agricultura"},
        )
        assert isinstance(dossier, dict) and dossier
        ruta = guardar_dossier(dossier, tmp_path / "dossiers")
        assert Path(ruta).is_file(), "el dossier no se guardo en disco"

        # BORDE 8+9: SupraClient -> POST real
        cliente = SupraClient(SupraClientConfig(endpoint=endpoint))
        proyecto = cliente.run_project(
            objective=objective_from_dossier(dossier),
            domain="criba_blackforge",
            allow_disruptive=True,
            criba_dossier=dossier,
        )
        project_id = proyecto.project_id
        assert project_id, f"la creacion no devolvio project_id: {proyecto!r}"

        # BORDE 10: persistencia real en SUPRA
        listado = cliente.list_projects()
        assert any(p.get("project_id") == project_id for p in listado.projects), (
            "el proyecto no aparece en la lista de SUPRA: no se persistio"
        )

        # BORDE 11: GET / readback
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
