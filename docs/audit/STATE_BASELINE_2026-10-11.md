STATE BASELINE — CB-00
========================

Registro sellado
----------------
REPO:        Klsx-Moli/Criba-Blackforge-Supra
REF:         refs/heads/main
BASE_SHA:    6b3d02b9639466e0dcfd594a66b0744bb46abe57
OBSERVED_AT: 2026-10-11 (sesión Hermes, Hora de verano romance UTC+02:00)
GIT_STATUS:  limpio (local HEAD == remoto == 6b3d02b, sin cambios sin commitear)
PYTHON_VERSION: 3.11.15 (venv del checkout local)
PLATFORM:    Windows 11, bash (MSYS) sobre terminal
UV_LOCK_HASH (sha256, criba-blackforge/uv.lock):
            d4482adfb56d4bd5e82229cf4a93342d743acd0cc7a8044d1e5409a71aa83f2f

Etiqueta del sello: STATICALLY_INSPECTED (lectura remota GitHub + git local, sin mutación)

Nota de autoridad: el SHA proviene de la API de GitHub (git refs/heads/main) y coincide
con el HEAD local. La ref local origin/main estuvo stale en un momento anterior de la
sesión (apuntaba a 4332ff1) y fue corregida manualmente a 6b3d02b; el SHA remoto real
siempre fue 6b3d02b. Sin impacto en el código: era una ref local desactualizada.


Checks del SHA (CI_REVIEW)
---------------------------
Commit 6b3d02b:
  - monorepo-result .... completed / success
  - CRIBA / BLACKFORGE .. completed / success
  - SUPRA .............. completed / success
Los tres verdes sobre el HEAD actual. Nota: un test verde en CI no acredita por sí solo
UI, EXE, Windows, GPU, proveedor real ni recuperación tras reinicio (ver Definición de DONE).


