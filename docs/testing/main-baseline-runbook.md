# Runbook de Baseline de Main (CBS-K4)

- MAIN_SHA: 15bc237be5555fcc38bc8a25f80724473c13435b
- TIMESTAMP_UTC: 2026-10-08
- AUTOR: Hermes (writer; comandos localizados en archivos reales del repo)
- Regla: ningún comando inventado. Cada uno lleva su fuente y estado.

## Tabla de comandos

| Acción | Comando exacto | Fuente | Requisitos | Riesgo | Estado |
|--------|----------------|--------|-----------|--------|--------|
| Entorno (CRIBA/BLACKFORGE) | `uv sync --all-extras --locked` | .github/workflows/ci.yml L39 (job criba-blackforge, working-directory criba-blackforge) | uv; uv.lock presente | Bajo | VERIFIED_FROM_REPO |
| Entorno (SUPRA) | `uv sync --all-extras --locked` | .github/workflows/ci.yml L70 (job supra) | uv; supra/uv.lock | Bajo | VERIFIED_FROM_REPO |
| Tests CRIBA/BLACKFORGE | `uv run --locked pytest -q` | .github/workflows/ci.yml L42 | deps instaladas | Medio (suite larga ~4min) | VERIFIED_FROM_REPO |
| mypy gate CRIBA/BLACKFORGE | `uv run --locked python scripts/check_mypy_baseline.py` | .github/workflows/ci.yml L45 | deps + ci/mypy_baseline.json | Bajo | VERIFIED_FROM_REPO |
| Tests SUPRA | `uv run --locked pytest -q --no-header` | .github/workflows/ci.yml L73 | deps supra | Bajo | VERIFIED_FROM_REPO |
| Lint SUPRA | `uv run --locked ruff check .` | .github/workflows/ci.yml L76 | deps supra | Bajo | VERIFIED_FROM_REPO |
| Type-check SUPRA | `uv run --locked mypy src/supra_agentic` | .github/workflows/ci.yml L79 | deps supra | Bajo | VERIFIED_FROM_REPO |
| Lint CRIBA/BLACKFORGE | `uv run --locked ruff check` | .pre-commit-config.yaml L7 (hook local ruff) | deps | Medio (1891 hallazgos en main) | DERIVED_FROM_REPO |
| Format CRIBA/BLACKFORGE | `uv run --locked ruff format --check` | .pre-commit-config.yaml L13 | deps | Bajo | DERIVED_FROM_REPO |
| Cobertura CRIBA/BLACKFORGE | (pytest-cov está en dev deps; sin config de umbral en CI) | pyproject.toml L49; ci.yml no lo invoca | — | — | DERIVED_FROM_REPO (sin umbral) |
| Python CI | 3.11 | ci.yml L31/L61 | — | — | VERIFIED_FROM_REPO |
| Python soportado | >=3.10 | pyproject.toml L10 | — | — | VERIFIED_FROM_REPO |
| mypy python_version | 3.12 | pyproject.toml L115 | — | — | VERIFIED_FROM_REPO |
| uv CI | 0.11.28 | ci.yml L34/L64 | — | — | VERIFIED_FROM_REPO |

## Notas de descubrimiento

- NO existen `Makefile`, `tox.ini`, `noxfile.py`, `pytest.ini`, `requirements.txt`
  (solo `requirements-optional.txt`). Localizado con `ls`.
- pytest se configura en `pyproject.toml` `[tool.pytest.ini_options]` (pythonpath).
- ruff config en `pyproject.toml` `[tool.ruff]`.
- mypy config en `pyproject.toml` `[tool.mypy]` (strict; excluye gui/ui).
- mutmut configurado para `src/criba/personas.py` (no gate CI).
- `scripts/check_mypy_baseline.py` compara contra `ci/mypy_baseline.json` (78).

## Servicios/fixtures

- No se detectaron servicios externos requeridos por CI (runs-on: windows-2025,
  solo uv + pytest + mypy). Los tests SUPRA usan TestClient en proceso.
- Advertencia: el job CRIBA/BLACKFORGE de CI NO ejecuta ruff (solo supra lo hace).

## Limitación local

- uv local observado: 0.12.15 (CI fija 0.11.28). Diferencia de versión a tener
  en cuenta para reproducibilidad exacta.
