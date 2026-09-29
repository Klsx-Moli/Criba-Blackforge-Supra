"""``criba inventar``: el loop de innovación completo en un comando.

Cadena (siempre 0€, reproducible por semilla, nunca afirma novedad):

1. **Lotería estratificada** — divergencia determinista por clases de
   pensamiento (perspectiva/generación/ruptura/escape) con banco de dominio
   como segundo dado opcional.
2. **Propuesta** — el intérprete aplica el cruce al problema y devuelve
   hipótesis + mecanismo + aportación de cada técnica. Sin modelo disponible
   el estado queda ``PENDIENTE_INTERPRETACION``: no se fabrica contenido.
3. **Juez (crítica automática)** — ``LocalInterprete`` evalúa la propuesta;
   sin clave, scoring offline. Una llamada distinta no es validación
   independiente.
4. **Prior-art del mecanismo** — la búsqueda de antecedentes usa el
   MECANISMO interpretado (no el título del cruce). Sin mecanismo no hay
   búsqueda: ``UNRESOLVED`` honesto. Lattice determinista → par gratuito
   (Wikipedia + Google Patents) → skeptic → verdict → mutation loop
   fail-closed. Veredictos posibles: ``UNRESOLVED`` / ``PARTIAL_PRIOR_ART``
   / ``SURVIVED_SEARCH``.
5. **Ficha + ledger** — salida legible y ``invention_ledger/verdicts.jsonl``
   append-only con el registro completo por candidato.

Modo offline: bloquea TODA adquisición en el transporte común
(``Transport.offline``) y no construye fuentes de red.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .catalog import methods as catalog_methods
from .intelligence.contracts import InventionCandidate, SourceQueryResult
from .intelligence.prior_art.lattice import build_query_lattice
from .intelligence.prior_art.mutation_loop import run_prior_art_mutation_loop
from .intelligence.prior_art.protocol import AdversarialSearchProtocol
from .intelligence.prior_art.scouts import CrossDomainScout
from .intelligence.prior_art.skeptic import PriorArtSkeptic
from .intelligence.prior_art.verdict import PriorArtVerdictEngine
from .intelligence.sources import build_sources, default_context
from .intelligence.sources.protocol import IntelligenceSource
from .interprete.adaptador import LocalInterprete
from .lottery import LotteryEngine

_PROPOSER = Callable[..., dict[str, Any]]  # (query, idea, domain, evidence) -> dict

_PENDING: dict[str, Any] = {
    "estado": "PENDIENTE_INTERPRETACION",
    "hipotesis": "",
    "mecanismo": "",
    "aportacion_por_tecnica": [],
    "supuestos": [],
    "prueba_concreta": "",
    "error": "",
}


def _pending_proposal(error: str) -> dict[str, Any]:
    pending = dict(_PENDING)
    pending["error"] = error
    return pending


def _ledger_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base / "CRIBA-Blackforge" / "invention_ledger"


def _offline_mode(offline: bool | None) -> bool:
    if offline is not None:
        return offline
    return os.environ.get("CRIBA_INVENTAR_OFFLINE", "") == "1"


def _stable_run_id(query: str, seed: int) -> str:
    """Huella estable entre procesos: sha256 de semilla+consulta.

    Sustituye a ``hash()`` de Python (aleatorio entre procesos).
    """
    digest = hashlib.sha256(f"{seed}|{query}".encode("utf-8")).hexdigest()[:12]
    return f"invent-{seed}-{digest}"


def _default_proponer(
    query: str,
    idea: dict[str, Any],
    domain: dict[str, Any] | None,
    offline: bool = False,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Ruta real de propuesta. Con ``offline=True`` nunca toca la red.

    La comprobación vive AQUÍ y no solo dentro de ``LocalInterprete`` (cuyo
    estado depende de NOUS_API_KEY): el modo offline del comando debe bloquear
    la propuesta aunque haya credenciales configuradas. ``evidence`` (documentos
    locales pertinentes) se entrega al intérprete, no solo se archiva.
    """
    if offline:
        return _pending_proposal("modo offline")
    try:
        return LocalInterprete().proponer(query, idea, domain, evidence)
    except Exception as exc:  # noqa: BLE001 - la propuesta nunca rompe el loop
        return _pending_proposal(f"proposal_failed:{type(exc).__name__}")


