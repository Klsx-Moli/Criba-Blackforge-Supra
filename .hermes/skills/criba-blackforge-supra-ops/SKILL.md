# CRIBA / BLACKFORGE / SUPRA — KLSX operativo

## Dónde vive todo
- **Monorepo canónico (ÚNICA fuente operativa):** `Klsx-Moli/Criba-Blackforge-Supra`.
  `criba-blackforge/` y `supra/` son componentes dentro del mismo repo, no
  repos separados. Todo el trabajo ocurre en clones aislados de este repo.
- Worktree principal operativo: `C:\ASTRA_WORK\Criba-Blackforge-Supra` con
  `.venv` en `criba-blackforge/.venv` (Python 3.11.15) y `supra/.venv`.
- Worktrees aislados para auditar ramas: `C:\ASTRA_WORK\iso-<proposito>`.
- Las rutas históricas (`repo`, `Music\INNOVATIONS\ACTIVE\*`, etc.) se midieron
  AUSENTES. Si reaparecen, mide primero su `origin`: un clon cuyo origin es
  otro directorio describe una copia, no el remoto.
- **Nunca escribas** en rutas que otra sesión, otro turno o un `.gitignore`
  declare: comprueba con `ls` que la ruta EXISTE antes de usarla.
- Los worktrees son EFÍMEROS: ciérralos/limpia después de citarlos. El único
  dato durable es el remoto (`git ls-remote origin main`).

## Entorno de ejecución
- Shell: bash (git-bash / MSYS), NO PowerShell/cmd. Sintaxis POSIX.
- Caminos para herramientas NATIVAS (git, rg, node, python): usa estilo
  forward-slash nativo `C:/Users/...`, NUNCA estilo MSYS `/c/Users/...` — la
  conversión de paths está deshabilitada y `/c/astra_worl/...` falla con
  'cannot change to' para herramientas nativas.
- `$TMPDIR` señala a `C:\Users\KLSX\AppData\Local\hermes\cache\scratch` para
  archivos temporales nativos. Nunca uses `/tmp` en Windows.
- `python` no existe; el intérprete real es `python3` vía `.venv/Scripts/python.exe`.

## Workflow operativo
1. **BASE:** `git status --short --branch` + `git rev-parse HEAD` antes de tocar.
2. **DIAGNÓSTICO:** identifica rutas reales de cada componente, no asumas layout.
3. **PASOS ATÓMICOS:** separa changes por scope (uno de `style(supra)` en otro,
   `chore(deps)` de `uv.lock`). Nunca mezcles Ruff + uv.lock en un commit.
4. **VERIFICA LOCAL:** ruff + mypy debt gate + tests relevantes ANTES de commit.
5. **CI:** el commit no es verdad hasta que CI lo confirme. Revisa:
   `gh pr checks <n>` y `gh api ... actions/runs --jq ...`.
6. **NO MERGEES** PR si Monorepo CI o Anti-Goodhart fallan.

## Puntos a politicas (NO cambiar sin OK de moli)
- THEKEY/CHECKMATE estrictamente separado de SUPRA. No mezclar terminología.
- STANDARD=DISABLED, G3=NOT_VERIFIED.
- La abstención `request_more_evidence` es un resultado válido; no se fuerza a propuesta.
- `persisted != executed`; `IN_PROCESS_MEMORY_CACHE != PERSISTED_STATE`.
- El artefacto faltante no promueve cache a verdad durable.

## Comandos
|- `uv lock` en `criba-blackforge/` (el workspace root con `pyproject.toml`).
|- `uvx ruff check .` por componente (`supra/`, `criba-blackforge/`). No sobre root sin config.
|- `uv run --locked ruff check .` es cómo CI ejecuta Ruff (usa `.venv` del workspace).
|- SUPRA: `uvicorn supra_agentic.service:app --host <h> --port <p>` (Dockerfile: 0.0.0.0:8080).
|- Shadow: `criba_shadow_main.py` arranca SupraServer en thread daemon en free_port.

## Testing patterns
|- **Server-side recovery ≠ client-side recovery.** Ver `status_source == PERSISTED_STATE`
  tras un restart del proceso SUPRA acredita durabilidad del server, NO recovery del cliente.
  Un corte vertical K13/K15 debe verificar AMBOS: (1) GET tras restart del proceso SUPRA,
  y (2) `_load_latest_supra()` / `on_restore_latest_supra()` tras restart real de Shadow
  (nuevo proceso, data_root, single-instance lock). El hash del dossier readbackeado debe
  match con el SHA256 pre-restart. Un stub de cliente (`MockSupraClient`) no acredita esto.
  Ver detalle en `references/storage-status-semantics.md`.
|- **Tests por origen, nunca mezclados.** Separa tests existentes / tests PROPOSED de
  auditoría / tests del delta propio. Un "75 passed + 3 xfailed" mezclado es un reporte
  engañoso — documenta el origen de cada nodeid.
|- **RC-24: no ejecutar suite completa.** `pytest --collect-only` da el inventario.
  Ejecuta por lotes (intelligence, unit) con `--timeout`, `-p no:randomly` para seed fijo.
  Un lote que bloquea: aísla con hipótesis, no cambies flags al azar.

## Troubleshooting rápido
- "The lockfile at `uv.lock` needs to be updated, but `--locked` was provided":
  ejecuta `uv lock` en el workspace root. Si añade un paquete ya declarado en
  `pyproject.toml`, es *lock completion*, no dependencia nueva.
- `ModuleNotFoundError` en tests: el rootdir cambió al worktree del piloto y
  `pythonpath = ["src"]` del `pyproject.toml` no aplica. Ejecuta pytest desde el
  workspace root, no desde subdirectorios.

---
## Referencias
- `references/supra-service-contract.md` — contrato del service SUPRA (`/health`, env vars, storage states)
- `references/storage-status-semantics.md` — status_source / persisted_artifact_status, qué significa cada uno y cómo verificarlo
- `references/shadow-launcher.md` — secuencia de arranque de `criba_shadow_main.py`, single-instance lock y riesgos de orphans
- `references/mypy-debt-gate.md` — protocolo para diferenciar mypy debt gate de Ruff y de lockfile blocks
- `references/windows-shell-path-resolution.md` — paths nativos vs MSYS y el `git -C` broken
