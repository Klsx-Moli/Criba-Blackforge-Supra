# CBS-FINAL-32/40 — registro canónico de campaña

Estado inicial: 2026-11-22. Rama de trabajo acumulativa: `campaign/cbs-final-32-40`.
Baseline inmutable de transferencia: `757519c480390167f22df60d7ef2da79215d1a72` (`handoff/cbs-final-20261122`).
Main observado: `1304649b781c335e66016b480ed7d7797fa6f359`.
La referencia de progreso es el HEAD remoto de la rama de campaña, no un SHA autorreferencial escrito antes del commit.
Preservar el handoff, su matriz original, todos los materiales locales, los checkpoints y las 26 tareas anteriores. Esta campaña no renumera ni cancela esas tareas.

## Reglas de ejecución y aceptación

- Usuario autoriza desarrollo incremental en GitHub; no merge a main, despliegue, gasto, borrado, force-push ni modificación de ASTRA. BLACKFORGE diferido para la campaña. No arrancar inferencia sin autorización G0 correspondiente. No publicar secretos, datos personales, DB, modelos o binarios.
- Leer EEIMC-001, AGENTS, PROMPT_ARRANQUE y CONTROL_PREVIO. Sus blobs en la transferencia son idénticos a los previamente leídos en main (e31cd169, 8a753c79, 2f4060da, 4ec8b1f3). No rebajar puertas. Mantener Shadow como interfaz principal y CRIBA como motor de invención, SUPRA como desarrollo y verificación.
- Cada ciclo: comprobar HEAD y trabajo nuevo, delimitar contrato, reproducir, agregar regresión, reparar cuando sea autorizado y viable, ejecutar pruebas, mutar/refutar, revisar diff, registrar evidencia y siguiente punto. No afirmar pruebas no ejecutadas. Ramas auxiliares solo si necesarias; mantener rama de campaña acumulativa.
- Estados: VERIFIED_BY_EXECUTION, STATICALLY_INSPECTED, REPORTED_BY_AGENT, NOT_EXECUTED, NOT_ACCESSIBLE. Diferenciar SOURCE, WIRED, EXECUTED, TESTED, PACKAGED_VERIFIED. Un test sintético no demuestra inferencia, causalidad, novedad ni rendimiento. Los porcentajes de fases no son funcionalidad.
- G0=DRAFT_NOT_APPROVED; P0_SEMANTIC=OPEN; SCIENTIFIC_ADVANTAGE=NOT_ESTABLISHED; DESKTOP_VISUAL_ACCEPTANCE=NOT_VERIFIED. No cambiar esos estados mediante documentación o pruebas estructurales.
- La aceptación final requiere recorrido real en Shadow: problema -> generar/inventar -> interpretar -> evaluar -> desarrollar en SUPRA -> guardar -> cerrar -> reiniciar -> recuperar -> exportar; errores, cancelaciones, modelos y recuperación; compilación y arranque EXE Windows desde entorno aislado, verificación visual, CI y regresión. Sin acceso al PC, separar lo pendiente para ERNIE y no declarar completitud.

## Fase 01 — Consolidación canónica y reproducibilidad del handoff

Resultado dentro del alcance: COMPLETADO para la corrección de portabilidad del gate y establecimiento de baseline; campaña IN_PROGRESS, aceptación productiva pendiente.
Baseline comparado con main: ahead 3, behind 0, 22 archivos. Transferencia sin check runs registrados; main 5/5 informado y verificado previamente, no equivalente a CI de candidata. 156 dirigidos, 1791 unitarios/8 skips, Ruff F/E9 y mypy son REPORTED_BY_AGENT, no pruebas propias de toda la rama. La suite 1791 pertenece al worktree ASTRA, no al SHA de transferencia. No se reclasifica como aceptación de EXE.

### Reparación F01-01 (P1 reproducibilidad)
`criba-blackforge/tests/unit/test_k3_ledger_gate.py` usaba una ruta absoluta de otro worktree Windows. Un test omitido, otro falla por import; los registros del supuesto test de integración se construían manualmente. El gate de referencia no está en el árbol transferido.
Reproducción: archivos exactos del remoto, verificados con git hash-object: normalizador 3dcd28a193d650f7f640e72ebc098949e0393e3f; test original 80e699068efb3a0b3d401b2a458af5ae40cdb3a2; gate 74cac16e6e5458c076afeab22cef643e401fecc9; casos 25a6b77fdf2e99b5b71a97142ee9eb1d5d712d50. Entorno Linux aislado Python/pytest, sin clon completo por DNS inaccesible; reconstrucción byte a byte de esos cuatro archivos.
Antes: 11 passed, 1 failed (ModuleNotFoundError), 1 skipped.
Cambio: incorporar los cinco blobs exactos de `28727ba494640ef32e04ada576eb26e14cca65be` en `docs/research/semantic-correspondence/g0-draft/`; no editar sus reglas; importar gate desde ruta de checkout con runpy (sin contaminación sys.path/sys.modules), usar normalizar_lote real, sin skip, probar A/B/C (16/36/108), slot inesperado y recibo sintético sin promoción.
Después: 16 passed, 0 failed, 0 skipped desde raíz de Criba y desde /tmp con PYTHONPATH. Dos mutaciones detectadas (manifiesto alterado y normalizador que retorna lista vacía: 5 fallos cada una), módulo ambiente impostor no cargado (5 passed). Restaurado 16 passed. compileall dirigido PASS. Test modificado blob 1296fc9f606b54be6ea5d083f36b1954d3d2580a. Sin llamadas LLM ni datos reales. No suite completa, Ruff/mypy o CI de esta fase ejecutados. Esta es una reparación de laboratorio y tests habilitante G3, no de semántica productiva.

Comandos desde `criba-blackforge`:
```sh
python -m pytest -q tests/unit/test_k3_ledger_gate.py
python -m compileall -q tests/unit/test_k3_ledger_gate.py ../docs/research/semantic-correspondence/g0-draft/pilot_gate.py
```

### Conciliación del handoff (sin sobrescribir su documento histórico)

| ID | Hallazgo | Estado |
|---|---|---|
| F01-02 P1 | El handoff §6.3 atribuye BEGIN IMMEDIATE de record_event a ERNIE como novedad respecto de main. Main exacto ya lo tiene (storage.py blob a624a0e9..., línea 250); transferencia añade comentarios, busy timeout y otras rutas. | STATICALLY_INSPECTED; corrección de atribución, no volver a reparar por esa afirmación. |
| F01-03 P0 candidato | El handoff §5 y matriz dicen que _assert_requested_model contrasta /props.model_path y que test_model_runtime_identity.py existe. En transferencia, model_runtime.py blob b547a9aa0b2d2ba97731d5b2ed70b34461c5dec4, líneas 189–195, 312–338, solo verifica /v1/models (o /api/tags) y alias. El árbol completo no contiene ese test. | STATICALLY_INSPECTED, no reproduccion dinámica aún. Identidad real de GGUF NOT_VERIFIED. Solicitar recuperación de reparación local o reconstruir con pruebas dirigidas. |
| F01-04 P0 candidato | normalizar_slot toma el primer recibo con request_sha coincidente; no comprueba body_sha256 == receipt_sha256, ni intento, ni STATUS del recibo. El if final y su retorno alternativo son equivalentes. Extrae labels autorreportadas desde múltiples campos. | STATICALLY_INSPECTED. Fase 02: reproducir con almacenamiento, puentes y hashes reales antes de corregir. |
| F01-05 P1 | El banco de 500 y cbs_corpus.py/test_cbs_corpus_adapter.py no están en árbol transferido; el laboratorio de 58 variantes sí. El gate 18 casos es público, desarrollo, no holdout independiente. | NOT_ACCESSIBLE para el adaptador local. Recuperar código exacto y decidir preservación de reserved; no fingir integración. |
| F01-06 P1 | Matriz marca PACKAGED_VERIFIED en varias capacidades sin build del SHA transferido, EXE con hash reportado y smoke offscreen únicamente; no hay acreditación visual o artefacto de ese SHA. | REPORTED_BY_AGENT; verificar después localmente y separar build/source. |
| F01-07 P1 | Contabilidad física inferida de recibos cerrados, llamadas perdidas/duplicadas no demostrables; límite documentado por ERNIE, no resuelto. | Fase 02/03: distinguir intentos de envío observados, incertidumbre y consumo proveedor. No prometer prueba por recibos únicamente. |
| F01-08 P1 | Contrato de targets de Shadow con constante literal declarada en handoff. | REPORTED_BY_AGENT; inspeccionar en fase UI. |

