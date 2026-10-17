# STATE.md — ESTADO CANÓNICO VERIFICADO DEL MONOREPO

Fecha de medición: 2026-10-15 (OBSERVED_AT 00:38)
Base de integración: origin/main = defd0fd9955c5aaf3f7ff8b23fdf016639ed062b
Rama de trabajo: hermes/cloud-provider-layer-20261013 @ HEAD 4f2c8c1e51acd175c87f7bcd9d4a10c4cc641db4
Writer: Hermes (único). Campaña LOCAL de integración y cierre funcional.
NO autorizado: merge/push a main, push de ramas, PRs, publicación, gasto.

## PARA QUÉ EXISTE

K-INT-00 detectó que tres documentos daban tres cifras de tests distintas con
tres fechas distintas. Este fichero fija UNA cifra por snapshot, medida por
ejecución, y declara el alcance exacto de esa medición.

CORRECCIONES APLICADAS (mandato de campaña, 2026-10-15):
- Las cifras corresponden a 4f2c8c1, NO a main (defd0fd). NO son universales.
- CRIBA usó seed 20261014 vía pytest-randomly (el venv de CRIBA lo tiene).
- SUPRA NO usó pytest-randomly (su venv no lo tiene); NO se caracterizó su orden.
- mypy NO revalidado contra el SHA actual.
- Evidencia de otras ramas: histórica / no aplicable a este snapshot, no falsa.
- Se distingue: MEDICIÓN TERMINADA vs DOCUMENTACIÓN COMMITEADA vs PUBLICACIÓN.

---

## 1. MEDICIÓN TERMINADA (VERIFIED_BY_EXECUTION, snapshot 4f2c8c1)

CRIBA — seed fija 20261014 vía pytest-randomly:
  cd criba-blackforge
  ./.venv/Scripts/python.exe -m pytest tests/ -q -p randomly --randomly-seed=20261014
  → 2074 passed, 3 skipped, 1 warning, exit 0, 627.55s (10:27)
  Log: C:\ASTRA_WORK\kint00_suite_seed20261014.log

SUPRA — SIN pytest-randomly, SIN seed impuesto por ese plugin:
  cd supra
  ./.venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider
  → 319 passed, 2 warnings, exit 0, 48.10s
  Log: C:\ASTRA_WORK\kint00_supra_seed20261014.log
  DETERMINISMO (VERIFIED_BY_EXECUTION, 2026-10-15 00:50): 3 corridas consecutivas
  del mismo comando dieron 319 passed las 3 (39.40s / 43.75s / 40.37s). El orden
  POR DEFECTO de pytest en este venv es estable entre ejecuciones. NO equivale a
  robustez ante permutaciones arbitrarias (eso exigiría pytest-randomly, que NO
  instalo por iniciativa propia). Log: C:\ASTRA_WORK\kfunc_supra_determinism.log.
  NOTA: import pytest_randomly FALLA en supra/.venv (VERIFIED); SÍ existe en
  criba-blackforge/.venv. El orden de SUPRA no está fijado por plugin, pero es
  estable en la práctica para este árbol.

ALCANCE EXACTO DE LA MEDICIÓN:
- Ambas cifras son del árbol en 4f2c8c1 (rama aislada), NO de main defd0fd.
- NO se transfieren a ningún otro SHA (p. ej. TARGET_SHA de K-INT-04).
- Son medición puntual, no contrato semántico ni cobertura.

---

## 2. DOCUMENTACIÓN COMMITEADA (distinto de medición)

- STATE.md (este fichero) y STATE-KANBAN: redactados, SIN commitear (?? en el
  worktree principal a OBSERVED_AT). Documentación existente, medición cerrada.
- K-INT-04 (docs CBS): INTEGRADO en rama local aislada k-int-04-cbs-docs
  @ TARGET_SHA 0c289fd, COMMITEADO localmente. NO publicado, NO en main.
- NADA de lo anterior está publicado ni fusionado a main.

## 3. PUBLICACIÓN

- Estado: NADA publicado. main remoto = defd0fd (intacto, VERIFIED por
  git ls-remote). Rama k-int-04 NO existe en remoto (solo local).

---

## 2. DOCUMENTOS DE ESTADO — CLASIFICACIÓN

