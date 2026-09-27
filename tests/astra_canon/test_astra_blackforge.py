"""BLACKFORGE sentinels for ASTRA-011/012/013/022/026/030/031."""

import pytest

from criba import blackforge_selector
from criba.blackforge_orthogonal.compositor import Composition, CompositionMode


def _record(identity, stage, category, source, axis, *, safety="S1_DEFENSIVE", score=1.0):
    return {
        "blackforge_id": identity,
        "activation_tier": "core",
        "safety_class": safety,
        "profile_hybrid": score,
        "diversity_contribution_v2": 0.5,
        "selection_weight": 1.0,
        "functional_category_primary": category,
        "source_family": source,
        "source_catalog": source,
        "causal_axis_primary": axis,
        "pipeline_stage": stage,
        "requires_sandbox": safety in {"S2_SANDBOX", "S3_HIGH_CONTROL"},
        "requires_explicit_authorization": safety in {"S2_SANDBOX", "S3_HIGH_CONTROL"},
        "external_target_prohibited": safety in {"S2_SANDBOX", "S3_HIGH_CONTROL"},
    }


def _catalog():
    constraints = {
        "maximum_per_primary_category": 4,
        "maximum_per_source_family": 4,
        "maximum_unknown_causal_axis": 0,
        "minimum_source_catalogs": 1,
        "minimum_primary_categories": 1,
        "minimum_causal_axes": 1,
    }
    records = [
        _record("BF-1", "ROMPER", "c1", "s1", "a1"),
        _record("BF-2", "DIVERGIR", "c2", "s2", "a2"),
        _record("BF-3", "ATACAR", "c3", "s3", "a3", score=0.9),
        _record("BF-4", "EVALUAR", "c4", "s4", "a4", score=0.8),
        _record("BF-S3", "ROMPER", "c5", "s5", "a5", safety="S3_HIGH_CONTROL", score=999.0),
    ]
    return {
        "selection_policy": {"allowed_tiers_default": ["core"], "constraints": constraints}
    }, records


def test_astra_011_preference_never_overrides_blackforge_eligibility(monkeypatch):
    monkeypatch.setattr(blackforge_selector, "_load_catalog", _catalog)
    report = blackforge_selector.select_blackforge(session_size=4)
    assert report.status_ok()
    assert "BF-S3" not in report.selected_ids
    assert report.s3_count == 0


def test_astra_012_ties_and_operational_tiebreak_are_reported(monkeypatch):
    monkeypatch.setattr(blackforge_selector, "_load_catalog", _catalog)
    report = blackforge_selector.select_blackforge(session_size=4)
    assert ["BF-1", "BF-2"] in report.tie_sets
    assert "not scientific superiority" in report.tiebreak_rule
    assert report.selected_ids.index("BF-1") < report.selected_ids.index("BF-2")


def test_astra_030_signature_projection_preserves_every_selected_axis():
    selected = {"AX-01": "INVERTIR", "AX-03": "ADVERSARIO", "AX-07": "CONTRAFACTUAL"}
    composition = Composition(
        selected_axes=selected,
        mode=CompositionMode.COUNTERFACTUAL,
        coverage_score=0.0,
        distance_score=0.0,
        novelty_estimate=0.0,
    )
    assert composition.to_signature().coordinates == {
        axis: (value,) for axis, value in selected.items()
    }


def test_astra_unknown_or_nonfinite_blackforge_score_fails_closed(monkeypatch):
    for bad in (None, float("nan"), float("inf"), "1.0", True):
        meta, records = _catalog()
        records[0]["profile_hybrid"] = bad
        monkeypatch.setattr(blackforge_selector, "_load_catalog", lambda m=meta, r=records: (m, r))
        report = blackforge_selector.select_blackforge(session_size=4)
        assert not report.status_ok()
        assert report.failure is not None
        assert report.failure.failed_quota == "ranking_signal_integrity"
        assert report.selected_ids == []


def test_astra_failed_blackforge_quota_never_exposes_partial_selection(monkeypatch):
    meta, records = _catalog()
    # Remove one mandatory stage while keeping enough records to fill the session.
    records[3]["pipeline_stage"] = "ROMPER"
    monkeypatch.setattr(blackforge_selector, "_load_catalog", lambda: (meta, records))
    report = blackforge_selector.select_blackforge(session_size=4)
    assert not report.status_ok()
    assert report.failure is not None
    assert report.failure.failed_quota == "mandatory_stages"
    assert report.selected_ids == []
    assert report.to_dict()["selected_count"] == 0


def test_astra_blackforge_rejects_duplicate_candidate_identity(monkeypatch):
    meta, records = _catalog()
    records[1]["blackforge_id"] = records[0]["blackforge_id"]
    monkeypatch.setattr(blackforge_selector, "_load_catalog", lambda: (meta, records))
    report = blackforge_selector.select_blackforge(session_size=4)
    assert not report.status_ok()
    assert report.failure is not None
    assert report.failure.failed_quota == "candidate_identity_integrity"
    assert report.selected_ids == []