## Plan de fases (orientativo, no presupuesto de calidad)

01 baseline, reproducibilidad y campaña (esta fase). 02 integridad del recibo y lector del ledger; 03 contabilidad de transporte y presupuesto; 04 recuperar/certificar identidad modelo y completar alcance local transferido; 05 contrato semántico experimental y adjudicación; 06 comparabilidad S0/S1 y preflight; 07 criterios G0/autorizaciones y pruebas físicas cuando proceda; 08 interpretación de fallos y estados; 09 integración controlada en productor-consumidor tras autorización; 10 validación del contrato semántico y rutas alternativas.
11 persistencia de sesión y evidencia; 12 deduplicación/replay; 13 cache, migraciones y versiones; 14 recuperación y exportación.
15 inventario del motor y cruces operativos; 16 generación y diversidad sin proxies inválidos; 17 interpretación del cruce y propuesta; 18 evaluación y comparación con baseline sin claims no demostrados.
19 Shadow targets reales; 20 flujo generar/inventar; 21 acciones, cancelación, retry y errores; 22 selección/modelos/estado; 23 historial, recuperación y UX.
24 puente SUPRA; 25 dossieres y contratos; 26 runner, errores, recuperación; 27 journey integrado.
28 runtime local/cloud autorizado; 29 rendimiento y recursos; 30 seguridad y robustez; 31 regresión/CI y empaquetado; 32 aceptación final real y handoff.
33–40 reserva de ciclos adicionales por hallazgos o puertas pendientes. Si una fase revela P0/P1 se puede reordenar con justificación. Las fases que requieren autorizaciones/inferencia/local se conservan bloqueadas mientras se sigue con trabajo independiente.

## Siguiente acción exacta (histórica, al cierre de fase 01)

Fase 02: comprobar el contrato persistido de semantic_reservations/semantic_receipts y su unión con semantic_critic_bridge, semantic_lab y semantic_ledger_gate. Reproducir recibo de mismo request pero distinto body_sha, STALE con mismo request, mismo request en scopes/attempts distintos, cuerpo alterado, recibo ausente, campos contradictorios y filtro corrupto parseable. No tratar un hash de request como hash de respuesta ni etiqueta declarada como veredicto acreditado. Crear sentinelas que fallen sobre el código actual; reparar experimentalmente y verificar almacenamiento -> lector -> gate, sin activar productor productivo ni hacer inferencias. Mantener el gate reproducible. Si falta evidencia local, registrar exactamente y continuar con lo accesible.

Local pendiente: conservar los 33 worktrees y WIP. No cambiar de rama con árbol sucio. Git fetch de la rama de campaña y worktree aislado para inspección; aún no cherry-pick sobre árbol de ERNIE. Solicitar más adelante el diff exacto de model_runtime.py/test_model_runtime_identity.py y cbs_corpus.py/tests, sin subir datos sensibles ni reserved. No exigir otra ejecución local durante las primeras fases remotas.

## Fase 02 — Integridad de reservas, recibos y lectura semántica

Baseline: `6d9a448f2d6c2d81c2c27a6fcfcdea6ae05da774`. Alcance: reparación experimental de identidad y persistencia, no activación productiva. Estado: candidato reparado y verificado de forma dirigida; regresión completa pendiente.

### Reproducción y reparación F01-04 (VERIFIED_BY_EXECUTION)

- Normalizador previo: aceptaba etiquetas planas inventadas, hashes de recibo incorrectos, STALE, primer recibo equivocado, identidad ajena y etiquetas contradictorias; no sabía traducir el envelope auténtico del laboratorio. También podía lanzar TypeError ante estados corruptos parseables.
- Storage previo: secuencia A -> B -> A reactivaba una identidad superada; una respuesta antigua de A cerraba esa reserva. INSERT OR IGNORE podía confundir dos peticiones con un mismo hash de recibo.
- Reparación: tabla aditiva semantic_superseded_requests, bloqueo de reactivación y conflicto de reviewer, comprobación de colisiones y cierres idempotentes coherentes. Sin borrar datos históricos ni reescribir el esquema existente. La historia ya perdida antes de esta versión no es reconstruible: iniciar campañas nuevas con namespace nuevo.
- load_semantic_snapshot lee reserva y recibos con scope/attempt en una sola transacción SQLite de lectura. Los lectores antiguos conservan sus formas de retorno. Un snapshot es una lectura histórica; no autoriza un cierre sin compare-and-set.
- SlotContext liga posición S1/repetición/nonce al Trial y Request de ASTRA, usando su algoritmo canónico, sin cambiar semantic_lab.py. Exige contexto del host, envelope original, scope, attempt, reviewer, request_sha256, cierre, exactamente un recibo que coincide con receipt_sha256 y estado de inserción ACTIVE. read_current verifica cuerpo estructurado, modelo declarado, finish_reason, citas y digest del envelope; solo sus outcomes se traducen a etiquetas diagnósticas. No se aceptan etiquetas planas. S0 sin implementación de adjudicación, fail closed hasta fase 05/06.
- El campo legado physical_calls ahora es un proxy 0/1 de recibos aceptados, no un contador de transporte. ERROR/NOT_RUN con 0 no acredita ausencia de consumo. Prohibido autorizar presupuesto o ejecución a partir del proxy. Hashes coherentes no acreditan un proveedor honesto ni una llamada real. No persiste el envelope original en SQLite todavía.

### Evidencia ejecutada

Sandbox Linux aislado, sin clon íntegro (limitación de acceso DNS previamente constatada). Archivos exactos reconstruidos: normalizador original 3dcd28a193d650f7f640e72ebc098949e0393e3f, candidato 1a0393cd11b73049e126f1a8804a1c64423805e9; laboratorio 5f9b9c8121b7d4499bc50c713b986b68e785ae12; test fase 01 previo 1296fc9f606b54be6ea5d083f36b1954d3d2580a y candidato 4a42faf5c188e07d259892c621c2dfc3a8354a5d; test nuevo c86139996230ff1db9d3d513f1f291bcc49dd848. Gate y manifiesto exactos de fase 01. Storage probado con configuración mínima y fragmentos exactos de inicialización/conexión y métodos de reservas/recibos; resto del módulo no ejecutado. SHA1 de fragmentos candidatos 759251617a7979e7822eeaae1608cf163f077434 y 31b03b240d77394f3ffd219a7acf04cecdaf2b7e; blob completo candidato badd3bc981de139d3efaba7a32eeddd3f09ae7bc preparado preservando el resto.

