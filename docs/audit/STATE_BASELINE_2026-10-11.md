# STATE_BASELINE 2026-10-11 (CB-00)

Fecha de captura: 2026-10-11 (Europe/Madrid, UTC+02:00)
Autor de la linea: Hermes (Lead Integration Engineer)
Repo: Klsx-Moli/Criba-Blackforge-Supra
Checkout: C:\ASTRA_WORK\Criba-Blackforge-Supra
Rama activa durante la captura: cb-i01-contract-interpreter-dossier-supra

## 1. SHA vigente

- HEAD: 6b3d02b9639466e0dcfd594a66b0744bb46abe57
- main: 6b3d02b9639466e0dcfd594a66b0744bb46abe57
- origin/main: 6b3d02b9639466e0dcfd594a66b0744bb46abe57
- Local main == origin/main == HEAD de la rama de trabajo: SI.
- Divergencia inexplicada local vs remoto: NINGUNA en main. Divergencia explicada (PRs no fusionados, commits solo locales): ver seccion 3.

## 2. Historial reciente de main (git log -15)

```
6b3d02b Unidad BANCO/GRAMMAR aislada (04A/04B/05) + evidencia banco-trace (#20)
ab6f0a9 fix(mono03): supra/LICENSE completo (Apache-2.0 canonico, estaba truncado) (#19)
7242793 Integracion: tests robustez/readiness/interaccion (K6/K7/M2) + evidencia (#18)
4332ff1 Merge pull request #16 from Klsx-Moli/chatgpt/criba-shadow-supra-main-candidate-20261009
d38d9a9 Merge pull request #17 from Klsx-Moli/hermes/reconcile-deep-execution-20261009
9a8af79 docs: estado local 2026-10-09 04:20 - sesion guardada
b992b0c docs: update mega prompt with final suite results at c2a708d
c2a708d chore: add root .gitignore and untrack _probe/ diagnostic scripts
2ea0cf5 fix: sentinel BLACKFORGE con pruebas reales de independencia
786c408 docs: update mega prompt with SUPRA suite results (299 passed)
d0cf2bd feat: add BLACKFORGE unavailable sentinel and integration mega prompt
583d44e fix: add missing _t import and fix ruff import order after cherry-picks
424ebc4 fix(test): update selector text assertion to 'Cargar modelo'
d3a2d01 fix(ui): preserve recovery identity and dialog access
79151dc fix(journey): expose planning limits and declared block causes
```

PRs observados en historial: #16, #17, #18, #19, #20.
Nota: solo main/HEAD local se verifico; la enumeracion completa de PRs remotos requiere API de GitHub (gh no ejecutado en esta captura). Ver limitaciones.

## 3. Ramas y trabajo no integrado

### 3.1 Ramas locales

