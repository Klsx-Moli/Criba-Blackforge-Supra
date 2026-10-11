"""Prefiltrado, puerto único y registro. Conserva el orden; no asigna scores."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .contrato import SYSTEM, evidencia_entregada, prompt_propuesta
from .prefilter import PreFilter
from .puerto import InterpreterPort, hash_salida
from .seleccion import construir_interprete
from .store import InterpreteStore

if TYPE_CHECKING:
    from criba.storage import Storage


class JuezInterprete:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "glm-5.3-flash",
        storage: Storage | None = None,
        *,
        interpreter: InterpreterPort | None = None,
        backend: str | None = None,
    ) -> None:
        self.interpreter = interpreter or construir_interprete(backend)
        self.prefilter = PreFilter(top_n=12, strict=True)
        self.store = InterpreteStore(storage) if storage is not None else None

    def interpretar_lote(
        self,
        query: str,
        ideas: list[dict[str, Any]],
        activation_id: str,
        run_id: str,
        seed: int | None = None,
        *,
        evidence: list[dict[str, Any]] | None = None,
        evidence_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        evidence = evidencia_entregada(evidence)
        prefiltrado = self.prefilter.apply(ideas)
        resultados = []
        modelo = str(getattr(self.interpreter, "model", ""))
        for original in prefiltrado["candidates"]:
            idea = dict(original)
            if evidence_context is not None:
                idea["evidence_context"] = evidence_context
            previo = (
                self.store.get_verdict(idea["id"], modelo, run_id=run_id, seed=seed)
                if self.store
                else None
            )
            if (
                previo
                and InterpreteStore.cache_valido(previo, idea, evidence)
                and previo["provenance"].get("generation_parameters", {})
                == getattr(self.interpreter, "generation_parameters", {})
                and previo["provenance"].get("prompt_sha256")
                == hash_salida(SYSTEM + prompt_propuesta(query, idea, None, evidence))
            ):
                idea.update(previo["response"]["interpretation"])
                idea["_registro"] = {"status": "deduplicated"}
            else:
                result = self.interpreter.proponer(query, idea, evidence=evidence)
                campos = result.to_campos()
                status = "CRITIQUED" if result.es_propuesta else "NOT_EVALUATED"
                idea.update(
                    {
                        "interprete_labels": [],
                        "interprete_score": None,
                        "interprete_verdict": campos["estado"],
                        "interprete_analisis": result.error,
                        "interprete_evaluation_status": status,
                        "interprete_result": campos,
                        "interprete_provenance": result.provenance.sin_secretos()
                        if result.provenance
                        else {},
                        "interprete_raw_output": result.raw_output,
                        "interprete_evidence_delivered": evidence or [],
                    }
                )
                idea["_registro"] = (
                    self.store.record_decision(
                        activation_id=activation_id,
                        idea=idea,
                        modelo=modelo,
                        run_id=run_id,
                        seed=seed,
                    )
                    if self.store
                    else {"status": "unregistered", "reason": "no storage"}
                )
                if self.store and idea["_registro"]["status"] == "deduplicated":
                    # A concurrent writer may have won after our initial read.
                    elegido = self.store.get_verdict(idea["id"], modelo, run_id=run_id, seed=seed)
                    if elegido is not None:
                        idea.update(elegido["response"]["interpretation"])
            resultados.append(idea)
        return {
            "query": query,
            "activation_id": activation_id,
            "total_ideas_entrada": len(ideas),
            "prefiltrado": prefiltrado,
            "interpretados": resultados,
            "modelo": modelo,
            "fallback_usado": False,
        }