- 55 passed (39 integridad nueva + 16 normalizador/gate), última restauración 0.68 s. SQLite real en bases temporales: aceptación de tres lecturas estructurales sintéticas, hashes/citas/cuerpos alterados, conflictos de identidad y repetición, reordenamiento, replay, colisiones, migración aditiva y reapertura, cierre previo inconsistente, lectura concurrente de snapshot, y normalización hasta el gate real.
- 9/9 mutantes detectados: receipt_digest, stale_status, scope_attempt, repetition_binding, pointer, aba, collision, snapshot, duplicate_request. Restauración posterior verde.
- compileall dirigido PASS. diff --no-index --check sin diagnósticos sobre normalizador y test previo vs reparados.
- Ajustados test_k3_contabilidad_fisica.py y test_k3_sqlite_race.py a nuevo contrato: etiquetas sin envelope ahora ERROR, proxy no prueba llamada; carrera usa hashes de envelopes diferentes (colisión tiene regresiones propias). Estos dos archivos históricos modificados NO EJECUTADOS en esta sesión; suite completa, Ruff, mypy, CI y Windows pendientes. No declarar todos los tests del repo verdes. Cero inferencias reales.

Reproducción desde criba-blackforge en checkout completo:
```sh
python -m pytest -q tests/unit/test_k3_receipt_integrity.py tests/unit/test_k3_ledger_gate.py tests/unit/test_k3_contabilidad_fisica.py tests/unit/test_k3_sqlite_race.py tests/unit/test_k3_semantic_reservation.py
```

### Pendientes y continuidad

- F01-04: reparación del lector de recibos y replay verificada en alcance experimental; identidad de transporte y verdad semántica siguen sin acreditar. F02-01: S0 bloqueado; el bridge anterior calcula digest de petición del lab mientras prepara prompt de crítica de producción, incluso para etapas distintas. Debe reconciliarse antes de un piloto comparable, sin inventar equivalencia.
- G0=DRAFT_NOT_APPROVED, P0_SEMANTIC=OPEN, SCIENTIFIC_ADVANTAGE=NOT_ESTABLISHED, DESKTOP_VISUAL_ACCEPTANCE=NOT_VERIFIED. F01-03 (identidad GGUF) continúa pendiente. No activar producción.

## Siguiente acción exacta (histórica, al cierre de fase 02)

Fase 03: contabilidad de transporte y presupuesto. Primero ejecutar las regresiones históricas de fase 02 que queden accesibles. Inspeccionar rutas reales de _pedir/cliente HTTP, retries, fallback, timeout, envío y respuesta. Diseñar registro durable de intento antes de enviar, identificación de tentativa física, resultado/ausencia de respuesta, recuperación tras crash, UNKNOWN cuando el envío es incierto; vincular recibo original a contexto y journal sin aceptar metadatos fabricados como prueba de llamadas. Distinguir slot lógico, intentos reservados, envío observado, respuesta y consumo acreditado por proveedor. No usar physical_calls del normalizador como presupuesto; no autorizar nuevos intentos si el estado de presupuesto es incierto. Probar replay, concurrencia, timeout, escritura parcial, reinicio y límites explícitos 16/36/108 offline, sin activar inferencia, sin cambiar ASTRA ni BLACKFORGE. Conservar G0 y P0. Si una decisión científica o cambio de contrato requiere aprobación, dejar puerta explícita y seguir trabajo independiente.

## Fase 03 — Transporte y presupuesto experimental

Baseline: `45936b9e2a63797ddf52e10a0c100e89244e368e`. Resultado: simulador de contabilidad persistente implementado y verificado de forma dirigida. Transporte productivo y autorización de inferencias NO activados.

### F03-01 — STATICALLY_INSPECTED

`criba-blackforge/src/criba/interprete/openai_compatible.py`: `_post_chat_completion` puede reintentar errores transitorios hasta cuatro intentos; `_request_structured_json` tiene reintento de truncamiento; `proponer` puede ejecutar otra llamada con presupuesto de tokens aumentado. El interruptor CRIBA_ACCEPTANCE_NO_RETRIES no prueba por sí solo ausencia de todas estas vías. El resultado model_requests=1 de _pedir no enumera necesariamente los POST físicos. Inspección estática; no se ha reproducido consumo real ni modificado esa ruta. No emplear model_requests ni physical_calls del gate como autoridad presupuestaria.

### F03-02 — VERIFIED_BY_EXECUTION (rehearsal aislado)

Nuevo `benchmarks/innovation/semantic_transport_journal.py`. Usa Storage.connect y dos tablas aditivas, creadas únicamente al instanciar explícitamente SimulationJournal: semantic_mock_campaigns y semantic_mock_dispatches. No modifica el esquema productivo por defecto ni conecta _pedir. Lee el schedule congelado del prerregistro, valida orden/identidad/hash del plan, tamaños A=16 B=36 C=108, hash de bytes canónicos del payload y modelo solicitado. Rechaza request_sha256 reutilizado dentro del plan. Un BEGIN IMMEDIATE reserva de forma durable el siguiente slot, incrementa contador y crea dispatch_id antes de enviar. Un fallo transaccional impide enviar. Solo acepta MockTransport exacto, URL .invalid, sin redirects ni trust_env. Una sola llamada al cliente por slot. ERROR o incertidumbre bloquea el resto del plan; no reembolsa un slot ni permite replay. Si cae el proceso o falla la escritura de cierre, IN_FLIGHT queda conservado, sin afirmar que el envío llegó al proveedor. Cierra por identidad y compare-and-set; valida hashes del plan y respuestas, conserva bytes de respuesta, y reconstruye envelope estricto desde respuesta persistida. UNKNOWN y RESPONSE_ERROR no se presentan como verdicts. Prueba integrada de respuesta simulada -> receipt -> reserva K3 -> lector S1: incertidumbre conserva UNRESOLVED; alteración de transport_id produce ERROR.

### Evidencia ejecutada

- Sandbox Linux aislado, mismas reconstrucciones y fragmentos exactos de fase 02. No se dispone de clon ejecutable íntegro (acceso de red Git/DNS no disponible). Reejecutadas 55 pruebas de fase 02, añadidas 33 del journal: 88 passed; última ejecución tras formateo, 4.48 s. Compileall dirigido PASS. Archivos históricos test_k3_contabilidad_fisica.py, test_k3_sqlite_race.py, test_k3_semantic_reservation.py y suite íntegra siguen sin ejecutar; intento de recuperar por copia exacta rechazado al no coincidir el blob, no se contabiliza.
- Campañas simuladas independientes completas A/B/C con 16/36/108 envíos MockTransport respectivamente: 160 envíos en total entre esas tres simulaciones; 0 adicionales sobre esos límites. No son tres fases consecutivas de un piloto real. Sin inferencias externas.
- Concurrencia de dos workers contra SQLite, commit anterior al envío, rollback de reserva, fallo de cierre, reapertura, timeout/conexión/crash simulado, error de proveedor simulado, redirect, rechazo de truncamiento y modelo declarado distinto, JSON corrupto/duplicado/NaN, replay y respuesta tardía, bytes válidos alterados y plan válido alterado. Las pruebas inspeccionan estado y envío observado, no solo mocks de SQL.
- 10/10 mutaciones dirigidas detectadas después de fortalecer dos sentinels: presupuesto/orden, hash payload, claim previo, respuesta, plan, status, modelo, límite de transporte/redirect, reserva incierta y replay. Restaurado el código; suite dirigida verde. No extrapolar a cobertura total, ni a proveedor real.
- Blobs exactos locales y remotos: journal 9439d79caf765e5386e1e01fdf4e1f86bd5fffed; tests 7e7f02d0999a8556247b017c8cdf343d12877496. Cambios experimentales, no nueva dependencia (httpx ya declarado). Ruff/mypy/CI completo pendientes; compileall no sustituye esos controles.

Comando en checkout completo desde criba-blackforge:
```sh
python -m pytest -q tests/unit/test_k3_receipt_integrity.py tests/unit/test_k3_ledger_gate.py tests/unit/test_k3_transport_journal.py tests/unit/test_k3_contabilidad_fisica.py tests/unit/test_k3_sqlite_race.py
```

### Límites y puertas

