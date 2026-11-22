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

## Siguiente acción exacta (histórica, al cierre de fase 08)

Fase 09: comprobar integración productiva transversal de Inventar->historial->Shadow->dossier SUPRA y del Juez->InterpreteStore->pipeline->CLI/API, incluyendo carreras de último escritor, caché que envejece entre read y write, errores/retries, campos no verificados en export y reanudación entre ejecuciones. Primero ejecutar las pruebas de integración fase08 en checkout completo si ya es accesible; si no, preservar NOT_EXECUTED y ejecutar sentinelas aislados sobre contratos críticos. Reparar solo defectos reproducibles con tests; evitar que `NOT_EVALUATED` o `PENDIENTE` se conviertan en evidencia/puntuación/estado `PROPUESTA` al cruzar las capas. No activar G0 ni tocar ASTRA/BLACKFORGE, no gastar, desplegar, borrar o mezclar a main.

## Fase 09 — Juez, caché concurrente y callbacks asíncronos de Shadow/SUPRA

Baseline: `352db907535720fef87b8f581012bc168687f781`. Alcance: reparación de dos carreras reproducidas con dependencias controladas; la integración Qt y el viaje completo del monorepo siguen pendientes. **G0=NO_GO; P0_SEMANTIC=OPEN.**

### F09-01 P1: segundo GET de la caché sin validar (juez -> storage)

- **STATICALLY_INSPECTED:** `criba-blackforge/src/criba/interprete/juez.py` original Git blob `44fcab9ac8cd6d9d2c80e1853154f898f1c35d7f`. La lectura anterior a `proponer` aplicaba `InterpreteStore.cache_valido`, parámetros y `prompt_sha256`. Pero si `record_decision` devolvía `deduplicated` tras competir con otro escritor, el segundo `get_verdict` recuperaba `response.interpretation` y ejecutaba `idea.update` sin ninguna de esas validaciones. El `BEGIN IMMEDIATE` de `record_decision` no cubre el GET posterior: otra escritura o estado dañado puede aparecer tras liberar la transacción.
- **VERIFIED_BY_EXECUTION, ISOLATED_SEAM:** se reprodujo el método de `JuezInterprete` con filtro, puerto y store falsos que fuerzan el interleaving read -> generate -> store.deduplicated -> read. Baseline: 5 de 6 controles fallaban, incluido reemplazar una respuesta fresca por un ganador pendiente, incompleto, con otro prompt o con parámetros distintos. No se reprodujo ese interleaving con dos procesos del Storage productivo; esa integración es EVIDENCE_PENDING.
- **FIX:** `JuezInterprete._cache_reusable` concentra un único gate de coherencia para ambos GET (validación de `InterpreteStore`, procedencia, parámetros y SHA del prompt). Antes de generar se congela mediante `deepcopy` la entrada para revalidar con la identidad original incluso si el intérprete muta la idea. El segundo ganador solo puede sustituir el resultado si revalida. Si cambió/desapareció, se conserva la generación fresca pero se declara `_registro={"status":"unregistered","reason":"concurrent_winner_not_reusable"}`, **nunca se finge que se persistió**. No se escribe una tercera vez ni se inicia otra inferencia.
- **VERIFIED_BY_EXECUTION:** 10 controles aislados del juez PASS tras reparación, incluidos ganador válido y caché válida anterior que evitan llamadas adicionales, cambios de entrada y ausencia de ganador. No se reemplazó el resultado por un estado inventado. Archivo candidato `juez.py` blob `a18c65cd6c5205435efee312b974fafd41388d96`.
- **NOT_EXECUTED IN FULL CHECKOUT:** test real `tests/unit/test_juez_concurrent_winner_phase09.py`, blob `bcad240fdd74999d7bdb8ded447688114aaf5704`. Debe probar con `JuezInterprete`, `InterpreteStore.cache_valido`, y `verification.interpreter_cases` genuinos; puerto/store con carrera simulada. No confundir prueba preparada con test verde.

### F09-02 P1: trabajo asíncrono de SUPRA atribuido a otra sesión de Shadow

- **STATICALLY_INSPECTED:** `criba-blackforge/src/criba/ui/actions.py` original Git blob `d3a76a39f356141c2ab295b6b9fe9ba4f1061db7`: `on_desarrollar_supra` creaba Worker y conectaba `done`/`fail` solo con `win`. `_on_supra_dossiers_done` escribía `sheet=win.invent_sheet; sheet["supra_runs"]=report["runs"]` sin identidad de la sesión que lanzó el trabajo; la ruta de fallo sobreescribía igualmente el estado de la pantalla. Un worker de la sesión A puede terminar mientras el usuario trabaja en B; también puede competir con un segundo envío de la misma sesión.
- **VERIFIED_BY_EXECUTION, ISOLATED_SEAM:** callback extraído con `refs`, `set_chip`, `_activity`, `show_error` controlados. La versión base falló al recibir argumentos de identidad (no estaban soportados). Se probó la inyección de callbacks obsoletos en sesiones distintas, mismo `run_id` reutilizado, un envío posterior del mismo sheet, un `run_id` modificado y señales terminales duplicadas.
- **FIX:** `on_desarrollar_supra` crea un token único por envío y captura el objeto `sheet` y `run_id` al conectar signals. Ambos callbacks exigen identidad del objeto de sesión, token todavía vigente y `run_id` cuando existe. El primer callback terminal aceptado consume el token: un `done` duplicado o `fail` tardío no puede escribir una segunda vez. Los callbacks legacy directos mantienen signatura compatible cuando no se proporcionan esos argumentos; la ruta Worker nueva siempre los proporciona. No se ha alterado `_execute_supra_dossiers`, su cliente, ni GET/readback.
- **VERIFIED_BY_EXECUTION:** 6 pruebas aisladas del callback, con escenarios positivos para el envío actual y negativos para callbacks tardíos. Archivo candidato `actions.py` blob `c9633d498dbb338d50552e7d4971c5e0e7c0e454`.
- **NOT_EXECUTED IN FULL CHECKOUT:** `tests/unit/test_shadow_supra_stale_callback_phase09.py`, blob `147cd4eef5f451f41a7402a3e5a32abd8a76e3d2`, usa Worker y dossier IO falsos, y el `actions` real cuando Qt esté disponible. No se ejecutó el GUI real. No considerar un resultado de SUPRA acreditado por el contenido de un callback simulado.

### Pruebas y false coverage

- **VERIFIED_BY_ME:** `/mnt/data/cbs_final_phase09_sandbox`, ejecutadas **16/16** pruebas aisladas del método/callback extraídos tras restaurar código. Se probaron 11 mutaciones no destructivas y fueron detectadas: omitir validación del ganador, SHA, parámetros, copia congelada y estado de registro; omitir token, `run_id`, identidad del sheet, guard de `done`/`fail` y consumo de señal terminal. Los dos controles de identidad de sesión/run son deliberadamente distintos; se añadió el caso `run_id` reutilizado al detectar protección redundante.
- **VERIFIED_BY_ME:** la regresión offline exacta de fases 01–07 fue reejecutada con `PYTHONPATH=src:.` en el sandbox disponible: **242/242 PASS** (4.38 s). Una primera ejecución sin `PYTHONPATH` no pudo recopilar tres módulos por `ModuleNotFoundError`; se corrigió la invocación y se reejecutó, sin modificar pruebas. Estos 242 **NO incluyen** la suite real de fase 08 ni de fase 09. Las 16 pruebas de fase 09 pertenecen a otro sandbox, no a un único checkout.
- **VERIFIED_BY_ME:** compileall dirigido sobre los fragmentos aislados y sus tests PASS. **NOT_EXECUTED:** integración real de módulos completos fase 09, PySide6/Qt, full pytest, Ruff, mypy, Windows, CI (comprobar tras push). No hay clon completo; acceso HTTPS GitHub desde el contenedor falló por DNS y solo se puede inspeccionar/modificar código remoto con herramientas GitHub. Cero inferencias, cero gasto, cero SUPRA productivo.
- **EVIDENCE_PENDING:** una tercera escritura entre `record_decision` y segundo GET aún podría hacer que el resultado leído dejase de ser la última versión. El guard prueba coherencia de la fila observada, no serializabilidad futura. Un CAS/revisión persistente sería otra modificación y requiere diseño de concurrencia/contrato.
- **EVIDENCE_PENDING:** `Storage.save_invention` admite en el historial un entry con estado `PROPUESTA` y mecanismo no vacío sin revalidar todo el contrato; `on_desarrollar_supra` selecciona por estado. Los consumidores downstream pueden poseer validadores propios y no se demostró ejecución efectiva de un dossier inválido. Fase 10 debe inspeccionar esos validadores y evitar promociones solo nominales sin romper la ruta determinista válida. Otros callbacks de recuperación SUPRA y errores de worker deben revisarse por identidad.
- Se mantienen interfaces, rama productiva main, SUPRA remoto, BLACKFORGE, ASTRA, scoring científico y G0 intactos. No se han fusionado branches, desplegado ni publicado datos privados.

