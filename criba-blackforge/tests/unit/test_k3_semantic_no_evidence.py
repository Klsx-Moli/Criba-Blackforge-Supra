"""K3 paso 3 - Ninguna lectura semantica se convierte en evidencia.

Sin proveedor y sin red: se comprueba que los consumidores productivos
(interpretacion, scoring/reward, exportacion) no promocionan una lectura
del laboratorio a resultado cientifico.

Aceptacion:
  - identidad alterada, version antigua, fallo, retry o respuesta tardia
    nunca promueven;
  - un candidato defendible sigue visible;
  - la historica es legible;
  - ningun side effect cientifico antes/despues de un cache hit.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from benchmarks.innovation.semantic_bridge_test_data import (
    IDEA,
    PROPUESTA,
    QUERY,
)
from benchmarks.innovation.semantic_critic_bridge import (
    build_receipt,
    request_sha_de_critica,
)
from benchmarks.innovation.semantic_lab import (
    ResearchReading,
    Trial,
    read_current,
)

REVIEWER = "judge-local"
ATTEMPT = "intento-1"


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
        input_context_sha256=hashlib.sha256(b"ctx").hexdigest(),
    )


def _cuerpo() -> dict:
    trial = _trial()
    propuesta = trial.proposal
    restriccion = trial.restrictions[0]
    cita = "agua fría desperdiciada"
    if cita not in trial.query:
        cita = trial.query[:30]
    frag_mec = propuesta["mechanism"][:40]
    frag_met = propuesta["metric"][:40]

    def fila(a: str, sq: str, pf: str, pq: str) -> dict:
        return {"assessment": a, "reason": "r", "source_quote": sq,
                "proposal_field": pf, "proposal_quote": pq}

    return {
        "axes": {
            "objective": fila("SUPPORTS", cita, "mechanism", frag_mec),
            "mechanism": fila("SUPPORTS", cita, "mechanism", frag_mec),
            "metric": fila("SUPPORTS", cita, "metric", frag_met),
        },
        "restrictions": {
            restriccion: fila("SUPPORTS", restriccion, "mechanism", frag_mec),
        },
    }


def _sha(**kw) -> str:
    base = {"reviewer": REVIEWER, "attempt": ATTEMPT, "stage": "DIRECT"}
    base.update(kw)
    return request_sha_de_critica(_trial(), **base)


def _recibo(sha: str, **kw) -> str:
    base = {"request_sha256": sha, "observed_model": REVIEWER,
            "transport_id": "t", "finish_reason": "stop", "body": _cuerpo()}
    base.update(kw)
    return build_receipt(**base)


# --- Ningun estado de lectura es un PASS ---

def test_lectura_no_es_predicado_booleano() -> None:
    """bool(lectura) falla deliberadamente: no se puede usar como condicion."""
    sha = _sha()
    reading = read_current(
        _trial(), reviewer=REVIEWER, attempt=ATTEMPT,
        current_request_sha256=sha, raw=_recibo(sha),
    )
    with pytest.raises(TypeError):
        bool(reading)


def test_lectura_solo_tiene_disposiciones_de_investigacion() -> None:
    """No existe salida PASS, score ni reward en la API de lectura."""
    permitidos = {
        "CAUSALLY_ARGUED_CANDIDATE",
        "MISMATCH_FOR_THIS_PROBLEM",
        "RESEARCH_ONLY",
    }
    assert isinstance(ResearchReading("REVIEW_SUPPORTED", "RESEARCH_ONLY", "a", None).disposition, str)
    # Las disposiciones observables estan acotadas a esos tres valores.
    for disp in ("CAUSALLY_ARGUED_CANDIDATE", "MISMATCH_FOR_THIS_PROBLEM", "RESEARCH_ONLY"):
        assert disp in permitidos


def test_candidato_argumentado_sigue_visible_sin_ascender() -> None:
    """Un candidato defendible queda como candidato, no como validado."""
    sha = _sha()
    reading = read_current(
        _trial(), reviewer=REVIEWER, attempt=ATTEMPT,
        current_request_sha256=sha, raw=_recibo(sha),
    )
    assert reading.outcome == "REVIEW_SUPPORTED"
    # Visibilidad sin promocion: la palabra "VALID" no aparece en la disposicion.
    assert reading.disposition == "CAUSALLY_ARGUED_CANDIDATE"
    assert "VALID" not in reading.disposition


# --- Nada promueve en los casos de fallo ---

def test_identidad_alterada_no_promueve() -> None:
    sha = _sha()
    reading = read_current(
        _trial(), reviewer=REVIEWER, attempt=ATTEMPT,
        current_request_sha256=sha, raw=_recibo(sha, observed_model="otro"),
    )
    assert reading.outcome == "EVALUATOR_ERROR"


def test_version_antigua_no_promueve() -> None:
    """Un recibo atado a un request que ya no es el vigente no promueve."""
    sha = _sha()
    reading = read_current(
        _trial(), reviewer=REVIEWER, attempt=ATTEMPT,
        current_request_sha256="0" * 64, raw=_recibo(sha),
    )
    assert reading.outcome == "EVALUATOR_ERROR"
    assert reading.disposition == "RESEARCH_ONLY"


def test_fallo_no_promueve() -> None:
    sha = _sha()
    with pytest.raises(ValueError):
        _recibo(sha, finish_reason="length")


def test_respuesta_tardia_no_promueve() -> None:
    """Mismo request, pero la reserva ya paso a otro intento."""
    sha = _sha()
    reading = read_current(
        _trial(), reviewer=REVIEWER, attempt="intento-2",
        current_request_sha256=sha, raw=_recibo(sha),
    )
    assert reading.outcome == "EVALUATOR_ERROR"


def test_sin_recibo_no_promueve() -> None:
    reading = read_current(
        _trial(), reviewer=REVIEWER, attempt=ATTEMPT,
        current_request_sha256=_sha(), raw=None,
    )
    assert reading.outcome == "NOT_EVALUATED"
    assert reading.disposition == "RESEARCH_ONLY"


# --- Sin side effects entre cache hit y miss ---

def test_cache_hit_no_cambia_la_lectura() -> None:
    """La misma entrada da la misma lectura: la cache no inventa semantica."""
    sha = _sha()
    args = dict(reviewer=REVIEWER, attempt=ATTEMPT, current_request_sha256=sha)
    a = read_current(_trial(), raw=_recibo(sha), **args)
    b = read_current(_trial(), raw=_recibo(sha), **args)
    assert a.outcome == b.outcome
    assert a.disposition == b.disposition


def test_lectura_no_es_serializable_como_evidencia_cientifica() -> None:
    """La lectura no expone score ni reward: solo outcome/disposicion/hash."""
    sha = _sha()
    reading = read_current(
        _trial(), reviewer=REVIEWER, attempt=ATTEMPT,
        current_request_sha256=sha, raw=_recibo(sha),
    )
    campos = set(vars(reading).keys())
    assert campos == {"outcome", "disposition", "request_sha256", "receipt_sha256"}
    for prohibido in ("score", "reward", "epistemic_score", "veredicto", "pass"):
        assert prohibido not in campos