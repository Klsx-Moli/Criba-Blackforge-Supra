# Auditoría Semántica de Autorización: PR8 vs PR11

- BASE: PR8 head 65a58e5 (worktree iso-pr8-safety); PR11 head 3244879 (worktree iso-dossier)
- TARGET_MAIN: 15bc237
- TIMESTAMP_UTC: 2026-10-08
- AUTOR: Hermes (writer; inspección de diffs reales, no ejecución de suite)

## 1. Qué representa la autorización en PR8

Módulo: `criba-blackforge/src/criba/blackforge_safety.py` (función pura, SIN I/O).

- Tipos: `AuthorizationState(str, Enum)` = PENDING / GRANTED / DENIED / EXPIRED.
- Función: `evaluate_blackforge_safety(item, session_context, clock, session_id) -> SafetyDecision`.
- Decisiones: ALLOW_CONCEPTUAL / ALLOW_DEFENSIVE_DESIGN / ALLOW_LOCAL_NON_DESTRUCTIVE /
  REQUIRE_SANDBOX / REQUIRE_HUMAN_APPROVAL / DENY.
- Fail-closed: clase de seguridad desconocida -> DENY; prohibiciones duras -> DENY;
  estado de autorización DENIED/EXPIRED con authorization_required -> DENY; estado
  inválido (ValueError al parsear) -> DENY por defecto.
- Defaults: `authorization_state` por defecto PENDING; si no se requiere autorización,
  el estado no bloquea (solo S2/S3 lo exigen).
- Invalidaciones: `requires_explicit_authorization=True` o safety_class S2/S3 fuerzan
  authorization_required; aprobar lo secundario no reactiva DENIED/EXPIRED.
- Persistencia: NINGUNA. `SafetyDecision` es dataclass en memoria; no hay storage.
- Integración con flujo: es un GATE previo a cualquier hook de materialización/simulación/
  ataque. No conoce nonce, broker ni execution.

## 2. Qué representa la autorización en PR11

Módulos: `blackforge_case.py` (DefensiveCase + Authorization + AuthorizationAxis),
`blackforge_broker.py` (reserve/dispatch con SQLite journal),
`blackforge_slice_authz.py` (modelo declarativo de permisos, sin ejecución).

- DefensiveCase.authorization: `AuthorizationAxis` = NONE / GRANTED / EXPIRED / REVOKED /
  DENIED / CONSUMED.
- Authorization (dataclass): subject, credential_ref, approved_plan_digest (sha256),
  approved_intent, case_id, nonce (single-use), max_duration_s, valid_from, limits,
  approved_actions, resolved_targets, state.
- Estados de validación en `authorization_is_live` (fail-closed):
  - record ausente -> no live;
  - nonce revocado -> no live (revocation chequeada ANTES del eje, causa precisa);
  - eje != GRANTED -> no live;
  - boot_epoch distinto -> no live (reinicio invalida);
  - now < valid_from -> no live;
  - (now - valid_from) > max_duration_s -> EXPIRED, no live.
- Validadores: `attach_authorization` exige plan_digest coincidente, boot_epoch actual,
  nonce no revocado, case_id/revision coincidentes.
- Persistencia: SÍ. Broker SQLite (`grants`, `attempts`, `consumptions`) con
  BEGIN IMMEDIATE; reserve consume el nonce en la misma tx; journal fsync antes de dispatch.
- Punto exacto de bloqueo: `broker.reserve` requiere grant en GRANTED, nonce no consumido,
  no expirado, acciones en lista, plan_digest coincidente -> si no, AuthorizationError
  "cero despachos". `require_authorized` en el case también falla cerrado.
- Slice authz (`blackforge_slice_authz.py`): modelo DECLARATIVO de permisos (grants/denies/
  inherits/revokes/requires_role) sobre un snapshot exportado; NO ejecuta nada, NO consulta
  sistema real; concluye DIRECT/INHERITED/ABSENT/INDETERMINATE. Es análisis, no autorización
  ejecutiva.

## 3. Matriz de casos

