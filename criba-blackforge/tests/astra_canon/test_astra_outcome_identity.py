"""ASTRA-021/022: stable episode identity, corrections, and temporal replay."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from criba.intelligence.outcome_store import CHANNEL_OBSERVED, TechniqueOutcomeStore

BASE = datetime(2026, 1, 2, tzinfo=timezone.utc)


def record(store, outcome, when, run="episode-1"):
    return store.record(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        outcome=outcome,
        canon_version="c",
        run_id=run,
        recorded_at=when,
    )


def test_astra_021_same_observation_twice_is_same_statistical_evidence(tmp_path):
    once = TechniqueOutcomeStore(tmp_path / "once.jsonl")
    twice = TechniqueOutcomeStore(tmp_path / "twice.jsonl")
    record(once, "positivo", BASE)
    record(twice, "positivo", BASE)
    record(twice, "positivo", BASE + timedelta(days=10))
    assert once.prior(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        canon_version="c",
        now=BASE + timedelta(days=20),
    ) == twice.prior(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        canon_version="c",
        now=BASE + timedelta(days=20),
    )


def test_astra_021_correction_replaces_value_without_new_sample_or_recency(tmp_path):
    corrected = TechniqueOutcomeStore(tmp_path / "corrected.jsonl")
    reference = TechniqueOutcomeStore(tmp_path / "reference.jsonl")
    record(corrected, "positivo", BASE)
    record(corrected, "negativo", BASE + timedelta(days=10))
    record(reference, "negativo", BASE)
    assert corrected.prior(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        canon_version="c",
        now=BASE + timedelta(days=20),
    ) == reference.prior(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        canon_version="c",
        now=BASE + timedelta(days=20),
    )


def test_astra_021_future_observation_is_unavailable_to_historical_replay(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "future.jsonl")
    record(store, "positivo", BASE + timedelta(days=1))
    assert store.prior(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        canon_version="c",
        now=BASE,
    ) == (0.0, 0, "sin_datos")


def test_astra_b01_reexport_same_episode_survives_restart_without_new_sample_or_recency(tmp_path):
    path = tmp_path / "restart.jsonl"
    first = TechniqueOutcomeStore(path)
    record(first, "positivo", BASE)
    record(first, "positivo", BASE + timedelta(days=10))

    restarted = TechniqueOutcomeStore(path)
    reference = TechniqueOutcomeStore(tmp_path / "reference-restart.jsonl")
    record(reference, "positivo", BASE)

    assert restarted.prior(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        canon_version="c",
        now=BASE + timedelta(days=20),
    ) == reference.prior(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        canon_version="c",
        now=BASE + timedelta(days=20),
    )


def test_astra_b01_correction_survives_restart_as_one_episode(tmp_path):
    path = tmp_path / "corrected-restart.jsonl"
    store = TechniqueOutcomeStore(path)
    record(store, "positivo", BASE)
    record(store, "negativo", BASE + timedelta(days=10))

    restarted = TechniqueOutcomeStore(path)
    prior = restarted.prior(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        canon_version="c",
        now=BASE + timedelta(days=20),
    )
    reference = TechniqueOutcomeStore(tmp_path / "negative-reference.jsonl")
    record(reference, "negativo", BASE)
    assert prior == reference.prior(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        canon_version="c",
        now=BASE + timedelta(days=20),
    )


def test_astra_b03_legacy_reward_is_preserved_on_disk_but_invalidated_after_restart(tmp_path):
    path = tmp_path / "legacy.jsonl"
    legacy = {
        "profile": "CRIBA",
        "family": "f",
        "technique_id": "T1",
        "channel": CHANNEL_OBSERVED,
        "outcome": "positivo",
        "value": 1.0,
        "learning_eligible": True,
        "canon_version": "c",
        "run_id": "legacy-run",
        "recorded_at": BASE.isoformat(),
    }
    path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

    restarted = TechniqueOutcomeStore(path)
    with pytest.warns(RuntimeWarning, match="revalidación semántica"):
        assert restarted.prior(
            profile="CRIBA",
            family="f",
            technique_id="T1",
            channel=CHANNEL_OBSERVED,
            canon_version="c",
            now=BASE + timedelta(days=1),
        ) == (0.0, 0, "sin_datos")

    raw = path.read_text(encoding="utf-8")
    assert '"value": 1.0' in raw
    assert '"learning_eligible": true' in raw.lower()


def test_astra_b01_no_run_id_is_preserved_but_never_learning_evidence(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "no-id.jsonl")
    record = store.record(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        outcome="positivo",
        canon_version="c",
        recorded_at=BASE,
    )
    assert record["value"] == 1.0
    assert record["identity_eligible"] is False
    assert record["learning_eligible"] is False
    assert record["learning_invalidation_reason"] == "STABLE_RUN_ID_REQUIRED"
    assert store.prior(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        canon_version="c",
        now=BASE + timedelta(days=1),
    ) == (0.0, 0, "sin_datos")


def test_astra_b01_summary_does_not_count_unidentified_rows_as_samples(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "summary-no-id.jsonl")
    store.record(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        outcome="positivo",
        canon_version="c",
        recorded_at=BASE,
    )
    summary = store.summary(profile="CRIBA", canon_version="c")
    assert len(summary) == 1
    assert summary[0]["n"] == 0
    assert summary[0]["unidentified_records"] == 1
    assert summary[0]["value"] is None

def test_astra_b03_naive_timestamp_is_preserved_but_excluded_after_restart(tmp_path):
    path = tmp_path / "naive-timestamp.jsonl"
    row = {
        "profile": "CRIBA",
        "family": "f",
        "technique_id": "T1",
        "channel": CHANNEL_OBSERVED,
        "outcome": "positivo",
        "value": 1.0,
        "learning_eligible": True,
        "canon_version": "c",
        "outcome_semantics_version": 2,
        "run_id": "naive-run",
        "recorded_at": "2026-01-02T00:00:00",
    }
    raw = json.dumps(row) + "\n"
    path.write_text(raw, encoding="utf-8")

    restarted = TechniqueOutcomeStore(path)
    with pytest.warns(RuntimeWarning, match="malformadas"):
        assert restarted.prior(
            profile="CRIBA",
            family="f",
            technique_id="T1",
            channel=CHANNEL_OBSERVED,
            canon_version="c",
            now=BASE + timedelta(days=1),
        ) == (0.0, 0, "sin_datos")

    assert path.read_text(encoding="utf-8") == raw


def test_astra_b03_writer_rejects_naive_recorded_at(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "writer-naive.jsonl")
    with pytest.raises(ValueError, match="zona horaria"):
        record(store, "positivo", datetime(2026, 1, 2))
    assert not store.path.exists()

