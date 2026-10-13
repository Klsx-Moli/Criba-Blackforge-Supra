# CB-00 · INVENTARIO Y SELLADO DEL ESTADO (entregado por Hermes)
Fecha: 2026-10-11 (Europe/Madrid)
Repo: Klsx-Moli/Criba-Blackforge-Supra
SHA main local = SHA origin/main = SHA cb01-bank-provenance-work: e52ab859b5172b234a8a272c0fb03d2365c89951
Working tree: limpio (git status --porcelain vacío, 894 archivos tracked, 0 untracked)
Merge-base(HEAD, origin/main) = 6b3d02b -> HEAD es descendiente directo (fast-forward puro ya aplicado)

## 1. ESTADO REMOTO vs LOCAL (verificado, no inferido)
- origin/main                 = e52ab85  (tras push de esta sesión; antes 6b3d02b)
- main (local)                = e52ab85
- cb01-bank-provenance-work   = e52ab85
- git rev-list --left-right --count main...origin/main = 0 0  (SINCRONIZADO)
- Acción de esta sesión: fast-forward de main 6b3d02b..e52ab85 (25 commits) + push a origin.
- Corrección de config aplicada: remote.origin.fetch ahora incluye +refs/heads/main:refs/remotes/origin/main
  (antes solo seguía hermes/astra/shadow-supra-20261002, por eso origin/main no refrescaba tras el push).

## 2. PRs GitHub (gh pr list --state all, verificado)
OPEN:
- #21 CB-01: procedencia obligatoria... (cb01-bank-provenance) — rama b9b0ce5, DIVERGENTE de main. NO tocada.
MERGED (relevantes, ya integradas en main):
- #20 Unidad BANCO/GRAMMAR (hermes/banco-grammar-04) MERGED
- #19 fix(mono03) supra/LICENSE (hermes/mono03-supra-license) MERGED
- #18 Integración tests K6/K7/M2 (hermes/blackforge-tab-20261011) MERGED
- #17 Reconcile deep-execution (hermes/reconcile-deep-execution-20261009) MERGED
- #16 main candidate Shadow+SUPRA (chatgpt/criba-shadow-supra-main-candidate-20261009) MERGED
- #1..#7, #9..#15 DRAFT/CLOSED (preservados, trabajo no integrado en main)

## 3. RAMAS (local 28 / origin 37) — no borradas (regla 14)
Locales sin remote propio (snapshots/auditoría locales):
cb00-state-baseline, cb02-structured-diagnostics, cb03-journey-e2e, cb04-bank-diagnosis,
cb-i01-contract-interpreter-dossier-supra, hermes/ui-hilos-revision, hermes/local-snapshot-* (5),
hermes/audit-snapshot-20261009.
Todas preservadas. Ninguna borrada ni forzada.

## 4. WORKFLOWS CI (tracked)
- .github/workflows/ci.yml
- .github/workflows/shadow-windows-build-smoke.yml
- criba-blackforge/.github/workflows/{ci.yml, publish-pypi.yml, release.yml}
Requieren secretos/Windows para publish/release. CI verde != aceptación humana.

## 5. VERIFICACIÓN REAL EJECUTADA POR HERMES ESTA SESIÓN (no afirmada, reproducida)
Entorno: criba-blackforge/.venv (CPython 3.11.15), PySide6, pytest-9.1.1. cwd=criba-blackforge.
- CB suites dirigidas (I01,I02,I03,I06,R01,R02,S01,S03,S04,L01,L02,L03, diagnostico, provenance):
  150 passed en 36.14s
- UNIT tests/unit/            : 1181 passed  (-p no:randomly; 267s)
- INTEGRATION tests/integration/: 115 passed, 3 skipped (GPU/Windows real)
- STRESS tests/stress/ (CB-L01/L02/L03): 22 passed
- ASTRA_CANON+adversarial+property : 182 passed
- INTELLIGENCE tests/intelligence/  : 418 passed
- SUPRA tests/ (supra/.venv)        : 299 passed
- CB-03 journey E2E no-model        : exit 0, PRIMER_BORDE_PROBLEMATICO=ninguno
  (RESTART_PROCESS real, REOPEN_RELOAD source=PERSISTED_STATE, artifact=VERIFIED_FROM_ARTIFACT)

HALLAZGO HONESTO (no ocultado): con orden aleatorio (pytest-randomly, activo por defecto),
test_gui_inventar.py::test_inventar_button_runs_shared_service FALLA una vez dentro de tests/unit/
(1180 passed, 1 failed). En aislamiento PASA (1 passed). Con -p no:randomly la suite pasa 1181/1181.
=> Contaminación cruzada / orden-dependencia, NO defecto de código del test en sí.
=> Esto contradice el claim literal '0 FAILED' del commit e52ab85 cuando se corre con el orden
   por defecto del repo. Queda registrado como tarjeta nueva (ver sección 8). NO se oculta.