### Comandos de verificación pendientes (desde checkout completo `criba-blackforge`)

```sh
python -m pytest -q tests/unit/test_juez_concurrent_winner_phase09.py tests/unit/test_shadow_supra_stale_callback_phase09.py tests/unit/test_interpreter_state_integrity_phase08.py tests/unit/test_interpreter_hardening.py tests/unit/test_inventar.py tests/unit/test_shadow_interpreter_journey.py
python -m compileall -q src/criba/interprete/juez.py src/criba/ui/actions.py
python -m ruff check src/criba/interprete/juez.py src/criba/ui/actions.py tests/unit/test_juez_concurrent_winner_phase09.py tests/unit/test_shadow_supra_stale_callback_phase09.py
git diff --check
```

## Siguiente acción exacta (histórica, al cierre de fase 09)

Fase 10: persistencia y frontera de aceptación del dossier. Revisar las rutas de `Storage.save_invention`, restauración desde SQLite/JSONL, `shadow_invention_probe.chosen_entry`, `on_desarrollar_supra`, `_entry_para_desarrollo`, CLI `--dossier`, `supra_dossier.preparar_dossier` y `SupraClient` para determinar si un `PROPUESTA` falsificado/incompleto o un `PENDIENTE/UNKNOWN` legacy puede generar un dossier aparentemente acreditado. Reproducir con estado parseable corrupto y casos válidos, identificar validadores downstream antes de reparar. Verificar también callback `_on_supra_restore_done` contra sesiones activas y persistencia cross-run, y las regresiones preparadas en fases 08–09 si se obtiene checkout completo. No introducir falsos PASS ni llenar campos de evidencia sin fuente; preservar datos históricos, ASTRA, G0, y main.

## Fase 10 — Persistencia y frontera de aceptación de dossiers SUPRA

Baseline: `4008442c751cd8c96cfb30b5f9b6cf735bb2853d`. Resultado: guardas de aceptación compartidas, orden preparación→persistencia→worker y contextos de recuperación asíncrona añadidos a la rama de campaña. **Alcance corregido en fuente y probado por contrato aislado; integración Qt/CLI/SQLite del checkout íntegro NOT_EXECUTED**.

### F10-01 P1: rutas de aceptación divergentes

- **STATICALLY_INSPECTED, refutación parcial:** `actions._prepare_dossier_for_selected_idea` (ruta vertical SUPRA) YA comprobaba selected_index, query activo, PROPUESTA, candidate_id, hipotesis, mecanismo, prueba_concreta y siete campos de prueba; no declarar inseguras todas las rutas SUPRA. `preparar_dossier_desde_idea` deriva protocolos del núcleo determinista con fuentes declaradas y mantiene el estado NO_EJECUTADA; se preserva sin hacerle pasar por una respuesta del intérprete.
- **STATICALLY_INSPECTED:** `Storage.save_invention` solo exigía PROPUESTA y mecanismo; aceptaba una fila con hipótesis vacía, error de interpretación o `interprete_result` contradictorio y la archivaba con status PROPUESTA. `on_desarrollar_supra` y `cli inventar --dossier` filtraban solo la etiqueta PROPUESTA, incluso si faltaban mecanismo, protocolo o prueba. `supra_dossier.preparar_dossier` no contrastaba `estado_interpretacion` si estaba declarado.
- **FIX:** `src/criba/invention_acceptance.py` expone `errores_entrada_interpretada`, `exigir_entrada_interpretada` y `propuestas_para_supra`. Para ARCHIVO: exige estado PROPUESTA, hipotesis y mecanismo textuales, ausencia de error y coherencia de `interprete_result` si existe. Para SUPRA: añade candidate_id exacto, prueba_concreta, siete obligaciones de prueba discriminante, crítica no REJECTED, identidad de lote sin duplicados. Solo PENDIENTE_INTERPRETACION se omite; UNKNOWN, missing, enum inválido o fila no objeto bloquean el lote. El contrato verifica estructura y declaraciones, **no pertinencia causal, procedencia física, novedad o éxito científico**.
- **PRODUCT WIRING STATICALLY_INSPECTED:** `Storage.save_invention` aplica el nivel de archivo, sin exigir una prueba inventada a registros históricos y sin reescribir datos previos. `CLI inventar --dossier` y `Shadow on_desarrollar_supra` realizan preflight del lote y problema antes de empezar IO. La ruta vertical reutiliza la comprobación común y mantiene validaciones locales. `preparar_dossier` rechaza un estado de interpretación declarado incoherente; permite la ruta explícita del núcleo determinista sin ese marcador para preservar compatibilidad. Dossiers siguen SUPRA_EJECUCION_PENDIENTE y NO_EJECUTADA.
- **P10 efectos transversales:** preparo TODOS los dossiers antes del primer guardado (GUI y CLI); si falla la preparación del segundo, no se escribe el primero ni se envía el lote. Si falla el disco después de comenzar a guardar, pueden quedar archivos parciales; NO HAY transacción JSONL entre dossiers. No se inicia un worker si falla preparación o persistencia; la CLI devuelve 2 con error. La aplicación exacta del nuevo wiring no se ha ejecutado en GUI real.

### F10-02 P1: recuperación SUPRA tardía

- **STATICALLY_INSPECTED:** `on_restore_latest_supra` conectaba las señales done/fail a la ventana sin ligarlas al contexto de sesión. Una respuesta vieja podía escribir sobre una idea/paquete/problema posterior o aplicar un error de otra operación. El `_supra_callback_is_current` de F09 protege los envíos, no la recuperación.
- **FIX:** cada restore tiene token único y snapshot de identidad de hoja, packet, problema y run_id; ambos callbacks verifican esos elementos ANTES de mutar UI. La primera señal terminal válida consume token; señales tardías se ignoran. Un nuevo panel SUPRA, envío por lotes o slice vertical invalida el restore pendiente. Las llamadas legacy directas a callbacks conservan compatibilidad, pero no están protegidas si omiten el contexto.
- **VERIFIED_BY_EXECUTION, ISOLATED_SEAM:** 10 pruebas de contexto/callback sin Qt ni servicios; transiciones de mismo sheet con run_id cambiado, sheet/packet reemplazados, problem distinto, token nuevo, otro restore y señales duplicadas. Es prueba del guard y contexto, no confirmación de entrega Qt. Nuevos tests de import productivo para Qt están añadidos pero NOT_EXECUTED.
- **RESEARCH_QUESTION:** otras rutas asíncronas, especialmente callbacks de `on_supra_vertical` y health, aún requieren barrera de contexto equivalente si pueden convivir con sesiones nuevas. No declarar resuelto todo el riesgo de señales tardías.

### Evidencia ejecutada y mutaciones

- **VERIFIED_BY_ME:** Python 3.13, sandbox `/mnt/data/cbs_final_phase10_sandbox`. 67 tests de aceptación pura con el archivo EXACTO cuyo Git blob es `37e4a4bcdb0530cdbb065f41c5ec8d0cc1c9cc8f`; 10 tests de contexto de recuperación aislado; dos tests con SQLite REAL ejecutando la decisión exacta de `Storage.save_invention` con un esquema mínimo. **79/79 PASS**. Contraste anterior: tres entradas corruptas se guardaban con status PROPUESTA en el método antiguo, y el nuevo rechazo es determinista. No se ejecutó la clase `Storage` íntegra del checkout actual; el entorno SQLite usa un seam de `initialize`.
- 10 mutantes individuales de validación: **9 detectados y 1 sobrevive por protección redundante**; la mutación compuesta que elimina AMBOS controles de estado es detectada con **8 fallos**. Código restaurado y 77/77 validación + restore PASS, ampliado a 79/79 al incluir SQLite. No reportar 10/10 falsamente. Recuento de rondas anteriores separado: fases 01–07 **242/242 PASS**, repetidos en sandbox disponible; no mezcla con los 79 de fase 10. Compileall dirigido PASS.
- **REPORTED_BY_AGENT** suite 1791 ASTRA/156 dirigidos del handoff, no ejecutados personalmente para HEAD actual. **NOT_EXECUTED:** Qt/PySide6 no instalado, suite íntegra, CI, Ruff, mypy, empaquetado, EXE, transport real. Acceso git-clone a GitHub falló DNS; inspección de árboles, funciones, SHA y commits por herramientas de GitHub. Tests productivos preparados: `tests/unit/test_invention_acceptance_phase10.py`, `test_invention_boundaries_phase10.py`, `test_shadow_supra_restore_phase10.py`, `test_shadow_supra_export_boundary_phase10.py`. Ajustadas tres fixtures heredadas para protocolos sintéticos válidos. Requiere ejecutar esas pruebas en checkout íntegro antes de fusionar a main.
- Sin inferencias reales, gastos, modificación ASTRA, BLACKFORGE, merge o despliegue. G0=NO_GO, P0_SEMANTIC=OPEN, SCIENTIFIC_ADVANTAGE=NOT_ESTABLISHED.

