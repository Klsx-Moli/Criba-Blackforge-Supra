"""Loopback OpenAI-compatible stub for deterministic GUI and transport tests."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


def _proposal(prompt: str) -> dict[str, Any]:
    token = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
    return {
        "pertinencia": "PERTINENTE",
        "hipotesis": (
            "La retención física de la bandeja reduce los registros erróneos "
            "que avanzan al siguiente puesto."
        ),
        "cadena_causal": [
            "La etiqueta se compara con la orden en el lector de la estación.",
            "Si no coincide, el pestillo retiene la bandeja hasta la corrección.",
        ],
        "mecanismo": (
            f"El pestillo {token} de la caja de retención bloquea la bandeja "
            "cuando el lector óptico detecta una etiqueta que no coincide con "
            "la orden; la bandeja permanece retenida hasta que el operador "
            "corrige la etiqueta y libera el pestillo."
        ),
        "aportacion_por_tecnica": [
            "El lector aporta la comparación local entre etiqueta y orden.",
            "El pestillo aporta la retención física de la bandeja.",
        ],
        "supuestos": ["Las etiquetas son legibles en la estación de empaque."],
        "evidencia_citada": [],
        "conocimiento_previo": [
            "La retención física impide que el registro erróneo avance.",
        ],
        "incertidumbre": "No se conoce la tasa de falsos rechazos del lector.",
        "novedad": "Los antecedentes concretos no se han verificado.",
        "prueba_concreta": (
            "Comparar errores por 1.000 registros con el pestillo activo y desactivado."
        ),
        "prueba": {
            "metrica": "errores por 1.000 registros",
            "baseline": "cinta sin pestillo de retención",
            "umbral": "reducción de al menos 20%",
            "condicion_fracaso": "reducción menor al 5% o más tiempo de inspección",
            "alternativa_explicativa": (
                "La mejora se explica por mayor atención del operador, no por el pestillo."
            ),
            "resultado_favorable_mecanismo": (
                "El grupo con pestillo reduce los errores al menos 20%."
            ),
            "resultado_favorable_alternativa": (
                "Ambos grupos reducen igual y el pestillo no cambia el resultado."
            ),
        },
        "comprobacion_restricciones": [],
        "ruta_desbloqueo": "sustituir_mecanismo",
    }


def _critique() -> dict[str, Any]:
    from criba.interprete.contrato import PREGUNTAS

    return {
        "pertinente": True,
        "mecanismo_especifico": True,
        "falsable": True,
        "fiel_evidencia": True,
        "restricciones_respetadas": True,
        "discrimina_alternativas": True,
        "intercambio_tecnicas_generico": False,
        "objeciones": [],
        "incertidumbre": "Crítica de stub: no demuestra eficacia ni novedad.",
        "respuestas_epistemologicas": {
            pregunta.id: f"Respuesta de stub para {pregunta.id}." for pregunta in PREGUNTAS
        },
    }


def _refinement() -> dict[str, Any]:
    return {
        "resumen": "Retención física de la bandeja en la salida de empaque.",
        "fuente_error": "La etiqueta incorrecta avanza asociada a la orden equivocada.",
        "punto_intervencion": "Salida de la cinta 2, estación de empaque.",
        "por_que_reduce": (
            "Impide que el registro erróneo continúe antes de que el operador corrija la etiqueta."
        ),
        "mecanismo_concreto": (
            "El lector óptico compara la etiqueta con la orden y activa el "
            "pestillo; el pestillo bloquea la bandeja en la salida hasta que "
            "el operador corrige la etiqueta y libera el paso."
        ),
        "punto_fisico": "Salida de la cinta 2, estación de empaque.",
        "modo_efecto": "MITIGA",
        "prueba_mecanismo": (
            "Comparar la tasa de registros erróneos que llegan al siguiente "
            "puesto con el pestillo activo y desactivado."
        ),
        "componentes": [
            "Lector óptico - captura la etiqueta - interfaz de la cinta",
            "Pestillo - bloquea la bandeja - salida de la cinta",
        ],
        "secuencia_operativa": [
            "Etiqueta leída -> comparación con la orden -> si no coincide, el pestillo retiene",
            "Operador corrige -> pestillo libera -> el registro continúa",
        ],
        "definiciones_operativas": [
            "Error: etiqueta que no coincide con la orden.",
            "Error menor: discrepancia corregida antes de la salida.",
            "Error mayor: registro erróneo que llega al siguiente puesto.",
        ],
        "criterio_dominancia": "Pareto 80/20 sobre las causas observadas.",
        "asignacion_presupuesto": "Priorizar la inspección de las causas dominantes.",
        "metrica_principal": "Errores por 1.000 registros",
        "metrica_secundaria": "Tiempo medio de inspección por registro",
        "regla_exito": "Reducción de al menos 20% sin aumentar el tiempo más de 10%.",
        "banda_intermedia": "Reducción entre 5% y 20%: repetir con más muestra.",
        "condicion_fracaso": "Reducción menor al 5% o aumento de tiempo mayor al 10%.",
        "guardarrail_tiempo": "Detener el brazo si el tiempo medio sube más de 10%.",
        "prueba_brazos": [
            {
                "brazo": "A",
                "descripcion": "Pestillo activo",
                "metrica": "errores por 1.000 registros",
                "umbral": "reducción >= 20%",
            },
            {
                "brazo": "B",
                "descripcion": "Sin pestillo",
                "metrica": "errores por 1.000 registros",
                "umbral": "línea base",
            },
            {
                "brazo": "C",
                "descripcion": "Solo aviso al operador",
                "metrica": "errores por 1.000 registros",
                "umbral": "sin reducción esperada",
            },
        ],
        "tamano_muestra": "Mínimo 500 registros por brazo, ajustable a calibrar.",
        "riesgos": [
            "Falsos rechazos por etiquetas dañadas.",
            "Retención de la cinta si el operador no corrige.",
        ],
        "condiciones_parada": [
            "Falsos rechazos superiores al 5%.",
            "Aumento del tiempo medio superior al 10%.",
        ],
        "parametros_a_calibrar": ["Umbral de similitud del lector"],
        "limitaciones": "Protocolo propuesto; no es una validación experimental.",
    }


@dataclass
class StubOpenAIConfig:
    mode: str = "success"
    delay_s: float = 0.0
    model_id: str = "stub/valid-model"
    requests: list[dict[str, Any]] = field(default_factory=list)


class _Handler(BaseHTTPRequestHandler):
    server: Any

    def log_message(self, format: str, *args: Any) -> None:
        del format, args

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.rstrip("/") != "/v1/models":
            self._send_json(404, {"error": {"message": "not found"}})
            return
        self._send_json(
            200,
            {
                "object": "list",
                "data": [{"id": self.server.config.model_id, "object": "model"}],
            },
        )

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._send_json(404, {"error": {"message": "not found"}})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            request = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": {"message": "invalid json"}})
            return
        with self.server.lock:
            self.server.config.requests.append(request)
        if self.server.config.delay_s:
            time.sleep(self.server.config.delay_s)
        if self.server.config.mode == "429":
            self._send_json(429, {"error": {"message": "rate limited"}})
            return
        messages = request.get("messages") or []
        prompt = "\n".join(
            str(message.get("content") or "") for message in messages if isinstance(message, dict)
        )
        if "PROPUESTA A CRITICAR" in prompt:
            payload = _critique()
        elif "Convierte la propuesta en un protocolo operativo" in prompt:
            payload = _refinement()
        else:
            payload = _proposal(prompt)
        content = json.dumps(payload, ensure_ascii=False)
        self._send_json(
            200,
            {
                "id": "stub-completion",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": str(request.get("model") or self.server.config.model_id),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"completion_tokens": 1, "total_tokens": 1},
            },
        )


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, config: StubOpenAIConfig) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.config = config
        self.lock = threading.Lock()


class StubOpenAIServer:
    """A loopback-only server implementing the subset CRIBA calls."""

    def __init__(self, *, mode: str = "success", delay_s: float = 0.0) -> None:
        self.config = StubOpenAIConfig(mode=mode, delay_s=delay_s)
        self._server = _Server(self.config)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}/v1"

    @property
    def requests(self) -> list[dict[str, Any]]:
        with self._server.lock:
            return list(self.config.requests)

    def __enter__(self) -> StubOpenAIServer:
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
