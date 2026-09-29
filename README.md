# CRIBA · BLACKFORGE · SUPRA

Canonical monorepo for the CRIBA / BLACKFORGE / SUPRA suite.

## Layout

- `criba-blackforge/` — CRIBA and BLACKFORGE component, imported with full Git ancestry from canonical commit `670f583479b78e7c276281d673a153d6071745c5`.
- `supra/` — SUPRA component, imported with full Git ancestry from canonical commit `95e01c36c32f4ce17a91c32ad7fa5d6cdfaea570`.
- `docs/migration/` — provenance and migration evidence.
- `.github/workflows/ci.yml` — monorepo-level component verification.

The components remain independently packaged. Monorepo does **not** mean monolith: each component keeps its own `pyproject.toml`, lockfile, tests and internal architecture.

## Canonical baseline

ASTRA workflow: `ASTRA-FIVE-TASKS-LOCAL`
Generation: `ASTRA4-20260928-G000002`
Library state at migration: `state_version=16`

See `docs/migration/SOURCE_CANON.md` for exact source identities and bundle hashes.