| Caso | PR8 (safety gate) | PR11 (broker/case) | Conflicto | Severidad | Recomendación |
|------|-------------------|---------------------|-----------|-----------|---------------|
| Autorización ausente | Si S2/S3 requerido -> DENY; si S0/S1 -> ALLOW según clase | require_authorized -> CaseError "no hay autorizacion registrada"; reserve -> AuthorizationError | Sin conflicto: PR8 es pre-gate por clase; PR11 es ejecutivo por nonce | BAJA | Documentar frontera: PR8 filtra items, PR11 autoriza ejecución de caso |
| Autorización expirada | authorization_state=EXPIRED + required -> DENY | authorization_is_live: (now-start)>max_duration_s -> EXPIRED, no live | Semántica coincidente (fail-closed) pero modelos distintos (enum vs TTL) | BAJA | Unificar vocabulario en documento de frontera; no duplicar lógica |
| Autorización denegada | DENIED + required -> DENY | REVOKED/DENIED eje -> no live | Coincidente | BAJA | — |
| Autorización inválida/corrupta | ValueError al parsear estado -> DENY por defecto | attach_authorization: campos vacíos/sha256 malo -> CaseError | PR8 falla cerrado en parseo; PR11 falla cerrado en validación de campos | BAJA | — |
| Autorización válida | S0/S1 -> ALLOW; S2/S3 con ctx completo -> REQUIRE_* | GRANTED + nonce vivo + acciones ok -> reserve OK | Sin conflicto | BAJA | — |
| Autorización desconocida | clase desconocida -> DENY | vocabulario cerrado de verbs; fuera -> SnapshotError (solo slice) | Distinto ámbito (slice vs gate) | BAJA | — |
| Datos parciales | ctx parcial -> faltan requisitos -> DENY con unmet_requirements | snapshot completeness != COMPLETE -> INDETERMINATE (no infiere grant) | Coincidente en espíritu (no inferir de datos parciales) | BAJA | — |
| Persistencia previa incompatible | N/A (PR8 no persiste) | broker SQLite con schema propio; grants consumidos son inmutables | Sin colisión: PR8 no escribe; PR11 escribe en sus tablas | BAJA | — |
| Replay/reintento | N/A | nonce single-use: reintento con mismo nonce -> "ya se consumió", cero despachos | PR11 previene replay por diseño | BAJA | — |
| Ejecución broker sin autorización explícita | PR8 no llega a broker si DENY | mark_reserved exige GRANTED; si no, CaseError "cero despachos" | Sin conflicto: ambos fallan cerrado | BAJA | — |

## 4. Doble fuente / duplicación

- Doble fuente de verdad: NO. PR8 opera sobre `safety_class` + `session_context`;
  PR11 sobre `Authorization` (nonce/credential/plan). Dominios distintos.
- Doble enum/estado: SÍ, pero distinto propósito. PR8 `AuthorizationState`
  (PENDING/GRANTED/DENIED/EXPIRED) es un sello de entrada al gate; PR11
  `AuthorizationAxis` (NONE/GRANTED/EXPIRED/REVOKED/DENIED/CONSUMED) es ciclo de
  ejecución con nonce. Riesgo de CONFUSIÓN terminológica, no de divergencia lógica.
- Doble serialización: NO (PR8 no serializa; PR11 serializa Authorization en broker).
- Doble validación: PR8 valida por clase de seguridad; PR11 valida por nonce/TTL/plan.
  Ambas fail-closed; no se anulan.
- Responsabilidades mal separadas: NO detectadas. PR8 es pre-ejecución; PR11 es
  ejecución. El slice authz es análisis declarativo aislado.
- Huecos: ninguno donde uno permita y otro no decida. PR8 DENY bloquea antes; PR11
  DENIED/EXPIRED/revocado bloquea en reserve.
- Lógica duplicada susceptible de divergir: el concepto "autorización expirada/denegada
  => denegar" aparece en ambos; si algún día se cambia el significado de EXPIRED en uno,
  el otro no lo sabe. Bajo riesgo mientras estén documentados.

## 5. Clasificación final

COMPLEMENTARY_WITH_BOUNDARY

PR8 y PR11 son complementarios: PR8 filtra por clase de seguridad antes de cualquier
ejecución; PR11 autoriza la ejecución de un caso con nonce único, TTL y broker durable.
Comparten la palabra "autorización" pero no la fuente de verdad. La frontera debe
documentarse en un contrato canónico de autorización (CBS-K1) para evitar divergencia
terminológica futura. No son duplicados ni contradictorios.

## UNVERIFIED
- Tests de PR8/PR11 citados como REPORTED_BY_PR (no ejecutados en esta sesión).
- No se verificó que PR8 y PR11 se invoquen en el mismo flujo de producción real
  (HARD_PAUSE; ninguno ejecuta BLACKFORGE en vivo).
- Semántica de `blackforge_pipeline.run_headless` (usado por PR9) no inspeccionada aquí.