### Riesgos residuales

- El ensamblador genérico `preparar_dossier` sin marcador `estado_interpretacion` preserva compatibilidad histórica y del núcleo, pero NO autentica el origen de un dict arbitrario; el envío productivo necesita validar su origen a través de su caller. El archivo de inventos acepta declaraciones históricas mínimas: no acredita prueba científica ni modelo físico. Evitar que consumidores interpreten PROPUESTA archivada como resultado verificado.
- Falla de disco en la segunda escritura JSONL: el primer dossier puede persistir aunque el segundo no. No se llama a SUPRA en ese caso, pero queda rastro de preparación parcial; estudiar journal/commit de lote y recuperación antes de afirmar atomicidad. Mutaciones de identidad entre validación y futuras llamadas, o estados legacy corruptos, siguen siendo potenciales.
- `shadow_invention_probe.chosen_entry` y `_entry_para_desarrollo` siguen con validación menos estricta para aceptación/revisión, respectivamente; requieren análisis según su propósito y no deben presentarse como certificación científica. La rama de campaña no tiene aceptación visual Windows y el contrato real completo no se ha ejecutado aquí.

### Comandos pendientes en checkout íntegro (desde criba-blackforge)

```sh
python -m pytest -q tests/unit/test_invention_acceptance_phase10.py tests/unit/test_invention_boundaries_phase10.py tests/unit/test_shadow_supra_restore_phase10.py tests/unit/test_shadow_supra_export_boundary_phase10.py tests/unit/test_gui_inventar.py tests/unit/test_shadow_supra_stale_callback_phase09.py tests/unit/test_supra_cross_thread_signal_regression.py tests/unit/test_invention_persistence.py tests/unit/test_dossier_integrity.py tests/unit/test_m2_dossier_desde_idea.py
python -m compileall -q src/criba/invention_acceptance.py src/criba/storage.py src/criba/supra_dossier.py src/criba/ui/actions.py src/criba/cli.py
python -m ruff check src/criba/invention_acceptance.py src/criba/storage.py src/criba/supra_dossier.py src/criba/ui/actions.py src/criba/cli.py tests/unit/test_invention_acceptance_phase10.py
git diff --check
```

## Siguiente acción exacta (histórica, al cierre de fase 10)

**Fase 11 — Persistencia de sesiones y evidencia**: reproducir y proteger consistencia entre `Storage.save_invention`, `sessions`, JSONL de dossiers y `InterpreteStore`. Foco: concurrencia de escritura/lectura, archive vs certified, reemplazo de fila corrupta sin borrar historia, comprobación de pertenencia candidate_id+run_id+problema, recuperación tras reinicio y error de disco entre dossiers; diseño mínimo de journaling sin mutar archivos de usuario existentes. Antes, si se dispone de checkout, ejecutar las pruebas completas introducidas en F08–F10 y corregir regresiones; en caso contrario registrar NOT_EXECUTED y seguir con verificaciones independientes. Analizar callback `on_supra_vertical` tardío contra cambios de sesión. No inferencia, no aprobación de G0, no tocar ASTRA/BLACKFORGE/main, no forzar borrados ni despliegues.

## Fase 11 — Consistencia JSONL: escritores, revisiones y recuperación

Baseline: `54c0530fcfb78ace9120df38d0188d555886dfbd`. Alcance ejecutado: **corrección dirigida del log JSONL de dossiers/observaciones**. Las uniones SQLite↔JSONL y callbacks verticales no se declaran completadas; pasarán a F12. G0=NO_GO; P0_SEMANTIC=OPEN; ASTRA/main sin modificar.

### F11-01 P1 — Dos escritores aceptan simultáneamente el mismo dossier_id

- **STATICALLY_INSPECTED:** `src/criba/supra_dossier.py` original Git blob `9c15940c56b58747bcdcf470e1266f12c43fce2d`, `guardar_dossier`: `_leer_historial` → comprobación de identidad → `path.open("a")` sin exclusión. `registrar_resultado` calculaba `revision_index = len(previous_revisions)` del historial y añadía sin lock, permitiendo dos revisiones con el mismo índice.
- **VERIFIED_BY_EXECUTION / RECONSTRUCTED_FUNCTIONS:** reproducción determinista de carrera con `Barrier(2)` antes del append del código original; 3 rondas con **2/2 escritores que devolvían éxito** y 2 líneas del mismo dossier_id con mecanismos distintos. Esto provoca identidad ambigua al volver a leer, no una exportación acreditada. El fragmento es fiel al original remoto pero no importado desde el clon íntegro.
- **FIX:** `_historial_exclusive` crea `.dossiers.jsonl.lock` persistente y usa `fcntl.flock` POSIX / `msvcrt.locking` Windows. **Ambas escrituras productivas** `guardar_dossier` y `registrar_resultado` toman el mismo bloqueo alrededor de leer, validar, asignar revisión y añadir. No se elimina el sidecar, pues la eliminación durante uso separaría el dominio de exclusión. El lock es ADVISORY: requiere que todos los escritores usen el código reparado. Windows **NOT_EXECUTED**.
- **VERIFIED_BY_EXECUTION / RECONSTRUCTED_FUNCTIONS:** 12 hilos con idéntico dossier_id y cuerpos distintos → exactamente 1 guardado, 11 rechazados; 5 procesos con `multiprocessing.spawn` → exactamente 1 guardado y 4 rechazados; 50 escrituras concurrentes del mismo cuerpo → una sola línea idempotente. Para observaciones con misma `execution_id`/protocolo, 12 hilos y 6 procesos produjeron índices 0..N-1 sin colisión. Casos sintéticos no acreditan ejecución causal.
- El `execution_resolver` se consulta **fuera del lock**, tras comprobar que el dossier existe y no es ambiguo; se vuelve a verificar dentro del lock. Así no se llama a proveedores por dossiers huérfanos ni se provoca deadlock por callbacks reentrantes que necesiten escribir historial. Una lectura previa puede quedar obsoleta y provocar rechazo conservador, nunca atribución automática. `lecciones_previas` mantiene la reverificación del recibo por lectura. Una vez confirmado un resultado, las correcciones siguen siendo revisiones; no se reescribe ni se borra el historial.

### F11-02 P1 — Un final de JSONL incompleto destruye la legibilidad del siguiente append

- **VERIFIED_BY_EXECUTION / RECONSTRUCTED_FUNCTIONS:** un archivo terminado en `{"dossier_id":"old","mecanismo":"torn"` recibía otro JSON sin separador. Ambos quedaron fusionados en una sola línea inválida; `_leer_historial` omitió ambas entradas.
- **FIX:** `_append_historial` construye la línea íntegra, valida JSON finito, añade separador si el archivo termina sin LF, escribe y ejecuta `flush+os.fsync` antes de devolver éxito. Nunca trunca ni reescribe el fragmento roto original. El lector trata cada línea como bytes independientes; un UTF-8 final incompleto no impide recuperar líneas posteriores. JSON con claves duplicadas o `NaN/Infinity` se considera no fiable y se ignora, sin convertirlo a identidad válida. Se conserva físicamente el contenido anterior. **No se garantiza recuperación del fragmento corrupto**, reparación automática del historial, atomicidad de batch ni durabilidad del directorio tras apagón.
- Un `fsync` que lanza excepción no se convierte en `NOT_WRITTEN`: los bytes podrían haberse añadido. Un reintento con la misma identidad/cuerpo debe ser idempotente. Si el segundo dossier de un lote falla, sigue pudiendo quedar persistido el primero (F10); el nuevo lock serializa registros individuales, **no** crea una transacción multi-dossier.

### F11-03 pruebas y mutaciones