def test_astra_blackforge_rejects_zero_session_size(monkeypatch):
    monkeypatch.setattr(blackforge_selector, "_load_catalog", _catalog)
    report = blackforge_selector.select_blackforge(session_size=0)
    assert not report.status_ok()
    assert report.failure is not None
    assert report.failure.failed_quota == "session_size_integrity"
    assert report.selected_ids == []

@pytest.mark.parametrize("field,value", [
    ("maximum_per_primary_category", -1),
    ("maximum_per_source_family", True),
    ("maximum_unknown_causal_axis", float("nan")),
    ("minimum_source_catalogs", "3"),
    ("minimum_primary_categories", None),
    ("minimum_causal_axes", float("inf")),
])
def test_selector_rejects_malformed_policy_constraints(monkeypatch, field, value):
    meta, recs = blackforge_selector._load_catalog()
    meta = dict(meta)
    policy = dict(meta.get("selection_policy", {}))
    constraints = dict(policy.get("constraints", {}))
    constraints[field] = value
    policy["constraints"] = constraints
    meta["selection_policy"] = policy
    monkeypatch.setattr(blackforge_selector, "_load_catalog", lambda: (meta, recs))
    report = blackforge_selector.select_blackforge(session_size=4)
    assert not report.status_ok()
    assert report.failure is not None
    assert report.failure.failed_quota == "selection_policy_integrity"
    assert report.selected_ids == []


@pytest.mark.parametrize("tiers", ["core", ["core", "bogus"], ["core", "core"], ["core", 3], []])
def test_selector_rejects_malformed_allowed_tiers(tiers):
    report = blackforge_selector.select_blackforge(session_size=4, allowed_tiers=tiers)
    assert not report.status_ok()
    assert report.failure is not None
    assert report.failure.failed_quota == "allowed_tiers_integrity"
    assert report.selected_ids == []

@pytest.mark.parametrize("field,value", [
    ("activation_tier", "bogus"),
    ("safety_class", "UNKNOWN_SAFE"),
    ("pipeline_stage", "UNKNOWN_STAGE"),
])
def test_selector_rejects_malformed_candidate_control_fields(monkeypatch, field, value):
    meta, records = _catalog()
    records[0][field] = value
    monkeypatch.setattr(blackforge_selector, "_load_catalog", lambda: (meta, records))
    report = blackforge_selector.select_blackforge(session_size=4)
    assert not report.status_ok()
    assert report.failure is not None
    assert report.failure.failed_quota == "candidate_control_integrity"
    assert report.selected_ids == []

@pytest.mark.parametrize("field,value", [
    ("status", "disabled"),
    ("status", "ACTIVE"),
    ("requires_sandbox", "yes"),
    ("requires_explicit_authorization", 1),
    ("external_target_prohibited", "false"),
])
def test_selector_rejects_malformed_candidate_policy_controls(monkeypatch, field, value):
    meta, records = _catalog()
    for record in records:
        record[field] = value
    monkeypatch.setattr(blackforge_selector, "_load_catalog", lambda: (meta, records))
    report = blackforge_selector.select_blackforge(session_size=4)
    assert not report.status_ok()
    assert report.failure is not None
    assert report.failure.failed_quota == "candidate_control_integrity"
    assert report.selected_ids == []

@pytest.mark.parametrize("field", [
    "requires_sandbox",
    "requires_explicit_authorization",
    "external_target_prohibited",
])
def test_selector_rejects_high_control_candidate_with_disabled_required_control(monkeypatch, field):
    meta, records = _catalog()
    high = records[-1]
    high[field] = False
    monkeypatch.setattr(blackforge_selector, "_load_catalog", lambda: (meta, records))
    report = blackforge_selector.select_blackforge(
        session_size=4,
        explicit_high_control_approval=True,
        authorized_scope_confirmed=True,
        sandbox_available=True,
    )
    assert not report.status_ok()
    assert report.failure is not None
    assert report.failure.failed_quota == "candidate_control_integrity"
    assert report.selected_ids == []

@pytest.mark.parametrize("field", [
    "requires_sandbox",
    "requires_explicit_authorization",
    "external_target_prohibited",
])
def test_selector_rejects_high_control_candidate_with_missing_required_control(monkeypatch, field):
    meta, records = _catalog()
    high = records[-1]
    high.pop(field, None)
    monkeypatch.setattr(blackforge_selector, "_load_catalog", lambda: (meta, records))
    report = blackforge_selector.select_blackforge(
        session_size=4,
        explicit_high_control_approval=True,
        authorized_scope_confirmed=True,
        sandbox_available=True,
    )
    assert not report.status_ok()
    assert report.failure is not None
    assert report.failure.failed_quota == "candidate_control_integrity"
    assert report.selected_ids == []
