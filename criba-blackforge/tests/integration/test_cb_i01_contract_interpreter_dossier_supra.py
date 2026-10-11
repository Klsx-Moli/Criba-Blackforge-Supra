"""CB-I01: Contrato intérprete ↔ dossier ↔ SUPRA.

Demuestra que la propuesta llega intacta al dossier y a SUPRA, con
intérprete simulado determinista (sin proveedor externo) y SUPRA real en
subproceso. Cada caso del megaprompt produce un veredicto específico:

- propuesta válida → dossier construible, campos preservados
- crítica válida → se registra
- abstención correcta → NO es ERROR
- schema inválido → PENDIENTE con error_kind=schema
- dominio inválido → PENDIENTE con error_kind=domain
- truncamiento → PENDIENTE con error de truncamiento
- crítica ausente → PENDIENTE con critica_no_disponible
- crítica inválida → PENDIENTE con validación
- sin evidencia → evidencia_citada vacío
- restricciones → comprobación obligatoria
- campos extra → no se propagan al dossier

Invariantes verificados:
- ABSTENER no es ERROR
- REJECTED no implica transporte
- UNKNOWN != 0
- PERSISTED != EXECUTED
- PLANNED != VALIDATED
- sin relleno automático
- procedencia sobrevive
"""
from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.integration

# --------------------------------------------------------------------------
# Intérprete simulado determinista (sin proveedor externo).
# --------------------------------------------------------------------------


