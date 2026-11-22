"""F11: real revision counters and evidence semantics across writers/restarts.

Uses the production dossier JSONL module; receipts below are synthetic and
never imply a real experiment. No remote SUPRA, model, or external service.
"""
from __future__ import annotations

import multiprocessing
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from criba import supra_dossier as sd


PROTOCOL = {
    name: "synthetic declared field" for name in (
        "afirmacion_decisiva", "alternativa_explicativa",
        "intervencion_prueba", "observable",
        "resultado_favorable_mecanismo", "resultado_favorable_alternativa",
        "regla_decision", "condicion_fracaso",
    )
}


def _dossier():
    return {
        "dossier_id": "synthetic-d1",
        "candidate_id": "synthetic-c1",
        "claim_id": "synthetic-claim",
        "mechanism_version": "sha256:synthetic-mechanism",
        "protocol_version": "sha256:synthetic-protocol",
        "mecanismo": "A proposed, unvalidated mechanism.",
        "problema": "Synthetic test case",
        "prueba_discriminante": dict(PROTOCOL),
    }


def _receipt():
    return {
        "candidate_id": "synthetic-c1",
        "claim_id": "synthetic-claim",
        "mechanism_version": "sha256:synthetic-mechanism",
        "protocol_version": "sha256:synthetic-protocol",
        "execution_id": "synthetic-exec",
        "observed_result": "positivo",
        "result_scope": "EXPERIMENTAL_OBSERVATION",
    }


def _append(directory):
    return sd.registrar_resultado(
        "synthetic-d1", "positivo",
        execution_id="synthetic-exec",
        protocol_version="sha256:synthetic-protocol",
        execution_resolver=lambda _: _receipt(),
        directory=directory,
    )


def _spawn_revision(directory, barrier, queue):
    barrier.wait()
    try:
        record = _append(Path(directory))
    except Exception as exc:
        queue.put(("ERROR", str(exc)))
    else:
        queue.put(("OK", record["revision_index"]))


def test_concurrent_revision_indices_and_first_timestamp_stable(tmp_path):
    sd.guardar_dossier(_dossier(), tmp_path)
    gate = threading.Barrier(12)

    def submit(_):
        gate.wait()
        return _append(tmp_path)

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(submit, range(12)))
    assert sorted(r["revision_index"] for r in results) == list(range(12))
    assert len({r["observation_id"] for r in results}) == 1
    assert len({r["first_registered_at"] for r in results}) == 1
    assert all(r["learning_eligible"] is True for r in results)
    _, ambiguous, records = sd._leer_historial(tmp_path / "dossiers.jsonl")
    assert not ambiguous and len(records) == 12
    assert sorted(r["revision_index"] for r in records) == list(range(12))


def test_concurrent_revisions_between_processes_with_spawn(tmp_path):
    sd.guardar_dossier(_dossier(), tmp_path)
    ctx = multiprocessing.get_context("spawn")
    gate = ctx.Barrier(6)
    queue = ctx.Queue()
    children = [
        ctx.Process(target=_spawn_revision, args=(str(tmp_path), gate, queue))
        for _ in range(6)
    ]
    try:
        for child in children:
            child.start()
        for child in children:
            child.join(timeout=20)
        assert all(child.exitcode == 0 for child in children)
        results = [queue.get(timeout=2) for _ in children]
        assert sorted(results) == [("OK", i) for i in range(6)]
    finally:
        for child in children:
            if child.is_alive():
                child.terminate()
                child.join(timeout=3)
        queue.close()


def _reentrant_worker(directory: str, queue) -> None:
    path = Path(directory)

    def callback(_execution_id):
        sd.guardar_dossier(
            {"dossier_id": "another", "mecanismo": "different synthetic"},
            path,
        )
        return _receipt()

    try:
        result = sd.registrar_resultado(
            "synthetic-d1", "positivo", execution_id="synthetic-exec",
            protocol_version="sha256:synthetic-protocol",
            execution_resolver=callback, directory=path,
        )
        queue.put(result["accreditation"])
    except Exception as exc:
        queue.put(type(exc).__name__)


