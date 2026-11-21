"""Opt-in acceptance HTTP guard; never used by normal product execution.

Counts physical POST attempts before forwarding, including failed attempts and retries.
Only the approved model and one loopback upstream can pass. No headers or prompts are logged.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit


class BudgetExceeded(RuntimeError):
    """The authorized physical-attempt budget has been consumed."""


class BudgetLedger:
    def __init__(self, path, model: str, upstream: str, *, initialize=False):
        self.path = Path(path)
        self.model, self.upstream = model, upstream.rstrip("/")
        parsed = urlsplit(self.upstream)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost"}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path != "/v1"
            or not model.endswith(":free")
        ):
            raise ValueError("Acceptance permits one loopback /v1 upstream and a free model only")
        if initialize:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("xb"):
                pass
            with closing(sqlite3.connect(self.path)) as con, con:
                con.execute("CREATE TABLE budget(model TEXT, upstream TEXT, used INTEGER)")
                con.execute("INSERT INTO budget VALUES(?,?,0)", (model, self.upstream))
                con.execute("CREATE TABLE attempts(id INTEGER PRIMARY KEY, at TEXT, digest TEXT)")
        if not self.path.is_file():
            raise FileNotFoundError("Authorized ledger must already exist")
        with self._connect() as con:
            self._state(con)

    @contextmanager
    def _connect(self):
        # mode=rw refuses accidental recreation; sqlite's transaction context alone
        # does not close the handle (locks the file on Windows).
        with (
            closing(
                sqlite3.connect(self.path.resolve().as_uri() + "?mode=rw", uri=True, timeout=30)
            ) as connection,
            connection,
        ):
            yield connection

    def _state(self, con):
        rows = con.execute("SELECT model,upstream,used FROM budget").fetchall()
        if len(rows) != 1 or rows[0][:2] != (self.model, self.upstream):
            raise ValueError("Acceptance configuration differs from the authorized ledger")
        used = rows[0][2]
        count, latest = con.execute("SELECT COUNT(*),COALESCE(MAX(id),0) FROM attempts").fetchone()
        if type(used) is not int or not 0 <= used <= 12 or count != used or latest != used:
            raise ValueError("Acceptance ledger is inconsistent; refusing to reset its budget")
        return used

    @property
    def used(self):
        with self._connect() as con:
            return self._state(con)

    def reserve(self, model: str, payload: bytes) -> int:
        if model != self.model:
            raise ValueError("Model is outside this acceptance authorization")
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            used = self._state(con)
            if used >= 12:
                raise BudgetExceeded("Twelve physical attempts consumed; no request forwarded")
            number = used + 1
            con.execute("UPDATE budget SET used=?", (number,))
            con.execute(
                "INSERT INTO attempts VALUES(?,?,?)",
                (
                    number,
                    datetime.now(UTC).isoformat(),
                    hashlib.sha256(payload).hexdigest(),
                ),
            )
        return number


def install_native_budget(server, ledger: BudgetLedger):
    """Instrument each native upstream open, including its OAuth retry.

    Process-local acceptance instrumentation only; the installed Hermes source is unchanged.
    The inspected native opener sends exactly once with allow_redirects=False.
    """
    original = server._open_upstream

    async def counted(request, rel_path, body, credential):
        if rel_path != "/chat/completions":
            if rel_path == "/models" and getattr(request, "method", None) == "GET":
                return await original(request, rel_path, body, credential)
            return server._json_error(403, "Acceptance path refused"), None
        if rel_path == "/chat/completions":
            try:
                payload = json.loads(body)
                ledger.reserve(payload.get("model"), body)
            except (ValueError, AttributeError, BudgetExceeded, sqlite3.Error, OSError):
                return server._json_error(403, "Acceptance budget/model refused"), None
        return await original(request, rel_path, body, credential)

    server._open_upstream = counted


@contextmanager
def budget_proxy(ledger: BudgetLedger):
    target = urlsplit(ledger.upstream)

    class Guard(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, status, body, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path != "/v1/models":
                self.reply(403, b'{"error":"acceptance_path_denied"}')
                return
            self.forward(None)

        def do_POST(self):
            try:
                if self.path != "/v1/chat/completions":
                    raise ValueError("path")
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 2_000_000:
                    raise ValueError("payload size")
                body = self.rfile.read(size)
                payload = json.loads(body)
                if not isinstance(payload, dict) or payload.get("stream"):
                    raise ValueError("Only ordinary non-streaming acceptance requests")
                ledger.reserve(payload.get("model"), body)
            except (ValueError, BudgetExceeded, sqlite3.Error, OSError):
                self.reply(403, b'{"error":"acceptance_request_denied"}')
                return
            self.forward(body)

        def forward(self, body):
            connection = http.client.HTTPConnection(target.hostname, target.port, timeout=240)
            try:
                headers = {
                    name: self.headers[name]
                    for name in ("Authorization", "Content-Type")
                    if name in self.headers
                }
                connection.request(self.command, self.path, body=body, headers=headers)
                response = connection.getresponse()
                content = response.read()
                self.reply(
                    response.status, content, response.getheader("Content-Type", "application/json")
                )
            except (OSError, http.client.HTTPException):
                self.reply(502, b'{"error":"acceptance_upstream_unavailable"}')
            finally:
                connection.close()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Guard)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)
