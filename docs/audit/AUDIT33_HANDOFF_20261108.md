# AUDIT /33 — handoff reproducible para Hermes (2026-11-08)

**ESTADO: AUDITORÍA NO AGOTADA / CORRECCIONES EN VALIDACIÓN.** Este documento no acredita un PASS completo ni la aplicación local.

## Identidad y límites

- Repo: `Klsx-Moli/Criba-Blackforge-Supra`.
- Base remota comprobada: `main@5978d33b2fcd23def901ba96b855036f0203cd39`.
- Corrección anterior, sin tocar por esta auditoría: `fix/ci-green-20261106@15051af99e2d0f6cb8b5a89a6af8de1b07d54f72` (tres commits por delante de main, cero detrás).
- Rama aislada de esta auditoría: `chatgpt/audit33-ci-contracts-20261108`, descendiente de la corrección anterior.
- Ningún merge a `main`, force-push, borrado, release, gasto ni modificación del motor ASTRA por esta auditoría.
- El checkout Windows y sus worktrees/WIP no son accesibles desde este entorno: **NOT_ACCESSIBLE**; no asumir clean local.
- Código remoto consultado mediante conector GitHub. Reproducciones Python local/full suite: **NOT_EXECUTED** hasta confirmar el CI de esta PR.

## Evidencia de la línea base

- `main` Monorepo CI run `41715328720` (2026-11-03): **FAIL**. Windows/Linux CRIBA fallaron al leer un snapshot histórico no versionado:
  `docs/research/triz-inventiva/evidence/resume_20261028/before/criba-blackforge/src/criba/lottery.py` desde `test_imp10_proposal.py`. SUPRA: tres incidencias Ruff.
- Rama previa `fix/ci-green-20261106`: Monorepo CI run `42143268287` (2026-11-06): **SUCCESS** en CRIBA Windows, Linux informativo, SUPRA y agregador.
- La rama previa añadió `pytest.mark.skipif(not EVIDENCE_BUNDLE.is_dir())` al test IMP-10 histórico; el bundle no está versionado. Esto **no reproduce** por sí mismo la comparación byte-exacta con baseline.
- `tests/unit/test_lossless_operations_contract.py` prueba material completo/escaping, pero antes de esta auditoría NO comparaba replay de RNG ni identidad/score de dos ejecuciones. Se añadieron sentinels metamórficos, no se afirmó equivalencia histórica byte-exacta.
- El workflow `.github/workflows/ci.yml` marca Linux como `continue-on-error: true` y el agregador solo depende de CRIBA Windows y SUPRA; un verde del agregador no garantiza Linux. La rama previa sí obtuvo éxito individual de Linux en run 133.
- El gate `anti-goodhart.yml` solo se dispara en PR y push a main, NO en push de rama de corrección. Una PR draft es necesaria para observarlo aquí.

## Hallazgo A — P2: refinamiento aceptaba JSON contrario a su propio esquema

- **STATICALLY_INSPECTED**, contrato: `criba-blackforge/src/criba/interprete/refinamiento.py` publica `REFINEMENT_SCHEMA` con `type:string`, `maxLength`, `maxItems` y `additionalProperties:false`.
- Antes: `validar_protocolo` usaba `_texto` que convertía `False`/números en cadenas, aceptaba arrays por encima del máximo y descartaba silenciosamente campos desconocidos anidados de `prueba_brazos`.
- Impacto: `parse_refinement` podía marcar `PROTOCOLO` algo que el esquema ofrecido al modelo y consumidores prohíbe. La verificación científica no se promovía, pero el dato de contrato sí era falso.
- **Fix aislado**: validar tipos, longitudes, cantidad de elementos y claves anidadas contra el mismo `REFINEMENT_SCHEMA`, sin completar secciones, sin normalizar valores falsos a texto. Errores sin eco de contenido sensible.
- **Regression sentinels** en `tests/unit/test_refinamiento.py`: booleanos y números, `maxLength`, `maxItems`, valores no string dentro de arrays, claves extras y límites válidos.
- Riesgo a verificar: compatibilidad con modelos que devuelvan JSON mal tipado; comportamiento esperado es `PENDIENTE`, no validación silenciosa.

## Hallazgo B — P2: cobertura parcial de IMP-10 tras reemplazar snapshot ausente

