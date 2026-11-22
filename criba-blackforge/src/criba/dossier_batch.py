"""Crash-recoverable local dossier batches; never auto-retry an uncertain POST.

The journal is a durable *local intention*, not proof of remote execution or
scientific evidence. All transitions share the dossier JSONL advisory lock.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from . import supra_dossier as sd

SCHEMA = "criba-dossier-batch/1"
JOURNAL = "dossier_batches.jsonl"


def _exact(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def _fingerprint(dossiers: list[dict[str, Any]]) -> str:
    return hashlib.sha256(_canonical([sd._contexto(p) for p in dossiers])).hexdigest()


def _validate(dossiers: list[dict[str, Any]]) -> tuple[str | None, str]:
    if not isinstance(dossiers, list) or not dossiers:
        raise ValueError("batch requires at least one dossier")
    if any(not isinstance(p, dict) for p in dossiers):
        raise ValueError("batch dossier must be object")
    ids = [p.get("dossier_id") for p in dossiers]
    candidates = [p.get("candidate_id") for p in dossiers]
    if any(not _exact(i) for i in ids + candidates):
        raise ValueError("batch identities must be exact text")
    if len(set(ids)) != len(ids) or len(set(candidates)) != len(candidates):
        raise ValueError("batch identities must be unique")
    problems = {p.get("problema") for p in dossiers}
    if len(problems) != 1 or not all(_exact(x) for x in problems):
        raise ValueError("batch problem must be exact and identical")
    runs = [p.get("run_id") for p in dossiers]
    if any(r not in (None, "") and not _exact(r) for r in runs):
        raise ValueError("batch run_id malformed")
    if any(r != runs[0] for r in runs):
        raise ValueError("batch run_id mismatch")
    if any(p.get("estado") != "SUPRA_EJECUCION_PENDIENTE" for p in dossiers):
        raise ValueError("batch contains non-pending dossier")
    _canonical(dossiers)
    return runs[0] or None, next(iter(problems))


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("batch journal duplicate JSON key")
        result[key] = value
    return result


def _bad_constant(value: str) -> None:
    raise ValueError(f"nonfinite batch journal value: {value}")


def _events(path: Path) -> list[dict[str, Any]]:
    """Ignore only an unterminated, invalid tail; reject completed corruption."""
    if not path.exists():
        return []
    lines = path.read_bytes().splitlines(keepends=True)
    result: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        try:
            rec = json.loads(line, object_pairs_hook=_unique_pairs,
                             parse_constant=_bad_constant)
        except (UnicodeDecodeError, ValueError) as exc:
            if index == len(lines) - 1 and not line.endswith(b"\n"):
                break
            raise ValueError("batch journal has corrupt committed row") from exc
        if not isinstance(rec, dict) or rec.get("schema") != SCHEMA:
            raise ValueError("batch journal schema mismatch")
        result.append(rec)
    return result


def _state(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    batches: dict[str, dict[str, Any]] = {}
    runs: dict[str, str] = {}
    for event in events:
        key, kind = event.get("batch_id"), event.get("event")
        if not _exact(key):
            raise ValueError("invalid batch journal identity")
        if kind == "PREPARED":
            if key in batches:
                raise ValueError("duplicate batch preparation")
            dossiers = event.get("dossiers")
            run, problem = _validate(dossiers)
            if event.get("run_id") != run or event.get("problema") != problem:
                raise ValueError("batch intent lineage mismatch")
            if event.get("fingerprint") != _fingerprint(dossiers):
                raise ValueError("batch intent payload mismatch")
            if run:
                if run in runs and runs[run] != key:
                    raise ValueError("same run_id spans conflicting batch intents")
                runs[run] = key
                if key != _batch_id(run, problem):
                    raise ValueError("batch id does not match run")
            batches[key] = {"intent": event, "committed": False, "remote": "NOT_ATTEMPTED"}
        elif key not in batches:
            raise ValueError("orphan batch event")
        else:
            batch = batches[key]
            if kind == "LOCAL_COMMITTED" and not batch["committed"]:
                batch["committed"] = True
            elif kind == "REMOTE_UNKNOWN" and batch["committed"] and batch["remote"] == "NOT_ATTEMPTED":
                batch["remote"] = "UNKNOWN"
            elif kind == "REMOTE_READBACK_OBSERVED" and batch["remote"] == "UNKNOWN":
                batch["remote"] = "READBACK_OBSERVED"
            else:
                raise ValueError("out-of-order or repeated batch event")
    return batches


def _batch_id(run: str, problem: str) -> str:
    return "batch-" + hashlib.sha256(_canonical([run, problem])).hexdigest()


def _event(kind: str, key: str, **extra: Any) -> dict[str, Any]:
    return {"schema": SCHEMA, "event": kind, "batch_id": key, **extra}


def _save_under_lock(directory: Path, key: str,
                     batches: dict[str, dict[str, Any]]) -> dict[str, Any]:
    batch = batches[key]
    dossiers = batch["intent"]["dossiers"]
    history_path = directory / "dossiers.jsonl"
    existing, ambiguous, _ = sd._leer_historial(history_path)
    # Preflight all identities before any append, avoiding avoidable partial commits.
    for dossier in dossiers:
        identity = dossier["dossier_id"]
        if identity in ambiguous or (identity in existing and
                                     sd._contexto(existing[identity]) != sd._contexto(dossier)):
            raise ValueError("batch dossier_id collides with historical content")
    for dossier in dossiers:
        identity = dossier["dossier_id"]
        if identity not in existing:
            sd._append_historial(history_path, dossier)
            existing[identity] = dossier
    if not batch["committed"]:
        sd._append_historial(directory / JOURNAL, _event("LOCAL_COMMITTED", key))
        batch["committed"] = True
    return {"batch_id": key, "dossiers": json.loads(_canonical(dossiers)),
            "remote_state": batch["remote"]}


def guardar_lote_dossiers(dossiers: list[dict[str, Any]],
                          directory: Path | None = None) -> dict[str, Any]:
    """Fsync intent, replay missing dossiers, fsync commit. No remote calls.

    Repreparing an existing run with new random dossier IDs reuses the original
    durable IDs. Conflicting contents for that run are rejected, not overwritten.
    """
    run, problem = _validate(dossiers)
    fingerprint = _fingerprint(dossiers)
    key = _batch_id(run, problem) if run else "legacy-batch-" + uuid4().hex
    directory = sd._dossiers_dir(directory)
    with sd._historial_exclusive(directory):
        batches = _state(_events(directory / JOURNAL))
        previous = batches.get(key)
        if previous is not None:
            if previous["intent"]["fingerprint"] != fingerprint:
                raise ValueError("run_id reused with conflicting batch content")
        else:
            if run and any(b["intent"]["run_id"] == run for b in batches.values()):
                raise ValueError("same run_id cannot span distinct problems/batches")
            intent = _event("PREPARED", key, run_id=run, problema=problem,
                            fingerprint=fingerprint,
                            dossiers=json.loads(_canonical(dossiers)))
            sd._append_historial(directory / JOURNAL, intent)
            batches[key] = {"intent": intent, "committed": False,
                            "remote": "NOT_ATTEMPTED"}
        result = _save_under_lock(directory, key, batches)
        result["replayed"] = previous is not None
        result["path"] = str(directory / "dossiers.jsonl")
        return result


def recuperar_lotes_pendientes(directory: Path | None = None) -> list[str]:
    """Resume local-only pending intents across restarts. Never issue POST."""
    directory = sd._dossiers_dir(directory)
    with sd._historial_exclusive(directory):
        batches = _state(_events(directory / JOURNAL))
        restored: list[str] = []
        for key, batch in batches.items():
            if not batch["committed"]:
                _save_under_lock(directory, key, batches)
                restored.append(key)
        return restored


def marcar_envio_incierto(batch_id: str, directory: Path | None = None) -> bool:
    """Write-ahead remote UNKNOWN. False means NEVER automatically re-POST."""
    if not _exact(batch_id):
        raise ValueError("batch_id invalid")
    directory = sd._dossiers_dir(directory)
    with sd._historial_exclusive(directory):
        batches = _state(_events(directory / JOURNAL))
        batch = batches.get(batch_id)
        if batch is None or not batch["committed"]:
            raise ValueError("batch has no durable local commit")
        if batch["intent"]["run_id"] is None:
            raise ValueError("remote batch requires original run_id")
        if batch["remote"] != "NOT_ATTEMPTED":
            return False
        sd._append_historial(directory / JOURNAL, _event("REMOTE_UNKNOWN", batch_id))
        return True


def marcar_readback_observado(batch_id: str, runs: list[dict[str, Any]],
                              directory: Path | None = None) -> None:
    """Record observed GETs; never assert scientific validity or execution."""
    if not _exact(batch_id) or not isinstance(runs, list):
        raise ValueError("invalid remote report")
    directory = sd._dossiers_dir(directory)
    with sd._historial_exclusive(directory):
        batches = _state(_events(directory / JOURNAL))
        batch = batches.get(batch_id)
        if batch is None or batch["remote"] != "UNKNOWN":
            raise ValueError("remote attempt not pending UNKNOWN")
        expected = {d["dossier_id"] for d in batch["intent"]["dossiers"]}
        actual = [r.get("dossier_id") for r in runs if isinstance(r, dict)]
        expected_by_id = {d["dossier_id"]: d for d in batch["intent"]["dossiers"]}
        if len(runs) != len(expected) or set(actual) != expected or len(set(actual)) != len(actual):
            raise ValueError("readback report does not cover exact batch")
        for run in runs:
            dossier = expected_by_id[run["dossier_id"]]
            project = "astram2-" + hashlib.sha256(run["dossier_id"].encode()).hexdigest()[:32]
            receipt = run.get("read", {}).get("receipt") if isinstance(run.get("read"), dict) else None
            if (run.get("project_id") != project or not isinstance(receipt, dict) or
                    any(receipt.get(remote) != dossier.get(local) for local, remote in (
                        ("dossier_id", "criba_dossier_id"),
                        ("candidate_id", "criba_candidate_id"),
                        ("claim_id", "claim_id"),
                        ("mechanism_version", "mechanism_version"),
                        ("protocol_version", "protocol_version"),
                    )) or receipt.get("receipt_scope") != "PLANNED_DISCRIMINANT_PROTOCOL_ONLY" or
                    receipt.get("execution_status") != "NOT_EXECUTED" or
                    receipt.get("scientific_status") != "NOT_VALIDATED"):
                raise ValueError("readback report does not bind the local dossier")
        sd._append_historial(directory / JOURNAL,
                            _event("REMOTE_READBACK_OBSERVED", batch_id))
