# Kanban Ejecutable Real — CBS K0R..K12

- TARGET_MAIN: 15bc237be5555fcc38bc8a25f80724473c13435b
- BRANCH: hermes/cbs-pr8-11-convergence-audit
- TIMESTAMP_UTC: 2026-10-08
- AUTOR: Hermes (writer)
- Nota: basado en evidencia real (diffs/gh), no en el informe externo (SC-01).

---

## CBS-K0R  Reconstrucción real de ramas, PRs y contratos
**Prioridad:** P0
**Columna inicial:** REVIEW
**Owner:** unassigned
**Dependencias:** ninguna
**Riesgo:** ORANGE

**Problema**
El informe externo describía PR #8–#11 como consenso/evidencia/replay/VOI/shadow
pricing; los diffs reales no contienen esas capacidades (SC-01).

**Alcance permitido**
- Matriz real por PR con base/head SHA y área (ya hecha).
- Registro de SC-01.

**Fuera de alcance**
- Integración, rebase, merge.

**Archivos / subsistemas**
- docs/architecture/pr-8-11-convergence-matrix.md

**Criterios de aceptación**
- PR #8–#12 clasificados por ámbito real y SHA.
- SC-01 registrado con resolución.
- origin/main=15bc237 identificado.

**Verificación requerida**
- Comando real: `git ls-remote origin main`
- Resultado esperado: 15bc237be5555fcc38bc8a25f80724473c13435b
- Evidencia a adjuntar: salida de terminal (VERIFICADO en esta sesión)

**STOP**
- Si checkout y GitHub divergen sin poder determinar remoto canónico.

**Rollback**
- No aplica (solo lectura/docs).

---

## CBS-K0A  Auditoría semántica authz PR8 vs PR11
**Prioridad:** P0
**Columna inicial:** REVIEW
**Owner:** unassigned
**Dependencias:** CBS-K0R
**Riesgo:** YELLOW

**Problema**
PR8 (safety gate) y PR11 (broker/case) usan ambos "authorization" con enums
distintos; hay que decidir si son compatibles o duplicados.

**Alcance permitido**
- Matriz de casos y clasificación (ya hecha).
- Inspección de diffs reales.

**Fuera de alcance**
- Unificar código authz.

**Archivos / subsistemas**
- blackforge_safety.py (PR8), blackforge_case.py / blackforge_broker.py (PR11)
- docs/architecture/pr8-pr11-authz-semantic-audit.md

**Criterios de aceptación**
- Clasificación única emitida: COMPLEMENTARY_WITH_BOUNDARY.
- Matriz de 10 casos mínima documentada.

**Verificación requerida**
- Comando real: `git diff 15bc237..3244879 -- criba-blackforge/src/criba/blackforge_case.py`
- Resultado esperado: revisión de AuthorizationAxis/require_authorized (VERIFICADO por lectura)
- Evidencia a adjuntar: doc de auditoría

**STOP**
- Si aparece contradicción donde uno permite y el otro no decide.

**Rollback**
- No aplica (docs).

---

## CBS-K0B  Readiness de persistencia PR9
**Prioridad:** P0
**Columna inicial:** REVIEW
**Owner:** unassigned
**Dependencias:** CBS-K0R
**Riesgo:** YELLOW

**Problema**
PR9 introduce persistencia SQLite con audit events; hay deuda legacy/crash sin test.

**Alcance permitido**
- Auditoría de esquema/round-trip/legacy (ya hecha).

**Fuera de alcance**
- Migrar datos o cambiar schema.

**Archivos / subsistemas**
- storage.py, blackforge_agentic.py (PR9)
- docs/architecture/pr9-persistence-readiness-audit.md

**Criterios de aceptación**
- Clasificación emitida: READY_AFTER_TESTS_ONLY.

**Verificación requerida**
- Comando real: `git show 1a98b7e:criba-blackforge/src/criba/storage.py` (VERIFICADO por lectura)
- Resultado esperado: SCHEMA_VERSION=1, user_version check, record_event append-only
- Evidencia a adjuntar: doc de auditoría

**STOP**
- Si aparece dependencia oculta de PR11.

**Rollback**
- No aplica (docs).

---

## CBS-K0C  Evaluación línea PR10/PR12
**Prioridad:** P0
**Columna inicial:** REVIEW
**Owner:** unassigned
**Dependencias:** CBS-K0R
**Riesgo:** ORANGE

**Problema**
PR10 parte de shadow-supra (no main) y arrastra 122 archivos vs main; PR12 depende de PR10.

**Alcance permitido**
- Evaluación de acoplamiento (ya hecha).

**Fuera de alcance**
- Rebase o split real de PR10.

