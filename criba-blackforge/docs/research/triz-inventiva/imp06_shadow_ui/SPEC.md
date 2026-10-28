IMP-06 — Especificación de uso en Shadow UI existente
======================================================
Estado: SPEC / MAPPING / PLAN DE PRUEBAS (NO IMPLEMENTADO). risk_profile DOC.
Autor: Hermes (sesión nous/ornith-1.5-122b:free). Fecha: 2026-10-28.
Autorización: LOCAL_PREPARATION_ONLY. No se modifica runtime en esta tarjeta.

1. OBJETIVO
-----------
Diseñar cómo la Shadow UI EXISTENTE presentaría el material de la campaña
(función, contradicción, operador, origen/destino, puente, relación, ruptura,
mecanismo y prueba), reutilizando la vista canónica de candidatos/dossier/fuentes.
NO rediseñar dashboard, NO añadir una UI SUPRA, NO cambiar identidad visual.

2. COMPONENTES REALES INSPECCIONADOS
------------------------------------
- src/criba/ui/dossier_workflow_view.py
    * apply_dossier_report(window, report): renderiza el report del workflow.
      - report["workflow_schema"] debe == SCHEMA ("criba-dossier-workflow/1").
      - dossier -> widget candidates.dossier_output (setPlainText JSON).
      - report completo -> widget candidates.supra_output.
      - refs["ideaSummary"] recibe un suffix con local_dossier_status (i18n).
    * bind_language(window): listener de cambio de idioma; no genera datos.
- src/criba/dossier_workflow.py (SCHEMA "criba-dossier-workflow/1")
    * WorkflowReport: {workflow_schema, endpoint, dossier, read{...},
      local_dossier_status, local_dossier_reason}.
- src/criba/ui/actions.py (no modificado aquí): acciones de la UI.

3. PRINCIPIO DE HONESTIDAD (no generar hechos al renderizar)
-----------------------------------------------------------
Cada campo mostrado procede de un payload con provenance. Donde el dato falte,
se muestra UNKNOWN, nunca un valor fabricado. El modo de selección se muestra
como dato; los costes reales solo si existen; UNKNOWN donde falten.
Separar cuatro acciones distintas, sin autoejecución ni falsa habilitación:
  (1) consultar (read-only)   (2) generar propuesta (determinista/local)
  (3) guardar (persistencia local)   (4) solicitar ejecución (requiere aprobación)

4. MAPPING VIEW-MODEL (payload -> widget)
-----------------------------------------
El material académico (fichas AC-06, operadores) NO tiene estos campos en la
ficha cruda; el mapping define qué campo del payload productivo alimenta cada
widget. La ficha se presenta como DATO de campaña, no como resultado validado.

  Campo UI (widget)        <- payload / provenance
  ------------------------  -------------------------------------------------
  dossier_output           <- report["dossier"] (supra_dossier)
  supra_output             <- report completo (workflow report)
  ideaSummary suffix       <- "dossier.local.<local_dossier_status>" (i18n)
  [propuesto] ficha.acion  <- ficha.content.operacion   provenance: source_id
  [propuesto] ficha.mecanismo <- ficha.content.mecanismo provenance: source_id
  [propuesto] ficha.ruptura <- ficha.limits.ruptura       (UNKNOWN si ausente)
  [propuesto] ficha.rival  <- ficha.discrimination.rival
  [propuesto] ficha.pred_m <- ficha.discrimination.prediccion_mecanismo
  [propuesto] ficha.pred_r <- ficha.discrimination.prediccion_rival
  [propuesto] ficha.puente <- operador.cross_domain.puente (si existe)
  [propuesto] estado_inventivo <- "REPRESENTATION_ONLY_NOT_FUNCTIONAL_TEST"
                                   (de limitations del dossier, no del modelo)

Los widgets [propuesto] NO se añaden en esta fase: requieren ampliar la vista
real, lo que es IMP-10 (NO autorizado). Aquí se define el mapping para que la
implementación futura tenga contrato claro y no invente campos.

5. EVENTOS (propuestos, no implementados)
-----------------------------------------
  consultar_propuesta   -> read-only; llama a workflow.validate/cargar; sin efecto.
  generar_propuesta     -> determinista/local (preparar_dossier); sin servicio.
  guardar_propuesta     -> guardar_dossier en storage local; NO a base productiva.
  solicitar_ejecucion   -> habilitado SOLO con aprobación; abre flujo de
                           autorización (IMP-07); nunca autoejecuta.
Ningún botón declara "invención validada" ni elude la aprobación.

6. PLAN DE PRUEBAS UI (sin ejecutar UI productiva)
--------------------------------------------------
Las pruebas de estados se diseñan como pruebas de mapeo de datos (view-model),
no como clics en la UI productiva:
  T-14 estados Shadow: Loading, empty, error, stale, retry, doble envío.
    - empty: dossier ausente -> "UNKNOWN"/empty, no éxito.
    - error: workflow.validate lanza -> estado error visible, no ocultado.
    - stale: read con status_source=IN_PROCESS_MEMORY_CACHE y
      persisted_artifact_status=DIVERGES_FROM_CACHE -> mostrar divergencia.
    - retry: segundo read tras error -> reconstruye el estado real.
    - doble envío: dos solicitudes de ejecución -> rechazada la segunda sin
      efecto externo.
  T-15 BLACKFORGE: no aprobado/fuera de alcance/key ausente -> rechazo seguro
    sin executor alternativo ni efecto externo (ver IMP-07).
Verificación de esta fase: pruebas de mapping view-model deterministas que
pasen, sin arrancar la ventana productiva. (Pendiente de escribir si se
autoriza IMP-06b; no implementado aquí.)

7. NO VERIFICADO / LÍMITES
--------------------------
- No se ejecutó la UI real; no se verificó renderizado visual.
- Los widgets [propuesto] no existen; el mapping es un contrato de diseño.
- No se modificó ni se probó en runtime productivo.