SimulationJournal cuenta slots reclamados por el host en una campaña simulada, no consumo físico de un proveedor. provider_consumption=None y authorization=NOT_GRANTED son invariantes. IN_FLIGHT/UNKNOWN representan incertidumbre; la existencia del hash de un plan, cuerpo o receipt no prueba autenticidad o verdad causal. El MockTransport de pruebas no acredita que exista defensa frente a reintentos de un proveedor real. Las identidades request_sha256 que recibe bind_slot son suministradas por el host y aún requieren reconstrucción desde el Trial y comparación con el payload realmente construido; no usar datos fabricados como certificación. El límite de presupuesto es por campaña simulada, no global entre campañas ni a través de procesos externos. No se concede autorización por registrar otra campaña. No existe aún control de wall time/coste/tokens de un piloto real, ni integración de ese control con transporte productivo. No convertir los envelopes sintéticos en evidencia real. No usar el proxy physical_calls del normalizador para decidir si una llamada puede realizarse. Mantener F03-01 abierto hasta solución y prueba de la ruta real. F02-01 (S0/comparabilidad) pendiente. G0=DRAFT_NOT_APPROVED, P0_SEMANTIC=OPEN, SCIENTIFIC_ADVANTAGE=NOT_ESTABLISHED, DESKTOP_VISUAL_ACCEPTANCE=NOT_VERIFIED. ASTRA y BLACKFORGE intactos.

## Siguiente acción exacta (histórica, al cierre de fase 03)

Fase 04: reconciliar alcance local e identidad real de modelos. Inspeccionar model_runtime.py y su superficie /v1/models, /props, GGUF, alias, caches, selección y las rutas alternativas. Recuperar o reconstruir con evidencias la reparación de ERNIE test_model_runtime_identity.py ausente de la transferencia; no promover alias a identidad del fichero/modelo. Distinguir modelo solicitado, declarado, observado por endpoint y acreditado por identidad física. Reproducir alias correcto/modelo equivocado, /props ausente o corrupto, cambios de runtime, id ambiguo, múltiples rutas y reinicio. Probar offline sin iniciar procesos ni realizar inferencias, conservar incertidumbre. Revisar cbs_corpus.py y tests no transferidos; no fingir su integración ni publicar reserved o datos privados. Recuperar únicamente código autorizado y verificado, sin interferir con el WIP local. Ejecutar las regresiones históricas pendientes si es posible; mantener las no ejecutadas explícitas. No tocar ASTRA ni activar BLACKFORGE. Continuar fases 05/06 con el contrato comparativo S0/S1 y los límites F02-01/F03-01; no autorizar G0 automáticamente.

## Fase 04 — Identidad de modelos y alcance de transferencia

Baseline: `0dbb06c4c588aa8c8c298ca97b216f2616d4381a`. Resultado: preflight offline de identidad implementado y verificado de forma dirigida. No cambia model_runtime.py ni la admisión productiva. F01-03 sigue abierto para la ruta real.

### Hallazgos y evidencia

- F01-03 / VERIFIED_BY_EXECUTION (fragmento): `criba-blackforge/src/criba/model_runtime.py` blob b547a9aa0b2d2ba97731d5b2ed70b34461c5dec4, _served_model_ids, _model_is_served, _assert_requested_model. Extracto verificado FNV1a32 3395aad9, dependencia ModelProfile sustituida por instancia mínima. La comprobación original devuelve éxito para alias correcto incluso con ruta GGUF distinta, /props ausente, alias duplicado, catálogo de varios modelos y espacios añadidos. Las últimas condiciones incluyen política conservadora de preflight, no prueba de fraude del servidor. No se ejecutó servidor real.
- F04-01 / STATICALLY_INSPECTED: el perfil seleccionado puede quedar obsoleto o ambiguo. ModelSettings.active_profile recurre al primer perfil; LocalLlamaInterpreter admite overrides de endpoint/modelo; distinguir perfil de selección efectiva. No introducir cambio incompatible de configuración sin autorización.
- F04-02 / VERIFIED_BY_EXECUTION (fragmento): LocalLlamaInterpreter.operativo, extracto FNV1a32 5ce87fc4. Con seam mínimo para _local y _modo_actual y gate_report passed, cambiar model y base conserva admisión positiva sin reevaluar super().operativo. No es una prueba de reinicio del proceso físico; caché de admisión sin identidad fresca sigue pendiente. No reutilizar esta admisión para una campaña científica.
- F01-05 / NOT_ACCESSIBLE: árboles completos del handoff, campaña anterior y referencias recientes inspeccionadas no incluyen cbs_corpus.py, test_cbs_corpus_adapter.py ni test_model_runtime_identity.py. El adaptador local exacto no se ha recuperado; no afirmar que se transfirió. Se conservan los bancos originales fuera del repositorio, sin publicar reserved, capturas, configuraciones ni datos de usuario.

### Implementación experimental

`benchmarks/innovation/model_identity_preflight.py`: función assess de comparación offline de models.json bruto y captura del host; no consulta endpoints, no arranca servidores, no importa runtime de producción ni realiza inferencias. Valida schema, habilitación, unicidad y selección explícita, backend/ruta, endpoint efectivo y modelo efectivo; exige catálogo coherente y no confunde Ollama tags con modelo cargado. Para llama.cpp de un solo alias compara rutas absolutas GGUF en el sistema anfitrión de modo conservador. Nunca abre una ruta distinta suministrada por el servidor; comprueba fichero seleccionado regular, cabecera GGUF, stat/fstat antes/después y SHA256 opcional por streaming. Rechaza rutas relativas, UNC y discrepancias lexicales; no afirma que rutas distintas impliquen bytes distintos. Una cabecera GGUF no valida un modelo completo. No considera reportes HTTP como autenticación; REPORTED_PATH_MATCH sigue teniendo loaded_file_identity=NOT_VERIFIED y authorization=NOT_GRANTED. compare detecta cambios de la proyección de captura (ruta, configuración efectiva, build y metadatos/hash locales); NO_CHANGE_OBSERVED no prueba continuidad entre observaciones ni ausencia de un reinicio. Sin carga real ni gestión de procesos. La documentación de llama.cpp distingue model_path de pesos en memoria y el modo router puede tener autoload: no consultar /props sin comprobar la modalidad y autorización.

### Evidencia dirigida

- 55 casos nuevos de identidad, 88 regresiones anteriores de sandbox, 143 passed (4.48 s última ejecución). No es la suite completa. Archivos fuente/test exactos f103944a6b9f56f41e808cfab8aef6488150d990 y 473a22d7234b67df78ee178182e2afd4cf18580c. Los fixtures GGUF son diminutos y sintéticos; validan IO y controles, no inferencia.
- 12/12 mutantes dirigidos detectados (ruta, modelo/endpoint efectivo, catálogo múltiple, alias duplicado, cabecera, cambio concurrente, promoción de identidad, modelo reportado, JSON duplicado, comparación, schema). Restaurado el código y rerun verde tras formato. Compileall dirigido PASS. Ruff y mypy no instalados en sandbox; suite/CI/Windows no ejecutados. Conservan pendiente test_k3_contabilidad_fisica.py, test_k3_sqlite_race.py y test_k3_semantic_reservation.py históricos. No efectuar conclusiones sobre hardware, PID real, modelo en memoria, calidad ni consumo real.
- Evidencia reproducible desde criba-blackforge en checkout completo:
```sh
python -m pytest -q tests/unit/test_model_identity_preflight.py tests/unit/test_k3_receipt_integrity.py tests/unit/test_k3_ledger_gate.py tests/unit/test_k3_transport_journal.py
python -m benchmarks.innovation.model_identity_preflight --config models.json --capture local-capture.json
```
El último comando necesita archivos privados obtenidos localmente; no exponerlos al remoto. --hash-gguf lee todo el GGUF elegido y puede consumir IO/tiempo; es optativo y no autentica el servidor. Una captura contiene route (local_llama o synthesis), effective_endpoint (base /v1 para local_llama), effective_model, models y props para llama.cpp, opcional response_model. No rellenar estos campos a partir de la etiqueta UI; deben provenir de observaciones efectivas. En un futuro comprobar inicio/proceso, modo router, modelo/endpoint, identidad del fichero, contexto y versión antes y después, con fuente acreditada; si no es demostrable, conservar UNKNOWN.

