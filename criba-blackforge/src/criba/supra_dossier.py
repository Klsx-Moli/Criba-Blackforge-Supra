"""Dossier de avance tipo SUPRA (astra!.txt paso 4) — sin ejecutar SUPRA.

Contrato de exportación versionado: un candidato seleccionado se convierte en
un dossier con PRUEBA DISCRIMINANTE — la observación que haría abandonar la
propuesta o cambiar su mecanismo ANTES de construir un prototipo costoso.

Regla de honestidad (megaprompt §7, SUPRA): sin experimento ejecutado el
estado es ``SUPRA_EJECUCION_PENDIENTE`` — NUNCA PASS. El resultado observado
se registra aparte y alimenta ``lecciones_previas`` (paso 5: aprendizaje sobre
mecanismos y condiciones), cerrando el circuito con trazabilidad.
"""
from __future__ import annotations

import hashlib
import json
import os
import warnings
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeGuard
from uuid import uuid4

DOSSIER_RESULT_SEMANTICS_VERSION = 3


def _exact_identity_text(value: object) -> TypeGuard[str]:
    """Identity text is exact authority; never coerce or trim it implicitly."""
    return isinstance(value, str) and bool(value) and value == value.strip()


def _text(source: dict[str, Any], key: str, limit: int = 400) -> str:
    """Read one declared field as bounded text, or fail loudly.

    A missing source field is UNKNOWN, and UNKNOWN is never a placeholder.
    Callers use this so a dossier cannot be completed with invented content.
    """
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"dossier source field is missing: {key}")
    return value.strip()[:limit]


