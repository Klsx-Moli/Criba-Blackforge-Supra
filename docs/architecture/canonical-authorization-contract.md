# Contrato Canónico de Autorización (CBS-K1)

- MAIN_SHA: 15bc237be5555fcc38bc8a25f80724473c13435b
- BRANCH: hermes/cbs-pr8-11-convergence-audit
- TIMESTAMP_UTC: 2026-10-08
- AUTOR: Hermes (writer; basado en lectura directa de PR8/PR11, no ejecución)
- ESTADO: ESPECIFICACIÓN (no implementada; no se modifica código)

## 0. Alcance

Fija la frontera entre el pre-gate de seguridad (PR8) y la autorización de
ejecución (PR11) para que puedan integrarse sin doble autoridad. No cambia
código; define responsabilidades, fuente de verdad, invariantes, transiciones,
escenarios y un plan de implementación futuro.

Evidencia base: docs/architecture/pr8-pr11-authz-semantic-audit.md
(clasificación COMPLEMENTARY_WITH_BOUNDARY).

## 1. Responsabilidades por capa

| Capa | Módulo real | Responsabilidad | Puede denegar | Puede permitir sola |
|------|-------------|-----------------|---------------|---------------------|
| Security pre-gate | `blackforge_safety.evaluate_blackforge_safety` (PR8) | Clasificar un ITEM por safety_class (S0–S3) y estado de autorización declarado; filtrar antes de cualquier hook | SÍ (DENY) | SÍ, para análisis conceptual/local (ALLOW_CONCEPTUAL/DEFENSIVE/LOCAL) |
| DefensiveCase | `blackforge_case.DefensiveCase` (PR11) | Máquina de estados del caso; sella plan; valida autorización de ejecución | SÍ (AUTH_BLOCKED/DENIED) | NO (una autorización por sí sola no ejecuta) |
| Broker | `blackforge_broker` (PR11) | Único punto de autoridad ejecutiva; reserva+consume nonce; dispatch | SÍ (AuthorizationError, "cero despachos") | SÍ, pero solo si el grant está GRANTED y el nonce vivo |
| Persistencia/auditoría | `storage.Storage` (PR9) + broker SQLite (PR11) | Registrar sesiones/eventos y el journal de intentos | SÍ (falla la escritura -> no se ejecuta) | NO |
| Caller/consumer | UI/adapters/MCP | Invocar y respetar las decisiones | NO (no decide autorización) | NO |

## 2. Fuente de verdad

- Estado global de política/seguridad: **PR8** (`safety_class` + `session_context`).
  Es un pre-gate declarativo, sin persistencia.
- Autorización de UNA ejecución concreta: **PR11** (`Authorization` con nonce,
  plan_digest, boot_epoch, max_duration_s). Persistida en el broker SQLite
  (tablas `grants`/`attempts`/`consumptions`).
- Capa que puede denegar: ambas, y la denegación es acumulativa.
- Capa que puede permitir por sí sola: solo el broker (PR11) puede habilitar una
  ejecución, y únicamente con grant GRANTED + nonce vivo. PR8 nunca habilita
  ejecución: como máximo permite análisis conceptual/local.
- **Precedencia**: una denegación en CUALQUIER capa prevalece. Orden de
  evaluación: PR8 (pre-gate) -> DefensiveCase (estado) -> broker (reserva) ->
  dispatch. Si PR8 = DENY, el broker nunca se alcanza. Si el broker deniega,
  PR8 no puede revertirlo.

## 3. Invariantes

