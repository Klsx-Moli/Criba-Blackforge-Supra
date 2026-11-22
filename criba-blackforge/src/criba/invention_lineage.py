"""Offline integrity checks for saved CRIBA inventions and SUPRA export lineage.

These checks verify internal consistency of declared identities, never model,
provider, evidence, causal correctness, or scientific approval.
"""
from __future__ import annotations

import hashlib
from copy import deepcopy
from collections.abc import Mapping
from typing import Any


def _exact(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _candidate_key(entry: Mapping[str, Any], index: int) -> str:
    return str(entry.get("candidate_id") or entry.get("id") or index)


def bind_entry_to_sheet(sheet: Mapping[str, Any], entry: Mapping[str, Any]) -> dict[str, Any]:
    """Bind a SUPRA-bound candidate to its originating sheet, without mutation.

    Legacy sheets without run_id remain representable, but do not acquire a
    fabricated run identity. Modern sheets with one must carry it unchanged.
    """
    if not isinstance(sheet, Mapping) or not isinstance(entry, Mapping):
        raise ValueError("sheet/entry must be objects")
    query = sheet.get("query")
    if not _exact(query):
        raise ValueError("sheet query is missing or inexact")
    records = sheet.get("entries")
    if not isinstance(records, list):
        raise ValueError("sheet entries must be a list")
    candidate = entry.get("candidate_id")
    if not _exact(candidate):
        raise ValueError("candidate_id must be exact")
    matches = [other for other in records
               if isinstance(other, Mapping) and other.get("candidate_id") == candidate]
    if len(matches) != 1 or matches[0] != entry:
        raise ValueError("candidate not uniquely bound to sheet")
    run = sheet.get("run_id")
    if run is not None and not _exact(run):
        raise ValueError("sheet run_id is malformed")
    entry_run = entry.get("run_id")
    if entry_run not in (None, "") and not _exact(entry_run):
        raise ValueError("candidate run_id is malformed")
    if run is not None and entry_run not in (None, "", run):
        raise ValueError("candidate belongs to another run")
    if run is None and entry_run not in (None, ""):
        raise ValueError("candidate run_id cannot be verified against sheet")
    for name in ("query", "problema"):
        declared = entry.get(name)
        if declared not in (None, "") and declared != query:
            raise ValueError(f"candidate {name} contradicts sheet query")
    bound = deepcopy(dict(entry))
    if run is not None:
        bound["run_id"] = run
    return bound


def verify_archived_invention(row: Mapping[str, Any]) -> None:
    """Fail closed on parseable SQLite/JSON contradictions before UI activation.

    The generic Storage.get stays a forensic read; this only protects active
    restoration of a saved invention_sheet, not historical browsing.
    """
    if not isinstance(row, Mapping) or row.get("status") != "PROPUESTA":
        raise ValueError("archived session is not an interpreted proposal")
    packet = row.get("packet")
    if not isinstance(packet, Mapping) or packet.get("kind") != "invention_sheet":
        raise ValueError("not a saved invention sheet")
    sheet = packet.get("sheet")
    if not isinstance(sheet, Mapping):
        raise ValueError("saved invention sheet missing")
    query = sheet.get("query")
    if not _exact(query) or row.get("query") != query:
        raise ValueError("archived query differs from original")
    digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
    if row.get("query_hash") != digest:
        raise ValueError("archived query hash mismatch")
    entries = sheet.get("entries")
    index = packet.get("selected_index")
    if not isinstance(entries, list) or type(index) is not int or not 0 <= index < len(entries):
        raise ValueError("archived selection invalid")
    selected = entries[index]
    if not isinstance(selected, Mapping) or selected.get("estado_interpretacion") != "PROPUESTA":
        raise ValueError("archived interpretation not proposed")
    if any(not _exact(selected.get(k)) for k in ("hipotesis", "mecanismo")):
        raise ValueError("archived interpretation incomplete")
    if selected.get("interpretacion_error", "") != "":
        raise ValueError("archived interpretation has an error")
    inner = selected.get("interprete_result")
    if inner is not None and (not isinstance(inner, Mapping)
                              or inner.get("estado") != "PROPUESTA"
                              or inner.get("error") != ""):
        raise ValueError("archived inner result contradicts proposal")
    if row.get("current_id") != _candidate_key(selected, index):
        raise ValueError("archived selected candidate identity mismatch")
    run = sheet.get("run_id")
    if run is not None:
        if not _exact(run):
            raise ValueError("archived run id malformed")
        if selected.get("run_id") not in (None, "", run):
            raise ValueError("archived candidate belongs to another run")
