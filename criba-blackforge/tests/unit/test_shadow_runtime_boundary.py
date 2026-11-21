"""Regression sentinels for the Windows Shadow/SUPRA startup trust boundaries.

Tests use ephemeral loopback HTTP and isolated state. No real SUPRA, model or
BLACKFORGE credentials are required. A 200 from an unrelated service is NOT
readiness, and the PID written to disk is NOT the single-writer authority.
"""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def launcher(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path / "isolated"))
    return importlib.import_module("criba_shadow_main")


class _Health(BaseHTTPRequestHandler):
    payload: object = {}
    status_code = 200
    redirect = False

    def do_GET(self):
        if self.path == "/health" and type(self).redirect:
            self.send_response(302)
            self.send_header("Location", "/ready")
            self.end_headers()
            return
        body = json.dumps(type(self).payload).encode("utf-8")
        self.send_response(type(self).status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


@pytest.fixture()
def probe_server():
    # A per-test subclass avoids state races with other tests in the suite.
    handler = type("ProbeForTest", (_Health,), {})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", handler
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=10)


def test_200_from_unrelated_service_does_not_count_as_supra(launcher, probe_server):
    endpoint, handler = probe_server
    handler.payload = {"status": "healthy", "service": "unrelated", "storage": {}}
    assert not launcher.health_ok(endpoint)


def test_empty_json_and_malformed_health_are_not_supra(launcher, probe_server):
    endpoint, handler = probe_server
    for payload in ({}, [], None, {"status": "healthy"}, {"status": "healthy", "service": "supra-agentic-taskmaster"}):
        handler.payload = payload
        assert not launcher.health_ok(endpoint)


def test_correctly_identified_local_supra_can_be_reused(launcher, probe_server):
    endpoint, handler = probe_server
    handler.payload = {
        "status": "healthy",
        "service": "supra-agentic-taskmaster",
        "storage": {"mode": "LOCAL_FILESYSTEM"},
    }
    assert launcher.health_ok(endpoint)


def test_redirect_does_not_count_as_supra(launcher, probe_server):
    endpoint, handler = probe_server
    handler.redirect = True
    handler.payload = {
        "status": "healthy",
        "service": "supra-agentic-taskmaster",
        "storage": {},
    }
    assert not launcher.health_ok(endpoint)


@pytest.mark.parametrize("endpoint", [
    "https://127.0.0.1:7777",
    "http://127.0.0.2:7777",
    "http://example.org:7777",
    "http://127.0.0.1:7777/other",
    "http://user:pass@127.0.0.1:7777",
])
def test_noncanonical_endpoints_are_rejected_without_network(launcher, endpoint):
    assert not launcher.health_ok(endpoint)


def test_os_lock_refuses_competitor_even_if_pid_metadata_is_forged(launcher, tmp_path):
    root = launcher.data_root()
    acquired, reason = launcher.acquire_single_instance(root)
    assert acquired, reason
    try:
        # A forged/dead PID must not allow a second process to take the lock.
        (root / launcher.LOCK_NAME).write_text(
            json.dumps({"pid": 999999, "started": "2020-01-01"}),
            encoding="utf-8",
        )
        code = (
            "import sys;from pathlib import Path;"
            f"sys.path.insert(0,{str(ROOT)!r});"
            "import criba_shadow_main as m;"
            f"ok,msg=m.acquire_single_instance(Path({str(root)!r}));"
            "print('ACQUIRED' if ok else 'BLOCKED')"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=35, check=True,
        )
        assert result.stdout.strip() == "BLOCKED"
    finally:
        launcher.release_single_instance(root)


def test_stale_pid_metadata_without_os_lock_is_recoverable(launcher):
    root = launcher.data_root()
    (root / launcher.LOCK_NAME).write_text(
        json.dumps({"pid": 999999, "started": "2020-01-01"}), encoding="utf-8"
    )
    acquired, reason = launcher.acquire_single_instance(root)
    assert acquired, reason
    launcher.release_single_instance(root)
