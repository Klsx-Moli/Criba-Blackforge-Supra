# Monorepo migration verification — 2026-09-29

## Identity

- CRIBA source commit: `670f583479b78e7c276281d673a153d6071745c5`
- CRIBA subtree tree SHA: `3c7a1f59f2f2800525e9f88277f4696216c78ce0`
- CRIBA source tree SHA: `3c7a1f59f2f2800525e9f88277f4696216c78ce0`
- CRIBA tree identity: **PASS**
- SUPRA source commit: `95e01c36c32f4ce17a91c32ad7fa5d6cdfaea570`
- SUPRA subtree tree SHA: `861fbfe00819126997a0e7f3da60153e5aea5170`
- SUPRA source tree SHA: `861fbfe00819126997a0e7f3da60153e5aea5170`
- SUPRA tree identity: **PASS**
- Both source commits are ancestors of the monorepo HEAD: **PASS**

## Executed in migration runtime

- CRIBA G000002 contract/integration selection: **68 passed**.
- SUPRA full suite: **215 passed**.
- Python compileall over both source trees: **PASS**.
- Migration wiring commit `git diff --check`: **PASS**.
- Working tree after verification: **CLEAN**.

## Runtime qualification

An initial SUPRA run without `PYTHONPATH=src` produced one failure in the multiprocess observer sentinel because subprocess children could not import the package. The exact same failure reproduced in the original SUPRA checkout. Re-running the monorepo SUPRA suite with `PYTHONPATH=src` passed all 215 tests, so the failure was refuted as a migration regression.

The imported component source trees were not modified to achieve these results.