G0=DRAFT_NOT_APPROVED, P0_SEMANTIC=OPEN, SCIENTIFIC_ADVANTAGE=NOT_ESTABLISHED, DESKTOP_VISUAL_ACCEPTANCE=NOT_VERIFIED. ASTRA y BLACKFORGE intactos.

## Siguiente acción exacta (histórica, al cierre de fase 04)

Fase 05: contrato semántico experimental y adjudicación, desde semantic_lab.py, semantic_critic_bridge.py, semantic_ledger_gate.py y los preregistros existentes. Resolver F02-01: contrastar digest de Trial/Request canónico con prompt realmente preparado en producción; construir o exponer contrato explícito de brazo S0 (LLM directo) y S1 (CRIBA), sin inventar equivalencia, sin etiqueta de éxito por texto autorreportado. Adjudicación determinista de integridad no debe confundirse con juicio científico: separar lectura evaluable, insuficiencia, UNRESOLVED, rechazo de evidencia y ERROR/NOT_RUN; no usar proxy de recibos como verdad ni consumo. Verificar qué datos recibe cada judge, presupuesto, rúbrica, información simétrica, cegamiento a brazo y prevención de leakage; no usar reserved ni realizar llamadas reales. Probar mutaciones semánticas de consultas, respuestas, citas, identidad, redundancia, negatividad y corrupción; conservar originales y mostrar si control detecta falso coverage. Dejar decisiones científicas por aprobar y los límites epistemológicos; no convertir un criterio provisional en contrato productivo. Reejecutar regresiones dirigidas acumuladas accesibles, sin tocar ASTRA ni activar BLACKFORGE. Identidad de modelo físico y conexión real del journal continúan como puertas para G0; adaptador local faltante no se da por integrado.

## Fase 05 — Contrato semántico, prompt realmente enviado y evidencia del evaluador

Base: `448123cdf7a8913df7cf22e06499dee3467c5dd6`. Estado: CORRECCIÓN DE INTEGRIDAD EXPERIMENTAL VERIFICADA EN AISLAMIENTO; VALIDACIÓN CIENTÍFICA PENDIENTE.

### Hallazgos

- **F05-01 P1 / STATICALLY_INSPECTED + REPRODUCED_IN_ISOLATED_SEAM:** `semantic_critic_bridge.preparar_critica` obtenía `request_sha256` de `semantic_lab.direct_request` o `blind_request` pero construía el mensaje real con `contrato.prompt_critica`. Los prompts tienen instrucciones, datos y esquemas distintos. Dos hashes correctos por separado NO vinculan un mismo mensaje: el recibo podía aparentar el request del laboratorio sin que ese prompt se hubiera enviado. Para BLIND el mensaje preparado incluía el problema original; por tanto no era ciego. No se verificó una llamada productiva ni se modificó el transporte.
- **F05-02 P1 / VERIFIED_BY_EXECUTION:** `CritiqueCall` era `frozen=True` pero contenía `mensajes: list[dict]` mutable. Se podía alterar el texto tras calcular `message_sha256`. La nueva estructura almacena JSON canónico como string privado y expone una copia nueva; **esto no autentica los bytes que efectivamente despache un futuro cliente HTTP**. El payload final deberá ligarse en la frontera real del envío.
- **F05-03 P0 SEMÁNTICO / VERIFIED_BY_EXECUTION, NO FIX CIENTÍFICO:** se construyó un recibo sintético conforme a `semantic_lab.evaluate` que marca SUPPORTS en todos los ejes con citas literales auténticas, pero para `CBS500-01-01:incident` (mecanismo de registros administrativos aplicado a desperdicio de agua). El laboratorio devolvió `REVIEW_SUPPORTED`; la referencia de desarrollo es `REJECT`. Esto demuestra que citas/estructura/etiquetas no acreditan pertinencia, no que el modelo real haya juzgado así. La función declara `evaluator assertion only` y `ResearchReading.__bool__` rechaza el uso como PASS. No cambiar el scoring ni promover una supuesta solución. La referencia es provisional, no gold.

### Reparación aplicada

En `criba-blackforge/benchmarks/innovation/semantic_critic_bridge.py`:
1. Centralizar la construcción de Request canónico para SHA y etapa.
2. `preparar_critica` comprueba igualdad exacta de `[system,user]` que se pretende enviar frente al prompt solicitado al laboratorio, antes de crear CritiqueCall. Si difieren, `ValueError("critica_no_vinculada...")`; **la llamada productiva actual no puede legitimarse como equivalente a S1**. No hay fallback ni conversión silenciosa. El comportamiento de fallo cerrado es intencional.
3. `CritiqueCall` guarda instantánea textual canónica y entrega copias de mensajes, preservando hash contra mutaciones de referencias.
4. Actualizar la prueba de K3 que antes afirmaba que los dos hashes demostraban mismo mensaje; ahora exige el bloqueo. Añadir sentinelas positivos de construcción alineada **simulada**, rechazo BLIND, episodio distinto, stage inválido, cita falso positivo, protección de copia.

### Evidencia y límites exactos

- Sandbox Linux Python 3.13.5 con `semantic_lab.py` (blob 5f9b9c8121b7d4499bc50c713b986b68e785ae12), `semantic_cases.py` (cc713aee9d7198fdef38e4d9bbf5e351ff6eee95) y puente original (7b69c3eaff799b8c6c2b79fdfa909b83c8a9ec4a) reconstruidos y verificados por identidad Git. En sandbox, `contrato.py` y `_SYSTEM` fueron **seams mínimos** porque no hay clon íntegro accesible; el hecho de que los prompts de laboratorio y producción difieren se contrastó también contra el código productivo exacto mediante inspección estática. No afirmar ejecución real de todo `contrato.py` ni del transporte. El puente modificado tiene blob b665af294d1741ebcb093ec6549f83f42fd0426d.
- Suite dirigida: 143 regresiones previas + 15 sentinelas nuevos = **158 PASS** en sandbox. Ocho mutantes iniciales más uno de instantánea mutable: **9/9 detectados**, restaurados y nueva pasada verde. `compileall` dirigido PASS, líneas de los dos archivos nuevos/modificados <=100. Ruff completo, mypy, CI y suite del repo **NOT_EXECUTED**.
- `test_k3_semantic_bridge.py` modificado en remoto para reflejar contrato fail-closed; **NO EJECUTADO** completo en el sandbox, que emplea un seam de contrato. Ejecutar en checkout íntegro y corregir cualquier otra expectativa obsoleta antes de considerar CI verde.
- Ningún cambio bajo `src/` o `shadow_ui/`, sin inference real, sin gasto, sin push a main, sin G0. No atribuir este cambio a reparación científica del P0.
- Comando para checkout completo, desde `criba-blackforge`:
```sh
python -m pytest -q tests/unit/test_k3_semantic_binding_phase05.py tests/unit/test_k3_semantic_bridge.py tests/unit/test_semantic_lab.py tests/unit/test_k3_semantic_no_evidence.py tests/unit/test_k3_receipt_integrity.py tests/unit/test_k3_ledger_gate.py tests/unit/test_k3_transport_journal.py tests/unit/test_model_identity_preflight.py
```

### G0 y rutas alternativas

