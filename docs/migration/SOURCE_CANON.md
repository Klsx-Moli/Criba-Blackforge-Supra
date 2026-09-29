# Source canon and provenance

This monorepo was assembled from the exact canonical Library bundles, not from the older GitHub mirrors.

## CRIBA / BLACKFORGE

- Source commit: `670f583479b78e7c276281d673a153d6071745c5`
- Source ref: `refs/heads/astra4-g1-criba-e1`
- Source bundle SHA256: `adbdbc21559342755fc4722364759b2bd18383a29e52539992b0d86a3cdfcd6a`
- Imported path: `criba-blackforge/`

## SUPRA

- Source commit: `95e01c36c32f4ce17a91c32ad7fa5d6cdfaea570`
- Source ref: `refs/heads/astra4-g2-supra-e1`
- Source bundle SHA256: `41385b418a00104b11255a6400470a0b06d9d9dc3853e9df8a7b5e98afd66bee`
- Imported path: `supra/`

## ASTRA identity

- Workflow: `ASTRA-FIVE-TASKS-LOCAL`
- Generation: `ASTRA4-20260928-G000002`
- Library state at migration: `state_version=16`

## Migration invariants

1. Both source commits must remain ancestors of the monorepo HEAD.
2. File trees below `criba-blackforge/` and `supra/` must match the corresponding canonical source trees at import time.
3. Source component histories are retained; no squash import was used.
4. No source repository is deleted or rewritten by this migration.
5. `main` must never be force-pushed as part of normal continuation.
