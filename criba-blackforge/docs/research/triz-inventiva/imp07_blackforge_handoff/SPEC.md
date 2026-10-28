IMP-07 — Handoff controlado a BLACKFORGE sin ejecución
======================================================
Estado: SPEC / CASOS DE SEGURIDAD PROPUESTOS (NO EJECUTADO). risk_profile DOC.
Autor: Hermes (sesión nous/ornith-1.5-122b:free). Fecha: 2026-10-28.
Autorización: LOCAL_PREPARATION_ONLY. BLACKFORGE NO se ejecuta.

1. OBJETIVO
-----------
Preparar la transferencia de un candidato de la campaña a BLACKFORGE como
SOLICITUD CONTROLADA bajo contrato y autorizaciones vigentes — nunca ejecución
automática. Inspeccionar el contrato real del broker; no imponer una pausa
histórica; declarar NOT_WIRED si no hay receptor; nunca crear un executor
alternativo.

2. CONTRATO REAL DE BLACKFORGE INSPECCIONADO
--------------------------------------------
src/criba/blackforge_broker.py — el BROKER es el ÚNICO camino a un executor:
  * KERNEL (core/Shadow UI): analiza y propone planes. NO tiene executor, NO
    abre el ledger de autorizaciones para escritura, NO retiene credencial.
  * BROKER: posee el ledger (SQLite), el journal append-only (fsync) y el loop
    de dispatch. ÚNICO path a un executor.
  * EXECUTOR: operaciones tipadas dentro de un lab autorizado; nunca amplía scope.
  * TYPED_OPERATIONS: {probe_parser_quote, probe_authz_matrix, read_header_names,
    enumerate_declared_routes, snapshot_config_flags}. Una cadena libre de un
    modelo se rechaza en el límite de tipo.
  * Fail-closed: sin grant, grant para otro plan, grant expirado, nonce
    consumido, precondición falsa o fallo de persistencia ANTES del dispatch =
    CERO efecto y error explícito.
  * reserve() consume el grant en una transacción IMMEDIATE y lo journaliza
    ANTES de cualquier efecto. dispatch() es el ÚNICO lugar que alcanza un
    executor y exige policy.execution_enabled (operación administrativa
    autenticada con credencial enrolada).
  * enable_execution(actor, reason): amplía capacidad SOLO con actor+motivo y
    un grant con credencial; de lo contrario PolicyError.
  * OutcomeUnknown: efecto posible cuyo resultado se perdió; nunca se reintenta.

3. HANDOFF PROPUESTO (NO IMPLEMENTADO)
--------------------------------------
El handoff de la campaña NO es una ejecución: es un PLAN de solicitud.
  (a) El candidato (dossier SUPRA de la campaña) se conserva en SUPRA como
      planning receipt (PLANNED_DISCRIMINANT_PROTOCOL_ONLY, NOT_EXECUTED).
  (b) La solicitud a BLACKFORGE es un Plan (blackforge_case.build_plan) con
      pasos que son operaciones tipadas de TYPED_OPERATIONS — NO acciones de
      modelo libres.
  (c) La autorización se gestiona por el ledger del broker: un grant con
      plan_digest, acciones enumeradas, targets, nonce único, límites y
      credencial. El KERNEL no puede registrar ni consumir un grant.
  (d) Si no existe receptor/grant válido -> estado NOT_WIRED, sin executor
      alternativo. El cambio mínimo para wirear es administrativo, fuera de
      alcance de esta fase.

4. CASOS DE SEGURIDAD PROPUESTOS (no ejecutados)
------------------------------------------------
  S-1 No autorizado:
      acción sin grant -> AuthorizationError; CERO efecto.
  S-2 Grant para otro plan:
      plan_digest alterado -> AuthorizationError (reserve rechaza); CERO efecto.
  S-3 Key/credencial ausente:
      enable_execution sin grant con credencial -> PolicyError
      ("habilitar ejecución sin ella fabricaría autoridad").
  S-4 Candidato incompleto:
      dossier sin lineage no vacío (dossier_id/candidate_id/claim_id/
      mechanism_version/protocol_version) -> el write path de SUPRA lo rechaza;
      y un Plan sin pasos tipados -> _actions_from_digest_shape = [] y reserve
      rechaza todo dispatch.
  S-5 Efectos fuera de alcance:
      una operación no en TYPED_OPERATIONS, o con params no permitidos, se
      rechaza en validate_operation; CERO efecto.
  S-6 Key ausente si aplica:
      sin executor restringido disponible -> CapabilityNotEnabled; CERO efecto.
  S-7 Falta de capacidad como estado:
      execution_enabled=False -> CapabilityNotEnabled; el estado se muestra, NO
      se suplanta con éxito simulado.

5. AC DE LA TARJETA CUBIERTAS (diseño)
--------------------------------------
  * Ningún candidato se ejecuta ni obtiene autorización por existir en SUPRA o
    UI: el receipt es PLANNED_NOT_EXECUTED; la UI (IMP-06) separa consultar/
    generar/guardar/solicitar; la solicitud pasa por reserve() del broker.
  * Falta de capacidad se muestra como estado (CapabilityNotEnabled/NOT_WIRED),
    no se suplanta con éxito simulado.

6. NO VERIFICADO / LÍMITES
--------------------------
- No se registró ni consumió ningún grant; no se ejecutó ningún dispatch.
- No se verificó el ACL del ledger en este entorno (scripts/install_broker_acl.py
  fuera de alcance). La frontera de seguridad es el ACL del FS, no este proceso.
- El handoff es un contrato de diseño; la wireación real requiere aprobación
  administrativa y credencial, fuera de LOCAL_PREPARATION_ONLY.
