"""Wrappers históricos del puerto único, sin puntuaciones ni fallbacks."""

from __future__ import annotations

from typing import Any

import httpx as httpx  # historical public transport hook

from .openai_compatible import LocalLlamaInterpreter, OpenAICompatibleInterpreter
from .protocolo import protocolo_para

ZAI_BASE = "https://api.z.ai/v1"
DEFAULT_MODEL = "glm-5.3-flash"


class LocalInterprete:
    """Alias histórico del runtime local real; nunca llama a Nous ni puntúa."""

    def __init__(self) -> None:
        self.interpreter: OpenAICompatibleInterpreter = LocalLlamaInterpreter()
        self.model = self.interpreter.model

    def proponer(
        self,
        query: str,
        idea: dict[str, Any],
        domain: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return self.interpreter.proponer(query, idea, domain, evidence).to_campos()

    def interpretar(self, query: str, idea: dict[str, Any]) -> dict[str, Any]:
        result = self.interpreter.proponer(query, idea)
        return {
            "labels": [],
            "score": None,
            "veredicto": result.to_campos()["estado"],
            "analisis": result.error,
            "protocolo_aplicado": protocolo_para(idea),
            "evaluation_status": "CRITIQUED" if result.es_propuesta else "NOT_EVALUATED",
            "provenance": result.provenance.sin_secretos() if result.provenance else {},
            "resultado": result.to_campos(),
        }


class CloudInterprete(LocalInterprete):
    """Alias explícito z.ai; la producción elige por seleccion.construir_interprete."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, base: str = ZAI_BASE) -> None:
        self.interpreter = OpenAICompatibleInterpreter(base_url=base, model=model, api_key=api_key)
        self.model = self.interpreter.model