- **VERIFIED_BY_ME:** sandbox `/mnt/data/cbs_final_phase11_sandbox`, Python 3.13, fuentes de secciones críticas copiadas y cotejadas con el código original/candidato GitHub, no un import productivo íntegro. **30/30 PASS** en 4.24 s, tests de concurrencia de hilos/procesos `spawn`, tail truncado, UTF-8 incompleto, JSON ambiguo/no finito, idempotencia, reinicio, resolución reentrante, revisión 2021→2035, recibos no concordantes, cero crédito sin resolver, error `fsync` e intento huérfano. `compileall` dirigido PASS. **10/10 mutantes detectados**: lock de escritor, lock de revisión, cola truncada, duplicados, `NaN`, omisión de `fsync`, doble escritura, invocación de resolver huérfano, reinicio del timestamp y aceptación de recibo errado. Restaurado código y repetida suite. Estas pruebas verifican la lógica reconstruida, no el módulo completo tras importar dependencias.
- **VERIFIED_BY_ME:** regresión exacta anterior de laboratorio reejecutada por separado en `cbs_final_phase07_sandbox`: **242/242 PASS** (4.84 s). No sumarla a una suite íntegra del repo ni afirmar CI verde. La rama de campaña recibe `test_dossier_jsonl_lock_phase11.py` y `test_dossier_observation_revision_phase11.py`, pruebas que sí importan el módulo productivo y deben ejecutarse en checkout completo. Ruff/mypy/Qt/Windows/CI/full pytest **NOT_EXECUTED**.
- **STATICALLY_INSPECTED:** `DossierWorkflow.bind_local` ya contrasta identidades, estado y `payload_fingerprint` entre recibo SUPRA y JSONL; `lecciones_previas` ya verifica autoridad del recibo de nuevo tras reiniciar. No deshacer esas defensas ni presentarlas como nuevas.

### Límites y decisión

- El lock no cubre escritores ajenos que editen JSONL sin usar el sidecar. En sistemas de archivos de red, o bajo interrupción de alimentación, la semántica de locks/`fsync` debe validarse aparte. El archivo `.dossiers.jsonl.lock` es una nueva entrada persistente; no borrarlo para “limpiar”. No existe `fsync` del directorio, transacción global SQLite+JSONL, verificador físico del proceso remoto, ni sistema de recuperación/restauración del fragmento parcial.
- `_leer_historial` omite líneas corruptas y conserva los bytes, pero aún falta un informe de integridad visible para operadores. No promocionar registros omitidos a recuentos de 0, PASSED, evidencias o recompensas.
- **F11-04 EVIDENCE_PENDING:** pertenencia candidato+run+problema entre `sessions`, `InterpreteStore`, dossiers y respuestas SUPRA; estado persistente tras crash/reintentos multi-run; callbacks `on_supra_vertical` todavía sin bloqueo de contexto equivalente; idempotencia multi-dossier; verificación Windows. Incluir expresamente en F12.
- CRIBA app no se ha ejecutado íntegra en este entorno, no hay inferencias ni cargos, no merge/push a main, sin cambios ASTRA/BLACKFORGE.

Comando en checkout íntegro desde `criba-blackforge`:

```sh
python -m pytest -q tests/unit/test_dossier_jsonl_lock_phase11.py tests/unit/test_dossier_observation_revision_phase11.py tests/unit/test_dossier_integrity.py tests/unit/test_invention_persistence.py tests/unit/test_invention_boundaries_phase10.py tests/unit/test_shadow_supra_restore_phase10.py tests/unit/test_shadow_supra_stale_callback_phase09.py
python -m compileall -q src/criba/supra_dossier.py
python -m ruff check src/criba/supra_dossier.py tests/unit/test_dossier_jsonl_lock_phase11.py tests/unit/test_dossier_observation_revision_phase11.py
python -m mypy src/criba/supra_dossier.py
git diff --check
```

## Siguiente acción exacta (histórica, al cierre de fase 11)

**Fase 12 — Recuperación cruzada SQLite↔JSONL y contexto del worker vertical.** Reconciliar `Storage.save_invention` y `InterpreteStore` con `candidate_id`, `run_id`, `query_hash` y recibo de dossier. Probar doble guardado con contenido distinto, cursor histórico, duplicados de IDs en múltiples ejecuciones, reinicio tras error en segundo dossier y recuperación de proyecto remoto con identidad correcta pero otro problema. Revisar `_on_supra_vertical_done/failed` contra sesión nueva y reintentos; usar tokens y guardas sin tocar SUPRA remoto. Ejecutar primero las regresiones completas F08–F11 si existe checkout real, corrigiendo fallos de integración documentados, con preferencia por pruebas de SQLite real. No tocar ASTRA, BLACKFORGE, G0 ni main; ninguna inferencia/acción externa de pago.

## Fase 12 — Identidad de candidatos entre runs y barrera de callbacks SUPRA vertical

Base: `6c6bb8a35985d4862e2454a2682924e1657ca93e`. Resultado: correcciones de trazabilidad y protección del GUI en fuente, con regresión aislada; **NO se declara integrado/verificado en PySide6 ni se cierra atomicidad SQLite↔JSONL**.

### F12-01 — Reconciliación del contrato run_id / candidate_id / problema

- **STATICALLY_INSPECTED / REFUTACIÓN:** `src/criba/inventar.py` crea `run_id = uuid.uuid4().hex` por corrida y **ya copia** ese valor a cada entry. No había pérdida sistemática de run_id en el productor vigente. El defecto residía en las rutas consumidoras: `supra_dossier.preparar_dossier` usa `entry.get("run_id","")` y las tres rutas de exportación no rechazaban explícitamente un entry legado, alterado o que perteneciese a otra sesión. `Storage.save_invention` escribe otra identidad de archivo (`invention-uuid`) y guarda query_hash; ni ese ID ni el hash prueban que el modelo fue auténtico.
- **FIX:** `src/criba/invention_lineage.py` introduce `bind_entry_to_sheet`. Comprueba query del sheet, candidate_id exacto, pertenencia por contenido a una única entrada del sheet, run_id explícito consistente, campos query/problema contradichos; devuelve copia profunda y copia el run_id canónico sin modificar la entrada. Legacy sin run_id permanece representable como **no acreditado**, sin fabricar identidad. `ui.actions.on_desarrollar_supra`, `_prepare_dossier_for_selected_idea` y `cli inventar --dossier` llaman a esa función ANTES de construir el dossier. La validación de F10, preparación completa y bloqueo de escrituras F11 se conservan.
- **FIX:** `verify_archived_invention` protege la activación de una sesión histórica: contrasta status=PROPUESTA, tipo del paquete, query exacta, sha256 almacenado, selected_index entero y válido (no bool), current_id frente a candidate_id/id/índice, estado interno, análisis de error, hipótesis/mecanismo y run_id cuando existe. `ui.dialogs.show_history` lo invoca tras `Storage.get` y antes de aceptar el diálogo, y comunica el rechazo; `Storage.get` sigue siendo lectura forense y no se borran ni corrigen bytes históricos. Es una comprobación de consistencia, NO firma ni verdad histórica.
- **VERIFIED_BY_EXECUTION:** archivo de la lógica pura exacto SHA Git `a46999768b1043dc458f9669e5b8eb1e15eeab58`, probado en sandbox Linux. `30/30 PASS`, incluida lectura desde archivo SQLite de pruebas tras reinicio y 15 mutaciones de campos corruptos parseables; 8/8 mutantes dirigidos detectados tras restauración. Test del checkout `tests/unit/test_invention_lineage_phase12.py` SHA `e33f4b55b4c63b2d7cfd5d977df2811eb92f1a8a` corresponde al test ejecutado salvo que importa por su ruta productiva `criba.invention_lineage`; esa ruta se probó también en sandbox.

### F12-02 — Worker vertical y respuestas tardías

