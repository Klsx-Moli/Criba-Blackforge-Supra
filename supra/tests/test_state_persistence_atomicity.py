"""Persistence atomicity of SUPRA project state transitions.

Contract (ASTRA: persisted != executed, generated != validated):

    A persistence failure must not leave any new observable state in memory.
    After a failed transition:

        memory == state_before
        disk   == state_before
        reload == state_before

`create_project` has an additional obligation: a project whose posture could
not be persisted must not survive as a cache ghost, because a later
`create_project` with the same id would then observe a project that never
existed on disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from supra_agentic import state as state_module
from supra_agentic.models import (
    StrategyCandidate,
    StructuredDecomposition,
    Subtask,
    TaskmasterStage,
    VerificationReport,
)
from supra_agentic.state import ProjectStateManager

PROJECT_ID = "atomicity-probe"


def _fail_persistence(_project_id: str) -> None:
    raise OSError("injected persistence failure")


def _decomposition() -> StructuredDecomposition:
    return StructuredDecomposition(
        domain="atomicity",
        core_objective="Verify that a failed persistence leaves no new state",
        invariants=["memory matches disk after failure"],
        mutable_assumptions=["filesystem accepts the write"],
        risk_factors=["partial write"],
        subtasks=[
            Subtask(
                title="inject persistence failure",
                description="replace the writer with a failing stub",
                stage_target=TaskmasterStage.STRATIFIED,
            )
        ],
    )


def _candidates() -> list[StrategyCandidate]:
    return [
        StrategyCandidate(
            candidate_id="cand-atomicity",
            pathway_name="Bounded rollback",
            paradigm_type="CONSERVATIVE",
            hypothesis="A failed write is indistinguishable from a no-op write.",
        )
    ]


def _verification() -> VerificationReport:
    return VerificationReport(
        candidate_id="cand-atomicity",
        verdict="FAIL",
        confidence_score=0.1,
        rationale="coverage incomplete",
    )


def _seed(manager: ProjectStateManager, *, through: str) -> None:
    """Drive a project to a known stage without ever failing persistence."""
    manager.create_project(objective="persistence atomicity sentinel", project_id=PROJECT_ID)
    if through in {"update_decomposition", "add_candidates", "record_verification"}:
        manager.update_decomposition(PROJECT_ID, _decomposition())
    if through in {"add_candidates", "record_verification"}:
        manager.add_candidates(PROJECT_ID, _candidates())
    if through == "record_verification":
        manager.record_verification(PROJECT_ID, _verification())


def _apply(manager: ProjectStateManager, transition: str) -> None:
    if transition == "update_decomposition":
        manager.update_decomposition(PROJECT_ID, _decomposition())
    elif transition == "add_candidates":
        manager.add_candidates(PROJECT_ID, _candidates())
    elif transition == "record_verification":
        manager.record_verification(PROJECT_ID, _verification())
    elif transition == "block_project":
        manager.block_project(PROJECT_ID, "completion gates unmet")
    elif transition == "fail_project":
        manager.fail_project(PROJECT_ID, "injected abort")
    else:  # pragma: no cover - guards the sentinel table itself
        raise AssertionError(f"unknown transition {transition!r}")


TRANSITIONS = (
    "update_decomposition",
    "add_candidates",
    "record_verification",
    "block_project",
    "fail_project",
)


@pytest.mark.parametrize("transition", TRANSITIONS)
def test_failed_persistence_leaves_memory_disk_and_reload_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, transition: str
) -> None:
    manager = ProjectStateManager(storage_dir=tmp_path)
    _seed(manager, through=transition)
    state_file = tmp_path / f"{PROJECT_ID}.json"

    before_memory = manager.get_project(PROJECT_ID)
    assert before_memory is not None
    before_model = before_memory.model_dump_json()
    before_disk = state_file.read_text(encoding="utf-8")

    monkeypatch.setattr(manager, "_persist_project", _fail_persistence)
    with pytest.raises(OSError, match="injected persistence failure"):
        _apply(manager, transition)

    monkeypatch.undo()

    same_process = manager.get_project(PROJECT_ID)
    assert same_process is not None
    assert same_process.model_dump_json() == before_model

    assert state_file.read_text(encoding="utf-8") == before_disk

    restarted = ProjectStateManager(storage_dir=tmp_path).get_project(PROJECT_ID)
    assert restarted is not None
    assert restarted.model_dump_json() == before_model


@pytest.mark.parametrize("transition", TRANSITIONS)
def test_failed_persistence_keeps_transition_effector_derived_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, transition: str
) -> None:
    """A rolled-back transition must not leave a stage or ledger entry behind.

    `planned != executed` also covers bookkeeping: a checkpoint that records a
    transition that was never persisted would let a consumer read history that
    did not survive restart.
    """
    manager = ProjectStateManager(storage_dir=tmp_path)
    _seed(manager, through=transition)
    before = manager.get_project(PROJECT_ID)
    assert before is not None
    before_checkpoints = len(before.checkpoints)
    before_stage = before.stage

    monkeypatch.setattr(manager, "_persist_project", _fail_persistence)
    with pytest.raises(OSError, match="injected persistence failure"):
        _apply(manager, transition)
    monkeypatch.undo()

    after = manager.get_project(PROJECT_ID)
    assert after is not None
    assert len(after.checkpoints) == before_checkpoints
    assert after.stage is before_stage

    restarted = ProjectStateManager(storage_dir=tmp_path).get_project(PROJECT_ID)
    assert restarted is not None
    assert len(restarted.checkpoints) == before_checkpoints
    assert restarted.stage is before_stage


def test_failed_create_project_leaves_no_ghost_in_cache_or_on_disk(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manager = ProjectStateManager(storage_dir=tmp_path)

    monkeypatch.setattr(manager, "_persist_project", _fail_persistence)
    with pytest.raises(OSError, match="injected persistence failure"):
        manager.create_project("ghost project sentinel", project_id="ghost")
    monkeypatch.undo()

    assert "ghost" not in manager._projects
    assert not (tmp_path / "ghost.json").exists()
    assert manager.get_project("ghost") is None

    # A second, healthy create must succeed: nothing survived to claim the id.
    posture = manager.create_project("ghost project sentinel", project_id="ghost")
    assert posture.project_id == "ghost"
    assert posture.stage is TaskmasterStage.RECEIVED
    assert json.loads((tmp_path / "ghost.json").read_text(encoding="utf-8"))[
        "project_id"
    ] == "ghost"


@pytest.mark.parametrize("transition", TRANSITIONS)
def test_failed_persistence_restores_previously_handed_out_reference(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, transition: str
) -> None:
    """A reference obtained BEFORE the failure must not keep the phantom state.

    `get_project` returns the cached instance, not a copy. Rolling back by
    swapping a new object into the cache would leave an earlier reader looking
    at a stage and checkpoint ledger that never reached disk.
    """
    manager = ProjectStateManager(storage_dir=tmp_path)
    _seed(manager, through=transition)
    alias = manager.get_project(PROJECT_ID)
    assert alias is not None
    alias_snapshot = alias.model_dump_json()

    monkeypatch.setattr(manager, "_persist_project", _fail_persistence)
    with pytest.raises(OSError, match="injected persistence failure"):
        _apply(manager, transition)
    monkeypatch.undo()

    assert alias.model_dump_json() == alias_snapshot
    fresh = manager.get_project(PROJECT_ID)
    assert fresh is not None
    assert fresh.model_dump_json() == alias_snapshot


def test_failed_persistence_preserves_exception_provenance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The original failure must stay reachable from the raised error.

    A persistence failure that loses its cause becomes unattributable, which
    is how a data-loss event turns into an unexplained incident.
    """
    manager = ProjectStateManager(storage_dir=tmp_path)
    _seed(manager, through="block_project")
    before = manager.get_project(PROJECT_ID)
    assert before is not None
    before_stage = before.stage
    before_checkpoints = len(before.checkpoints)

    def _refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise PermissionError("injected unwritable storage")

    monkeypatch.setattr(state_module.tempfile, "NamedTemporaryFile", _refuse)
    with pytest.raises(RuntimeError) as excinfo:
        manager.block_project(PROJECT_ID, "gates unmet")

    cause = excinfo.value.__cause__
    assert isinstance(cause, PermissionError)
    assert "injected unwritable storage" in str(cause)
    assert PROJECT_ID in str(excinfo.value)

    # The rollback must still have happened even on the real writer's path.
    after = manager.get_project(PROJECT_ID)
    assert after is not None
    assert after.stage is before_stage
    assert len(after.checkpoints) == before_checkpoints
    assert not any(item.title == "Completion Gate Blocked" for item in after.checkpoints)


def test_real_writer_failure_leaves_previous_artifact_byte_identical(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The atomic tmp+replace writer must not damage the previous artifact."""
    manager = ProjectStateManager(storage_dir=tmp_path)
    _seed(manager, through="block_project")
    before = manager.get_project(PROJECT_ID)
    assert before is not None
    state_file = tmp_path / f"{PROJECT_ID}.json"
    previous = state_file.read_bytes()

    def _refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise OSError("injected unwritable storage")

    monkeypatch.setattr(state_module.tempfile, "NamedTemporaryFile", _refuse)
    with pytest.raises(RuntimeError):
        manager.block_project(PROJECT_ID, "gates unmet")
    monkeypatch.undo()

    assert state_file.read_bytes() == previous
    assert not list(tmp_path.glob("*.tmp"))
    restarted = ProjectStateManager(storage_dir=tmp_path).get_project(PROJECT_ID)
    assert restarted is not None
    assert restarted.stage is before.stage
    assert restarted.model_dump_json() == before.model_dump_json()