**Archivos / subsistemas**
- interprete/*, intelligence/*, shadow_ui/*, supra/* (PR10)
- docs/architecture/pr10-pr12-line-assessment.md

**Criterios de aceptación**
- Clasificación emitida: SPLIT_BEFORE_REBASE (+ PR12 DOCS_ONLY_HOLD).

**Verificación requerida**
- Comando real: `git diff --stat 15bc237 2dc0094 -- criba-blackforge supra`
- Resultado esperado: 122 files changed (VERIFICADO en esta sesión)
- Evidencia a adjuntar: doc de evaluación

**STOP**
- Si se intenta merge directo de PR10 a main.

**Rollback**
- No aplica (docs).

---

## CBS-K1  Contrato canónico de autorización
**Prioridad:** P0
**Columna inicial:** READY
**Owner:** unassigned
**Dependencias:** CBS-K0A
**Riesgo:** YELLOW

**Problema**
PR8 `AuthorizationState` y PR11 `AuthorizationAxis` coexisten con semánticas
distintas; falta un contrato que fije la frontera para evitar divergencia.

**Alcance permitido**
- Redactar contrato de frontera (pre-gate por clase vs autorización ejecutiva
  por nonce) sin cambiar código.
- Definir vocabulario unificado de estados y su mapeo.

**Fuera de alcance**
- Modificar blackforge_safety.py o blackforge_case.py.
- Unificar enums en código.

**Archivos / subsistemas**
- docs/architecture/ (nuevo: authorization-canonical-contract.md)

**Criterios de aceptación**
- Frontera PR8↔PR11 explícita (quién decide qué).
- Mapeo EXPIRED/DENIED/REVOKED/CONSUMED documentado.
- Sin cambios de código.

**Verificación requerida**
- Comando real: revisión humana del contrato contra pr8-pr11-authz-semantic-audit.md
- Resultado esperado: coherencia con el código real
- Evidencia a adjuntar: contrato + diff de solo docs

**STOP**
- Si el contrato exige cambiar semántica de un PR (requiere aprobación).

**Rollback**
- No aplica (docs).

---

## CBS-K2  Contrato de persistencia y schema
**Prioridad:** P0
**Columna inicial:** READY
**Owner:** unassigned
**Dependencias:** CBS-K0B
**Riesgo:** YELLOW

**Problema**
PR9 usa SCHEMA_VERSION=1 con migración que solo sube user_version; la
compatibilidad de columnas legacy no está garantizada.

**Alcance permitido**
- Documentar contrato de schema, versionado y política de migración/legacy.
- Definir comportamiento exigido ante BD previa sin columnas nuevas.

**Fuera de alcance**
- Escribir migraciones reales o alterar storage.py.

**Archivos / subsistemas**
- docs/architecture/ (nuevo: persistence-schema-contract.md)
- referencia: storage.py (PR9)

**Criterios de aceptación**
- Política de compatibilidad legacy definida (cargar o fallar con diagnóstico).
- Versionado y reglas de migración documentadas.

**Verificación requerida**
- Comando real: revisión del contrato contra storage.py real
- Resultado esperado: coherencia con user_version/CREATE TABLE IF NOT EXISTS
- Evidencia a adjuntar: contrato

**STOP**
- Si exige cambio de schema (fuera de alcance).

**Rollback**
- No aplica (docs).

---

## CBS-K3  Estrategia de integración mínima BLACKFORGE
**Prioridad:** P0
**Columna inicial:** BLOCKED
**Owner:** unassigned
**Dependencias:** CBS-K1, CBS-K2, CBS-K0A
**Riesgo:** ORANGE

**Problema**
Definir e (idealmente) ejecutar la integración mínima PR8→PR9→PR11 sobre main en
rama aislada, sin fusionar a main.

**Alcance permitido**
- Crear rama `hermes/cbs-integration-<fecha>` desde 15bc237.
- Cherry-pick de commits de PR8/PR9 tras rebase (requiere autorización de fase).
- Ejecutar suite.

**Fuera de alcance**
- Merge a main.
- Tocar PRs existentes.
- PR10 (bloqueado por split).

**Archivos / subsistemas**
- blackforge_safety.py, storage.py, blackforge_agentic.py, blackforge_case.py,
  blackforge_broker.py, blackforge_slice_authz.py

**Criterios de aceptación**
- Suite CRIBA/BLACKFORGE verde en rama de integración.
- Sin regresión vs baseline de main (CBS-K4).
- Sin cambios a main.

**Verificación requerida**
- Comando real: `cd criba-blackforge && pytest` (comando canónico a confirmar)
- Resultado esperado: PASS sin regresión (NOT_RUN aquí)
- Evidencia a adjuntar: log de pytest

**STOP**
- Si hay conflicto de semántica authz no trivial.
- Si se requiere rebase de PRs existentes (prohibido en esta misión).

**Rollback**
- `git checkout 15bc237`; rama de integración descartable.

---

## CBS-K4  Baseline de tests en main
**Prioridad:** P0
**Columna inicial:** READY
**Owner:** unassigned
**Dependencias:** CBS-K0R
**Riesgo:** GREEN

**Problema**
Sin baseline de main no se puede afirmar "sin regresión".

**Alcance permitido**
- Ejecutar suite en worktree aislado de main.
- Guardar conteos/duración.

**Fuera de alcance**
- Modificar CI o tests.

**Archivos / subsistemas**
- .github/workflows/ci.yml (referencia), criba-blackforge/tests, supra/tests

**Criterios de aceptación**
- Baseline de main documentado y reproducible.

**Verificación requerida**
- Comando real: `gh run list --branch main --limit 5`
- Resultado esperado: runs PASS con conteos (NOT_RUN aquí)
- Evidencia a adjuntar: run IDs / log local

**STOP**
- Si la suite no es reproducible localmente.

**Rollback**
- No aplica.

---

## CBS-K5  Tests críticos authz/broker
**Prioridad:** P1
**Columna inicial:** BLOCKED
**Owner:** unassigned
**Dependencias:** CBS-K1, CBS-K3
**Riesgo:** YELLOW

**Problema**
Falta test de frontera PR8↔PR11 y de replay de nonce en entorno persistente.

**Alcance permitido**
- Añadir tests de frontera y de consumo único de nonce (en rama de integración).

**Fuera de alcance**
- Cambiar código de producto.

**Archivos / subsistemas**
- criba-blackforge/tests/unit/ (test_blackforge_safety, test_blackforge_v1_*)

**Criterios de aceptación**
- Test que pruebe que PR8 DENY bloquea antes de broker.
- Test de replay: segundo reserve con mismo nonce falla.

**Verificación requerida**
- Comando real: `pytest criba-blackforge/tests/unit/test_blackforge_safety.py -q`
- Resultado esperado: PASS (NOT_RUN aquí)
- Evidencia a adjuntar: log

**STOP**
- Si el test requiere ejecutar BLACKFORGE en vivo.

**Rollback**
- Revertir tests añadidos.

---

## CBS-K6  Tests de persistencia y reinicio
**Prioridad:** P1
**Columna inicial:** BLOCKED
**Owner:** unassigned
**Dependencias:** CBS-K2, CBS-K3
**Riesgo:** YELLOW

**Problema**
Sin test de BD legacy (pre-SCHEMA_VERSION=1) ni de recuperación ante crash.

**Alcance permitido**
- Fixture de BD legacy; test de round-trip y corrupción; test de reinicio.

**Fuera de alcance**
- Migrar producción.

**Archivos / subsistemas**
- criba-blackforge/tests/unit/test_storage_decision_evidence.py

**Criterios de aceptación**
- Legacy carga o falla con diagnóstico explícito.
- Round-trip idéntico; corrupción detectada.

**Verificación requerida**
- Comando real: `pytest criba-blackforge/tests/unit/test_storage_decision_evidence.py -q`
- Resultado esperado: PASS (NOT_RUN aquí)
- Evidencia a adjuntar: log

**STOP**
- Si el formato legacy es desconocido (requiere decisión de operador).

**Rollback**
- Revertir tests.

---

## CBS-K7  Decisión sobre rebase/split de PR10
**Prioridad:** P1
**Columna inicial:** BLOCKED
**Owner:** unassigned
**Dependencias:** CBS-K0C
**Riesgo:** ORANGE

**Problema**
PR10 no es rebaseable entero (122 archivos vs main). Hay que decidir split y
qué es portable a main.

**Alcance permitido**
- Definir el split (docs/contract, script, tests, módulos).
- Verificar existencia en main de los módulos objetivo.

**Fuera de alcance**
- Ejecutar el rebase/split.

**Archivos / subsistemas**
- interprete/*, intelligence/*, shadow_ui/*, supra/*

**Criterios de aceptación**
- Plan de split con lista de archivos portables vs acoplados.
- Confirmación de qué existe ya en main.

**Verificación requerida**
- Comando real: `git ls-tree 15bc237 -- criba-blackforge/src/criba/interprete`
- Resultado esperado: lista de módulos presentes/ausentes en main (NOT_RUN aquí)
- Evidencia a adjuntar: salida

**STOP**
- Si el split implica reescribir lógica (fuera de alcance).

**Rollback**
- No aplica (planificación).

---

## CBS-K8  Cierre documental realista
**Prioridad:** P2
**Columna inicial:** READY
**Owner:** unassigned
**Dependencias:** CBS-K0R..K0C
**Riesgo:** GREEN

**Problema**
Consolidar el paquete documental y separar MAIN/EXPERIMENTAL/PLANNED/NOT_VALIDATED;
evitar que PR12 se use como fuente de verdad.

**Alcance permitido**
- Índice de documentos y etiquetado de estado.

**Fuera de alcance**
- Afirmar implementación.

**Archivos / subsistemas**
- docs/architecture/, docs/roadmap/, docs/testing/

**Criterios de aceptación**
- Cada doc etiqueta su estado de evidencia.

**Verificación requerida**
- Comando real: revisión de los docs publicados
- Resultado esperado: etiquetas UNVERIFIED/NOT_RUN presentes
- Evidencia a adjuntar: lista de docs

**STOP**
- Si un doc presenta propuesta como hecho.

**Rollback**
- No aplica (docs).

---

## CBS-K9  Protección de main / governance
**Prioridad:** P0
**Columna inicial:** READY
**Owner:** unassigned
**Dependencias:** ninguna
**Riesgo:** GREEN

**Problema**
Asegurar que main no recibe merge sin checks verdes.

**Alcance permitido**
- Lectura del estado de protección.

**Fuera de alcance**
- Cambiar reglas de protección/permisos.

**Archivos / subsistemas**
- GitHub branch protection (main)

**Criterios de aceptación**
- Estado de protección documentado (requeridos: CRIBA/BLACKFORGE, SUPRA,
  monorepo-result).

**Verificación requerida**
- Comando real: `gh api repos/Klsx-Moli/Criba-Blackforge-Supra/branches/main/protection`
- Resultado esperado: JSON con required checks (NOT_RUN aquí)
- Evidencia a adjuntar: JSON

**STOP**
- Si la protección está ausente (acción del operador, no del agente).

**Rollback**
- No aplica (lectura).

---

## CBS-K10  Inventario de dependencias y seguridad
**Prioridad:** P1
**Columna inicial:** READY
**Owner:** unassigned
**Dependencias:** ninguna
**Riesgo:** YELLOW

**Problema**
PR10 modifica pyproject.toml y CribaShadow.spec; falta inventario y SBOM.

**Alcance permitido**
- Leer pyproject.toml; generar listado de dependencias (sin cambiar).

**Fuera de alcance**
- Actualizar dependencias.

**Archivos / subsistemas**
- criba-blackforge/pyproject.toml, CribaShadow.spec

**Criterios de aceptación**
- Dependencias y versiones listadas; vulnerabilidades conocidas anotadas.

**Verificación requerida**
- Comando real: `uv pip freeze` o `pip-audit` (NOT_RUN aquí)
- Resultado esperado: lista de paquetes / hallazgos
- Evidencia a adjuntar: salida

**STOP**
- Si hay vulnerabilidad crítica en dependencia de producción.

**Rollback**
- No aplica (lectura).

---

## CBS-K11  Release candidate path
**Prioridad:** P2
**Columna inicial:** BLOCKED
**Owner:** unassigned
**Dependencias:** CBS-K3, CBS-K4, CBS-K9, CBS-K10
**Riesgo:** YELLOW

**Problema**
PR10 añade version.py; PR8/9/11 no versionan. Falta política de versión y RC.

**Alcance permitido**
- Documentar esquema de versión y criterios de RC.

**Fuera de alcance**
- Publicar release; cambiar versión/licencia.

**Archivos / subsistemas**
- criba-blackforge/src/criba/version.py, LICENSE

**Criterios de aceptación**
- Política de versión y criterios de RC documentados.

**Verificación requerida**
- Comando real: `git show 15bc237:criba-blackforge/src/criba/version.py`
- Resultado esperado: versión actual (NOT_RUN aquí)
- Evidencia a adjuntar: contenido

**STOP**
- Si se propone cambio de licencia.

**Rollback**
- No aplica (docs).

---

## CBS-K12  Policy de PR/documentación experimental
**Prioridad:** P2
**Columna inicial:** READY
**Owner:** unassigned
**Dependencias:** CBS-K8
**Riesgo:** GREEN

**Problema**
Evitar que documentación experimental se confunda con main (caso SC-01/PR12).

**Alcance permitido**
- Definir política: etiquetar REPORTED_BY_PR, HISTORICAL_UNVERIFIED,
  MAIN/EXPERIMENTAL/PLANNED/NOT_VALIDATED.

**Fuera de alcance**
- Cambiar configuración de PRs existentes.

**Archivos / subsistemas**
- docs/ (política)

**Criterios de aceptación**
- Política documentada y aplicable a PRs futuros.

**Verificación requerida**
- Comando real: revisión de la política
- Resultado esperado: reglas claras de etiquetado
- Evidencia a adjuntar: doc

**STOP**
- Si exige modificar PRs existentes.

**Rollback**
- No aplica (docs).
