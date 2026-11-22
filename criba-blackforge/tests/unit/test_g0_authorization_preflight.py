"""G0 consistency and permission boundaries, without requests to any provider."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from benchmarks.innovation import g0_authorization_preflight as gate
from benchmarks.innovation import semantic_cases, semantic_lab


ROOT = Path(__file__).resolve().parents[3]


def _baseline():
    return gate.inspect(ROOT)


def test_reconciles_four_artifacts_and_all_development_case_digests():
    report = _baseline()
    assert report["decision"] == "NO_GO"
    assert report["case_manifest_integrity"] == "CONSISTENT_DEVELOPMENT_ONLY"
    assert len(report["artifact_integrity"]) == 4
    assert all(r["status"] == "EXACT" for r in report["artifact_integrity"].values())
    assert report["sample"] == {
        "selected": 18, "root_problems": 3,
        "labels": {"SUPPORT": 5, "REJECT": 11, "UNRESOLVED": 2},
        "schedule_slots": {"A": 16, "B": 36, "C": 108},
    }
    assert report["provider_consumption"] is None
    assert report["source_trust"] == "DEVELOPMENT_ONLY"


def test_phase_a_cannot_be_authorized_and_bc_never_auto_escalate():
    r = _baseline()
    assert r["authorization"] == "NOT_GRANTED_BY_THIS_TOOL"
    assert {r[k] for k in ("phase_A", "phase_B", "phase_C")} == {"NOT_AUTHORIZED"}
    assert r["g0_status"] == "DRAFT_NOT_APPROVED"
    assert r["p0_semantic"] == "OPEN"
    assert r["scientific_advantage"] == "NOT_ESTABLISHED"
    assert len(r["decisions"]) >= 13
    assert "INFERENCE_PERMISSION_NOT_GRANTED" in r["issues"]
    assert "S0_S1_INFORMATION_NOT_COMPARABLE" in r["issues"]
    assert "INDEPENDENT_REFERENCE_NOT_ADJUDICATED" in r["issues"]


@pytest.mark.parametrize("entry", sorted(gate._EFFECTIVE))
def test_tampered_same_size_sources_never_upgrade_to_ready(tmp_path, entry):
    root = tmp_path / "repo"
    for filename in gate._EFFECTIVE:
        dest = root / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / filename).read_bytes())
    altered = root / entry
    original = altered.read_bytes()
    altered.write_bytes(original[:-1] + (b"X" if original[-1:] != b"X" else b"Y"))
    report = gate.inspect(root)
    assert report["decision"] == "NO_GO"
    assert report["artifact_integrity"][entry]["status"] == "CHANGED"
    assert report["case_manifest_integrity"] == "NOT_VERIFIED"
    assert any(entry in issue for issue in report["issues"])


@pytest.mark.parametrize("entry", sorted(gate._EFFECTIVE))
def test_missing_critical_source_is_not_zero_or_pass(tmp_path, entry):
    root = tmp_path / "repo"
    for filename in gate._EFFECTIVE:
        if filename == entry:
            continue
        p = root / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / filename).read_bytes())
    report = gate.inspect(root)
    assert report["artifact_integrity"][entry]["status"] == "NOT_ACCESSIBLE"
    assert report["case_manifest_integrity"] == "NOT_VERIFIED"
    assert report["decision"] == "NO_GO"


@pytest.mark.parametrize("claim", [
    {"approved": True, "signature": "owner", "phase": "C", "calls": 108},
    {"approved": True, "owner": "KLSX", "contract": "READY"},
    {"signature": "fake", "budget": float("nan")},
    {},
])
def test_purported_signature_cannot_become_authorization(claim):
    result = gate.inspect(ROOT, purported_approval=claim)
    assert result["decision"] == "NO_GO"
    assert "PURPORTED_APPROVAL_NOT_AUTHENTICATED" in result["issues"]
    assert result["authorization"] == "NOT_GRANTED_BY_THIS_TOOL"
    assert result["phase_B"] == "NOT_AUTHORIZED"
    assert "owner" not in result and "signature" not in result


def test_matching_reported_comparability_status_is_still_insufficient():
    valid_shape = {"status": "BLOCKED", "authorization": "NOT_GRANTED_BY_PREFLIGHT"}
    result = gate.inspect(ROOT, phase06_report=valid_shape)
    assert result["decision"] == "NO_GO"
    assert result["decisions"]["fair_s0_s1_contract"] == "UNVERIFIED_OR_UNDECIDED"


@pytest.mark.parametrize("report", [
    {"status": "READY", "authorization": "GRANTED"},
    {"status": "BLOCKED", "authorization": "GRANTED"},
    {"status": "READY", "authorization": "NOT_GRANTED_BY_PREFLIGHT"},
    {},
    "READY",
])
def test_forged_phase06_positive_never_removes_scientific_blockers(report):
    result = gate.inspect(ROOT, phase06_report=report)
    assert "PHASE06_CLAIM_NOT_CREDIBLE" in result["issues"]
    assert result["decision"] == "NO_GO"


def test_fake_perfect_reference_matching_thresholds_are_not_approval():
    import runpy
    source = ROOT / gate._GATE_DIR / "pilot_gate.py"
    original = runpy.run_path(str(source))
    refs = original["references"]()
    schedule = original["schedule"]("A")
    fake = [{**s, "outcome": refs[s["case_id"]], "physical_calls": 1}
            for s in schedule]
    summary = original["summarize"]("A", fake)
    assert summary["status"] == "THRESHOLDS_MET_ONLY"
    assert summary["physical_calls_reported"] == 16
    assert summary["authorization"] == "NOT_GRANTED_BY_THIS_TOOL"
    assert gate.inspect(ROOT)["decision"] == "NO_GO"
    # This is a counterexample to treating a threshold as external evidence.
    assert summary["gain"] == "NO_GAIN_OBSERVED"


def test_mutating_case_semantics_without_breaking_json_is_detected(monkeypatch):
    old = semantic_cases.cases

    def corrupt():
        rows = old()
        row = next(r for r in rows if r["id"] == "CBS500-01-01:incident")
        row["proposal"]["mecanismo"] += " ADDED KEYWORD"
        return rows

    monkeypatch.setattr(semantic_cases, "cases", corrupt)
    report = _baseline()
    assert report["case_manifest_integrity"] == "FAILED"
    assert "CASE_MANIFEST_OR_GATE_INCONSISTENT" in report["issues"]
    assert report["decision"] == "NO_GO"


def test_wrong_reference_label_with_same_case_identifiers_fails(monkeypatch):
    old = semantic_cases.cases

    def altered():
        rows = old()
        rows[0]["reference"] = "SUPPORT" if rows[0]["reference"] != "SUPPORT" else "REJECT"
        return rows

    monkeypatch.setattr(semantic_cases, "cases", altered)
    result = _baseline()
    assert result["case_manifest_integrity"] == "FAILED"


def test_case_collision_and_wrong_root_distribution_fail(monkeypatch):
    old = semantic_cases.cases

    def altered():
        rows = old()
        rows[0]["id"] = rows[1]["id"]
        return rows

    monkeypatch.setattr(semantic_cases, "cases", altered)
    result = _baseline()
    assert result["case_manifest_integrity"] == "FAILED"


def test_wrong_module_import_is_not_reconciled(monkeypatch, tmp_path):
    monkeypatch.setattr(semantic_lab, "__file__", str(tmp_path / "fake_lab.py"))
    result = _baseline()
    assert result["case_manifest_integrity"] == "FAILED"
    assert "CASE_MANIFEST_OR_GATE_INCONSISTENT" in result["issues"]


def test_valid_json_with_duplicate_keys_and_nonfinite_values_rejected():
    for raw in ('{"approved":true,"approved":false}',
                '{"budget":NaN}', '{"timeout":Infinity}'):
        with pytest.raises(ValueError):
            gate._strict_json(raw)


def test_non_ascii_or_whitespace_change_triggers_sha_mismatch(tmp_path):
    name = next(x for x in gate._EFFECTIVE if x.endswith("pilot_cases.json"))
    root = tmp_path / "repo"
    for f in gate._EFFECTIVE:
        p = root / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / f).read_bytes())
    p = root / name
    p.write_bytes(p.read_bytes().replace(b'"cases":', b' "cases":', 1))
    report = gate.inspect(root)
    assert report["artifact_integrity"][name]["status"] == "CHANGED"
    assert report["decision"] == "NO_GO"


def test_no_authorization_from_editable_claim_even_with_matching_hashes():
    r = gate.inspect(ROOT, purported_approval={
        "approved": True, "sha256": {
            key: entry for key, entry in gate._EFFECTIVE.items()},
        "independent_reviewers": ["a", "b", "c"],
        "zero_retries": True, "authenticated_provider": True,
    })
    assert r["case_manifest_integrity"] == "CONSISTENT_DEVELOPMENT_ONLY"
    assert r["decision"] == "NO_GO"
    assert r["provider_consumption"] is None


def test_report_is_machine_readable_without_secret_or_backfilled_permission():
    report = _baseline()
    text = json.dumps(report, ensure_ascii=False, allow_nan=False)
    assert json.loads(text) == report
    assert "api_key" not in text and "sk-proj" not in text
    assert not any(k.endswith("_APPROVED") and report[k] is True for k in report)


def test_phase_a_substitution_with_same_length_and_prefix_is_detected(monkeypatch):
    import runpy
    old = runpy.run_path

    def altered(path):
        result = old(path)
        schedule = result["schedule"]

        def fake(phase):
            rows = schedule(phase)
            if phase in ("A", "B", "C"):
                for row in rows:
                    if row["case_id"] == "CBS500-01-01:incident":
                        row["case_id"] = "CBS500-01-01:swap"
            return rows

        result["schedule"] = fake
        return result

    monkeypatch.setattr(runpy, "run_path", altered)
    result = _baseline()
    assert result["case_manifest_integrity"] == "FAILED"
    assert result["decision"] == "NO_GO"


def test_repetition_slot_masquerading_detected(monkeypatch):
    import runpy
    old = runpy.run_path

    def altered(path):
        result = old(path)
        schedule = result["schedule"]

        def fake(phase):
            rows = schedule(phase)
            if phase == "C":
                rows[-1]["repetition"] = 1
            return rows

        result["schedule"] = fake
        return result

    monkeypatch.setattr(runpy, "run_path", altered)
    result = _baseline()
    assert result["case_manifest_integrity"] == "FAILED"


def test_fake_gate_reference_with_same_ids_detected(monkeypatch):
    import runpy
    old = runpy.run_path

    def altered(path):
        result = old(path)
        refs = result["references"]

        def fake():
            data = refs()
            data["CBS500-01-01:incident"] = "SUPPORT"
            return data

        result["references"] = fake
        return result

    monkeypatch.setattr(runpy, "run_path", altered)
    result = _baseline()
    assert result["case_manifest_integrity"] == "FAILED"


def test_sample_manifest_claimed_approved_does_not_pass(monkeypatch):
    original = gate._strict_json

    def altered(raw):
        item = original(raw)
        if isinstance(item, dict) and "reference_status" in item:
            item["status"] = "APPROVED"
        return item

    monkeypatch.setattr(gate, "_strict_json", altered)
    result = _baseline()
    assert result["case_manifest_integrity"] == "FAILED"
    assert result["authorization"] == "NOT_GRANTED_BY_THIS_TOOL"


def test_empty_other_root_and_invalid_case_still_not_accepted(monkeypatch):
    old = semantic_cases.cases

    def altered():
        rows = old()
        for row in rows:
            if row["id"].startswith("CBS500-21-01:"):
                row["parent_id"] = "CBS500-09-02"
        return rows

    monkeypatch.setattr(semantic_cases, "cases", altered)
    result = _baseline()
    assert result["case_manifest_integrity"] == "FAILED"