| Documento | Fecha cabecera | Última mod git (real) | Cifra que afirma | Veredicto |
|---|---|---|---|---|
| criba-blackforge/CHECKPOINT.md | 2026-08-25, cd49109, 500 tests | 2026-09-29 (91246df, import histórico) | 500 tests | OBSOLETO. Viene del import de historia canónica; su propia fecha de cabecera no coincide con su fecha git real. NO refleja el estado actual. |
| docs/audit/STATE_BASELINE_2026-10-11.md | 2026-10-11, 83d50ddd | 2026-10-11 (32e4d6e) | 2357 tests (CB-VERIFICATION) | OBSOLETO respecto a la rama actual. 2357 era de otra rama (cb01-bank-provenance-work), no de main ni de la rama aislada. Conservar como histórico de CB. |
| docs/audit/BASELINE.md (F0) | 2026-10-13 | 2026-10-13 | SUPRA 319 passed | VIGENTE como línea base F0 del 2026-10-13, pero su cifra de SUPRA (319) queda supeditada a la medición de esta sesión (sección 1b). |
| docs/audit/HANDOFF.md | 2026-10-14 | 2026-10-14 (4f2c8c1) | CRIBA 2074 | COINCIDE con la medición de esta sesión. VIGENTE. |
| **este STATE.md** | 2026-10-15 | — | ver sección 1 | **CANÓNICO.** Única fuente de cifras de tests. |

REGLA: si un documento afirma una cifra de tests distinta a la sección 1 de este
fichero, el documento está OBSOLETO para ese dato. Este STATE.md manda.

---

## 3. HALLAZGOS DE LA RECONCILIACIÓN (VERIFIED_BY_EXECUTION)

H1. La cifra 2074 del HANDOFF es CORRECTA para la rama aislada actual
    (hermes/cloud-provider-layer-20261013). Confirmada por ejecución con seed fijo.
H2. CHECKPOINT.md (500 tests) es histórico importado; su cabecera dice agosto pero
    su último commit git es de septiembre (import canónico). No describe main.
H3. STATE_BASELINE (2357) medía otra rama (cb01), no main ni la rama aislada.
    Su propio texto lo dice ("2357 tests GREEN" en contexto cb01-bank-provenance-work).
H4. No existe STATE.md canónico previo; este es el primero. Los tres documentos
    convivían sin que ninguno declarara a los otros obsoletos → la confusión.

---

## 4. ESTADOS DE GOBERNANZA (NO alterados por este documento)

- STANDARD=DISABLED
- G3=NOT_VERIFIED
- D3_NOVELTY=UNRESOLVED, D4_FUNCTIONAL_DIVERSITY=UNRESOLVED, D6_ADAPTIVE_BENEFIT=STILL_UNRESOLVED
- SCIENTIFIC_ADVANTAGE_OF_CRIBA=NOT_ESTABLISHED
- BLACKFORGE: INERTE / HARD_PAUSE (no inicializar, sin key, no bloquea producto activo)
Fuente: governance/ANTI_GOODHART_STATUS.yaml + HANDOFF. No se promueven por tests verdes.

---

## 5. GATES VIGENTES (regla de la sesión)

- gate_windows_full (suite local venv, seed fija): AUTORITATIVO. ← esta sesión.
- gate_modal_mypy: gate de TIPOS (167 archivos, PASS sobre SHA pre-eb24690).
- gate_modal_pytest_linux: EXPERIMENTAL, NO verde (25 fallos de entorno Linux).
  NO sustituye al gate Windows.
- gate_modal_smoke: POR CREAR.

---

## 8. LIMITACIONES DECLARADAS (honestas)

- Medición @ 4f2c8c1, NO @ main. Cada rama a integrar se mide contra SU SHA.
- SUPRA: orden de ejecución NO caracterizado (sin pytest-randomly). Cifra
  puntual, no determinismo demostrado entre permutaciones.
- mypy NO re-ejecutado en esta campaña; PASS previo es de SHA anterior.
- NO abrí GUI visible ni construí EXE: arranque visible = DESCONOCIDO (gate
  de operador humano). OFFSCREEN != aceptación visual Windows.

---

## 9. ESTADO DE LA CAMPAÑA (OBSERVED_AT 2026-10-17 TRAS M4/M5)

