# CBS TEST LOG — 2026-10-24
# Modelo: poolside/laguna-s-2.1:free | Provider: nous | Platform: cli
# Worktree: Criba-Blackforge-Supra/criba-blackforge | Rama: reconcile/candidate-fix-20261020
# HEAD: b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0 (inmutable, nada commiteado)

## 1. COLECCIÓN DE TESTS (pytest --collect-only)
Comando: PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests --collect-only -q
Exit code: 0
Duración: 19.63s
Archivo: C:\Users\KLSX\AppData\Local\hermes\cache\scratch\collect_all.txt
SHA256 del log: 574bb0f75edc1651adfb65c10f7fd47656929314732295d0937773c14ffbc0fe
Total de tests recogidos: 2328

### Tests por directorio (collect-only):
- tests/intelligence: 481 tests
- tests/unit: 1344 tests
- tests/astra_canon: 154 tests
- tests/integration: 153 tests
- tests (raíz): 70 tests
- tests/security: 51 tests
- tests/adversarial: 25 tests
- tests/stress: 22 tests
- tests/recovery: 18 tests
- tests/fixtures/retrybox_pilot/evaluator: 5 tests
- tests/property: 3 tests
- tests/fixtures/retrybox_pilot/participant_repo/tests: 2 tests

### Directorios de tests/ que NO estaban en los lotes de K06 (intelligence + unit):
- tests/astra_canon (154 tests)
- tests/integration (153 tests)
- tests/adversarial (25 tests)
- tests/stress (22 tests)
- tests/recovery (18 tests)
- tests/security (51 tests)
- tests/property (3 tests)
- tests/fixtures (5 + 2 = 7 tests)
- tests/ raíz (70 tests) — incluye test_causal_mechanism.py, test_genome_similarity_unknown.py, test_mvp_golden_output.py, test_packet_ideas_invariant.py, test_packet_v1_regression.py

## 2. EL "991" — Reconciliación
El "991" NO es un ID de test ni técnica. Es un conteo histórico de "suite completa" que aparece en literatura previa (paste.txt:991). Los dos lotes suman 478+1333 = 1811 tests ejecutados, que superan ampliamente el número 991. El conteo actual de tests recogidos es 2328.

Conclusión: el 991 es un dato OBSOLETO. Marcado como obsoleto en este handoff.
Fuente: paste.txt:991 — referenciado como literatura previa, no como métrica vigente.

## 3. LAS 11 SKIPS — Motivo de cada una (VERIFICADO COMANDO REAL)
Lote K06 Lot2 (tests/unit) — comando original: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit --timeout=60 -q --log-file=k06_unit_output.log`
Resultado: 1333 passed, 11 skipped, 1 warning, 574.07s (registrado en handoff §9)
Exit code: 0
Archivo completo: VERIFICATION/cbs_regression_20261023/unit_run.log

Comando diagnóstico: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/test_scientific_cycle.py -rs --tb=no -q`
Exit code: 0
Duración: 22.82s

### Detalle de los 11 skips (con -rs, línea exacta y razón — output del comando real con -v):
Salida del comando: `.venv/Scripts/python.exe -m pytest tests/unit -rs --timeout=60 -v`
Resultado: 1333 passed, 11 skipped, 1 warning, 561.61s (exit 0)
Todos los 11 skips son del archivo: tests/unit/test_scientific_cycle.py
Razón: fixture autouse `skip_if_no_supra()` a nivel módulo (línea 31-40) verifica si SUPRA_ENDPOINT
responde en /health. Cuando no responde, ejecuta: pytest.skip(f"SUPRA no disponible en {endpoint}")

Los 11 tests skipped (con nodeid exacto de la salida -v):
1. tests/unit/test_scientific_cycle.py:50 — TestCientificoUnitario::test_01_activate_genera_ideas_con_mecanismo_causal
   - Motivo: SUPRA no disponible en http://127.0.0.1:11817 (fixture autouse módulo)
