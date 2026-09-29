# ASTRA Anti-Goodhart Entry Gate

Authority: ASTRA  
Decision: `ASTRA_BASE_READY_AFTER_LISTED_FIXES`

This file is operational guidance for the future Anti-Goodhart runtime. It does
not implement that runtime.

## Preconditions before enabling STANDARD

### G1 — Common corrected base

- OFF and STANDARD preserve the same mandatory ASTRA contracts.
- OFF disables additional observation only; it does not disable base integrity.
- The corrected base is versioned.
- Historical baselines and negative evidence remain preserved.

### G2 — Separation of effects

STANDARD may observe but MUST NOT modify:

- decision state;
- shared RNG state or consumption;
- candidate set;
- score/order/finalists;
- memory or priors;
- decision-relevant caches;
- prompts;
- retrievable product corpus;
- learning updates;
- future automated decisions.

Diagnostics never feed generation, selection or learning.

### G3 — Temporal non-interference

Observer cost, failure, persistence and diagnostic volume MUST NOT modify:

- retries;
- budgets;
- deadlines;
- fallback;
- provider call opportunities;
- later decision timing semantics.

If that isolation is not demonstrated for a route, STANDARD remains disabled on
that route.

### G4 — Trajectory verification

With identical controlled external inputs and replayed external responses:

`OFF current -> next -> restart -> next`

must equal

`STANDARD current -> next -> restart -> next`.

Required adversarial cases include:

- observer failure;
- duplicated diagnostics;
- zero diagnostics;
- large diagnostic volume;
- restart;
- replay.

Human-visible alerts can alter future external inputs. In confirmatory trials
they must be deferred or explicitly treated as an intervention.

## MUST_PROMOTE from research before/with runtime work

Promote contracts and reusable tests only, not whole research branches:

1. field-level lineage and access rules for generation/selection/learning/evaluation;
2. production-path sentinels for contamination, duplicate inflation and state promotion;
3. effective-decision logging: initial selection, substitutions, discards and final result;
4. verdict semantics separating contractual failure, invalid execution,
   NOT_EVALUATED and scientifically unresolved conclusions;
5. non-interference tests required by G1-G4.

## MUST_REMAIN_RESEARCH_ONLY

Do not promote as product conclusions:

- D3 external novelty claims from negative retrieval or local scores;
- D4 functional diversity from distance/category/family/quota alone;
- D6 adaptive attribution/back-off/UCB/OPE as demonstrated beneficial learning;
- D8 judge/consensus/score as independently validated evaluation without controls;
- hidden-evaluation labels/corpora/results into product runtime or feedback;
- development pilots/replays/integrity tests as confirmatory evidence;
- any claim of `CRIBA_ADVANTAGE_SUPPORTED`.

Current status remains:

- `D3_NOVELTY = UNRESOLVED`
- `D4_FUNCTIONAL_DIVERSITY = UNRESOLVED`
- `D6_ADAPTIVE_BENEFIT = STILL_UNRESOLVED`
- `SCIENTIFIC_ADVANTAGE_OF_CRIBA = NOT_ESTABLISHED`

## Binding implementation order

1. stable event identity and semantic states;
2. historical revalidation + invalidation of incompatible derived state;
3. consumers preserve meaning end-to-end;
4. version the corrected base;
5. production-path sentinels;
6. build isolated observer;
7. multi-decision + restart replay;
8. enable STANDARD only after G1-G4 pass.

Building the observer before G4 is allowed in isolation. Product activation is not.
