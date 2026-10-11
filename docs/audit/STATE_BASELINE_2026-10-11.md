# STATE_BASELINE_2026-10-11 (CB-00) — actualizado con verificación real

Fecha de captura: 2026-10-11 (Europe/Madrid, UTC+02:00)
Rama activa durante la captura: cb01-bank-provenance-work
Checkout: C:\ASTRA_WORK\Criba-Blackforge-Supra

Registro sellado (versión anterior del mismo fichero en commit b9b0ce5, rama cb01-bank-provenance):
- BASE_SHA: 6b3d02b9639466e0dcfd594a66b0744bb46abe57
- GIT_STATUS en 6b3d02b: limpio (local HEAD == remoto == 6b3d02b, sin cambios sin commitear)
- UV_LOCK_HASH (sha256, criba-blackforge/uv.lock):
    d4482adfb56d4bd5e82229cf4a93342d743acd0cc7a8044d1e5409a71aa83f2f
- Etiqueta del sello: STATICALLY_INSPECTED (lectura remota GitHub + git local, sin mutación)
- Los tres checks de CI sobre 6b3d02b pasaron:
  monorepo-result / CRIBA / BLACKFORGE / SUPRA = success
- Python: 3.11.15 (venv local)

## 1. SHA vigente

- HEAD: 7f666cb9ee88f15c97c3b3ffa6434f857bd1f20d (commit CB-00 en rama cb01-bank-provenance-work)
- main: 6b3d02b9639466e0dcfd594a66b0744bb46abe57
- origin/main: 6b3d02b9639466e0dcfd594a66b0744bb46abe57
- Divergencia explicada: HEAD está 1 commit por delante de origin/main (el commit CB-00 mismo).
- Divergencia inexplicada: NINGUNA.

## 2. Estado del checkout

- Rama: cb01-bank-provenance-work
- git status --short --branch:
  ## cb01-bank-provenance-work
  A  criba-blackforge/tests/unit/test_bank_provenance_cb01.py
  A  criba-blackforge/verification/_provenance.py
  ?? criba-blackforge/tests/integration/test_cb_i01_contract_interpreter_dossier_supra.py
- Tres ficheros sin resolver: dos staged (contenido CB-01 parcial) + uno untracked (test CB-I01).

## 3. Ramas y trabajo no integrado

### 3.1 Ramas locales