La crítica original S0 usa campos booleanos, objeciones y once preguntas; S1 usa assessment por eje y citas contra propuesta proyectada. **No existe todavía una traducción científica preregistrada, validada y comparable**. S0 y S1 no reciben exactamente el mismo conjunto de datos (S0 recibe dominio/cruce/evidencia; S1 trabaja sobre proyección y restricciones), y los presupuestos/esquemas difieren. No declarar un ensayo A/B comparable por hashes iguales, por `REVIEW_SUPPORTED` o por una tabla sintética. El flujo de validación científica necesita referencias revisadas independientemente y una métrica congelada; no hay tres revisores competentes acreditados. Los indicadores P0_SEMANTIC=OPEN; G0=DRAFT_NOT_APPROVED; SCIENTIFIC_ADVANTAGE=NOT_ESTABLISHED; DESKTOP_VISUAL_ACCEPTANCE=NOT_VERIFIED no cambian.

## Siguiente acción exacta (histórica, al cierre de fase 05)

Fase 06 — Comparabilidad S0/S1 y preflight experimental: analizar por caso la información efectiva de `prompt_critica` y `direct_request`, identidad del candidato, restricciones, dominio/evidencia y output schemas; crear manifiesto de asimetrías y contrato de resolución (sistema, usuario, schema, modelo, muestreo, timeout, retries, budget, tokenización), dejando BLOCKED donde no hay equivalencia. No hacer de un mensaje S0 una petición S1 por renombrar el hash. Proponer adaptación mínima del prompt a igualdad de hechos manteniendo la diferencia de método; medir tamaño y política de tokenización offline sin inferencias. Resolver política de adjudicación S0 con rechazo/unknown/errores y coste antes de solicitar G0; respetar tres revisores, fuentes, los 18 casos de desarrollo y los 8 de A, sin abrir reserved. Mutar stuffing/transferencia legítima/dominio equivocado/metric swap, conservar desconocido y proteger el resultado. Ejecutar regresión íntegra si se obtiene acceso a un checkout completo, no inventar resultados. No modificar ASTRA, BLACKFORGE ni el runtime productivo sin G0.

## Fase 06 — Comparabilidad científica S0/S1 (diagnóstico offline)

Baseline: `08d95995c6918dcadbdb0464c093637f60679756`. Alcance experimental F06 COMPLETADO **para diagnosticar desigualdades y bloquear inferencias injustificadas**, no para resolverlas. Estado de comparabilidad: BLOCKED. G0 DRAFT_NOT_APPROVED. P0_SEMANTIC OPEN.

### Fuentes y análisis de contratos

- **STATICALLY_INSPECTED:** `src/criba/interprete/contrato.py` blob `977fafa15c56b226b04f2b5af79962c4e54f683a`, funciones `prompt_critica`/`_datos_prompt`/`validar_critica`/`separar_errores_critica` y `schema_critica`. S0 usa un prompt de crítica con PROBLEMA, DOMINIO, CRUCE, BLOQUEO IDENTIFICADO, RESTRICCIONES OBLIGATORIAS, EVIDENCIA LOCAL PERTINENTE, CONTENCION_DECLARADA, PROPUESTA A CRITICAR completa. Devuelve booleanos, objeciones, incertidumbre y preguntas Q1–Q11.
- **VERIFIED_BY_EXECUTION (laboratorio):** `semantic_lab.py` blob `5f9b9c8121b7d4499bc50c713b986b68e785ae12` y `semantic_cases.py` blob `cc713aee9d7198fdef38e4d9bbf5e351ff6eee95`. S1 DIRECT contiene query, restrictions, project_proposal de seis campos, restriction_claims_unverified; devuelve assessments de ejes/citas. La propuesta original incluye pertinencia, aportacion_por_tecnica, evidencia_citada y novedad, que la proyección S1 omite. S0 y S1 tienen distinta información y distinta gramática de resultado.
- **VERIFIED_BY_EXECUTION:** el plan A de `pilot_gate.py`, blob `74cac16e6e5458c076afeab22cef643e401fecc9`, tiene 8 casos × 2 brazos = 16 slots, sin autorizaciones. Es un conjunto de desarrollo publicado, no holdout independiente. NO lectura de reserved.
- **NO_EQUIVALENCE:** mismo alias o max_tokens NO garantiza información, tratamiento del error, número de llamadas, tokens efectivos, adjudicación o modelo en memoria equivalentes. S0 critic real y S1 laboratorio no pueden considerarse científicamente comparables ahora. El cambio F05 en el puente evita falsificar identidad a través de hashes; no los alinea. Ninguna etiqueta o cita literal constituye prueba de pertinencia.

### Instrumento y pruebas

- Nuevo `criba-blackforge/benchmarks/innovation/semantic_pair_preflight.py`: read-only, sin red ni runtime productivo automático; `preflight` compara datos congelados, identidad canónica S1, settings reportados, campos extra, proyección, hashes y bytes UTF-8. `inspect_production_pair` puede invocar `contrato.prompt_critica` en un checkout completo, sin invocar el intérprete. `normalize_s0_diagnostic` devuelve UNMAPPED, nunca inferir SUPPORT/REJECT de booleanos sin protocolo validado.
- Rechazo estricto de campos de referencia/etiqueta/variante en payload, JSON duplicado/NaN, datos no coincidentes, parámetros fuera de rango, reintentos y contexto excedido. Diferencia expresada por motivo, nunca escondida tras agregado. Siempre `status=BLOCKED`, `G0_NOT_APPROVED`, `S0_OUTCOME_MAPPING_NOT_VALIDATED`, `MODEL_LOAD_IDENTITY_UNATTESTED`, `INDEPENDENT_REFERENCE_PENDING`, `PROVIDER_DISPATCH_UNVERIFIED`, `scientific_advantage=NOT_ESTABLISHED`; hashes y parámetros reportados no autentican envío.
- 50 nuevas pruebas del módulo sobre captura S0 **sintética de forma**, casos A reales del laboratorio, campos perdidos, filtración de etiquetas, settings, falta de tokenizer/identidad, mapeo no aprobado. 158 regresiones previas repetidas. **208 PASS** Python sandbox, último rerun 4.29 s. Dos archivos fuente/test exactos con git hash-object `89f5d1e1442c38dbdd8b51650fb2554bfe4a4701` y `9c01495416c39a79c83b444a58f860dbfa730c79`; documento de protocolo `a17aa6014c2bd8210c775b839f81555394e152f0`. Blobs remotos creados y cotejados por SHA.
- **12/12 mutantes adversariales detectados**, incluidos autoconceder GO, omitir leakage, ignorar desigualdad de candidato, aceptar request S1 incorrecto, falsear modelo, forzar SUPPORT a S0, perder control de tokens y aprobación. Un primer mutante redundante de validación sobrevivió y fue sustituido por uno material que desactiva el control íntegro; se restauró el código y el conjunto volvió a PASS.
- `compileall` dirigido PASS, líneas nuevas <= 100. NO EJECUTADO: generación productiva auténtica `prompt_critica` en sandbox (seam mínimo), tests del checkout completo, Ruff, mypy, CI, proveedor, tokenizer real, adjudicación humana, Windows/GUI. No declarar esos PASS. Cero inferencias reales y cero coste.

### Protocolo y decisión

Ver `docs/research/semantic-correspondence/g0-draft/PHASE06_COMPARABILITY.md`. Propuesta a aprobar: paquete factual **idéntico** para S0/S1 y solo estrategia de crítica distinta; si altera la crítica productiva actual, denominarla variante nueva y no S0 original. Congelar taxonomía de outputs, directrices de UNKNOWN/ERROR/NOT_RUN, juez independiente, origen de datos, modelo y tokens efectivos, presupuesto de una llamada por slot y protocolo A/B/C. Los ocho casos A son desarrollo; las referencias no son gold ni observaciones de eficacia. Sin evidencia y aprobación, NO-GO de inferencias.

