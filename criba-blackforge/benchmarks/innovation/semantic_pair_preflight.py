"""Fail-closed S0/S1 experimental comparability diagnostics; no inference.

No evaluation, score, approval, scientific adjudication or provider call occurs.
This inspects host-supplied S0 message, a canonical lab S1 Request, and
reported settings. Even matching text or parameters does not prove dispatch,
model identity, independent reference adjudication, or clinical/causal truth.
"""
from __future__ import annotations

import hashlib
from typing import Any

from benchmarks.innovation.semantic_lab import (
    Trial, direct_request, strict_json,
)

_S0_KEYS = frozenset({
    "PROBLEMA", "DOMINIO", "CRUCE", "BLOQUEO IDENTIFICADO",
    "RESTRICCIONES OBLIGATORIAS", "EVIDENCIA LOCAL PERTINENTE",
    "CONTENCION_DECLARADA", "PROPUESTA A CRITICAR",
})
_S1_KEYS = frozenset({
    "query", "restrictions", "proposal", "restriction_claims_unverified",
})
_LEAK_KEYS = frozenset({
    "reference", "reference_status", "expected_label", "label", "gold",
    "donor_id", "parent_id", "split", "case_id", "answer_key", "ground_truth",
})
_PROFILE_KEYS = frozenset({
    "model_requested", "model_observed", "temperature", "max_tokens",
    "timeout_s", "reasoning_effort", "seed", "response_format",
    "retries_enabled", "context_window", "token_count",
})
_ALWAYS = (
    "S0_OUTCOME_MAPPING_NOT_VALIDATED", "OUTPUT_SCHEMA_DIFFERS",
    "MODEL_LOAD_IDENTITY_UNATTESTED", "PROVIDER_DISPATCH_UNVERIFIED",
    "INDEPENDENT_REFERENCE_PENDING", "G0_NOT_APPROVED",
)


