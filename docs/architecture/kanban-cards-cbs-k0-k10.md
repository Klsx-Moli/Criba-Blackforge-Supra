# Tarjetas Kanban — Convergencia PR #8–#12 (reales)

Generadas por Hermes tras auditoría de checkout + GitHub/gh. Basadas en
evidencia real; los resultados de comandos son ESPERADOS, no ejecutados salvo
donde se indique NOT_RUN.

---

## CBS-K0R  Reconstruir mapa real de ramas, PRs y contratos
**Prioridad:** P0
**Columna inicial:** IN PROGRESS
**Owner:** unassigned
**Dependencias:** ninguna
**Riesgo:** ORANGE

**Problema**
El informe externo/Kanban describe PR #8–#11 como consenso/evidencia/reliability/
episodic replay/VOI/shadow pricing. Los diffs reales de GitHub NO contienen esas
capacidades (SC-01). El mapa debe reconstruirse desde checkout, refs remotas, PRs,
diffs y checks actuales.

**Alcance permitido**
- Clasificar PR #8–#12 por ámbito real y SHA base/head.
- Registrar conflictos entre informe y repositorio (SC-01).
- Identificar origin/main y su SHA (15bc237).
- Determinar orden de integración o declararlo indeterminado.
- Solo lectura: sin merge, rebase, push, tests, modificación de código.

**Fuera de alcance**
- Cualquier integración real a main.
- Ejecución de BLACKFORGE (HARD_PAUSE vigente).
- Cambios de permisos/secretos/protección de GitHub.
- Inventar contratos ausentes (episodic/VOI/consensus).

**Archivos / subsistemas**
- docs/architecture/pr-8-11-convergence-matrix.md (creado en esta sesión)
- docs/architecture/episodic-memory-canonical-contract.md (creado)
- docs/roadmap/integration-plan-pr-8-11.md (creado)
- Metadatos GitHub vía `gh pr view`/`gh pr checks`

**Criterios de aceptación**
- PR #8–#12 clasificados por ámbito real y SHA base/head.
- SC-01 registrado con resolución.
- origin/main y SHA 15bc237 identificados.
- Orden de integración determinado o declarado indeterminado con causa.
- Ninguna modificación de código/merge/rebase/push.
- Evidencia vinculada a comandos y SHAs reproducibles.

**Verificación requerida**
- Comando real: `git -C C:/ASTRA_WORK/Criba-Blackforge-Supra rev-parse origin/main`
- Resultado esperado: 15bc237be5555fcc38bc8a25f80724473c13435b
- Evidencia a adjuntar: salida de terminal (verificado en esta sesión: SÍ).
- Comando real: `gh pr view 11 --json baseRefOid,headRefOid`
- Resultado esperado: baseRefOid=15bc237..., headRefOid=3244879...
- Evidencia a adjuntar: salida de gh (verificado en esta sesión: SÍ).

**STOP**
- Si GitHub/checkout difieren y no se puede determinar qué remoto es canónico.
- Si hay cambios locales no atribuibles al agente.
- Si un PR apunta a repositorio/base distinto del esperado (ya ocurrió: PR10 base shadow-supra, no main).

**Rollback**
- No aplica: fase exclusivamente de lectura y documentación en rama aislada.

---

## CBS-K0  Matriz y decisión de convergencia PR #8–#11
**Prioridad:** P0
**Columna inicial:** READY
**Owner:** unassigned
**Dependencias:** CBS-K0R
**Riesgo:** ORANGE

**Problema**
Decidir estrategia de integración entre PR #8–#11 cuando NO son variantes de una
misma capacidad sino líneas distintas (safety, persistence, intérprete, broker).

**Alcance permitido**
- Matriz de deltas reales (hecha en pr-8-11-convergence-matrix.md).
- Decisión de orden seguro; port selectivo en rama de integración aislada.
- Verificar solapamiento authz PR8 vs PR11.

**Fuera de alcance**
- Merge a main.
- Cualquier capacidad no presente (episodic/VOI/consensus).
- Ejecución BLACKFORGE.

