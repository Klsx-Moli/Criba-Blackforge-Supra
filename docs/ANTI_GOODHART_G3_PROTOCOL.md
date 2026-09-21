# Anti-Goodhart G3 deployment-isolation protocol

Authority: ASTRA  
Target: SUPRA  
Public trace schema: `astra-supra-public-trace/1`

## Purpose

This protocol is the **only remaining deployment gate** after code-boundary G1/G2/G4
sentinels. It does not test whether diagnostics are useful. It tests whether the
observer can change decisional timing/resources.

Passing this protocol **does not edit** `STANDARD_RELEASE_STATE`. Product
STANDARD remains disabled until a separate reviewed/versioned release commit.

## Required topology

D (decisional runtime) and O (observer) MUST have distinct resource-domain
identities. A Python thread or sibling process on the same unconstrained host
does not establish G3.

Evidence must identify, at minimum:

- D resource-domain id;
- O resource-domain id;
- CPU/memory limits for each domain;
- storage paths/devices used by each domain;
- network/provider credentials and quotas available to each domain;
- locks, DB pools, queues and schedulers accessible to each domain;
- exact D commit, O commit, trace schema and detector versions.

If any lock, connection pool, provider quota, retry budget, deadline scheduler
or decisional persistence path is shared, G3 is **NOT_VERIFIED** unless the
experiment demonstrates by construction that O cannot consume or block it.

## Paired experiment

Use identical frozen external inputs and dependencies.

For each scenario run a paired OFF/control and observer-stress trajectory.

Record:

- semantic trajectory digest (excluding observational artifacts);
- candidate/order/selected result where applicable;
- fallback and retry decisions;
- decisional persisted-state digest;
- start/deadline/fallback timestamps;
- D wall time and provider-call accounting;
- O wall time and failures separately.

Required perturbations:

1. observer absent;
2. observer exception;
3. observer storage failure;
4. duplicate diagnostic delivery;
5. diagnostic payload 1x vs 100x;
6. observer artificial latency;
7. observer timeout/termination;
8. observer CPU saturation;
9. observer memory pressure within O limit;
10. observer restart;
11. persisted O diagnostics present before a subsequent D decision;
12. changed observer RNG/process seed;
13. two consecutive D decisions;
14. fallback path in D.

## Pass condition

For every applicable row:

- D semantic trajectory is identical;
- D retry/fallback/budget decisions are identical;
- D persisted decisional state is identical;
- O artifacts never appear in D prompts, memory, priors, caches or retrieval;
- O failures do not propagate to D;
- any D timing delta remains within a **pre-registered measurement tolerance**
  justified by measurement noise, not selected after observing results;
- sensitivity control deliberately mutating one D field is detected.

The tolerance itself is not evidence of scientific benefit and must be recorded
before the benchmark.

## Automatic fail / revoke

G3 is NOT_VERIFIED (or a previous allowance is revoked) if:

- any applicable row is skipped;
- resource-domain identity is missing;
- D and O unexpectedly share a protected resource;
- semantic trajectory differs;
- O changes retry, fallback, budget, deadline or future decision;
- comparator misses the deliberate contamination control;
- deployment/code/schema/detector scope changes after evidence was collected.

## Output artifact

The local harness/report should produce JSON containing:

```json
{
  "gate": "G3",
  "status": "PASS|FAIL|NOT_VERIFIED",
  "d_scope": {},
  "o_scope": {},
  "scope_fingerprint": "...",
  "pre_registered_tolerance": {},
  "rows": [],
  "sensitivity_control_pass": false,
  "standard_release_state": "DISABLED"
}
```

No generated report is allowed to set product activation.


## Local same-host probe

The repository includes a verification-only probe. It exercises the O-domain
worker after a completed D run and applies these perturbations:

- normal observer run;
- duplicate delivery;
- 100 diagnostics;
- detector exception;
- observer storage failure;
- artificial observer latency;
- observer restart.

Run from the repository root:

```powershell
uv run python scripts/anti_goodhart_g3_probe.py --output "verification/anti_goodhart_g3_supra.json"
```

Expected safe outcome on one machine:

- `FAIL` means semantic trajectory interference or a broken sensitivity control.
- `NOT_VERIFIED` means no semantic interference was detected, but same-host
  subprocess execution is insufficient to accredit G3.
- The probe can never emit `PASS`.
- The probe can never edit `STANDARD_RELEASE_STATE`.
- The report is written to `verification/anti_goodhart_g3_supra.json`.

Do not interpret `NOT_VERIFIED` as failure of the implementation. It means the
remaining evidence must come from a genuinely separate resource domain or an
equivalent deployment topology satisfying this protocol.