| # | Invariante | Implementado hoy | Dónde |
|---|-----------|------------------|-------|
| I1 | Ausencia = denegación | SÍ | PR8: auth_required sin estado válido; PR11: `authorization_is_live` record ausente -> no live |
| I2 | Estado desconocido = denegación | SÍ | PR8: clase desconocida -> DENY; estado inválido -> DENY; PR11: eje != GRANTED -> no live |
| I3 | Caducidad = denegación | SÍ | PR8: EXPIRED + required -> DENY; PR11: (now-start)>max_duration_s -> EXPIRED |
| I4 | Corrupción = denegación | PARCIAL | PR8: ValueError parseo -> DENY; PR11: campos vacíos/sha256 inválido -> CaseError |
| I5 | Nonce reutilizado = denegación | SÍ | PR11 broker: `consumptions` nonce UNIQUE; segundo reserve -> "ya se consumió" |
| I6 | Toda ejecución autorizada es trazable | SÍ | PR11: journal fsync antes de dispatch + tablas attempts/consumptions |
| I7 | Ninguna ejecución por default permisivo | SÍ | PR8 default PENDING; PR11 default AuthorizationAxis.NONE + `_allow_mutation=False` |

## 4. Modelo de transición (propuesto)

Estados conceptuales (mapean a los reales de PR8/PR11):

- PRE_GATE_DENY  -> PR8 devuelve DENY; fin. (safety_class desconocida, S2/S3 sin requisitos, DENIED/EXPIRED requerido)
- CASE_CREATED   -> DefensiveCase DRAFT -> PLAN_SEALED (PR11)
- EXEC_AUTH_ISSUED  -> Authorization adjuntada (attach_authorization) con nonce/plan_digest/boot_epoch válidos
- EXEC_AUTH_CONSUMED -> broker.reserve consume nonce (CONSUMED) en BEGIN IMMEDIATE
- EXEC_DENIED    -> mark_auth_blocked (AuthorizationAxis.DENIED) o broker AuthorizationError
- EXEC_EXPIRED   -> authorization_is_live: TTL excedido -> EXPIRED
- AUDIT_PERSISTED -> journal fsync + event append (PR9 storage / PR11 journal)
- RECOVERY_REQUIRED -> crash tras posible efecto: OUTCOME_UNKNOWN, nunca reintento automático

Transiciones legales: PRE_GATE_DENY es terminal; EXEC_AUTH_CONSUMED solo desde
GRANTED vivo; EXEC_DENIED/EXPIRED son terminales para ese nonce; RECOVERY_REQUIRED
requiere intervención humana.

## 5. Tabla de escenarios (15)

| # | Input | Pre-gate (PR8) | DefensiveCase (PR11) | Broker (PR11) | Persistencia | Decisión final | Evidencia requerida |
|---|-------|----------------|----------------------|---------------|--------------|----------------|---------------------|
| 1 | Item S0_CONCEPTUAL | ALLOW_CONCEPTUAL | — | — | sesión opcional | Permitido (análisis) | SafetyDecision.to_dict |
| 2 | Item S1_DEFENSIVE | ALLOW_DEFENSIVE/LOCAL | — | — | sesión opcional | Permitido (diseño local) | SafetyDecision |
| 3 | Item S2 sin sandbox | DENY (unmet) | — | — | — | Denegado | unmet_requirements |
| 4 | Item S3 sin aprobación humana | DENY | — | — | — | Denegado | unmet_requirements |
| 5 | Autorización ausente + ejecución | DENY (si required) | require_authorized -> CaseError | reserve -> AuthorizationError | — | Denegado | mensaje "no hay autorizacion registrada" |
| 6 | Autorización expirada | DENY (EXPIRED) | authorization_is_live -> False | reserve: TTL -> AuthorizationError | grant state | Denegado | causa "expiro (max_duration_s=...)" |
| 7 | Autorización denegada | DENY (DENIED) | mark_auth_blocked -> DENIED | reserve: state != GRANTED | audit event | Denegado | eje DENIED |
| 8 | Autorización revocada | (no aplica en PR8) | revoke -> REVOKED | authorization_is_live: revocada ANTES del eje | _revoked_authorizations | Denegado | causa "autorizacion revocada: <nonce>" |
| 9 | Autorización corrupta (sha256 malo) | — | attach_authorization -> CaseError | — | — | Denegado | CaseError approved_plan_digest |
| 10 | Autorización válida | permitido por clase | attach OK | reserve OK, nonce consumido | journal fsync | Autorizado | attempt + consumption rows |
| 11 | Autorización desconocida | DENY (estado/clase) | eje != GRANTED -> no live | — | — | Denegado | mensaje de causa |
| 12 | Datos parciales (snapshot incompleto) | — | slice: INDETERMINATE | — | — | Indeterminado | blockers "completitud PARTIAL" |
| 13 | Persistencia previa incompatible | — | — | reserve falla (sqlite) -> PersistenceError | rollback | Denegado | PersistenceError "cero efectos" |
| 14 | Replay/reintento mismo nonce | — | — | segundo reserve -> AuthorizationError "ya se consumió" | consumptions UNIQUE | Denegado | attempt_id original |
| 15 | Ejecución broker sin autorización explícita | DENY si required | mark_reserved exige GRANTED | reserve exige GRANTED | — | Denegado | "cero despachos" |
| 16 | Reinicio entre emisión y consumo | — | boot_epoch distinto -> no live | reserve: boot_epoch | — | Denegado | causa "otra epoca de arranque" |

