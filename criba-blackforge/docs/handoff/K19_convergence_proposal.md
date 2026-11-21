# K19 PROPOSICIÓN DE CONVERGENCIA A MAIN (DOCUMENTO ÚNICAMENTE)
# Modelo: poolside/laguna-s-2.1:free | Relay: Laguna
# HEAD: b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0 (NO commit/push realizado — SOLO LECTURA)
# Generado: 2026-10-24

## NOTA DE ALCANCE
Per PROMPT_09 y MASTER_TODO línea 252: STANDARD=OFF, executor OFF.
NO commit, push, merge, release, deploy. NO edición de PR #23.
Esta es una propuesta documental SOLO.

## 1. MATRIZ DE CONVERGENCIA POR ARCHIVO

| Archivo | Cambio | Proveniencia | SHA256 NOW | SHA256 HEAD | Contenido | Gates | Status |
|---------|--------|-------------|------------|-------------|-----------|-------|--------|
| .hermes/iie/gen_registry.py | Override revertido | S06 (writer Hermes) | 2dd28d7ac1c2... | ddf9730a25dc... | Elimina override S06 T054/T061 → PLANNED canónico restaurado | canon check: technique_registry regenerado con T054/T061=PLANNED | VERIFIED |
| .hermes/iie/reg_parts/p3.txt | Additivo | S06 (writer Hermes) | 46fa4930139b... | e1d72f117510... | Añade entradas T104/T111 como técnica | registry coherencia: T104/T111 aparecen en YAML | VERIFIED |
| benchmarks/innovation/criba_adapter.py | Nuevo | S06 (writer Hermes) | b7fa4acf8ef1... | (nuevo) | Benchmark MCDA adapter (114 líneas) | test_mcda_adapter.py: 4 pass | VERIFIED |
| benchmarks/innovation/harness.py | Nuevo | S06 (writer Hermes) | 204b4c9162a2... | (nuevo) | Harness S06 (18 líneas) | No direct tests | NEW |
| data/intelligence/technique_fichas.yaml | Additivo | S06 (writer Hermes) | 59362f7c2b6e... | (modificado) | 52 líneas: fichas T104/T111 | registry coherence (parte del YAML regen) | VERIFIED |
| data/intelligence/technique_registry.yaml | Regenerado | gen_registry.py | f4b106b30ca7... | (regen) | T054/T061=PLANNED (canon restored) | test_technique_runtime_traceability: PASS | VERIFIED |
| src/criba/intelligence/execution.py | Additivo (4 líneas) | S06 (writer Hermes) | 0cf735f3caad... | (modificado) | T104/T111 en _INPUT_ADAPTERS (4 añadidos) | test_registry_module_resolution: 7 pass | VERIFIED |
| src/criba/inventar.py | Additivo | S06 | e2a44ead6b4e... | (modificado) | 7 líneas añadidas | Parte del delta S06 | NEW |
| src/criba/lottery.py | Additivo | S06 | e80289e2ae2b... | (modificado) | 26 líneas añadidas | test_lottery_family_delivery: pass | NEW |
| src/criba/ui/actions.py | Additivo (77 líneas) | S06 (writer Hermes) | 53bcf2592f97... | (modificado) | Shadow UI wiring: score_idea → mcda_dossier → value_score | test_s06_shadow_mcda_integration: 3 pass | VERIFIED |
| src/criba/ui/widgets.py | Additivo (19 líneas) | S06 | 325b0b1ed4d0... | (modificado) | UI elements for Shadow ranking | No direct tests | NEW |

## 2. ARCHIVOS NUEVOS (UNTRACKED)

| Archivo | Tipo | SHA256 NOW | Tests asociados | Status |
|---------|------|------------|-----------------|--------|
| src/criba/intelligence/mcda_adapter.py | Module | aa96cb9c26f3... | test_mcda_adapter.py: 4 pass | VERIFIED |
| src/criba/intelligence/scoring/__init__.py | Module | 7d2ab6655a14... | test_t104_t111_scoring.py: 11 pass | VERIFIED |
| src/criba/intelligence/scoring/evidence.py | Module | 39391388a212... | test_t104_t111_scoring.py: 11 pass | VERIFIED |
| src/criba/intelligence/invention/recombination.py | Module | 32a70b8b8546... | test_t054_t061: 22 pass, test_t061_wiring: 5 pass | VERIFIED |
| tests/intelligence/test_mcda_adapter.py | Test | c6924ee409e5... | 4 pass | VERIFIED |
| tests/intelligence/test_s06_shadow_mcda_integration.py | Test | 4b930f7fb0a9... | 3 pass | VERIFIED |
| tests/intelligence/test_s06b_shadow_technique_action.py | Test | 196066fb254a... | 1 pass, 3 xfail (post-revert) | VERIFIED |
| tests/intelligence/test_t054_technological_recombination.py | Test | f10d77b8e067... | 22 pass | VERIFIED |
| tests/intelligence/test_t061_attribute_substitution.py | Test | 8678e2f204b4... | Verificado: 22 pass (HANDOFF §5.4.9) | VERIFIED |
| tests/intelligence/test_t061_wiring.py | Test | 5cac5472ac12... | 5 pass (HANDOFF §5.4.8) | VERIFIED |
| tests/intelligence/test_t104_t111_scoring.py | Test | 99fb813e5ce1... | 11 pass | VERIFIED |
| tests/intelligence/test_registry_module_resolution.py | Test | 7e7dbeb49fca... | 7 pass | VERIFIED |
| tests/unit/test_lottery_family_delivery.py | Test | 5b7df06a2446... | Part of K06 unit suite | VERIFIED |
| tests/unit/test_selection_report_attribution.py | Test | cb918cfd0d19... | Part of K06 unit suite | VERIFIED |
| tests/unit/test_selection_report_persistence.py | Test | ebc97d84b3ac... | Part of K06 unit suite | VERIFIED |
| tests/unit/test_shadow_absent_score_contract.py | Test | 6833d52561dc... | Part of K06 unit suite | VERIFIED |

