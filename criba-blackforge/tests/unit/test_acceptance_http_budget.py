"""Acceptance instrumentation must count physical attempts durably and fail closed."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import httpx
import pytest

MODEL = "fixture/model:free"


def test_native_proxy_retry_is_counted_at_each_upstream_open(tmp_path):
    import asyncio
    from types import SimpleNamespace

    from scripts.acceptance_http_budget import BudgetLedger, install_native_budget

    ledger = BudgetLedger(
        tmp_path / "native.sqlite3", MODEL, "http://127.0.0.1:8645/v1", initialize=True
    )
    forwarded = []

    async def original(*args):
        forwarded.append(args)
        return "session", "response"

    server = SimpleNamespace(_open_upstream=original, _json_error=lambda status, *_a, **_k: status)
    install_native_budget(server, ledger)
    body = json.dumps({"model": MODEL}).encode()
    for _ in range(12):
        assert (
            asyncio.run(server._open_upstream(None, "/chat/completions", body, None))[1]
            == "response"
        )
    assert asyncio.run(server._open_upstream(None, "/chat/completions", body, None)) == (403, None)
    assert len(forwarded) == ledger.used == 12


def test_ledger_closes_each_sqlite_connection(tmp_path, monkeypatch):
    import sqlite3

    from scripts.acceptance_http_budget import BudgetLedger

    ledger = BudgetLedger(
        tmp_path / "handles.db", MODEL, "http://127.0.0.1:8645/v1", initialize=True
    )
    opened = []
    original = sqlite3.connect

    def connect(*args, **kwargs):
        connection = original(*args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", connect)
    assert ledger.used == 0
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")


def test_budget_counts_twelve_attempts_and_refuses_the_thirteenth(tmp_path):
    from scripts.acceptance_http_budget import BudgetExceeded, BudgetLedger

    ledger = BudgetLedger(
        tmp_path / "budget.sqlite3", MODEL, "http://127.0.0.1:8645/v1", initialize=True
    )
    for number in range(1, 13):
        assert ledger.reserve(MODEL, b"synthetic") == number
    with pytest.raises(BudgetExceeded):
        ledger.reserve(MODEL, b"synthetic")
    assert ledger.used == 12
    reopened = BudgetLedger(ledger.path, MODEL, ledger.upstream)
    assert reopened.used == 12
    with pytest.raises(BudgetExceeded):
        reopened.reserve(MODEL, b"synthetic")


def test_budget_rejects_other_models_missing_ledger_and_changed_configuration(tmp_path):
    from scripts.acceptance_http_budget import BudgetLedger

    path = tmp_path / "budget.sqlite3"
    with pytest.raises(FileNotFoundError):
        BudgetLedger(path, MODEL, "http://127.0.0.1:8645/v1")
    ledger = BudgetLedger(path, MODEL, "http://127.0.0.1:8645/v1", initialize=True)
    for model in ("paid/model", "another/model:free"):
        with pytest.raises(ValueError):
            ledger.reserve(model, b"synthetic")
    assert ledger.used == 0
    with pytest.raises(ValueError):
        BudgetLedger(path, MODEL, "http://127.0.0.1:9000/v1")


def test_http_guard_refuses_over_budget_without_forwarding(tmp_path):
    from scripts.acceptance_http_budget import BudgetLedger, budget_proxy

    received = []

    class Upstream(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            body = b'{"synthetic_transport_only":true}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    thread = Thread(target=upstream.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{upstream.server_port}/v1"
        ledger = BudgetLedger(tmp_path / "budget.sqlite3", MODEL, url, initialize=True)
        with budget_proxy(ledger) as endpoint:
            for _ in range(12):
                assert (
                    httpx.post(endpoint + "/chat/completions", json={"model": MODEL}).status_code
                    == 200
                )
            assert (
                httpx.post(endpoint + "/chat/completions", json={"model": MODEL}).status_code == 403
            )
            assert (
                httpx.post(endpoint + "/chat/completions", json={"model": "paid"}).status_code
                == 403
            )
        assert len(received) == ledger.used == 12
    finally:
        upstream.shutdown()
        upstream.server_close()
        thread.join(timeout=5)