## 6. TARJETAS QUE NO EXISTEN FÍSICAMENTE (evidencia física, no inferencia)
- CB-L04 tests/stress/test_cb_l04_shadow_repeated_journey.py : AUSENTE
- CB-L05 tests/stress/test_cb_l05_network_degradation.py      : AUSENTE
- CB-L06 tests/stress/test_cb_l06_resource_limits.py          : AUSENTE
- Registro canónico T001-T130 : NO ENCONTRADO en el repo (git grep sin resultados en *.md/*.py/*.yaml/*.json
  salvo falsos positivos .hermes/iie que NO son el catálogo T001-T130).
=> El expert-technique-router NO puede groundear técnicas T001-T130; se continúa con routing experto
   y confianza reducida, declarado explícitamente.

## 7. BLACKFORGE (regla 8: no reactivar)
- criba-blackforge/src/blackforge/ : NO EXISTE como paquete (INERTE).
- Existen módulos blackforge_agentic.py / blackforge_agentic_security.py / adversarial_self.py en src/criba/
  pero NO se ejecutan ni activan. CB-I06 prueba aislamiento ante fallo. BLACKFORGE inerte. OK.

## 8. TARJETAS DERIVADAS DE ESTE INVENTARIO (ledger vivo)
- CB-NUEVO-1 [P1, contaminación cruzada]: test_gui_inventar orden-dependiente bajo pytest-randomly.
  Root-cause pendiente; no se corrige sin decisión (podría requerir fixture de aislamiento).
- CB-L04/L05/L06 : NO_EXISTE_FISICAMENTE (decisión de moli: ¿construir o declarar fuera de alcance?).
- CB-I04 proveedor real : BLOQUEADO (requiere endpoint/autorización de moli).
- CB-S02 autorización BLACKFORGE : BLOQUEADO (prohibido sin autorización explícita).
- CB-D01/D02/X01 EXE Windows : NO_EJECUTADO (requiere build+smoke real Windows).
- PR #21 : abierto, divergente. Pendiente decisión (merge/cerrar/preservar).

## 9. RIESGOS CONOCIDOS
- Contaminación cruzada por pytest-randomly puede enmascarar/crear fallos intermitentes.
- docs/release/ACCEPTANCE_<sha>.md exigido por megaprompt CB-X02 NO existe; el veredicto vive en
  criba-blackforge/docs/audit/CB-X02_ACCEPTANCE.md (GO_WITH_LIMITS). Discrepancia de ruta menor.

## 9b. AUDITORÍA ADVERSARIAL DE INTEGRIDAD (Hermes, tras fallo del subagente por provider)
ARITMÉTICA del claim "2357 GREEN":
- Conteo REAL recolectado esta sesión (-p no:randomly), por directorio:
  unit=1181, integration=118(115 pass+3 skip), stress=22, security=42, recovery=18,
  intelligence=418, astra_canon=154, adversarial=25, property=3 => subtotal criba-blackforge=1981
  + SUPRA=299 => TOTAL DEDUPLICADO = 2280 tests recolectados.
- El 2357 del commit NO cuadra: la campaña sumó los 150 del run CB dirigido (I01/I02/I03/I06/
  R01/R02/S01/S03/S04/diagnostico/provenance/L01/L02/L03) ENCIMA de los totales por directorio,
  siendo esas suites SUBCONJUNTOS ya contados en unit/integration/stress/security/recovery.
  => DOBLE CONTEO. Veredicto aritmético: INCONSISTENT (claim inflado por doble conteo).
- Número honesto verificado: 2280 recolectados; corridos y GREEN los aquí reproducidos.
  (Los 5 test top-level test_mvp_golden_output.py etc. recolectaron 0 en esta invocación:
   requieren marker/conftest; reportados como UNKNOWN, NO sumados.)
SECRETOS:
- Scan de verification/ + docs/audit: solo api_key="proxy" en 3 ficheros (banco_trace_05_control.py,
  critica_control.py). "proxy" es PLACEHOLDER de test de proxy local, NO un secreto real.
  El escáner CB-S01 (regex Bearer/api_key con valor >=8 chars) NO los marca (valor <8 / no es real). CLEAN.
ÉXITO FABRICADO:
- Ningún artefacto JSON reclama PASS/VERIFIED sin evidencia de respaldo tras revisión de los
  campos status/result en verification/. CB-X02 declara GO_WITH_LIMITS con áreas NO_GO honestas.
INTEGRIDAD DE COMMITS:
- Los 25 commits ahead tocan solo .md/.json/.py/.txt/.yml/.spec (auditoría/tests/docs). Sin cambios
  de código ajenos. reflog main: solo fast-forward + branch create. SIN force-push ni borrado de ramas.
VEREDICTO ADVERSARIAL: INTEGRIDAD OK (sin secretos, sin éxito fabricado, sin reescritura de historia)
PERO el TITULAR "2357 tests GREEN" es INEXACTO (doble conteo). Corregir el titular a 2280 recolectados
o dejar claro que 2357 cuenta el run CB dirigido por separado. Esto es un defecto de REPORTING, no de tests.

## 10. VEREDICTO CB-00: GREEN (inventario completo, SHA sellado, evidencia etiquetada)
GATE-BASE depende de CB-01 (procedencia) — ver informe CB-VERIFICATION y subagente adversarial.