def _axis_moves(idea: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Parse the engine's declared ``difference_signature`` into axis moves.

    Measured format: ``(eje:antes→después|eje2:antes2→después2)``. These are the
    concrete before/after pairs the engine claims the cross mutates; they are
    what an observation has to show to discriminate the mechanism from the
    rival explanation. An unparsable signature is an error, never a guess.
    """
    signature = _text(idea, "difference_signature", 600)
    moves: list[tuple[str, str, str]] = []
    for part in signature.strip("()").split("|"):
        chunk = part.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise ValueError(f"difference_signature axis has no before/after: {chunk}")
        axis, _, values = chunk.partition(":")
        before, arrow, after = values.partition("→")
        if not arrow or not before.strip() or not after.strip():
            raise ValueError(f"difference_signature axis is not a move: {chunk}")
        moves.append((axis.strip(), before.strip(), after.strip()))
    if not moves:
        raise ValueError("difference_signature declares no axis move")
    return moves


def _movements_text(moves: list[tuple[str, str, str]]) -> str:
    return "; ".join(f"{axis}: {before} → {after}" for axis, before, after in moves)


def _entry_desde_idea(idea: dict[str, Any], problema: str) -> dict[str, Any]:
    """Build the dossier entry from a REAL deterministic CRIBA idea.

    Measured against ``criba.engine.activate`` on 2026-10-02: every field this
    reads is present on 295/295 ideas across three problems, and every field
    below has exactly one declared source. Nothing is invented and nothing is
    defaulted, because SUPRA's validated schema requires all eight protocol
    obligations to be non-empty and a filler string would convert a missing
    declaration into a declared one.

    The epistemology is preserved end to end: the engine marks its own output
    ``MECHANISM_PROPOSED_UNVALIDATED``, the dossier keeps
    ``SUPRA_EJECUCION_PENDIENTE`` and the protocol keeps ``NO_EJECUTADA``. What
    this function adds is a *declared, falsifiable* test — never a result.
    """
    moves = _axis_moves(idea)
    causal_variables = idea.get("causal_variables")
    if not isinstance(causal_variables, dict):
        raise ValueError("idea has no causal_variables")
    evidencia = causal_variables.get("evidencia_requerida")
    if not isinstance(evidencia, str) or not evidencia.strip():
        raise ValueError("idea has no causal_variables.evidencia_requerida")
    si_falla = causal_variables.get("si_falla")
    if not isinstance(si_falla, str) or not si_falla.strip():
        raise ValueError("idea has no causal_variables.si_falla")

    # H1 is what the engine claims; H2 is the assumption it says the mechanism
    # breaks, which is precisely the explanation that must be discriminated.
    hipotesis = _text(idea, "expected_effect", 800)
    alternativa = _text(idea, "broken_assumption", 1200)
    firma = _movements_text(moves)

    return {
        "candidate_id": _text(idea, "id", 256),
        "claim_id": None,
        "hipotesis": hipotesis,
        "mecanismo": _text(idea, "mechanism_causal", 2000),
        "prueba_concreta": _text(idea, "mechanism_explanation", 600),
        "observable": (
            f"los ejes declarados cambian de valor: {firma} "
            f"(evidencia requerida: {evidencia.strip()})"
        ),
        "alternativa_explicativa": alternativa,
        "resultado_favorable_mecanismo": (
            f"los ejes {firma} adoptan el valor 'después' y el efecto declarado "
            f"se observa: {hipotesis}"
        ),
        "resultado_favorable_alternativa": (
            f"los ejes permanecen en 'antes' y el supuesto se sostiene sin cambio: "
            f"{alternativa}"
        ),
        "regla_decision": (
            f"adoptar el mecanismo solo si el observable confirma {firma}; "
            f"si los ejes no cambian, la explicación alternativa gana y el "
            f"mecanismo se descarta"
        ),
        "condicion_fracaso": (
            f"eje sin el movimiento declarado, o fallo observado como "
            f"{si_falla.strip()[:200]}"
        ),
        "evidencia_requerida": evidencia.strip()[:400],
        "supuestos": [
            str(idea.get("rupture") or "").strip(),
            str(idea.get("known_space_element") or "").strip(),
        ],
        "causal_claim": str(idea.get("causal_claim") or "").strip(),
    }


def preparar_dossier_desde_idea(
    idea: dict[str, Any],
    problema: str,
    *,
    ficha_bloqueo: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dossier with a complete discriminant protocol from a core idea.

    ``preparar_dossier`` is the assembler and stays the single place that
    computes versions and identity; this only supplies the entry that a real
    deterministic idea can actually support, so the resulting dossier is
    accepted by SUPRA's validated schema without any field being filled with a
    placeholder.
    """
    entry = _entry_desde_idea(idea, problema)
    return preparar_dossier(
        entry,
        problema,
        ficha_bloqueo=ficha_bloqueo,
        alternativa_explicativa=entry["alternativa_explicativa"],
    )


def _dossiers_dir(override: Path | None = None) -> Path:
    if override is not None:
        return override
    shadow_home = os.environ.get("CRIBASHADOW_HOME")
    if shadow_home:
        return Path(shadow_home) / "dossiers"
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "CRIBA-Blackforge"
    return base / "dossiers"


def _contexto(dossier: dict[str, Any]) -> dict[str, Any]:
    """La fecha de reexportación no cambia el contenido del experimento."""
    return {k: v for k, v in dossier.items() if k not in ("creado_at", "dossier_id")}


def _leer_historial(
    path: Path,
) -> tuple[dict[str, dict[str, Any]], set[str], list[dict[str, Any]]]:
    dossiers: dict[str, dict[str, Any]] = {}
    ambiguos: set[str] = set()
    resultados: list[dict[str, Any]] = []
    if not path.exists():
        return dossiers, ambiguos, resultados
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        identity = rec.get("dossier_id")
        if not isinstance(identity, str) or not identity.strip():
            continue
        if rec.get("tipo") == "resultado_observado":
            resultados.append(rec)
            continue
        if identity in dossiers and _contexto(dossiers[identity]) != _contexto(rec):
            ambiguos.add(identity)
        else:
            dossiers.setdefault(identity, rec)
    return dossiers, ambiguos, resultados


def preparar_dossier(
    entry: dict[str, Any],
    problema: str,
    *,
    ficha_bloqueo: dict[str, Any] | None = None,
    alternativa_explicativa: str = "",
) -> dict[str, Any]:
    """Dossier con prueba discriminante para un candidato PROPUESTA.

    ``alternativa_explicativa``: la otra explicación que la observación debe
    distinguir. Si no se aporta, el dossier lo declara en lugar de inventarla.
    """
    bloqueo = ficha_bloqueo or {}
    raw_prueba = entry.get("prueba")
    declarada: dict[str, Any] = raw_prueba if isinstance(raw_prueba, dict) else {}
    prueba_concreta = str(entry.get("prueba_concreta", ""))[:600]
    claim = str(entry.get("hipotesis", ""))[:800]
    mechanism = str(entry.get("mecanismo", ""))
    supuestos = [
        str(item).strip()
        for item in (entry.get("supuestos") or [])
        if str(item).strip()
    ]
    # Solo se reutiliza contenido ya declarado por el intérprete. Si tampoco
    # existe un supuesto alternativo, el campo sigue vacío y el dossier no pasa
    # a SUPRA: nunca se inventa una explicación para satisfacer el schema.
    alternativa = (alternativa_explicativa.strip() or declarada.get("alternativa_explicativa")
                   or (supuestos[0] if supuestos else ""))
    observable = str(
        entry.get("observable") or declarada.get("metrica")
        or entry.get("metrica") or prueba_concreta
    )[:400]
    resultado_mecanismo = str(
        entry.get("resultado_favorable_mecanismo")
        or declarada.get("resultado_favorable_mecanismo") or claim
    )[:400]
    resultado_alternativa = str(
        entry.get("resultado_favorable_alternativa")
        or declarada.get("resultado_favorable_alternativa") or alternativa
    )[:400]
    regla_decision = str(
        entry.get("regla_decision") or declarada.get("umbral") or prueba_concreta
    )[:400]
    prueba = {
        "afirmacion_decisiva": prueba_concreta,
        "alternativa_explicativa": alternativa,
        "intervencion_prueba": prueba_concreta,
        "observable": observable,
        "comparacion": declarada.get("baseline") or (
            "observación que distinga el mecanismo propuesto de la alternativa; "
            "si no hay alternativa declarada, la prueba no es discriminante"
        ),
        "metrica": observable,
        "resultado_favorable_mecanismo": resultado_mecanismo,
        "resultado_favorable_alternativa": resultado_alternativa,
        "regla_decision": regla_decision,
        "condicion_fracaso": str(
            entry.get("condicion_fracaso")
            or declarada.get("condicion_fracaso")
            or "si la observación no discrimina, el dossier no decide"
        )[:400],
        "coste_permisos": "a evaluar por el responsable antes de ejecutar",
        "estado_prueba": "NO_EJECUTADA",
    }

    raw_candidate_id = entry.get("candidate_id", "")
    if raw_candidate_id in (None, ""):
        candidate_id = ""
    elif not _exact_identity_text(raw_candidate_id):
        raise ValueError("candidate_id must be exact non-blank text")
    else:
        candidate_id = raw_candidate_id

    default_claim_id = "claim-" + hashlib.sha256(claim.encode("utf-8")).hexdigest()[:16]
    raw_claim_id = entry.get("claim_id")
    if raw_claim_id in (None, ""):
        claim_id = default_claim_id
    elif not _exact_identity_text(raw_claim_id):
        raise ValueError("claim_id must be exact non-blank text")
    else:
        claim_id = raw_claim_id

    default_mechanism_version = "sha256:" + hashlib.sha256(mechanism.encode("utf-8")).hexdigest()
    raw_mechanism_version = entry.get("mechanism_version")
    if raw_mechanism_version in (None, ""):
        mechanism_version = default_mechanism_version
    elif not _exact_identity_text(raw_mechanism_version):
        raise ValueError("mechanism_version must be exact non-blank text")
    else:
        mechanism_version = raw_mechanism_version

    default_protocol_version = "sha256:" + hashlib.sha256(
        json.dumps(prueba, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    raw_protocol_version = entry.get("protocol_version")
    if raw_protocol_version in (None, ""):
        protocol_version = default_protocol_version
    elif not _exact_identity_text(raw_protocol_version):
        raise ValueError("protocol_version must be exact non-blank text")
    else:
        protocol_version = raw_protocol_version
    delivered = list(entry.get("evidence_delivered", entry.get("evidencia_local_usada", [])))
    documented = list(entry.get("evidence_documented_as_used", []))
    interpretacion = {
        "provenance": entry.get("interpretacion_provenance") or {},
        "critica": entry.get("critica") or {},
        "evidencia_citada": entry.get("evidencia_citada") or [],
        "conocimiento_previo": entry.get("conocimiento_previo") or [],
        "incertidumbre": entry.get("incertidumbre") or "",
    }
    return {
        "dossier_id": f"dossier-{uuid4().hex}",
        "candidate_id": candidate_id,
        "run_id": entry.get("run_id", ""),
        "claim_id": claim_id,
        "protocol_version": protocol_version,
        "mechanism_version": mechanism_version,
        "problema": problema[:400],
        "bloqueo": bloqueo.get("bloqueo", ""),
        "origen_bloqueo": bloqueo.get("origen_bloqueo", ""),
        "hipotesis": claim,
        "mecanismo": mechanism,
        "evidence_delivered": delivered,
        "evidence_documented_as_used": documented,
        "evidencia_utilizada": documented,
        **({"interpretacion": interpretacion} if any(interpretacion.values()) else {}),
        "prueba_discriminante": prueba,
        "supuestos": supuestos,
        "estado": "SUPRA_EJECUCION_PENDIENTE",
        "creado_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def guardar_dossier(dossier: dict[str, Any], directory: Path | None = None) -> Path:
    directory = _dossiers_dir(directory)
    path = directory / "dossiers.jsonl"
    identity = dossier.get("dossier_id")
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("dossier_id es obligatorio")
    if dossier.get("tipo") == "resultado_observado":
        raise ValueError("usar registrar_resultado para observaciones")
    existentes, ambiguos, _ = _leer_historial(path)
    if identity in ambiguos or (
        identity in existentes and _contexto(existentes[identity]) != _contexto(dossier)
    ):
        raise ValueError("dossier_id ambiguo: crear un dossier nuevo para cambiar su contenido")
    if identity in existentes:
        return path
    directory.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dossier, ensure_ascii=False) + "\n")
    return path


def cargar_dossier(
    dossier_id: str,
    directory: Path | None = None,
) -> dict[str, Any] | None:
    """Load one unambiguous local dossier by identity."""
    identity = dossier_id.strip()
    if not identity:
        raise ValueError("dossier_id es obligatorio")
    path = _dossiers_dir(directory) / "dossiers.jsonl"
    dossiers, ambiguos, _ = _leer_historial(path)
    if identity in ambiguos:
        raise ValueError("dossier_id ambiguo")
    dossier = dossiers.get(identity)
    return dict(dossier) if dossier is not None else None


def cargar_ultimo_dossier(directory: Path | None = None) -> dict[str, Any] | None:
    """Load the newest unambiguous local dossier for Shadow restart recovery."""
    path = _dossiers_dir(directory) / "dossiers.jsonl"
    dossiers, ambiguos, _ = _leer_historial(path)
    for identity, dossier in reversed(list(dossiers.items())):
        if identity not in ambiguos:
            return dict(dossier)
    return None


def _discriminant_protocol_complete(dossier: dict[str, Any]) -> bool:
    """Return True only when the dossier can actually discriminate rival claims."""
    prueba = dossier.get("prueba_discriminante")
    if not isinstance(prueba, dict):
        return False
    required = (
        "afirmacion_decisiva",
        "alternativa_explicativa",
        "intervencion_prueba",
        "observable",
        "resultado_favorable_mecanismo",
        "resultado_favorable_alternativa",
        "regla_decision",
        "condicion_fracaso",
    )
    return bool(str(dossier.get("claim_id") or "").strip()) and all(
        str(prueba.get(field) or "").strip() for field in required
    )


_RECEIPT_FIELDS = (
    "candidate_id",
    "mechanism_version",
    "claim_id",
    "protocol_version",
    "execution_id",
    "observed_result",
    "result_scope",
)

def _normalizar_execution_receipt(receipt: dict[str, Any] | None) -> dict[str, str]:
    """Keep only the non-secret fields needed to verify execution identity."""
    if not isinstance(receipt, dict):
        return {}
    # Execution identity is typed authority, not display data.  Coercing ints,
    # bools, or arbitrary objects to text can make a malformed authoritative
    # receipt collide with a legitimate textual identity (e.g. 1 -> "1").
    return {
        field: value if isinstance((value := receipt.get(field)), str) else ""
        for field in _RECEIPT_FIELDS
    }


def _execution_receipt_matches(
    dossier: dict[str, Any],
    receipt: dict[str, Any] | None,
    *,
    resultado: str,
    execution_id: str,
    protocol_version: str,
) -> bool:
    """Accredit only a receipt that independently binds the full experiment identity."""
    normalized = _normalizar_execution_receipt(receipt)
    identity_fields = ("candidate_id", "mechanism_version", "claim_id", "protocol_version")
    if not all(_exact_identity_text(dossier.get(field)) for field in identity_fields):
        return False
    if not _exact_identity_text(protocol_version) or not _exact_identity_text(execution_id):
        return False
    if dossier["protocol_version"] != protocol_version:
        return False
    expected = {
        "candidate_id": dossier["candidate_id"],
        "mechanism_version": dossier["mechanism_version"],
        "claim_id": dossier["claim_id"],
        "protocol_version": protocol_version,
        "execution_id": execution_id,
        "observed_result": resultado,
        "result_scope": "EXPERIMENTAL_OBSERVATION",
    }
    if not all(expected.values()):
        return False
    return all(normalized.get(field) == value for field, value in expected.items())


def registrar_resultado(
    dossier_id: str,
    resultado: str,
    *,
    condiciones: str = "",
    execution_id: str = "",
    protocol_version: str = "",
    execution_receipt: dict[str, Any] | None = None,
    execution_resolver: Callable[[str], dict[str, Any] | None] | None = None,
    directory: Path | None = None,
) -> dict[str, Any]:
    """Record a declared result, accrediting it only to a bound execution.

    A result without a matching execution/protocol identity is preserved as
    ``DECLARED_RESULT`` but is not eligible for ``lecciones_previas``.
    """
    if resultado not in ("positivo", "negativo", "indeterminado"):
        raise ValueError("resultado debe ser positivo|negativo|indeterminado")
    directory = _dossiers_dir(directory)
    path = directory / "dossiers.jsonl"
    dossiers, ambiguos, existing_results = _leer_historial(path)
    if dossier_id not in dossiers or dossier_id in ambiguos:
        raise ValueError("el resultado requiere un dossier existente y no ambiguo")
    dossier = dossiers[dossier_id]
    bound_protocol = str(dossier.get("protocol_version") or "")
    declared_receipt = _normalizar_execution_receipt(execution_receipt)
    resolved_receipt: dict[str, str] = {}
    execution_identity_valid = _exact_identity_text(execution_id)
    protocol_identity_valid = _exact_identity_text(protocol_version)
    if execution_resolver is not None and execution_identity_valid:
        try:
            resolved_receipt = _normalizar_execution_receipt(
                execution_resolver(execution_id)
            )
        except Exception:  # noqa: BLE001 — resolver failure cannot fabricate accreditation
            resolved_receipt = {}
    protocol_complete = _discriminant_protocol_complete(dossier)
    accredited = bool(
        protocol_complete
        and execution_identity_valid
        and protocol_identity_valid
        and protocol_version == bound_protocol
        and execution_resolver is not None
        and _execution_receipt_matches(
            dossier,
            resolved_receipt,
            resultado=resultado,
            execution_id=execution_id,
            protocol_version=protocol_version,
        )
    )
    observation_id = ""
    previous_revisions: list[dict[str, Any]] = []
    if execution_identity_valid and protocol_identity_valid:
        observation_id = hashlib.sha256(
            f"{dossier_id}|{execution_id}|{protocol_version}".encode()
        ).hexdigest()
        previous_revisions = [
            item
            for item in existing_results
            if item.get("observation_id") == observation_id
            and item.get("result_semantics_version") == DOSSIER_RESULT_SEMANTICS_VERSION
        ]
    first_registered_at = (
        str(
            previous_revisions[0].get("first_registered_at")
            or previous_revisions[0].get("registrado_at")
            or ""
        )
        if previous_revisions
        else ""
    )
    registered_at = datetime.now(UTC).isoformat(timespec="seconds")
    if not first_registered_at:
        first_registered_at = registered_at

    registro = {
        "observation_id": observation_id,
        "revision_index": len(previous_revisions),
        "first_registered_at": first_registered_at,
        "dossier_id": dossier_id,
        "candidate_id": dossier.get("candidate_id", ""),
        "mechanism_version": dossier.get("mechanism_version", ""),
        "claim_id": dossier.get("claim_id", ""),
        "protocol_version": protocol_version,
        "execution_id": execution_id,
        "resultado": resultado,
        "observed_result": resultado,
        "declared_execution_receipt": declared_receipt,
        "execution_receipt": resolved_receipt,
        "receipt_authority": "EXECUTION_RESOLVER" if accredited else "NONE",
        "result_semantics_version": DOSSIER_RESULT_SEMANTICS_VERSION,
        "protocol_complete": protocol_complete,
        "accreditation": "ACCREDITED_EXECUTION" if accredited else "DECLARED_RESULT",
        "learning_eligible": bool(accredited and resultado in ("positivo", "negativo")),
        "accreditation_reason": (
            "resolved_authoritative_execution_receipt"
            if accredited
            else (
                "incomplete_discriminant_protocol"
                if not protocol_complete
                else "no_authoritative_matching_execution_receipt"
            )
        ),
        "condiciones": condiciones[:400],
        "registrado_at": registered_at,
        "autor": "humano/experimento",
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(
            {**registro, "tipo": "resultado_observado"}, ensure_ascii=False) + "\n")
    return registro


def lecciones_previas(
    query: str, directory: Path | None = None, limit: int = 3,
    *, execution_resolver: Callable[[str], dict[str, Any] | None] | None = None,
) -> list[str]:
    """Lecciones registradas pertinentes a la consulta (paso 5 del circuito).

    Un resultado elegible vuelve a la búsqueda como aprendizaje trazable y
    acotado: se informa qué se observó en una ejecución acreditada bajo su
    protocolo; no se convierte automáticamente en afirmación causal general.
    """
    path = _dossiers_dir(directory) / "dossiers.jsonl"
    if not path.exists() or limit <= 0:
        return []
    q = (query or "").casefold()
    dossiers, ambiguos, resultados = _leer_historial(path)
    if ambiguos:
        warnings.warn(
            "Historial ambiguo: resultados excluidos del aprendizaje; registros conservados",
            RuntimeWarning,
            stacklevel=2,
        )
    # Latest revision wins for one stable accredited observation identity.
    # Corrections remain in JSONL but never become independent lessons.
    effective_results: dict[str, dict[str, Any]] = {}
    for res in resultados:
        observation_id = str(res.get("observation_id") or "")
        if (
            not observation_id
            or res.get("result_semantics_version") != DOSSIER_RESULT_SEMANTICS_VERSION
        ):
            continue
        effective_results[observation_id] = res

    out: list[str] = []
    for res in effective_results.values():
        identity = res.get("dossier_id", "")
        if identity in ambiguos or identity not in dossiers:
            continue
        if res.get("accreditation") != "ACCREDITED_EXECUTION":
            continue
        if res.get("result_semantics_version") != DOSSIER_RESULT_SEMANTICS_VERSION:
            # Preserve legacy observations but never reactivate old derived
            # lessons after semantic/accreditation rules become stricter.
            continue
        if res.get("receipt_authority") != "EXECUTION_RESOLVER":
            # Legacy/caller-declared receipts are preserved but never promoted
            # to learning evidence after the authoritative-resolver contract.
            continue
        if res.get("learning_eligible") is not True:
            # INDETERMINATE is an observed state, not a learning reward/lesson.
            continue
        # Persisted accreditation records what was accepted at write time; it
        # is not itself authority after restart. Re-resolve the execution on
        # every learning read and fail closed if live authority is unavailable.
        if execution_resolver is None:
            continue
        execution_id = res.get("execution_id")
        protocol_version = res.get("protocol_version")
        if not _exact_identity_text(execution_id) or not _exact_identity_text(protocol_version):
            continue
        try:
            authoritative_receipt = _normalizar_execution_receipt(
                execution_resolver(execution_id)
            )
        except Exception:  # resolver failure cannot reactivate stored evidence
            continue
        d = dossiers[identity]
        if not _execution_receipt_matches(
            d,
            authoritative_receipt,
            resultado=str(res.get("resultado") or ""),
            execution_id=execution_id,
            protocol_version=protocol_version,
        ):
            continue
        if res.get("resultado") not in ("positivo", "negativo", "indeterminado"):
            continue
        problema = str(d.get("problema", "")).casefold()
        if q and not any(w in problema for w in q.split() if len(w) >= 4):
            continue
        out.append(
            f"{res['dossier_id']}: en ejecución acreditada se observó "
            f"'{res['resultado']}' para el contraste del mecanismo "
            f"'{str(d.get('mecanismo', ''))[:120]}' "
            f"(protocolo={res.get('protocol_version', '')[:80]}; "
            f"condiciones: {res.get('condiciones', '')[:120]}). "
            "Alcance: resultado del contraste ejecutado, no causalidad general."
        )
        if len(out) >= limit:
            break
    return out