- **STATICALLY_INSPECTED**: `test_imp10_proposal.py` conserva asserts de before/after, RNG, score, identidad y diff exacto pero queda omitido cuando falta el bundle histórico.
- **Fix aislado**: se amplía el test productivo `test_lossless_operations_contract.py` con replay mismo seed, igualdad completa de ideas, identidad explícita y no consumo adicional de RNG al construir prompt.
- **Límite**: replay vs misma versión NO prueba igualdad con score/JSON de la versión histórica no disponible. No eliminar este `UNKNOWN`; recuperar y versionar fixture histórico solo después de comprobar licencias/datos y autorización pertinente.

## Cobertura /33 honesta

| Paso | Estado |
|---|---|
| P1 Git/baseline/scope | VERIFIED remoto; checkout local NOT_ACCESSIBLE |
| P2 arquitectura/runtime | STATICALLY_INSPECTED parcial (CRIBA intérprete/lotería y SUPRA servicio/estado) |
| P3 esquemas/contratos | STATICALLY_INSPECTED, defecto reproducible por razonamiento de código |
| P4 verdad de tests | STATICALLY_INSPECTED; sentinels añadidos |
| P5 UI→backend→disco | NOT_EXECUTED E2E |
| P6 retry/cache/restart/replay | STATICALLY_INSPECTED parcial; Linux/Windows ejecución general previa no cubre semántica total |
| P7 CLI/API/MCP/exportadores | NOT_EXECUTED E2E |
| P8 CI/seguridad | VERIFIED_BY_GITHUB_ACTIONS CI observada; rama protection/secret scan EVIDENCE_PENDING |
| P9 docs/claims | STATICALLY_INSPECTED: las pruebas omitidas no deben contarse como equivalentes |
| P10 mutaciones | Parcial (tipos, arrays, nested fields, límites, RNG/replay); pendiente matriz completa |
| P11 transversales | Parcial; validar consumidores de protocolos |
| P12 research/histórico | Parcial; IMP-10 bundle ausente y PRs históricos revisados |
| P13 re-scan adversarial | PENDIENTE tras CI y cambios |

**G0 del Art. 26**: este lote es habilitante para G1/contratos; no modifica motor inventivo, distribución de puntuaciones ni claims N2/N3.

## Comprobación para Hermes

En checkout/revisión aislada, sin instalar servicios ni llamar modelos:

```powershell
cd criba-blackforge
uv sync --all-extras --locked
uv run --locked pytest -q tests/unit/test_refinamiento.py tests/unit/test_lossless_operations_contract.py tests/unit/test_retry_ledger.py
uv run --locked pytest -q
uv run --locked python scripts/check_mypy_baseline.py
uv run --locked ruff check src scripts tests shadow_ui criba_shadow_main.py --select E9,F63,F7,F82,F601,F811,B023
cd ../supra
uv sync --all-extras --locked
uv run --locked pytest -q --no-header
uv run --locked ruff check .
uv run --locked mypy src/supra_agentic
```

Antes de marcar PASS, comprobar PR checks Monorepo CI y Anti-Goodhart y ejecutar refutación por mutación contra los tests añadidos. No sustituir pruebas ejecutadas por descripciones de este archivo. No tocar motor ASTRA ni efectuar merge a main.

## LOCAL_SYNC_PLAN (sin tocar checkout actual)

```powershell
cd C:\ASTRA_WORK\Criba-Blackforge-Supra
git status --short
git worktree list
git fetch origin
git show --no-patch --oneline origin/chatgpt/audit33-ci-contracts-20261108
# Elegir una ruta NUEVA, que no exista, fuera de carpetas protegidas:
git worktree add ..\cbs-audit33-review-20261108 --detach origin/chatgpt/audit33-ci-contracts-20261108
cd ..\cbs-audit33-review-20261108
git status --short
git log --oneline --max-count=8
```

Si hay WIP en el checkout original, NO ocultarlo ni arrastrarlo: el worktree aislado conserva esos ficheros donde están. No usar `reset`, `clean`, `--force`, `stash pop` automático ni `pull` sobre un checkout sucio. Tras revisión/gates y autorización explícita: AUDITAR → REPARAR → VERIFICAR → PUSH → SINCRONIZAR LOCAL → VERIFICAR LOCAL.