Últimos 20 commits de main (STATICALLY_INSPECTED)
--------------------------------------------------
6b3d02b Unidad BANCO/GRAMMAR aislada (04A/04B/05) + evidencia banco-trace (#20)
ab6f0a9 fix(mono03): supra/LICENSE completo (Apache-2.0 canónico, estaba truncado) (#19)
7242793 Integración: tests robustez/readiness/interacción (K6/K7/M2) + evidencia (#18)
4332ff1 Merge pull request #16 from chatgpt/criba-shadow-supra-main-candidate-20261009
d38d9a9 Merge pull request #17 from hermes/reconcile-deep-execution-20261009
9a8af79 docs: estado local 2026-10-09 — sesión guardada
b992b0c docs: update mega prompt with final suite results at c2a708d
c2a708d chore: add root .gitignore and untrack _probe/ diagnostic scripts
2ea0cf5 fix: sentinel BLACKFORGE con pruebas reales de independencia
786c408 docs: update mega prompt with SUPRA suite results (299 passed)
d0cf2bd feat: add BLACKFORGE unavailable sentinel and integration mega prompt
583d44e fix: add missing _t import and fix ruff import order after cherry-picks
424ebc4 fix(test): update selector text assertion to 'Cargar modelo'
d3a2d01 fix(ui): preserve recovery identity and dialog access
79151dc fix(journey): expose planning limits and declared block causes
120807b fix(m2): export displayed interpreted proposal, not unrelated core axis
26e166c fix(ui): Cargar modelo on startup + async enhance + condicion_fracaso test fix
0445e87 fix(ui): reflect selected model in Generación tab + progress feedback
7017eee fix(ui): breathing gradient on model test button + condicion_fracaso sentinel
0bed7cc fix(ui): don't track enhance worker in _live_workers

Observación relevante: los commits 424ebc4 y 26e166c ya tocan "Cargar modelo" en el
arranque y en el selector. Esto contradice parcialmente una premisa previa de que "arranca
en nous". Requiere verificación en CB-02/CB-10 sobre qué proveedor queda efectivo por
defecto tras esos commits (no se afirma aquí sin reproducirlo).


PRs — estado completo (CI_REVIEW, API state=all, paginado; re-verificado 2026-10-11 post-CB-01)
-------------------------------------------------------------------------------------------
MERGED:
  #1  base:main  head:6e5f90c  ASTRA5: reduce CRIBA/BLACKFORGE type debt + scoring
  #2  base:main  head:2a3b48d  SUPRA: rollback every state mutation when persistence fails
  #3  base:main  head:12bdd88  CRIBA: make lottery history persistence honest and lossless
  #4  base:main  head:77a3620  SUPRA: fail explicitly on corrupt persisted project state
  #5  base:main  head:66b1e9d  CRIBA: reject timezone-ambiguous outcome timestamps
  #7  base:main  head:d8ed9c7  SUPRA: return project listing diagnostics atomically
  #16 base:main  head:d38d9a9  DRAFT main candidate: CRIBA Shadow + SUPRA + reconcile
  #17 base:chatgpt/criba-shadow-supra-main-candidate-20261009 head:9a8af79 reconcile deep
  #18 base:main  head:c9ff543  Integración tests robustez/readiness/interacción (K6/K7/M2)
  #19 base:main  head:ca5bb59  fix(mono03): supra/LICENSE completo
  #20 base:main  head:3351992  Unidad BANCO/GRAMMAR aislada (04A/04B/05) + evidencia

CLOSED sin merge:
  #6  base:main  head:93a1362  SUPRA: return project listing diagnostics atomically
      (cerrada sin merged_at; #7 cubre el mismo objetivo y sí está merged)

DRAFT abiertos (no mergeables por diseño; trabajo de otros autores):
  #8  base:main  head:65a58e5  BLACKFORGE: deny expired or denied authorization
  #9  base:main  head:1a98b7e  BLACKFORGE: make agentic audit persistence durable
  #10 base:hermes/astra/shadow-supra-20261002 head:2dc0094 Require causal interpreter proposals
  #11 base:main  head:3244879  BLACKFORGE v1: canonical DefensiveCase, execution broker
  #12 base:codex/interpreter-hardening-20261004 head:8b1ba5b docs(continuity) CBS
  #13 base:codex/interpreter-hardening-20261004 head:61b1b94 Harden Shadow–SUPRA startup
  #14 base:chatgpt/shadow-supra-reliability-20261008 head:14ec9d2 EXE journey
  #15 base:chatgpt/shadow-exe-journey-20261008 head:19f9085 reconcile Hermes snapshots

ABIERTO propio (Hermes, esta sesión / sesión previa):
  #21 base:main  head:0344089 (cb01-bank-provenance) CB-01: procedencia obligatoria en
      artefactos de verificación del banco. MERGEABLE. Checks Monorepo CI sobre 0344089:
      "CRIBA / BLACKFORGE" SUCCESS (03:55:26Z), "SUPRA" SUCCESS (03:52:28Z),
      "monorepo-result" SUCCESS (03:55:33Z), run 38109735687. Test local dirigido:
      .venv/Scripts/python -m pytest tests/unit/test_bank_provenance_cb01.py -> 12 passed.
      NOTA DE GOBIERNO: gates verdes en CI no autorizan merge; el merge queda pendiente
      de autorización explícita del propietario (regla vigente). Contiene además el
      presente documento STATE_BASELINE (CB-00) — unidad coherente baseline+procedencia.

Nota: #10, #12, #13, #14, #15 tienen base distinta de main (ramas de trabajo antiguas).
Su mergeabilidad contra 6b3d02b no se evalúa aquí; se revisa en CB-06/CB-07/CB-08.


Ramas remotas (33) — STATICALLY_INSPECTED (gh api branches, 2026-10-11)
---------------------------------------------------------------------
Clasificación por prefijo:
  astra/*  (9): blackforge-dossier-20261005, blackforge-persistence/15bc23-durable-agentic-audit,
               blackforge-safety/dfca79-auth-state-failclosed, criba-core/22813e65-lottery-storage-integrity,
               criba-outcome/edd50814-aware-timestamps, supra-state/22813e65-persistence-rollback,
               supra-state/ad1a4-atomic-list-snapshot, supra-state/dfca79-atomic-list-snapshot,
               supra-state/edd50814-corrupt-state-load
  astra5-20260930-criba-type-debt (1)
  cb01-bank-provenance (1)  <- rama propia de esta tarjeta (CB-01, PR #21)
  chatgpt/* (5): criba-shadow-supra-main-candidate-20261009, forensic-all-fixes-20261001,
               reconcile-hermes-deep-20261009, shadow-exe-journey-20261008,
               shadow-supra-reliability-20261008
  codex/interpreter-hardening-20261004 (1)
  hermes/*  (14): astra/p0-state-utf8-persistence, astra/p1-golden-blob-path,
               astra/shadow-supra-20261002, audit-snapshot-20261009, banco-trace-04a-20261010,
               cbs-continuity-memory-20261005, cbs-pr8-11-convergence-audit, deep-execution-20261005,
               local-snapshot-20261009-convergence-audit, local-snapshot-20261009-dossier,
               local-snapshot-20261009-eval-cbs, local-snapshot-20261009-main-baseline,
               local-snapshot-20261009-pr9-persistence, reconcile-deep-execution-20261009
  main (1)
  reconcile/local-vs-remote (1)

Corrección de deriva (2026-10-11, segunda pasada): la primera versión de este baseline
contaba 32 ramas y 201 ficheros de test; ambas cifras eran correctas en su momento y
quedaron obsoletas al crear la rama cb01-bank-provenance (+1 rama) y el fichero
tests/unit/test_bank_provenance_cb01.py (+1 test). Verificado con `gh api .../branches`
y `find criba-blackforge/tests -name 'test_*.py' | wc -l` (202). El conteo local de
remote-tracking refs (12) es sólo lo que este checkout tiene fetchado; no es el inventario
remoto. Los SHAs remotos verificados de las ramas astra/* coinciden con los heads de los
PRs mergeados (#2–#5/#7).

Nota de gobierno: las ramas astra/* corresponden a trabajo ya fusionado vía #1–#5/#7
(rollback, atomicidad, timestamps, estado corrupto). No se borran aquí; su absorción se
verifica por diff en CB-06/CB-08 antes de cualquier cierre.


Árbol de trabajo (STATICALLY_INSPECTED)
---------------------------------------
criba-blackforge/src/criba/: anti_goodhart, blackforge_orthogonal, core, integrations,
  intelligence, interprete, scoring, ui, (módulos raíz engine.py, storage.py, banco, etc.)
criba-blackforge/verification/: scripts de banco/trace y JSON de evidencia
criba-blackforge/scripts/: utilidades
supra/src/supra_agentic/: anti_goodhart, integrations, providers, web

Tests: criba-blackforge/tests = 201 ficheros test_*.py; supra/tests = 28 ficheros.
Specs PyInstaller: criba-blackforge/{CRIBA.spec, CRIBA-Blackforge.spec, CribaShadow.spec}
Workflows:
  raíz .github/workflows/: ci.yml, shadow-windows-build-smoke.yml
  criba-blackforge/.github/workflows/: ci.yml, publish-pypi.yml, release.yml
  supra/.github/workflows/: ci.yml, release.yml


Riesgos conocidos / premisas a revalidar (NO dadas por buenas)
-------------------------------------------------------------
1. Proveedor por defecto del launcher/EXE: sin verificar de forma ejecutable. El código
   openai_compatible.py define default "nous_oauth_subscription_proxy" (STATICALLY_INSPECTED),
   pero los commits 424ebc4/26e166c ya ajustan el arranque a "Cargar modelo". Contradicción
   abierta → CB-10.
2. Diagnóstico PENDIENTE_INTERPRETACION / HTTP 503: operativo() en openai_compatible.py
   devuelve motivo honesto y específico (STATICALLY_INSPECTED). El 503 NO es hueco silencioso.
   Falta acreditar que llega diferenciado hasta Shadow → CB-02.
3. Integridad SUPRA: state.py tiene _persist_transition_or_rollback + ProjectStateLoadError
   (STATICALLY_INSPECTED). Falta prueba de reintroducción de fallo (mutation) → CB-09.
4. BLACKFORGE: el gate de autorización vive en blackforge_safety.py (sandbox, rollback,
   human_approval). FIDO2 no aparece en el código (solo en un .txt de catálogo de métodos).
   Contención vigente; no reactivar sin autorización → CB-11.
5. Evidencia del banco (verification/*.json): procedencia SHA/entorno no garantizada en los
   JSON antiguos → CB-01.
6. EXE reproducible: build/hash/arranque no ejecutados en este entorno → CB-10 (NOT_EXECUTED).


Plan de ejecución actualizado (orden del megaprompt)
----------------------------------------------------
CB-00 (este doc) → CB-01 (procedencia evidencia) → CB-03 (journey E2E sin modelo) →
CB-04 (reproducir fallo banco) → CB-02 (diagnóstico hasta Shadow) → CB-09 (persistencia) →
CB-05 (OpenAPI) → CB-06/CB-07/CB-08 (recuperación PRs #13/#14, #15, #10/#12) →
CB-10 (EXE) → CB-11 (BLACKFORGE) → CB-12 (aceptación final).

Siguiente paso: CB-01 — añadir metadatos de procedencia a los scripts que generan JSON de
verification/ y test que valide su presencia/tipos/ausencia de secretos. No toca contratos
de ejecución (RISK GREEN).