| Rama | SHA corto | Estado vs main | Ahead |
|---|---|---|---|
| main | 6b3d02b | - | - |
| cb00-state-baseline | 7f666cb | NOT-MERGED | 1 |
| cb01-bank-provenance | b9b0ce5 | NOT-MERGED | 2 |
| cb01-bank-provenance-work | 7f666cb | NOT-MERGED | 1 |
| cb02-structured-diagnostics | eb356e1 | NOT-MERGED | 1 |
| cb03-journey-e2e | 2b2d130 | NOT-MERGED | 1 |
| cb04-bank-diagnosis | 3cb776b | NOT-MERGED | 1 |
| cb-i01-contract-interpreter-dossier-supra | 6b3d02b | = main (0 ahead) + 1 fichero untracked | 0 |
| candidate-20261009 | 19f9085 | NOT-MERGED | pendiente de medir |
| hermes/* y astra/* | ver 3.2 | NOT-MERGED en general | pendiente de medir |

### 3.2 Ramas remotas (origin)

```
origin/main                                    6b3d02b
origin/codex/interpreter-hardening-20261004    2dc0094
origin/hermes/astra/shadow-supra-20261002      b91e43c
origin/hermes/cbs-continuity-memory-20261005   fc33a7a
origin/astra/blackforge-persistence/15bc23-durable-agentic-audit  1a98b7e
origin/astra/blackforge-safety/dfca79-auth-state-failclosed       4340f52
origin/astra/criba-core/22813e65-lottery-storage-integrity        12bdd88
origin/astra/criba-outcome/edd50814-aware-timestamps              66b1e9d
origin/astra/supra-state/22813e65-persistence-rollback            2a3b48d
origin/astra/supra-state/ad1a4-atomic-list-snapshot               93a1362
origin/astra/supra-state/dfca79-atomic-list-snapshot              d8ed9c7
origin/astra/supra-state/edd50814-corrupt-state-load              77a3620
origin/cb01-bank-provenance                    b9b0ce5 (remota; local coincide)
origin/hermes/cbs-pr8-11-convergence-audit     3b2472a
```

Ramas cb01/cb02/cb03/cb04 NO están en remoto (solo locales); trabajo valioso sin respaldo remoto.

### 3.3 Worktrees activos

```
C:/ASTRA_WORK/Criba-Blackforge-Supra                [cb01-bank-provenance-work]
C:/ASTRA_WORK/Criba-Blackforge-Supra-main-baseline  [hermes/local-snapshot-20261009-main-baseline]
C:/ASTRA_WORK/iso-deep-execution-20261005           [hermes/deep-execution-20261005]
C:/ASTRA_WORK/iso-dossier                            [hermes/local-snapshot-20261009-dossier]
C:/ASTRA_WORK/iso-main-4332ff1                       [hermes/mono03-supra-license]
C:/ASTRA_WORK/iso-pr8-safety                         [astra/blackforge-safety/dfca79-auth-state-failclosed]
C:/ASTRA_WORK/iso-pr9-persistence                    [hermes/local-snapshot-20261009-pr9-persistence]
C:/ASTRA_WORK/iso-valida-17                          (detached HEAD @ 9a8af79)
```

Los 7 worktrees secundarios están sucios = 0 líneas en git status --porcelain (verificado). Regla de escritor único: solo se toca C:/ASTRA_WORK/Criba-Blackforge-Supra. Los iso-* se leen solo si hace falta comparar.

## 4. Inventario de superficies

### 4.1 criba-blackforge/ (núcleo CRIBA + Shadow)

- src/criba/: ~110 módulos.
  - UI/Shadow: gui.py, ui/ (actions.py, widgets.py, panels.py, main_window...), blackforge_gui.py, blackforge_selector.py
  - Intérprete: interprete/ {puerto.py, banco.py, contrato.py, openai_compatible.py, seleccion.py, pipeline.py, juez.py, adaptador.py, store.py, ids.py, prefilter.py, protocolo.py}
  - Persistencia/integración: storage.py, supra_dossier.py, migration.py, api.py, mcp_server.py
  - Modelo: model_config.py, model_runtime.py, llm_adapter.py, latency.py
  - BLACKFORGE: blackforge_agentic.py, blackforge_agentic_security.py, blackforge_safety.py, blackforge_catalog.py, blackforge_causal.py, blackforge_pipeline.py, blackforge_orthogonal/
- tests/ presentes: adversarial/, astra_canon/ (22 ficheros), fixtures/, integration/ (10 ficheros incl. test_blackforge_unavailable_sentinel.py), intelligence/, property/, unit/, golden_mvp_output.json, test_mvp_golden_output.py, test_packet_ideas_invariant.py, test_packet_v1_regression.py, test_causal_mechanism.py, test_genome_similarity_unknown.py
- verification/ presente con:
  - _provenance.py (staged CB-01)
  - audit_ui_geometry.py, banco_05_seeds.{json,py}, banco_trace_05.{json,py}, banco_trace_05_control.{json,py}, banco_trace_05_n3.json, baseline_fase0.json
  - local_bank_*.json NO están físicamente aquí; viven en hermes/banco-grammar-04 y hermes/banco-trace-04a-20261010.

### 4.2 supra/

- src/, tests/, verification/, scripts/, governance/, data/, Dockerfile, pyproject.toml, uv.lock, LICENSE (Apache-2.0 verificado en ab6f0a9), README.md, run_500.py
- Servicio Cloud Run (evidencia previa, no verificada en esta captura):
    supra-agentic-taskmaster-128843903420.us-central5.run.app

### 4.3 Empaquetado

- .spec en criba-blackforge/: CRIBA.spec, CRIBA-Blackforge.spec, CribaShadow.spec (verificados físicamente)
- scripts/, ci/ presentes.
- .github/workflows/ en raíz: ci.yml, shadow-windows-build-smoke.yml.
- criba-blackforge/.github/workflows/: ci.yml, publish-pypi.yml, release.yml.
- CI corre pytest, ruff y mypy en ubuntu-latest / windows-2025 / ubuntu-latest.

### 4.5 Docs

- docs/continuity/, docs/contracts/, docs/migration/
- docs/HERMES_AUDIT_REVIEW_20261005.md
- docs/INTERPRETER_CONTRACT.md
- docs/SHADOW_SUPRA_RELEASE_AND_VALUE_GATE.md
- docs/audit/: existe. STATE_BASELINE_2026-10-11.md (este fichero).

## 5. Evidencias etiquetadas

- VERIFICADO (esta sesión, comandos ejecutados):
  - SHA HEAD/main/origin, lista de ramas locales y remotas, worktrees, git status.
  - 3 checks de CI sobre 6b3d02b = success (gh api check-runs).
  - 3 checks de PR #21 (cb01-bank-provenance) = pass (gh pr checks).
  - Existencias físicas de criba-blackforge/verification/, .spec files, workflows.
  - Todos los 7 worktrees secundarios limpios.
- INFERIDO (de historial/estructura, sin ejecución):
  - Contenido funcional de los módulos fuente.
  - Estado de tests locales (no ejecutados en esta captura).
  - Contenido de run_500.py.
- DESCONOCIDO (no verificable sin más acciones):
  - Checks de CI que requieren secretos/Windows/GPU.
  - Estado del servicio Cloud Run.
  - Estado de tests ejecutados en local.

## 6. Riesgos conocidos

R1. verification/ con local_bank_*.json no existe físicamente en el checkout actual; vive en ramas hermes/banco-*. CB-04 usó esos JSON vía rama; CB-01 debe consultarlos ahí antes de afirmar baseline.
R2. Múltiples ramas con trabajo valioso no integrado (cb01-cb04 locales sin respaldo remoto, hermes/*, astra/*, codex/*). Regla dura: no borrar ninguna rama.
R3. BLACKFORGE presente en el árbol. Regla dura: no ejecutar, habilitar ni borrar sin autorización explícita de moli.
R4. Worktree iso-pr8-safety en la rama astra/blackforge-safety. Cualquier trabajo ahí requiere leerse antes de afirmar contenido.
R5. git status muestra tests/integration/test_cb_i01...py sin commitear: evidencia de sesión previa cortada. Hay que conservarlo (no borrar) y decidir si se commitea en la rama CB-I01.
R6. Rama cb-i01-contract-interpreter-dossier-supra está a 0 ahead de main pero tiene untracked: la "integración" aparente puede ser solo posicionamiento de punteros.
R7. Commit 7f666cb (CB-00) no está en remoto; el trabajo CB-00 existe solo local.
R8. Rama cb01-bank-provenance-work tiene 2 ficheros staged y un untracked, pero está 1 commit por delante de origin/main sin push. El commit contiene baseline desactualizada que este fichero corrige.

## 7. Mapa de trabajo por tarjeta (derivado del inventario)

| Tarjeta | Ruta de trabajo | Bloqueo previsto |
|---|---|---|
| CB-00 | docs/audit/ (este fichero) | Ninguno |
| CB-01 | criba-blackforge/verification/ o scripts de procedencia | R1 (JSON históricos) |
| CB-02 | src/criba/ui + interprete (diagnóstico estructurado) | rama cb02 existe, comparar |
| CB-03 | verification/journey_e2e_no_model.py | rama cb03 existe |
| CB-04 | interprete/banco + JSON banco | R1 + entorno local |
| CB-I01 | tests/integration/test_cb_i01_*.py | fichero untracked a conservar |
| CB-I02 | tests/integration + ui/actions.py | - |
| CB-I03 | tests/integration + storage/supra_dossier | - |
| CB-S01 | tests/security/ | - |
| CB-S03 | tests/security/ + adversarial | - |
| CB-S02 | blackforge_safety (solo lectura/tests) | BLACKFORGE inerte |
| CB-L0x | tests/stress/ | - |
| CB-D0x | scripts/ + .spec | - |

## 8. Plan de ejecución inmediato (tras CB-00)

1. CB-00 (este documento): actualizar el baseline con hechos verificados y commit en rama propia desde main.
2. Recuperar inventario de artefactos verification/ desde ramas hermes/banco-* para desbloquear CB-01/CB-04.
3. Continuar con el orden de fases del megaprompt: CB-01 -> CB-03 -> CB-04 -> CB-02 -> CB-I01 -> ... respetando gates.

## 9. Limitaciones de esta línea base

- No se ejecutó pytest en esta captura: el estado de tests locales es DESCONOCIDO.
- No se leyó contenido de SUPRA ni de módulos fuente: solo estructura.
- Los checks de CI solo acreditan el CI, no la UI real ni el EXE en Windows.
