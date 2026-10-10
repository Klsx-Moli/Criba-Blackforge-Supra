"""M1 honesto — el banco separa error técnico (json_invalido) del derivado (invalid_json).

Se exige que al menos dos intentos con salida no-JSON conserven el error técnico
exacto y la causa derivada como campos separados, sin sobrescribir uno por otro.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from criba.interprete.openai_compatible import LocalLlamaInterpreter


class _FakeLocalHandler(BaseHTTPRequestHandler):


    def do_GET(self) -> None:
        if self.path.endswith("/models"):
            body = json.dumps({"object": "list", "data": [{"id": "criba-local"}]}).encode()
        else:
            body = b"{}"
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        payload_raw = self.rfile.read(length) if length else b""
        payload_str = payload_raw.decode("utf-8", errors="replace") if isinstance(payload_raw, bytes) else str(payload_raw)
        body = json.dumps(
            {"model": "criba-local", "choices": [{"finish_reason": "stop", "message": {"content": "not json"}}]}
        ).encode() if "Reducir" in payload_str or "Eliminar" in payload_str else json.dumps(
            {"choices": [{"finish_reason": "stop", "message": {"content": '{"pertinencia": "ABSTENER", "motivo_abstencion": "no relacionado con el cruce"}'}}]}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        pass


def test_local_M1_preserva_error_tecnico_json_invalido(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), _FakeLocalHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("CRIBA_LOCAL_BASE", f"http://127.0.0.1:{port}/v1")
        monkeypatch.setenv("CRIBA_LOCAL_MODEL", "criba-local")
        local = LocalLlamaInterpreter()

        ok, reason = local.operativo()
        assert ok is False
        assert "falta superar el banco local" in reason
        report = local.gate_report
        assert report is not None
        assert report["passed"] is False
        assert report["total_attempts"] == 8
        assert report["completed_attempts"] == 8

        # PASO 2 — aserciones honestas (no simplificadas para que pasen):
        intentos_json_invalido = [
            i for c in report["cases"] for i in c["attempts"]
            if (i.get("technical_error") or "").startswith("json_invalido:")
        ]
        assert len(intentos_json_invalido) >= 2, (
            f"se esperan al menos 2 intentos con json_invalido; hay {len(intentos_json_invalido)}"
        )
        for i in intentos_json_invalido:
            assert i["derived_error"] == "invalid_json", i
            assert i["result"] == "ERROR", i
            assert i["raw_output"] is not None, "raw_output debe conservarse (aunque sea vacío)"

        # Los intentos de dominio (JSON válido pero abstención) no deben tener error técnico.
        intentos_dominio = [
            i for c in report["cases"] for i in c["attempts"]
            if (i.get("derived_error") or "").startswith("validacion:")
        ]
        assert len(intentos_dominio) >= 2, f"se esperan intentos de dominio; hay {len(intentos_dominio)}"
        for i in intentos_dominio:
            assert i["technical_error"] is None, f"domain error no debe sobrescribir technical: {i}"
            assert i["result"] == "REJECTED", i

        # Propuesta posterior queda pendiente con motivo operativo, sin campos fabricados.
        for case in (
            {"query": "Reducir la cola", "idea": {"method1": "Poka-Yoke", "title": "t"}},
            {"query": "Eliminar segundas", "idea": {"method1": "Confirmación", "title": "t2"}},
        ):
            result = local.proponer(case["query"], case["idea"], None, [])
            assert not result.es_propuesta
            assert result.estado == "PENDIENTE_INTERPRETACION"
            assert "falta superar el banco local" in result.error
            assert result.raw_output == ""
            assert result.model_requests == 0
            assert result.provenance is not None
    finally:
        server.shutdown()