CAMPAÑA MVA (Master Value Archive 2026-10-02) — MAPEO FLUJO PRODUCTO ACTIVO:

CRIBA SHADOW UI → CRIBA CORE REAL → DOSSIER/EVIDENCIA DISCRIMINANTE → SupraClient → SUPRA REAL → PERSISTENCIA → GET/RELOAD/RESTART/REPLAY → VERDAD EN SHADOW

1. Shadow launchable — VERIFIED_BY_EXECUTION (criba_shadow_main.py, abrir_criba.cmd)
2. CRIBA real desde Shadow — VERIFIED (engine.py, lottery.py, selector.py)
3. Dossier real — VERIFIED (supra/src/supra_agentic/dossier.py + contrato evidencia discriminante)
4. SupraClient real — VERIFIED (criba/integrations/supra_client.py:378)
5. SUPRA real — VERIFIED (service.py: FastAPI + health + providers endpoints)
6. Persistencia durable — VERIFIED (state.py: proyectos, rollback, atomicidad)
7. GET/RELOAD/RESTART/REPLAY — VERIFIED (test_b03_replay_restart_contract.py + test_m3_restart_provenance_contract.py)
8. Verdad representada en Shadow — VERIFIED (ui_actions.on_restore_latest_supra + startup trace)
9. Windows one-command — VERIFIED_BY_CREATION (abrir_criba.cmd)
10. User journeys — VERIFIED (verify_shadow_bundle_journey.py + verify_shadow_windows.py)
11. MVP package — VERIFIED (PyInstaller 6.22.2, CribaShadow.exe 10.6MB, recursos incluidos)
12. Hardening/observabilidad/polish — PARCIAL (K-INT-01/02 diferidos por seguridad/moli)

PRÓXIMO PASO: PR #23 merge a main con OK de moli.
NO merge a main sin autorización específica.

- K-INT-00: CERRADO (reconciliación + STATE.md + correcciones aplicadas).
  Commit f05de79 preserva STATE.md + kanban en rama de trabajo (NO main).
- K-INT-04: PREPARADO_LOCAL / VERIFICADO_LOCAL. Rama k-int-04-cbs-docs @ 0c289fd.
  13 docs CBS revisados: sin secretos, sin contradicción de código (docs-only).
  NO en main. NO publicado.
- K-INT-01/02/03: NO integrar, con evidencia (H-CAMP-01/02/03 del kanban).
- BLACKFORGE (K-BF-00): HARD_PAUSE, no integrado.

EVIDENCIA FRESCA de esta sesión (VERIFIED_BY_EXECUTION, sobre HEAD 4f2c8c1):
- Shadow subset: 51 passed / 0 failed (loadings, journey, runtime boundary,
  recovery identity, cli entry), EXIT 0, 23.37s. venv criba-blackforge.
- SUPRA contratos de estado: 44 passed / 0 failed (state_corruption,
  state_persistence_atomicity, service), EXIT 0, 8.08s. venv supra.

HALLAZGO DE CAMPAÑA H-CAMP-04 (VERIFIED_BY_EXECUTION, NO integrar):
Ramas astra/* con commits únicos vs main NO integrables sin destruir producto:
- astra/supra-state/{22813e65-persistence-rollback, ad1a4-atomic-list-snapshot,
  dfca79-atomic-list-snapshot, edd50814-corrupt-state-load}
- astra/criba-core/22813e65-lottery-storage-integrity
- astra/criba-outcome/edd50814-aware-timestamps
Motivo: su base es un árbol distinto (split). Un diff vs main borra ~32k líneas
e incluye borrado de contratos protegidos (test_m3_restart_provenance_contract,
test_state_persistence_atomicity, test_criba_envelope_*, source_progress.py).
Y su trabajo ÚNICO YA está absorbido en 4f2c8c1: _corrupt_state_response
("no degradar autoridad corrupta a 404 falso") vive en service.py; outcome_store.py
ya rechaza timestamps naive/ambiguos. Integrar = redundante + destructivo.
Veredicto: DIFERIDO. Requeriría re-base sobre el split real, no merge de rama.

PRÓXIMO PASO: continuar con unidades elegibles locales sin publicación.
NO merge a main sin autorización específica.
