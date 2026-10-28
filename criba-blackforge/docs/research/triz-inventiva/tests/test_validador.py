"""Pruebas contractuales aisladas de la campaña TRIZ+Koestler (IMP-03/04/08).

ALCANCE: laboratorio. No activa servicios, red, modelos, ejecución de candidatos
ni persistencia productiva. Ejercita el validador y el mapeo de entrada al
intérprete con fixtures locales y con las colas documentales generadas.

EVIDENCIA: VERIFIED_BY_EXECUTION (solo lo ejecutado aquí).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from fixtures.fixtures import (
    FICHA_VALIDA,
    FICHA_INVALIDA_MISSING,
    FICHA_INVALIDA_NO_RIVAL,
    INTERPRETER_INPUT_VALIDO,
    OPERADOR_INVALIDO,
    OPERADOR_VALIDO,
)
from validator.validador import (
    validate_bundle,
    validate_cards,
    validate_inventive_card,
    validate_operators,
    validate_sources,
)

BUNDLE_DIR = Path(__file__).resolve().parents[1]


def _load_jsonl(path: Path) -> list[dict]:
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            out.append(json.loads(raw))
    return out


# ---------- Cola documental generada por IMP-01/02 ----------

@pytest.fixture(scope="module")
def bundle():
    sources = _load_jsonl(BUNDLE_DIR / "sources" / "sources.jsonl")
    operators = _load_jsonl(BUNDLE_DIR / "operators" / "operators.jsonl")
    cards = _load_jsonl(BUNDLE_DIR / "findings" / "cards.jsonl")
    return {"sources": sources, "operators": operators, "cards": cards}


def test_bundle_counts(bundle):
    assert len(bundle["sources"]) == 35
    assert len(bundle["operators"]) == 8
    assert len(bundle["cards"]) == 70


def test_bundle_valid(bundle):
    errs, counts = validate_bundle(BUNDLE_DIR)
    assert errs == [], [e.as_dict() for e in errs]
    assert counts == {"sources": 35, "operators": 8, "cards": 70}


def test_operators_all_not_executed(bundle):
    source_ids = {s["source_id"] for s in bundle["sources"]}
    errs = validate_operators(bundle["operators"], source_ids)
    assert errs == [], [e.as_dict() for e in errs]


def test_cards_no_cycles_no_dupes(bundle):
    source_ids = {s["source_id"] for s in bundle["sources"]}
    errs = validate_cards(bundle["cards"], source_ids)
    codes = {e.code for e in errs}
    assert "CARD_CYCLE" not in codes, [e.as_dict() for e in errs if e.code == "CARD_CYCLE"]
    assert "CARD_DUPLICATE_ID" not in codes
    assert "CARD_UNKNOWN_DEP" not in codes


# ---------- Ficha AC-06 (IMP-03) ----------

def test_ficha_valida_passes():
    assert validate_inventive_card(FICHA_VALIDA) == []


def test_ficha_no_rival_rejected():
    errs = validate_inventive_card(FICHA_INVALIDA_NO_RIVAL)
    codes = {e.code for e in errs}
    assert "CARD6_NO_RIVAL" in codes


def test_ficha_missing_rejected():
    errs = validate_inventive_card(FICHA_INVALIDA_MISSING)
    codes = {e.code for e in errs}
    assert {"CARD6_MISSING", "SRC_NO_READING_UNKNOWN"} & codes or "CARD6_MISSING" in codes


def test_ruptura_zero_is_rejected():
    # UNKNOWN != 0: ruptura = 0 debe ser rechazado
    errs = validate_inventive_card(FICHA_INVALIDA_NO_RIVAL)
    codes = {e.code for e in errs}
    assert "CARD6_RUPTURA_ZERO" in codes


# ---------- Operador (IMP-03) ----------

def test_operator_valid_passes():
    errs = validate_operators([OPERADOR_VALIDO], {"SRC03"})
    assert errs == []


def test_operator_executed_status_rejected():
    errs = validate_operators([OPERADOR_INVALIDO], {"SRC03"})
    codes = {e.code for e in errs}
    assert "OP_EXEC_STATUS" in codes


def test_operator_unknown_source_rejected():
    op = dict(OPERADOR_VALIDO)
    op["source_ids"] = ["SRC999"]
    errs = validate_operators([op], {"SRC03"})
    codes = {e.code for e in errs}
    assert "OP_UNKNOWN_SOURCE" in codes


# ---------- Mapeo al contrato del intérprete (IMP-03) ----------

def test_interpreter_input_has_required_fields():
    for field in ("PROBLEMA", "DOMINIO", "CRUCE", "BLOQUEO IDENTIFICADO", "EVIDENCIA LOCAL PERTINENTE"):
        assert field in INTERPRETER_INPUT_VALIDO, f"falta campo de contrato: {field}"


def test_interpreter_input_constraints_are_list_of_str():
    bloqueo = INTERPRETER_INPUT_VALIDO["BLOQUEO IDENTIFICADO"]
    raw = bloqueo.get("restricciones_obligatorias", [])
    assert isinstance(raw, list)
    assert all(isinstance(x, str) and x.strip() for x in raw)


def test_interpreter_input_evidence_indexable():
    ev = INTERPRETER_INPUT_VALIDO["EVIDENCIA LOCAL PERTINENTE"]
    assert isinstance(ev, list) and len(ev) >= 1
    # citation index = position + 1 (contrato: indices empiezan en 1)
    for i, item in enumerate(ev, 1):
        assert item.get("source_id"), f"evidencia {i} sin source_id"


def test_interpreter_input_no_embedded_instructions():
    # Frontera de confianza: los datos no deben contener órdenes de acción.
    blob = json.dumps(INTERPRETER_INPUT_VALIDO, ensure_ascii=False).lower()
    for forbidden in ("ejecuta blackforge", "revela la clave", "ignora las restricciones", "cambia de proveedor"):
        assert forbidden not in blob, f"entrada contiene instrucción embebida: {forbidden}"


# ---------- Sources: UNKNOWN de licencia no se oculta ----------

def test_source_license_unknown_flagged(bundle):
    _errors, warnings = validate_sources(bundle["sources"])
    codes = {e.code for e in warnings}
    # Al menos una fuente tiene license UNKNOWN (esperado en este bundle documental)
    assert "SRC_LICENSE_UNKNOWN" in codes


# ---------- Pruebas dirigidas mínimas (steer punto 4) ----------

def _card(cid, depends_on=None, sources=None, exec_status="NOT_EXECUTED"):
    return {
        "card_id": cid,
        "depends_on": depends_on or [],
        "source_ids": sources or [],
        "execution_status": exec_status,
    }


def test_dependency_to_later_card_accepted():
    # LIT-026 depende de tarjetas posteriores (LIT-027..034): aceptada.
    cards = [_card("LIT-026", ["LIT-027"]), _card("LIT-027")]
    source_ids = {"SRC01"}
    errs = [e for e in validate_cards(cards, source_ids) if e.code == "CARD_UNKNOWN_DEP"]
    assert errs == []


def test_same_cards_different_order_same_result():
    a = [_card("A", ["B"]), _card("B", ["C"]), _card("C")]
    b = [_card("C"), _card("B", ["C"]), _card("A", ["B"])]
    s = {"SRC01"}
    ea = {e.code for e in validate_cards(a, s)}
    eb = {e.code for e in validate_cards(b, s)}
    assert ea == eb == set()


def test_nonexistent_dependency_rejected():
    cards = [_card("A", ["Z"]), _card("B")]
    errs = [e for e in validate_cards(cards, {"SRC01"}) if e.code == "CARD_UNKNOWN_DEP"]
    assert len(errs) == 1 and errs[0].locator == "A"


def test_duplicate_id_rejected():
    cards = [_card("A"), _card("A")]
    errs = [e for e in validate_cards(cards, {"SRC01"}) if e.code == "CARD_DUPLICATE_ID"]
    assert len(errs) == 1 and errs[0].locator == "A"


def test_bad_id_type_rejected_not_traceback():
    cards = [{"card_id": 123, "depends_on": [], "source_ids": [], "execution_status": "NOT_EXECUTED"}, _card("B")]
    errs = [e for e in validate_cards(cards, {"SRC01"}) if e.code == "CARD_BAD_ID"]
    assert len(errs) == 1


def test_bad_depends_on_type_rejected():
    cards = [{"card_id": "A", "depends_on": "B", "source_ids": [], "execution_status": "NOT_EXECUTED"}]
    errs = [e for e in validate_cards(cards, {"SRC01"}) if e.code == "CARD_BAD_DEPS"]
    assert len(errs) == 1


def test_unknown_vs_unknown_explicit_and_prefix():
    # UNKNOWN exacto y "UNKNOWN: explicacion" son marcadores; "UNKNOWNLAND" no.
    _e, w1 = validate_sources([{"source_id": "S1", "license": "UNKNOWN"}])
    assert any(e.code == "SRC_LICENSE_UNKNOWN" for e in w1)
    _e, w2 = validate_sources([{"source_id": "S2", "license": "UNKNOWN: verificar"}])
    assert any(e.code == "SRC_LICENSE_UNKNOWN" for e in w2)
    # Prefijo no delimitado: NO se reconoce como marcador (no debe flaggear SRC_LICENSE_UNKNOWN).
    _e3, w3 = validate_sources([{"source_id": "S3", "license": "UNKNOWNLAND"}])
    assert not any(e.code == "SRC_LICENSE_UNKNOWN" for e in w3)


def test_ficha_nested_valid_accepted():
    assert validate_inventive_card(FICHA_VALIDA) == []


def test_ficha_bad_container_type_rejected():
    # content no es un contenedor: rechazado.
    bad = dict(FICHA_VALIDA)
    bad["content"] = "no es dict"
    errs = [e for e in validate_inventive_card(bad) if e.code == "CARD6_MISSING"]
    assert errs