**Archivos / subsistemas**
- criba-blackforge/src/criba/blackforge_safety.py (PR8)
- criba-blackforge/src/criba/blackforge_agentic.py, storage.py, pipeline.py (PR9)
- criba-blackforge/src/criba/blackforge_broker.py, blackforge_case.py, blackforge_slice_authz.py (PR11)
- codex/interpreter-hardening (PR10, base no-main)

**Criterios de aceptación**
- Orden de integración propuesto con justificación por base/head refs.
- Solapamiento authz PR8/PR11 resuelto (unificar o frontera documentada).
- Sin cambios a main.

**Verificación requerida**
- Comando real: diff semántico blackforge_safety.py vs blackforge_broker.py authorization
- Resultado esperado: lista de símbolos duplicados o confirmación de dominios distintos
- Evidencia a adjuntar: diff / patch de los dos módulos
- Comando real: `gh pr checks 8` y `gh pr checks 11`
- Resultado esperado: CLEAN/PASS (ya observado PASS en esta sesión)

**STOP**
- Si el solapamiento authz no puede resolverse sin cambiar semántica de PR8 o PR11.

**Rollback**
- Rama de integración por paso; `git revert` o branch por paso.

---

## CBS-K1  Contrato canónico de memoria episódica
**Prioridad:** P1
**Columna inicial:** BLOCKED
**Owner:** unassigned
**Dependencias:** CBS-K0
**Riesgo:** YELLOW

**Problema**
La misión pide un contrato canónico de memoria episódica, pero NO existe en los PR
actuales. Debe definirse como plantilla de aceptación, no como capacidad inventada.

**Alcance permitido**
- Definir invariantes (hecho en episodic-memory-canonical-contract.md).
- Declarar NO_EXISTE_EN_PR.

**Fuera de alcance**
- Implementar memoria episódica.
- Cualquier PR que la proponga sin diff reproducible.

**Archivos / subsistemas**
- docs/architecture/episodic-memory-canonical-contract.md

**Criterios de aceptación**
- Invariantes documentados.
- Estado marcado UNKNOWN/NO_EXISTE, no como si estuviera implementado.

**Verificación requerida**
- Ninguna ejecución; revisión humana del documento.

**STOP**
- Si alguien propone "integrar" memoria episódica sin PR/diff real.

**Rollback**
- No aplica (solo docs).

---

## CBS-K2  Integración mínima sobre una sola rama candidata
**Prioridad:** P1
**Columna inicial:** BLOCKED
**Owner:** unassigned
**Dependencias:** CBS-K0, CBS-K1
**Riesgo:** YELLOW

**Problema**
Portar selectivamente PR8+PR9 (y PR11 tras resolver authz) a una rama de integración
desde main, sin fusionar a main.

**Alcance permitido**
- Rama `hermes/cbs-integration-<fecha>` desde 15bc237.
- Cherry-pick de commits de PR8/PR9 tras rebase.

**Fuera de alcance**
- PR10 hasta rebasear a main.
- BLACKFORGE real.

**Archivos / subsistemas**
- blackforge_safety.py, blackforge_agentic.py, storage.py, pipeline.py

**Criterios de aceptación**
- Suite CRIBA/BLACKFORGE verde en la rama de integración.
- Sin regresión vs main baseline.

**Verificación requerida**
- Comando real: `cd criba-blackforge && pytest` (o el comando canónico del repo)
- Resultado esperado: PASS sin regresión (no ejecutado en esta sesión: NOT_RUN)
- Evidencia a adjuntar: log de pytest

**STOP**
- Si cherry-pick produce conflicto de semántica no trivial.

**Rollback**
- `git checkout 15bc237` o branch por paso.

---

## CBS-K3  Compatibilidad legacy, migración y round-trip
**Prioridad:** P1
**Columna inicial:** BLOCKED
**Owner:** unassigned
**Dependencias:** CBS-K2
**Riesgo:** YELLOW

**Problema**
PR9 introduce persistencia de auditoría; debe probarse carga de datos legacy y
round-trip.

