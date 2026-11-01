"""Non-chat native forwarding must not bypass an inference budget."""

import asyncio
from types import SimpleNamespace

from scripts.acceptance_http_budget import BudgetLedger, install_native_budget


def test_native_acceptance_refuses_other_inference_routes(tmp_path):
    ledger = BudgetLedger(
        tmp_path / "budget.db", "fixture/model:free", "http://127.0.0.1:8645/v1", initialize=True
    )
    sent = []

    async def original(*args):
        sent.append(args)
        return "session", "response"

    server = SimpleNamespace(_open_upstream=original, _json_error=lambda *_a, **_k: 403)
    install_native_budget(server, ledger)
    for path in ("/completions", "/embeddings", "/responses"):
        assert asyncio.run(server._open_upstream(None, path, b"{}", None)) == (403, None)
    assert sent == []
    assert ledger.used == 0
