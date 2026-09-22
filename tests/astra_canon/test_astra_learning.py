"""ASTRA-002/019/020: absence of evaluation is not numeric reward."""

from criba.intelligence.outcome_store import (
    CHANNEL_JUDGE,
    CHANNEL_OBSERVED,
    CHANNEL_VERDICT,
    TechniqueOutcomeStore,
)
from criba.inventar import record_outcomes


def test_astra_020_indeterminate_observation_is_persisted_but_not_reward(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
    record = store.record(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        outcome="indeterminado",
        canon_version="c",
        run_id="episode-1",
    )
    assert record["value"] is None
    assert record["learning_eligible"] is False
    prior, n, label = store.prior(
        profile="CRIBA", family="f", technique_id="T1", channel=CHANNEL_OBSERVED, canon_version="c"
    )
    assert (prior, n, label) == (0.0, 0, "sin_datos")


def test_astra_020_unresolved_verdict_is_not_reward(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
    record = store.record(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_VERDICT,
        outcome="UNRESOLVED",
        canon_version="c",
        run_id="episode-1",
    )
    assert record["value"] is None and record["learning_eligible"] is False
    assert store.prior(
        profile="CRIBA", family="f", technique_id="T1", channel=CHANNEL_VERDICT, canon_version="c"
    )[:2] == (0.0, 0)


def test_astra_020_observed_success_and_failure_remain_numeric(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
    success = store.record(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        outcome="positivo",
        canon_version="c",
        run_id="success",
    )
    failure = store.record(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        outcome="negativo",
        canon_version="c",
        run_id="failure",
    )
    assert success["value"] == 1.0 and success["learning_eligible"] is True
    assert failure["value"] == 0.0 and failure["learning_eligible"] is True


def test_astra_020_pending_judge_is_not_persisted_as_valid_zero(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
    sheet = {
        "run_id": "r",
        "entries": [
            {
                "run_id": "r",
                "classes": ["f"],
                "method_ids": ["M1"],
                "aportacion_por_tecnica": [],
                "prior_art": {"verdict": "UNRESOLVED"},
                "judge": {
                    "veredicto": "PENDIENTE_OFFLINE",
                    "score": None,
                    "evaluation_status": "NOT_EVALUATED",
                },
            }
        ],
    }
    record_outcomes(sheet, store, canon_version="c")
    assert not [row for row in store._read_valid() if row["channel"] == CHANNEL_JUDGE]