## 3. GAPS

### Gap 1: T104/T111 NO pasan por el dispatcher canónico
- Registry YAML marca T104/T111 = PLANNED → execute_technique("T104") levanta ExecutionError
- El wiring productivo funciona SOLO vía mcda_adapter.score_idea → criba.mcda.score → actions.py:672
- Esto es INTENCIONAL (Shadow bypass) pero representa un gap de arquitectura
- ADR pendiente: docs/arch/ (K19 — no resuelto en este relay)

### Gap 2: No integration end-to-end productivo T104/T111
- Unit tests cubren producer→consumer aislados
- NO test demuestra ranking Shadow usa composite para ordenar ideas reales (handoff §5.8)
- test_s06_shadow_mcda_integration.py cubre mcda_adapter→result, NO actions.py:672 con packet real

### Gap 3: Test count discrepancy
- Handoff §1 dice "12 modified + 16 untracked" pero git muestra 13 modified + 17 untracked
- Handoff §5.3 dice "15 passed" para subset pero reproducción da 14 pass
- Handoff §5.2 dice "75 passed/3 xfailed" — REPROCIDO exactamente

## 4. RESTRICCIONES RESPETADAS
- NO commit/push/merge: ✓ (HEAD imutado b07147b)
- NO push de rama: ✓
- NO edición de PRs: ✓
- NO cambios globales/instalaciones: ✓ (.pth intacto, .venv no reinstalado)
- NO modelo/llamadas reales: ✓ (solo unit tests)
- NO reset/clean/stash/rebase: ✓
- Backup separado preservado: ✓ (b845aeb baseline intacto)

## 5. GATES PARA CONVERGENCIA
1. CAPABILITY_PROOF §79 (T054/T061): PENDING_OWNER_DECISION — requiere 986+ tests, mypy clean, determinismo + attestation A2 (A3.G1 NOT_AVAILABLE)
2. SHADOW_BYPASS_REVIEW (T104/T111): PENDING_OWNER_DECISION — ADR en docs/arch/ pendiente
3. ACCESS_VIOLATION_REPRO: PENDING_HUMAN_VERIFICATION — K17 requiere Windows + Qt + datos runtime reales
4. COMMIT_AUTH: PENDING_OWNER_DECISION — RC-24 prohíbe commit antes de autorización owner
5. WINDOWS_BUILD_SMOKE: PENDING_HUMAN_VERIFICATION — K16 requiere PyInstaller 3.11 + UI levantable

## 6. PROCEDENCIA POR ARCHIVO
- gen_registry.py, reg_parts/p3.txt, technique_registry.yaml: S06 revert (writer Hermes)
- mcda_adapter.py, scoring/*, evidence.py: S06 nuevos módulos (writer Hermes)
- execution.py: 4 líneas additivas S06 (writer Hermes)
- actions.py: 77 líneas Shadow wiring S06 (writer Hermes)
- inventar.py, lottery.py, widgets.py: additivos S06 (writer Hermes)
- benchmarks/*: S06 harness (writer Hermes)
- recombination.py: restaurado del commit 1fc1b5e (writer Hermes)
- 16 tests: creados por Hermes S06

## 7. CONSUMIDORES VERIFICADOS
- T104/T111: src/criba/ui/actions.py:660-673 (Shadow UI ranking) ✓ verificado
- T104/T111: src/criba/mcda.py:98 (consumer DOMAIN 11) ✓ verificado
- T054/T061: execute_technique → RECHAZADO (PLANNED), 0 consumers productivos ✓ verificado
- T063: execute_technique → IMPLEMENTED, en _INPUT_ADAPTERS ✓ verificado (gateway para P10-T11)