**Alcance permitido**
- Leer formato previo de storage; probar carga o fallo con diagnóstico.
- Round-trip JSON de PR11 (ya reportado idéntico).

**Fuera de alcance**
- Migración destructiva.

**Archivos / subsistemas**
- storage.py, blackforge_agentic.py

**Criterios de aceptación**
- Datos legacy cargan o fallan con diagnóstico explícito (no silencioso).

**Verificación requerida**
- Comando real: test de carga legacy (por definir tras inspección de storage)
- Resultado esperado: load OK o error con causa; no corrupción silenciosa
- Evidencia a adjuntar: salida de test

**STOP**
- Si el formato legacy es desconocido o no hay fixture.

**Rollback**
- Revertir cambios de storage.

---

## CBS-K4  Baseline reproducible CI sobre main y rama integrada
**Prioridad:** P0
**Columna inicial:** READY
**Owner:** unassigned
**Dependencias:** CBS-K0R
**Riesgo:** GREEN

**Problema**
Establecer baseline de CI de main (15bc237) para comparar con rama integrada.

**Alcance permitido**
- Ejecutar suite en main en worktree aislado.
- Guardar conteos como baseline.

**Fuera de alcance**
- Modificar CI.

**Archivos / subsistemas**
- .github/workflows/ci.yml

**Criterios de aceptación**
- Baseline de main documentado (conteos, duración).
- Reproducible en worktree limpio.

**Verificación requerida**
- Comando real: `gh run list --branch main --limit 5` o ejecución local de suite
- Resultado esperado: PASS (ya observado PASS en checks de PR8/9/11)
- Evidencia a adjuntar: run IDs / log local

**STOP**
- Si CI no es reproducible localmente.

**Rollback**
- No aplica (solo lectura/ejecución local).

---

## CBS-K5  Benchmark reservado para episodic replay/reliability/VOI
**Prioridad:** P2
**Columna inicial:** BLOCKED
**Owner:** unassigned
**Dependencias:** CBS-K1
**Riesgo:** YELLOW

**Problema**
No hay capacidades de replay/VOI; el benchmark se reserva como requisito previo
a cualquier afirmación empírica.

**Alcance permitido**
- Definir protocolo de benchmark fuera de muestra.

**Fuera de alcance**
- Ejecutar benchmark (no hay implementación).

**Archivos / subsistemas**
- N/A hasta propuesta real.

**Criterios de aceptación**
- Protocolo documentado; ninguna afirmación de mejora sin él.

**Verificación requerida**
- Revisión del protocolo.

**STOP**
- Si se declara mejora empírica sin benchmark.

**Rollback**
- No aplica.

---

## CBS-K6  Pruebas adversariales de reliability, coste, VOI y feedback loops
**Prioridad:** P2
**Columna inicial:** BLOCKED
**Owner:** unassigned
**Dependencias:** CBS-K1, CBS-K5
**Riesgo:** ORANGE

**Problema**
Las pruebas adversariales exigidas (feedback loops, coste cero/negativo, fuentes
no fiables) no aplican porque esas capacidades no existen. Se reservan como
plantilla.

**Alcance permitido**
- Plantilla de pruebas adversariales por invariante.

**Fuera de alcance**
- Ejecutar pruebas sobre capacidades inexistentes.

**Archivos / subsistemas**
- tests/ (cuando exista propuesta)

**Criterios de aceptación**
- Plantilla lista; marcada UNKNOWN hasta propuesta real.

**Verificación requerida**
- Revisión de plantilla.

**STOP**
- Si se ejecutan pruebas sobre capacidades no presentes.

**Rollback**
- No aplica.

---

## CBS-K7  Cierre documental de PR #12 tras decidir integración
**Prioridad:** P2
**Columna inicial:** BLOCKED
**Owner:** unassigned
**Dependencias:** CBS-K0, CBS-K4
**Riesgo:** GREEN

**Problema**
PR12 es documentation-only sobre PR10 (base no-main). Debe cerrarse solo tras
decidir integración de PR10, y nunca usarse como fuente de verdad de comportamiento.