- **STATICALLY_INSPECTED:** `on_supra_vertical` rechazaba una segunda pulsación durante el envío, pero conectaba `done/fail` exclusivamente con `win`. Ambos callbacks alteraban el GUI y el flag `_supra_vertical_running` sin identificar el proyecto, la sesión ni el candidato del trabajo original. F09/F10 ya protegían los callbacks de lote y restore, pero **NO** el slice vertical.
- **FIX:** `actions._supra_vertical_context_current` vincula token único, proyecto remoto esperado, objeto invent_sheet, paquete activo, problema, run_id, índice seleccionado y snapshot de contenido del candidato. Al cambiar contexto puede iniciarse explícitamente otro envío; los callbacks de la petición antigua no mutan la nueva. La señal terminal consume el token una sola vez; si `done` informa otro project_id, se muestra fallo y no éxito. Una operación de origen desconocido todavía activa no autoriza un segundo envío. Compatibilidad de firmas legacy preservada para llamadas directas sin contexto, **sin garantía de identidad para esas llamadas**.
- **VERIFIED_BY_EXECUTION, ISOLATED_SEAM:** guardas lógicas del módulo copiadas de la candidata y ejecutadas sin Qt/HTTP; 12/12 PASS (incluido mismo contenido en dos índices distintos, mismo run_id en otro objeto, mutación in-place, problema/paquete cambiados, señales repetidas). 8/8 mutaciones dirigidas detectadas, tras corregir un falso coverage inicial por candidatos distintos. El test que importa `criba.ui.actions` productivo `test_vertical_context_phase12.py` se ha creado, pero es **NOT_EXECUTED en un checkout Qt**. No confundir el fragmento aislado con un signal Qt entregado en el hilo real.
- **NO CAMBIO** en `_execute_supra_vertical`, DossierWorkflow, clientes HTTP ni SUPRA remoto. No se han ejecutado inferencias ni callbacks reales.

### Estado verificable y límites

- 42/42 pruebas locales dirigidas (30 módulo puro + 12 guardas extraídas) PASS; `python -m compileall` dirigido PASS. Dos pasadas de mutaciones separadas: 8/8 + 8/8 detectadas y restauradas. PySide6 no instalado. No existe clon completo en la sesión; `git ls-remote` falla por DNS. **NOT_EXECUTED:** pytest completo fases 08–12, interfaz Windows, Ruff, mypy, CI, integración real SQLite/JSONL/remote SUPRA. No reetiquetar 242 pruebas históricas de otra sesión como reejecutadas en F12.
- `DossierWorkflow.bind_local` ya conserva contrato de payload_fingerprint y recibo; `recover_latest` selecciona un proyecto remoto por orden, pero **no autentica pertenencia a la sesión actualmente visible**. La UI lo presenta como resultado PREVIO. Mantener ese alcance, sin presentarlo como resultado del candidato actual.
- **EVIDENCE_PENDING:** transacción atómica multi-dossier, recuperación de escrituras parciales, vinculación persistente entre archive-id SQLite y dossier-id JSONL (la creación de dossier no exige guardar antes en SQLite), aceptación Qt y consistencia cuando cambian versiones durante el replay. El nuevo control impide contradicciones observables, pero no proporciona identidad criptográfica del productor ni prueba causal.
- G0=NO_GO, P0_SEMANTIC=OPEN, SCIENTIFIC_ADVANTAGE=NOT_ESTABLISHED, ASTRA/BLACKFORGE/main/handoff sin cambios, sin despliegues ni gastos.

Comandos para checkout íntegro:

```sh
python -m pytest -q tests/unit/test_invention_lineage_phase12.py tests/unit/test_vertical_context_phase12.py tests/unit/test_invention_persistence.py tests/unit/test_shadow_supra_restore_phase10.py tests/unit/test_shadow_supra_stale_callback_phase09.py tests/unit/test_dossier_jsonl_lock_phase11.py tests/unit/test_dossier_observation_revision_phase11.py
python -m compileall -q src/criba/invention_lineage.py src/criba/ui/actions.py src/criba/ui/dialogs.py src/criba/cli.py
python -m ruff check src/criba/invention_lineage.py src/criba/ui/actions.py src/criba/ui/dialogs.py src/criba/cli.py tests/unit/test_invention_lineage_phase12.py tests/unit/test_vertical_context_phase12.py
git diff --check
```

## Siguiente acción exacta

**Fase 13 — Replay y recuperación de lotes tras fallo parcial.** Probar y diseñar la recuperación idempotente cuando el dossier 1 se escribe y el dossier 2 falla antes del envío; separar preparation/commit del lote respecto a resultados remotos UNKNOWN. Construir journal durable mínimo (sin borrar ni editar JSONL existente), reanudar sin duplicar efectos externos ante timeout/reinicio y registrar estado incierto como UNKNOWN, no 0 o PASS. Primero ejecutar pruebas productivas pendientes F08–F12 si se logra checkout completo y resolver regresiones causadas por nuevas precondiciones. Inspeccionar CLI/exportadores y ergonomía Windows sin activar proveedores. Mantener protección ASTRA, BLACKFORGE, main, G0 y datos privados.


## Fase 13 — Lotes de dossiers reanudables y write-ahead UNKNOWN

Baseline: `3a85e2dea7887e672ce10f5882e193c45e3220b6`. Cambio dirigido con journal local nuevo y cableado CLI/Shadow; no sustituye transacción SQLite↔JSONL, validación de Qt ni pruebas contra SUPRA real.

- **Defecto de partida / STATICALLY_INSPECTED:** CLI y Shadow guardaban el primer dossier antes de intentar el segundo. Si fallaba, quedaba un prefijo persistido sin manifest de lote; repetir Inventar regeneraba IDs aleatorios. En Shadow la reserva previa al POST tampoco tenía estado remoto durable por lote.
- **Corrección local:** `src/criba/dossier_batch.py` escribe `dossier_batches.jsonl` bajo el mismo bloqueo de `dossiers.jsonl`, `PREPARED` con payloads/identidad/fingerprint y `LOCAL_COMMITTED` tras guardar cada dossier, fsync en cada transición. Recuperar reusa dossier_ids originales y no duplica los ya guardados; `recuperar_lotes_pendientes()` no contacta ningún servicio. Un `run_id` válido más problema vincula el lote; misma ejecución con contenido distinto se rechaza, no sobrescribe. Legacy sin run_id puede archivarse localmente, pero no iniciarse automáticamente en SUPRA desde este camino.
- **Límite remoto:** Shadow registra `REMOTE_UNKNOWN` de forma durable **antes** de arrancar un worker. Si el registro ya existe o el lote llegó a `READBACK_OBSERVED`, la UI rechaza un segundo POST automático. Sólo se registra `REMOTE_READBACK_OBSERVED` después de obtener el conjunto completo de GETs y cotejar la identidad de dossier/proyecto/recibo y el `payload_fingerprint` del contenido contra el canon de `supra_client`. El marcador NO significa validación científica, ejecución física del mecanismo ni garantía de persistencia remota. Un fallo de red, disco, aplicación o readback conserva UNKNOWN y requiere reconciliación por GET antes de cualquier reenvío manual.
- **Evidencia ejecutada:** 20/20 pruebas locales dirigidas en Linux/Python con módulo nuevo real e interfaz `supra_dossier` sustituida por seam mínimo compatible, uso real de archivos/fsync/flock; primera corrida reveló fallo del bloqueo same-run/different-problem y fue reparado. Incluye reinicio, fallo en segunda escritura, concurrencia, replay, intent truncado, corrupción parseable, solicitudes duplicadas, readback de otro proyecto/recibo. `compileall` dirigido PASS. **NOT_EXECUTED** módulo de persistencia completo en checkout, Qt/PySide6, Ruff, mypy, CI, regresión del monorepo, tests contra SUPRA y Windows. Las 19 pruebas no equivalen a suite de producto ni certificación de atomicidad.
- **Límites conservados:** journal local no es firma/autenticación; JSONL+SQLite no es transacción distribuida; fallo físico de fsync/almacenamiento no modelado; cambios de esquema y migración todavía abiertos. La recuperación completa de proyectos externos es **EVIDENCE_PENDING**. No se ejecutaron inferencias, gastos ni despliegues. G0=NO_GO, P0_SEMANTIC=OPEN, main/handoff/ASTRA/BLACKFORGE intactos.

### Ejecutar en checkout integral

```sh
cd criba-blackforge
python -m pytest -q tests/unit/test_dossier_batch_phase13.py tests/unit/test_dossier_jsonl_lock_phase11.py tests/unit/test_invention_lineage_phase12.py tests/unit/test_vertical_context_phase12.py tests/unit/test_shadow_supra_export_boundary_phase10.py tests/integration/test_supra_client_contract.py
python -m compileall -q src/criba/dossier_batch.py src/criba/cli.py src/criba/ui/actions.py
python -m ruff check src/criba/dossier_batch.py src/criba/cli.py src/criba/ui/actions.py tests/unit/test_dossier_batch_phase13.py
git diff --check
```

## Siguiente acción exacta (tras fase 13)

