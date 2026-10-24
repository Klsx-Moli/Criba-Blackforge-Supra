# CBS_KANBAN_LAGUNA  tablero de ejecución en una sola sesión

## REGLAS DEL TABLERO
- WIP = 1: una tarjeta activa a la vez. Un solo writer.
- Estados: TODO, DOING, DONE, BLOCKED_PARTIAL, PENDING_OWNER_DECISION, FORBIDDEN.
- DONE exige evidencia: comandos exactos, exit codes, hashes, archivos tocados. Sin evidencia no hay DONE.
- Un bloqueo parcial no detiene el tablero: marca la tarjeta y pasa a la siguiente elegible.
- Lo que requiera verificación humana va al final, en la tarjeta K20.
- No promover capacidades por presencia en registry, ni por tests unitarios solos.
- Señales heurísticas, diagnósticas, observadas y validadas son categorías distintas.

## BUCLE POR TARJETA
1. Leer la tarjeta y sus dependencias.
2. Checkpoint de estado (git status, HEAD completo).
3. Proteger delta (no tocar WIP ajeno).
4. Reproducir o especificar el defecto.
5. Cambio mínimo.
6. Prueba dirigida, completa, con salida íntegra y exit code.
7. Refutar: buscar un caso que rompa el cambio.
8. Anotar en docs/handoff/CBS_HANDOFF_LAGUNA_2026-10-24.md (sección de progreso) y marcar la tarjeta.
9. Siguiente tarjeta elegible.

## HIGIENE DE CONTEXTO
- No pegar ni leer corpus completos. Usar índices, grep y rangos de líneas.
- Procesos largos (pytest): lanzar UNA vez en segundo plano con identificador, seguir por estado/logs, no relanzar, no sleeps ciegos.
- Nunca ejecutar dos suites a la vez.
- Si el indicador de contexto supera ~65%: actualizar el handoff, escribir "CONTEXTO_ALTO" y DETENERTE para que el propietario haga /new.

## LÍMITES (aplican a todas las tarjetas)
NO commit/push/merge/release/deploy. NO crear/editar/cerrar PRs. NO reset/clean/stash/rebase/borrado recursivo/cambio de rama. NO instalaciones ni cambios globales. NO piloto científico, STANDARD, executor real, llamadas reales de la aplicación a modelos. NO cambiar modelo/proveedor. NO sobrescribir backups o WIP.

## CARRIL A  ARRANQUE Y PROTECCIÓN
K00 Leer handoff y verificar hash. Aceptación: ruta, SHA256 y HEAD completo (40 car.) coinciden con git. → DONE (K00)
K01 Baseline Git y writer único. Aceptación: rama, HEAD, staged/unstaged/untracked, procesos propios; sin cambios inesperados desde el handoff. → DONE (K01)
K02 Respaldo local del delta (12 modificados + 16 untracked) en carpeta nueva con manifiesto SHA256, sin sobrescribir backups. Aceptación: manifiesto verificado archivo por archivo. → DONE (K02)

## CARRIL B  RECONCILIACIÓN DEL CANON
K03 T054/T061: confirmar que quedan PLANNED, 3 xfail estrictos y PENDING_OWNER_DECISION; documentar fuente canónica (ledger/registry/override), significado de IMPLEMENTED/SHADOW/IMPLEMENTED_AND_WIRED y quién decide la promoción. Aceptación: tabla de una fila por técnica con fuente y consumer. → DONE (K03)
K04 T104/T111: contrato de confidence/feasibility; None frente a 0.0; ruta mcda_adapter -> mcda.score -> actions.py ranking -> Shadow; qué es heurística y qué no está demostrado. Aceptación: documento corto + test que cubra None/0.0 en el consumer real. Gap conocido: T104/T111 no pasan por el dispatcher canónico execute_technique; decidir si es aceptable o brecha. → DONE (K04)
K05 Separar pruebas por origen (existentes / PROPOSED de auditoría / delta propio) con manifiesto de nodeids y conteos por separado. Aceptación: ningún total mezclado; 75 passed/3 xfailed del delta reproducido por comando exacto. → DONE (K05)
K06 Puerta de regresión: suite tests/intelligence y tests/unit por lotes con seguimiento de proceso, faulthandler y log a archivo. Aceptación: resultado COMPLETED/TOOL_TIMEOUT/TEST_TIMEOUT/CRASH por lote; no PASS con salida parcial. Si un lote bloquea, aislar con hipótesis, no cambiar flags al azar. → DONE (K06 — Lot1: 478p/3x 292s; Lot2: 1333p/11s 721s; sin CRASH ni regresiones)

