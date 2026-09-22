"""Mutation sentinels for ASTRA scorer, UNKNOWN and credit-assignment contracts."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from criba.diversity_selector import select_finalists
from criba.engine import _BASE_VALUES, _evaluate_idea
from criba.inventar import record_outcomes
from criba.intelligence.outcome_store import CHANNEL_OBSERVED, TechniqueOutcomeStore
from criba.similarity import genome_distance


NOW = datetime(2026, 1, 2, tzinfo=timezone.utc)


def _idea(*, name1="A", name2="B", desc1="x", desc2="y", axes=None):
    cv = dict(_BASE_VALUES)
    if axes:
        cv.update(axes)
    return {
        "causal_variables": cv,
        "method1_name": name1,
        "method2_name": name2,
        "method1_desc": desc1,
        "method2_desc": desc2,
        "family": "f1",
        "family2": "f2",
        "extreme": False,
    }


def test_astra_007_text_padding_cannot_raise_score():
    axes = {"quien_decide": "algoritmo", "evidencia_requerida": "adversarial"}
    concise = _idea(axes=axes)
    padded = _idea(
        name1="A" * 500,
        name2="B" * 500,
        desc1="scientific " * 500,
        desc2="validated causal novelty " * 500,
        axes=axes,
    )
    assert _evaluate_idea(concise) == _evaluate_idea(padded)


def test_astra_002_missing_axes_are_unknown_not_moved():
    absent = _idea()
    absent["causal_variables"] = {}
    result = _evaluate_idea(absent)
    assert result["novelty"] == 0.0
    assert result["evidence"] == pytest.approx(0.3)


def test_astra_009_deleting_information_cannot_create_genome_distance():
    full_a = {
        "mechanism": ["m"],
        "trust_model": ["t"],
        "topology": ["x"],
        "actor": ["a"],
        "time_model": ["now"],
    }
    full_b = dict(full_a)
    partial_b = {"mechanism": ["m"], "trust_model": ["t"]}
    full = genome_distance(full_a, full_b)
    partial = genome_distance(full_a, partial_b)
    assert full["distance"] == 0.0
    assert partial["distance"] == 0.0
    assert partial["similarity"] == 1.0
    assert partial["coverage"] < full["coverage"]


def test_astra_020_unparseable_timestamp_is_preserved_but_excluded(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "outcomes.jsonl")
    store.path.write_text(
        json.dumps(
            {
                "profile": "CRIBA",
                "family": "f",
                "technique_id": "T1",
                "channel": CHANNEL_OBSERVED,
                "outcome": "positivo",
                "value": 1.0,
                "learning_eligible": True,
                "canon_version": "c",
                "run_id": "r1",
                "recorded_at": "not-a-time",
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
            channel=CHANNEL_OBSERVED,
            canon_version="c",
            now=NOW,
        ) == (0.0, 0, "sin_datos")
    assert "not-a-time" in store.path.read_text(encoding="utf-8")


def test_astra_022_shared_candidate_outcome_is_not_individual_learning(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "outcomes.jsonl")
    sheet = {
        "run_id": "run-shared",
        "entries": [
            {
                "candidate_id": "c1",
                "run_id": "run-shared",
                "classes": ["f1", "f2"],
                "method_ids": ["T1", "T2"],
                "aportacion_por_tecnica": [],
                "prior_art": {"verdict": "SURVIVED_SEARCH"},
                "judge": {
                    "score": 0.9,
                    "evaluation_status": "EVALUATED",
                    "veredicto": "OK",
                },
            }
        ],
    }
    assert record_outcomes(sheet, store, canon_version="c") == 0
    assert store._read_valid() == []


def test_astra_022_single_identifiable_component_may_learn(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "outcomes.jsonl")
    sheet = {
        "run_id": "run-single",
        "entries": [
            {
                "candidate_id": "c1",
                "run_id": "run-single",
                "classes": ["f1"],
                "method_ids": ["T1"],
                "aportacion_por_tecnica": [],
                "prior_art": {"verdict": "SURVIVED_SEARCH"},
                "judge": {"score": None, "evaluation_status": "NOT_EVALUATED", "veredicto": "PENDIENTE"},
            }
        ],
    }
    assert record_outcomes(sheet, store, canon_version="c") == 2
    rows = store._read_valid()
    assert {row["technique_id"] for row in rows} == {"T1", "__family__"}


def test_astra_012_criba_reports_operational_score_ties():
    genome = {
        "mechanism": ["m"],
        "trust_model": ["t"],
        "topology": ["x"],
        "actor": ["a"],
        "time_model": ["now"],
    }
    pool = [
        {"idea_id": "A", "score": 1.0, "genome": genome, "family": "f"},
        {"idea_id": "B", "score": 1.0, "genome": genome, "family": "f"},
    ]
    _selected, report = select_finalists(pool, 1)
    assert ["A", "B"] in report["tie_sets"]
    assert "not scientific superiority" in report["tiebreak_rule"]


def test_astra_021_summary_counts_episode_corrections_once(tmp_path):
    store = TechniqueOutcomeStore(tmp_path / "outcomes.jsonl")
    store.record(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        outcome="positivo",
        canon_version="c",
        run_id="same-run",
        recorded_at=NOW,
    )
    store.record(
        profile="CRIBA",
        family="f",
        technique_id="T1",
        channel=CHANNEL_OBSERVED,
        outcome="negativo",
        canon_version="c",
        run_id="same-run",
        recorded_at=NOW,
    )
    summary = store.summary(profile="CRIBA", canon_version="c")
    assert sum(row["n"] for row in summary) == 1
    assert summary[0]["outcome"] == "negativo"