**Fase 14 — Reconciliación remota y recuperación verificada tras reinicio.** Consultar por GET las identidades deterministas de proyectos de un batch UNKNOWN; verificar receipt, fingerprint, estado persistido y endpoint, sin mandar POST. No promover UNKNOWN a éxito ni reintentar automáticamente. Antes, ejecutar suite real de fase 13 y resolver incompatibilidades del wiring. Probar cierres, fallos tras POST, reinicios, cambios de endpoint y pruebas de falsas coberturas, sin tocar ASTRA, BLACKFORGE ni main.


### Fase 13 — reconciliación de pruebas históricas (compatibilidad pendiente de ejecutar)

- **STATICALLY_INSPECTED:** La prueba de callbacks Phase09 exigía dos workers al pulsar dos veces el MISMO sheet; ahora ese comportamiento es inseguro y se sustituye por una aserción de un solo worker y segundo intento bloqueado como UNKNOWN. La fixture usa directorio temporal real, no un fake guardar_dossier que ya no es la escritura productiva.
- **STATICALLY_INSPECTED:** test_gui_inventar.py interceptaba guardar_dossier, que el lote nuevo ya no invoca, y su fake de _execute_supra_dossiers no aceptaba batch_id. Se adapta para comprobar persistencia real mediante cargar_dossier y aceptar ese argumento sin ejecutar red.
- Estos cambios siguen **NOT_EXECUTED** en PySide6/Qt y checkout completo: son adaptación de expectativas e instrumentación, no nuevos PASS. El scheduler global y la integración visual requieren validación.


## Fase 14 — Reconciliación remota GET-only tras reinicio

Base: `eed004dd557f7afa9e6f84d045a637d380d8c6fb`; implementación incremental en la rama de campaña. No se modifican ASTRA, BLACKFORGE, main ni handoff.

- **F14-01 P1 / STATICALLY_INSPECTED:** el journal Phase13 aceptaba `REMOTE_READBACK_OBSERVED` por una etiqueta sin receipt persistido. Ahora los eventos nuevos incluyen identidad, endpoint, fingerprint y procedencia, y `_state` revalida la evidencia; las etiquetas legadas sin recibos permanecen UNKNOWN.
- **F14-02 P1 / STATICALLY_INSPECTED:** un tail truncado podía saltarse temporalmente y reaparecer como corrupción tras el siguiente append. La lectura nueva falla cerrada y preserva bytes; reparación manual pendiente, sin truncar el archivo ni tratar corrupción como PASS.
- **F14-03 P1 / STATICALLY_INSPECTED:** se registra el endpoint junto al intento remoto y se exige el mismo origen antes del worker y de los GET de recuperación. Historial remoto antiguo sin endpoint no obtiene acreditación retroactiva.
- **F14-04 / FIX:** `dossier_batch_recovery.reconciliar_lote_por_get` hace un GET por dossier esperado, sin POST ni retries. Valida proyecto, postura, stage, receipt scope, identidades, fingerprint, PERSISTED_STATE/VERIFIED_FROM_ARTIFACT, NOT_EXECUTED y NOT_VALIDATED. Si falla un GET o un guardado del journal, el lote sigue UNKNOWN.
- **F14-05 / FIX:** comando explícito desde `criba-blackforge`: `python -m criba.dossier_batch_recovery --batch-id ID --dry-run`. Sin `--dry-run` solo registra readback totalmente confirmado. No se activa automáticamente al abrir Shadow.
- **VERIFIED_BY_ME, ISOLATED_SEAM:** 19 tests unitarios de recuperación ejecutados en sandbox con journal/HTTP simulados, 19 PASS; inspección y compilación dirigida del módulo. **NOT_EXECUTED:** suite con código completo de SQLite/JSONL, PySide6 GUI, Ruff/mypy/CI, Windows, servicio SUPRA real e inferencias. Las pruebas fuente se publican para ejecución en checkout íntegro, no se atribuyen a CI.
- El servidor puede declarar persistencia sin prueba criptográfica externa: este contrato verifica coherencia de los datos observados, no identidad física del servidor ni validación científica. No hay atomicidad transaccional entre SQLite, JSONL y POST.

### Siguiente acción exacta: Fase 15

Ejecutar checkout integral en entorno con red/Git, corregir regressions de F08–F14, tests con MockTransport, proceso/restart, corrupción, migración, interfaz Qt y control de hash/ramas. Ninguna promoción a main ni aprobación G0. G0=NO_GO, P0_SEMANTIC=OPEN.

Comandos de validación (desde `criba-blackforge`):

```sh
python -m pytest -q tests/unit/test_dossier_batch_phase13.py tests/unit/test_dossier_batch_recovery_phase14.py tests/unit/test_shadow_supra_stale_callback_phase09.py tests/unit/test_gui_inventar.py
python -m compileall -q src/criba/dossier_batch.py src/criba/dossier_batch_recovery.py src/criba/ui/actions.py
python -m ruff check src/criba/dossier_batch.py src/criba/dossier_batch_recovery.py tests/unit/test_dossier_batch_phase13.py tests/unit/test_dossier_batch_recovery_phase14.py
git diff --check
```


## Fase 15 — Reconciliación de regresión GUI y pruebas de integración

- REPRODUCED_BY_ME en ejecución Python mínima: la fixture `fake_execute` antigua fallaba con TypeError ante `expected_endpoint`, agregado en F14. Se acepta/verifica el keyword y se fija `SUPRA_ENDPOINT` en el test para que sea determinista.
- EVIDENCE_PENDING: prueba GUI Qt (PySide6 no instalado en sandbox), suite de producto y Windows. No promover a PASS por inspección.
- Política CI real: workflow `ci.yml` se ejecuta por PR, push en main o manual; los pushes a campaña no lo activan por defecto.


### F15 — Integración real de los ficheros locales (8 casos nuevos)

- Suite nueva: `tests/unit/test_dossier_batch_phase15_integration.py`. Usa `guardar_lote_dossiers`, `_events`, `_state`, `_leer_historial`, bloqueo de procesos y append/fsync reales. Solo sustituye la red SUPRA por respuestas GET deterministas; no ejecuta POST.
- Cobertura: readback verificado tras reabrir journal, replay sin IDs nuevos, GET parcial, endpoint cambiado, dossier alterado, recibo alterado después del commit, fallo de escritura del marcador, legacy sin recibo y borrado del historial local.
- **NOT_EXECUTED:** estos 8 casos en el checkout integral: no se certifica PASS. El sandbox F14 reejecutado 38/38 PASS y compileall PASS, pero usa journal simulado. Este cierre no permite elevar G0 ni cerrar el P0 semántico.
- Punto siguiente: ejecutar los 8 casos junto con las suites F13/F14/GUI en Windows y CI de PR; refutar y corregir fallos, sin mezclar en main.


## Fase 16 — Contratos de readback y migración conservadora

- Base: `9fba726d7b4bd0236892030db12d40938acbed0c`. Mantener la rama `campaign/cbs-final-32-40` y no tocar `main`.
- **P1 / STATICALLY_INSPECTED:** `marcar_envio_incierto` permitía guardar un intento remoto nuevo sin endpoint; la recuperación F14 no podía acreditar su origen. Ahora el endpoint se exige para toda reserva nueva. Los eventos legacy sin origen siguen legibles sin inventarles origen.
- **P1 / STATICALLY_INSPECTED:** la función de confirmación productiva `marcar_readback_observado` comprobaba receipt e identidad, pero no `read.scientific_status`, `read.criba_mechanism_execution_status` ni `read.criba_planning_receipt_status`. La recuperación F14 sí comprobaba los tres: el productor Shadow y la recuperación divergían. Se añade validación y persistencia de los tres canales; contradicciones no se promocionan.
- **Versionado y migración:** nuevo evento `REMOTE_READBACK_OBSERVED` lleva `evidence_version=criba-batch-readback/2`. Eventos anteriores sin versión se conservan como `UNKNOWN` para reconciliación GET-only explícita. No se borran ni editan.
- Tests añadidos F16: endpoint nulo, tres mutaciones de canales superiores, marcador antiguo y adulteración del evento v2. Adaptadas fixtures F13 y F15. Test de readback real y GUI/CI requieren checkout completo.
- **NOT_EXECUTED:** nuevo conjunto de pruebas F16 contra el código exacto (contenedor sin acceso GitHub por DNS y sin PySide6). No elevar G0 ni P0 semántico, y no declarar fase 16 aceptada antes de suite y verificación.


### F16 re-scan adversarial: evitar falsa cobertura