def test_resolver_callback_can_reenter_storage_without_deadlock(tmp_path):
    sd.guardar_dossier(_dossier(), tmp_path)
    # A buggy lock-around-callback would deadlock. Bound the worker lifetime
    # rather than hanging the entire test process if this regression returns.
    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    process = ctx.Process(target=_reentrant_worker, args=(str(tmp_path), queue))
    try:
        process.start()
        process.join(timeout=12)
        assert process.exitcode == 0
        assert queue.get(timeout=2) == "ACCREDITED_EXECUTION"
        dossiers, _, _ = sd._leer_historial(tmp_path / "dossiers.jsonl")
        assert "another" in dossiers
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=3)
        queue.close()


def test_orphan_never_invokes_external_resolver(tmp_path):
    calls = []

    def callback(execution_id):
        calls.append(execution_id)
        raise AssertionError("Must not call resolver for orphaned dossier")

    with pytest.raises(ValueError, match="dossier existente"):
        sd.registrar_resultado(
            "missing", "positivo", execution_id="synthetic-exec",
            protocol_version="sha256:synthetic-protocol",
            execution_resolver=callback, directory=tmp_path,
        )
    assert calls == []
    assert not (tmp_path / "dossiers.jsonl").exists()


def test_resolver_unavailable_does_not_accredit(tmp_path):
    sd.guardar_dossier(_dossier(), tmp_path)

    def fail(_):
        raise RuntimeError("unavailable")

    result = sd.registrar_resultado(
        "synthetic-d1", "positivo", execution_id="synthetic-exec",
        protocol_version="sha256:synthetic-protocol",
        execution_resolver=fail, directory=tmp_path,
    )
    assert result["accreditation"] == "DECLARED_RESULT"
    assert result["learning_eligible"] is False
    assert sd.lecciones_previas(
        "Synthetic test case", directory=tmp_path, execution_resolver=fail
    ) == []


def test_changed_model_identity_cannot_accredit_declared_result(tmp_path):
    sd.guardar_dossier(_dossier(), tmp_path)

    def wrong(_):
        return {**_receipt(), "candidate_id": "someone-else"}

    result = sd.registrar_resultado(
        "synthetic-d1", "positivo", execution_id="synthetic-exec",
        protocol_version="sha256:synthetic-protocol",
        execution_resolver=wrong, directory=tmp_path,
    )
    assert result["accreditation"] == "DECLARED_RESULT"


def test_latest_unaccredited_revision_prevents_old_reward_resurrection(tmp_path):
    sd.guardar_dossier(_dossier(), tmp_path)
    first = _append(tmp_path)
    assert first["learning_eligible"] is True
    # A second revision for the same observation lacks an authoritative
    # receipt; a prior positive must not survive as a separate lesson.
    latest = sd.registrar_resultado(
        "synthetic-d1", "negativo", execution_id="synthetic-exec",
        protocol_version="sha256:synthetic-protocol",
        execution_resolver=lambda _: _receipt(),
        directory=tmp_path,
    )
    assert latest["revision_index"] == 1
    assert latest["learning_eligible"] is False
    assert sd.lecciones_previas(
        "Synthetic test case", directory=tmp_path,
        execution_resolver=lambda _: _receipt(),
    ) == []


def test_no_resolver_after_restart_never_promotes_saved_receipt(tmp_path):
    sd.guardar_dossier(_dossier(), tmp_path)
    _append(tmp_path)
    assert sd.lecciones_previas("Synthetic", directory=tmp_path) == []


def test_invalid_outcome_cannot_create_any_history(tmp_path):
    with pytest.raises(ValueError):
        sd.registrar_resultado("missing", "PASS", directory=tmp_path)
    assert not (tmp_path / ".dossiers.jsonl.lock").exists()
    assert not (tmp_path / "dossiers.jsonl").exists()


def test_first_registration_time_is_retained_across_revision(monkeypatch, tmp_path):
    from datetime import UTC, datetime

    sd.guardar_dossier(_dossier(), tmp_path)

    class Clock:
        current = datetime(2021, 1, 1, tzinfo=UTC)

        @classmethod
        def now(cls, _zone):
            return cls.current

    monkeypatch.setattr(sd, "datetime", Clock)
    first = _append(tmp_path)
    Clock.current = datetime(2035, 2, 2, tzinfo=UTC)
    second = _append(tmp_path)
    assert first["first_registered_at"] == "2021-01-01T00:00:00+00:00"
    assert second["first_registered_at"] == first["first_registered_at"]
    assert second["registrado_at"] == "2035-02-02T00:00:00+00:00"