def _judge(query: str, idea: dict[str, Any], offline: bool) -> dict[str, Any]:
    """Automatic critique; unavailable evaluation has no numeric score."""
    if offline:
        return {
            "veredicto": "PENDIENTE_OFFLINE", "labels": [], "score": None,
            "evaluation_status": "NOT_EVALUATED", "analisis": "",
        }
    try:
        result = LocalInterprete().interpretar(query, idea)
        if isinstance(result, dict):
            result.setdefault("evaluation_status", "EVALUATED")
        return result
    except Exception:  # noqa: BLE001 - el juez nunca rompe el loop
        return {
            "veredicto": "PENDIENTE_OFFLINE", "labels": [], "score": None,
            "evaluation_status": "NOT_EVALUATED", "analisis": "",
        }


def _assess_candidate(
    candidate: InventionCandidate,
    sources: list[IntelligenceSource],
) -> dict[str, Any]:
    """Lattice → scout (≥2 dominios) → skeptic → verdict → mutation loop.

    La búsqueda parte del MECANISMO. Sin mecanismo interpretado no hay
    búsqueda: ``UNRESOLVED`` con detalle honesto (no equivale a novedad).
    """
    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id,
        max_prior_art_rounds=2,
        max_mutations_per_candidate=1,
    )
    verdict_engine = PriorArtVerdictEngine()
    mechanism = (candidate.mechanism or "").strip()
    if not mechanism:
        return {
            "verdict": "UNRESOLVED",
            "queries": [],
            "rounds": 0,
            "mutations": 0,
            "detail": "sin-mecanismo: interpretación pendiente, no se buscó antecedente",
        }

    lattice = build_query_lattice(mechanism, max_variants=4)
    variant = lattice[0] if lattice else None
    if variant is None:
        return {
            "verdict": "UNRESOLVED",
            "queries": [],
            "rounds": 0,
            "mutations": 0,
            "detail": "lattice-vacío",
        }

    try:
        scout = CrossDomainScout(sources)
        results: dict[str, SourceQueryResult] = scout.cross_search(variant, limit_per_source=3)
    except ValueError as exc:
        return {
            "verdict": "UNRESOLVED",
            "queries": [],
            "rounds": 0,
            "mutations": 0,
            "detail": f"fuentes no utilizables: {exc}",
        }
    skeptic = PriorArtSkeptic()
    report = skeptic.review(candidate, results)
    assessment = verdict_engine.assess(candidate, results, report, matches=[])

    try:
        mutation = run_prior_art_mutation_loop(
            candidate=candidate,
            initial_assessment=assessment,
            protocol=protocol,
            scout=scout,
        )
        return {
            "verdict": mutation.verdict,
            "queries": list(mutation.queries_executed[:8]),
            "rounds": mutation.rounds_completed,
            "mutations": mutation.mutations_completed,
            "assessments": list(mutation.assessments_by_round),
            "detail": "",
        }
    except ValueError as exc:
        # Fail-closed del loop (UNRESOLVED inicial u otro contrato): el
        # veredicto de la evaluación directa es el resultado honesto.
        return {
            "verdict": assessment.verdict,
            "queries": list(assessment.queries_executed[:8]),
            "rounds": 0,
            "mutations": 0,
            "assessments": [assessment.verdict],
            "detail": f"mutation-loop-fail-closed: {exc}",
        }


def _estado_antecedentes(assessment: dict[str, Any]) -> str:
    """Estado honesto de antecedentes (mandato §7). Ninguno equivale a
    novedad universal; los errores no se convierten en «sin coincidencia»."""
    verdict = assessment.get("verdict")
    detail = str(assessment.get("detail") or "")
    queries = assessment.get("queries") or []
    if verdict == "PARTIAL_PRIOR_ART":
        return "antecedente_cercano_encontrado"
    if verdict == "SURVIVED_SEARCH":
        return "sin_coincidencia_cercana_en_fuentes_consultadas"
    if "sin-mecanismo" in detail or not queries:
        return "pendiente_de_busqueda"
    if detail.startswith("mutation-loop-fail-closed") or "error" in detail:
        return "busqueda_incompleta"
    return "busqueda_incompleta"


def _fts_query(query: str) -> str:
    """Consulta FTS tolerante: OR de tokens relevantes (el MATCH exacto de
    una frase completa exige TODOS los términos y casi nunca coincide)."""
    tokens = [t for t in query.split() if len(t) >= 4][:8]
    return " OR ".join(tokens) if tokens else query