**Alcance permitido**
- Verificar que PR12 no afirma comportamiento de código.
- Separar MAIN / EXPERIMENTAL / PLANNED / NOT_VALIDATED.

**Fuera de alcance**
- Usar PR12 como evidencia de implementación.

**Archivos / subsistemas**
- docs/continuity/*, .gitattributes

**Criterios de aceptación**
- PR12 explícitamente marcado como docs/handoff, CORPUS_INTEGRITY=INCOMPLETE.

**Verificación requerida**
- Comando real: `gh pr view 12 --json body` (ya ejecutado: confirma docs-only)
- Resultado esperado: sin afirmaciones de comportamiento de código
- Evidencia a adjuntar: descripción de PR12

**STOP**
- Si PR12 se usa para acreditar implementación.

**Rollback**
- No aplica.

---

## CBS-K8  Protección de main y checks requeridos
**Prioridad:** P0
**Columna inicial:** READY
**Owner:** unassigned
**Dependencias:** ninguna
**Riesgo:** GREEN

**Problema**
Asegurar que main no recibe merge sin checks verdes y sin revisión.

**Alcance permitido**
- Verificar estado de protección de rama (lectura).
- No cambiar reglas.

**Fuera de alcance**
- Cambiar reglas de protección, permisos, secretos.

**Archivos / subsistemas**
- branch protection (GitHub)

**Criterios de aceptación**
- main protegido; checks CRIBA/BLACKFORGE/SUPRA/monorepo-result requeridos.

**Verificación requerida**
- Comando real: `gh api repos/Klsx-Moli/Criba-Blackforge-Supra/branches/main/protection`
- Resultado esperado: (lectura; NOT_RUN en esta sesión por no ejecutarlo)
- Evidencia a adjuntar: JSON de protección

**STOP**
- Si la protección está ausente (requiere acción del operador, no del agente).

**Rollback**
- No aplica (solo lectura).

---

## CBS-K9  Inventario de dependencias, SBOM y vulnerabilidades
**Prioridad:** P1
**Columna inicial:** READY
**Owner:** unassigned
**Dependencias:** ninguna
**Riesgo:** YELLOW

**Problema**
PR10 modifica pyproject.toml y CribaShadow.spec; PR11 añade módulos. Requiere
inventario de dependencias.

**Alcance permitido**
- Leer pyproject.toml, generar SBOM (lectura/herramienta, sin push).

**Fuera de alcance**
- Cambiar dependencias.

**Archivos / subsistemas**
- criba-blackforge/pyproject.toml, CribaShadow.spec

**Criterios de aceptación**
- Listado de dependencias y versiones; alertas conocidas documentadas.

**Verificación requerida**
- Comando real: `pip-audit` o `uv pip freeze` (NOT_RUN en esta sesión)
- Resultado esperado: lista de paquetes / vulnerabilidades
- Evidencia a adjuntar: salida de la herramienta

**STOP**
- Si hay vulnerabilidad crítica en dependencia de producción.

**Rollback**
- No aplica (solo lectura).

---

## CBS-K10  Estrategia de releases, versión y licencia/distribución
**Prioridad:** P2
**Columna inicial:** BLOCKED
**Owner:** unassigned
**Dependencias:** CBS-K8, CBS-K9
**Riesgo:** YELLOW

**Problema**
PR10 añade version.py; PR11/PR9 no versionan. Definir política de versión.

**Alcance permitido**
- Documentar esquema de versión y licencia (sin cambiar).

**Fuera de alcance**
- Cambiar licencia, publicar release.

**Archivos / subsistemas**
- criba-blackforge/src/criba/version.py, LICENSE

**Criterios de aceptación**
- Política de versión documentada; licencia intacta.

**Verificación requerida**
- Comando real: `git show 15bc237:criba-blackforge/src/criba/version.py` (NOT_RUN)
- Resultado esperado: versión actual documentada
- Evidencia a adjuntar: contenido del archivo

**STOP**
- Si se propone cambio de licencia.

**Rollback**
- No aplica.
