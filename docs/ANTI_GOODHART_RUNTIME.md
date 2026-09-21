# Anti-Goodhart OFF + STANDARD runtime

Status: **implementation in progress; STANDARD disabled**.

This implementation follows the ASTRA binding contract:

- D is the decisional runtime. O is the observer domain.
- STANDARD writes only O and consumes a sealed, immutable, versioned public
  projection produced after the run.
- The observer is not imported by CRIBA engine, lottery, selection, prompts,
  OutcomeStore, or learning paths.
- Diagnostics, counters, hashes and observer failures have no decisional authority.
- UNKNOWN / NOT_EVALUATED are preserved and never interpreted as "no problem".
- Initial detectors are descriptive only: traceability integrity, descriptive
  distributions and record consistency. There is no aggregate Goodhart score.
- OPE remains research-only.

## Activation

STANDARD_ALLOWED is binary and scope-bound. The gate requires G1, G2, G3 and
G4, every applicable acceptance row, sensitivity controls and exact deployment
scope match.

This branch intentionally ships **no passing deployment gate evidence**.
governance/ANTI_GOODHART_STATUS.yaml therefore keeps STANDARD disabled.

G1/G2/G4 code-boundary sentinels can run in CI. G3 requires deployment evidence
that the observer worker has separate resources and cannot affect runtime
deadlines, retries, provider quotas, scheduling, locks or fallback. A thread or
process on the same machine is not sufficient evidence by itself.

## External worker

scripts/anti_goodhart_observer.py consumes a sealed trace after runtime
completion. OFF creates no observer state. STANDARD refuses to run unless the
provided gate evidence matches the exact scope fingerprint and all gates pass.

Human alerts are outside this initial implementation. When added, they must be
hidden during paired non-interference benchmarks and confirmatory evaluation,
or recorded as an explicit human intervention.
