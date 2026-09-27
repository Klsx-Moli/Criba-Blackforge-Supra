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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DOSSIER_RESULT_SEMANTICS_VERSION = 3
from uuid import uuid4


def _exact_identity_text(value: object) -> bool:
    """Identity text is exact authority; never coerce or trim it implicitly."""
    return isinstance(value, str) and bool(value) and value == value.strip()


def _dossiers_dir(override: Path | None = None) -> Path:
    if override is not None:
        return override
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
    bloqueo = (ficha_bloqueo or {})
    prueba_concreta = str(entry.get("prueba_concreta", ""))[:600]
    observable = str(entry.get("observable") or entry.get("metrica") or "")[:400]
    prueba = {
        "afirmacion_decisiva": prueba_concreta,
        "alternativa_explicativa": alternativa_explicativa.strip(),
        "intervencion_prueba": prueba_concreta,
        "observable": observable,
        "comparacion": (
            "observación que distinga el mecanismo propuesto de la alternativa; "
            "si no hay alternativa declarada, la prueba no es discriminante"
        ),
        "metrica": observable,
        "resultado_favorable_mecanismo": str(
            entry.get("resultado_favorable_mecanismo") or ""
        )[:400],
        "resultado_favorable_alternativa": str(
            entry.get("resultado_favorable_alternativa") or ""
        )[:400],
        "regla_decision": str(entry.get("regla_decision") or "")[:400],
        "condicion_fracaso": str(
            entry.get("condicion_fracaso")
            or "si la observación no discrimina, el dossier no decide"
        )[:400],
        "coste_permisos": "a evaluar por el responsable antes de ejecutar",
        "estado_prueba": "NO_EJECUTADA",
    }
    claim = str(entry.get("hipotesis", ""))[:800]
    mechanism = str(entry.get("mecanismo", ""))

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
        "prueba_discriminante": prueba,
        "supuestos": list(entry.get("supuestos", [])),
        "estado": "SUPRA_EJECUCION_PENDIENTE",
        "creado_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
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
            f"{dossier_id}|{execution_id}|{protocol_version}".encode("utf-8")
        ).hexdigest()
        previous_revisions = [
            item
            for item in existing_results
            if item.get("observation_id") == observation_id
            and item.get("result_semantics_version") == DOSSIER_RESULT_SEMANTICS_VERSION
        ]
    first_registered_at = (
        str(previous_revisions[0].get("first_registered_at") or previous_revisions[0].get("registrado_at") or "")
        if previous_revisions
        else ""
    )
    registered_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
