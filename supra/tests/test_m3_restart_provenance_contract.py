"""M3 contract: a live read may never claim persisted state it did not read.

K1 declared this limitation and M3 inherits the decision:

    "the SUPRA state_manager serves state from its in-memory cache even when
     the on-disk artifact is corrupt; the corruption surfaces on restart."

Reproduced against the REAL server by execution on 2026-10-03
(_probe/k1_cache_vs_disk_probe.py), not read off the implementation:

    POST /api/v1/projects                      -> 201  (artifact on disk, valid)
    corrupt {project}.json on disk             -> file is no longer JSON
    GET  /api/v1/projects/{id}   (live proc)  -> 200  status_source=PERSISTED_STATE
    GET  /api/v1/projects        (live proc)  -> storage_errors == []
    kill + restart the process
    GET  /api/v1/projects/{id}                 -> 500  "corrupt or incompatible"

So the same corrupt artifact answers 200 "PERSISTED_STATE" while the process
lives and 500 once it restarts. The state itself was never wrong, and the
restart path already fails closed. The defect is the LABEL: the read path
asserts a provenance it did not verify, which is the same class of defect K1
fixed for `status` in D2.

DECISION (M3): architecture is acceptable, the label is not. An in-process
cache that survives external artifact corruption is legitimate; publishing
that cached answer as ``PERSISTED_STATE`` is a false provenance claim. The
contract is therefore:

  * ``status_source`` reports WHERE the served posture came from:
    ``PERSISTED_STATE`` (decoded from the artifact) or ``IN_PROCESS_MEMORY_CACHE``.
  * ``IN_PROCESS_MEMORY_CACHE`` is published ONLY together with the
    verification status of that artifact, so a consumer can see that the
    durable copy is unverified without losing the served state.
  * a listing must not hide a corrupt artifact behind the cache either.

This does not change any scientific meaning, threshold, golden or contract.
PLANNED is still PLANNED, a persisted execution result is still not an
executed one, and the restart path still fails closed on the same input.

Mutation sentinels (each one turns this file red on its own):
  * hardcode ``status_source="PERSISTED_STATE"`` again -> every cache test.
  * drop the ``cache_verified`` channel -> the honesty assertions.
  * report ``persisted_artifact_status`` as ``NOT_CHECKED`` unconditionally ->
    ``test_live_read_must_say_whether_the_artifact_was_verified``.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from supra_agentic.service import app
from supra_agentic.state import state_manager

client = TestClient(app, raise_server_exceptions=False)

# Keep the TemporaryDirectory objects alive for the whole module (see
# test_b03_replay_restart_contract.py: a collected directory deletes itself out
# from under the state singleton and every assertion then fails with a
# FileNotFoundError, which is a fixture artifact and not a product defect).
_LIVE_TEMP_DIRS: list[tempfile.TemporaryDirectory] = []


def _isolated_storage() -> Path:
    """Point the singleton at a fresh, empty directory and drop its cache."""
    tmpdir = tempfile.TemporaryDirectory()
    _LIVE_TEMP_DIRS.append(tmpdir)
    state_manager.storage_dir = Path(tmpdir.name)
    state_manager._projects.clear()
    return Path(tmpdir.name)


def _create_live_cached_project(project_id: str) -> dict:
    """Create a real project through the public API so its cache entry is warm."""
    created = client.post(
        "/api/v1/projects",
        json={
            "objective": "Decide whether a cached read may claim persisted state",
            "project_id": project_id,
        },
    )
    assert created.status_code == 201, created.text
    return created.json()


def _corrupt_artifact(storage: Path, project_id: str) -> None:
    artifact = storage / f"{project_id}.json"
    assert artifact.is_file(), "the run never persisted an artifact to corrupt"
    artifact.write_text("{ corrupt by an external actor", encoding="utf-8")
    assert not _parses(artifact.read_text(encoding="utf-8"))


def _parses(raw: str) -> bool:
    try:
        json.loads(raw)
    except Exception:
        return False
    return True


# ---------------------------------------------------------------------------
# D3: the read path may not claim a provenance it did not verify
# ---------------------------------------------------------------------------
def test_live_read_of_a_warm_cache_does_not_claim_persisted_state() -> None:
    """D3: the served state survives, the provenance label must not lie.

    The cache is what makes this a hard case: the artifact is intact and the
    answer is genuinely correct, so nothing but the label can reveal that no
    disk read happened. That is exactly why the label is the contract.
    """
    _isolated_storage()
    project_id = "m3-warm-cache-provenance"
    _create_live_cached_project(project_id)

    warm = client.get(f"/api/v1/projects/{project_id}")
    assert warm.status_code == 200, warm.text
    body = warm.json()

    # The posture is real and served: this defect is not about losing state.
    assert body["posture"]["project_id"] == project_id
    assert body["stage"] == body["posture"]["stage"]
    # The provenance claim is the defect.
    assert body["status_source"] == "IN_PROCESS_MEMORY_CACHE", (
        "a read served from the in-process cache must not be labelled "
        f"PERSISTED_STATE: {body['status_source']!r}"
    )


def test_live_read_declares_the_status_of_the_durable_copy() -> None:
    """A consumer needs to know whether the durable copy was verified.

    Without this channel the only honest option for the server would be to
    refuse the read, which would throw away a correct state because of an
    unverified duplicate of it. Publishing the verdict keeps both facts.
    """
    storage = _isolated_storage()
    project_id = "m3-warm-cache-verdict"
    _create_live_cached_project(project_id)
    _corrupt_artifact(storage, project_id)

    body = client.get(f"/api/v1/projects/{project_id}").json()

    assert "persisted_artifact_status" in body, (
        "the read must publish the verification status of the durable artifact"
    )
    assert body["persisted_artifact_status"] == "UNVERIFIABLE", body
    # The served state is still served, and still honestly labelled.
    assert body["status_source"] == "IN_PROCESS_MEMORY_CACHE"
    assert body["stage"] == body["posture"]["stage"]
    # A corrupt durable copy is never reported as a healthy persisted one.
    assert body["persisted_artifact_status"] not in {"MATCHES_CACHE", "VERIFIED"}


def test_live_cache_reports_version_skew_separately_from_corrupt_json() -> None:
    """A valid JSON artifact with an incompatible schema is not corrupt JSON."""
    storage = _isolated_storage()
    project_id = "m3-version-skew-cache"
    corrupt_id = "m3-corrupt-cache-kind"
    _create_live_cached_project(project_id)
    _create_live_cached_project(corrupt_id)
    artifact = storage / f"{project_id}.json"
    valid = artifact.read_text(encoding="utf-8").rstrip()
    artifact.write_text(valid[:-1] + ',"schema_version":999}', encoding="utf-8")
    _corrupt_artifact(storage, corrupt_id)

    corrupt_response = client.get(f"/api/v1/projects/{corrupt_id}")
    assert corrupt_response.status_code == 200, corrupt_response.text
    assert corrupt_response.json()["persisted_artifact_error_kind"] == "CORRUPT_JSON"

    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status_source"] == "IN_PROCESS_MEMORY_CACHE"
    assert body["persisted_artifact_status"] == "UNVERIFIABLE"
    assert body["persisted_artifact_error_kind"] == "INCOMPATIBLE_SCHEMA", body


def test_a_read_that_really_decoded_the_artifact_still_says_persisted_state() -> None:
    """The fix must not degrade the honest case into a permanent cache label.

    Mutation sentinel: always answer IN_PROCESS_MEMORY_CACHE -> this goes red,
    because a restart read genuinely reconstructs from the artifact.
    """
    _isolated_storage()
    project_id = "m3-cold-read-provenance"
    _create_live_cached_project(project_id)

    state_manager._projects.clear()  # only the durable state remains
    cold = client.get(f"/api/v1/projects/{project_id}")
    assert cold.status_code == 200, cold.text
    body = cold.json()
    assert body["status_source"] == "PERSISTED_STATE"
    assert body["persisted_artifact_status"] == "VERIFIED_FROM_ARTIFACT"


def test_a_corrupt_artifact_still_fails_closed_after_a_restart() -> None:
    """The already-protected restart behaviour must survive the new label.

    This is the regression guard for K1's existing fail-closed guarantee: the
    fix adds provenance, it must not make a corrupt artifact readable.
    """
    storage = _isolated_storage()
    project_id = "m3-restart-still-closed"
    _create_live_cached_project(project_id)
    _corrupt_artifact(storage, project_id)

    state_manager._projects.clear()
    restarted = client.get(f"/api/v1/projects/{project_id}")
    assert restarted.status_code == 500, restarted.text
    assert "corrupt" in restarted.text.lower()


def test_listing_may_not_hide_a_corrupt_artifact_behind_the_cache() -> None:
    """D3 on the list path: a warm cache used to erase the storage error.

    Reproduced by execution: with the artifact corrupt and the project cached,
    ``storage_errors`` came back empty, so the only endpoint that enumerates
    storage health denied that anything was wrong.
    """
    storage = _isolated_storage()
    project_id = "m3-listing-hides-corruption"
    _create_live_cached_project(project_id)
    _corrupt_artifact(storage, project_id)

    listing = client.get("/api/v1/projects")
    assert listing.status_code == 200, listing.text
    errors = listing.json()["storage_errors"]
    reported = {item["project_id"]: item["error"] for item in errors}
    assert reported.get(project_id) == "PERSISTED_STATE_CORRUPT_OR_INCOMPATIBLE", (
        f"a corrupt artifact behind a warm cache was not reported: {errors}"
    )
    assert next(item for item in errors if item["project_id"] == project_id)["kind"] == (
        "CORRUPT_JSON"
    )


def test_listing_still_reports_healthy_projects_without_false_errors() -> None:
    """The honesty channel must not turn every listing into an alarm.

    Mutation sentinel: report every cached project as corrupt -> this goes red.
    """
    _isolated_storage()
    _create_live_cached_project("m3-listing-healthy")

    listing = client.get("/api/v1/projects")
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body["storage_errors"] == [], body["storage_errors"]
    assert [p["project_id"] for p in body["projects"]] == ["m3-listing-healthy"]


def test_a_deleted_artifact_behind_a_warm_cache_is_not_reported_as_healthy() -> None:
    """Disappearance is not absence either: the copy on disk is gone.

    The same class as corruption. A listing that calls this project healthy
    would tell an operator its durable copy exists when it does not.
    """
    storage = _isolated_storage()
    project_id = "m3-listing-deleted-artifact"
    _create_live_cached_project(project_id)
    (storage / f"{project_id}.json").unlink()

    listing = client.get("/api/v1/projects")
    assert listing.status_code == 200, listing.text
    reported = {item["project_id"]: item["error"] for item in listing.json()["storage_errors"]}
    assert reported.get(project_id) == "PERSISTED_ARTIFACT_MISSING", (
        f"a project whose artifact was deleted was reported as healthy: {reported}"
    )