Comando desde checkout `criba-blackforge`:
```sh
python -m pytest -q tests/unit/test_semantic_pair_preflight.py tests/unit/test_k3_semantic_binding_phase05.py tests/unit/test_k3_receipt_integrity.py tests/unit/test_k3_ledger_gate.py tests/unit/test_k3_transport_journal.py tests/unit/test_model_identity_preflight.py
```

## Siguiente acción exacta (histórica, al cierre de fase 06)

Fase 07 — Consolidación de permisos y preflight G0. Reconciliar las dos versiones de prerregistro y `VERSIONES_EFECTIVAS_G0.md` con hashes reales; crear checklist única de autorizaciones con estado explícito del propietario, sin asignar firmas ni defaults arbitrarios. Si el contrato S0/S1 continúa siendo injusto y no hay modelo efectivo/fuentes/juez independiente/verificación local, documentar NO-GO y posponer llamadas; avanzar tareas offline productivas sin bloquear toda la campaña. Revisar que `pilot_gate.py` no permita promocionar un threshold con falsos datos, y que `K3` y `physical_calls` no se traten como autenticidad. No tocar ASTRA, BLACKFORGE, runtime productivo ni main. No inferencias ni gasto.

## Fase 07 — Consolidación de G0, manifiesto y autorización (NO-GO)

Baseline GitHub: `a385ecf774d394c8988493afbe8fc658957179c7`. Resultado: verificación de **integridad de fuentes y lista de permisos** completada en laboratorio aislado. NO se ha aprobado G0 ni realizado ninguna llamada a un modelo. El P0 semántico continúa abierto.

### Reconciliación ejecutada

- Raw SHA256 exacto comprobado para `semantic_lab.py` = `e0692a16559309e34a47af4c6dd8987695df1d978c2da6cd1d0956ae40623ca6`; `semantic_cases.py` = `af9e945eaa558d28be9a123d63c59380b11636bbff28dd389b46d048415aedfa`; `pilot_cases.json` = `fad4b6fc0ac3a421d3475864ed7daef37be38cfa03c3551c7ff5b46a234c4c14`; `pilot_gate.py` = `69d1d283b2be5cb9334a8c4c46416fe7d42a4667572a3a69c1858c402a276abe`.
- Los cuatro coinciden con las versiones EFECTIVAS de `VERSIONES_EFECTIVAS_G0.md`; el prerregistro inicial cita `ef07d195...` para lab, versión histórica no efectiva. No se han editado los documentos archivados ni ASTRA.
- `semantic_cases.cases()` contiene 58 variantes development, 12 raíces. Manifiesto: 18 variantes, 3 raíces, 5 SUPPORT/11 REJECT/2 UNRESOLVED. **18/18 digest(case)**, IDs, etiquetas y versión development coinciden. Agenda exacta A/B/C: 16/36/108, prefijos, IDs específicos de A, identidades de slots y repeticiones. No hay reserved ni referencias independientes; los digest incluyen etiquetas autorales, no truth.
- El documento `VERSIONES_EFECTIVAS_G0.md` es válido como checkpoint histórico, pero sus descripciones del puente de crítica, storage y runtime ya no son declaraciones confirmadas para la rama de campaña: fases 02 y 05 cambiaron los dos primeros; fase 04 encontró que la comprobación productiva remota solo valida alias. No promover documentación histórica a evidencia de integración vigente.

### Nueva herramienta fail-closed

`criba-blackforge/benchmarks/innovation/g0_authorization_preflight.py` crea un reporte offline de integridad y 13 decisiones G0. Comprueba SHA de bytes, manifiesto por contenido, módulo Python importado efectivamente desde el árbol inspeccionado y agenda. Si falta archivo, cambia hash, se mueve la identidad del caso, hay duplicación, cambia referencia o falta un slot, informa FAILED/NOT_ACCESSIBLE y se mantiene NO-GO. **Siempre** retorna decision=NO_GO, authorization=NOT_GRANTED_BY_THIS_TOOL, G0=DRAFT_NOT_APPROVED, P0=OPEN, phase_A/B/C=NOT_AUTHORIZED, provider_consumption=null. Un archivo que afirme `approved: true` no autentica al propietario. No conecta runtime, red o proveedores; sin credenciales. La aprobación futura debe venir de autorización explícita comprobable con prerequisitos materiales resueltos, fuera de este checker.

`docs/research/semantic-correspondence/g0-draft/G0_DECISION_MATRIX.md` registra la matriz, condiciones y plan de continuidad. El resultado de `pilot_gate.summarize` ante **16 registros sintéticos fabricados** con las etiquetas del propio manifiesto es THRESHOLDS_MET_ONLY y 16 supuestas llamadas físicas; no acredita ninguna inferencia. La herramienta nueva se mantiene NO-GO incluso si el gate muestra umbrales perfectos. Las fases B/C nunca se autorizan por aprobar A.

### Ejecución directa y mutation reasoning

- En `/mnt/data/cbs_final_phase07_sandbox` con los mismos cuatro archivos exactos del remoto y los componentes aislados de fases 01–06: **242 passed** = 208 previas + 34 nuevas, última ejecución 4.54 s. SHA de blobs Git nuevos: script `74724174908e508b11776c72dd2cd8b2aafb3292`; tests `7a85c7513d1a7007173636adf15fa192db8f6fed`; matriz `976cdf3ae1d072981e46bd77dd83788f5ee70d8f`. Las tres cargas remotas verificadas con SHA exacto. `compileall` dirigido PASS, git diff --no-index --check sin diagnósticos; git diff --no-index rc=1 significa archivos diferentes, no fallo de whitespace.
- 12 mutaciones individuales: **10 detectadas, 2 sobrevivientes** por controles redundantes: quitar comprobación explícita de `len(rows)==18` aún es bloqueado por los conteos y contraste de agenda; quitar igualdad de `reference` aún deja verificación por digest que incluye la etiqueta. Mutación compuesta que desactiva referencia y digest: detectada (2 fallos). Mutación compuesta tamaño+conteo también sobrevive porque `gate.references` y agenda protegen el contrato; no es prueba de ausencia de cobertura. Se declara el resultado real, no 12/12.
- Sandbox no es clon completo. **NOT_EXECUTED**: suite íntegra del monorepo, tests Qt, CI de commit (sin check runs), Ruff, mypy y Windows. Tests productivos del contrato completo siguen pendientes. No se ha realizado inferencia, gasto, firma G0, merge ni despliegue.

Comando offline desde el checkout completo `criba-blackforge`:

```sh
python -m benchmarks.innovation.g0_authorization_preflight
python -m pytest -q tests/unit/test_g0_authorization_preflight.py tests/unit/test_semantic_pair_preflight.py tests/unit/test_k3_semantic_binding_phase05.py tests/unit/test_k3_receipt_integrity.py tests/unit/test_k3_ledger_gate.py tests/unit/test_k3_transport_journal.py tests/unit/test_model_identity_preflight.py
```

### Condición de salida

**Fase 07 terminada en su alcance de inventario y comprobación; autorización G0 = NO_GO.** No se buscará firma del propietario para ejecutar A/B/C mientras S0/S1, referencias, jueces, identidad física y transporte productivo sigan pendientes. El avance funcional offline sigue independiente de G0.

## Siguiente acción exacta (histórica, al cierre de fase 07)

