"""Read-only GET reconciliation for phase-13 uncertain SUPRA dossier batches.

A readback establishes only a bound persisted planning receipt, not mechanism
execution, scientific verification, or absence of requests not found by GET.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import dossier_batch as journal
from .integrations.supra_client import _dossier_payload_fingerprint

MAX_PARTIAL_GETS = 64  # bounded recovery effort; never auto-sweep arbitrary batches


def _field(value: Any, name: str) -> Any:
    return value.get(name) if isinstance(value, Mapping) else getattr(value, name, None)


def _object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        try:
            result = dump(mode="json")
        except TypeError:
            result = dump()
        return result if isinstance(result, dict) else None
    return None


def _expected_project(dossier_id: str) -> str:
    return "astram2-" + hashlib.sha256(dossier_id.encode("utf-8")).hexdigest()[:32]


def _readback(dossier: dict[str, Any], lookup: Any) -> dict[str, Any] | None:
    """Validate an independently fetched project with durable provenance."""
    target = _expected_project(dossier["dossier_id"])
    posture = _field(lookup, "posture")
    if (not isinstance(_field(lookup, "stage"), str)
            or not _field(lookup, "stage")
            or _field(lookup, "project_id") != target
            or _field(posture, "project_id") != target
            or _field(lookup, "stage") != _field(posture, "stage")
            or _field(lookup, "status_source") != "PERSISTED_STATE"
            or _field(lookup, "persisted_artifact_status") != "VERIFIED_FROM_ARTIFACT"
            or _field(lookup, "scientific_status") != "NOT_VALIDATED"
            or _field(lookup, "criba_mechanism_execution_status") != "NOT_EXECUTED"
            or _field(lookup, "criba_planning_receipt_status") != "PRESERVED_NOT_EXECUTED"):
        return None
    receipt = _object(_field(posture, "criba_dossier_receipt"))
    if receipt is None:
        return None
    try:
        fingerprint = _dossier_payload_fingerprint(dossier)
    except (TypeError, ValueError, KeyError):
        return None
    expected = {
        "criba_dossier_id": dossier["dossier_id"],
        "criba_candidate_id": dossier["candidate_id"],
        "claim_id": dossier["claim_id"],
        "mechanism_version": dossier["mechanism_version"],
        "protocol_version": dossier["protocol_version"],
        "payload_fingerprint": fingerprint,
        "integration_version": "criba-supra/1",
        "receipt_scope": "PLANNED_DISCRIMINANT_PROTOCOL_ONLY",
        "execution_status": "NOT_EXECUTED",
        "scientific_status": "NOT_VALIDATED",
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        return None
    return {"dossier_id": dossier["dossier_id"], "project_id": target,
            "read": {"receipt": {key: receipt[key] for key in expected},
                     "status_source": "PERSISTED_STATE",
                     "persisted_artifact_status": "VERIFIED_FROM_ARTIFACT",
                     "scientific_status": "NOT_VALIDATED",
                     "criba_mechanism_execution_status": "NOT_EXECUTED",
                     "criba_planning_receipt_status": "PRESERVED_NOT_EXECUTED",
                     "stage": _field(lookup, "stage")}}


def _local_batch_still_intact(
    batch_id: str, directory: Path, endpoint: str, fingerprint: str,
    *, allow_unknown: bool = False,
) -> bool:
    """Re-read exact journal intent and dossier history under a shared lock.

    A valid UNKNOWN intent is sufficient only to guard a *dry-run fresh GET*.
    It must never establish a historically recorded v2 confirmation.
    """
    with journal.sd._historial_exclusive(directory):
        state = journal._state(journal._events(directory / journal.JOURNAL))
        batch = state.get(batch_id)
        expected_states = (
            ("UNKNOWN", "READBACK_OBSERVED") if allow_unknown
            else ("READBACK_OBSERVED",)
        )
        if (batch is None or not batch["committed"]
                or batch["remote"] not in expected_states
                or batch["endpoint"] != endpoint
                or batch["intent"].get("fingerprint") != fingerprint):
            return False
        history, ambiguous, _ = journal.sd._leer_historial(directory / "dossiers.jsonl")
        return all(
            d["dossier_id"] not in ambiguous
            and d["dossier_id"] in history
            and journal.sd._contexto(d) == journal.sd._contexto(history[d["dossier_id"]])
            for d in batch["intent"]["dossiers"]
        )


def _confirmed_v2_still_local(
    batch_id: str, directory: Path, endpoint: str, fingerprint: str,
) -> bool:
    """Verify a prior durable v2 receipt, not current scientific success."""
    return _local_batch_still_intact(
        batch_id, directory, endpoint, fingerprint,
    )


def _fresh_get_unconfirmed(
    batch_id: str, directory: Path, endpoint: str, fingerprint: str,
    reason: str, checked: int, expected: int,
) -> dict[str, Any]:
    """Separate prior local verification from fresh GET failure, never promote."""
    if _confirmed_v2_still_local(batch_id, directory, endpoint, fingerprint):
        return {
            "batch_id": batch_id, "status": "READBACK_OBSERVED",
            "reason": "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED",
            "fresh_get_status": reason, "checked": checked, "expected": expected,
            "journal_recorded": True, "scientific_status": "NOT_VALIDATED",
            "mechanism_execution": "NOT_EXECUTED",
        }
    return {"batch_id": batch_id, "status": "UNKNOWN", "reason": reason,
            "checked": checked, "expected": expected}


def reconciliar_lote_por_get(
    batch_id: str, client: Any, directory: Path | None = None,
    *, registrar: bool = True,
    expected_run_id: str | None = None,
    expected_problem: str | None = None,
) -> dict[str, Any]:
    """Read only remote via GET; optionally journal the fully verified readback.

    Never call run_project/POST or retry missing projects. Existing legacy
    UNKNOWN journals without a known endpoint remain unknown without GET.
    """
    directory = journal.sd._dossiers_dir(directory)
    with journal.sd._historial_exclusive(directory):
        states = journal._state(journal._events(directory / journal.JOURNAL))
        batch = states.get(batch_id)
        if batch is None:
            raise ValueError("batch_id not in journal")
        if not batch["committed"] or batch["remote"] not in ("UNKNOWN", "READBACK_OBSERVED"):
            raise ValueError("batch is not an uncertain remote attempt")
        dossiers = batch["intent"]["dossiers"]
        # Bind the active Shadow sheet to the original fsynced PREPARED intent.
        # Caller-supplied batch_id alone is insufficient lineage authority.
        if ((expected_run_id is not None
             and batch["intent"]["run_id"] != expected_run_id)
                or (expected_problem is not None
                    and batch["intent"]["problema"] != expected_problem)):
            return {"batch_id": batch_id, "status": "UNKNOWN",
                    "reason": "INTENT_LINEAGE_MISMATCH", "checked": 0,
                    "expected": len(dossiers)}
        endpoint = batch.get("endpoint")
        fingerprint = batch["intent"]["fingerprint"]
        history, ambiguous, _ = journal.sd._leer_historial(directory / "dossiers.jsonl")
        if any(d["dossier_id"] in ambiguous or
               d["dossier_id"] not in history or
               journal.sd._contexto(d) != journal.sd._contexto(history[d["dossier_id"]])
               for d in dossiers):
            return {"batch_id": batch_id, "status": "UNKNOWN",
                    "reason": "LOCAL_HISTORY_MISMATCH", "checked": 0,
                    "expected": len(dossiers)}
    current_endpoint = _field(_field(client, "config"), "endpoint")
    if not endpoint:
        return {"batch_id": batch_id, "status": "UNKNOWN",
                "reason": "ENDPOINT_NOT_BOUND", "checked": 0,
                "expected": len(dossiers)}
    if not isinstance(current_endpoint, str) or endpoint != current_endpoint.rstrip("/"):
        return {"batch_id": batch_id, "status": "UNKNOWN",
                "reason": "ENDPOINT_MISMATCH", "checked": 0,
                "expected": len(dossiers)}
    verified: list[dict[str, Any]] = []
    for dossier in dossiers:
        try:
            lookup = client.get_project(_expected_project(dossier["dossier_id"]))
        except Exception:
            return _fresh_get_unconfirmed(
                batch_id, directory, endpoint, fingerprint,
                "GET_FAILED", len(verified), len(dossiers),
            )
        read = _readback(dossier, lookup)
        if read is None:
            return _fresh_get_unconfirmed(
                batch_id, directory, endpoint, fingerprint,
                "READBACK_NOT_DURABLY_BOUND", len(verified), len(dossiers),
            )
        verified.append(read)
    if registrar and batch["remote"] == "UNKNOWN":
        try:
            journal.marcar_readback_observado(batch_id, verified, directory,
                                               endpoint=endpoint)
        except (OSError, ValueError):
            # Another GET worker may have committed the SAME audited receipt.
            # A stale pre-GET batch snapshot is never sufficient evidence.
            if _confirmed_v2_still_local(batch_id, directory, endpoint, fingerprint):
                return {
                    "batch_id": batch_id, "status": "READBACK_OBSERVED",
                    "reason": "JOURNAL_CONFIRMED_CONCURRENTLY",
                    "fresh_get_status": "VERIFIED_FROM_ARTIFACT",
                    "checked": len(verified), "expected": len(dossiers),
                    "scientific_status": "NOT_VALIDATED",
                    "mechanism_execution": "NOT_EXECUTED",
                    "journal_recorded": True,
                }
            return {"batch_id": batch_id, "status": "UNKNOWN",
                    "reason": "JOURNAL_COMMIT_UNCONFIRMED", "checked": len(verified),
                    "expected": len(dossiers)}
    # An UNKNOWN dry-run never enters marcar_readback_observado. Without
    # this recheck, a concurrent journal/dossier mutation can be promoted
    # as a valid GET result even when local evidence is now lost.
    if (not registrar or batch["remote"] == "READBACK_OBSERVED") and not (
        _local_batch_still_intact(
            batch_id, directory, endpoint, fingerprint,
            allow_unknown=(batch["remote"] == "UNKNOWN"),
        )
    ):
        return {"batch_id": batch_id, "status": "UNKNOWN",
                "reason": "LOCAL_OR_JOURNAL_CHANGED_DURING_GET",
                "checked": len(verified), "expected": len(dossiers)}
    return {"batch_id": batch_id, "status": "READBACK_OBSERVED",
            "reason": "PERSISTED_PLANNING_RECEIPTS_ONLY", "checked": len(verified),
            "expected": len(dossiers), "scientific_status": "NOT_VALIDATED",
            "mechanism_execution": "NOT_EXECUTED",
            "fresh_get_status": "VERIFIED_FROM_ARTIFACT",
            "journal_recorded": registrar or batch["remote"] == "READBACK_OBSERVED"}



def inspeccionar_lote_parcial_por_get(
    batch_id: str, client: Any, directory: Path | None = None,
    *, registrar: bool = False, expected_run_id: str | None = None,
    expected_problem: str | None = None,
) -> dict[str, Any]:
    """Sweep exact projects by GET; never infer missing POSTs or batch success.

    Each row describes THIS inspection only; historical partial receipts are
    not fresh GET. registrar=True fsyncs individual positive planning receipts,
    not the complete-batch v2 marker. A crash may interrupt the sweep while
    preserving earlier positive rows. No POST or automatic remote retries.
    """
    directory = journal.sd._dossiers_dir(directory)

    def refusal(reason: str, expected: int = 0) -> dict[str, Any]:
        return {
            "batch_id": batch_id, "status": "UNKNOWN", "reason": reason,
            "expected": expected, "fresh_verified": 0, "journal_partials": 0,
            "rows": [], "full_batch_recorded": False,
            "scientific_status": "NOT_VALIDATED",
            "mechanism_execution": "NOT_EXECUTED",
        }

    with journal.sd._historial_exclusive(directory):
        states = journal._state(journal._events(directory / journal.JOURNAL))
        batch = states.get(batch_id)
        if batch is None:
            raise ValueError("partial batch_id not in journal")
        if not batch["committed"] or batch["remote"] not in (
            "UNKNOWN", "READBACK_OBSERVED",
        ):
            return refusal("BATCH_NOT_REMOTELY_RESERVED")
        original = batch["intent"]["dossiers"]
        if len(original) > MAX_PARTIAL_GETS:
            return refusal("PARTIAL_SWEEP_LIMIT_EXCEEDED", len(original))
        if ((expected_run_id is not None
             and batch["intent"]["run_id"] != expected_run_id)
                or (expected_problem is not None
                    and batch["intent"]["problema"] != expected_problem)):
            return refusal("INTENT_LINEAGE_MISMATCH", len(original))
        endpoint = batch["endpoint"]
        fingerprint = batch["intent"]["fingerprint"]
        history, ambiguous, _ = journal.sd._leer_historial(directory / "dossiers.jsonl")
        if any(
            d["dossier_id"] in ambiguous
            or d["dossier_id"] not in history
            or journal.sd._contexto(d) != journal.sd._contexto(history[d["dossier_id"]])
            for d in original
        ):
            return refusal("LOCAL_HISTORY_MISMATCH", len(original))
    current_endpoint = _field(_field(client, "config"), "endpoint")
    if not endpoint:
        return refusal("ENDPOINT_NOT_BOUND", len(original))
    if (not isinstance(current_endpoint, str)
            or endpoint != current_endpoint.rstrip("/")):
        return refusal("ENDPOINT_MISMATCH", len(original))
    rows: list[dict[str, Any]] = []
    for dossier in original:
        identity = dossier["dossier_id"]
        try:
            lookup = client.get_project(_expected_project(identity))
        except Exception:
            # Includes HTTP 404: a failed GET is not proof that no POST ran.
            rows.append({
                "dossier_id": identity, "get_status": "GET_UNAVAILABLE_UNKNOWN",
            })
            continue
        verified = _readback(dossier, lookup)
        if verified is None:
            rows.append({
                "dossier_id": identity, "get_status": "UNBOUND_READBACK_UNKNOWN",
            })
            continue
        recorded = False
        if registrar:
            try:
                recorded = journal.registrar_readback_parcial(
                    batch_id, verified, directory, endpoint=endpoint,
                )
            except (OSError, ValueError):
                # Fresh response was verified, but persistence is not confirmed.
                rows.append({
                    "dossier_id": identity,
                    "get_status": "JOURNAL_WRITE_UNCONFIRMED",
                })
                continue
        rows.append({
            "dossier_id": identity,
            "get_status": "FRESH_PLANNING_RECEIPT_VERIFIED",
            "partial_written_now": recorded,
        })
    # The journal or local originals can change during network I/O. Always
    # recheck after sweep; no freshness result survives a lineage change.
    with journal.sd._historial_exclusive(directory):
        state = journal._state(journal._events(directory / journal.JOURNAL))
        current = state.get(batch_id)
        if (current is None or not current["committed"]
                or current["remote"] not in ("UNKNOWN", "READBACK_OBSERVED")
                or current["endpoint"] != endpoint
                or current["intent"]["fingerprint"] != fingerprint):
            return refusal("JOURNAL_CHANGED_DURING_GET", len(original))
        history, ambiguous, _ = journal.sd._leer_historial(directory / "dossiers.jsonl")
        if any(
            d["dossier_id"] in ambiguous
            or d["dossier_id"] not in history
            or journal.sd._contexto(d) != journal.sd._contexto(history[d["dossier_id"]])
            for d in current["intent"]["dossiers"]
        ):
            return refusal("LOCAL_HISTORY_CHANGED_DURING_GET", len(original))
        historical_count = len(current["partial_readbacks"])
        for row in rows:
            # This receipt was persisted in an earlier or current inspection.
            # Never mistake it for a fresh GET or evidence about other IDs.
            row["historical_partial_recorded"] = (
                row["dossier_id"] in current["partial_readbacks"]
            )
        complete = current["remote"] == "READBACK_OBSERVED"
    return {
        "batch_id": batch_id, "status": "PARTIAL_DIAGNOSTIC_ONLY",
        "reason": "NO_FULL_BATCH_PROMOTION", "expected": len(original),
        "fresh_verified": sum(
            row["get_status"] == "FRESH_PLANNING_RECEIPT_VERIFIED"
            for row in rows
        ),
        "journal_partials": historical_count, "rows": rows,
        "full_batch_recorded": complete,
        "scientific_status": "NOT_VALIDATED",
        "mechanism_execution": "NOT_EXECUTED",
    }


def main(argv: list[str] | None = None) -> int:
    """Remote GET-only CLI; local receipt writes unless --dry-run."""
    import argparse
    import json
    from .integrations.supra_client import SupraClient

    parser = argparse.ArgumentParser(description="Reconcilia un lote SUPRA sin POST")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--inspect-partial", action="store_true",
        help="GET each dossier; does NOT confirm a complete batch",
    )
    args = parser.parse_args(argv)
    with SupraClient() as client:
        if args.inspect_partial:
            result = inspeccionar_lote_parcial_por_get(
                args.batch_id, client, registrar=not args.dry_run,
            )
        else:
            result = reconciliar_lote_por_get(
                args.batch_id, client, registrar=not args.dry_run,
            )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    # A previously recorded planning receipt is not a *fresh* remote check.
    # Automation must not interpret stale/offline evidence as CLI success.
    if args.inspect_partial:
        # A partial diagnostic is never a successful full-batch confirmation.
        return 2
    return 0 if (result["status"] == "READBACK_OBSERVED"
                 and result.get("fresh_get_status") == "VERIFIED_FROM_ARTIFACT") else 2


if __name__ == "__main__":
    raise SystemExit(main())
