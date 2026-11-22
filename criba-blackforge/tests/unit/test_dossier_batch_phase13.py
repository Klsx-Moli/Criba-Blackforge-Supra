"""Phase 13: no remote calls; journal tests use real file operations and locks.

In a full checkout, imports the real criba.supra_dossier and criba.dossier_batch.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from criba import dossier_batch as b, supra_dossier as sd


def dossiers(run="run-13", mechanism="M", attempt=1):
    return [
        {"dossier_id": f"d{attempt}-{i}", "candidate_id": f"cand-{i}",
         "run_id": run, "problema": "Synthetic water", "estado": "SUPRA_EJECUCION_PENDIENTE",
         "mecanismo": mechanism + str(i), "claim_id": f"claim-{i}",
         "mechanism_version": f"sha256:mech{i}", "protocol_version": f"sha256:prot{i}", "creado_at": "2026-11-22T15:00:00+00:00"}
        for i in (1, 2)
    ]


def lines(directory, name="dossiers.jsonl"):
    path = directory / name
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def test_first_batch_commits_intent_and_dossiers(tmp_path):
    result = b.guardar_lote_dossiers(dossiers(), tmp_path)
    assert result["replayed"] is False
    assert result["remote_state"] == "NOT_ATTEMPTED"
    assert len(lines(tmp_path)) == 2
    assert [e["event"] for e in lines(tmp_path, b.JOURNAL)] == ["PREPARED", "LOCAL_COMMITTED"]


def test_reprepared_same_run_reuses_original_ids_without_duplicate_rows(tmp_path):
    first = b.guardar_lote_dossiers(dossiers(attempt=1), tmp_path)
    second = b.guardar_lote_dossiers(dossiers(attempt=2), tmp_path)
    assert second["replayed"] and second["dossiers"] == first["dossiers"]
    assert len(lines(tmp_path)) == 2
    assert len(lines(tmp_path, b.JOURNAL)) == 2


def test_second_append_failure_recovers_without_duplicating_first(tmp_path, monkeypatch):
    actual = sd._append_historial
    n = {"dossiers": 0}
    def fail_second(path, record):
        if path.name == "dossiers.jsonl":
            n["dossiers"] += 1
            if n["dossiers"] == 2:
                raise OSError("synthetic disk failure")
        return actual(path, record)
    monkeypatch.setattr(sd, "_append_historial", fail_second)
    with pytest.raises(OSError, match="disk failure"):
        b.guardar_lote_dossiers(dossiers(attempt=1), tmp_path)
    assert len(lines(tmp_path)) == 1
    assert [x["event"] for x in lines(tmp_path, b.JOURNAL)] == ["PREPARED"]
    monkeypatch.setattr(sd, "_append_historial", actual)
    result = b.guardar_lote_dossiers(dossiers(attempt=2), tmp_path)
    assert result["replayed"]
    assert len(lines(tmp_path)) == 2
    assert [x["dossier_id"] for x in lines(tmp_path)] == ["d1-1", "d1-2"]
    assert [x["event"] for x in lines(tmp_path, b.JOURNAL)] == ["PREPARED", "LOCAL_COMMITTED"]


def test_independent_restart_recovery_only_local(tmp_path, monkeypatch):
    actual = sd._append_historial
    def fail_save(path, record):
        if path.name == "dossiers.jsonl":
            raise OSError("interrupted before first dossier")
        return actual(path, record)
    monkeypatch.setattr(sd, "_append_historial", fail_save)
    with pytest.raises(OSError): b.guardar_lote_dossiers(dossiers(), tmp_path)
    monkeypatch.setattr(sd, "_append_historial", actual)
    keys = b.recuperar_lotes_pendientes(tmp_path)
    assert len(keys) == 1 and len(lines(tmp_path)) == 2
    assert b.recuperar_lotes_pendientes(tmp_path) == []


def test_conflicting_content_same_run_fails_without_writes(tmp_path):
    b.guardar_lote_dossiers(dossiers(), tmp_path)
    before = (tmp_path / "dossiers.jsonl").read_bytes()
    with pytest.raises(ValueError, match="conflicting"):
        b.guardar_lote_dossiers(dossiers(mechanism="changed", attempt=2), tmp_path)
    assert (tmp_path / "dossiers.jsonl").read_bytes() == before


def test_same_run_different_problem_cannot_be_reused(tmp_path):
    b.guardar_lote_dossiers(dossiers(), tmp_path)
    altered = dossiers(attempt=2)
    for record in altered: record["problema"] = "Other problem"
    with pytest.raises(ValueError, match="same run_id"):
        b.guardar_lote_dossiers(altered, tmp_path)


@pytest.mark.parametrize("mutate", [
    lambda rec: rec.update(fingerprint="0" * 64),
    lambda rec: rec.update(run_id="fabricated"),
    lambda rec: rec.update(problema="other"),
    lambda rec: rec.update(event="LOCAL_COMMITTED"),
    lambda rec: rec.update(schema="unknown"),
])
def test_parseable_journal_corruption_blocks_replay(tmp_path, mutate):
    b.guardar_lote_dossiers(dossiers(), tmp_path)
    path = tmp_path / b.JOURNAL
    records = lines(tmp_path, b.JOURNAL)
    mutate(records[0])
    path.write_text("\n".join(json.dumps(x) for x in records) + "\n", encoding="utf-8")
    with pytest.raises(ValueError): b.guardar_lote_dossiers(dossiers(attempt=2), tmp_path)


def test_duplicate_json_keys_in_journal_fail_closed(tmp_path):
    path = tmp_path / b.JOURNAL
    path.write_bytes(b'{"schema":"criba-dossier-batch/1","schema":"forged"}\n')
    with pytest.raises(ValueError, match="corrupt"):
        b.guardar_lote_dossiers(dossiers(), tmp_path)


def test_torn_commit_tail_fails_closed_and_preserves_bytes(tmp_path):
    b.guardar_lote_dossiers(dossiers(), tmp_path)
    path = tmp_path / b.JOURNAL
    with path.open("ab") as f:
        f.write(b'{"schema":"crippled"')
    before = path.read_bytes()
    with pytest.raises(ValueError, match="journal corrupt"):
        b.guardar_lote_dossiers(dossiers(attempt=2), tmp_path)
    assert path.read_bytes() == before and len(lines(tmp_path)) == 2


def test_remote_unknown_is_write_ahead_and_never_auto_retried(tmp_path):
    result = b.guardar_lote_dossiers(dossiers(), tmp_path)
    key = result["batch_id"]
    assert b.marcar_envio_incierto(key, tmp_path, endpoint="https://supra.test") is True
    assert b.marcar_envio_incierto(key, tmp_path, endpoint="https://supra.test") is False
    replay = b.guardar_lote_dossiers(dossiers(attempt=2), tmp_path)
    assert replay["remote_state"] == "UNKNOWN"
    assert len(lines(tmp_path, b.JOURNAL)) == 3


def readback(dossier):
    import hashlib
    from criba.integrations.supra_client import _dossier_payload_fingerprint
    return {"dossier_id": dossier["dossier_id"],
            "project_id": "astram2-" + hashlib.sha256(dossier["dossier_id"].encode()).hexdigest()[:32],
            "read": {"receipt": {"criba_dossier_id": dossier["dossier_id"],
                "criba_candidate_id": dossier["candidate_id"],
                "claim_id": dossier["claim_id"],
                "mechanism_version": dossier["mechanism_version"],
                "protocol_version": dossier["protocol_version"],
                "receipt_scope": "PLANNED_DISCRIMINANT_PROTOCOL_ONLY",
                "execution_status": "NOT_EXECUTED", "scientific_status": "NOT_VALIDATED",
                "integration_version": "criba-supra/1",
                "payload_fingerprint": _dossier_payload_fingerprint(dossier)},
                "status_source": "PERSISTED_STATE",
                "persisted_artifact_status": "VERIFIED_FROM_ARTIFACT",
                "scientific_status": "NOT_VALIDATED",
                "criba_mechanism_execution_status": "NOT_EXECUTED",
                "criba_planning_receipt_status": "PRESERVED_NOT_EXECUTED"}}


def test_readback_requires_all_dossiers_and_remains_unknown_on_bad_report(tmp_path):
    key = b.guardar_lote_dossiers(dossiers(), tmp_path)["batch_id"]
    b.marcar_envio_incierto(key, tmp_path, endpoint="https://supra.test")
    with pytest.raises(ValueError, match="entire batch"):
        b.marcar_readback_observado(
        key, [{"dossier_id": "d1-1", "project_id": "p1", "read": {}}],
        tmp_path, endpoint="https://supra.test"
    )
    assert b.guardar_lote_dossiers(dossiers(attempt=2), tmp_path)["remote_state"] == "UNKNOWN"
    b.marcar_readback_observado(
        key, [readback(d) for d in dossiers()], tmp_path, endpoint="https://supra.test"
    )
    assert b.guardar_lote_dossiers(dossiers(attempt=2), tmp_path)["remote_state"] == "READBACK_OBSERVED"
    assert b.marcar_envio_incierto(key, tmp_path) is False


def test_remote_mark_never_allowed_for_incomplete_local_batch(tmp_path, monkeypatch):
    actual = sd._append_historial
    def fail_save(path, record):
        if path.name == "dossiers.jsonl": raise OSError("fail")
        return actual(path, record)
    monkeypatch.setattr(sd, "_append_historial", fail_save)
    with pytest.raises(OSError): b.guardar_lote_dossiers(dossiers(), tmp_path)
    key = b._batch_id("run-13", "Synthetic water")
    with pytest.raises(ValueError, match="durable"):
        b.marcar_envio_incierto(key, tmp_path)


def test_concurrent_replays_one_intent_no_duplicate_dossiers(tmp_path):
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda i: b.guardar_lote_dossiers(dossiers(attempt=i), tmp_path), range(1, 9)))
    assert len({tuple(d["dossier_id"] for d in x["dossiers"]) for x in results}) == 1
    assert len(lines(tmp_path)) == 2 and len(lines(tmp_path, b.JOURNAL)) == 2


def test_legacy_local_preservation_without_replay_claim(tmp_path):
    records = dossiers(run="")
    first = b.guardar_lote_dossiers(records, tmp_path)
    assert first["batch_id"].startswith("legacy-batch-")
    with pytest.raises(ValueError, match="run_id"):
        b.marcar_envio_incierto(first["batch_id"], tmp_path)


def test_readback_other_dossier_or_project_rejected(tmp_path):
    key = b.guardar_lote_dossiers(dossiers(), tmp_path)["batch_id"]
    b.marcar_envio_incierto(key, tmp_path, endpoint="https://supra.test")
    for mutation in ("project", "receipt"):
        wrong = [readback(d) for d in dossiers()]
        if mutation == "project":
            wrong[0]["project_id"] = "other"
        else:
            wrong[0]["read"]["receipt"]["criba_candidate_id"] = "another"
        with pytest.raises(ValueError, match="bind"):
            b.marcar_readback_observado(key, wrong, tmp_path, endpoint="https://supra.test")
    assert b.guardar_lote_dossiers(dossiers(attempt=2), tmp_path)["remote_state"] == "UNKNOWN"


def test_readback_same_ids_but_wrong_content_fingerprint_rejected(tmp_path):
    key = b.guardar_lote_dossiers(dossiers(), tmp_path)["batch_id"]
    b.marcar_envio_incierto(key, tmp_path, endpoint="https://supra.test")
    forged = [readback(d) for d in dossiers()]
    forged[0]["read"]["receipt"]["payload_fingerprint"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="bind"):
        b.marcar_readback_observado(key, forged, tmp_path, endpoint="https://supra.test")
    assert b.guardar_lote_dossiers(dossiers(attempt=2), tmp_path)["remote_state"] == "UNKNOWN"
