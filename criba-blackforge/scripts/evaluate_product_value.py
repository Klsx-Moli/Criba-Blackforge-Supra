"""Paired, blinded-review bookkeeping for CRIBA+SUPRA versus direct LLM.

This tool does not run models, invent outcomes, or claim scientific superiority.
It only checks a predeclared case/arm ledger against separately entered reviews.
Unknown, disagreement, absent ratings and non-confirmatory cases never become
wins or zeros. All blinding and preregistration remain DECLARED, not verified.

Usage:
    python scripts/evaluate_product_value.py manifest.json reviews.json --output report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "criba-llm-paired/1"
ARM_LABELS = frozenset({"CRIBA_SUPRA", "DIRECT_LLM"})
SPLITS = frozenset({"exploratory", "confirmatory"})
CHOICES = frozenset({"A", "B", "TIE", "ABSTAIN"})
HEX256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha(value: Any, field: str) -> str:
    _require(isinstance(value, str) and bool(HEX256.fullmatch(value)), f"{field}: expected sha256:<64 lowercase hex>")
    return value


def _id(value: Any, field: str) -> str:
    _require(isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value)), f"{field}: invalid ID")
    return value


def _as_list(value: Any, field: str) -> list[Any]:
    _require(isinstance(value, list), f"{field}: expected list")
    return value


def evaluate_pairs(manifest: dict[str, Any], reviews: dict[str, Any]) -> dict[str, Any]:
    """Describe *observed declared reviews*, never validate scientific benefit."""
    _require(isinstance(manifest, dict) and isinstance(reviews, dict), "expected JSON objects")
    _require(manifest.get("schema") == SCHEMA, "unsupported manifest schema")
    _require(reviews.get("schema") == SCHEMA, "unsupported reviews schema")
    _sha(manifest.get("protocol_sha256"), "protocol_sha256")
    cases = _as_list(manifest.get("cases"), "cases")
    rows = _as_list(reviews.get("reviews"), "reviews")
    _require(bool(cases), "at least one case required")

    case_map: dict[str, dict[str, Any]] = {}
    pair_fingerprints: set[tuple[str, str]] = set()
    for item in cases:
        _require(isinstance(item, dict), "case must be an object")
        case_id = _id(item.get("case_id"), "case_id")
        _require(case_id not in case_map, f"duplicate case_id: {case_id}")
        split = item.get("split")
        _require(isinstance(split, str) and split in SPLITS, f"{case_id}: invalid split")
        domain = _id(item.get("domain"), f"{case_id}.domain")
        _require(bool(domain), "domain required")
        arms = item.get("arms")
        _require(isinstance(arms, dict) and set(arms) == {"A", "B"}, f"{case_id}: must contain A and B")
        for key in ("A", "B"):
            _require(isinstance(arms[key], dict), f"{case_id}: {key} must be object")
            _require(isinstance(arms[key].get("system"), str) and arms[key]["system"] in ARM_LABELS, f"{case_id}: invalid system")
            _sha(arms[key].get("artifact_sha256"), f"{case_id}.{key}.artifact_sha256")
        _require({arms["A"]["system"], arms["B"]["system"]} == ARM_LABELS, f"{case_id}: both comparison systems required")
        fingerprint = tuple(sorted([arms["A"]["artifact_sha256"], arms["B"]["artifact_sha256"]]))
        _require(fingerprint[0] != fingerprint[1], f"{case_id}: identical artifacts cannot form comparison")
        _require(fingerprint not in pair_fingerprints, f"{case_id}: duplicate artifact pair (padding)")
        pair_fingerprints.add(fingerprint)
        case_map[case_id] = item

    review_by_case: dict[str, list[dict[str, Any]]] = {case_id: [] for case_id in case_map}
    review_owners: set[tuple[str, str]] = set()
    for row in rows:
        _require(isinstance(row, dict), "review must be object")
        case_id = _id(row.get("case_id"), "review.case_id")
        reviewer = _id(row.get("reviewer_id"), "review.reviewer_id")
        _require(case_id in case_map, f"unknown case review: {case_id}")
        _require((case_id, reviewer) not in review_owners, f"{case_id}: duplicate reviewer {reviewer}")
        review_owners.add((case_id, reviewer))
        choice = row.get("choice")
        _require(isinstance(choice, str) and choice in CHOICES, f"{case_id}: invalid choice")
        # A self-declaration is not evidence of blinding, but unblinded
        # reviews must not be counted as if they were blinded.
        _require(type(row.get("blind_declared")) is bool, f"{case_id}: blind_declared must be bool")
        evidence = row.get("evidence_ref")
        _require(isinstance(evidence, str) and bool(evidence.strip()), f"{case_id}: missing evidence_ref")
        _require("system" not in row and "model" not in row, f"{case_id}: arm identity leaked into review")
        review_by_case[case_id].append(row)

    results: list[dict[str, Any]] = []
    wins = {"CRIBA_SUPRA": 0, "DIRECT_LLM": 0}
    ties = 0
    unresolved = 0
    for case_id, item in case_map.items():
        eligible = item["split"] == "confirmatory"
        reviewers = review_by_case[case_id]
        winner: str | None = None
        status = "EXPLORATORY_NOT_SCORED" if not eligible else "UNKNOWN"
        # Two distinct blinded-declared reviewers must agree. Self-reported
        # blinding remains unverified, even when agreement is present.
        if eligible:
            if len(reviewers) >= 2 and all(r["blind_declared"] for r in reviewers):
                choices = {r["choice"] for r in reviewers}
                if len(choices) == 1:
                    choice = next(iter(choices))
                    if choice in {"A", "B"}:
                        winner = item["arms"][choice]["system"]
                        wins[winner] += 1
                        status = "REVIEWER_CONSENSUS_DECLARED"
                    elif choice == "TIE":
                        ties += 1
                        status = "REVIEWER_TIE_DECLARED"
            if status == "UNKNOWN":
                unresolved += 1
        results.append({
            "case_id": case_id,
            "split": item["split"],
            "review_count": len(reviewers),
            "status": status,
            "winner": winner,
        })

    compared = sum(wins.values())
    canonical = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return {
        "schema": SCHEMA,
        "ledger_sha256": "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "preregistration_verified": False,
        "blinding_verified_independently": False,
        "scientific_advantage": "NOT_ESTABLISHED",
        "interpretation": "DESCRIPTIVE_ONLY_DECLARED_REVIEWS",
        "confirmatory_count": sum(item["split"] == "confirmatory" for item in cases),
        "criba_wins": wins["CRIBA_SUPRA"],
        "direct_llm_wins": wins["DIRECT_LLM"],
        "ties": ties,
        "unresolved": unresolved,
        "paired_win_rate": wins["CRIBA_SUPRA"] / compared if compared else None,
        "cases": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("reviews", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        reviews = json.loads(args.reviews.read_text(encoding="utf-8"))
        report = evaluate_pairs(manifest, reviews)
    except (OSError, ValueError) as exc:
        print(f"NO_RESULT: {exc}", file=sys.stderr)
        return 2
    formatted = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(formatted, encoding="utf-8")
    else:
        print(formatted, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
