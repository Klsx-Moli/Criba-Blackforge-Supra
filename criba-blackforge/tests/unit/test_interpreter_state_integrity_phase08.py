"""F08: cached status consistency and honest Inventar judge state.

The cache must not reuse parseable-but-contradictory historical rows. The
Inventar judge must not mark a pending generation as CRITIQUED merely because
the pending object happens to contain a successful-looking critique payload.
No model endpoint or external search is contacted by these synthetic tests.
"""
from __future__ import annotations

import json

import pytest

from criba.interprete.contrato import PROMPT_VERSION, SCHEMA_VERSION
from criba.interprete.store import InterpreteStore
from criba.storage import Storage
from verification.interpreter_cases import critica, resultado

IDEA = {
    "id": "c1",
    "method1": "Poka-Yoke",
    "method2": "Retroalimentación",
    "description": "Revisar campos ausentes antes de confirmar citas.",
    "causal_axes_changed": ["flujo", "feedback"],
    "convergence": {"novelty": 0.75},
}


def _stored_success(tmp_path):
    storage = Storage(str(tmp_path / "interpreter-state.db"))
    store = InterpreteStore(storage)
    synthetic = resultado()
    assert synthetic.es_propuesta
    idea = {
        **IDEA,
        "interprete_labels": [],
        "interprete_score": None,
        "interprete_verdict": "PROPUESTA",
        "interprete_evaluation_status": "CRITIQUED",
        "interprete_analisis": "",
        "interprete_result": synthetic.to_campos(),
        "interprete_raw_output": "synthetic",
        "interprete_evidence_delivered": [],
        "interprete_provenance": {
            "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "prompt_sha256": "synthetic-prompt-sha",
            "raw_output_sha256": "synthetic-raw-sha",
            "generation_parameters": {},
            "fallback_used": False,
        },
    }
    args = {"activation_id": "activation", "idea": idea, "modelo": "mock",
            "run_id": "run", "seed": None}
    assert store.record_decision(**args)["status"] == "recorded"
    row = store.get_verdict("c1", "mock", run_id="run", seed=None)
    assert row is not None and InterpreteStore.cache_valido(row, idea, [])
    return storage, store, idea, args


@pytest.mark.parametrize(
    "target,value",
    [
        ("row_verdict", "PENDIENTE_INTERPRETACION"),
        ("nested_verdict", "PENDIENTE_INTERPRETACION"),
        ("nested_evaluation", "NOT_EVALUATED"),
        ("nested_evaluation", "ERROR"),
        ("nested_analisis", "timeout"),
        ("nested_analisis", "critica_invalida"),
        ("result_error", "timeout"),
        ("result_error", "UNKNOWN"),
        ("missing_nested_verdict", None),
        ("missing_result_error", None),
    ],
)
def test_parseable_conflict_never_reused_and_retry_preserves_history(tmp_path, target, value):
    storage, store, idea, args = _stored_success(tmp_path)
    con = storage.connect()
    try:
        with con:
            if target == "row_verdict":
                con.execute("UPDATE interprete_decisions SET veredicto=?", (value,))
            else:
                raw = con.execute(
                    "SELECT response_json FROM interprete_decisions"
                ).fetchone()[0]
                data = json.loads(raw)
                interpretation = data["interpretation"]
                if target in ("nested_verdict", "missing_nested_verdict"):
                    container, key = interpretation, "interprete_verdict"
                elif target == "nested_evaluation":
                    container, key = interpretation, "interprete_evaluation_status"
                elif target == "nested_analisis":
                    container, key = interpretation, "interprete_analisis"
                else:
                    container, key = interpretation["interprete_result"], "error"
                if target.startswith("missing_"):
                    container.pop(key, None)
                else:
                    container[key] = value
                con.execute(
                    "UPDATE interprete_decisions SET response_json=?",
                    (json.dumps(data, ensure_ascii=False),),
                )
    finally:
        con.close()

    row = store.get_verdict("c1", "mock", run_id="run", seed=None)
    assert row is not None and row["evaluation_status"] == "CRITIQUED"
    assert not InterpreteStore.cache_valido(row, idea, [])
    # The conflict never becomes a reusable result, even after process/reopen.
    reopened = InterpreteStore(Storage(str(tmp_path / "interpreter-state.db")))
    again = reopened.get_verdict("c1", "mock", run_id="run", seed=None)
    assert again is not None and not reopened.cache_valido(again, idea, [])
    assert reopened.record_decision(**args)["status"] == "retried"
    repaired = reopened.get_verdict("c1", "mock", run_id="run", seed=None)
    assert repaired is not None and reopened.cache_valido(repaired, idea, [])
    con = storage.connect()
    try:
        assert con.execute("SELECT count(*) FROM interprete_attempts").fetchone()[0] == 2
    finally:
        con.close()


