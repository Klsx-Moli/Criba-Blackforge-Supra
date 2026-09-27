"""Tests for SUPRA Project State Manager and Models."""

import tempfile

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
            protocol_version="sha256:test-protocol",
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
            protocol_version="sha256:test-protocol",
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
            protocol_version="sha256:test-protocol",
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
                protocol_version="sha256:test-protocol",
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
        old_pass = RestrictedExecutionResult(attempt_id=a1, attempt_generation=g1, candidate_id=identity["candidate_id"], mechanism_version=identity["mechanism_version"], claim_id=identity["claim_id"], protocol_version="sha256:p", execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION, action_type="RESTRICTED_CODE_RUN", passed=True, output_log="old pass", duration_ms=1)
        assert sm.record_restricted_execution(p.project_id, old_pass).stage is TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED

        a2, g2 = sm.issue_restricted_execution_attempt(p.project_id)
        new_fail = RestrictedExecutionResult(attempt_id=a2, attempt_generation=g2, candidate_id=identity["candidate_id"], mechanism_version=identity["mechanism_version"], claim_id=identity["claim_id"], protocol_version="sha256:p", execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION, action_type="RESTRICTED_CODE_RUN", passed=False, output_log="new fail", duration_ms=1)
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
        stale_fail = RestrictedExecutionResult(attempt_id=a1, attempt_generation=g1, candidate_id=identity["candidate_id"], mechanism_version=identity["mechanism_version"], claim_id=identity["claim_id"], protocol_version="sha256:p", execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION, action_type="RESTRICTED_CODE_RUN", passed=False, output_log="old fail", duration_ms=1)
        a2, g2 = sm.issue_restricted_execution_attempt(p.project_id)
        current_pass = RestrictedExecutionResult(attempt_id=a2, attempt_generation=g2, candidate_id=identity["candidate_id"], mechanism_version=identity["mechanism_version"], claim_id=identity["claim_id"], protocol_version="sha256:p", execution_semantics_version=RESTRICTED_EXECUTION_SEMANTICS_VERSION, action_type="RESTRICTED_CODE_RUN", passed=True, output_log="new pass", duration_ms=1)
        assert sm.record_restricted_execution(p.project_id, current_pass).stage is TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED
        assert sm.record_restricted_execution(p.project_id, stale_fail).stage is TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED
        reloaded = ProjectStateManager(storage_dir=tmpdir).get_project(p.project_id)
        assert reloaded.stage is TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED
