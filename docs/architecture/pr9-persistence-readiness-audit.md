# Auditoría de Preparación de Persistencia: PR9

- BASE: PR9 head 1a98b7e (worktree iso-pr9-persistence)
- TARGET_MAIN: 15bc237
- TIMESTAMP_UTC: 2026-10-08
- AUTOR: Hermes (writer; inspección de diffs reales)

## 1. Qué se persiste exactamente

Módulo `criba-blackforge/src/criba/storage.py` (Storage sobre SQLite, WAL):

- Tabla `sessions`: id, created_at, query_hash, query, current_id, status,
  config_json, packet_json, evidence_json (DEFAULT '[]').
- Tabla `decisions`: id, session_id, created_at, status, evidence_json, note.
- Tablas chain_*: chain_sessions, chain_memory, chain_outputs, chain_reviews.
- Tabla `lottery_used_combinations`: (catalog_fingerprint, combo_key) PK.
- Audit events BLACKFORGE: `record_event` añade a `evidence_json` de la sesión
  entradas {mitigation_proposed, mitigation_applied} (append-only).
- `blackforge_agentic.py`: `save_blackforge_session` persiste el packet completo;
  `apply_approved_mitigation` registra evento antes de mutar estado local.

## 2. Formatos / esquemas

- SQLite con `user_version` (SCHEMA_VERSION = 1).
- JSON embebido en columnas *_json (config, packet, evidence).
- `evidence_json` siempre lista (validado al leer: si no es lista -> ValueError).
- combo_key codificado con `_encode_combo_key` (sorted:: o JSON canónico) y
  decodificado tolerante a legacy (`_decode_combo_key`).

## 3. Versionado de schema

- SÍ presente: `initialize()` lee `PRAGMA user_version`; si > SCHEMA_VERSION -> RuntimeError
  (base más nueva no soportada). Si < SCHEMA_VERSION -> setea user_version=1.
- Limitación: la migración solo sube el número; NO altera columnas existentes ni
  reconstruye datos. No hay ALTER/MIGRATE de columnas.

## 4. Datos legacy o ausentes

- Legacy (pre-SCHEMA_VERSION=1): no hay evidencia de un esquema anterior en el diff;
  el único chequeo es user_version. Si existiera una BD con tabla `sessions` sin
  columna `evidence_json`, `initialize` NO la añade (CREATE TABLE IF NOT EXISTS no
  agrega columnas). RIESGO: compatibilidad legacy de columnas no verificada.
- Ausentes: `save_blackforge_session` exige session_id/timestamp/status no vacíos y
  coincidentes con el packet; si no, ValueError explícito (no silencioso).

## 5. Cobertura de tests (REPORTED_BY_PR, no ejecutados aquí)

Según diff de PR9:
- test_blackforge_agentic.py (+106): propuesta/aplicación de mitigación.
- test_blackforge_pipeline.py (+23): integration.
- test_storage_decision_evidence.py (+113): eventos de decisión/evidencia.
- Commit messages citan: "prove durable agentic audit trail", "prove BLACKFORGE event
  atomicity", "concurrent audit append integrity", "reject fabricated history sessions",
  "bind BLACKFORGE packet to session identity", "serialize BLACKFORGE audit appends".

Cobertura aparente por contrato:
- guardar: SÍ (save_blackforge_session / save).
- recargar: SÍ (get / list_sessions).
- round-trip: SÍ aparente (get rehidrata JSON); NO ejecutado aquí.
- corrupción: PARCIAL (row inexistente -> ValueError; evidence_json no-lista -> ValueError).
- defaults: PARCIAL (evidence_json DEFAULT '[]').
- idempotencia: SÍ en chain_review (INSERT OR IGNORE) y chain_memory (dedup).
- duplicados: SÍ en lottery (PK + INSERT OR IGNORE).
- reinicio de proceso: NO verificado aquí (WAL + user_version; requiere test de crash).

## 6. Módulos que toca y colisión

- Toca: blackforge_agentic.py, storage.py, blackforge_pipeline.py (+tests).
- PR11 broker tiene SU PROPIO SQLite (grants/attempts/consumptions) en blackforge_broker.py;
  NO comparte tablas con storage.py de PR9. Sin colisión de esquema.
- PR10 intelligence/storage/store.py es MÓDULO DISTINTO (intelligence, no blackforge);
  confirmado en Fase A (diff PR10 no toca storage.py/blackforge_* de PR9). Sin colisión.

## 7. Dependencia implícita de PR11

- PR9 NO depende de contratos de PR11. Usa `evaluate_blackforge_safety` (PR8) vía
  blackforge_agentic.apply_approved_mitigation, no el broker de PR11.
- El "AuthorizationState" de PR8 es independiente del "AuthorizationAxis" de PR11.
- Conclusión: PR9 es integrable sin PR11.

## Clasificación final

READY_AFTER_TESTS_ONLY

Razón: schema versionado presente, round-trip y corrupción cubiertos por tests
reportados, sin colisión con PR8/PR11. Pero:
- compatibilidad legacy de columnas (BD preexistente sin evidence_json) no verificada;
- reinicio de proceso / durabilidad ante crash no ejecutada aquí;
- conteos de tests no reproducidos.
Por tanto integrable pronto, pero solo tras correr la suite de PR9 en worktree aislado
sobre main (verificación requerida en CBS-K6).

## UNVERIFIED
- Tests no ejecutados en esta sesión (NOT_RUN).
- Existencia de BD legacy real con esquema previo: desconocida.
- Durabilidad ante crash / corrupción de WAL: no probada aquí.