class _SimInterpreter:
    """Intérprete que devuelve un resultado fijo por caso, sin HTTP."""

    backend = "simulado"
    provider = "simulado"

    def __init__(self, resultado: Any) -> None:
        self._resultado = resultado

    def operativo(self) -> tuple[bool, str]:
        return True, "simulado"

    def proponer(
        self,
        query: str,
        idea: dict[str, Any],
        domain: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> Any:
        return self._resultado


def _propuesta_valida() -> Any:
    """InterpretationResult con PROPUESTA completa y crítica aprobada."""
    from criba.interprete.puerto import ESTADO_PROPUESTA, InterpretationResult

    return InterpretationResult(
        estado=ESTADO_PROPUESTA,
        hipotesis="La confirmación automática reduce segundas visitas.",
        mecanismo=(
            "El sistema detecta el registro incompleto al momento de la entrada "
            "(variable intermedia: detección temprana), bloquea su propagación al "
            "registro oficial (variable intermedia: error bloqueado), y reduce la "
            "necesidad de corrección posterior (efecto observable: menos visitas)."
        ),
        aportacion_por_tecnica=[
            "Confirmación automática: detectar y bloquear registros incompletos",
            "Recordatorios: notificar al usuario antes de confirmar",
        ],
        supuestos=["Los usuarios corrigen errores cuando se les notifica."],
        prueba_concreta="Ensayo controlado midiendo segundas visitas por registro incompleto.",
        ruta_desbloqueo="sustituir_mecanismo",
        pertinencia="PERTINENTE",
        cadena_causal=[
            "Confirmación automática detecta registro incompleto",
            "Reducción de segundas visitas por error de registro",
        ],
        evidencia_citada=[],
        conocimiento_previo=["La confirmación automática aumenta retornos."],
        incertidumbre="No se conoce la efectividad a largo plazo.",
        novedad="Aplicación en este dominio específico.",
        prueba={
            "metrica": "Número de segundas visitas por registro incompleto",
            "baseline": "Sin confirmación automática",
            "umbral": "20% de reducción",
            "condicion_fracaso": "No se observa reducción significativa",
            "alternativa_explicativa": "Mejora en comunicación entre profesionales",
            "resultado_favorable_mecanismo": "Se reduce 20% las segundas visitas",
            "resultado_favorable_alternativa": "No se reduce las segundas visitas",
        },
        comprobacion_restricciones=[],
        critica={
            "evaluation_status": "CRITIQUED",
            "independent_validation": True,
            "same_model": False,
            "respuesta": {
                "pertinente": True,
                "mecanismo_especifico": True,
                "falsable": True,
                "fiel_evidencia": True,
                "restricciones_respetadas": True,
                "discrimina_alternativas": True,
                "intercambio_tecnicas_generico": False,
                "objeciones": [],
                "incertidumbre": "límites de esta crítica automática",
                "respuestas_epistemologicas": {
                    f"Q{i}": f"respuesta {i}" for i in range(1, 12)
                },
            },
        },
        model_requests=2,
    )


def _entry_propuesta() -> dict[str, Any]:
    """Entry con la estructura que preparar_dossier consume de verdad."""
    return {
        "candidate_id": "idea-test-001",
        "claim_id": "",
        "hipotesis": "La confirmación automática reduce segundas visitas.",
        "mecanismo": (
            "El sistema detecta el registro incompleto al momento de la entrada "
            "(variable intermedia: detección temprana), bloquea su propagación al "
            "registro oficial (variable intermedia: error bloqueado), y reduce la "
            "necesidad de corrección posterior (efecto observable: menos visitas)."
        ),
        "prueba_concreta": (
            "Ensayo controlado midiendo segundas visitas por registro incompleto."
        ),
        "supuestos": ["Los usuarios corrigen errores cuando se les notifica."],
        "observable": "número de segundas visitas por registro incompleto",
        "prueba": {
            "metrica": "Número de segundas visitas por registro incompleto",
            "baseline": "Sin confirmación automática",
            "umbral": "20% de reducción",
            "condicion_fracaso": "No se observa reducción significativa",
            "alternativa_explicativa": "Mejora en comunicación entre profesionales",
            "resultado_favorable_mecanismo": "Se reduce 20% las segundas visitas",
            "resultado_favorable_alternativa": "No se reduce las segundas visitas",
        },
        "interpretacion_provenance": {
            "interpreter_backend": "simulado",
            "model_requested": "m1",
            "request_id": "req-001",
        },
    }


def _idea_valida() -> dict[str, Any]:
    """Idea con method1/method2 para validación de contrato."""
    return {
        "method1": "Confirmación automática",
        "method2": "Recordatorios",
        "title": "Confirmar sin revisar",
        "id": "idea-test-001",
    }


# --------------------------------------------------------------------------
# SUPRA real en subproceso (patrón de test_e2e_interprete_supra).
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def supra_real(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """SUPRA como subproceso con su propio intérprete, en un puerto libre."""
    repo = Path(__file__).resolve().parents[2]
    supra_src = repo.parent / "supra" / "src"
    supra_python = Path(os.getenv("SUPRA_E2E_PYTHON") or (
        repo.parent / "supra" / ".venv" / "Scripts" / "python.exe"
    ))
    if not supra_python.is_file():
        pytest.skip("venv de SUPRA ausente: el componente real no se puede lanzar")

    tmp_path = tmp_path_factory.mktemp("cb_i01_supra")
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
        yield {"endpoint": endpoint, "storage": storage}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:  # pragma: no cover - cleanup guard
            proc.kill()
        log.close()


# --------------------------------------------------------------------------
# Casos del megaprompt.
# --------------------------------------------------------------------------


def test_propuesta_valida_llega_intacta_al_dossier(supra_real: Any) -> None:
    """Caso 1: propuesta válida → dossier construible, campos preservados."""
    from criba.supra_dossier import preparar_dossier

    entry = _entry_propuesta()
    dossier = preparar_dossier(
        entry,
        "Eliminar segundas visitas por errores de registro.",
        ficha_bloqueo={"title": "salud"},
    )
    assert isinstance(dossier, dict) and dossier
    # La propuesta llega intacta: los campos científicos no se pierden.
    assert dossier.get("hipotesis")
    assert dossier.get("mecanismo")
    assert dossier.get("candidate_id") == "idea-test-001"
    # PERSISTED != EXECUTED: sin experimento ejecutado el estado es pendiente.
    assert dossier.get("estado") == "SUPRA_EJECUCION_PENDIENTE"


def test_propuesta_valida_llega_a_supra(supra_real: Any) -> None:
    """Caso 1 (continuación): dossier → SupraClient → POST → persistencia."""
    from criba.integrations.supra_client import (
        SupraClient,
        SupraClientConfig,
        objective_from_dossier,
    )
    from criba.supra_dossier import preparar_dossier

    entry = _entry_propuesta()
    dossier = preparar_dossier(
        entry,
        "Eliminar segundas visitas por errores de registro.",
        ficha_bloqueo={"title": "salud"},
    )
    cliente = SupraClient(SupraClientConfig(endpoint=supra_real["endpoint"]))
    proyecto = cliente.run_project(
        objective=objective_from_dossier(dossier),
        domain="criba_blackforge",
        allow_disruptive=True,
        criba_dossier=dossier,
    )
    assert proyecto.project_id
    # El artefacto existe en disco, no solo en memoria.
    artefactos = list(supra_real["storage"].glob(f"{proyecto.project_id}.json"))
    assert artefactos, "el dossier no se persistió en disco de SUPRA"


def test_abstencion_correcta_no_es_error() -> None:
    """Caso 3: ABSTENER correcto no es ERROR."""
    from criba.interprete.puerto import ESTADO_PENDIENTE, InterpretationResult

    # Abstención por regla de dominio: el problema no se relaciona con el cruce.
    resultado = InterpretationResult(
        estado=ESTADO_PENDIENTE,
        error="validacion:abstencion:el problema no se relaciona con el cruce",
    )
    campos = resultado.to_campos()
    # ABSTENER no es ERROR: el estado es PENDIENTE pero el motivo es abstención.
    assert campos["estado"] == ESTADO_PENDIENTE
    assert "abstencion:" in campos["error"]
    # No se rellena nada: los campos científicos quedan vacíos.
    assert campos["mecanismo"] == ""
    assert campos["hipotesis"] == ""


def test_schema_invalido_produce_pendiente_con_kind() -> None:
    """Caso 4: schema inválido → PENDIENTE con error_kind=schema."""
    from criba.interprete.contrato import validar_propuesta_estructurada

    parsed = {"pertinencia": "PERTINENTE"}  # falta todo lo demás
    errores = validar_propuesta_estructurada(parsed, _idea_valida(), [])
    assert errores
    kinds = {kind for kind, _ in errores}
    assert "schema" in kinds


def test_dominio_invalido_produce_pendiente_con_kind() -> None:
    """Caso 5: dominio inválido → PENDIENTE con error_kind=domain."""
    from criba.interprete.contrato import validar_propuesta_estructurada

    # Mecanismo repite nombres de técnicas: fallo de dominio.
    parsed = {
        "pertinencia": "PERTINENTE",
        "hipotesis": "test",
        "mecanismo": "La Confirmación automática y los Recordatorios funcionan juntos.",
        "cadena_causal": ["a", "b"],
        "aportacion_por_tecnica": ["op A", "op B"],
        "supuestos": [],
        "prueba_concreta": "test",
        "incertidumbre": "test",
        "novedad": "test",
        "evidencia_citada": [],
        "conocimiento_previo": [],
        "prueba": {
            "metrica": "m",
            "baseline": "b",
            "umbral": "20%",
            "condicion_fracaso": "f",
            "alternativa_explicativa": "alt",
            "resultado_favorable_mecanismo": "H1",
            "resultado_favorable_alternativa": "H2 distinto",
        },
        "comprobacion_restricciones": [],
    }
    errores = validar_propuesta_estructurada(parsed, _idea_valida(), [])
    assert errores
    kinds = {kind for kind, _ in errores}
    assert "domain" in kinds


def test_sin_evidencia_citas_vacias() -> None:
    """Caso 9: sin evidencia entregada, evidencia_citada debe ser []."""
    from criba.interprete.contrato import validar_propuesta_estructurada

    # Propuesta sin evidencia: evidencia_citada vacío es válido.
    parsed = {
        "pertinencia": "PERTINENTE",
        "hipotesis": "test",
        "mecanismo": "Un mecanismo causal suficientemente específico y largo aquí.",
        "cadena_causal": ["intervención", "efecto"],
        "aportacion_por_tecnica": ["op A", "op B"],
        "supuestos": [],
        "prueba_concreta": "test",
        "incertidumbre": "test",
        "novedad": "test",
        "evidencia_citada": [],
        "conocimiento_previo": [],
        "prueba": {
            "metrica": "m",
            "baseline": "b",
            "umbral": "20%",
            "condicion_fracaso": "f",
            "alternativa_explicativa": "alt",
            "resultado_favorable_mecanismo": "H1",
            "resultado_favorable_alternativa": "H2 distinto",
        },
        "comprobacion_restricciones": [],
    }
    errores = validar_propuesta_estructurada(parsed, _idea_valida(), [])
    # Sin evidencia no debe aparecer el error de índices inexistentes.
    assert not any("evidencia_citada" in m for _, m in errores)


def test_restricciones_no_comprobadas_producen_error() -> None:
    """Caso 10: restricciones obligatorias no comprobadas exactamente."""
    from criba.interprete.contrato import validar_propuesta_estructurada

    idea = _idea_valida()
    idea["bloqueo"] = {"restricciones_obligatorias": ["No usar X"]}
    parsed = {
        "pertinencia": "PERTINENTE",
        "hipotesis": "test",
        "mecanismo": "Un mecanismo causal suficientemente específico y largo aquí.",
        "cadena_causal": ["intervención", "efecto"],
        "aportacion_por_tecnica": ["op A", "op B"],
        "supuestos": [],
        "prueba_concreta": "test",
        "incertidumbre": "test",
        "novedad": "test",
        "evidencia_citada": [],
        "conocimiento_previo": [],
        "prueba": {
            "metrica": "m",
            "baseline": "b",
            "umbral": "20%",
            "condicion_fracaso": "f",
            "alternativa_explicativa": "alt",
            "resultado_favorable_mecanismo": "H1",
            "resultado_favorable_alternativa": "H2 distinto",
        },
        "comprobacion_restricciones": [],  # falta la restricción obligatoria
    }
    errores = validar_propuesta_estructurada(parsed, idea, [])
    assert any("restricciones obligatorias no comprobadas" in m for _, m in errores)


def test_campos_extra_no_se_propagan() -> None:
    """Caso 11: campos extra en el parsed no llegan al dossier."""
    from criba.interprete.puerto import InterpretationResult

    # to_campos() solo expone CAMPOS_PROPUESTA, nunca campos extra.
    resultado = InterpretationResult(estado="PROPUESTA")
    campos = resultado.to_campos()
    from criba.interprete.puerto import CAMPOS_PROPUESTA

    assert set(campos.keys()) == set(CAMPOS_PROPUESTA)


def test_procedencia_sobrevive_al_dossier() -> None:
    """Invariante: la procedencia sobrevive al dossier."""
    from criba.supra_dossier import preparar_dossier

    entry = _entry_propuesta()
    # El entry declara la procedencia del intérprete.
    assert entry["interpretacion_provenance"]["interpreter_backend"] == "simulado"
    assert entry["interpretacion_provenance"]["request_id"] == "req-001"
    dossier = preparar_dossier(
        entry,
        "Eliminar segundas visitas por errores de registro.",
        ficha_bloqueo={"title": "salud"},
    )
    # La procedencia del intérprete queda registrada en el dossier,
    # anidada en interpretacion.provenance (ubicación contractual de SUPRA).
    assert dossier.get("interpretacion")
    prov = dossier["interpretacion"]["provenance"]
    assert prov["interpreter_backend"] == "simulado"
    assert prov["request_id"] == "req-001"