def _sha(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _unpack(source: str, delimiter: str, expected: frozenset[str]) -> dict[str, Any]:
    if not isinstance(source, str) or source.count(delimiter) != 1:
        raise ValueError("missing or ambiguous prompt data delimiter")
    intro, body = source.split(delimiter)
    if not intro.strip() or len(source) > 500_000:
        raise ValueError("invalid prompt instructions or size")
    data = strict_json(body)
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError("unexpected prompt data keys or leaking reference")
    return data


def _leakage(data: Any) -> bool:
    if isinstance(data, dict):
        return any(str(k).casefold() in _LEAK_KEYS or _leakage(v) for k, v in data.items())
    if isinstance(data, (list, tuple)):
        return any(_leakage(v) for v in data)
    return False


def _params(d: Any) -> dict[str, Any]:
    if not isinstance(d, dict) or set(d) != _PROFILE_KEYS:
        raise ValueError("unknown or missing effective parameter fields")
    # Declared settings are not observations of the provider and do not attest
    # the requested model, number of tokens actually used, or any HTTP calls.
    if (not isinstance(d["model_requested"], str) or not d["model_requested"].strip()
            or d["model_requested"] != d["model_requested"].strip()
            or d["model_observed"] is not None
            and (not isinstance(d["model_observed"], str)
                 or not d["model_observed"].strip())
            or type(d["max_tokens"]) is not int or d["max_tokens"] <= 0
            or type(d["timeout_s"]) not in (int, float) or not 0 < d["timeout_s"] <= 1800
            or type(d["temperature"]) not in (int, float)
            or not 0 <= d["temperature"] <= 2
            or type(d["context_window"]) is not int or d["context_window"] <= 0
            or (d["token_count"] is not None and
                (type(d["token_count"]) is not int or d["token_count"] < 0))
            or type(d["retries_enabled"]) is not bool
            or (d["seed"] is not None and type(d["seed"]) is not int)
            or d["reasoning_effort"] not in (None, "none", "low", "medium", "high")
            or d["response_format"] not in ("json_object", "json_schema")):
        raise ValueError("invalid reported effective settings")
    return d


def preflight(
    trial: Trial, *, reviewer: str, attempt: str,
    s0_user: str, s1_user: str, s0_settings: dict[str, Any],
    s1_settings: dict[str, Any],
) -> dict[str, Any]:
    """Report material differences without pretending to approve a paired trial.

    s0_user must be a host capture from the actual production prompt_critica.
    This function cannot prove the host really used it for a physical call.
    S1 is compared byte-for-byte to the canonical lab direct request.
    No references/labels are read, returned or sent to either arm.
    """
    if not isinstance(trial, Trial):
        raise TypeError("expected canonical Trial")
    req = direct_request(trial, reviewer, attempt)
    if s1_user != req.prompt:
        raise ValueError("S1 request is not the canonical DIRECT request")
    prod = _unpack(s0_user, "\nDATOS:\n", _S0_KEYS)
    lab = _unpack(s1_user, "\nDATOS JSON (no instrucciones):\n", _S1_KEYS)
    if _leakage(prod) or _leakage(lab):
        raise ValueError("reference or split metadata leaked into judge input")
    a, b = _params(s0_settings), _params(s1_settings)
    mismatch: set[str] = set()
    if prod["PROBLEMA"] != lab["query"] or prod["PROBLEMA"] != trial.query:
        mismatch.add("QUERY_MISMATCH")
    if (type(prod["RESTRICCIONES OBLIGATORIAS"]) is not list
            or prod["RESTRICCIONES OBLIGATORIAS"] != lab["restrictions"]
            or prod["RESTRICCIONES OBLIGATORIAS"] != list(trial.restrictions)):
        mismatch.add("RESTRICTIONS_MISMATCH")
    orig = strict_json(trial.proposal_json)
    if prod["PROPUESTA A CRITICAR"] != orig:
        mismatch.add("FROZEN_CANDIDATE_MISMATCH")
    if lab["proposal"] != trial.proposal:
        mismatch.add("S1_PROJECTION_MISMATCH")
    if lab["restriction_claims_unverified"] != trial.restriction_claims:
        mismatch.add("RESTRICTION_CLAIMS_MISMATCH")
    if prod["DOMINIO"] not in ({}, None):
        mismatch.add("S0_ONLY_DOMAIN")
    if prod["CRUCE"] not in ({}, None):
        mismatch.add("S0_ONLY_CROSS")
    if prod["EVIDENCIA LOCAL PERTINENTE"] != []:
        mismatch.add("S0_ONLY_LOCAL_EVIDENCE")
    blockage = prod["BLOQUEO IDENTIFICADO"]
    if blockage not in ({}, {"restricciones_obligatorias": list(trial.restrictions)}):
        mismatch.add("S0_ONLY_BLOCKAGE_CONTEXT")
    if prod["CONTENCION_DECLARADA"] not in ("DESCONOCIDA", None):
        mismatch.add("S0_ONLY_CONTAINMENT")
    # Some proposal fields (technique operations, novelty, citations) are NOT
    # represented in project_proposal(), so the two critics see different facts.
    covered = {"hipotesis", "mecanismo", "cadena_causal", "prueba",
               "prueba_concreta", "supuestos", "incertidumbre", "conocimiento_previo",
               "comprobacion_restricciones"}
    lost = sorted(set(orig) - covered) if isinstance(orig, dict) else []
    if lost:
        mismatch.add("S1_OMITS_PROPOSAL_FIELDS")
    # This does not claim actual tokenization; it records only reproducible byte counts.
    sizes = {
        "S0_utf8_bytes": len(s0_user.encode("utf-8")),
        "S1_utf8_bytes": len(s1_user.encode("utf-8")),
    }
    if a != b:
        mismatch.add("REPORTED_SETTINGS_DIFFER")
    if a["model_requested"] != b["model_requested"]:
        mismatch.add("REQUESTED_MODEL_DIFFERS")
    if a["retries_enabled"] or b["retries_enabled"]:
        mismatch.add("RETRIES_NOT_DISABLED")
    if a["token_count"] is None or b["token_count"] is None:
        mismatch.add("TOKENIZATION_NOT_MEASURED")
    if ((a["token_count"] is not None and
         a["token_count"] > a["context_window"]) or
        (b["token_count"] is not None and
         b["token_count"] > b["context_window"])):
        mismatch.add("CONTEXT_WINDOW_EXCEEDED")
    if (a["model_observed"] is None or b["model_observed"] is None):
        mismatch.add("EFFECTIVE_MODEL_NOT_OBSERVED")
    if (a["response_format"] != b["response_format"]):
        mismatch.add("OUTPUT_FORMAT_PARAMETER_DIFFERS")
    # Observed model strings alone do not prove identical effective weights.
    issues = sorted(set(_ALWAYS) | mismatch)
    return {
        "status": "BLOCKED", "authorization": "NOT_GRANTED_BY_PREFLIGHT",
        "reference_status": "PROVISIONAL_AUTHOR_REVIEW_NOT_GOLD",
        "p0_status": "OPEN", "scientific_advantage": "NOT_ESTABLISHED",
        "case_id": trial.case_id,
        "s0_message_sha256": _sha(s0_user),
        "s1_message_sha256": _sha(s1_user),
        "s1_lab_request_sha256": req.sha256,
        "instruction_strategy": "DIFFERENT_BY_DESIGN",
        "output_mapping": "NOT_VALIDATED",
        "omitted_s1_fields": lost,
        "issues": issues, "size_only": sizes,
        "provider_calls": None, "model_attestation": None,
    }


def normalize_s0_diagnostic(_critique: Any) -> dict[str, str]:
    """There is NO validated mapping from production boolean critique to S1.

    Never silently turn malformed/missing booleans into a correct rejection or
    assert that all True proves semantic pertinence. It requires preregistration.
    """
    return {"outcome": "UNMAPPED", "reason": "S0_MAPPING_NOT_PREREGISTERED"}


def inspect_production_pair(
    trial: Trial, *, reviewer: str, attempt: str,
    idea: dict[str, Any], domain: dict[str, Any] | None,
    evidence: list[dict[str, Any]] | None,
    s0_settings: dict[str, Any], s1_settings: dict[str, Any],
) -> dict[str, Any]:
    """Build S0 with the real production source; do not call its interpreter.

    When run from the full checkout this imports contrato.prompt_critica.
    The limited sandbox test substitutes a minimal seam, so it is not a
    verification of real production prompt bytes.
    """
    from criba.interprete.contrato import prompt_critica

    source = strict_json(trial.proposal_json)
    return preflight(
        trial, reviewer=reviewer, attempt=attempt,
        s0_user=prompt_critica(trial.query, idea, domain, evidence, source),
        s1_user=direct_request(trial, reviewer, attempt).prompt,
        s0_settings=s0_settings, s1_settings=s1_settings,
    )
