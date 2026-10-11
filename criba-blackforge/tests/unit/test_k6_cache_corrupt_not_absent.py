"""K6 · Robustez del cache del intérprete: AUSENTE != CORRUPTO.

Invariante clave de K6 sobre InterpreterStore.get_verdict: una entrada con
response_json/provenance_json CORRUPTO (JSON inválido o tipo incompatible) NO
se reporta como ausente (None) ni se fabrica un valor por defecto silencioso.
Se conserva el raw dañado en la clave física, se marca evaluation_status=
CACHE_INVALID y se preserva cache_error. Evidencia preservada, no destruida.

API real: Storage(path).connect() -> sqlite3; InterpreterStore(storage);
get_verdict(idea_id, modelo) lee interprete_decisions por combo_key
(= json.dumps([idea_id, modelo])).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # iso-bf-tab/criba-blackforge
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from criba.interprete.store import InterpreteStore as InterpreterStore  # noqa: E402
from criba.storage import Storage  # noqa: E402

IDEA = "idea-k6-corrupta"
MODELO = "modelo-k6"


def _store(tmp_path):
    storage = Storage(tmp_path / "k6.sqlite3")
    st = InterpreterStore(storage)
    storage.connect().close()
    return st, storage


def _insertar_decision(storage, *, response_json, provenance_json, labels_json=None):
    con = storage.connect()
    try:
        con.execute(
            "INSERT INTO interprete_decisions "
            "(combo_key, run_id, seed_key, activation_id, idea_id, modelo, labels_json, "
            "veredicto, evaluation_status, response_json, provenance_json, prompt_version, "
            "schema_version, raw_output_sha256, fallback_used, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                json.dumps([IDEA, MODELO], ensure_ascii=False),
                "run-k6",
                "none",
                "act-k6",
                IDEA,
                MODELO,
                labels_json if labels_json is not None else json.dumps(["etiqueta"]),
                "ABSTENER",
                "EVALUATED",
                response_json,
                provenance_json,
                "v-k6",
                "s-k6",
                "sha-k6",
                0,
                "2026-10-11T00:00:00Z",
            ),
        )
        con.commit()
    finally:
        con.close()


def test_verdict_corrupto_no_es_ausente_ni_fabricado(tmp_path):
    """response_json corrupto -> get_verdict devuelve la fila marcada
    CACHE_INVALID, conservando el raw dañado. NO devuelve None."""
    st, storage = _store(tmp_path)
    _insertar_decision(
        storage,
        response_json="{json roto, no parseable",
        provenance_json=json.dumps({"prompt_sha256": "sha-ok"}),
    )

    res = st.get_verdict(IDEA, MODELO)

    assert res is not None, "entrada corrupta NO debe reportarse como ausente (None)"
    assert res.get("evaluation_status") == "CACHE_INVALID"
    assert res.get("cache_error", "").startswith("response_json:")
    assert res.get("response_json") == "{json roto, no parseable"
    assert res.get("provenance") == {"prompt_sha256": "sha-ok"}


def test_verdict_tipo_incompatible_es_cache_invalid(tmp_path):
    """response_json con tipo incorrecto (lista donde se espera dict) ->
    CACHE_INVALID, no se coerciona silenciosamente perdiendo la evidencia."""
    st, storage = _store(tmp_path)
    _insertar_decision(
        storage,
        response_json=json.dumps(["no", "soy", "un", "dict"]),
        provenance_json=json.dumps({"prompt_sha256": "sha-ok"}),
    )

    res = st.get_verdict(IDEA, MODELO)

    assert res is not None
    assert res.get("evaluation_status") == "CACHE_INVALID"
    assert res.get("response_json") == json.dumps(["no", "soy", "un", "dict"])
    assert res.get("response") == {}


def test_verdict_valido_no_se_marca_invalido(tmp_path):
    """Control: una entrada válida NO se marca CACHE_INVALID (sin falso positivo)."""
    st, storage = _store(tmp_path)
    _insertar_decision(
        storage,
        response_json=json.dumps({"propuesta": "ok"}),
        provenance_json=json.dumps({"prompt_sha256": "sha-ok"}),
    )

    res = st.get_verdict(IDEA, MODELO)

    assert res is not None
    assert res.get("evaluation_status") != "CACHE_INVALID"
    assert res.get("response") == {"propuesta": "ok"}
    assert res.get("provenance") == {"prompt_sha256": "sha-ok"}


def test_verdict_realmente_ausente_devuelve_none(tmp_path):
    """Distinción AUSENTE: si no hay fila, devuelve None (ausente honesto)."""
    st, _storage = _store(tmp_path)
    assert st.get_verdict("idea-que-no-existe", MODELO) is None
