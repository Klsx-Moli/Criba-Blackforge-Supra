"""Tests for SUPRA Project State Manager and Models."""

import json
import tempfile
from pathlib import Path

import pytest

from supra_agentic.models import (
    RESTRICTED_EXECUTION_SEMANTICS_VERSION,
    RestrictedExecutionResult,
    StrategyCandidate,
    StructuredDecomposition,
    Subtask,
    TaskmasterStage,
    VerificationReport,
    candidate_execution_identity,
)
from supra_agentic.state import ProjectStateManager


def test_project_lifecycle_transitions():
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = ProjectStateManager(storage_dir=tmpdir)
        p = sm.create_project(objective="Design an autonomous zero-trust authentication protocol")

        assert p.stage == TaskmasterStage.RECEIVED
        assert p.objective == "Design an autonomous zero-trust authentication protocol"
        assert len(p.checkpoints) == 1

        # Stage 2: Decomposition
        decomp = StructuredDecomposition(
            domain="cybersecurity",
            core_objective="Zero-trust authentication without static secrets",
            invariants=["Memory safety", "Zero-leakage"],
            mutable_assumptions=["Centralized LDAP", "Bearer tokens"],
            risk_factors=["Replay attacks"],
            subtasks=[
                Subtask(
                    title="Formulate ephemeral challenge",
                    description="Challenge-response without stored secrets",
                    stage_target=TaskmasterStage.STRATIFIED,
                )
            ],
        )
        p2 = sm.update_decomposition(p.project_id, decomp)
        assert p2.stage == TaskmasterStage.STRUCTURED
        assert p2.decomposition is not None
        assert len(p2.checkpoints) == 2

        # Stage 3: Candidates
        cand1 = StrategyCandidate(
            pathway_name="Ephemeral Asymmetric Prover",
            paradigm_type="ORTHOGONAL",
            hypothesis="Zero-knowledge handshake eliminates bearer credential interception.",
            action_plan=["Generate ephemeral keypair", "Verify proof"],
            divergence_score=0.75,
            feasibility_score=0.88,
        )
        cand2 = StrategyCandidate(
            pathway_name="Rotating SMS OTP",
            paradigm_type="CONSERVATIVE",
            hypothesis="Standard OTP rotation.",
            action_plan=["Send SMS code"],
            divergence_score=0.10,
            feasibility_score=0.95,
        )
        p3 = sm.add_candidates(p.project_id, [cand1, cand2], select_best=True)
        assert p3.stage == TaskmasterStage.STRATIFIED
        assert p3.selected_candidate is not None
        assert p3.selected_candidate.pathway_name == "Ephemeral Asymmetric Prover"
        assert len(p3.checkpoints) == 3

        # Stage 4: Verification
        v_rep = VerificationReport(
            candidate_id=cand1.candidate_id,
            invariants_preserved=True,
            invariants_checked=["Memory safety", "Zero-leakage"],
            vulnerabilities_detected=[],
            confidence_score=0.96,
            verdict="PASS",
            rationale="Proof verified without memory mutations.",
        )
        sm.record_verification(p.project_id, v_rep)

        # Stage 4b: trusted restricted execution
        expected_identity = candidate_execution_identity(cand1)
        attempt_id, attempt_generation = sm.issue_restricted_execution_attempt(p.project_id)
        execution_result = RestrictedExecutionResult(
            attempt_id=attempt_id, attempt_generation=attempt_generation,
            candidate_id=expected_identity["candidate_id"],
            mechanism_version=expected_identity["mechanism_version"],
            claim_id=expected_identity["claim_id"],
            protocol_version="sha256:" + "0" * 64,
            execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION,
            action_type="RESTRICTED_CODE_RUN",
            passed=True,
            output_log="Restricted internal assertions passed.",
            duration_ms=4.2,
        )
        p4 = sm.record_restricted_execution(p.project_id, execution_result)
        assert p4.stage == TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED
        assert len(p4.restricted_execution_results) == 1

        # Stage 5: Completion
        final_doc = {
            "deliverable": "Zero-Trust Ephemeral Prover Protocol v1",
            "audit_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        }
        p5 = sm.complete_project(p.project_id, final_doc)
        assert p5.stage == TaskmasterStage.COMPLETED
        assert p5.final_output == final_doc
        assert len(p5.checkpoints) == 6

        # Persistence check: load in fresh instance
        sm2 = ProjectStateManager(storage_dir=tmpdir)
        loaded = sm2.get_project(p.project_id)
        assert loaded is not None
        assert loaded.stage == TaskmasterStage.COMPLETED
        assert loaded.selected_candidate.pathway_name == "Ephemeral Asymmetric Prover"


def test_latest_restricted_revision_replaces_prior_pass():
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = ProjectStateManager(storage_dir=tmpdir)
        p = sm.create_project(objective="revision semantics")
        cand = StrategyCandidate(
            pathway_name="Path",
            paradigm_type="ORTHOGONAL",
            hypothesis="Current candidate hypothesis",
            action_plan=["step"],
            divergence_score=0.5,
            feasibility_score=0.5,
        )
        posture = sm.add_candidates(p.project_id, [cand], select_best=True)
        selected = posture.selected_candidate
        assert selected is not None
        identity = candidate_execution_identity(selected)

        attempt_id, attempt_generation = sm.issue_restricted_execution_attempt(p.project_id)
        passed = RestrictedExecutionResult(
            attempt_id=attempt_id, attempt_generation=attempt_generation,
            candidate_id=identity["candidate_id"],
            mechanism_version=identity["mechanism_version"],
            claim_id=identity["claim_id"],
            protocol_version="sha256:" + "0" * 64,
            execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION,
            action_type="RESTRICTED_CODE_RUN",
            passed=True,
            output_log="pass",
            duration_ms=1.0,
        )
        assert sm.record_restricted_execution(p.project_id, passed).stage == (
            TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED
        )

        attempt_id, attempt_generation = sm.issue_restricted_execution_attempt(p.project_id)
        failed = RestrictedExecutionResult(
            attempt_id=attempt_id, attempt_generation=attempt_generation,
            candidate_id=identity["candidate_id"],
            mechanism_version=identity["mechanism_version"],
            claim_id=identity["claim_id"],
            protocol_version="sha256:" + "0" * 64,
            execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION,
            action_type="RESTRICTED_CODE_RUN",
            passed=False,
            output_log="fail",
            duration_ms=1.0,
        )
        revised = sm.record_restricted_execution(p.project_id, failed)
        assert revised.stage == TaskmasterStage.STRATIFIED
        assert [item.passed for item in revised.restricted_execution_results] == [True, False]


def test_completed_workflow_preserves_completion_but_latest_failure_revises_execution_cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = ProjectStateManager(storage_dir=tmpdir)
        p = sm.create_project(objective="completed revision semantics")
        cand = StrategyCandidate(
            pathway_name="Path",
            paradigm_type="ORTHOGONAL",
            hypothesis="Current candidate hypothesis",
            action_plan=["step"],
            divergence_score=0.5,
            feasibility_score=0.5,
        )
        posture = sm.add_candidates(p.project_id, [cand], select_best=True)
        selected = posture.selected_candidate
        assert selected is not None
        identity = candidate_execution_identity(selected)

        def _result(passed: bool) -> RestrictedExecutionResult:
            attempt_id, attempt_generation = sm.issue_restricted_execution_attempt(p.project_id)
            return RestrictedExecutionResult(
                attempt_id=attempt_id, attempt_generation=attempt_generation,
                candidate_id=identity["candidate_id"],
                mechanism_version=identity["mechanism_version"],
                claim_id=identity["claim_id"],
                protocol_version="sha256:" + "0" * 64,
                execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION,
                action_type="RESTRICTED_CODE_RUN",
                passed=passed,
                output_log="pass" if passed else "fail",
                duration_ms=1.0,
            )

        sm.record_verification(
            p.project_id,
            VerificationReport(candidate_id=selected.candidate_id, verdict="PASS"),
        )
        sm.record_restricted_execution(p.project_id, _result(True))
        completed = sm.complete_project(
            p.project_id,
            {
                "workflow_status": "COMPLETED",
                "restricted_execution_identity_bound": True,
                "restricted_execution_status": "BOUND_PASS",
            },
        )
        assert completed.stage == TaskmasterStage.COMPLETED

        revised = sm.record_restricted_execution(p.project_id, _result(False))
        assert revised.stage == TaskmasterStage.STRATIFIED
        assert revised.final_output["workflow_status"] == "EVIDENCE_INVALIDATED"
        assert revised.final_output is not None
        assert revised.final_output["restricted_execution_status"] == "BOUND_FAIL"
        assert revised.final_output["restricted_execution_identity_bound"] is True
        assert revised.final_output["derived_execution_state_revalidated"] is True


def test_strategy_candidate_rejects_nonfinite_or_out_of_range_scores():
    import math
    import pytest
    from pydantic import ValidationError
    for field in ("feasibility_score", "divergence_score"):
        for value in (float("nan"), float("inf"), float("-inf"), -0.01, 1.01):
            kwargs = dict(pathway_name="x", paradigm_type="ORTHOGONAL", hypothesis="h")
            kwargs[field] = value
            with pytest.raises(ValidationError):
                StrategyCandidate(**kwargs)


def test_add_candidates_rejects_duplicate_identity_before_selection():
    import pytest
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = ProjectStateManager(storage_dir=tmpdir)
        p = sm.create_project(objective="identity sentinel")
        c1 = StrategyCandidate(candidate_id="cand-same", pathway_name="A", paradigm_type="ORTHOGONAL", hypothesis="h1")
        c2 = StrategyCandidate(candidate_id="cand-same", pathway_name="B", paradigm_type="LATERAL", hypothesis="h2")
        with pytest.raises(ValueError, match="duplicate candidate_id"):
            sm.add_candidates(p.project_id, [c1, c2])
        reloaded = sm.get_project(p.project_id)
        assert reloaded is not None
        assert reloaded.candidates == []
        assert reloaded.selected_candidate is None
        assert reloaded.stage == TaskmasterStage.RECEIVED


def test_strategy_candidate_identity_and_enum_fail_closed():
    import pytest
    from pydantic import ValidationError
    for candidate_id in ("", "   "):
        with pytest.raises(ValidationError):
            StrategyCandidate(candidate_id=candidate_id, pathway_name="x", paradigm_type="ORTHOGONAL", hypothesis="h")
    with pytest.raises(ValidationError):
        StrategyCandidate(pathway_name="x", paradigm_type="UNKNOWN", hypothesis="h")


def test_stale_distinct_execution_cannot_override_newer_authoritative_generation_after_restart():
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = ProjectStateManager(storage_dir=tmpdir)
        p = sm.create_project(objective="causal authority")
        cand = StrategyCandidate(pathway_name="Path", paradigm_type="ORTHOGONAL", hypothesis="h", action_plan=["step"], divergence_score=0.5, feasibility_score=0.5)
        selected = sm.add_candidates(p.project_id, [cand], select_best=True).selected_candidate
        assert selected is not None
        identity = candidate_execution_identity(selected)

        a1, g1 = sm.issue_restricted_execution_attempt(p.project_id)
        old_pass = RestrictedExecutionResult(attempt_id=a1, attempt_generation=g1, candidate_id=identity["candidate_id"], mechanism_version=identity["mechanism_version"], claim_id=identity["claim_id"], protocol_version="sha256:" + "0" * 64, execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION, action_type="RESTRICTED_CODE_RUN", passed=True, output_log="old pass", duration_ms=1)
        assert sm.record_restricted_execution(p.project_id, old_pass).stage is TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED

        a2, g2 = sm.issue_restricted_execution_attempt(p.project_id)
        new_fail = RestrictedExecutionResult(attempt_id=a2, attempt_generation=g2, candidate_id=identity["candidate_id"], mechanism_version=identity["mechanism_version"], claim_id=identity["claim_id"], protocol_version="sha256:" + "0" * 64, execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION, action_type="RESTRICTED_CODE_RUN", passed=False, output_log="new fail", duration_ms=1)
        assert sm.record_restricted_execution(p.project_id, new_fail).stage is TaskmasterStage.STRATIFIED

        delayed_old = old_pass.model_copy(update={"execution_id": "exec-delayed"})
        assert sm.record_restricted_execution(p.project_id, delayed_old).stage is TaskmasterStage.STRATIFIED
        assert sm.get_project(p.project_id).restricted_execution_results[-1].identity_bound is False

        reloaded = ProjectStateManager(storage_dir=tmpdir).get_project(p.project_id)
        assert reloaded is not None
        assert reloaded.stage is TaskmasterStage.STRATIFIED


def test_stale_failure_after_new_pass_stays_completed_authority_after_restart():
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = ProjectStateManager(storage_dir=tmpdir)
        p = sm.create_project(objective="causal pass authority")
        cand = StrategyCandidate(pathway_name="Path", paradigm_type="ORTHOGONAL", hypothesis="h", action_plan=["step"], divergence_score=0.5, feasibility_score=0.5)
        selected = sm.add_candidates(p.project_id, [cand], select_best=True).selected_candidate
        identity = candidate_execution_identity(selected)
        a1, g1 = sm.issue_restricted_execution_attempt(p.project_id)
        stale_fail = RestrictedExecutionResult(attempt_id=a1, attempt_generation=g1, candidate_id=identity["candidate_id"], mechanism_version=identity["mechanism_version"], claim_id=identity["claim_id"], protocol_version="sha256:" + "0" * 64, execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION, action_type="RESTRICTED_CODE_RUN", passed=False, output_log="old fail", duration_ms=1)
        a2, g2 = sm.issue_restricted_execution_attempt(p.project_id)
        current_pass = RestrictedExecutionResult(attempt_id=a2, attempt_generation=g2, candidate_id=identity["candidate_id"], mechanism_version=identity["mechanism_version"], claim_id=identity["claim_id"], protocol_version="sha256:" + "0" * 64, execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION, action_type="RESTRICTED_CODE_RUN", passed=True, output_log="new pass", duration_ms=1)
        assert sm.record_restricted_execution(p.project_id, current_pass).stage is TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED
        assert sm.record_restricted_execution(p.project_id, stale_fail).stage is TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED
        reloaded = ProjectStateManager(storage_dir=tmpdir).get_project(p.project_id)
        assert reloaded.stage is TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED


def test_completion_gate_uses_current_attempt_not_last_arrival_after_restart():
    """A stale PASS must not become completion authority merely by arriving last."""
    import pytest
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = ProjectStateManager(storage_dir=tmpdir)
        p = sm.create_project(objective="completion causal authority")
        cand = StrategyCandidate(pathway_name="Path", paradigm_type="ORTHOGONAL", hypothesis="h", action_plan=["step"], divergence_score=0.5, feasibility_score=0.5)
        selected = sm.add_candidates(p.project_id, [cand], select_best=True).selected_candidate
        assert selected is not None
        identity = candidate_execution_identity(selected)
        sm.record_verification(p.project_id, VerificationReport(candidate_id=selected.candidate_id, verdict="PASS"))

        a1, g1 = sm.issue_restricted_execution_attempt(p.project_id)
        old_pass = RestrictedExecutionResult(attempt_id=a1, attempt_generation=g1, candidate_id=identity["candidate_id"], mechanism_version=identity["mechanism_version"], claim_id=identity["claim_id"], protocol_version="sha256:" + "0" * 64, execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION, action_type="RESTRICTED_CODE_RUN", passed=True, output_log="old pass", duration_ms=1)
        sm.record_restricted_execution(p.project_id, old_pass)

        a2, g2 = sm.issue_restricted_execution_attempt(p.project_id)
        current_fail = RestrictedExecutionResult(attempt_id=a2, attempt_generation=g2, candidate_id=identity["candidate_id"], mechanism_version=identity["mechanism_version"], claim_id=identity["claim_id"], protocol_version="sha256:" + "0" * 64, execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION, action_type="RESTRICTED_CODE_RUN", passed=False, output_log="current fail", duration_ms=1)
        sm.record_restricted_execution(p.project_id, current_fail)
        delayed_old = old_pass.model_copy(update={"execution_id": "exec-delayed-old-pass"})
        sm.record_restricted_execution(p.project_id, delayed_old)

        reloaded_sm = ProjectStateManager(storage_dir=tmpdir)
        reloaded = reloaded_sm.get_project(p.project_id)
        assert reloaded is not None
        assert reloaded.stage is TaskmasterStage.STRATIFIED
        with pytest.raises(ValueError, match="completion gate"):
            reloaded_sm.complete_project(p.project_id, {"workflow_status": "COMPLETED"})


def test_attempt_generation_rejects_bool_and_string_type_confusion():
    from pydantic import ValidationError
    import pytest
    base = dict(action_type="RESTRICTED_CODE_RUN", passed=True, output_log="x", duration_ms=1)
    for bad in (True, False, "1", 1.0, -1):
        with pytest.raises(ValidationError):
            RestrictedExecutionResult(attempt_generation=bad, **base)



def _project_with_authoritative_attempt(tmpdir: str):
    sm = ProjectStateManager(storage_dir=tmpdir)
    p = sm.create_project(objective="single result per attempt")
    cand = StrategyCandidate(
        pathway_name="Path",
        paradigm_type="ORTHOGONAL",
        hypothesis="Current candidate hypothesis",
        action_plan=["step"],
        divergence_score=0.5,
        feasibility_score=0.5,
    )
    sm.add_candidates(p.project_id, [cand])
    sm.record_verification(
        p.project_id,
        VerificationReport(candidate_id=cand.candidate_id, verdict="PASS"),
    )
    attempt_id, generation = sm.issue_restricted_execution_attempt(p.project_id)
    identity = candidate_execution_identity(cand)
    base = dict(
        attempt_id=attempt_id,
        attempt_generation=generation,
        candidate_id=identity["candidate_id"],
        mechanism_version=identity["mechanism_version"],
        claim_id=identity["claim_id"],
        protocol_version="sha256:" + "0" * 64,
        execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION,
        action_type="RESTRICTED_CODE_RUN",
        output_log="result",
        duration_ms=1,
    )
    return sm, p, base


def test_authoritative_attempt_rejects_second_distinct_result():
    with tempfile.TemporaryDirectory() as tmpdir:
        sm, p, base = _project_with_authoritative_attempt(tmpdir)
        first = RestrictedExecutionResult(execution_id="exec-first", passed=False, **base)
        sm.record_restricted_execution(p.project_id, first)

        conflicting = RestrictedExecutionResult(execution_id="exec-second", passed=True, **base)
        with pytest.raises(ValueError, match="attempt result conflict"):
            sm.record_restricted_execution(p.project_id, conflicting)

        posture = sm.get_project(p.project_id)
        assert posture is not None
        assert len(posture.restricted_execution_results) == 1
        assert posture.stage is TaskmasterStage.STRATIFIED
        with pytest.raises(ValueError, match="completion gate"):
            sm.complete_project(p.project_id, {"workflow_status": "COMPLETED"})


def test_restart_fails_closed_on_duplicate_current_attempt_results():
    with tempfile.TemporaryDirectory() as tmpdir:
        sm, p, base = _project_with_authoritative_attempt(tmpdir)
        passed = RestrictedExecutionResult(execution_id="exec-pass", passed=True, **base)
        sm.record_restricted_execution(p.project_id, passed)
        sm.complete_project(p.project_id, {"workflow_status": "COMPLETED"})

        state_path = Path(tmpdir) / f"{p.project_id}.json"
        data = json.loads(state_path.read_text(encoding="utf-8"))
        duplicate = dict(data["restricted_execution_results"][0])
        duplicate["execution_id"] = "exec-conflicting-replay"
        duplicate["passed"] = False
        duplicate["output_log"] = "conflicting persisted replay"
        data["restricted_execution_results"].append(duplicate)
        state_path.write_text(json.dumps(data), encoding="utf-8")

        reloaded = ProjectStateManager(storage_dir=tmpdir).get_project(p.project_id)
        assert reloaded is not None
        assert reloaded.stage is TaskmasterStage.STRATIFIED
        current = [
            result
            for result in reloaded.restricted_execution_results
            if result.attempt_id == reloaded.restricted_execution_attempt_id
            and result.attempt_generation == reloaded.restricted_execution_generation
        ]
        assert len(current) == 2
        assert not any(result.identity_bound for result in current)
        assert reloaded.final_output is not None
        assert reloaded.final_output["workflow_status"] == "EVIDENCE_INVALIDATED"
        with pytest.raises(ValueError, match="completion gate"):
            ProjectStateManager(storage_dir=tmpdir).complete_project(
                p.project_id, {"workflow_status": "COMPLETED"}
            )

@pytest.mark.parametrize("malformed_attempt_id", [" ", "attempt-", "not-server-issued", "attempt-" + "g" * 32])
def test_restart_rejects_malformed_persisted_attempt_authority(malformed_attempt_id):
    with tempfile.TemporaryDirectory() as tmpdir:
        sm, p, base = _project_with_authoritative_attempt(tmpdir)
        passed = RestrictedExecutionResult(execution_id="exec-pass", passed=True, **base)
        sm.record_restricted_execution(p.project_id, passed)
        sm.complete_project(p.project_id, {"workflow_status": "COMPLETED"})

        state_path = Path(tmpdir) / f"{p.project_id}.json"
        data = json.loads(state_path.read_text(encoding="utf-8"))
        data["restricted_execution_attempt_id"] = malformed_attempt_id
        data["restricted_execution_results"][0]["attempt_id"] = malformed_attempt_id
        state_path.write_text(json.dumps(data), encoding="utf-8")

        reloaded = ProjectStateManager(storage_dir=tmpdir).get_project(p.project_id)
        assert reloaded is not None
        assert reloaded.stage is TaskmasterStage.STRATIFIED
        assert not reloaded.restricted_execution_results[0].identity_bound
        assert reloaded.final_output is not None
        assert reloaded.final_output["workflow_status"] == "EVIDENCE_INVALIDATED"

def test_restart_rejects_selected_candidate_not_present_in_candidate_set():
    with tempfile.TemporaryDirectory() as tmpdir:
        sm, p, base = _project_with_authoritative_attempt(tmpdir)
        passed = RestrictedExecutionResult(execution_id="exec-pass", passed=True, **base)
        sm.record_restricted_execution(p.project_id, passed)
        sm.complete_project(p.project_id, {"workflow_status": "COMPLETED"})

        state_path = Path(tmpdir) / f"{p.project_id}.json"
        data = json.loads(state_path.read_text(encoding="utf-8"))
        data["candidates"] = []
        state_path.write_text(json.dumps(data), encoding="utf-8")

        reloaded = ProjectStateManager(storage_dir=tmpdir).get_project(p.project_id)
        assert reloaded is not None
        assert reloaded.stage is not TaskmasterStage.COMPLETED
        assert not reloaded.restricted_execution_results[0].identity_bound
        assert reloaded.final_output is not None
        assert reloaded.final_output["workflow_status"] == "EVIDENCE_INVALIDATED"

@pytest.mark.parametrize("bad_protocol", ["sha256:", "sha256:x", "sha256:" + "g" * 64, "SHA256:" + "0" * 64])
def test_malformed_protocol_hash_never_binds_execution_authority(bad_protocol):
    with tempfile.TemporaryDirectory() as tmpdir:
        sm, p, base = _project_with_authoritative_attempt(tmpdir)
        base["protocol_version"] = bad_protocol
        result = RestrictedExecutionResult(execution_id="exec-bad-protocol", passed=True, **base)
        posture = sm.record_restricted_execution(p.project_id, result)
        assert posture.stage is TaskmasterStage.STRATIFIED
        assert not posture.restricted_execution_results[-1].identity_bound
        with pytest.raises(ValueError, match="completion gate"):
            sm.complete_project(p.project_id, {"workflow_status": "COMPLETED"})

@pytest.mark.parametrize("mutation", ["duplicate", "same_id_different_semantics"])
def test_restart_rejects_ambiguous_selected_candidate_membership(mutation):
    with tempfile.TemporaryDirectory() as tmpdir:
        sm, p, base = _project_with_authoritative_attempt(tmpdir)
        sm.record_restricted_execution(
            p.project_id,
            RestrictedExecutionResult(execution_id="exec-pass", passed=True, **base),
        )
        sm.complete_project(p.project_id, {"workflow_status": "COMPLETED"})

        state_path = Path(tmpdir) / f"{p.project_id}.json"
        data = json.loads(state_path.read_text(encoding="utf-8"))
        if mutation == "duplicate":
            data["candidates"].append(dict(data["selected_candidate"]))
        else:
            for candidate in data["candidates"]:
                if candidate["candidate_id"] == data["selected_candidate"]["candidate_id"]:
                    candidate["hypothesis"] = "semantically different candidate"
        state_path.write_text(json.dumps(data), encoding="utf-8")

        reloaded = ProjectStateManager(storage_dir=tmpdir).get_project(p.project_id)
        assert reloaded is not None
        assert reloaded.stage is not TaskmasterStage.COMPLETED
        assert not any(r.identity_bound for r in reloaded.restricted_execution_results)
        assert reloaded.final_output is not None
        assert reloaded.final_output["workflow_status"] == "EVIDENCE_INVALIDATED"


def test_restart_rejects_same_execution_id_with_conflicting_semantic_payload():
    with tempfile.TemporaryDirectory() as tmpdir:
        sm, p, base = _project_with_authoritative_attempt(tmpdir)
        failed = RestrictedExecutionResult(execution_id="exec-same", passed=False, **base)
        sm.record_restricted_execution(p.project_id, failed)

        state_path = Path(tmpdir) / f"{p.project_id}.json"
        data = json.loads(state_path.read_text(encoding="utf-8"))
        conflicting = dict(data["restricted_execution_results"][0])
        conflicting["passed"] = True
        conflicting["output_log"] = "conflicting persisted PASS with same execution id"
        data["restricted_execution_results"].append(conflicting)
        data["stage"] = "COMPLETED"
        data["final_output"] = {"workflow_status": "COMPLETED"}
        state_path.write_text(json.dumps(data), encoding="utf-8")

        reloaded = ProjectStateManager(storage_dir=tmpdir).get_project(p.project_id)
        assert reloaded is not None
        assert reloaded.stage is TaskmasterStage.STRATIFIED
        current = [
            result
            for result in reloaded.restricted_execution_results
            if result.attempt_id == reloaded.restricted_execution_attempt_id
            and result.attempt_generation == reloaded.restricted_execution_generation
        ]
        assert len(current) == 2
        assert not any(result.identity_bound for result in current)
        with pytest.raises(ValueError, match="completion gate"):
            ProjectStateManager(storage_dir=tmpdir).complete_project(
                p.project_id, {"workflow_status": "COMPLETED"}
            )