Fase 08: inspeccionar y reproducir la ruta productiva de estados PROPUESTA/PENDIENTE/ABSTENER/ERROR/UNRESOLVED en `openai_compatible.py`, `InterpretationResult`, `JuezInterprete`, `InterpreteStore`, `invention_service`, Shadow, exportadores y consumidores SUPRA. Probar respuestas parciales, crítica fallida, error de red, retry oculto, resultado obsoleto, caché legacy, ausencia de evidencia y múltiples ejecuciones. Crear sentinelas que fallen ante promoción silenciosa de UNKNOWN/PENDIENTE a éxito, sin cambiar ASTRA, scoring científico ni BLACKFORGE; reparar lo que pueda verificarse en GitHub y conservar lo que requiere ejecución Windows. No inferencias ni gasto, no main merge ni publicaciones.

## Fase 08 — Integridad de estados productivos, caché y juez de Inventar

Baseline: `ba201b2f91bed68d9971b8d45737fd1248c668e2`. Alcance: dos reparaciones fail-closed de discrepancias entre estados y un test de integración nuevo para un checkout real. **Fase 08 completada dentro de este alcance; no se declara viaje de producto completo validado.**

### F08-01 P1 — Caché de interpretaciones con estados contradictorios

- **STATICALLY_INSPECTED:** `src/criba/interprete/store.py`, objeto Git original `281e530b1a40042f16927bacf176c136e8e4ebb5`. `InterpreteStore.cache_valido` verificaba `row.evaluation_status=CRITIQUED`, versiones, `interprete_result.estado=PROPUESTA`, validación estructural y crítica; **no** exigía concordancia con `row.veredicto`, `interprete_verdict`, `interprete_evaluation_status`, `interprete_analisis` ni `interprete_result.error`.
- **VERIFIED_BY_EXECUTION, ISOLATED_SEAM:** extracto literal de `cache_valido` del objeto remoto (únicas sustituciones: funciones de `validar_propuesta` y `validar_critica` por validadores mínimos para aislar esta condición). Baseline: **1/9 pruebas pasa, 8 fallan** porque la función reutiliza filas parseables que contienen PENDIENTE, ERROR, timeout o análisis contradictorio. No afirmar que se reprodujo un modelo, UI o todo el contrato de producción.
- **FIX:** comprobar antes de usar la caché que los estados exterior/interior dicen inequívocamente `PROPUESTA`/`CRITIQUED`, análisis vacío y error interno vacío. Nunca modificar/borrar el historial. Fallos y casos legados pasan a revalidación o retry; no se convierten en cero ni aceptación. El nuevo blob de `store.py` es `64aca033891d38285c8dc2812cdb07a5cdb9affb`.
- **Regresión aislada ejecutada:** 15 casos de caché/SQLite con cierre y reapertura simulando filas parseables contradictorias, más pruebas externas de estado. Se añadieron pruebas para invariantes de versión y estado exterior tras detectar false coverage inicial. Función candidata verificada por FNV1a32 `79e11b67` del extracto exacto remoto; 8/8 mutaciones dirigidas detectadas, restauradas, rerun verde. El conjunto fase 08 de cache + juez tiene **27/27 PASS**. El módulo de almacenamiento completo no se ejecutó por falta de checkout íntegro.
- **Prueba real preparada, NOT_EXECUTED:** `tests/unit/test_interpreter_state_integrity_phase08.py` usa `Storage` real, `InterpreteStore.record_decision/get_verdict`, `verification.interpreter_cases`, recuperación SQLite, reemplazo transaccional de un registro inválido y conteo de `interprete_attempts`. La aceptación de esa prueba es requisito pendiente; no convertir preparación en PASS.

### F08-02 P1 — Crítica marcada CRITIQUED aunque la propuesta esté pendiente

- **STATICALLY_INSPECTED:** `src/criba/inventar.py` original blob `59af1f1ba40689dc4ee57ee4f34029ebcc6dd37d`, ruta `_desarrollar` -> `_judge`. El bucle pasaba `proposal.critica` directamente a `_judge` sin comprobar que `proposal.estado=PROPUESTA`. Una propuesta fallida con crítica `CRITIQUED` estructuralmente válida producía `entry.judge.evaluation_status=CRITIQUED`. La propia `entry.estado_interpretacion` seguía pendiente; era inconsistencia de presentación/consumo, no ejecución SUPRA probada.
- **VERIFIED_BY_EXECUTION, ISOLATED_SEAM:** función original `_judge` aislada, con validador de crítica sintético, confirma `CRITIQUED` ante una propuesta pendiente y crítica positiva. La corrección solo entrega dicha crítica al juez si el estado principal es PROPUESTA, conservando el payload original en `entry.critica` para auditoría. En estados PENDIENTE, ERROR, ABSTENER, NOT_RUN y UNKNOWN, el juez emite NOT_EVALUATED, nunca éxito; éxito genuino sigue CRITIQUED. Dos mutaciones del selector nuevo detectadas. Blob candidato de `inventar.py` `b331e273311d5b94457f6c1e79cdf51d0d4e7508`.
- **Prueba real preparada, NOT_EXECUTED:** caso integrado `invent(... proponer=synthetic_proposer, history_storage=False)` con fuentes offline falsas y casos de propuesta válida/pendiente. No hay modelo real ni tráfico. Probarlo en checkout completo.

### Inspección de consumidores y límites

- **STATICALLY_INSPECTED:** `src/criba/interprete/puerto.py`: `InterpretationResult.to_campos` convierte no-propuestas a PENDIENTE, pero conserva diagnóstico de crítica y otros campos; el consumidor debe verificar explícitamente estado. `src/criba/ui/actions.py`, `proposal_view.py` y CLI filtran `estado_interpretacion=PROPUESTA` antes de opciones SUPRA/guardado; no se verificó GUI real ni se garantiza que toda API/consumidor haga lo mismo. El registro estructurado del fallo debe seguir visible solo como diagnóstico.
- **VERIFIED_BY_EXECUTION:** regresión offline previa de fases 01–07 repetida sin cambios, **242/242 PASS** en sandbox parcial; el conjunto fase 08 aislado tiene **27/27 PASS**. No afirmar 269 casos en un checkout monorepo único. `compileall` del subconjunto candidato y pruebas de mutación dirigidas PASS. Ruff/mypy, suite íntegra, tests originales de `JuezInterprete` y Windows **NOT_EXECUTED** para esta candidata.
- Sin changes de scoring, ASTRA, SUPRA productivo, BLACKFORGE ni G0. G0=NO_GO; P0_SEMANTIC=OPEN; modelo físico no acreditado; contabilidad de llamadas reales no acreditada.

Comandos pendientes de validación en clon Windows o CI, desde `criba-blackforge`:

```sh
python -m pytest -q tests/unit/test_interpreter_state_integrity_phase08.py tests/unit/test_interpreter_hardening.py tests/unit/test_inventar.py tests/unit/test_interprete_puerto.py tests/unit/test_invention_acceptance_gate.py
python -m pytest -q tests/unit --ignore=tests/fixtures
python -m compileall -q src/criba/interprete/store.py src/criba/inventar.py
python -m ruff check src/criba/interprete/store.py src/criba/inventar.py tests/unit/test_interpreter_state_integrity_phase08.py
git diff --check
```

## Siguiente acción exacta

Fase 09: comprobar integración productiva transversal de Inventar->historial->Shadow->dossier SUPRA y del Juez->InterpreteStore->pipeline->CLI/API, incluyendo carreras de último escritor, caché que envejece entre read y write, errores/retries, campos no verificados en export y reanudación entre ejecuciones. Primero ejecutar las pruebas de integración fase08 en checkout completo si ya es accesible; si no, preservar NOT_EXECUTED y ejecutar sentinelas aislados sobre contratos críticos. Reparar solo defectos reproducibles con tests; evitar que `NOT_EVALUATED` o `PENDIENTE` se conviertan en evidencia/puntuación/estado `PROPUESTA` al cruzar las capas. No activar G0 ni tocar ASTRA/BLACKFORGE, no gastar, desplegar, borrar o mezclar a main.