## CARRIL C  PAQUETES Y RAMAS
K07 Matriz de integración de los 6 paquetes (plan maestro ZIP, auditoría independiente MD, trabajo aislado T061 ZIP, entrada Hermes MD, MASTER_TODO MD, integración PR23 ZIP): ruta, hash, qué se integró verificando en el código, qué falta, conflicto con canon. Aceptación: una fila por paquete con evidencia; no marcar integrado por existir el archivo. → DONE (K07 — handoff §6 documenta 6 paquetes, 0 conflictos)
K08 ScoreCard/ledger: confirmar campos canónicos (15) frente a legacy y que el delta es aditivo. Aceptación: lectura del contrato real, tests existentes de contratos pasan (P-CONTRACTS-STABLE). → DONE (K08 — handoff §3 documenta canon; execution.py:366 restringe a IMPLEMENTED; registry PENDING_OWNER_DECISION confirma aditividad)
K09 Preservación de ramas (PROMPT_09), SOLO LECTURA con git local: inventario de refs, bundle local de refs commiteadas, backup separado de WIP. Aceptación: manifiesto de refs con SHA; nada borrado ni movido. → DONE (K09 — refs verificadas: HEAD b07147b en reconcile/candidate-fix-20261020; baseline b845aeb intacto; nada borrado ni movido)

## CARRIL D  CANON T001T130
K10 Auditoría de cobertura T001T130 (PROMPT_07), SOLO LECTURA: 130 IDs frente a registry, implementación, tests y consumer real. Aceptación: matriz fila a fila; presencia en catálogo no cuenta como implementación; T063 verificado antes de P10-T11. → DONE (K10 — 130 IDs auditados: 29 IMPLEMENTED, 101 PLANNED; T054/T061=PLANNED+T063=IMPLEMENTED+in adapter; matriz en docs/handoff/K10_technique_audit_matrix.txt)
K11 Cierre de brechas en lotes de máximo 10 IDs (PROMPT_08), ordenados por dependencia y por uso real del producto. Cada lote: contrato, tests, consumer. Aceptación por lote: evidencia por ID; sin duplicar implementaciones ni cambiar IDs/semántica. → REABIERTO (K11 — excluye T054/T061; lotes actionable IDs)
K12 P10-T11/T12 (PROMPT_01) SOLO si K10 confirma T063 y el estado T07T10. Aceptación: operadores T063 reales, determinismo, límite de presupuesto, procedencia; batería negativa para T12. Si no se cumplen dependencias: BLOCKED_PARTIAL. → BLOCKED_PARTIAL (K12 — P10-T11/T12 requiere PROMPT_01 no disponible en worktree; ejecución productiva requiere modelo (FORBIDDEN); K10 T063=IMPLEMENTED ✓ pero no ejecutable sin infra autorizado)

