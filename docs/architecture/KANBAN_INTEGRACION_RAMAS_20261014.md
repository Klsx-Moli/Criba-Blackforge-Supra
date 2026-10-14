# KANBAN — INTEGRACIÓN DE RAMAS AL MONOREPO (TAREA_UNIFICADA_V3)

Fecha: 2026-10-14
Base de medición: origin/main = defd0fd9955c5aaf3f7ff8b23fdf016639ed062b
Checkout: C:\ASTRA_WORK\Criba-Blackforge-Supra (rama hermes/cloud-provider-layer-20261013, HEAD 4f2c8c1)
Writer: Hermes (único). NO merge/push a main sin OK explícito de moli.

## CÓMO LEER ESTE KANBAN

Cada tarjeta clasifica ramas por NATURALEZA, no mecánicamente una por rama.
Las ramas ya absorbidas en main NO generan tarjeta de merge (sería ficticio);
se listan aparte como "archivo". Las ramas BLACKFORGE quedan en HARD_PAUSE.

Vocabulario de evidencia (obligatorio en cada tarjeta cerrada):
- VERIFIED_BY_EXECUTION: comandos ejecutados esta sesión, salida real.
- INFERRED: derivado de evidencia, no comprobado directo.
- DESCONOCIDO: no verificable en el entorno actual.
- NO_EXISTE_FISICAMENTE: la ruta/fichero no existe en disco.

Regla anti-goodhart: un test en verde acredita ESE test. No es validación
científica de CRIBA/SUPRA ni promoción de D3/D4/D6.

---

## BLOQUE 0 — RECONCILIACIÓN DE ESTADO (sin esto, nada se puede integrar bien)

### K-INT-00: Reconciliar los documentos de estado que se contradicen
Naturaleza: deuda documental. Bloquea la correcta clasificación de todo lo demás.
 Problema medido (VERIFIED):
- CHECKPOINT.md dice: 2026-08-25, rama feat/gguf-semantic-integration, commit cd49109, 500 tests.
- STATE_BASELINE_2026-10-11.md dice: HEAD 83d50ddd, 2357 tests verdes (CB-VERIFICATION).
- HANDOFF.md dice: suite CRIBA 2074 passed seed fija (rama aislada).
Tres documentos, tres cifras, tres fechas. No se puede afirmar "cuántos tests
tiene main" sin reconciliarlos.
 Reglas de ejecución:
- NO inventar una cifra. Medir la real: pytest tests/ -q sobre main (o la rama
  a integrar) con el venv del proyecto, seed fija.
- Marcar cada documento como VIGENTE / OBSOLETO / HISTÓRICO con fecha y SHA.
- NO purgar histórico (RESIDUAL_HISTORICAL declarado honesto, como en G1).
- Reescribir un ÚNICO STATE.md canónico que apunte a los demás.
 Gate: documento canónico con una sola cifra de tests, VERIFIED_BY_EXECUTION.
 Depende de: nada. Es la primera.
 Riesgo: bajo (docs). Coste: 1 ejecución de suite larga (8-20 min) + redacción.

---

## BLOQUE 1 — INTEGRACIÓN DE TRABAJO VIVO (commits únicos reales sobre main)

Estas ramas tienen trabajo NO presente en main. Se agrupan por dominio para
reducir el número de merges y los conflictos. Cada grupo se integra en UNA rama
de integración aislada, se verifica, y solo entonces se propone merge.

### K-INT-01: Integrar núcleo del INTÉRPRETE/BANCO (banco-grammar + banco-trace)
Ramas: hermes/banco-grammar-04 (7 commits), hermes/banco-trace-04a-20261010 (3 commits)
Dominio: criba-blackforge/src/criba/interprete/{banco,contrato,puerto,openai_compatible,seleccion}.py + shadow_window.py + ui/actions.py
Superposición: banco-grammar y banco-trace tocan los MISMOS ficheros núcleo.
  Deben integrarse JUNTAS y en orden, no por separado (conflicto seguro).
 Trabajo único vivo (VERIFIED):
- banco-grammar-04: topes de grammar, brevedad en prompt, detección campo
  truncado, pytest-randomly + pytest-qt en dev deps, fuzzing OpenAPI SUPRA
  (schemathesis), banco_trace_05 seeds a/b + crítica control.
- banco-trace-04a: schema con $defs+$ref, cap_hit, clasificación anclada de
  errores, seed fija.
 Reglas de ejecución:
- Rama de integración aislada desde main. NO tocar main.
- Orden: aplicar banco-trace primero (base), luego banco-grammar encima.
- pyproject.toml y uv.lock: revisar que las dev-deps nuevas no rompan el venv
  del proyecto ni el CI Windows.
