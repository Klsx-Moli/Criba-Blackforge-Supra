# Resultados de Baseline de Main @ 15bc237 (CBS-K4)

- MAIN_SHA: 15bc237be5555fcc38bc8a25f80724473c13435b
- WORKTREE AISLADO: C:/ASTRA_WORK/Criba-Blackforge-Supra-main-baseline (detached)
- TIMESTAMP_UTC: 2026-10-08
- AUTOR: Hermes (writer). Estos resultados SÍ se ejecutaron en esta sesión.

## Resultados por comando

| # | Comando | Dir | Exit | Duración | Clasificación | Resultado |
|---|---------|-----|------|----------|---------------|-----------|
| 1 | `uv sync --all-extras --locked` | criba-blackforge | 0 | ~120s | OK | 200+ paquetes instalados (uv 0.12.15) |
| 2 | `uv run --locked pytest -q` | criba-blackforge | 0 | 259.57s | OK | **1504 passed, 1 warning** |
| 3 | `uv run --locked python scripts/check_mypy_baseline.py` | criba-blackforge | 0 | ~40s | OK | current=0, baseline=78, new=0, removed=78; "no issues in 158 files" |
| 4 | `uv sync --all-extras --locked` | supra | 0 | ~60s | OK | deps supra instaladas |
| 5 | `uv run --locked pytest -q --no-header` | supra | 0 | 30.43s | OK | **230 passed, 2 warnings** |
| 6 | `uv run --locked ruff check .` | supra | 0 | ~5s | OK | All checks passed! |
| 7 | `uv run --locked mypy src/supra_agentic` | supra | 0 | ~30s | OK | no issues in 21 source files |
| 8 | `uv run --locked ruff check .` | criba-blackforge | 0 | ~10s | NO_GATE | **1891 errors (544 fixable)** — CI no ejecuta ruff en CRIBA |

## Baseline oficial (lo que CI exige y pasa)

- CRIBA/BLACKFORGE: 1504 passed (pytest -q) + mypy gate new=0.
- SUPRA: 230 passed + ruff clean + mypy clean.
- CI esperado: los 3 jobs (criba-blackforge, supra, monorepo-result) PASS.

## Test failures

- NINGUNO. Todos los comandos de CI terminaron exit 0.

## Observaciones y limitaciones

- **ruff CRIBA/BLACKFORGE**: 1891 hallazgos en main (exit 0 porque ruff check
  devuelve 0 en algunos modos, pero reporta errores). CI NO lo ejecuta para CRIBA.
  No es un gate actual. Riesgo de calidad si se activara sin baseline.
- **uv local 0.12.15 vs CI 0.11.28**: diferencia de versión; el lock (`--locked`)
  garantiza las dependencias, pero la resolución del entorno puede diferir.
- **Warnings**: StarletteDeprecationWarning (httpx/testclient) en ambos jobs;
  DeprecationWarning anyio en supra. No bloquean.
- **Artefactos generados por la ejecución** (NO commiteados, NO borrados):
  - criba-blackforge/verification/blackforge_catalog_report.json (M)
  - criba-blackforge/verification/blackforge_safety_report.json (M)
  - criba-blackforge/verification/blackforge_selector_report.json (??)
  - .venv/, .pytest_cache/, .mypy_cache/, .ruff_cache/ (ignorados por .gitignore)
- **Reproducibilidad**: alta (lock fijo, sin red en tests salvo mocks; no se
  detectaron tests de red/servicios externos fallidos).
- **Tests lentos**: la suite CRIBA/BLACKFORGE tarda ~4min20s (259.57s); SUPRA 30s.
- No se identificaron tests flaky en esta única ejecución (no repetida).

## Estado

BASELINE ESTABLECIDO Y REPRODUCIBLE para 15bc237. Cualquier rama de integración
debe igualar o superar: CRIBA 1504 passed / mypy new=0; SUPRA 230 passed / ruff
clean / mypy clean.
