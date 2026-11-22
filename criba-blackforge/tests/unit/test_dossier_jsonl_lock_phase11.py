"""F11: real JSONL dossier IO under thread/process concurrency and torn tails.

All fixtures are synthetic. The dossier functions are imported from the
actual production module in a complete checkout; no SUPRA provider is called.
"""
from __future__ import annotations

import json
import multiprocessing
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from criba import supra_dossier as sd


def _dossier(identity: str, mechanism: str = "synthetic A") -> dict:
    return {
        "dossier_id": identity,
        "candidate_id": "synthetic-candidate",
        "mecanismo": mechanism,
        "creado_at": "2026-11-22T00:00:00+00:00",
    }


def _writer(directory: str, index: int, gate, results) -> None:
    # Module-level target so Windows multiprocessing.spawn can import it.
    gate.wait()
    try:
        sd.guardar_dossier(_dossier("same", str(index)), Path(directory))
    except ValueError:
        results.put("rejected")
    else:
        results.put("saved")


def test_same_identity_different_payload_one_thread_wins(tmp_path):
    gate = threading.Barrier(12)

    def save(index):
        gate.wait()
        try:
            sd.guardar_dossier(_dossier("same", str(index)), tmp_path)
        except ValueError:
            return "rejected"
        return "saved"

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(save, range(12)))
    assert results.count("saved") == 1
    assert results.count("rejected") == 11
    dossiers, ambiguous, _ = sd._leer_historial(tmp_path / "dossiers.jsonl")
    assert len(dossiers) == 1 and set(dossiers) == {"same"}
    assert ambiguous == set()


def test_cross_process_identity_lock_with_spawn(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    gate = ctx.Barrier(5)
    queue = ctx.Queue()
    processes = [
        ctx.Process(target=_writer, args=(str(tmp_path), i, gate, queue))
        for i in range(5)
    ]
    try:
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=20)
        assert all(process.exitcode == 0 for process in processes)
        results = [queue.get(timeout=2) for _ in processes]
        assert results.count("saved") == 1
        assert results.count("rejected") == 4
        records = (tmp_path / "dossiers.jsonl").read_bytes().splitlines()
        assert len(records) == 1
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=3)
        queue.close()


def test_duplicate_same_payload_idempotent_across_threads(tmp_path):
    with ThreadPoolExecutor(max_workers=12) as executor:
        paths = list(
            executor.map(
                lambda _: sd.guardar_dossier(_dossier("same"), tmp_path),
                range(30),
            )
        )
    assert len(paths) == 30
    assert len((tmp_path / "dossiers.jsonl").read_bytes().splitlines()) == 1


@pytest.mark.parametrize("identity", ["", " same ", None, True, 42, []])
def test_invalid_id_does_not_write_history(tmp_path, identity):
    with pytest.raises(ValueError):
        sd.guardar_dossier(_dossier(identity), tmp_path)
    assert not (tmp_path / "dossiers.jsonl").exists()


def test_preexisting_ambiguous_history_is_never_silently_repaired(tmp_path):
    path = tmp_path / "dossiers.jsonl"
    path.write_text(
        json.dumps(_dossier("x", "A")) + "\n"
        + json.dumps(_dossier("x", "B")) + "\n",
        encoding="utf-8",
    )
    before = path.read_bytes()
    with pytest.raises(ValueError, match="ambiguo"):
        sd.guardar_dossier(_dossier("x", "A"), tmp_path)
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "tail",
    [b'{"dossier_id":"torn","mecanismo":"unfinished"',
     b'{"dossier_id":"bad","text":"\xf0\x9f'],
)
def test_torn_tail_keeps_original_bytes_and_new_entry_is_recoverable(tmp_path, tail):
    path = tmp_path / "dossiers.jsonl"
    path.write_bytes(tail)
    sd.guardar_dossier(_dossier("new", "synthetic recovered"), tmp_path)
    after = path.read_bytes()
    assert after.startswith(tail + b"\n")
    dossiers, ambiguous, _ = sd._leer_historial(path)
    assert dossiers["new"]["mecanismo"] == "synthetic recovered"
    assert not ambiguous
    assert "torn" not in dossiers and "bad" not in dossiers


def test_existing_valid_record_survives_subsequent_torn_tail(tmp_path):
    path = sd.guardar_dossier(_dossier("before"), tmp_path)
    with path.open("ab") as handle:
        handle.write(b'{"dossier_id":"half"')
    sd.guardar_dossier(_dossier("after"), tmp_path)
    dossiers, ambiguous, _ = sd._leer_historial(path)
    assert set(dossiers) == {"before", "after"} and not ambiguous


def test_duplicate_json_keys_nonfinite_not_interpreted_as_history(tmp_path):
    path = tmp_path / "dossiers.jsonl"
    path.write_bytes(
        b'{"dossier_id":"corrupt","dossier_id":"other","mecanismo":"X"}\n'
        b'{"dossier_id":"nan","mecanismo":NaN}\n'
    )
    original = path.read_bytes()
    sd.guardar_dossier(_dossier("valid"), tmp_path)
    assert path.read_bytes().startswith(original)
    dossiers, ambiguous, _ = sd._leer_historial(path)
    assert set(dossiers) == {"valid"} and not ambiguous


def test_fsync_is_requested_before_save_success(tmp_path, monkeypatch):
    actual = sd.os.fsync
    calls = []

    def traced(fd):
        calls.append(fd)
        actual(fd)

    monkeypatch.setattr(sd.os, "fsync", traced)
    sd.guardar_dossier(_dossier("durable"), tmp_path)
    assert len(calls) == 1


def test_fsync_error_is_not_misreported_as_unsaved(tmp_path, monkeypatch):
    actual = sd.os.fsync

    def broken(_fd):
        raise OSError("synthetic fsync failure")

    monkeypatch.setattr(sd.os, "fsync", broken)
    with pytest.raises(OSError, match="fsync"):
        sd.guardar_dossier(_dossier("uncertain"), tmp_path)
    # The complete line may already exist even if durability was not confirmed.
    monkeypatch.setattr(sd.os, "fsync", actual)
    sd.guardar_dossier(_dossier("uncertain"), tmp_path)
    assert len((tmp_path / "dossiers.jsonl").read_bytes().splitlines()) == 1