- Verificar con: pytest tests/unit/test_interpreter_hardening.py
  test_local_interpreter_m1.py test_schema_validator_alignment.py
  test_bank_error_classification.py -q, luego suite completa seed fija.
 Gate: suite CRIBA completa seed fija, 0 failed, sobre la rama integrada.
 Conflicto esperado: ALTO (mismos ficheros). Resolver conservando comportamiento.
 Riesgo: medio (toca motor de inferencia).

### K-INT-02: Integrar trabajo de UI/runtime deep-execution (RESIDUAL)
Rama: hermes/deep-execution-20261005 (9 commits)
 Dominio: shadow_window.py, model_runtime.py, supra_dossier.py, ui/actions.py,
  model_settings_dialog.py + tests M2.
 Estado medido (VERIFIED): CASI TODO ABSORBIDO en main.
- model_runtime.py, supra_dossier.py, test_shadow_recovery_identity.py,
  test_planning_scope_relationships.py, test_m2_vertical_slice_e2e.py,
  test_model_save_selects.py, test_b03_replay_restart_contract.py: 0 diff = absorbidos.
- DIFERENCIA VIVA: actions.py (88 líneas) y model_settings_dialog.py (13 líneas).
  main ELIMINÓ un bloque supra_result_status (status_label + scroll) que
  deep-exec CONSERVA. Es una divergencia de decisión, no trabajo perdido.
 Reglas de ejecución:
- NO hacer merge automático. Primero DECIDIR con moli: ¿main acertó al quitar
  supra_result_status, o deep-exec al conservarlo? Es una decisión de UX.
- Si se conserva deep-exec: portar manualmente ese bloque, no merge ciego.
- Verificar test_shadow_interpreter_journey.py y test_m2_selected_interpretation.py.
 Gate: diff semántico revisado por moli; tests M2 en verde.
 Riesgo: bajo (residuo pequeño) pero requiere decisión humana, no técnica.

### K-INT-03: Integrar banco CB-01..CB-04 (procedencia + diagnóstico + journey)
Ramas: cb01-bank-provenance (2), cb02-structured-diagnostics (1),
  cb03-journey-e2e (1), cb04-bank-diagnosis (1)
Dominio: verification/{_provenance,banco_trace_05_control,journey_e2e_no_model,
  recovery_reader}.py, src/criba/interprete/diagnostico.py, docs/audit/CB-04.
Estado: 4 ramas de la tanda CB, cada una 1 commit, tocando ficheros distintos
  (baja superposición entre sí, pero todas behind=36 de main → necesitan rebase).
 Reglas de ejecución:
- Rebase cada una sobre main actual ANTES de integrar (behind 36).
- Orden sugerido: cb01 (procedencia, base) -> cb02 (diagnóstico) -> cb04
  (diagnóstico banco, solo doc) -> cb03 (journey E2E).
- cb03 toca verification/ que es read-only-ish: no ejecuta, solo añade harness.
 Gate: journey_e2e_no_model.py corre sin modelo; diagnosis doc presente.
 Riesgo: bajo-medio (código de verificación, no de producto).