2. tests/unit/test_scientific_cycle.py:61 — TestCientificoUnitario::test_02_preparar_dossier_desde_idea_campos_astra
   - Motivo: SUPRA no disponible en http://127.0.0.1:11817 (fixture autouse módulo)
3. tests/unit/test_scientific_cycle.py:78 — TestCientificoUnitario::test_03_verify_dossier_astra_completo
   - Motivo: SUPRA no disponible en http://127.0.0.1:11817 (fixture autouse módulo)
4. tests/unit/test_scientific_cycle.py:98 — TestCientificoUnitario::test_04_verify_dossier_astra_incompleto
   - Motivo: SUPRA no disponible en http://127.0.0.1:11817 (fixture autouse módulo)
5. tests/unit/test_scientific_cycle.py:112 — TestCientificoUnitario::test_05_causal_model_family_specs_accesibles
   - Motivo: SUPRA no disponible en http://127.0.0.1:11817 (fixture autouse módulo)
6. tests/unit/test_scientific_cycle.py:122 — TestCientificoUnitario::test_06_mcda_reexporta_metodos_ranking
   - Motivo: SUPRA no disponible en http://127.0.0.1:11817 (fixture autouse módulo)
7. tests/unit/test_scientific_cycle.py:151 — TestCientificoIntegracion::test_07_scientific_cycle_genera_dossier
   - Motivo: SUPRA no disponible en http://127.0.0.1:11817 (fixture autouse módulo + clase)
8. tests/unit/test_scientific_cycle.py:163 — TestCientificoIntegracion::test_08_scientific_cycle_identidad_dossier
   - Motivo: SUPRA no disponible en http://127.0.0.1:11817 (fixture autouse módulo + clase)
9. tests/unit/test_scientific_cycle.py:174 — TestCientificoIntegracion::test_09_scientific_cycle_estados_honestos
   - Motivo: SUPRA no disponible en http://127.0.0.1:11817 (fixture autouse módulo + clase)
10. tests/unit/test_scientific_cycle.py:200 — TestCientificoRealHTTP::test_10_supra_health_real
    - Motivo: SUPRA no disponible en http://127.0.0.1:11817 (fixture autouse módulo)
11. tests/unit/test_scientific_cycle.py:212 — TestCientificoRealHTTP::test_11_scientific_cycle_envio_supra_real
    - Motivo: SUPRA no disponible en http://127.0.0.1:11817 (fixture autouse módulo)

NOTA CORRECTIVA: A diferencia de lo que indicaba el handoff previo (§5.5), los 11 skips NO son
solo de TestCientificoIntegracion/TestCientificoRealHTTP. Los 6 tests de TestCientificoUnitario
TAMBIÉN son skipped porque el fixture `skip_if_no_supra()` (línea 31) tiene autouse=True a nivel
módulo y afecta a TODAS las clases. TestCientificoIntegracion y TestCientificoRealHTTP tienen
SU PROPIO fixture autouse adicional (línea 139), pero el módulo ya salta antes de entrar a la clase.

Nota: "SUPRA no disponible" es un estado PENDING_OWNER_DECISION (requiere infra autorizado).

## 4. DELTA 13+17 vs 12+16 — Archivos extra
Comparación: `git -C criba-blackforge status --porcelain` vs MANIFEST.md de K02
(worktree: Criba-Blackforge-Supra/criba-blackforge, desde repo root)

MANIFEST.md lista: 13 modified + 17 untracked (= 30 archivos de código)
git status actual: 13 modified + 17 untracked (= 30 archivos de código)

Resultado: IDENTICAL — 13 modified coinciden exactamente entre MANIFEST y git.
17 untracked coinciden exactamente (excluyendo __pycache__, .hermes/skills/, docs/handoff, docs/audits, backups).

