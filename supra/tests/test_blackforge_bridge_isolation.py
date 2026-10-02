"""K2 (SUPRA side): BLACKFORGE trouble must be data, never a raised error.

The CRIBA half of the BLACKFORGE isolation gate lives in
criba-blackforge/tests/unit/test_blackforge_isolation_gate.py. This file covers
the SUPRA boundary, which reaches BLACKFORGE only through a subprocess bridge.

BLACKFORGE is DEFERRED / UNDER_CONSTRUCTION. Nothing here develops it, and
nothing here requires it to exist: every assertion holds whether or not the
BLACKFORGE pipeline can run on this machine.
"""

from __future__ import annotations

import subprocess

import pytest
from supra_agentic.integrations import criba_bridge


def test_call_blackforge_never_raises_when_the_pipeline_cannot_run():
    """An unavailable optional capability must degrade to data, not an exception."""
    outcome = criba_bridge.call_blackforge("K2 isolation probe")
    assert isinstance(outcome, dict)
    assert "error" in outcome or "raw_output" in outcome


def test_call_blackforge_failure_does_not_leak_stderr():
    """A failing optional subprocess must not echo its stderr to the caller."""
    outcome = criba_bridge.call_blackforge("K2 isolation probe")
    if "error" in outcome:
        assert outcome.get("stderr_redacted") is True
        assert "Traceback" not in str(outcome)


def test_call_criba_is_not_gated_on_blackforge(monkeypatch):
    """CRIBA's own bridge path must not consult BLACKFORGE at all."""
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout='{"packet_type": "M"}', stderr="")

    monkeypatch.setattr(criba_bridge.subprocess, "run", fake_run)
    outcome = criba_bridge.call_criba("probe query")
    assert outcome == {"packet_type": "M"}
    assert calls, "CRIBA bridge did not invoke a subprocess"
    assert "blackforge" not in calls[0]


def test_criba_bridge_survives_an_unresolvable_criba_root(monkeypatch, tmp_path):
    """A wrong CRIBA_ROOT must produce an error dict, never a traceback."""
    monkeypatch.setattr(criba_bridge, "_get_criba_root", lambda: str(tmp_path))
    outcome = criba_bridge.call_criba("probe query")
    assert isinstance(outcome, dict)
    assert "error" in outcome


@pytest.mark.parametrize("call", ["call_criba", "call_blackforge"])
def test_bridge_timeout_is_reported_as_data(monkeypatch, call):
    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout", 1))

    monkeypatch.setattr(criba_bridge.subprocess, "run", fake_run)
    outcome = getattr(criba_bridge, call)("probe query")
    assert isinstance(outcome, dict)
    assert "timeout" in str(outcome.get("error", "")).lower()