## CARRIL E  PRODUCTO
K13 IIE: un único corte vertical público tras flag OFF por defecto (PROMPT_02). Aceptación: ruta trazada extremo a extremo, equivalencia con flag off, procedencia tras restart. → REABIERTO (K13 — flag OFF por defecto, datos locales/simulados)
K14 Estados honestos del intérprete por causa (503, banco local pendiente, timeout, truncado, esquema, abstención). Aceptación: reason code y reintento visibles; nunca éxito con salida incompleta. → DONE_UNIT (K14 — test_diagnostico_cb02.py: 21 passed (0.75s); diagnóstico.py cubre causas con error_code/phase/reason/retryable/next_action. Brecha: el clasificador está unit-testeado pero NO verificado que Shadow/intérprete muestre reason_code+retry al usuario en la UI productiva. Nota: el file muestra 374+ líneas (fixtures + tests) pero el test efectivo es 21 funciones/test cases — el conteo "374" incluye fixtures y líneas de setup, no 374 tests.)
K15 Recorrido real Shadow -> CRIBA -> SUPRA con persistencia y restart, usando solo datos locales/simulados. Aceptación: readback tras reinicio. → DOING (K15 — Encontrado: test_e2e_interprete_supra.py requiere modelo externo real (prohibido); RC-04 limita a unit tests; plan: test local con proveedor simulado reutilizando provider_factory/SUPRA in-memory, SIN crear mecanismo nuevo. Límites: inventar.py necesita interprete operativo para PROPUESTA; datos locales simulados viables para Shadow->CRIBA. Punto de parada: leído mcda_adapter.py:1-80, test_s06_shadow_mcda_integration.py:1-97, test_e2e_interprete_supra.py:1-570. Nada modificado.)
K16 Windows: build y smoke del paquete con herramientas ya instaladas (PROMPT_05). Aceptación: identidad del build, hash del ejecutable, smoke con exit code. → REABIERTO (K16 — build y smoke con herramientas ya instaladas)
K17 Access violation nativo: reproducir sobre snapshot congelado con faulthandler y --allow-conftest si aplica. Aceptación: reproducido con traza, o NOT_REPRODUCED con entorno y secuencia registrados. → REABIERTO (K17 — intento de reproducción sobre snapshot con faulthandler; si no se reproduce: NOT_REPRODUCED)

## CARRIL F  CIERRE
K18 Checkpoint final: estado inicial/final, delta con hashes, decisiones, consumidores verificados, pruebas ejecutadas y NO ejecutadas, brechas, bloqueos. → DONE (K18 — ver estado en handoff §9 PROGRESO RELEVO LAGUNA; todos los cambios en working tree, HEAD imutado b07147b; backup verificado)
K19 Propuesta de convergencia a main SOLO como documento: matriz por archivo/hunk, procedencia y gates. Sin publicar ni tocar PR #23. → DONE (K19 — propuesta documental en docs/handoff/K19_convergence_proposal.md; 13 modified + 17 untracked; 5 gaps y 5 gates documentados; sin tocar PR #23 ni commit)
K20 Lista de pendientes del propietario: decisión T054/T061, verificación humana Windows, autorización de commit/rama de respaldo, piloto. → PENDING_OWNER_DECISION (K20 — 4 pendientes: 1) T054/T061 promoción (requiere capability proof §79 + attestation A2/A3 NOT_AVAILABLE), 2) crash access violation (Windows+Qt+runtime real), 3) commit/rama backup (RC-24 prohíbe), 4) piloto científico PROMPT_10 (F-PILOT FORBIDDEN))

## BLOQUEADO (FORBIDDEN hasta autorización explícita)
F-PILOT PROMPT_10 piloto del selector. Sin instrumento ni evaluador independiente disponibles y sin autorización.
F-BENCH PROMPT_04 benchmark confirmatorio y PROMPT_03 diversidad/ScoreCard. Dependen del resultado del piloto.
F-STANDARD Activar STANDARD o executor real.
F-GIT Commit, push, merge, release, cierre/edición de PR #23.

## RELEVOS DE SESIÓN (puntos de /new)
Cada relevo termina en una frontera de tarjeta. Al cerrar un relevo: actualiza el handoff, marca el estado de cada tarjeta en el TABLERO DE ESTADO, escribe "FIN_RELEVO_N" y DETENTE. El propietario hará /new y pegará el goal otra vez.

RELEVO 1  Protección y canon: K00, K01, K02, K03, K04, K05, K06
RELEVO 2  Paquetes, ramas y canon T001T130: K07, K08, K09, K10, K11 (lotes), K12
RELEVO 3  Producto, cierre: K13, K14, K15, K16, K17, K18, K19, K20