### K-INT-04: Integrar auditoría de convergencia CBS (solo documentación)
Ramas: hermes/cbs-pr8-11-convergence-audit (3), hermes/cbs-continuity-memory-20261005 (4)
Dominio: docs/architecture/*, docs/roadmap/*, docs/testing/*. PURO DOCS.
Estado (VERIFIED): NO en main. Trabajo de auditoría y contratos canónicos.
 Reglas de ejecución:
- Merge limpio (sin conflicto de código, solo docs).
- Revisar que no contradiga el STATE.md canónico de K-INT-00.
 Gate: docs presentes, coherentes con el estado canónico.
 Riesgo: muy bajo.

---

## BLOQUE 2 — ARCHIVO (trabajo YA INTEGRADO en main; NO merge)

Estas ramas tienen su HEAD ya incluido en main (VERIFIED con
git merge-base --is-ancestor). Generar tarjeta de merge sería ficticio.
Acción: etiquetar como ARCHIVADAS, opcionalmente borrar la rama local SOLO con
OK de moli (regla dura: NO borrar ramas sin autorización).

- candidate-20261009 (19f9085): HEAD en main. PR #16 lineage.
- codex/interpreter-hardening-20261004 (2dc0094): HEAD en main.
- hermes/astra/shadow-supra-20261002 (b91e43c): HEAD en main.
- hermes/reconcile-deep-execution-20261009 (9a8af79): HEAD en main. PR #17.
- hermes/local-snapshot-20261009-main-baseline (b845aeb): snapshot de un JSON
  de verificación. Archivo, no integración.
- hermes/audit-snapshot-20261009 (204c18f): snapshot doc de continuidad.

### K-ARCH-01: Snapshots de verificación — decidir si se preservan como artefactos
Ramas: hermes/local-snapshot-20261009-dossier, -convergence-audit,
  -pr9-persistence, -main-baseline
Naturaleza: NO son trabajo de producto; son copias de artefactos de verificación
  (JSONs de blackforge_selector_report, no_leak_plugin.py, etc.).
Decisión de moli: ¿preservar como artefactos históricos en docs/audit/, o
  archivar la rama? Regla de moli: NUNCA borrar remote-gone sin verificar
  commits únicos. Estos tienen contenido único (artefactos) aunque el código
  esté absorbido.
 Gate: inventario de artefactos únicos por rama, decidido por moli.

---

## BLOQUE 3 — BLACKFORGE (HARD_PAUSE, NO se integra sin OK explícito de moli)

Estas ramas tocan BLACKFORGE. Regla dura vigente: BLACKFORGE inerte, no
inicializar, sin key, sus tests no bloquean el producto activo. NO se mergean
en este ciclo. Se listan para que moli decida cuándo (o si) se retoman.

- astra/blackforge-dossier-20261005 (3244879): blackforge_broker/case/slice_authz
  + tests v1. 843-1033 líneas de diff vs main. TRABAJO ÚNICO VIVO pero en pausa.
- astra/blackforge-safety/dfca79-auth-state-failclosed (65a58e5): blackforge_safety
  + tests. Trabajo único en pausa.
- hermes/blackforge-tab-20261011 (c9ff543): tests k6/k7/m2. MEDIDO: sus 3 tests
  nuevos YA están en main. El commit de "BLACKFORGE como pestaña" fue REVERTIDO
  en la propia rama (c228981 revierte 746120b). Archivo, no merge.
- hermes/local-snapshot-20261009-pr9-persistence: artefactos blackforge_agentic/
  pipeline. Snapshot.

### K-BF-00 (BLOQUEADA por HARD_PAUSE): Inventario BLACKFORGE para cuando moli autorice
Naturaleza: preparación read-only. NO ejecuta, NO integra.
Entregable: qué tiene cada rama BF que no esté en main, para decidir futuro.
Regla: este ciclo NO se toca. Solo se documenta el inventario.

---

## BLOQUE 4 — CIERRE FUNCIONAL (lo que falta para que "funcione" de verdad)

Independiente de integrar ramas. Es el gate de producto.

### K-FUNC-01: Arranque VISIBLE en Windows (gate de operador)
Naturaleza: verificación humana. Yo NO puedo hacerla (exige ojos en la ventana).
Estado: offscreen DEMOSTRADO (ShadowWindow construye, BLACKFORGE modules = []).
 Falta: arrancar criba_shadow_main.py desde el venv del proyecto en Windows
 visible y confirmar que NO exige BLACKFORGE y muestra la ventana.
 Gate: GUI_VISIBLE = VERIFIED por el operador.

### K-FUNC-02: Build del .exe (PyInstaller)
Naturaleza: packaging. spec existe (CribaShadow.spec en raíz criba-blackforge).
Estado: NO construido en este ciclo.
 Gate: .exe con SHA256 + smoke test de arranque.

### K-FUNC-03: Revisión spec/recursos de packaging (MIGRATE-4)
Naturaleza: revisión del spec + resources GENERATED. Pendiente en HANDOFF.

---

## ORDEN DE EJECUCIÓN PROPUESTO

1. K-INT-00 (reconciliar docs) — desbloquea todo lo demás.
2. K-INT-04 (docs CBS, sin riesgo) — merge limpio, bajacola.
3. K-INT-01 (intérprete/banco, el grueso) — el trabajo vivo más grande.
4. K-INT-02 (residual deep-execution) — requiere decisión de moli.
5. K-INT-03 (CB-01..04) — rebase + integración.
6. K-ARCH-01 (snapshots) — decisión de moli.
7. K-FUNC-01/02/03 (cierre funcional) — en paralelo, gate de operador.

BLACKFORGE (K-BF-00) NO entra en este ciclo. HARD_PAUSE.

---

## REGLAS DURAS (heredadas, no negociables)

- NUNCA merge/push a main sin OK explícito de moli.
- BLACKFORGE HARD_PAUSE: no reactivar, no key falsa, no bypass.
- NO force-push. Preservar procedencia.
- NO afirmar ejecución sin evidencia real (VERIFIED_BY_EXECUTION).
- NO borrar ramas sin autorización (regla moli: verificar commits únicos antes).
- NO usar conteos históricos de tests: solo counts ejecutados sobre la SHA a integrar.
- gate_windows_full (suite local venv) = AUTORITATIVO. Modal mypy = tipos.
  Modal pytest Linux = EXPERIMENTAL, no sustituye al gate Windows.
- Offscreen != Windows visible. NO marcar done por existencia de ficheros.

## LIMITACIONES DECLARAS (esta sesión)

- NO ejecuté pytest: los counts son de documentos previos, NO re-verificados aquí.
  K-INT-00 existe precisamente para medir la cifra real.
- NO verifiqué el contenido funcional de cada módulo, solo estructura git y diffs.
- NO abrí GUI: arranque visible es DESCONOCIDO hasta gate de operador.
- La clasificación "absorbido en main" es por diff de ficheros clave + ancestry,
  VERIFIED; pero K-INT-02 tiene una divergencia de decisión (supra_result_status)
  que requiere juicio de moli, no solo datos.

---

# HALLAZGOS DE CAMPAÑA (OBSERVED_AT 2026-10-15 00:4x, base main=defd0fd)

Verificación por ejecución del estado real de cada rama candidata. Estos
hallazgos CORRIGEN premisas del kanban original sin fabricar implementación.

## H-CAMP-01: K-INT-03 (cb01-cb04) — PREMISA OBSOLETA, NO integrar
VERIFIED: todos los ficheros de cb01/cb02/cb03/cb04 YA EXISTEN en main defd0fd
(el merge PR#22 audit/fase0-fase1 los absorbió). Ninguno es nuevo.
- cb04: 100% idéntico a main. ARCHIVO.
- cb02 diagnostico.py: main ya lo tiene, reformateado (strings multilínea a una
  línea, mismo contenido). Integrar sería reformateo, no aporte.
- cb03 journey_e2e_no_model.py: main está MÁS AVANZADA (añadió bloque de
  procedencia CB03: SHA/head/plataforma). La rama cb03 además contiene
  `len(abstened) if False else len(abstained)` (código muerto) que main NO tiene.
  Integrar cb03 = RETROCESO (quita procedencia + reintroduce if False). NO integrar.
- cb01 _provenance.py / banco_trace_05_control.py: difieren por formato; main
  ya tiene el contenido.
DECISIÓN: cb01-cb04 → ARCHIVO con evidencia, NO integración.

## H-CAMP-02: K-INT-01 (banco-grammar-04 / banco-trace-04a) — RIESGO DE SEGURIDAD, NO integrar
VERIFIED: la rama banco-grammar-04 NO contiene la función `endpoint_problem()`
en openai_compatible.py. main SÍ la tiene. Es la defensa que RECHAZA:
- credenciales embebidas en URL (user:pass@host),
- http sin TLS a hosts no-loopback (Bearer viajaría sin cifrar),
- esquemas no http/https.
Fuente de la defensa en main: parche CB-X03 (HANDOFF: "conservando endpoint_problem").
Integrar banco-grammar-04 sobre main ELIMINARÍA esta defensa activa.
DECISIÓN: banco-grammar-04 / banco-trace-04a → NO integrar (regresión de seguridad
+ contrato). DIFERIDO hasta revisar qué trabajo único real queda tras absorber
main. Registrar motivo y condición de recuperación.

## H-CAMP-03: K-INT-02 (deep-execution residual) — requiere decisión de moli
La única divergencia viva es supra_result_status en actions.py (main lo quitó,
deep-exec lo conserva). Decisión de UX/producto, no técnica. APARCADA pendiente
de moli. No es bloqueo mecánico.

## RESUMEN DE CAMPAÑA LOCAL
- K-INT-00: CERRADO (STATE.md canónico + 7 correcciones aplicadas).
- K-INT-04: PREPARADO_LOCAL (rama k-int-04-cbs-docs @ 0c289fd). NO en main.
- K-INT-01/02/03: premisa revisada; NO integradas (absorbidas o riesgo). 
  Estado corregido en kanban sin fabricar implementación.
- BLACKFORGE: HARD_PAUSE intacto.
- main: defd0fd intacto. Nada publicado.
SIGUIENTE ELEGIBLE: ninguna integración de rama resta segura sin decisión de
moli (K-INT-02) o sin nuevo trabajo único (K-INT-01/03 absorbidos). Las unidades
ejecutables pasan a ser de cierre funcional (K-FUNC-*), varias de las cuales
exigen aceptación humana (GUI visible) o build local.
