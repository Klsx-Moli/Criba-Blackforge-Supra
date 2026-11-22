"""Offline draft schedule and threshold checker; no provider, runtime or storage calls."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

MANIFEST_SHA256 = "fad4b6fc0ac3a421d3475864ed7daef37be38cfa03c3551c7ff5b46a234c4c14"
SEEDS = (27183, 314159, 161803)
ARMS = ("S0", "S1")
LABELS = ("SUPPORT", "REJECT", "UNRESOLVED")
OUTCOMES = (*LABELS, "ERROR", "NOT_RUN")
A_IDS = frozenset(
    [f"CBS500-01-01:{v}" for v in (
        "aligned", "incident", "incident-lexical", "metric", "transfer", "unknown"
    )] + ["CBS500-09-02:aligned", "CBS500-21-01:transfer"]
)


def references() -> dict[str, str]:
    raw = Path(__file__).with_name("pilot_cases.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError("draft manifest changed; reconcile and version before use")
    refs = {case_id: label for case_id, label, _ in json.loads(raw)["cases"]}
    if len(refs) != 18 or Counter(refs.values()) != {"SUPPORT": 5, "REJECT": 11, "UNRESOLVED": 2}:
        raise ValueError("unexpected sample")
    return refs


def schedule(phase: str) -> list[dict[str, Any]]:
    """Prefix-stable cumulative schedule; never send these internal IDs to the LLM."""
    if phase not in ("A", "B", "C"):
        raise ValueError("unknown phase")
    all_ids = set(references())
    blocks = [(0, A_IDS)]
    if phase in ("B", "C"):
        blocks += [(0, all_ids - A_IDS)]
    if phase == "C":
        blocks += [(1, all_ids), (2, all_ids)]
    rows = []
    for repetition, ids in blocks:
        seed = SEEDS[repetition]
        ordered = sorted(ids, key=lambda c: hashlib.sha256(f"{seed}:{c}".encode()).hexdigest())
        for index, case_id in enumerate(ordered):
            arms = ARMS if (index + repetition) % 2 == 0 else ARMS[::-1]
            for arm in arms:
                rows.append({"case_id": case_id, "repetition": repetition, "arm": arm})
    return rows


def _key(row: dict[str, Any]) -> tuple[str, int, str]:
    return row["case_id"], row["repetition"], row["arm"]


def _strict_load(raw: str) -> Any:
    def unique(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def nonfinite(_value: str) -> Any:
        raise ValueError("nonfinite JSON constant")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def summarize(phase: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts normalized terminal slots, NOT raw receipts; cannot authenticate evidence."""
    refs = references()
    slots = {_key(row) for row in schedule(phase)}
    if not isinstance(records, list):
        raise ValueError("records must be an array")
    seen = {}
    physical_calls = 0
    for row in records:
        if not isinstance(row, dict) or set(row) != {
            "case_id", "repetition", "arm", "outcome", "physical_calls"
        }:
            raise ValueError("invalid normalized record")
        if (type(row["repetition"]) is not int
                or not isinstance(row["case_id"], str)
                or not isinstance(row["arm"], str)):
            raise ValueError("invalid slot identity")
        slot = _key(row)
        outcome, calls = row["outcome"], row["physical_calls"]
        if slot not in slots or slot in seen:
            raise ValueError("unexpected or duplicate slot")
        if outcome not in OUTCOMES or type(calls) is not int or calls not in (0, 1):
            raise ValueError("invalid outcome or physical call count")
        if (outcome == "NOT_RUN" and calls != 0) or (outcome in LABELS and calls != 1):
            raise ValueError("inconsistent call count")
        seen[slot] = outcome
        physical_calls += calls
    complete = all(seen.get(s) in LABELS for s in slots)
    table = {arm: {label: dict.fromkeys(OUTCOMES, 0) for label in LABELS} for arm in ARMS}
    for case_id, rep, arm in slots:
        table[arm][refs[case_id]][seen.get((case_id, rep, arm), "NOT_RUN")] += 1
    repetitions = []
    groups = [(rep, sorted({s[0] for s in slots if s[1] == rep}), phase == "A")
              for rep in sorted({s[1] for s in slots})]
    if phase != "A":
        groups.insert(0, (0, sorted(A_IDS), True))
    for rep, ids, first_gate in groups:
        outcome = {c: seen.get((c, rep, "S1"), "NOT_RUN") for c in ids}
        minimum_support = 3 if first_gate else 4
        minimum_reject = 3 if first_gate else 9
        support = sum(refs[c] == outcome[c] == "SUPPORT" for c in ids)
        rejects = sum(refs[c] == outcome[c] == "REJECT" for c in ids)
        false_support = sum(refs[c] == "REJECT" and outcome[c] == "SUPPORT" for c in ids)
        checks = {
            "support_minimum": support >= minimum_support,
            "reject_minimum": rejects >= minimum_reject,
            "no_false_support": false_support == 0,
            "incident_controls": all(outcome.get(f"CBS500-01-01:{v}") == "REJECT"
                                     for v in ("incident", "incident-lexical")),
            "transfer_controls": all(outcome.get(c) == "SUPPORT" for c in ids
                                     if c.endswith(":transfer")),
            "unknown_preserved": all(outcome[c] == "UNRESOLVED" for c in ids
                                     if refs[c] == "UNRESOLVED"),
        }
        repetitions.append({"repetition": rep, "subset": "A" if first_gate else "FULL",
                            "checks": checks, "support": support,
                            "reject": rejects, "false_support": false_support})
    met = complete and all(all(r["checks"].values()) for r in repetitions)
    losses = sorted([{"case_id": c, "repetition": r} for c, r, a in slots
                     if a == "S0" and refs[c] == "SUPPORT"
                     and seen.get((c, r, "S0")) == "SUPPORT"
                     and seen.get((c, r, "S1")) != "SUPPORT"],
                    key=lambda v: (str(v["case_id"]), int(v["repetition"])))
    paired_negatives = Counter(
        f"{seen.get((c, r, 'S0'), 'NOT_RUN')}->{seen.get((c, r, 'S1'), 'NOT_RUN')}"
        for c, r, arm in slots if arm == "S0" and refs[c] == "REJECT"
    )
    gain = table["S0"]["REJECT"]["SUPPORT"] > table["S1"]["REJECT"]["SUPPORT"]
    return {
        "status": ("THRESHOLDS_MET_ONLY" if met else
                   "INCOMPLETE" if not complete else "THRESHOLDS_NOT_MET"),
        "gain": ("INCOMPLETE" if not complete else
                 "FEWER_FALSE_SUPPORTS_ON_SAMPLE" if gain else "NO_GAIN_OBSERVED"),
        "phase": phase, "expected_slots": len(slots), "physical_calls_reported": physical_calls,
        "table": table, "repetitions": repetitions, "support_losses_vs_s0": losses,
        "paired_negative_transitions": dict(sorted(paired_negatives.items())),
        "reference_status": "PROVISIONAL_AUTHOR_REVIEW_NOT_GOLD",
        "provenance_status": "NOT_VALIDATED_BY_THIS_TOOL",
        "authorization": "NOT_GRANTED_BY_THIS_TOOL",
        "p0_status": "OPEN",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "check"))
    parser.add_argument("--phase", choices=("A", "B", "C"), default="A")
    parser.add_argument("--records", type=Path)
    args = parser.parse_args()
    if args.action == "plan":
        result: Any = schedule(args.phase)
    else:
        if not args.records:
            parser.error("check requires --records")
        result = summarize(args.phase, _strict_load(args.records.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
