from __future__ import annotations

import json
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


def _string_list(value: Any, error: str) -> list[str]:
    values = _require_list(value, error)
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise AntiGoodhartViolation(error)
    if len(values) != len(set(values)):
        raise AntiGoodhartViolation(error)
    return values


def _case_ids(case: Any) -> set[str]:
    if not isinstance(case, dict):
        raise AntiGoodhartViolation("INVALID_CASE")
    _require_nonempty_str(case.get("test_case_id"), "INVALID_CASE_ID")
    observations = _require_list(case.get("observations"), "INVALID_OBSERVATIONS")
    ids: list[str] = []
    for observation in observations:
        if not isinstance(observation, dict):
            raise AntiGoodhartViolation("INVALID_OBSERVATION")
        ids.append(_require_nonempty_str(observation.get("observation_id"), "INVALID_OBSERVATION_ID"))
    if len(ids) != len(set(ids)):
        raise AntiGoodhartViolation("DUPLICATE_OBSERVATION_ID")
    return set(ids)


def _oracle_anti(oracle: Any) -> dict[str, Any]:
    if not isinstance(oracle, dict):
        raise AntiGoodhartViolation("INVALID_ORACLE")
    anti = oracle.get("anti_goodhart", {})
    if not isinstance(anti, dict):
        raise AntiGoodhartViolation("INVALID_ORACLE_ANTI_GOODHART")
    if "must_not_claim_causal_mechanism" in anti and type(anti["must_not_claim_causal_mechanism"]) is not bool:
        raise AntiGoodhartViolation("INVALID_ORACLE_CAUSAL_FLAG")
    _string_list(anti.get("forbidden_fields", []), "INVALID_ORACLE_FORBIDDEN_FIELDS")
    return anti


def validate_retrybox_response(
    response: dict[str, Any],
    case: dict[str, Any],
    oracle: dict[str, Any] | None = None,
) -> None:
    """Validate structure and evidence identity, not scientific truth.

    Mirrors retrybox_evidence_contract.json without a runtime jsonschema dependency.
    """
    if not isinstance(response, dict):
        raise AntiGoodhartViolation("RESPONSE_NOT_OBJECT")
    valid_ids = _case_ids(case)
    _require_nonempty_str(response.get("test_case_id"), "CASE_ID_MISMATCH")
    if response["test_case_id"] != case["test_case_id"]:
        raise AntiGoodhartViolation("CASE_ID_MISMATCH")
    decision = response.get("decision")
    if not isinstance(decision, str) or decision not in {"propose", "request_more_evidence"}:
        raise AntiGoodhartViolation("INVALID_DECISION")
    evidence_ids = _require_list(response.get("evidence_ids"), "INVALID_EVIDENCE_IDS")
    if any(not isinstance(item, str) for item in evidence_ids):
        raise AntiGoodhartViolation("INVALID_EVIDENCE_ID_TYPE")
    if any(not item.strip() for item in evidence_ids):
        raise AntiGoodhartViolation("INVALID_EVIDENCE_IDS")
    if len(evidence_ids) != len(set(evidence_ids)):
        raise AntiGoodhartViolation("DUPLICATE_EVIDENCE")
    unknown = set(evidence_ids) - valid_ids
    if unknown:
        raise AntiGoodhartViolation(f"UNKNOWN_EVIDENCE:{sorted(unknown)}")
    _require_nonempty_str(response.get("rationale"), "MISSING_RATIONALE")
    requested = _string_list(response.get("requested_evidence"), "INVALID_REQUESTED_EVIDENCE")
    checks = _string_list(response.get("proposed_checks"), "INVALID_PROPOSED_CHECKS")
    if decision == "propose":
        _require_nonempty_str(response.get("hypothesis"), "PROPOSE_WITHOUT_HYPOTHESIS")
        if not evidence_ids:
            raise AntiGoodhartViolation("PROPOSE_WITHOUT_EVIDENCE")
        if not checks:
            raise AntiGoodhartViolation("PROPOSE_WITHOUT_CHECKS")
    else:
        if "hypothesis" not in response:
            raise AntiGoodhartViolation("MISSING_HYPOTHESIS")
        if response["hypothesis"] is not None:
            raise AntiGoodhartViolation("ABSTENTION_WITH_HYPOTHESIS")
        if not requested:
            raise AntiGoodhartViolation("ABSTENTION_WITHOUT_REQUEST")
    if oracle is not None:
        anti = _oracle_anti(oracle)
        if "test_case_id" in oracle and oracle["test_case_id"] != case["test_case_id"]:
            raise AntiGoodhartViolation("ORACLE_CASE_ID_MISMATCH")
        if decision == "propose" and anti.get("must_not_claim_causal_mechanism"):
            raise AntiGoodhartViolation("CAUSAL_OVERCLAIM")
        forbidden = set(anti.get("forbidden_fields", []))
        if forbidden.intersection(response):
            raise AntiGoodhartViolation(f"FORBIDDEN_FIELD_USED:{sorted(forbidden.intersection(response))}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise ValueError("nonfinite JSON constant")


def validate_oracle_file(oracle_path: str | Path) -> tuple[bool, str]:
    """Return a failed verdict for unreadable, malformed or inconsistent input.

    This checks oracle integrity, not causal/semantic correctness of the oracle.
    """
    oracle_path = Path(oracle_path)
    case_path = oracle_path.parent / "case.input.json"
    try:
        case = json.loads(case_path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        oracle = json.loads(oracle_path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        valid_ids = _case_ids(case)
        _oracle_anti(oracle)
        if "test_case_id" in oracle and oracle["test_case_id"] != case["test_case_id"]:
            return False, "ORACLE_CASE_ID_MISMATCH"
        allowed = set(_string_list(oracle.get("allowed_evidence_ids", []), "INVALID_ALLOWED_EVIDENCE_IDS"))
        required = set(_string_list(oracle.get("required_evidence_ids", []), "INVALID_REQUIRED_EVIDENCE_IDS"))
        if not allowed.issubset(valid_ids):
            return False, "oracle allowed_evidence_ids references unknown ids"
        if not required.issubset(allowed):
            return False, "oracle required_evidence_ids not in allowed"
        decision = oracle.get("expected_decision")
        if not isinstance(decision, str) or decision not in {"propose", "request_more_evidence"}:
            return False, "INVALID_ORACLE_DECISION"
        field = "expected_proposed_checks" if decision == "propose" else "expected_requested_evidence"
        values = _string_list(oracle.get(field), "INVALID_ORACLE_EXPECTED_EVIDENCE")
        if not values:
            return False, f"oracle {decision} requires {field}"
    except AntiGoodhartViolation as exc:
        return False, str(exc)
    except (OSError, UnicodeError, ValueError):
        return False, "ORACLE_OR_CASE_UNREADABLE_OR_INVALID_JSON"
    return True, "PASS"
