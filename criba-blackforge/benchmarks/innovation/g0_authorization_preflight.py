"""Read-only reconciliation of G0 artifacts and decision dependencies.

No inference, source modifications, credential reads, digital signatures, or
owner approval. A passing artifact hash is consistency, not scientific truth.
This checker NEVER grants G0, B/C escalation, deployment, or a runtime permit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

# Pinned effective artifact hashes (raw bytes, not Git object hashes).
# A new generation requires a new explicit decision/version, not silent repair.
_EFFECTIVE = {
    "criba-blackforge/benchmarks/innovation/semantic_lab.py":
        "e0692a16559309e34a47af4c6dd8987695df1d978c2da6cd1d0956ae40623ca6",
    "criba-blackforge/benchmarks/innovation/semantic_cases.py":
        "af9e945eaa558d28be9a123d63c59380b11636bbff28dd389b46d048415aedfa",
    "docs/research/semantic-correspondence/g0-draft/pilot_cases.json":
        "fad4b6fc0ac3a421d3475864ed7daef37be38cfa03c3551c7ff5b46a234c4c14",
    "docs/research/semantic-correspondence/g0-draft/pilot_gate.py":
        "69d1d283b2be5cb9334a8c4c46416fe7d42a4667572a3a69c1858c402a276abe",
}
_GATE_DIR = "docs/research/semantic-correspondence/g0-draft"
_DEVELOPMENT_COUNTS = {"SUPPORT": 5, "REJECT": 11, "UNRESOLVED": 2}
_REQUIRED_DECISIONS = (
    "scientific_scope", "independent_references", "independent_reviewers",
    "fair_s0_s1_contract", "s0_outcome_mapping", "model_identity",
    "runtime_and_inference_settings", "effective_tokenization", "no_retry_transport",
    "physical_attempt_accounting", "phase_a_budget", "owner_approval",
    "explicit_inference_permission",
)


def _strict_json(raw: str) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("duplicate JSON key")
            out[key] = value
        return out

    def no_nonfinite(_value: str) -> Any:
        raise ValueError("nonfinite JSON")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=no_nonfinite)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _artifact_checks(root: Path) -> dict[str, dict[str, str | None]]:
    checks = {}
    for name, expected in _EFFECTIVE.items():
        path = root / name
        try:
            raw = path.read_bytes()
            observed = _sha(raw)
            result = "EXACT" if observed == expected else "CHANGED"
        except OSError:
            observed, result = None, "NOT_ACCESSIBLE"
        checks[name] = {"status": result, "expected_sha256": expected,
                        "observed_sha256": observed}
    return checks


def inspect(
    root: Path, *, purported_approval: Mapping[str, Any] | None = None,
    phase06_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fail closed while preserving an auditable, strictly limited diagnosis.

    A user-provided file/claim is never treated as a verified authorization:
    this tool has no authority to authenticate a signer or approve scientific
    claims. Phase06 data is context, never permission to ignore its blockers.
    """
    artifacts = _artifact_checks(root)
    all_exact = all(x["status"] == "EXACT" for x in artifacts.values())
    issues: list[str] = []
    for path, entry in artifacts.items():
        if entry["status"] != "EXACT":
            issues.append("FROZEN_ARTIFACT_" + entry["status"] + ":" + path)
    manifest = None
    integrity = "NOT_VERIFIED"
    sample = {"selected": None, "root_problems": None,
              "labels": None, "schedule_slots": None}
    if all_exact:
        try:
            from benchmarks.innovation import semantic_cases, semantic_lab
            import runpy

            required_paths = (
                root / "criba-blackforge/benchmarks/innovation/semantic_cases.py",
                root / "criba-blackforge/benchmarks/innovation/semantic_lab.py",
            )
            active_paths = (Path(semantic_cases.__file__), Path(semantic_lab.__file__))
            if any(a.resolve() != b.resolve() for a, b in zip(
                    active_paths, required_paths, strict=True)):
                raise ValueError("executing different package from pinned artifacts")
            manifest = _strict_json((root / _GATE_DIR / "pilot_cases.json").read_text(
                encoding="utf-8"))
            if (not isinstance(manifest, dict) or
                    set(manifest) != {"status", "reference_status", "columns", "cases"} or
                    manifest["status"] != "DRAFT_NOT_APPROVED" or
                    manifest["reference_status"] != "PROVISIONAL_AUTHOR_REVIEW_NOT_GOLD" or
                    manifest["columns"] != ["case_id", "reference", "case_sha256"]):
                raise ValueError("manifest metadata inconsistent")
            rows = manifest["cases"]
            if not isinstance(rows, list) or len(rows) != 18:
                raise ValueError("manifest size inconsistent")
            development = {r["id"]: r for r in semantic_cases.cases()}
            if len(development) != 58:
                raise ValueError("laboratory development version inconsistent")
            seen: set[str] = set()
            refs = Counter()
            roots: set[str] = set()
            for row in rows:
                if (not isinstance(row, list) or len(row) != 3 or
                        not all(isinstance(value, str) for value in row)):
                    raise ValueError("invalid manifest row")
                case_id, label, raw_digest = row
                if case_id in seen or case_id not in development:
                    raise ValueError("duplicate or unknown development ID")
                seen.add(case_id)
                actual = development[case_id]
                if (actual["reference"] != label or
                        semantic_lab.digest(actual) != raw_digest or
                        actual["split"] != "development" or
                        actual["reference_status"] != "PROVISIONAL_AUTHOR_REVIEW_NOT_GOLD"):
                    raise ValueError("development content/reference digest mismatch")
                roots.add(actual["parent_id"])
                refs[label] += 1
            if dict(refs) != _DEVELOPMENT_COUNTS or len(roots) != 3:
                raise ValueError("unexpected label mix or problem roots")
            gate = runpy.run_path(str(root / _GATE_DIR / "pilot_gate.py"))
            if gate["references"]() != {row[0]: row[1] for row in rows}:
                raise ValueError("gate and effective references diverge")
            phases = {name: gate["schedule"](name) for name in ("A", "B", "C")}
            expected_a = {
                "CBS500-01-01:" + v for v in (
                    "aligned", "incident", "incident-lexical", "metric",
                    "transfer", "unknown"
                )
            } | {"CBS500-09-02:aligned", "CBS500-21-01:transfer"}
            expected_b = {(cid, 0, arm) for cid in seen for arm in ("S0", "S1")}
            expected_c = {(cid, rep, arm) for cid in seen
                          for rep in (0, 1, 2) for arm in ("S0", "S1")}
            observed_a = {(r["case_id"], r["repetition"], r["arm"])
                          for r in phases["A"]}
            observed_b = {(r["case_id"], r["repetition"], r["arm"])
                          for r in phases["B"]}
            observed_c = {(r["case_id"], r["repetition"], r["arm"])
                          for r in phases["C"]}
            if ([len(phases[k]) for k in ("A", "B", "C")] != [16, 36, 108] or
                    phases["A"] != phases["B"][:16] or
                    phases["B"] != phases["C"][:36] or
                    observed_a != {(cid, 0, arm) for cid in expected_a
                                   for arm in ("S0", "S1")} or
                    observed_b != expected_b or observed_c != expected_c):
                raise ValueError("schedule identity or prefix drift")
            sample = {"selected": 18, "root_problems": 3,
                      "labels": dict(refs),
                      "schedule_slots": {k: len(v) for k, v in phases.items()}}
            integrity = "CONSISTENT_DEVELOPMENT_ONLY"
        except (KeyError, TypeError, ValueError, OSError, ImportError, IndexError,
                UnicodeError, RecursionError) as exc:
            integrity = "FAILED"
            # No case IDs, reference labels, model secrets or stack traces
            # belong in the public status report.
            issues.append("CASE_MANIFEST_OR_GATE_INCONSISTENT")
    else:
        issues.append("CASE_MANIFEST_NOT_RECONCILED")
    if purported_approval is not None:
        issues.append("PURPORTED_APPROVAL_NOT_AUTHENTICATED")
    if phase06_report is not None:
        if (not isinstance(phase06_report, Mapping) or
                phase06_report.get("status") != "BLOCKED" or
                phase06_report.get("authorization") != "NOT_GRANTED_BY_PREFLIGHT"):
            issues.append("PHASE06_CLAIM_NOT_CREDIBLE")
    # These are scientific/operational blockers, not artifacts that a source
    # checksum, perfect synthetic outcome or editable local JSON can satisfy.
    issues.extend((
        "S0_S1_INFORMATION_NOT_COMPARABLE", "S0_OUTCOME_MAPPING_NOT_VALIDATED",
        "INDEPENDENT_REFERENCE_NOT_ADJUDICATED", "THREE_REVIEWERS_NOT_VERIFIED",
        "PHYSICAL_MODEL_IDENTITY_NOT_ATTESTED", "PRODUCTION_ZERO_RETRY_NOT_WIRED",
        "PHYSICAL_ATTEMPTS_NOT_PROVIDER_CERTIFIED", "OWNER_G0_DECISION_NOT_AUTHENTICATED",
        "INFERENCE_PERMISSION_NOT_GRANTED",
    ))
    matrix = {name: "UNVERIFIED_OR_UNDECIDED" for name in _REQUIRED_DECISIONS}
    matrix["scientific_scope"] = (
        "PROPOSED_DEVELOPMENT_DIAGNOSTIC" if integrity.startswith("CONSISTENT")
        else "INTEGRITY_PENDING")
    return {
        "decision": "NO_GO", "authorization": "NOT_GRANTED_BY_THIS_TOOL",
        "g0_status": "DRAFT_NOT_APPROVED", "p0_semantic": "OPEN",
        "scientific_advantage": "NOT_ESTABLISHED", "source_trust": "DEVELOPMENT_ONLY",
        "artifact_integrity": artifacts, "case_manifest_integrity": integrity,
        "sample": sample, "decisions": matrix,
        "pilot_gate": "THRESHOLDS_ONLY_NOT_AUTHORIZATION",
        "phase_A": "NOT_AUTHORIZED", "phase_B": "NOT_AUTHORIZED",
        "phase_C": "NOT_AUTHORIZED", "provider_consumption": None,
        "issues": sorted(set(issues)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3],
                        help="Repository root; read-only, no external services")
    args = parser.parse_args()
    print(json.dumps(inspect(args.root.resolve()), ensure_ascii=False, indent=2,
                     sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
