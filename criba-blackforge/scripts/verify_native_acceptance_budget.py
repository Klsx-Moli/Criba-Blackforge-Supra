"""Exercise the installed native proxy using ONLY a synthetic loopback upstream.

Run with Hermes Python and its source root on PYTHONPATH. No auth is loaded,
no provider is contacted, and native request/response forwarding is not mocked.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.acceptance_http_budget import (  # noqa: E402
    BudgetExceeded,
    BudgetLedger,
    install_native_budget,
)

MODEL = "fixture/native-model:free"
PROXY = "http://127.0.0.1:8645/v1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--negative-uninstrumented", action="store_true")
    args = parser.parse_args()
    import aiohttp
    from aiohttp import web
    from hermes_cli.proxy import server
    from hermes_cli.proxy.adapters.base import UpstreamAdapter, UpstreamCredential

    report = {
        "status": "FAIL",
        "real_provider_calls": 0,
        "transport": "installed native aiohttp HTTP forwarding, loopback upstream fixture",
        "checks": [],
        "negative_uninstrumented": args.negative_uninstrumented,
    }
    original = server._open_upstream

    async def exercise(directory):
        ledger = BudgetLedger(directory / "native.db", MODEL, PROXY, initialize=True)
        received = []
        retry = True

        async def upstream(request):
            nonlocal retry
            # Independent SQLite connection proves the reservation committed BEFORE receipt.
            with closing(sqlite3.connect(ledger.path)) as con, con:
                used = con.execute("SELECT used FROM budget").fetchone()[0]
                digest = hashlib.sha256(await request.read()).hexdigest()
                reservations = con.execute(
                    "SELECT COUNT(*) FROM attempts WHERE digest=?", (digest,)
                ).fetchone()[0]
            prior_same_body = sum(item == digest for item in received)
            assert used >= len(received) + 1, "no durable reservation before HTTP receipt"
            assert reservations > prior_same_body, (
                "received body has no prior committed reservation"
            )
            received.append(digest)
            if retry:
                retry = False
                return web.json_response({"synthetic_transport_only": True}, status=429)
            return web.json_response({"synthetic_transport_only": True})

        fixture = web.Application()
        fixture.router.add_post("/v1/chat/completions", upstream)
        fixture_runner = web.AppRunner(fixture, access_log=None)
        await fixture_runner.setup()
        site = web.TCPSite(fixture_runner, "127.0.0.1", 0)
        await site.start()
        fixture_port = site._server.sockets[0].getsockname()[1]

        class Adapter(UpstreamAdapter):
            name = "acceptance-fixture"
            display_name = "Synthetic local HTTP fixture, never a provider"
            allowed_paths = frozenset({"/chat/completions", "/completions", "/embeddings"})

            def is_authenticated(self):
                return True

            def get_credential(self):
                return UpstreamCredential(
                    "synthetic-fixture-only", f"http://127.0.0.1:{fixture_port}/v1"
                )

            def get_retry_credential(self, **_kwargs):
                return self.get_credential()

        if not args.negative_uninstrumented:
            install_native_budget(server, ledger)
        runner = web.AppRunner(
            server.create_app(Adapter(), bound_host="127.0.0.1"), access_log=None
        )
        await runner.setup()
        native = web.TCPSite(runner, "127.0.0.1", 0)
        await native.start()
        native_port = native._server.sockets[0].getsockname()[1]
        url = f"http://127.0.0.1:{native_port}/v1"
        try:
            async with aiohttp.ClientSession() as client:

                async def post(model=MODEL, path="/chat/completions"):
                    async with client.post(
                        url + path,
                        json={"model": model, "messages": [{"role": "user", "content": "fixture"}]},
                    ) as response:
                        await response.read()
                        return response.status

                assert await post() == 200
                assert ledger.used == len(received) == 2  # Native 429 retry was real HTTP.
                report["checks"].extend(["native_retry_counted", "durable_before_receive"])
                assert await post("paid-or-other-model") == 403
                assert ledger.used == len(received) == 2
                for path in ("/completions", "/embeddings"):
                    assert await post(path=path) == 403
                report["checks"].extend(
                    ["wrong_model_zero_forward", "other_inference_routes_denied"]
                )
                statuses = await asyncio.gather(*(post() for _ in range(24)))
                assert statuses.count(200) == 10 and statuses.count(403) == 14
                assert ledger.used == len(received) == 12
                assert await post() == 403
                assert len(received) == 12
                report["checks"].extend(
                    ["concurrent_http_never_exceeds_twelve", "thirteenth_not_sent"]
                )
                reader = (
                    "import sys; from scripts.acceptance_http_budget import BudgetLedger; "
                    "print(BudgetLedger(sys.argv[1],sys.argv[2],sys.argv[3]).used)"
                )
                child = await asyncio.to_thread(
                    subprocess.run,
                    [sys.executable, "-c", reader, str(ledger.path), MODEL, PROXY],
                    cwd=str(Path(__file__).resolve().parents[1]),
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=True,
                )
                assert child.stdout.strip() == "12"
                report["checks"].append("fresh_process_keeps_consumption")
                with closing(sqlite3.connect(ledger.path)) as con, con:
                    con.execute("UPDATE budget SET used=-1")
                assert await post() == 403 and len(received) == 12
                report["checks"].append("ledger_error_zero_forward")
        finally:
            await runner.cleanup()
            await fixture_runner.cleanup()
            server._open_upstream = original

    try:
        with tempfile.TemporaryDirectory(
            prefix="native-budget-verification-", dir=os.environ["TMPDIR"]
        ) as temp:
            directory = Path(temp)
            asyncio.run(exercise(directory))
            # Concurrent independent SQLite connections reserve at most twelve.
            ledger = BudgetLedger(directory / "concurrent.db", MODEL, PROXY, initialize=True)

            def reserve(_number):
                try:
                    return ledger.reserve(MODEL, b"synthetic")
                except BudgetExceeded:
                    return None

            with ThreadPoolExecutor(max_workers=12) as workers:
                reservations = list(workers.map(reserve, range(48)))
            assert sorted(x for x in reservations if x is not None) == list(range(1, 13))
            assert ledger.used == 12
            report["checks"].append("concurrent_durable_reservations")
        report["status"] = "NATIVE_GUARD_LOCAL_PASS"
    except Exception as exc:
        report.update(error_kind=type(exc).__name__, error=str(exc)[:300])
    finally:
        server._open_upstream = original
    report["native_server_sha256"] = hashlib.sha256(Path(server.__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return 0 if report["status"] == "NATIVE_GUARD_LOCAL_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
