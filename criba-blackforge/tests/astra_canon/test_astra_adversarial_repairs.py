"""Adversarial sentinels for ASTRA execution identity and learning semantics."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from criba.inventar import record_outcomes
from criba.intelligence.outcome_store import CHANNEL_JUDGE, CHANNEL_OBSERVED, TechniqueOutcomeStore
from criba.interprete.adaptador import LocalInterprete
from criba.supra_dossier import guardar_dossier, lecciones_previas, preparar_dossier, registrar_resultado

NOW = datetime(2026, 1, 2, tzinfo=timezone.utc)


def _dossier():
    return preparar_dossier(
        {
            "candidate_id": "candidate-A",
            "run_id": "run-A",
            "hipotesis": "claim-A",
            "mecanismo": "mechanism-A",
            "mechanism_version": "m-v1",
            "prueba_concreta": "apply intervention A",
            "observable": "metric-A",
            "resultado_favorable_mecanismo": "metric increases",
            "resultado_favorable_alternativa": "metric does not increase",
            "regla_decision": "positive iff metric increases",
        },
        "problem",
        alternativa_explicativa="rival explanation",
    )


def _receipt(dossier, *, execution_id="exec-1", observed_result="positivo"):
    return {
        "candidate_id": dossier["candidate_id"],
        "mechanism_version": dossier["mechanism_version"],
        "claim_id": dossier["claim_id"],
        "protocol_version": dossier["protocol_version"],
        "execution_id": execution_id,
        "observed_result": observed_result,
        "result_scope": "EXPERIMENTAL_OBSERVATION",
    }


def test_astra_017_arbitrary_execution_id_is_not_accreditation(tmp_path):
    d = _dossier()
    guardar_dossier(d, tmp_path)
    result = registrar_resultado(
        d["dossier_id"], "positivo", directory=tmp_path,
        execution_id="arbitrary-string", protocol_version=d["protocol_version"],
    )
    assert result["accreditation"] == "DECLARED_RESULT"
    assert lecciones_previas("", tmp_path) == []


def test_astra_017_declared_receipt_alone_is_not_authoritative(tmp_path):
    d = _dossier()
    guardar_dossier(d, tmp_path)
    declared = _receipt(d)
    result = registrar_resultado(
        d["dossier_id"], "positivo", directory=tmp_path,
        execution_id="exec-1", protocol_version=d["protocol_version"],
        execution_receipt=declared,
    )
    assert result["accreditation"] == "DECLARED_RESULT"
    assert result["declared_execution_receipt"] == declared
    assert result["execution_receipt"] == {}
    assert lecciones_previas("", tmp_path) == []


def test_astra_017_authoritative_execution_receipt_is_required_and_rechecked(tmp_path):
    d = _dossier()
    guardar_dossier(d, tmp_path)
    receipt = _receipt(d)
    result = registrar_resultado(
        d["dossier_id"], "positivo", directory=tmp_path,
        execution_id="exec-1", protocol_version=d["protocol_version"],
        execution_receipt={"execution_id": "caller-declared-only"},
        execution_resolver=lambda execution_id: receipt if execution_id == "exec-1" else None,
    )
    assert result["accreditation"] == "ACCREDITED_EXECUTION"
    assert result["receipt_authority"] == "EXECUTION_RESOLVER"
    assert lecciones_previas("", tmp_path, execution_resolver=lambda _id: receipt)

    d2 = _dossier()
    guardar_dossier(d2, tmp_path)
    bad_receipt = _receipt(d2, execution_id="exec-2", observed_result="negativo")
    bad = registrar_resultado(
        d2["dossier_id"], "positivo", directory=tmp_path,
        execution_id="exec-2", protocol_version=d2["protocol_version"],
        execution_resolver=lambda _execution_id: bad_receipt,
    )
    assert bad["accreditation"] == "DECLARED_RESULT"


def test_astra_018_incomplete_discriminant_protocol_cannot_be_accredited(tmp_path):
    d = preparar_dossier(
        {
            "candidate_id": "candidate-incomplete",
            "run_id": "run-incomplete",
            "hipotesis": "claim-incomplete",
            "mecanismo": "mechanism-incomplete",
            "mechanism_version": "m-v1",
            "prueba_concreta": "some test",
        },
        "problem",
    )
    guardar_dossier(d, tmp_path)
    receipt = _receipt(d, execution_id="exec-incomplete")
    result = registrar_resultado(
        d["dossier_id"],
        "positivo",
        directory=tmp_path,
        execution_id="exec-incomplete",
        protocol_version=d["protocol_version"],
        execution_resolver=lambda _execution_id: receipt,
    )
    assert result["protocol_complete"] is False
    assert result["accreditation"] == "DECLARED_RESULT"
    assert result["learning_eligible"] is False
    assert lecciones_previas("", tmp_path) == []


def test_astra_020_indeterminate_observation_never_becomes_learning_lesson(tmp_path):
    d = _dossier()
    guardar_dossier(d, tmp_path)
    receipt = _receipt(d, execution_id="exec-indeterminate", observed_result="indeterminado")
    result = registrar_resultado(
        d["dossier_id"],
        "indeterminado",
        directory=tmp_path,
        execution_id="exec-indeterminate",
        protocol_version=d["protocol_version"],
        execution_resolver=lambda _execution_id: receipt,
    )
    assert result["accreditation"] == "ACCREDITED_EXECUTION"
    assert result["learning_eligible"] is False
    assert lecciones_previas("", tmp_path) == []


def test_astra_020_semantically_impossible_unknown_reward_is_excluded(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "outcomes.jsonl")
    store.path.write_text(
        json.dumps({
            "profile": "CRIBA", "family": "f", "technique_id": "T1",
            "channel": CHANNEL_OBSERVED, "outcome": "not_evaluated",
            "value": 1.0, "learning_eligible": True, "canon_version": "c",
            "outcome_semantics_version": 2,
            "run_id": "episode-1", "recorded_at": NOW.isoformat(),
        }) + "\n",
        encoding="utf-8",
    )
    with pytest.warns(RuntimeWarning):
        assert store.prior(
            profile="CRIBA", family="f", technique_id="T1",
            channel=CHANNEL_OBSERVED, canon_version="c", now=NOW,
        ) == (0.0, 0, "sin_datos")


def test_astra_022_same_episode_across_cells_does_not_inflate_ucb_population(tmp_path):
    reference = TechniqueOutcomeStore(tmp_path / "reference.jsonl")
    duplicated = TechniqueOutcomeStore(tmp_path / "duplicated.jsonl")
    for store in (reference, duplicated):
        store.record(
            profile="CRIBA", family="f", technique_id="T1",
            channel=CHANNEL_OBSERVED, outcome="positivo", canon_version="c",
            run_id="episode-1", recorded_at=NOW,
        )
    for technique in ("T2", "T3"):
        duplicated.record(
            profile="CRIBA", family="f", technique_id=technique,
            channel=CHANNEL_OBSERVED, outcome="positivo", canon_version="c",
            run_id="episode-1", recorded_at=NOW,
        )
    assert duplicated.prior(
        profile="CRIBA", family="f", technique_id="T1",
        channel=CHANNEL_OBSERVED, canon_version="c", now=NOW,
    ) == reference.prior(
        profile="CRIBA", family="f", technique_id="T1",
        channel=CHANNEL_OBSERVED, canon_version="c", now=NOW,
    )


def test_astra_020_heuristic_fallback_is_not_judge_learning(monkeypatch, tmp_path):
    from criba.interprete.openai_compatible import LocalLlamaInterpreter

    monkeypatch.delenv("NOUS_API_KEY", raising=False)
    monkeypatch.setattr(
        LocalLlamaInterpreter, "operativo", lambda self: (False, "runtime no disponible (prueba)")
    )
    judge = LocalInterprete().interpretar(
        "query",
        {"description": "", "mechanism_causal": "", "prefilter": {"dh": 0.6}},
    )
    assert judge["evaluation_status"] == "NOT_EVALUATED"
    assert judge["score"] is None

    store = TechniqueOutcomeStore(tmp_path / "outcomes.jsonl")
    sheet = {
        "run_id": "run-1",
        "entries": [{
            "candidate_id": "c1", "run_id": "run-1", "classes": ["f"],
            "method_ids": ["T1"], "aportacion_por_tecnica": [],
            "prior_art": {"verdict": "UNRESOLVED"}, "judge": judge,
        }],
    }
    record_outcomes(sheet, store, canon_version="c")
    assert all(r["channel"] != CHANNEL_JUDGE for r in store._read_valid())


def test_astra_020_current_semantics_rejects_incoherent_positive_reward(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "outcomes.jsonl")
    with pytest.raises(ValueError, match="incompatible"):
        store.record(
            profile="CRIBA",
            family="f",
            technique_id="T1",
            channel=CHANNEL_OBSERVED,
            outcome="positivo",
            value=0.0,
            canon_version="c",
            run_id="episode-incoherent",
            recorded_at=NOW,
        )


def test_astra_b01_dossier_correction_same_execution_is_one_current_lesson(tmp_path):
    d = _dossier()
    guardar_dossier(d, tmp_path)

    positive = _receipt(d, execution_id="exec-corrected", observed_result="positivo")
    first = registrar_resultado(
        d["dossier_id"],
        "positivo",
        directory=tmp_path,
        execution_id="exec-corrected",
        protocol_version=d["protocol_version"],
        execution_resolver=lambda _execution_id: positive,
    )

    negative = _receipt(d, execution_id="exec-corrected", observed_result="negativo")
    second = registrar_resultado(
        d["dossier_id"],
        "negativo",
        directory=tmp_path,
        execution_id="exec-corrected",
        protocol_version=d["protocol_version"],
        execution_resolver=lambda _execution_id: negative,
    )

    assert first["observation_id"] == second["observation_id"]
    assert first["revision_index"] == 0
    assert second["revision_index"] == 1
    assert second["first_registered_at"] == first["first_registered_at"]

    lessons = lecciones_previas("", tmp_path, limit=10, execution_resolver=lambda _id: negative)
    assert len(lessons) == 1
    assert "'negativo'" in lessons[0]
    assert "'positivo'" not in lessons[0]


def test_astra_020_current_semantics_rejects_judge_score_without_numeric_value(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "judge-invalid.jsonl")
    store.path.write_text(
        json.dumps(
            {
                "profile": "CRIBA",
                "family": "f",
                "technique_id": "T1",
                "channel": CHANNEL_JUDGE,
                "outcome": "score",
                "value": None,
                "learning_eligible": False,
                "canon_version": "c",
                "outcome_semantics_version": 2,
                "run_id": "judge-episode",
                "recorded_at": NOW.isoformat(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.warns(RuntimeWarning):
        assert store.prior(
            profile="CRIBA",
            family="f",
            technique_id="T1",
            channel=CHANNEL_JUDGE,
            canon_version="c",
            now=NOW,
        ) == (0.0, 0, "sin_datos")


def test_astra_017_authoritative_receipt_does_not_coerce_numeric_identity(tmp_path):
    d = preparar_dossier(
        {
            "candidate_id": "1", "run_id": "run-numeric", "hipotesis": "claim",
            "mecanismo": "mechanism", "mechanism_version": "mv",
            "prueba_concreta": "apply intervention", "observable": "metric",
            "resultado_favorable_mecanismo": "yes", "resultado_favorable_alternativa": "no",
            "regla_decision": "positive iff metric changes",
        },
        "problem", alternativa_explicativa="rival",
    )
    guardar_dossier(d, tmp_path)
    receipt = _receipt(d, execution_id="1")
    receipt["candidate_id"] = 1
    receipt["execution_id"] = 1

    result = registrar_resultado(
        d["dossier_id"], "positivo", directory=tmp_path,
        execution_id="1", protocol_version=d["protocol_version"],
        execution_resolver=lambda _execution_id: receipt,
    )

    assert result["accreditation"] == "DECLARED_RESULT"
    assert result["learning_eligible"] is False
    assert lecciones_previas("", tmp_path, execution_resolver=lambda _id: receipt) == []


def test_execution_identity_whitespace_is_not_silently_canonicalized(tmp_path):
    d = _dossier()
    guardar_dossier(d, tmp_path)
    receipt = _receipt(d, execution_id="exec-space")

    result = registrar_resultado(
        d["dossier_id"],
        "positivo",
        directory=tmp_path,
        execution_id=" exec-space ",
        protocol_version=d["protocol_version"],
        execution_resolver=lambda _execution_id: receipt,
    )

    assert result["accreditation"] == "DECLARED_RESULT"
    assert result["learning_eligible"] is False
    assert result["observation_id"] == ""
    assert lecciones_previas("", tmp_path, execution_resolver=lambda _id: receipt) == []


def test_persisted_numeric_execution_identity_cannot_reactivate_learning(tmp_path):
    d = preparar_dossier(
        {
            "candidate_id": "1", "run_id": "run-persisted-numeric", "hipotesis": "claim",
            "mecanismo": "mechanism", "mechanism_version": "mv",
            "prueba_concreta": "apply intervention", "observable": "metric",
            "resultado_favorable_mecanismo": "yes", "resultado_favorable_alternativa": "no",
            "regla_decision": "positive iff metric changes",
        },
        "problem", alternativa_explicativa="rival",
    )
    guardar_dossier(d, tmp_path)
    receipt = _receipt(d, execution_id="1")
    result = registrar_resultado(
        d["dossier_id"], "positivo", directory=tmp_path,
        execution_id="1", protocol_version=d["protocol_version"],
        execution_resolver=lambda _execution_id: receipt,
    )
    assert result["accreditation"] == "ACCREDITED_EXECUTION"

    path = tmp_path / "dossiers.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if row.get("tipo") == "resultado_observado":
            row["execution_id"] = 1
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )

    assert lecciones_previas("", tmp_path, execution_resolver=lambda _id: receipt) == []


def test_execution_identity_unicode_is_exact_not_normalized(tmp_path):
    d = _dossier()
    d["candidate_id"] = "caf\u00e9"
    guardar_dossier(d, tmp_path)
    receipt = _receipt(d, execution_id="exec-unicode")
    receipt["candidate_id"] = "cafe\u0301"

    result = registrar_resultado(
        d["dossier_id"], "positivo", directory=tmp_path,
        execution_id="exec-unicode", protocol_version=d["protocol_version"],
        execution_resolver=lambda _execution_id: receipt,
    )

    assert result["accreditation"] == "DECLARED_RESULT"
    assert result["learning_eligible"] is False


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("candidate_id", 1),
        ("candidate_id", " candidate-A "),
        ("claim_id", 1),
        ("claim_id", " claim-A "),
        ("mechanism_version", 2),
        ("mechanism_version", " mv "),
        ("protocol_version", 3),
        ("protocol_version", " pv "),
    ],
)
def test_preparar_dossier_rejects_identity_coercion_and_outer_whitespace(field, bad_value):
    entry = {
        "candidate_id": "candidate-A",
        "run_id": "run-A",
        "hipotesis": "claim-A",
        "mecanismo": "mechanism-A",
        "prueba_concreta": "apply intervention A",
        "observable": "metric-A",
        "resultado_favorable_mecanismo": "metric increases",
        "resultado_favorable_alternativa": "metric does not increase",
        "regla_decision": "positive iff metric increases",
    }
    entry[field] = bad_value
    with pytest.raises(ValueError, match=field):
        preparar_dossier(entry, "problem", alternativa_explicativa="rival explanation")
