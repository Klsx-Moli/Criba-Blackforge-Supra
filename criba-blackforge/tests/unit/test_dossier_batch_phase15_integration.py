"""Phase15: real JSONL journal + GET-only reconciliation, HTTP simulated.

This suite DOES NOT monkeypatch journal._state/_events, local reader, lock,
append, or reconciliation commit. Only external GET is replaced.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from criba import dossier_batch as journal
from criba import supra_dossier as sd
from criba.dossier_batch_recovery import reconciliar_lote_por_get
from criba.integrations.supra_client import _dossier_payload_fingerprint

ENDPOINT = "http://127.0.0.1:8000"


def dossiers(prefix: str = "first") -> list[dict]:
    return [
        {
            "dossier_id": f"dossier-{prefix}-{n}",
            "candidate_id": f"candidate-{n}",
            "run_id": "phase15-run",
            "claim_id": f"claim-{n}",
            "mechanism_version": "sha256:" + "a" * 64,
            "protocol_version": "sha256:" + "b" * 64,
            "problema": "Synthetic recovery problem",
            "hipotesis": "Synthetic hypothesis",
            "mecanismo": f"mechanism-{n}",
            "estado": "SUPRA_EJECUCION_PENDIENTE",
        }
        for n in (1, 2)
    ]


def project(d: dict) -> str:
    return "astram2-" + hashlib.sha256(d["dossier_id"].encode()).hexdigest()[:32]


def lookup(d: dict) -> dict:
    target = project(d)
    return {
        "project_id": target,
        "stage": "BLOCKED",
        "status_source": "PERSISTED_STATE",
        "persisted_artifact_status": "VERIFIED_FROM_ARTIFACT",
        "scientific_status": "NOT_VALIDATED",
        "criba_mechanism_execution_status": "NOT_EXECUTED",
        "criba_planning_receipt_status": "PRESERVED_NOT_EXECUTED",
        "posture": {
            "project_id": target,
            "stage": "BLOCKED",
            "criba_dossier_receipt": {
                "criba_dossier_id": d["dossier_id"],
                "criba_candidate_id": d["candidate_id"],
                "claim_id": d["claim_id"],
                "mechanism_version": d["mechanism_version"],
                "protocol_version": d["protocol_version"],
                "integration_version": "criba-supra/1",
                "payload_fingerprint": _dossier_payload_fingerprint(d),
                "receipt_scope": "PLANNED_DISCRIMINANT_PROTOCOL_ONLY",
                "execution_status": "NOT_EXECUTED",
                "scientific_status": "NOT_VALIDATED",
            },
        },
    }


class OnlyGet:
    def __init__(self, records: list[dict], endpoint: str = ENDPOINT) -> None:
        self.config = SimpleNamespace(endpoint=endpoint)
        self.responses = {project(d): lookup(d) for d in records}
        self.calls: list[str] = []

    def get_project(self, key: str) -> dict:
        self.calls.append(key)
        result = self.responses[key]
        if isinstance(result, BaseException):
            raise result
        return deepcopy(result)

    def run_project(self, **_kwargs: object) -> None:
        raise AssertionError("No POST in recovery")


def prepared(tmp_path: Path, endpoint: str | None = ENDPOINT) -> tuple[str, list[dict]]:
    originals = dossiers()
    key = journal.guardar_lote_dossiers(originals, tmp_path)["batch_id"]
    if endpoint is None:
        # Construct historical unbound event rather than allowing a *new*
        # unbound reservation.
        sd._append_historial(tmp_path / journal.JOURNAL,
                            journal._event("REMOTE_UNKNOWN", key, endpoint=None))
    else:
        assert journal.marcar_envio_incierto(key, tmp_path, endpoint=endpoint)
    return key, originals


def events(tmp_path: Path) -> list[dict]:
    return journal._events(tmp_path / journal.JOURNAL)


def test_get_commit_and_reparse_preserve_original_ids(tmp_path: Path) -> None:
    key, original = prepared(tmp_path)
    client = OnlyGet(original)
    result = reconciliar_lote_por_get(key, client, tmp_path)
    assert result["status"] == "READBACK_OBSERVED"
    assert result["scientific_status"] == "NOT_VALIDATED"
    assert result["mechanism_execution"] == "NOT_EXECUTED"
    assert client.calls == [project(d) for d in original]
    assert [e["event"] for e in events(tmp_path)] == [
        "PREPARED", "LOCAL_COMMITTED", "REMOTE_UNKNOWN", "REMOTE_READBACK_OBSERVED"
    ]
    assert journal._state(events(tmp_path))[key]["remote"] == "READBACK_OBSERVED"
    restored = journal.guardar_lote_dossiers(dossiers("retry"), tmp_path)
    assert restored["replayed"]
    assert [d["dossier_id"] for d in restored["dossiers"]] == [
        d["dossier_id"] for d in original
    ]
    assert len(events(tmp_path)) == 4


def test_partial_get_failure_never_commits(tmp_path: Path) -> None:
    key, original = prepared(tmp_path)
    client = OnlyGet(original)
    client.responses[project(original[1])] = TimeoutError("lost response")
    before = (tmp_path / journal.JOURNAL).read_bytes()
    result = reconciliar_lote_por_get(key, client, tmp_path)
    assert result["status"] == "UNKNOWN" and result["checked"] == 1
    assert (tmp_path / journal.JOURNAL).read_bytes() == before
    assert journal._state(events(tmp_path))[key]["remote"] == "UNKNOWN"


def test_endpoint_changed_does_not_perform_get(tmp_path: Path) -> None:
    key, original = prepared(tmp_path)
    client = OnlyGet(original, "https://different.example")
    result = reconciliar_lote_por_get(key, client, tmp_path)
    assert result["reason"] == "ENDPOINT_MISMATCH"
    assert client.calls == []
    assert len(events(tmp_path)) == 3


def test_local_dossier_tamper_prevents_remote_verification(tmp_path: Path) -> None:
    key, original = prepared(tmp_path)
    path = tmp_path / "dossiers.jsonl"
    path.write_text(
        path.read_text(encoding="utf-8").replace("mechanism-1", "altered-mechanism"),
        encoding="utf-8",
    )
    client = OnlyGet(original)
    result = reconciliar_lote_por_get(key, client, tmp_path)
    assert result["reason"] == "LOCAL_HISTORY_MISMATCH"
    assert not client.calls
    assert len(events(tmp_path)) == 3


def test_readback_forgery_detected_during_journal_replay(tmp_path: Path) -> None:
    key, original = prepared(tmp_path)
    assert reconciliar_lote_por_get(key, OnlyGet(original), tmp_path)["status"] == "READBACK_OBSERVED"
    entries = events(tmp_path)
    entries[-1]["runs"][0]["read"]["receipt"]["payload_fingerprint"] = "sha256:" + "0" * 64
    path = tmp_path / journal.JOURNAL
    path.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="readback"):
        journal._state(journal._events(path))


def test_failed_write_of_readback_keeps_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    key, original = prepared(tmp_path)
    real_append = sd._append_historial

    def fail(path: Path, record: dict) -> None:
        if path.name == journal.JOURNAL and record.get("event") == "REMOTE_READBACK_OBSERVED":
            raise OSError("synthetic disk failure")
        real_append(path, record)

    monkeypatch.setattr(sd, "_append_historial", fail)
    result = reconciliar_lote_por_get(key, OnlyGet(original), tmp_path)
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "JOURNAL_COMMIT_UNCONFIRMED"
    assert journal._state(events(tmp_path))[key]["remote"] == "UNKNOWN"
    monkeypatch.setattr(sd, "_append_historial", real_append)
    assert reconciliar_lote_por_get(key, OnlyGet(original), tmp_path)["status"] == "READBACK_OBSERVED"


def test_legacy_marker_without_receipt_never_promotes(tmp_path: Path) -> None:
    key, _ = prepared(tmp_path, endpoint=None)
    sd._append_historial(tmp_path / journal.JOURNAL, journal._event(
        "REMOTE_READBACK_OBSERVED", key
    ))
    state = journal._state(events(tmp_path))[key]
    assert state["remote"] == "UNKNOWN" and state["legacy_readback_unverified"]


def test_commit_marker_cannot_replace_missing_local_dossiers(tmp_path: Path) -> None:
    key = journal.guardar_lote_dossiers(dossiers(), tmp_path)["batch_id"]
    (tmp_path / "dossiers.jsonl").unlink()
    with pytest.raises(ValueError, match="local dossier history"):
        journal.marcar_envio_incierto(key, tmp_path, endpoint=ENDPOINT)
    assert not any(x["event"] == "REMOTE_UNKNOWN" for x in events(tmp_path))