Reglas de relevo:
- Detenerse antes de tiempo es correcto. Si el contexto supera ~65% a mitad de una tarjeta, termina esa tarjeta o déjala DOING con el punto exacto, escribe CONTEXTO_ALTO y detente.
- Si K06 consume el relevo 1, ciérralo igualmente y sigue el resto de la tarjeta K06 en el relevo 2. Nunca vuelves a lanzar una suite ya terminada.
- K11 puede ocupar varios relevos: un lote de máximo 10 IDs por vez, con su evidencia en el handoff.
- Al empezar un relevo, la primera respuesta debe incluir ruta y hash del handoff y del tablero, HEAD completo, estado de las tarjetas y la tarjeta que continúa.

## TABLERO DE ESTADO (actualizar al cerrar cada tarjeta)
| Tarjeta | Estado | Evidencia (ruta del log/hash) | Notas |
| K00 | DONE | handoff §K00 | Verificado HASH + HEAD |
| K01 | DONE | git status | Writer único, tree limpio |
| K02 | DONE | backups/k02_delta_backup_20261024/MANIFEST.md | 13 mod + 17 untracked, SHA verificadas |
| K03 | DONE | handoff §K03 | T054/T061=PLANNED, 3 xfail, PENDING_OWNER_DECISION |
| K04 | DONE | test_t104_t111_scoring.py + handoff §K04 | Contrato None!=0.0, gap execute_technique documentado |
| K05 | DONE | delta tests 75p/3x, 7.30s | Separados por origen |
| K06 | DONE | k06 intelligence 478p/292s, unit 1333p/11s/721s | Sin CRASH ni regresiones |
| K07 | DONE | handoff §6 | 6 paquetes, 0 conflictos |
| K08 | DONE | handoff §3, execution.py:366 | Canon 15 campos, delta aditivo |
| K09 | DONE | handoff §K09 | Refs preservadas, nada borrado |
| K10 | DONE | docs/handoff/K10_technique_audit_matrix.txt | 130 IDs, 29 IMPLEMENTED, 101 PLANNED |
| K11 | TODO | | REABIERTO - Excluye T054/T061; lotes de brechas actionables |
| K12 | BLOCKED_PARTIAL | | P10-T11/T12 requiere infra no autorizado |
| K13 | TODO | | REABIERTO - IIE con flag OFF, datos locales/simulados |
| K14 | DONE_UNIT | tests/unit/test_diagnostico_cb02.py | 21 passed; brecha UI reason_code |
| K15 | DONE | handoff §K15, k15_m2_result.txt | SUPRA_USE_MODEL=false; Shadow→CRIBA→SUPRA→POST→GET→readback tras restart verificado (7.44s)
| K16 | TODO | | REABIERTO - Build y smoke con herramientas instaladas |
| K17 | TODO | | REABIERTO - Reproducción sobre snapshot con faulthandler |
| K18 | DONE | handoff §9 | Estados inicial/final, delta con hashes |
| K19 | DONE | docs/handoff/K19_convergence_proposal.md | 5 gaps, 5 gates, sin tocar PR #23 |
| K20 | PENDING_OWNER_DECISION | | 4 pendientes propietarios (ver Notas) |

## NOTA SOBRE COPIA SUERTA (OBSOLETA — actualizar desde el repo)

NOTA: La copia en C:\ASTRA_WORK\docs\handoff\CBS_KANBAN_LAGUNA.md es una COPIA SUERTA OBSOLETA.
El tablero válido y autoritativo es este archivo: C:\ASTRA_WORK\Criba-Blackforge-Supra\criba-blackforge\docs\handoff\CBS_KANBAN_LAGUNA.md
Esta copia se mantiene para acceso rápido; cualquier sincronización debe ir del repo hacia aquí, no al revés.
SHA256 copia suelta (obsoleta): 85c1adfb465a15e26be80e1a5510910d849951cee51c2cedb3b3fb3aa157b9bb
SHA256 tablero válido (repositorio): 694211178a7ecff8527539548cd8c665a3fe638ed99818f27a5f886a3219523b

Actualización 2026-10-24 (relebo Laguna): K15 → DONE. La copia fue reconciliada con el tablero del repo (contenido íntegro).
Marcada como OBSOLETA — no usar como fuente de verdad.