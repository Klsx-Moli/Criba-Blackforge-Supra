"""ASTRA B01/B03: persisted corruption must never masquerade as absence."""

from __future__ import annotations

import json

import pytest
from supra_agentic.state import ProjectStateLoadError, ProjectStateManager


def test_malformed_json_is_explicit_load_error_not_missing(tmp_path) -> None:
    (tmp_path / "broken.json").write_text("{not-json", encoding="utf-8")
    manager = ProjectStateManager(tmp_path)

    with pytest.raises(ProjectStateLoadError) as captured:
        manager.get_project("broken")

    assert captured.value.project_id == "broken"
    assert captured.value.error_type == "JSONDecodeError"


def test_parseable_but_incompatible_state_is_explicit_load_error(tmp_path) -> None:
    (tmp_path / "incompatible.json").write_text(
        json.dumps({"project_id": "incompatible"}), encoding="utf-8"
    )
    manager = ProjectStateManager(tmp_path)

    with pytest.raises(ProjectStateLoadError) as captured:
        manager.get_project("incompatible")

    assert captured.value.project_id == "incompatible"
    assert captured.value.error_type == "ValidationError"


def test_list_projects_keeps_healthy_entries_and_surfaces_bad_files(tmp_path) -> None:
    writer = ProjectStateManager(tmp_path)
    healthy = writer.create_project("healthy persisted project", project_id="healthy")
    (tmp_path / "broken.json").write_text("{bad", encoding="utf-8")
    (tmp_path / "bad name.json").write_text("{}", encoding="utf-8")

    reader = ProjectStateManager(tmp_path)
    projects, load_errors = reader.list_projects_with_errors()

    assert [project.project_id for project in projects] == [healthy.project_id]
    errors = {item["project_id"]: item["error"] for item in load_errors}
    assert errors == {
        "broken": "PERSISTED_STATE_CORRUPT_OR_INCOMPATIBLE",
        "bad name": "INVALID_PROJECT_FILENAME",
    }


def test_list_snapshot_errors_cannot_be_overwritten_by_later_listing(tmp_path) -> None:
    writer = ProjectStateManager(tmp_path)
    writer.create_project("healthy persisted project", project_id="healthy")
    broken = tmp_path / "broken.json"
    broken.write_text("{bad", encoding="utf-8")

    reader = ProjectStateManager(tmp_path)
    projects, errors = reader.list_projects_with_errors()
    broken.unlink()
    reader.list_projects_with_errors()
    reader.fail_project("healthy", "later concurrent mutation")

    assert [project.project_id for project in projects] == ["healthy"]
    assert projects[0].error_message is None
    assert errors == [
        {
            "project_id": "broken",
            "error": "PERSISTED_STATE_CORRUPT_OR_INCOMPATIBLE",
            "kind": "CORRUPT_JSON",
        }
    ]