def _filter_documented_evidence(
    documented: object,
    delivered: list[dict[str, Any]],
) -> list[Any]:
    """Keep only evidence references that can be resolved to delivered evidence.

    DOCUMENTED_AS_USED is a statement by the proposer, not proof of causal
    influence. It may only reference evidence actually delivered to that proposer.
    """
    if not isinstance(documented, list):
        return []
    valid_urls = {
        str(item.get("url") or "").strip()
        for item in delivered
        if isinstance(item, dict) and str(item.get("url") or "").strip()
    }
    valid_titles = {
        str(item.get("title") or "").strip()
        for item in delivered
        if isinstance(item, dict) and str(item.get("title") or "").strip()
    }
    out: list[Any] = []
    for item in documented:
        if isinstance(item, dict):
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or "").strip()
            if (url and url in valid_urls) or (title and title in valid_titles):
                out.append(item)
        elif isinstance(item, str):
            ref = item.strip()
            if ref and (ref in valid_urls or ref in valid_titles):
                out.append(item)
    return out


def invent(
    query: str,
    *,
    seed: int | None = None,
    rounds: int = 2,
    batch_size: int = 8,
    top: int = 3,
    offline: bool | None = None,
    methods: list[dict[str, Any]] | None = None,
    sources: list[IntelligenceSource] | None = None,
    proponer: _PROPOSER | None = None,
    store: Any | None = None,
    history_storage: Any = True,
    ficha_bloqueo: dict[str, Any] | None = None,
    adaptive: bool = False,
    outcome_store: Any | None = None,
    canon_version: str | None = None,
    execution_receipt_resolver: Callable[[str], dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Ejecuta el loop completo y devuelve la ficha de invención.

    ``methods``/``sources``/``proponer``/``store`` son inyectables para
    pruebas deterministas.

    ``adaptive`` controls OutcomeStore/UCB influence only. With an
    ``outcome_store`` present it weights the lottery and selector; adaptive
    does not disable ``history_storage``.
    ``history_storage=False`` is the explicit no-history reference policy for
    this component: it disables cooldown/history storage AND prior dossier
    lessons. External/provider state remains a separate dependency.

    Semilla (megaprompt §31-§33): ``seed=None`` genera una NUEVA semilla
    reproducible con ``secrets.randbits(64)`` (registra seed_source
    "generated"); una semilla explícita reproduce la exploración
    (seed_source "explicit"). Nunca timestamps ni ``hash()``.

    Historial (§35-§36): ``history_storage=True`` abre el Storage por
    defecto y aplica cooldown por decaimiento sobre pares usados (nunca
    prohibición permanente); ``False``/``None`` desactiva el historial;
    una instancia de Storage se usa tal cual. Los fallos de historial
    degradan a ejecución sin memoria (§ DV9).
    """
    if not query.strip():
        raise ValueError("query must not be blank")
    is_offline = _offline_mode(offline)
    proponer_fn = proponer or (lambda q, i, d, ev=None: _default_proponer(q, i, d, is_offline, ev))

    import secrets
    import uuid

    if seed is None:
        seed = secrets.randbits(64)
        seed_source = "generated"
    else:
        seed_source = "explicit"
    run_id = uuid.uuid4().hex  # identidad de ejecución independiente de la seed

    history = None
    first_seen: dict[tuple[str, str], str] | None = None
    if history_storage is True:
        try:
            from .storage import Storage

            history = Storage()
        except Exception:  # noqa: BLE001 — DV9: sin historial el motor funciona
            history = None
    elif history_storage:
        history = history_storage
    if history is not None:
        try:
            import hashlib as _hashlib

            ids = sorted(str(m["id"]) for m in (methods or catalog_methods()))
            fingerprint = _hashlib.sha256(",".join(ids).encode("utf-8")).hexdigest()
            first_seen = history.load_combination_first_seen(fingerprint)
        except Exception:  # noqa: BLE001 — degradación elegante (DV9)
            first_seen = None

    active_outcome_store = outcome_store if adaptive else None
    engine = LotteryEngine.from_methods(
        methods or catalog_methods(),
        seed=seed,
        outcome_store=active_outcome_store,
        outcome_profile="CRIBA",
        outcome_canon_version=canon_version,
    )
    for _ in range(rounds):
        engine.run_round(mode="stratified", batch_size=batch_size, query=query)
    domain = engine.draw_domain()
    # Selección finalista diversity-aware (megaprompt §24-§28): pool de alta
    # calidad → selector MMR → finalistas. get_top_ideas sigue existiendo
    # para sus otros consumidores; el flujo de invención ya no depende solo
    # del top-N por score.
    from .diversity_selector import select_finalists

    pool = engine.get_top_ideas(max(top * 6, 12))
    top_ideas, selection_report = select_finalists(
        pool,
        top,
        historical_first_seen=first_seen,
        outcome_store=active_outcome_store,
        outcome_profile="CRIBA",
        outcome_canon_version=canon_version,
    )
    selection_report["initial_candidate_pool"] = [
        {
            "idea_id": idea.get("idea_id", ""),
            "title": idea.get("title", ""),
            "score": idea.get("score", 0.0),
            "method_ids": [idea.get("method1_id", ""), idea.get("method2_id", "")],
        }
        for idea in pool
    ]
    selection_report["initial_finalists"] = [idea.get("idea_id", "") for idea in top_ideas]
    if history is not None and selection_report.get("pool_size"):
        try:  # registrar los pares de ESTA ejecución (first_seen=ahora)
            history.save_lottery_combinations(
                engine.catalog_fingerprint,
                sorted(engine.used_combos),
                run_id=run_id,
                mode="stratified",
                seed=seed,
            )
        except Exception:  # noqa: BLE001 — DV9: persistencia opcional
            pass

    # Offline: sin fuentes de red. El transporte común también bloquea
    # cualquier intento de conexión que escape (defensa en profundidad).
    if sources is not None:
        active_sources = sources
    elif is_offline:
        active_sources = []
    else:
        active_sources = build_sources(default_context(offline=is_offline))
    candidate_prefix = _stable_run_id(query, seed)  # reproducible por seed

    # Evidencia local para el intérprete (FTS del almacén): se RECUPERA UNA
    # VEZ y se ENTREGA a la llamada de interpretación — no solo se guarda.
    local_evidence: list[dict[str, Any]] = []
    if store is not None:
        try:
            local_evidence = [
                {"title": d.get("title", ""), "abstract": (d.get("abstract") or "")[:300],
                 "url": d.get("url", "")}
                for d in (store.search_documents(_fts_query(query), limit=3) or [])
            ]
        except Exception:  # noqa: BLE001 — la evidencia nunca rompe el loop
            local_evidence = []

    # Lecciones de dossiers previos (circuito de aprendizaje, astra!.txt §5):
    # un resultado observado vuelve a la búsqueda como evidencia trazable.
    lecciones: list[str] = []
    history_channels_enabled = history_storage is not False and history_storage is not None
    if ficha_bloqueo and history_channels_enabled:
        try:
            from .supra_dossier import lecciones_previas
            lecciones = lecciones_previas(
                query, execution_resolver=execution_receipt_resolver
            )
        except Exception:  # noqa: BLE001 — el aprendizaje nunca rompe el loop
            lecciones = []

    def _desarrollar(idea: dict[str, Any], index: int) -> dict[str, Any]:
        """Propuesta → crítica → antecedentes para un candidato del pool."""
        idea_enviada = idea
        if ficha_bloqueo:
            idea_enviada = {**idea, "bloqueo": {
                **ficha_bloqueo, "lecciones_previas": lecciones}}
        # 1) Propuesta: aplicar el cruce al problema (con evidencia) ANTES de
        #    buscar antecedentes.
        proposal = proponer_fn(query, idea_enviada, domain, local_evidence)
        documented_raw = proposal.get("evidence_documented_as_used", [])
        documented_evidence = _filter_documented_evidence(documented_raw, local_evidence)
        documented_rejected = (
            len(documented_raw) - len(documented_evidence)
            if isinstance(documented_raw, list)
            else 0
        )
        if proposal.get("estado") != "PROPUESTA" or not str(proposal.get("mecanismo", "")).strip():
            if proposal.get("estado") == "PROPUESTA":
                proposal = _pending_proposal("PROPUESTA sin mecanismo")
        candidate = InventionCandidate(
            candidate_id=f"{candidate_prefix}-{index + 1:02d}",
            title=str(idea.get("title", ""))[:120],
            description=str(idea.get("description", ""))[:400],
            mechanism=str(proposal.get("mecanismo", "")),
            origin="NEW_IIE",
        )
        # 2) Crítica automática sobre la propuesta (no validación independiente).
        judged = _judge(query, {**idea, "mecanismo": candidate.mechanism}, is_offline)
        # 3) Antecedentes del mecanismo (nunca del título).
        assessment = _assess_candidate(candidate, active_sources)
        return {
            "candidate_id": candidate.candidate_id,
            "run_id": run_id,  # cada entry arrastra su ejecución (trazabilidad dossier)
            "title": candidate.title,
            "score": idea.get("score", 0.0),
            "score_kind": "heuristica_local",
            "classes": [idea.get("class1", ""), idea.get("class2", "")],
            "methods": [idea.get("method1", ""), idea.get("method2", "")],
            "method_ids": [idea.get("method1_id", ""), idea.get("method2_id", "")],
            "hipotesis": proposal.get("hipotesis", ""),
            "mecanismo": candidate.mechanism,
            "estado_interpretacion": proposal.get("estado", "PENDIENTE_INTERPRETACION"),
            "aportacion_por_tecnica": list(proposal.get("aportacion_por_tecnica", [])),
            "supuestos": list(proposal.get("supuestos", [])),
            "prueba_concreta": proposal.get("prueba_concreta", ""),
            "ruta_desbloqueo": proposal.get("ruta_desbloqueo", ""),
            "interpretacion_error": proposal.get("error", ""),
            "evidence_retrieved": local_evidence,
            "evidence_delivered": local_evidence,
            "evidence_documented_as_used": documented_evidence,
            "evidence_documented_rejected_count": documented_rejected,
            # Deprecated read-compatible alias. Historically this meant only
            # retrieved+delivered, never demonstrated causal use.
            "evidencia_local_usada": local_evidence,
            "evidencia_local_usada_semantics": "DEPRECATED_ALIAS_FOR_EVIDENCE_DELIVERED",
            "judge": judged,
            "prior_art": assessment,
            "estado_antecedentes": _estado_antecedentes(assessment),
        }

    entries: list[dict[str, Any]] = [
        _desarrollar(idea, i) for i, idea in enumerate(top_ideas)
    ]

    # 4) Revisión post-interpretación (mandato §22: una revisión por candidato;
    # megaprompt §28): el selector eligió finalistas sobre estructura/técnicas
    # porque interpretar TODO el pool no cabe en presupuesto. Una vez
    # interpretados los mecanismos, si dos son la MISMA idea, el redundante
    # se sustituye por el siguiente candidato del pool. Cada intento
    # (aceptado o rechazado) se registra con identidad y llamadas consumidas;
    # UNKNOWN no descarta automáticamente (mandato de verificación §2).
    from .diversity_selector import compare_mechanisms

    pool_rest = [c for c in pool if all(c is not t for t in top_ideas)]
    intentos: list[dict[str, Any]] = []
    model_calls = len(entries)  # cada finalista interpretado = 1 llamada
    for idx, entry in enumerate(entries):
        if entry["estado_interpretacion"] != "PROPUESTA" or not entry["mecanismo"]:
            continue
        duplicated_with = next(
            (other["mecanismo"] for j, other in enumerate(entries)
             if j != idx and other["estado_interpretacion"] == "PROPUESTA"
             and other["mecanismo"]
             and compare_mechanisms(entry["mecanismo"], other["mecanismo"]) == "DUPLICATE"),
            None,
        )
        if duplicated_with is None:
            continue
        if not pool_rest:
            intentos.append({
                "reemplazado_id": entry["candidate_id"],
                "reemplazado_titulo": entry["title"],
                "motivo": "mecanismo duplicado; pool sin sustituto disponible",
                "resultado": "rechazado",
                "sustituto_id": None,
                "llamadas_modelo": 0,
            })
            entry["mecanismo_duplicado_con"] = "otro finalista (sin sustituto en el pool)"
            continue
        sustituto_idea = pool_rest.pop(0)
        sustituto_entry = _desarrollar(sustituto_idea, len(entries) + len(intentos))
        model_calls += 1  # el sustituto consume su propia llamada de propuesta
        distinto_de_todos = all(
            compare_mechanisms(sustituto_entry["mecanismo"], other["mecanismo"]) != "DUPLICATE"
            for j, other in enumerate(entries)
            if j != idx and other["estado_interpretacion"] == "PROPUESTA"
            and other["mecanismo"]
        )
        if (sustituto_entry["estado_interpretacion"] == "PROPUESTA"
                and sustituto_entry["mecanismo"] and distinto_de_todos):
            intentos.append({
                "reemplazado_id": entry["candidate_id"],
                "reemplazado_titulo": entry["title"],
                "motivo": "mecanismo interpretado duplicado con otro finalista",
                "resultado": "aceptado",
                "sustituto_id": sustituto_entry["candidate_id"],
                "sustituto_titulo": sustituto_entry["title"],
                "llamadas_modelo": 1,
            })
            entries[idx] = sustituto_entry
        else:
            motivo = "sustituto sin propuesta válida o aún duplicado"
            if sustituto_entry["estado_interpretacion"] == "PROPUESTA" and sustituto_entry["mecanismo"]:
                motivo = "sustituto aún duplicado o incomparable (UNKNOWN no descarta)"
            intentos.append({
                "reemplazado_id": entry["candidate_id"],
                "reemplazado_titulo": entry["title"],
                "motivo": motivo,
                "resultado": "rechazado",
                "sustituto_id": sustituto_entry["candidate_id"],
                "sustituto_titulo": sustituto_entry["title"],
                "llamadas_modelo": 1,
            })
            entry["mecanismo_duplicado_con"] = "otro finalista (sustitución rechazada)"
    selection_report["revision_post_interpretacion"] = {
        "intentos": intentos,
        "llamadas_revision": len(intentos),
        "candidate_development_attempts": model_calls,
        # Compatibility field: historically misnamed as model calls. It is not
        # authoritative request accounting because proposal/judge/provider
        # boundaries are not fully instrumented here.
        "llamadas_modelo_total": model_calls,
        "model_requests": None,
        "model_requests_authoritative": False,
        "sustituciones_aceptadas": sum(1 for i in intentos if i["resultado"] == "aceptado"),
    }
    selection_report["opportunity_accounting"] = {
        "generated_candidates": len(engine.all_ideas),
        "selection_candidates_considered": len(pool),
        "initial_finalists": len(top_ideas),
        "candidate_development_attempts": model_calls,
        "replacement_attempts": len(intentos),
        "finalists": len(entries),
        "provider_model_requests": None,
        "provider_model_requests_authoritative": False,
        "evaluation_calls_authoritative": False,
        "budget_complete": False,
        "scope": "LOCAL_PIPELINE_ACCOUNTING_ONLY",
    }
    selection_report["finalists"] = [entry["candidate_id"] for entry in entries]

    outcome_store_hash: str | None = None
    if active_outcome_store is not None and hasattr(active_outcome_store, "state_hash"):
        try:
            outcome_store_hash = str(active_outcome_store.state_hash())
        except Exception:  # noqa: BLE001
            outcome_store_hash = None
    reproducibility_dependencies = {
        "closure_complete": False,
        "seed": seed,
        "seed_source": seed_source,
        "rounds": rounds,
        "batch_size": batch_size,
        "canon_version": canon_version,
        "catalog_fingerprint": getattr(engine, "catalog_fingerprint", None),
        "outcome_store_hash": outcome_store_hash,
        "offline": is_offline,
        "history_storage_enabled": history is not None,
        "dossier_lessons_enabled": bool(ficha_bloqueo and history_channels_enabled),
        "known_unclosed_dependencies": [
            "code_version",
            "provider_model_and_config_when_used",
            "external_source_state_when_online",
            "environment_configuration",
        ],
    }

    sheet = {
        "query": query,
        "seed": seed,
        "seed_source": seed_source,
        "run_id": run_id,
        "mode": "stratified",
        "rounds": rounds,
        "reproducibility_dependencies": reproducibility_dependencies,
        "adaptation": {
            "enabled": bool(adaptive and active_outcome_store is not None),
            "policy": "outcome_store_ucb",
            "scope": "OUTCOME_STORE_ONLY",
            "history_storage_enabled": history is not None,
            "dossier_lessons_enabled": bool(ficha_bloqueo and history_channels_enabled),
            "fallback": "continue_without_outcome_prior",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "domain_coupling": {
            "id": domain.get("id") if domain else None,
            "title": domain.get("title") if domain else None,
            "usado_en_interpretacion": True,
        },
        "seleccion_finalista": selection_report,
        "ficha_bloqueo": dict(ficha_bloqueo) if ficha_bloqueo else None,
        "entries": entries,
        "totals": {
            "ideas": len(engine.all_ideas),
            "pending_interpretation": sum(
                1 for e in entries if e["estado_interpretacion"] != "PROPUESTA"
            ),
            "unresolved": sum(1 for e in entries if e["prior_art"]["verdict"] == "UNRESOLVED"),
            "partial_prior_art": sum(1 for e in entries if e["prior_art"]["verdict"] == "PARTIAL_PRIOR_ART"),
            "survived_search": sum(1 for e in entries if e["prior_art"]["verdict"] == "SURVIVED_SEARCH"),
        },
    }
    return sheet


def _entry_technique_ids(entry: dict[str, Any]) -> list[str]:
    """IDs T0xx que aportaron a un candidato (aportacion_por_tecnica).

    Forma tolerante: acepta dicts con 'tecnica'/'id'/'technique_id' o strings
    planos. Devuelve IDs únicos normalizados a mayúsculas; nunca inventa IDs.
    """
    out: list[str] = []
    for item in entry.get("aportacion_por_tecnica") or []:
        tid = ""
        if isinstance(item, dict):
            tid = str(item.get("tecnica") or item.get("id") or item.get("technique_id") or "")
        elif isinstance(item, str):
            tid = item
        tid = tid.strip().upper()
        if tid.startswith("T") and tid not in out:
            out.append(tid)
    return out


def record_outcomes(
    sheet: dict[str, Any],
    store: Any,
    *,
    profile: str = "CRIBA",
    canon_version: str = "",
) -> int:
    """Persist operational outcome channels only when attribution is identifiable.

    VERDICT (prior-art) and JUDGE (automatic critique) remain separately tagged.
    A candidate-level result is written to a technique only when one unique
    technique/family attribution is identifiable. Family back-off is written
    only for one identifiable family. Multi-component participation alone is
    not individual causal credit.

    Stable run_id controls learning eligibility in OutcomeStore. Memory is
    optional operational adaptation, not scientific validation, and never
    breaks the invention loop.
    """
    from .intelligence.outcome_store import CHANNEL_JUDGE, CHANNEL_VERDICT

    written = 0
    for entry in sheet.get("entries", []):
        verdict = entry.get("prior_art", {}).get("verdict", "UNRESOLVED")
        if verdict not in ("SURVIVED_SEARCH", "PARTIAL_PRIOR_ART", "UNRESOLVED"):
            verdict = "UNRESOLVED"
        judge = entry.get("judge", {})
        judge_score = judge.get("score")
        judge_status = str(judge.get("evaluation_status") or "").upper()
        judge_verdict = str(judge.get("veredicto") or "").upper()
        judge_evaluated = (
            isinstance(judge_score, (int, float))
            and judge_status == "EVALUATED"
            and not judge_verdict.startswith("PENDIENTE")
        )
        run_id = entry.get("run_id", sheet.get("run_id", ""))

        # ASTRA-022 credit assignment: a candidate-level outcome is not
        # automatically independent evidence for every component that
        # participated in a combination. Fine-grained learning is allowed only
        # when one unique technique/family attribution is identifiable.
        method_ids = [str(m).strip() for m in (entry.get("method_ids") or []) if str(m).strip()]
        classes = [str(c).strip() for c in (entry.get("classes") or []) if str(c).strip()]
        pairs = list(dict.fromkeys(zip(method_ids, classes))) if method_ids else []
        t_ids = _entry_technique_ids(entry)
        if t_ids and len(set(classes)) == 1:
            family_t = classes[0]
            pairs.extend((tid, family_t) for tid in t_ids)
        pairs = list(dict.fromkeys(pairs))

        def _escribe(tid: str, familia: str) -> None:
            nonlocal written
            try:
                store.record(
                    profile=profile, family=familia, technique_id=tid,
                    channel=CHANNEL_VERDICT, outcome=verdict,
                    canon_version=canon_version, run_id=run_id,
                )
                written += 1
                if judge_evaluated:
                    store.record(
                        profile=profile, family=familia, technique_id=tid,
                        channel=CHANNEL_JUDGE, outcome="score",
                        value=float(judge_score),
                        canon_version=canon_version, run_id=run_id,
                    )
                    written += 1
            except Exception:  # noqa: BLE001 — la memoria nunca rompe el loop
                return

        if len(pairs) == 1:
            _escribe(*pairs[0])

        # Family back-off is likewise written only when one family attribution
        # is identifiable. Multi-family candidate outcomes stay in the ledger
        # but do not masquerade as independent family evidence.
        unique_classes = list(dict.fromkeys(classes))
        if len(unique_classes) == 1:
            try:
                store.record_family_outcome(
                    profile=profile,
                    family=unique_classes[0],
                    channel=CHANNEL_VERDICT,
                    outcome=verdict,
                    canon_version=canon_version,
                    run_id=run_id,
                )
                written += 1
            except Exception:  # noqa: BLE001
                pass
    return written


def append_ledger(sheet: dict[str, Any], ledger_dir: Path | None = None) -> Path:
    """Append an auditable invention and selection record to the JSONL ledger."""
    directory = ledger_dir or _ledger_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "verdicts.jsonl"
    selection = sheet.get("seleccion_finalista") or {}
    revision = selection.get("revision_post_interpretacion") or {}
    selection_audit = {
        "initial_candidate_pool": list(selection.get("initial_candidate_pool") or []),
        "initial_finalists": list(selection.get("initial_finalists") or []),
        "selection_report": selection,
        "replacement_attempts": list(revision.get("intentos") or []),
        "final_finalists": list(selection.get("finalists") or []),
        "blocking_sheet": sheet.get("ficha_bloqueo"),
        "call_accounting": {
            "candidate_development_attempts": revision.get("candidate_development_attempts"),
            "model_requests": revision.get("model_requests"),
            "model_requests_authoritative": bool(
                revision.get("model_requests_authoritative", False)
            ),
        },
        "opportunity_accounting": dict(selection.get("opportunity_accounting") or {
            "budget_complete": False,
            "scope": "LEGACY_OR_UNINSTRUMENTED",
        }),
    }
    record = {
        "generated_at": sheet["generated_at"],
        "query": sheet["query"],
        "seed": sheet["seed"],
        "seed_source": sheet["seed_source"],
        "run_id": sheet["run_id"],
        "mode": sheet["mode"],
        "rounds": sheet["rounds"],
        "reproducibility_dependencies": sheet.get(
            "reproducibility_dependencies",
            {
                "closure_complete": False,
                "known_unclosed_dependencies": ["legacy_record_missing_dependency_closure"],
            },
        ),
        "adaptation": sheet.get("adaptation", {
            "enabled": False,
            "policy": "legacy_unspecified",
            "scope": "UNKNOWN",
            "history_storage_enabled": None,
            "fallback": "legacy_unspecified",
        }),
        "domain_coupling": sheet["domain_coupling"],
        "totals": sheet["totals"],
        "selection_audit": selection_audit,
        "entries": [
            {
                "candidate_id": e["candidate_id"],
                "run_id": e["run_id"],
                "title": e["title"],
                "estado_interpretacion": e["estado_interpretacion"],
                "mecanismo": e["mecanismo"],
                "score": e["score"],
                "score_kind": e["score_kind"],
                "classes": e["classes"],
                "methods": e["methods"],
                "technique_ids": _entry_technique_ids(e),  # §4.1: qué T0xx aportó
                "hipotesis": e["hipotesis"],
                "prueba_concreta": e["prueba_concreta"],
                "ruta_desbloqueo": e["ruta_desbloqueo"],
                "supuestos": e["supuestos"],
                "estado_antecedentes": e["estado_antecedentes"],
                "evidence_retrieved": list(
                    e.get("evidence_retrieved", e.get("evidencia_local_usada", []))
                ),
                "evidence_delivered": list(
                    e.get("evidence_delivered", e.get("evidencia_local_usada", []))
                ),
                "evidence_documented_as_used": list(e.get("evidence_documented_as_used", [])),
                "evidencia_local_usada": list(e.get("evidencia_local_usada", [])),
                "evidencia_local_usada_semantics": "DEPRECATED_ALIAS_FOR_EVIDENCE_DELIVERED",
                "verdict": e["prior_art"]["verdict"],
                "queries": e["prior_art"]["queries"],
                "detail": e["prior_art"]["detail"],
            }
            for e in sheet["entries"]
        ],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def print_sheet(sheet: dict[str, Any]) -> None:
    """Imprime la ficha de invención en consola."""
    line = "=" * 64
    print(line)
    print(f"INVENTAR · {sheet['query'][:50]} · seed={sheet['seed']} · {sheet['mode']}")
    print(line)
    domain = sheet.get("domain_coupling") or {}
    if domain.get("title"):
        print(f"Dominio de acoplamiento: {domain['title']}")
    for i, entry in enumerate(sheet["entries"], 1):
        prior = entry["prior_art"]
        judge = entry["judge"]
        print()
        print(f"{i}. {entry['title']}")
        print(f"   clases: {' x '.join(c or '?' for c in entry['classes'])} | score {entry['score']} ({entry['score_kind']})")
        print(f"   interpretación: {entry['estado_interpretacion']}")
        if entry["hipotesis"]:
            print(f"   hipótesis: {entry['hipotesis'][:200]}")
            print(f"   mecanismo: {entry['mecanismo'][:200]}")
            print(f"   prueba: {entry['prueba_concreta'][:200]}")
        print(f"   juez: {judge.get('veredicto', '?')} ({judge.get('score', 'N/A')})")
        print(f"   prior-art: {prior['verdict']} (rondas={prior['rounds']}, mutaciones={prior['mutations']})")
    totals = sheet["totals"]
    print()
    print(line)
    print(
        f"Ideas: {totals['ideas']} | pendientes: {totals['pending_interpretation']} | "
        f"UNRESOLVED: {totals['unresolved']} | "
        f"PARTIAL: {totals['partial_prior_art']} | SURVIVED: {totals['survived_search']}"
    )
    print(line)
