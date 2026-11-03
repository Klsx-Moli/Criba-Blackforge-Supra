"""Build/check the operational catalog from preserved original adaptations.

This adds data to the existing catalog, not a second selector or scoring engine.
No paper/book body is redistributed; source metadata keeps its rights/reading limits.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATERIAL = ROOT / "docs/research/triz-inventiva"
OUTPUT = ROOT / "data/methods/sources/inventive_operators.json"

# Explicit, reviewable catalog metadata; not an inference of scientific validity.
THINKING_CLASSES = {
    "OP-TRIZ-01": "ruptura",
    "OP-TRIZ-02": "ruptura",
    "OP-TRIZ-03": "generacion",
    "OP-BIS-01": "perspectiva",
    "OP-BIS-02": "generacion",
    "OP-BIS-03": "escape",
    "OP-EXP-01": "escape",
    "OP-CRIT-01": "ruptura",
    "A3-OP-GEN-01": "perspectiva",
    "A3-OP-GEN-02": "ruptura",
    "A3-OP-GEN-03": "perspectiva",
    "A3-OP-BOD-01": "generacion",
    "A3-OP-BOD-02": "generacion",
    "A3-OP-BOD-03": "escape",
    "A3-OP-GPL-01": "generacion",
    "A3-OP-GPL-02": "perspectiva",
    "A3-OP-GPL-03": "ruptura",
    "A4-OP-MOR-01": "generacion",
    "A4-OP-MOR-02": "ruptura",
    "A4-OP-MOR-03": "escape",
    "A4-OP-CK-01": "perspectiva",
    "A4-OP-CK-02": "escape",
    "A4-OP-CK-03": "generacion",
    "A4-OP-FIX-01": "ruptura",
    "A4-OP-FIX-02": "ruptura",
    "A4-OP-FBS-01": "perspectiva",
    "A4-OP-DBA-01": "generacion",
}


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def build_records() -> list[dict[str, Any]]:
    groups = [
        (
            "triz_koestler",
            {
                "operators": _jsonl(MATERIAL / "operators/operators.jsonl"),
                "sources": _jsonl(MATERIAL / "sources/sources.jsonl"),
            },
        )
    ]
    for name in ("a3", "a4"):
        groups.append(
            (
                name,
                json.loads(
                    (MATERIAL / f"supplements/{name}/payload_{name}.json").read_text(
                        encoding="utf-8"
                    )
                ),
            )
        )
    result = []
    for group, payload in groups:
        sources = {source["source_id"]: source for source in payload["sources"]}
        for operator in payload["operators"]:
            ident = operator["operator_id"]
            steps = operator.get("transformation_steps")
            description = "\n".join(steps) if steps else operator["transformation"]
            result.append(
                {
                    "id": ident,
                    "name": ident,
                    "title": operator["title"],
                    "description": description,
                    "family": f"inventiva_{group}",
                    "thinking_class": THINKING_CLASSES[ident],
                    "granularity": "method",
                    "origin": "original_adaptation",
                    "source": group,
                    "operator_record": operator,
                    "source_records": [sources[source_id] for source_id in operator["source_ids"]],
                }
            )
    ids = [record["id"] for record in result]
    if len(ids) != len(set(ids)) or set(ids) != set(THINKING_CLASSES):
        raise ValueError("Operator IDs/classification must match without duplicates")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Create the catalog; refuse overwrite")
    args = parser.parse_args()
    records = build_records()
    if args.write:
        if OUTPUT.exists():
            raise FileExistsError("Refusing to overwrite an existing catalog")
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(
            json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    actual = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if actual != records:
        raise ValueError("Shipped operational catalog differs from preserved inputs")
    print(
        json.dumps(
            {
                "catalog": str(OUTPUT.relative_to(ROOT)),
                "operators": len(records),
                "semantic_equality": True,
                "scientific_benefit": "NOT_ESTABLISHED",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
