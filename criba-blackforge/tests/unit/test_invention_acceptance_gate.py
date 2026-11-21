"""Acceptance must reject pending/empty output, not count GUI startup as a proposal."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow_ui"))


@pytest.mark.parametrize(
    "entry",
    [
        {},
        {"estado_interpretacion": "PENDIENTE_INTERPRETACION"},
        {"estado_interpretacion": "PROPUESTA", "hipotesis": "idea", "mecanismo": ""},
    ],
)
def test_invention_acceptance_rejects_pending_or_empty_output(entry):
    from shadow_invention_probe import chosen_entry

    with pytest.raises(ValueError):
        chosen_entry({"entries": [entry]})


def test_failed_acceptance_retains_diagnostics_without_raw_response(tmp_path):
    import json
    from types import SimpleNamespace

    from shadow_invention_probe import InventionProbe

    sheet = {
        "entries": [
            {
                "estado_interpretacion": "PENDIENTE_INTERPRETACION",
                "interpretacion_error": "schema:missing_mecanismo",
                "interpretacion_error_kind": "schema",
                "interpretacion_diagnostico": {
                    "error_code": "SCHEMA_VALIDATION_FAILED",
                    "phase": "validacion",
                    "retryable": False,
                    "next_action": "La respuesta no cumple el esquema del contrato.",
                },
                "interpretacion_raw_output": "private-raw-sentinel",
            }
        ]
    }
    probe = SimpleNamespace(directory=tmp_path)
    InventionProbe.preserve_sheet(probe, "shadow", sheet)
    text = (tmp_path / "shadow-observed-diagnostics.json").read_text(encoding="utf-8")
    assert "private-raw-sentinel" not in text
    diagnostics = json.loads(text)
    assert diagnostics["entries"][0]["interpretacion_error"] == "schema:missing_mecanismo"
    assert diagnostics["entries"][0]["interpretacion_error_kind"] == "schema"
    assert diagnostics["entries"][0]["interpretacion_diagnostico"]["error_code"] == (
        "SCHEMA_VALIDATION_FAILED"
    )
    assert diagnostics["entries"][0]["interpretacion_diagnostico"]["retryable"] is False


@pytest.mark.parametrize("kind", ["shadow", "blackforge"])
def test_failure_diagnostics_retain_run_identity_without_private_input(tmp_path, kind):
    """Synthetic metadata fixture, not a captured provider response or acceptance."""
    import json
    from types import SimpleNamespace

    from shadow_invention_probe import InventionProbe

    sheet = {
        "run_id": "synthetic-run-identity",
        "generated_at": "2026-10-29T00:00:00+00:00",
        "query": "private-query-sentinel",
        "entries": [
            {
                "candidate_id": "synthetic-candidate",
                "estado_interpretacion": "PENDIENTE_INTERPRETACION",
                "interpretacion_error": "synthetic-contract-rejection",
                "interpretacion_raw_output": "private-response-sentinel",
            }
        ],
    }
    InventionProbe.preserve_sheet(SimpleNamespace(directory=tmp_path), kind, sheet)
    text = (tmp_path / f"{kind}-observed-diagnostics.json").read_text(encoding="utf-8")
    diagnostics = json.loads(text)
    assert diagnostics["run_id"] == sheet["run_id"]
    assert diagnostics["generated_at"] == sheet["generated_at"]
    assert diagnostics["entries"][0]["interpretacion_error"] == "synthetic-contract-rejection"
    assert "private-query-sentinel" not in text
    assert "private-response-sentinel" not in text


def test_shadow_only_acceptance_never_opens_blackforge(tmp_path, monkeypatch):
    import time
    from types import SimpleNamespace

    import criba.ui.blackforge_window as blackforge
    from shadow_invention_probe import InventionProbe

    monkeypatch.setenv("CRIBA_ACCEPTANCE_SHADOW_ONLY", "1")
    attempted = []

    def forbidden(*_args, **_kwargs):
        attempted.append("blackforge")
        raise AssertionError("A Shadow-only authorization cannot start BLACKFORGE")

    monkeypatch.setattr(blackforge, "BlackforgeWindow", forbidden)
    sheet = {
        "entries": [
            {
                "estado_interpretacion": "PROPUESTA",
                "hipotesis": "synthetic fixture",
                "mecanismo": "fixture mechanism",
            }
        ]
    }
    candidates = SimpleNamespace(
        show_interpreter_entry=lambda _index: None,
        interpretation_output=SimpleNamespace(toPlainText=lambda: "fixture mechanism"),
        save_idea=SimpleNamespace(click=lambda: None),
    )
    window = SimpleNamespace(
        invent_sheet=sheet,
        _live_workers=[],
        candidates=candidates,
        store=SimpleNamespace(list_sessions=lambda: [{"id": "fixture-only"}]),
    )
    exits, failures = [], []
    probe = SimpleNamespace(
        started=time.monotonic(),
        stage="SHADOW_GENERATE",
        window=window,
        preserve_sheet=lambda *_args: None,
        remember=lambda *_args: None,
        snapshot=lambda *_args: None,
        expected={},
        directory=tmp_path,
        home=tmp_path,
        report={},
        finish=exits.append,
        fail=failures.append,
    )
    InventionProbe.poll(probe)
    assert attempted == []
    assert failures == []
    assert exits == [0]
    assert probe.report["status"] == "REAL_SHADOW_JOURNEY_PASS"


def test_invention_acceptance_selects_an_actual_proposal_not_the_first_pending():
    from shadow_invention_probe import chosen_entry

    entry = {
        "estado_interpretacion": "PROPUESTA",
        "hipotesis": "synthetic fixture",
        "mecanismo": "synthetic transport fixture only",
    }
    assert chosen_entry({"entries": [{}, entry]}) == 1


def test_live_acceptance_disables_provider_retries_before_generation(monkeypatch):
    import os
    from types import SimpleNamespace

    from shadow_invention_probe import InventionProbe

    monkeypatch.setenv("CRIBA_ACCEPTANCE_PHYSICAL_BUDGET", "12")
    monkeypatch.delenv("CRIBA_ACCEPTANCE_NO_RETRIES", raising=False)
    observed = []
    failures = []
    window = SimpleNamespace(problem="")
    problem_input = SimpleNamespace(
        setText=lambda text: setattr(window, "problem", text),
        returnPressed=SimpleNamespace(emit=lambda: None),
    )
    window.header = SimpleNamespace(problem_input=problem_input)
    window.topcards = SimpleNamespace(
        btn_gen=SimpleNamespace(
            click=lambda: observed.append(os.environ.get("CRIBA_ACCEPTANCE_NO_RETRIES"))
        )
    )
    probe = SimpleNamespace(mode="invention", window=window, fail=failures.append, stage="START")

    try:
        InventionProbe.begin(probe)

        assert failures == []
        assert observed == ["1"]
        assert probe.stage == "SHADOW_GENERATE"
    finally:
        os.environ.pop("CRIBA_ACCEPTANCE_NO_RETRIES", None)
