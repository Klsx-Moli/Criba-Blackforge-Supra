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
                     "stage": _field(lookup, "stage")}}


def reconciliar_lote_por_get(
    batch_id: str, client: Any, directory: Path | None = None,
    *, registrar: bool = True,
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
        endpoint = batch.get("endpoint")
        dossiers = batch["intent"]["dossiers"]
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
            return {"batch_id": batch_id, "status": "UNKNOWN",
                    "reason": "GET_FAILED", "checked": len(verified),
                    "expected": len(dossiers)}
        read = _readback(dossier, lookup)
        if read is None:
            return {"batch_id": batch_id, "status": "UNKNOWN",
                    "reason": "READBACK_NOT_DURABLY_BOUND", "checked": len(verified),
                    "expected": len(dossiers)}
        verified.append(read)
    if registrar and batch["remote"] == "UNKNOWN":
        try:
            journal.marcar_readback_observado(batch_id, verified, directory,
                                               endpoint=endpoint)
        except (OSError, ValueError):
            return {"batch_id": batch_id, "status": "UNKNOWN",
                    "reason": "JOURNAL_COMMIT_UNCONFIRMED", "checked": len(verified),
                    "expected": len(dossiers)}
    return {"batch_id": batch_id, "status": "READBACK_OBSERVED",
            "reason": "PERSISTED_PLANNING_RECEIPTS_ONLY", "checked": len(verified),
            "expected": len(dossiers), "scientific_status": "NOT_VALIDATED",
            "mechanism_execution": "NOT_EXECUTED",
            "journal_recorded": registrar or batch["remote"] == "READBACK_OBSERVED"}


def main(argv: list[str] | None = None) -> int:
    """Explicit, read-only reconciliation CLI; it never submits a project."""
    import argparse
    import json
    from .integrations.supra_client import SupraClient

    parser = argparse.ArgumentParser(description="Reconcilia un lote SUPRA sin POST")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    with SupraClient() as client:
        result = reconciliar_lote_por_get(
            args.batch_id, client, registrar=not args.dry_run
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "READBACK_OBSERVED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
