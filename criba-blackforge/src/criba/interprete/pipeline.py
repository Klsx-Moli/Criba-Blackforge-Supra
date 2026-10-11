"""Cableado del interprete-serendipia dentro del pipeline del engine.

Extrae de engine.activate() la capa P2 (bloque ``innovation.interprete``)
para que TODO lo relacionado con el interprete viva en este paquete:
prefilter, juez, adaptador, store, protocolo e IDs.

Contrato:
- Flag ``FEATURES["interprete_serendipia"]`` OFF -> ``{"applied": False}``
  sin tocar nada más (packet base intacto, golden master a salvo).
- ON -> interpreta el lote con IDs derivados de entrada completa, seed,
  modelos, backend y contrato. Sólo se reutilizan éxitos revalidados.
- Cualquier fallo del interprete NO rompe el pipeline: el bloque se
  degrada a ``{"applied": True, "error": "interprete_no_disponible"}``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from criba.constants import DEFAULT_DB, FEATURES
from criba.intelligence.evidence_context import retrieve_evidence_context
from criba.interprete.contrato import PROMPT_VERSION, SCHEMA_VERSION
from criba.interprete.ids import interprete_ids
from criba.interprete.juez import JuezInterprete
from criba.interprete.puerto import sin_secretos
from criba.storage import Storage

log = logging.getLogger(__name__)


def build_interprete_block(
    query: str,
    ideas: list[dict[str, Any]],
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Construye el bloque ``innovation.interprete`` del packet.

    ``context`` es el context dict del engine (seed, database, zai_api_key...).
    """
    if not FEATURES.get("interprete_serendipia"):
        return {"applied": False}

    ctx = context if isinstance(context, dict) else {}
    try:
        api_key = ctx.get("zai_api_key")
        storage = Storage(ctx.get("database", DEFAULT_DB)) if "database" in ctx else None
        juez = JuezInterprete(
            api_key=api_key,
            storage=storage,
            interpreter=ctx.get("interpreter"),
            backend=ctx.get("interpreter_backend"),
        )
        seed = ctx.get("seed")
        evidence_store = ctx.get("evidence_store")
        owns_evidence_store = "evidence_store" not in ctx
        if owns_evidence_store:
            from criba.intelligence.refresh import default_store

            evidence_store = default_store()
        try:
            snapshot = retrieve_evidence_context(query, evidence_store)
        finally:
            if owns_evidence_store and evidence_store is not None:
                evidence_store.close()
        evidence = snapshot["documents"]
        evidence_context = {key: value for key, value in snapshot.items() if key != "documents"}
        # PR-0: IDs deterministas — misma (query, seed, modelo) -> mismos IDs.
        modelo = str(getattr(juez.interpreter, "model", ""))
        scope = json.dumps(
            [
                juez.interpreter.backend,
                sin_secretos(str(getattr(juez.interpreter, "base", ""))),
                str(getattr(juez.interpreter, "critic_model", "")),
                PROMPT_VERSION,
                SCHEMA_VERSION,
                getattr(juez.interpreter, "generation_parameters", {}),
                snapshot,
                ideas,
            ],
            sort_keys=True,
            ensure_ascii=False,
        )
        ids = interprete_ids(query=query, seed=seed, modelo=modelo, repo=scope)
        interp_result = juez.interpretar_lote(
            query=query,
            ideas=ideas,
            activation_id=ids.activation_id,
            run_id=ids.run_id,
            seed=seed,
            evidence=evidence,
            evidence_context=evidence_context,
        )
        return {
            "applied": True,
            "modelo": interp_result["modelo"],
            "fallback_usado": interp_result["fallback_usado"],
            "evidence_delivered": evidence,
            "evidence_context": evidence_context,
            "interpretados": [
                {
                    "idea_id": r["id"],
                    "labels": r.get("interprete_labels", []),
                    "score": None,
                    "veredicto": r.get("interprete_verdict", "PENDIENTE"),
                    "dh": r.get("prefilter", {}).get("dh"),
                    "registro": r.get("_registro", {}).get("status"),
                    "evaluation_status": r.get("interprete_evaluation_status", "NOT_EVALUATED"),
                    "resultado": r.get("interprete_result", {}),
                    "provenance": r.get("interprete_provenance", {}),
                    "error": r.get("interprete_analisis", ""),
                }
                for r in interp_result["interpretados"]
            ],
            "prefiltrado_stats": interp_result["prefiltrado"]["stats"],
            "top_interprete": interp_result["interpretados"][0]
            if interp_result["interpretados"]
            else None,
        }
    except Exception as exc:
        tipo = type(exc).__name__
        log.error("interprete_no_disponible: %s", tipo)
        return {
            "applied": True,
            "error": "interprete_no_disponible",
            "error_type": tipo,
            "evaluation_status": "NOT_EVALUATED",
        }