- La primera suite F16 inyectaba los tres estados contradictorios solo a través del recuperador GET, que ya los filtraba en F14; una mutación que eliminase la validación del escritor directo de Shadow podría seguir pasando. Se añaden tres sentinels dirigidos a `marcar_readback_observado` con status falsificado y GET separado, más versión de evidencia desconocida que debe fallar cerrada.
- Quedan diez casos F16 en total (incluidos parametrizados). **NOT_EXECUTED** con checkout íntegro; no se promocionan por el número de casos.


## Fase 17 — Protocolo operativo: invalidación de callbacks asíncronos

- **STATICALLY_INSPECTED P1:** `on_protocolo_operativo` ligaba done/fail al `sheet` original sin comprobar `invent_sheet` al devolver el worker; `_on_protocolo_done` reasignaba el sheet antiguo a la ventana. Un callback retrasado puede borrar la sesión nueva. Un fail retrasado puede reactivar controles o mostrar error incorrecto. 
- **FIX:** request intent no persistido en ventana, con identidad de sheet, run, query, problem, índice y copia del entry. Callback consume solo su solicitud actual; si cambió sesión, propuesta u objetivo no altera datos y libera el botón únicamente cuando pertenece a la solicitud vigente. Duplicación del mismo request no lanza otro proveedor.
- **TESTS:** `tests/unit/test_shadow_protocol_stale_phase17.py`: nueva sesión, run, query, problema, mutación del entry, cambio de selección/orden, señales dobles, fallo viejo y llamadas duplicadas. Worker simulado: no implica ninguna inferencia ni modelo real.
- **EVIDENCE_PENDING:** suite Qt completa y Windows, CI remoto y comprobación de interacciones con estado de navegación. `main` y ASTRA no modificados.

### F17 re-scan — cambio de selección sin cambio de sesión

- **FALSE_COVERAGE evitada:** igualdad de sheet, run y entry no acredita que continúe seleccionada la misma tarjeta; un callback válido en contenido podía forzar la navegación al índice antiguo. Se vincula `interpretation_index` de la selección original. Al cambiar de tarjeta, el resultado obsoleto es descartado, incluso si el mismo `sheet` continúa en memoria.
- Dos pruebas nuevas: cambio de selección durante la solicitud, y una segunda solicitud de otra selección que anula la primera sin deshabilitar los controles de la nueva.

### F17 mutación adicional — objeto reemplazado con mismos campos

- Una sustitución del objeto `entries[index]` por `dict(old)` puede conservar igualdad de contenido y seguir representando una nueva revisión de sesión. Se comprueba además `is entry_ref` y se permite una nueva solicitud en ese caso. Test dirigido añadió escenario de dos workers en secuencia, done antiguo descartado y fail vigente respetado.

### F17 contrato de configuración del intérprete

- El worker preserva backend/model al crear la solicitud, pero el sheet activo puede cambiar su configuración durante la inferencia. La nueva identidad de solicitud incluye una copia profunda de `sheet.interpreter` y la invalida si se modifica el backend o modelo. Evita atribuir a la configuración actual un protocolo generado con otra.
- Tres casos dirigidos adicionales: mutación de backend, mutación de modelo y segunda solicitud que reemplaza a la primera.


### F17 headless AST real-body sentinels

- Se añaden pruebas sin dependencia PySide6 que cargan y ejecutan **los cuerpos reales** de cuatro funciones del checkout (`_entry_para_desarrollo`, `_protocolo_intent_actual`, `_finalizar_protocolo_worker`, `on_protocolo_operativo`) mediante Python AST. Sustituyen solo la ejecución Qt/Worker/proveedor y el render final. Casos: dedup, señal terminal única, cambio de sheet, cambio de identidad de entry aunque tenga igual contenido, cambio de modelo, cambio de tarjeta y mutaciones de run/query/mecanismo/objetivo.
- Estas pruebas son más fuertes que una reimplementación falsa de las guardas; su alcance sigue limitado: no prueban el ciclo real de Qt ni toda la integración.
- **NOT_EXECUTED** contra checkout completo en este entorno. Sin CI automática en rama de campaña.


## Fase 18 — Cancelación cooperativa del refinamiento sin cancelación ficticia de HTTP

- Base `a638fda67450c58dd8d1d6aa487935d0f4ad8745`. Se detectó que el worker capturaba la referencia viva de `entry` y podía preparar inferencia sobre contenido cambiado después del clic, pese a descartar el callback. Se pasa `deepcopy(intent["entry"])` a `refinar_propuesta`.
- Cada intent lleva `threading.Event`; una nueva solicitud cancela la anterior antes de construir intérprete o entrar en `refinar_propuesta`. Nuevo contexto invoca la misma invalidación en `_apply_new_problem`, `_on_invented`, `on_inventar` y `on_historial`. Sin lectura Qt desde el worker.
- Idempotencia de doble clic: no se cancela la solicitud vigente si el intento repetido es semántica e identitariamente el mismo.
- Límite explícito: **si `completar_json` ya comenzó, Event no interrumpe la llamada remota ni garantiza ahorro de tokens/coste**. Solo se descarta su señal final; no se afirma cancelación de red ni suspensión de thread.
- Añadida `tests/unit/test_shadow_protocol_cancellation_phase18.py` con nueve pruebas AST de cuerpos reales y simulado del límite de proveedor: dedup, queued skip, cancel después de construir intérprete, entrada y modelo original, proveedor iniciado, idempotencia y wiring de cuatro rutas. Pruebas GUI Qt y suit completa: **NOT_EXECUTED**.
- Estado: `IMPLEMENTED / EVIDENCE_PENDING` hasta test de checkout completo y validación Windows. G0 y P0 semántico no se elevan.

### F18 reconciliación retrocompatibilidad de pruebas F17

- **P1 / STATICALLY_INSPECTED / corrected:** `test_shadow_protocol_headless_phase17.py` compila en un namespace AST el cuerpo de `on_protocolo_operativo`; F18 introdujo una llamada global a `_cancelar_protocolo_pendiente` y `Event` que no se importaban en esa suite. Sin parche, las regresiones históricas sufrirían `NameError` (FALSE_COVERAGE del conjunto F18). El harness ahora extrae la función real y suministra `threading.Event`; test adicional verifica invalidación de la solicitud previa por el cuerpo real.
- **NOT_EXECUTED:** checkout integral de F17/F18 aún pendiente. La reparación conserva el contrato del harness, sin introducir sustitutos de la función productiva.

### F18 re-scan de cancelación durante copia de payload y token cancelado

- Se añadió un tercer control `Event.is_set()` **después** de construir el payload independiente y **antes** de llamar a `refinar_propuesta`. Evita iniciar gasto en un proveedor cuando la cancelación se activa durante una copia lenta de la propuesta.
- Se añadió el rechazo de `intent.cancel` en `_protocolo_intent_actual`, aun si el puntero a la solicitud no ha sido limpiado; una señal terminal de ese intent no puede publicar resultados.
- Dos pruebas adversariales nuevas en F18. El conjunto es 11 casos F18. **VERIFIED_BY_ME**: smoke espejo de cinco funciones productivas en sandbox local: 9/9 PASS y py_compile PASS, pero los bytes del checkout completo no son accesibles en contenedor; **NOT_EXECUTED**: suite F18 oficial, Qt, CI y tests globales.

## Fase 19 — Recuperación duradera, concurrencia GET y estados históricos

- Base: 176ad416be307ef606a955ad1a94f2d8f5a664df; main, handoff y ASTRA sin modificaciones.
- P1 / STATICALLY_INSPECTED: una segunda consulta GET fallida podía degradar la salida a UNKNOWN aunque el journal v2 verificable seguía marcando READBACK_OBSERVED. Se separa el estado histórico del estado fresco: reason=PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED, fresh_get_status=<causa real>.
- P1 / STATICALLY_INSPECTED: dos recuperadores GET simultáneos podían fsync el mismo resultado y reportar al segundo JOURNAL_COMMIT_UNCONFIRMED. Tras una colisión de escritura se relee el journal bajo lock y solo se acepta una confirmación v2 idéntica, con comprobación de dossier, fingerprint y endpoint.
- P1 / CLI: recibir status=READBACK_OBSERVED con fresh_get_status=GET_FAILED ya NO devuelve exit code 0. La automatización requiere GET fresco validado (exit 0), o código 2 cuando la confirmación es únicamente histórica.
- P2 / TOCTOU: para batches ya confirmados se revalida el journal y el historial local al concluir GET, evitando confirmación basada en una lectura anterior a una modificación concurrente.
- Se conservan journal bytes, no se repite POST y nunca se promociona UNKNOWN ni evidencia científica ausente.
- Tests F19: 10 escenarios reales de journal/lock/ficheros, más 4 escenarios parametrizados de salida CLI. Solo se simula GET/cliente CLI. NOT_EXECUTED: suite oficial contra checkout completo y CI Windows.
- Estado: IMPLEMENTED / EVIDENCE_PENDING. G0=NO-GO; P0 semántico=OPEN.

