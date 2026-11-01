"""Ordinary tests are offline; real inference is an explicitly guarded acceptance."""

import os
from pathlib import Path

import pytest

from tests.offline_inference_guard import install_offline_guard


def pytest_addoption(parser):
    parser.addoption(
        "--live-inference-ledger",
        default=None,
        help="Explicit opt-in: existing ledger of the instrumented native proxy",
    )


@pytest.fixture(autouse=True)
def offline_inference_boundary(monkeypatch, tmp_path, request):
    ledger_path = request.config.getoption("--live-inference-ledger")
    if ledger_path:
        from scripts.acceptance_http_budget import BudgetLedger

        if os.environ.get("CRIBA_EXTERNAL_BASE_URL") != "http://127.0.0.1:8645/v1":
            pytest.fail("Live acceptance requires the approved guarded proxy endpoint")
        model = os.environ.get("CRIBA_EXTERNAL_MODEL", "poolside/laguna-s-2.1:free")
        BudgetLedger(Path(ledger_path), model, "http://127.0.0.1:8645/v1")
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "isolated-model-settings.json"))
    install_offline_guard(monkeypatch, live_proxy=bool(ledger_path))