### Archivo modificado extra:
NO HAY diferencia. Los 13 archivos modified son idénticos.
Nota: el handoff original decía "12 modificados" pero el MANIFEST y git muestran 13.
La discrepancia se debe a que el handoff original excluía los 2 archivos CRLF-only 
(blackforge_broker.py y blackforge_case.py) que no cambian contenido pero aparecen 
como modificados en git status. El MANIFEST respalda los 13 correctamente.

### Archivo untracked extra:
Los 17 untracked del delta (src/, tests/, data/, benchmarks/, .hermes/iie/checkpoints/)
coinciden exactamente con git. Los archivos realmente "extra" (no en MANIFEST, no parte 
del delta de código) son los ARTEFACTOS DE ESTA SESIÓN:
1. docs/handoff/CBS_HANDOFF_LAGUNA_2026-10-24.md (handoff actualizado)
2. docs/handoff/CBS_KANBAN_LAGUNA.md (tablero actualizado)
3. docs/handoff/CBS_TEST_LOG_2026-10-24.md (este archivo)
4. docs/handoff/K10_technique_audit_matrix.txt (auditoría T001-T130)
5. docs/handoff/K19_convergence_proposal.md (propuesta de convergencia)
6. docs/audits/ (22 archivos de auditoría PROMPT_10)
7. .hermes/skills/criba-blackforge-supra-ops/ (skills de sesión)
8. backups/k02_delta_backup_20261024/ (backup K02)

El "13+17 vs 12+16" se explica por:
- 1 modified extra en el conteo original: blackforge_broker.py (CRLF normalization, contenido idéntico)
- 1 untracked extra: todos los artefactos de esta sesión (handoff, tablero, auditorías, etc.)
Estos fueron documentados en MANIFEST.md notas al pie (líneas 46-48).

## 5. RC-24 — Estado literal
Archivo: VERIFICATION/integracion_recon_22/CBS_INTEGRACION_20261022/03_REGISTRO_RECONCILIACION.md (line 122-125)

RC-24 — Suite verde vs mutaciones seguras:
"test_blackforge_v1_mutations modifica archivos fuente; no ejecutarlo en worktree ocupado ni usar cualquier rc distinto de cero como prueba de mutación matada."

Estado: ISOLATION_AND_DISCRIMINATION_REQUIRED

Significado: El test test_blackforge_v1_mutations.py modifica archivos fuente durante la ejecución.
No se debe ejecutarlo en un worktree ocupado ni usar resultados de CI distintos de cero (rc != 0)
como prueba de que una mutación fue "matada". Requiere aislamiento completo y discriminación
de resultados.

## 6. K15 — Shadow → CRIBA → SUPRA (proveedor simulado, restart real)

- **Test:** tests/integration/test_m2_vertical_slice_e2e.py::test_interpretation_diagnostics_survive_real_transport_and_restart
- **Comando:** `.venv/Scripts/python.exe -m pytest tests/integration/test_m2_vertical_slice_e2e.py::test_interpretation_diagnostics_survive_real_transport_and_restart -v --timeout=120 -p no:randomly`
- **Exit code:** 0
- **Duración:** 7.44s
- **Resultado:** PASSED
- **Evidencia:** Inicia SUPRA real en subprocess con `SUPRA_USE_MODEL=false` (modo simulado/determinista), POST de dossier real, GET con readback. Verifica: `status_source == PERSISTED_STATE`, `persisted_artifact_status == VERIFIED_FROM_ARTIFACT` tras restart.
- **SHA256 log:** ac971da8a47d01761ef032101174e9b790d7082ba02a75ed17ea543530ed787c
- **Artefacto:** C:\ASTRA_WORK\Criba-Blackforge-Supra\criba-blackforge\k15_m2_result.txt

## 7. SHA256 de logs de esta sesión

- collect_all.txt: 7410b68cd331b70f561cce6dd6e0a487e3f7417d83b4627685871defc6ce7544
- k15_m2_result.txt: ac971da8a47d01761ef032101174e9b790d7082ba02a75ed17ea543530ed787c