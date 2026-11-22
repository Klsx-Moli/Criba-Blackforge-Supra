"""Headless, read-only recovery decision for archived Shadow invention sheets.

A sheet may have been saved to SQLite before its SUPRA remote attempt. The
journal is authoritative for run identity, not a stale GUI snapshot. The
resolver never issues POST/GET, mutates a sheet or creates a dossier.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..dossier_batch import buscar_lote_por_sesion


def resolve_archived_batch(
    sheet: Any, directory: Path | None = None,
) -> dict[str, Any] | None:
    """Return the original batch, or None only for a genuinely new session.

    A sheet with a claimed batch that cannot be found must fail closed. A
    matching run_id attached to another problem is also an error, not a new
    submission. Incomplete local PREPARED remains local and cannot be POSTed
    as an apparently new batch.
    """
    if not isinstance(sheet, dict):
        return None
    batch_hint = sheet.get("dossier_batch_id")
    remote_hint = sheet.get("dossier_remote_state")
    if batch_hint is not None and (
        not isinstance(batch_hint, str)
        or not batch_hint
        or batch_hint.strip() != batch_hint
    ):
        raise ValueError("archived batch id is malformed")
    if remote_hint is not None and remote_hint not in (
        "NOT_ATTEMPTED", "UNKNOWN", "READBACK_OBSERVED",
    ):
        raise ValueError("archived batch remote state is unrecognised")
    # Missing batch_id after a partially written/corrupted archive does not
    # authorize a new POST if the sheet still declares dossier provenance.
    has_hint = any(
        field in sheet for field in (
            "dossier_batch_id", "dossier_remote_state",
            "dossiers", "dossiers_path",
        )
    )
    run_id, query = sheet.get("run_id"), sheet.get("query")
    if (not isinstance(run_id, str) or not run_id or run_id.strip() != run_id
            or not isinstance(query, str) or not query or query.strip() != query):
        if has_hint:
            raise ValueError("archived batch lacks exact run_id and problem lineage")
        return None
    original = buscar_lote_por_sesion(run_id, query, directory)
    if original is None:
        if has_hint:
            raise ValueError("archived batch claims missing local journal intent")
        return None
    if batch_hint is not None and batch_hint != original["batch_id"]:
        raise ValueError("archived batch id conflicts with original journal")
    # A stale ARCHIVED remote_hint is never trusted over the fsynced journal.
    return original