## 6. API/contrato conceptual propuesto (NO implementado)

Tipos (nombres conceptuales; no se crea código):

- `SecurityVerdict` (PR8): { decision, safety_class, unmet_requirements[], allowed_scope }.
- `ExecutionAuthorization` (PR11): { subject, credential_ref, plan_digest, nonce,
  boot_epoch, valid_from, max_duration_s, approved_actions[], resolved_targets[],
  state }.
- `ExecutionDecision`: { allowed: bool, cause: str, nonce: str }.
- `AuditEvent`: { case_id, nonce, kind, at, safety_verdict_ref }.

Datos que NO deben duplicarse:
- El estado de autorización NO debe vivir en dos sitios: PR8 no debe almacenar
  nonce/plan_digest; PR11 no debe re-clasificar safety_class.
- El TTL y el nonce son propiedad exclusiva de PR11 (broker).
- `safety_class` es propiedad exclusiva de PR8.

Evento que debe quedar auditado:
- Toda transición a EXEC_AUTH_ISSUED/CONSUMED/DENIED/EXPIRED y toda
  RECOVERY_REQUIRED, con (case_id, nonce, causa). Hoy: PR9 `record_event`
  (mitigation_*) y PR11 journal (`attempt_reserved`). Falta un evento unificado
  de autorización (gap).

## 7. Compatibilidad

- Datos sin nonce: no son una ejecución autorizable; deben tratarse como
  ausencia de autorización (I1). PR11 `Authorization.__post_init__` ya exige nonce
  no vacío -> CaseError.
- Casos legacy: una `DefensiveCase` sin `_authorization_record` -> no live
  (falla cerrado). PR8 no persiste, así que no hay legacy de seguridad.
- Datos corruptos: PR8 DENY por parseo; PR11 CaseError/PersistenceError.
- Reinicio entre emisión y consumo: boot_epoch invalida (I2) -> denegación.
- Reintentos: nonce single-use; reintento -> denegación (I5). Nunca reintento
  automático tras posible efecto (RECOVERY_REQUIRED).

## 8. Plan de implementación futuro (mínimo, no ejecutado)

1. Orden:
   a. Documentar el mapeo de estados (este contrato) — hecho.
   b. Añadir un evento de auditoría unificado de autorización (PR9/PR11) — futuro.
   c. Test de frontera PR8->PR11 (CBS-K5) antes de integrar.
   d. Rebase PR8 a main (CBS-K3) y merge PR9/PR11 tras gates verdes.
2. Cambios mínimos: no unificar enums en código; solo documentar frontera y
   añadir el evento de auditoría.
3. Pruebas necesarias: frontera pre-gate->broker; replay de nonce; boot_epoch.
4. Rollback: cada paso en rama aislada; revert del commit.
5. STOP: si unificar requiere cambiar semántica de PR8 o PR11 sin aprobación.

## UNVERIFIED
- No se ejecutó código de PR8/PR11 (HARD_PAUSE); el contrato es estático.
- El evento de auditoría unificado de autorización NO existe hoy (gap declarado).
- Nombres de tipos son conceptuales, no símbolos reales.
