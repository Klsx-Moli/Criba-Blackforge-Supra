"""K3 paso 2 - Adaptador de la MISMA llamada de critica.

Protege que el puente delegue su identidad en ``semantic_lab`` (sin
inventar un segundo formato) y que el recibo del transporte real cierre
el ciclo del laboratorio.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from benchmarks.innovation.semantic_bridge_test_data import (
    IDEA,
    PROPUESTA,
    QUERY,
    evidence,
)
from benchmarks.innovation.semantic_critic_bridge import (
    build_receipt,
    mensaje_compuesto,
    preparar_critica,
    request_sha_de_critica,
    sha_mensaje_compuesto,
    validar_critica_produccion,
)
from benchmarks.innovation.semantic_lab import Trial, read_current

REVIEWER = "judge-local"
ATTEMPT = "intento-1"
SCOPE = "scope-k3"


def _trial() -> Trial:
    data = {
        "pertinencia": "PERTINENTE",
        "hipotesis": PROPUESTA["hipotesis"],
        "mecanismo": PROPUESTA["mecanismo"],
        "cadena_causal": PROPUESTA["cadena_causal"],
        "prueba": PROPUESTA["prueba"],
        "prueba_concreta": PROPUESTA["prueba_concreta"],
        "supuestos": PROPUESTA["supuestos"],
        "incertidumbre": PROPUESTA["incertidumbre"],
        "conocimiento_previo": PROPUESTA["conocimiento_previo"],
    }
    canonico = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return Trial(
        case_id="CBS500-01-01",
        run_id="run-k3",
        episode_id="ep-k3",
        candidate_id="cand-k3",
        generator_model=REVIEWER,
        query=QUERY,
        restrictions=tuple(IDEA["bloqueo"]["restricciones_obligatorias"]),
        proposal_json=canonico,
        input_context_sha256=hashlib.sha256(b"ctx-k3").hexdigest(),
    )


def _cuerpo_valido() -> dict:
    """Cuerpo de critica sintetico que satisface validar_critica.

    El laboratorio exige citas LITERALES del problema y del campo de la
    propuesta, no basta con que los booleanos sean True. Una critica falsa
    con citas autenticas sigue siendo solo una afirmacion del evaluador.
    """
    trial = _trial()
    propuesta = trial.proposal
    restriccion = trial.restrictions[0]
    # Cita literal del problema: una frase exacta del query.
    cita_problema = "agua fría desperdiciada"
    frag_mecanismo = propuesta["mechanism"][:40]
    frag_metrica = propuesta["metric"][:40]
    if cita_problema not in trial.query:
        cita_problema = trial.query[:30]

    def fila(assessment: str, source_quote: str, field: str, proposal_quote: str) -> dict:
        return {
            "assessment": assessment,
            "reason": "lectura sintetica de prueba",
            "source_quote": source_quote,
            "proposal_field": field,
            "proposal_quote": proposal_quote,
        }

    return {
        "axes": {
            "objective": fila("SUPPORTS", cita_problema, "mechanism", frag_mecanismo),
            "mechanism": fila("SUPPORTS", cita_problema, "mechanism", frag_mecanismo),
            "metric": fila("SUPPORTS", cita_problema, "metric", frag_metrica),
        },
        "restrictions": {
            restriccion: fila("SUPPORTS", restriccion, "mechanism", frag_mecanismo),
        },
    }


def _sha(**kw) -> str:
    base = {"reviewer": REVIEWER, "attempt": ATTEMPT, "stage": "DIRECT"}
    base.update(kw)
    return request_sha_de_critica(_trial(), **base)


def _recibo(sha: str, **kw) -> str:
    base = {
        "request_sha256": sha, "observed_model": REVIEWER,
        "transport_id": "t-1", "finish_reason": "stop",
        "body": _cuerpo_valido(),
    }
    base.update(kw)
    return build_receipt(**base)


# --- Identidad ligada al laboratorio (no al formato del adaptador) ---

def test_request_sha_coincide_con_el_del_laboratorio() -> None:
    """El puente delega: su hash DEBE ser el del laboratorio, no otro."""
    from benchmarks.innovation.semantic_lab import direct_request

    t = _trial()
    esperado = direct_request(t, REVIEWER, ATTEMPT).sha256
    assert request_sha_de_critica(t, reviewer=REVIEWER, attempt=ATTEMPT) == esperado


def test_request_sha_distingue_attempt() -> None:
    assert _sha(attempt="intento-1") != _sha(attempt="intento-2")


def test_request_sha_distingue_reviewer() -> None:
    assert _sha(reviewer="judge-a") != _sha(reviewer="judge-b")


# --- Mensaje compuesto realmente enviado ---

def test_mensaje_compuesto_tiene_system_y_user() -> None:
    mensajes = mensaje_compuesto("prompt de critica")
    assert [m["role"] for m in mensajes] == ["system", "user"]
    assert mensajes[1]["content"] == "prompt de critica"
    assert mensajes[0]["content"].strip()


def test_hash_del_mensaje_cambia_con_el_prompt() -> None:
    a = sha_mensaje_compuesto(mensaje_compuesto("uno"))
    b = sha_mensaje_compuesto(mensaje_compuesto("dos"))
    assert a != b and len(a) == 64


def test_hash_del_mensaje_cambia_con_el_system() -> None:
    base = mensaje_compuesto("mismo prompt")
    alterado = [dict(m) for m in base]
    alterado[0]["content"] = alterado[0]["content"] + " extra"
    assert sha_mensaje_compuesto(base) != sha_mensaje_compuesto(alterado)


def test_preparar_critica_liga_ambos_hashes() -> None:
    call = preparar_critica(
        _trial(), query=QUERY, idea=IDEA, domain=None, evidence=evidence(),
        propuesta=PROPUESTA, reviewer=REVIEWER, attempt=ATTEMPT,
    )
    assert call.request_sha256 == _sha()
    assert call.message_sha256 == sha_mensaje_compuesto(call.mensajes)
    assert "ducha" in call.mensajes[1]["content"].lower()


# --- Recibo del transporte real ---

def test_recibo_valido_es_aceptado_por_el_laboratorio() -> None:
    sha = _sha()
    reading = read_current(
        _trial(), reviewer=REVIEWER, attempt=ATTEMPT,
        current_request_sha256=sha, raw=_recibo(sha),
    )
    assert reading.outcome == "REVIEW_SUPPORTED"


def test_recibo_con_modelo_distinto_es_rechazado() -> None:
    """Un alias no acredita identidad: observed_model debe coincidir."""
    sha = _sha()
    reading = read_current(
        _trial(), reviewer=REVIEWER, attempt=ATTEMPT,
        current_request_sha256=sha, raw=_recibo(sha, observed_model="otro-modelo"),
    )
    assert reading.outcome == "EVALUATOR_ERROR"


def test_recibo_no_cierra_si_la_reserva_se_mueve() -> None:
    """Caso K3: la peticion cambio, el recibo viejo ya no es vigente."""
    sha = _sha()
    reading = read_current(
        _trial(), reviewer=REVIEWER, attempt=ATTEMPT,
        current_request_sha256="f" * 64, raw=_recibo(sha),
    )
    assert reading.outcome == "EVALUATOR_ERROR"
    assert reading.disposition == "RESEARCH_ONLY"


def test_recibo_no_cierra_si_cambia_el_attempt() -> None:
    """Un recibo del intento 1 no vale para el intento 2."""
    sha = _sha()
    reading = read_current(
        _trial(), reviewer=REVIEWER, attempt="intento-2",
        current_request_sha256=sha, raw=_recibo(sha),
    )
    assert reading.outcome == "EVALUATOR_ERROR"


def test_recibo_incompleto_se_rechaza() -> None:
    with pytest.raises(ValueError):
        _recibo(_sha(), finish_reason="length")


def test_validar_critica_produccion_detecta_fallo() -> None:
    assert validar_critica_produccion({"pertinente": True})


def test_cache_no_inventa_identidad() -> None:
    """Un hash de cache es una clave, no una prueba de quien respondio."""
    sha = _sha()
    assert sha == _sha()  # determinista
    raw = _recibo(sha, transport_id="cache-hit")
    assert json.loads(raw)["observed_model"] == REVIEWER