### F19 re-scan: reinicio real de proceso

- Dos sentinels adicionales ejecutan sys.executable en subprocess independiente: un journal v2 fsynced se reabre como READBACK_OBSERVED sin reenvíos ni alteración de bytes, y otro journal con JSONL truncado falla cerrado en el nuevo proceso, preservando el tail corrupto.
- La suite F19 consta de 13 funciones y 16 casos expandidos (incluidos 4 CLI parametrizados). La ejecución íntegra real continúa NOT_EXECUTED; no confundir pruebas publicadas con pruebas ejecutadas.


## Fase 20 — Shadow: recuperación del lote exacto y estados epistemológicos

- Base: `d7deaeb0ddf26453edf4aa12b9e35deff593d84b`. Rama única `campaign/cbs-final-32-40`; no main/ASTRA/handoff.
- **P1 / STATICALLY_INSPECTED:** la recuperación previa `_load_latest_supra` usa LIST/GET del último proyecto, no el `dossier_batch_id` UNKNOWN del sheet. Un segundo clic en «Desarrollar con SUPRA» solo devolvía aviso, sin GET del lote correcto. Ahora se habilita acción explícita GET-only para lotes UNKNOWN/READBACK_OBSERVED, preservando el bloqueo de una segunda invocación mientras el POST original esté activo.
- **P1 / STATICALLY_INSPECTED:** `_on_supra_dossiers_done` presentaba «workflow completado» con solo un diccionario `read`, sin exigir escritura local v2. El worker productivo emite `journal_recorded` únicamente tras `marcar_readback_observado`; la UI exige acuse del mismo batch e identidades de dossiers y recibos GET estructurados. Sin acuse, muestra journal SIN RECIBO verificable y no promociona `supra_runs`.
- **Contrato de presentación, sin PySide6:** `ui/supra_batch_status.py` clasifica `FRESH_JOURNALED`, `FRESH_NOT_JOURNALED`, `HISTORICAL_ONLY`, `UNKNOWN`. Los tres estados sólo describen recibos de planificación, jamás mecanismo ejecutado ni validación científica. Campos ausentes, tipos bool en contadores, contadores parciales, marcadores contradictorios y estado no conocido fallan a UNKNOWN.
- **Callbacks:** identidad de token, `sheet is`, `run_id`, `batch_id` y `problem`. Duplicados GET bloqueados mientras corre la misma solicitud; abandonar sesión o recuperar el último proyecto invalida el GET antiguo. Nunca se invoca POST en reconciliación.
- **Tests:** 24 casos de proyección headless reproducidos localmente (24/24 PASS, Python 3.13), más 11 pruebas de cableado Qt publicadas (no ejecutadas por falta de PySide6). Fases 09 y GUI Inventar actualizadas para no exigir falsos resultados de un worker simulado sin journal.
- **EVIDENCE_PENDING:** tests oficiales contra checkout real, Qt Windows, suite completa, Ruff, mypy, CI. G0 NO-GO y P0 semántico OPEN.

### F20 re-scan — identidad del lote tras restauración

- El botón de recuperación consulta ahora un `dossier_batch_id` previamente reservado **antes de validar propuestas actuales**. El replay no depende de que una sesión antigua siga teniendo entradas interpretables; el journal local es la única autoridad de lo que se envió.
- `reconciliar_lote_por_get` acepta precondiciones opcionales `expected_run_id` / `expected_problem`. La ruta Shadow las exige y las coteja con el `PREPARED` duradero bajo lock, antes de abrir GET; un batch_id de otra sesión retorna `INTENT_LINEAGE_MISMATCH` y no toca remoto ni journal.
- Cuatro casos GET lineage con JSONL real y cuatro casos Qt adicionales de ficha sin propuestas, dedup, run_id ausente y cambio de query durante GET. **NOT_EXECUTED** contra checkout completo; no se interpreta la publicación de pruebas como PASS.

### F20 re-scan adversarial — contadores y procedencia contradictorios

- **FALSE_COVERAGE:** el primer presentador aceptaba `reason=PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED` junto a `fresh_get_status=VERIFIED_FROM_ARTIFACT` y contadores completos. Ahora la ruta fresca exige razones exactas `PERSISTED_PLANNING_RECEIPTS_ONLY` / `JOURNAL_CONFIRMED_CONCURRENTLY`, con acuse local obligatorio para la segunda.
- El caso histórico exige `checked < expected`; la primera fixture de prueba histórica usaba 2/2 GET y a la vez GET_FAILED, un estado inalcanzable. Se ajustó a 0/2 o 1/2 y se añaden mutaciones que deben devolver UNKNOWN.
- **VERIFIED_BY_ME:** el archivo de presentación original publicado tenía SHA Git idéntico al archivo probado en contenedor; tras las nuevas mutaciones la ejecución local del mismo código actualizó a 29/29 PASS. El checkout completo/UI Qt continúa NOT_EXECUTED.

## Fase 21 — Reconciliación de contratos 15–20 y pruebas contra falsa cobertura

- BASE: 235f58d75652f9aee0a7b8b9e6669b3b84072f9d. Alcance: recuperación GET local, proyección Shadow y guardas de callbacks. No cambiar ASTRA, main ni handoff.
- P1 VERIFIED_BY_ME: el presentador Shadow aceptaba datos contradictorios scientific_status=VALIDATED y mechanism_execution=COMPLETED junto a metadatos aparentemente correctos, devolviendo FRESH_JOURNALED. Se reprodujo con el archivo exacto en Python. Se exige scientific_status=NOT_VALIDATED y mechanism_execution=NOT_EXECUTED; faltantes y falsificaciones son UNKNOWN.
- P1 STATICALLY_INSPECTED: reconciliar_lote_por_get en modo registrar=False y estado UNKNOWN omitia relectura de journal/dossier tras finalizar GET. Se incorporó _local_batch_still_intact bajo lock para UNKNOWN dry-run y verificación v2 histórica estricta. Cinco pruebas de ficheros reales: mutación local, tail truncado, marcador duplicado, dry-run correcto y journal confirmado previo.
- P1 STATICALLY_INSPECTED: el callback de worker SUPRA interpretaba un bool journal_recorded=True junto a IDs coincidentes como suficiente para presentar recibo GET registrado. Se aisló la guarda submitted_batch_receipt_valid: verifica filas completas, identidad, provenance PERSISTED_STATE, artefacto VERIFIED_FROM_ARTIFACT, planning receipt y estados NO EJECUTADO/NO VALIDADO. Usa forma tipada de candidate_id y claim_id y tres SHA-256; no afirma probar el contenido de hashes. El validador de journal sigue siendo la autoridad duradera.
- FALSE_COVERAGE: el doble de F09 inventaba un acuse sin receipt completo. Se actualizó a un registro estructuralmente coherente y se añadieron mutaciones para evitar elevar falsos estados; los tests Qt siguen sin ejecutar.
- P6/P7: ocho pruebas adicionales cruzan la respuesta REAL del journal y reconciliador con el presentador real usando solo GET simulado: nuevo, dry-run, histórico offline, UNKNOWN, linaje incorrecto, artefacto no verificado, lectura parcial y carrera entre escritores.
- VERIFIED_BY_ME: 87/87 PASS headless en Python local sobre copia exacta del blob criba-blackforge/src/criba/ui/supra_batch_status.py con SHA Git 15e791f4d41be230b6b90f61b624b5a6e75e7592. py_compile PASS; no se trata de suite total ni de HTTP SUPRA real.
- NOT_EXECUTED: tests nuevos de journal sobre checkout completo, PySide6/GUI, Ruff, mypy, suite íntegra y CI remoto para el HEAD de campaña; todas las afirmaciones de integración plena siguen EVIDENCE_PENDING.
- RESEARCH_QUESTION para F22: la ficha Inventar archivada puede no conservar los nuevos campos dossier_batch_id/dossier_remote_state después de desarrollar; revisar persistencia tras cambios y recuperación directa desde PREPARED, sin asumir continuidad GUI tras reinicio.
- NO-GO: G0 NO-GO, P0 semántico OPEN; estados UNKNOWN no se elevan a evidencia ejecutada. No auto POST, merge, desplegar ni modificar el motor ASTRA.