| Rama | SHA corto | Estado vs main | Ahead |
|---|---|---|---|
| main | 6b3d02b | - | - |
| cb-i01-contract-interpreter-dossier-supra | 6b3d02b | = main (0 ahead) + 1 fichero untracked | 0 |
| cb01-bank-provenance | b9b0ce5 | NOT-MERGED | 2 |
| cb02-structured-diagnostics | eb356e1 | NOT-MERGED | 1 |
| cb03-journey-e2e | 2b2d130 | NOT-MERGED | 1 |
| cb04-bank-diagnosis | 3cb776b | NOT-MERGED | 1 |
| candidate-20261009 | 19f9085 | NOT-MERGED | pendiente de medir |
| hermes/* y astra/* | ver 3.2 | NOT-MERGED en general | pendiente de medir |

Contenido untracked en la rama activa:
- criba-blackforge/tests/integration/test_cb_i01_contract_interpreter_dossier_supra.py (sin commitear)

Estado del checkout: sin modificaciones tracked (git status solo muestra el untracked anterior).

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
```

Trabajo remoto no integrado: todas las ramas astra/* (PRs probablemente #2-#9 del plan), mas codex/interpreter-hardening-20261004 y las ramas hermes/*.

### 3.3 Worktrees activos

```
C:/ASTRA_WORK/Criba-Blackforge-Supra                [cb-i01-contract-interpreter-dossier-supra]
C:/ASTRA_WORK/Criba-Blackforge-Supra-main-baseline  [hermes/local-snapshot-20261009-main-baseline]
C:/ASTRA_WORK/iso-deep-execution-20261005           [hermes/deep-execution-20261005]
C:/ASTRA_WORK/iso-dossier                            [hermes/local-snapshot-20261009-dossier]
C:/ASTRA_WORK/iso-main-4332ff1                       [hermes/mono03-supra-license]
C:/ASTRA_WORK/iso-pr8-safety                         [astra/blackforge-safety/dfca79-auth-state-failclosed]
C:/ASTRA_WORK/iso-pr9-persistence                    [hermes/local-snapshot-20261009-pr9-persistence]
C:/ASTRA_WORK/iso-valida-17                          (detached HEAD @ 9a8af79)
```

Regla de escritor unico: el unico checkout a tocar durante esta campana es C:/ASTRA_WORK/Criba-Blackforge-Supra. Los worktrees iso-* se leen solo si hace falta comparar; no se escriben.

## 4. Inventario de superficies

### 4.1 criba-blackforge/ (nucleo CRIBA + Shadow)

- src/criba/: ~110 modulos. Relevantes para el plan:
  - UI/Shadow: gui.py, ui/ (actions.py, widgets.py, panels.py, main_window...), blackforge_gui.py, blackforge_selector.py
  - Interprete: interprete/ {puerto.py, banco.py, contrato.py, openai_compatible.py, seleccion.py, pipeline.py, juez.py, adaptador.py, store.py, ids.py, prefilter.py, protocolo.py}
  - Persistencia/integracion: storage.py, supra_dossier.py, migration.py, api.py, mcp_server.py
  - Modelo: model_config.py, model_runtime.py, llm_adapter.py, latency.py
  - BLACKFORGE: blackforge_agentic.py, blackforge_agentic_security.py, blackforge_safety.py, blackforge_catalog.py, blackforge_causal.py, blackforge_pipeline.py, blackforge_orthogonal/
  - Version: version.py presente en el checkout activo (ausente en main 15bc237 antiguo; ya no aplica).
- tests/ presentes: adversarial/, astra_canon/ (22 ficheros), fixtures/, integration/ (10 ficheros incl. test_blackforge_unavailable_sentinel.py), intelligence/, property/, unit/, golden_mvp_output.json, test_mvp_golden_output.py, test_packet_ideas_invariant.py, test_packet_v1_regression.py, test_causal_mechanism.py, test_genome_similarity_unknown.py
- verification/ en criba-blackforge: NO EXISTE en este checkout (directorio ausente). Los artefactos verification/local_bank_*.json citados por CB-01 no estan presentes en main actual; deben estar en otra rama o haberse perdido. Ver riesgos.

### 4.2 supra/

- src/, tests/, verification/, scripts/, governance/, data/, Dockerfile, pyproject.toml, uv.lock, LICENSE (Apache-2.0, verificado en ab6f0a9), README.md, run_500.py
- Servicio desplegado en Cloud Run (evidencia previa de sesiones): supra-agentic-taskmaster-128843903420.us-central1.run.app (no verificado en esta captura).

### 4.3 Empaquetado

- .spec en raiz: segun plan existen CRIBA-Blackforge.spec / CRIBA.spec / CribaShadow.spec (no verificados fisicamente en esta captura; ver limitaciones).
- scripts/, ci/: no verificados.

### 4.4 CI (.github/)

- workflows en raiz y criba-blackforge/.github/: no verificados en esta captura.

### 4.5 Docs

- docs/continuity/, docs/contracts/, docs/migration/
- docs/HERMES_AUDIT_REVIEW_20261005.md
- docs/INTERPRETER_CONTRACT.md
- docs/SHADOW_SUPRA_RELEASE_AND_VALUE_GATE.md
- docs/audit/: NO EXISTE -> CB-00 crea este documento como primer fichero.

## 5. Evidencias etiquetadas

- VERIFICADO (esta sesion, comandos ejecutados): SHA de HEAD/main/origin, lista de ramas, worktrees, git status, existencia de arboles de ficheros (docs/, verification/, tests/, src/criba/), estado de merge de las 5 ramas cb*.
- INFERIDO (de historial/estructura, sin ejecucion): contenido funcional de los modulos, estado de CI, existencia de specs, PRs remotos #2-#15, artefactos verification/ historicos.
- DESCONOCIDO (no verificable sin mas acciones): checks de CI que requieren secretos/Windows/GPU, estado del servicio Cloud Run, contenido de run_500.py.

## 6. Riesgos conocidos (derivados, no todos medidos)

R1. verification/ con artefactos del banco (local_bank_*.json, banco_05_seeds.json) no existe en el checkout actual -> CB-01 y CB-04 pueden quedar BLOCKED por falta de baseline de evidencia. Mitigacion: localizar los JSON en las ramas hermes/banco-* (hermes/banco-grammar-04, hermes/banco-trace-04a-20261010) antes de tocar nada.
R2. Multiples ramas con trabajo valioso no integrado (cb01-cb04, hermes/*, astra/*, codex/*). Riesgo de perdida si se borran sin demostrar absorcion. Regla: no borrar ninguna rama.
R3. BLACKFORGE presente en el arbol (blackforge_*.py). Regla dura: no ejecutar, habilitar ni borrar sin autorizacion explicita de moli.
R4. Worktree iso-pr8-safety en la rama astra/blackforge-safety: cualquier trabajo ahi requiere leerse antes de afirmar contenido.
R5. git status muestra tests/integration/test_cb_i01...py sin commitear: evidencia de sesion previa cortada. Hay que conservarlo (no borrar) y decidir si se commitea en la rama CB-I01.
R6. Rama cb-i01-contract-interpreter-dossier-supra esta a 0 ahead de main pero tiene untracked: la "integracion" aparente puede ser solo posicionamiento de punteros.

## 7. Mapa de trabajo por tarjeta (derivado del inventario)

| Tarjeta | Ruta de trabajo | Bloqueo previsto |
|---|---|---|
| CB-00 | docs/audit/ (este fichero) | Ninguno |
| CB-01 | criba-blackforge/verification/ o scripts de procedencia | R1 (JSON historicos) |
| CB-02 | src/criba/ui + interprete (diagnostico estructurado) | rama cb02 existe, comparar |
| CB-03 | verification/journey_e2e_no_model.py | rama cb03 existe |
| CB-04 | interprete/banco + JSON banco | R1 + entorno local |
| CB-I01 | tests/integration/test_cb_i01_*.py | fichero untracked a conservar |
| CB-I02 | tests/integration + ui/actions.py | - |
| CB-I03 | tests/integration + storage/supra_dossier | - |
| CB-S01 | tests/security/ | - |
| CB-S03 | tests/security/ + adversarial | - |
| CB-S02 | blackforge_safety (solo lectura/tests) | BLACKFORGE inerte |
| CB-L0x | tests/stress/ | - |
| CB-D0x | scripts/ + .spec | specs sin verificar |

## 8. Plan de ejecucion inmediato (tras CB-00)

1. CB-00 (este documento): commit en rama propia desde main.
2. Recuperar inventario de artefactos verification/ desde ramas hermes/banco-* para desbloquear CB-01/CB-04.
3. Continuar con el orden de fases del megaprompt: CB-01 -> CB-03 -> CB-04 -> CB-02 -> CB-I01 -> ... respetando gates.

## 9. Limitaciones de esta linea base

- gh CLI no ejecutado: no hay enumeracion completa de PRs ni checks de CI en remoto.
- No se ejecuto pytest en esta captura: el estado de tests es DESCONOCIDO, no declarado.
- No se verifico contenido de .spec ni workflows.
- No se leyo contenido de SUPRA ni de modulos fuente: solo estructura.