class _OfflineSource:
    def __init__(self, source_id: str, kind: str):
        from criba.intelligence.sources.transport import TransportBudget

        class _Transport:
            def __init__(self):
                self.budget = TransportBudget(max_requests=200)

            def get(self, url, **kwargs):
                raise ConnectionError("OFFLINE_TEST")

        self.SOURCE_ID = source_id
        self.KIND = kind
        self.context = type("_Context", (), {"transport": _Transport()})()

    def source_id(self) -> str:
        return self.SOURCE_ID

    def search(self, query: str, limit: int = 5):
        from criba.intelligence.contracts import SourceQueryResult

        return SourceQueryResult(
            source_id=self.SOURCE_ID, query_text=query, ok=False, error="OFFLINE_TEST"
        )

    def health(self) -> str:
        return "AVAILABLE"


def _methods():
    methods = [
        {
            "id": f"{cls}-{i:03d}",
            "name": f"{cls}-{i:03d}",
            "title": f"{cls} {i:03d}",
            "family": cls,
            "thinking_class": cls,
        }
        for cls in ("perspectiva", "generacion", "ruptura", "escape")
        for i in range(30)
    ]
    methods.extend(
        {
            "id": f"dominio-{i:03d}",
            "name": f"dominio-{i:03d}",
            "title": f"dominio {i:03d}",
            "family": "metodologias",
            "thinking_class": "dominio",
        }
        for i in range(20)
    )
    return methods


@pytest.mark.parametrize("pending", [True, False])
def test_inventar_judge_never_promotes_pending_critique(pending):
    from criba.inventar import invent

    def synthetic_proposer(query, idea, domain, evidence):
        if not pending:
            return resultado().to_campos()
        return {
            "estado": "PENDIENTE_INTERPRETACION",
            "hipotesis": "synthetic-only",
            "mecanismo": "",
            "error": "timeout",
            "critica": {"evaluation_status": "CRITIQUED", "respuesta": critica()},
            "interpretacion_model_requests": None,
        }

    sheet = invent(
        "Revisar registros antes de confirmar citas",
        seed=33, rounds=1, batch_size=4, top=1, offline=False,
        methods=_methods(), sources=[
            _OfflineSource("fake-a", "product"), _OfflineSource("fake-b", "patent"),
        ],
        proponer=synthetic_proposer, history_storage=False,
    )
    assert len(sheet["entries"]) == 1
    entry = sheet["entries"][0]
    if pending:
        assert entry["estado_interpretacion"] == "PENDIENTE_INTERPRETACION"
        assert entry["judge"]["evaluation_status"] == "NOT_EVALUATED"
        assert entry["judge"]["score"] is None
        # Keep the contradictory critique for forensic diagnosis, not credit.
        assert entry["critica"]["evaluation_status"] == "CRITIQUED"
        assert entry["interpretacion_error"] == "timeout"
    else:
        assert entry["estado_interpretacion"] == "PROPUESTA"
        assert entry["judge"]["evaluation_status"] == "CRITIQUED"
        assert entry["judge"]["score"] is None
