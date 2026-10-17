from __future__ import annotations

from pathlib import Path
from typing import Any


class AntiGoodhartViolation(ValueError):
    """Raised when a response violates the evidence contract."""


def _require_nonempty_str(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AntiGoodhartViolation(error)
    return value


def _require_list(value: Any, error: str) -> list[Any]:
    if not isinstance(value, list):
        raise AntiGoodhartViolation(error)
    return value


def validate_retrybox_response(
    response: dict[str, Any],
    case: dict[str, Any],
    oracle: dict[str, Any] | None = None,
) -> None:
    """Validate a structured interpreter response against the evidence contract.

    Raises AntiGoodhartViolation on any contract violation. Returns None on success.
    """
    if not isinstance(response, dict):
        raise AntiGoodhartViolation("RESPONSE_NOT_OBJECT")

    if response.get("test_case_id") != case.get("test_case_id"):
        raise AntiGoodhartViolation("CASE_ID_MISMATCH")

    decision = response.get("decision")
    if decision not in {"propose", "request_more_evidence"}:
        raise AntiGoodhartViolation("INVALID_DECISION")

    evidence_ids = _require_list(
        response.get("evidence_ids"),
        "INVALID_EVIDENCE_IDS",
    )

    if any(not isinstance(item, str) for item in evidence_ids):
        raise AntiGoodhartViolation("INVALID_EVIDENCE_ID_TYPE")

    if len(evidence_ids) != len(set(evidence_ids)):
        raise AntiGoodhartViolation("DUPLICATE_EVIDENCE")

    valid_ids = {
        obs["observation_id"]
        for obs in case.get("observations", [])
        if isinstance(obs, dict) and "observation_id" in obs
    }

    unknown = set(evidence_ids) - valid_ids
    if unknown:
        raise AntiGoodhartViolation(f"UNKNOWN_EVIDENCE:{sorted(unknown)}")

    _require_nonempty_str(
        response.get("rationale"),
        "MISSING_RATIONALE",
    )

    _require_list(
        response.get("requested_evidence"),
        "INVALID_REQUESTED_EVIDENCE",
    )

    _require_list(
        response.get("proposed_checks"),
        "INVALID_PROPOSED_CHECKS",
    )

    # UNKNOWN_PROMOTED: no field may convert None/null into positive.
    for field in ("evidence_ids", "rationale", "proposed_checks", "requested_evidence"):
        value = response.get(field)
        if value is None and field in response:
            raise AntiGoodhartViolation(f"UNKNOWN_PROMOTED:{field}")

    if decision == "propose":
        _require_nonempty_str(
            response.get("hypothesis"),
            "PROPOSE_WITHOUT_HYPOTHESIS",
        )
        if not evidence_ids:
            raise AntiGoodhartViolation("PROPOSE_WITHOUT_EVIDENCE")

    if decision == "request_more_evidence":
        requested = response.get("requested_evidence") or []
        if not requested:
            raise AntiGoodhartViolation("ABSTENTION_WITHOUT_REQUEST")

    if oracle:
        anti = oracle.get("anti_goodhart", {})

        if (
            decision == "propose"
            and anti.get("must_not_claim_causal_mechanism")
        ):
            raise AntiGoodhartViolation("CAUSAL_OVERCLAIM")

        forbidden = set(anti.get("forbidden_fields", []))
        if forbidden and forbidden.intersection(response):
            raise AntiGoodhartViolation(
                f"FORBIDDEN_FIELD_USED:{sorted(forbidden.intersection(response))}"
            )


def validate_oracle_file(oracle_path: str | Path) -> tuple[bool, str]:
    """Validate that an oracle references only observation_ids from its case.

    Returns (True, "PASS") or (False, reason).
    """
    import json as _json

    oracle_path = Path(oracle_path)
    case_path = oracle_path.parent / "case.input.json"
    if not case_path.is_file():
        return False, f"case.input.json not found next to {oracle_path.name}"

    case = _json.loads(case_path.read_text(encoding="utf-8"))
    oracle = _json.loads(oracle_path.read_text(encoding="utf-8"))

    valid_ids = {
        obs["observation_id"]
        for obs in case.get("observations", [])
        if isinstance(obs, dict) and "observation_id" in obs
    }

    allowed = set(oracle.get("allowed_evidence_ids", []))
    if not allowed.issubset(valid_ids):
        return False, f"oracle allowed_evidence_ids references unknown ids: {sorted(allowed - valid_ids)}"

    required = set(oracle.get("required_evidence_ids", []))
    if not required.issubset(allowed):
        return False, f"oracle required_evidence_ids not in allowed: {sorted(required - allowed)}"

    if oracle.get("expected_decision") == "propose":
        if not oracle.get("expected_proposed_checks"):
            return False, "oracle propose requires expected_proposed_checks"

    if oracle.get("expected_decision") == "request_more_evidence":
        if not oracle.get("expected_requested_evidence"):
            return False, "oracle request_more_evidence requires expected_requested_evidence"

    return True, "PASS"
