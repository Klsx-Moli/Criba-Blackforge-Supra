IMP-05 — Especificación de preservación de fichas en SUPRA
=========================================================
Estado: SPEC / PARCHES PROPUESTOS (NO APLICADOS). risk_profile LAB.
Autor: Hermes (sesión nous/ornith-1.5-122b:free). Fecha: 2026-10-28.
Autorización: LOCAL_PREPARATION_ONLY. IMP-10 NO AUTORIZADO.

1. OBJETIVO
-----------
Preparar la preservación de fichas/operadores de conocimiento inventivo en SUPRA
sin ejecutar SUPRA, sin llamar modelos ni BLACKFORGE, y sin tocar runtime.
Entregables de la tarjeta: (a) Mapping SUPRA, (b) Tests aislados round-trip/
conflictos, (c) Parche propuesto si procede.

2. COMPONENTES REALES INSPECCIONADOS (no inventados)
----------------------------------------------------
- src/criba/integrations/supra_client.py
    * SupraClient.run_project(criba_dossier=...): write path. Exige lineage no
      vacío (dossier_id, candidate_id, claim_id, mechanism_version,
      protocol_version) y un canonical sha256 en mechanism/protocol_version.
      * dossier_payload_fingerprint() = sha256 de _with_declared_defaults +
        json sort_keys. El receipt del servidor debe coincidir.
    * SupraCribaPlanningReceipt: scope PLANNED_DISCRIMINANT_PROTOCOL_ONLY,
      execution_status NOT_EXECUTED, scientific_status NOT_VALIDATED.
    * GET /api/v1/projects/{id} (get_project): read path con status_source y
      persisted_artifact_status; reconstruye estado tras restart.
- src/criba/supra_dossier.py
    * preparar_dossier(): ensambla un dossier SUPRA válido con prueba
      discriminante; estado = SUPRA_EJECUCION_PENDIENTE; protocolo NO_EJECUTADA.
    * guardar_dossier/cargar_dossier: almacenamiento local jsonl (dossiers.jsonl);
      rechaza sobrescribir un dossier_id con contenido distinto (ambigüedad).
- src/criba/dossier_workflow.py (SCHEMA "criba-dossier-workflow/1")
    * WorkflowWorkflow.validate/submit: orquesta prepare -> store -> SUPRA read.

3. MAPPING FICHA/OPERADOR -> DOSSIER SUPRA
------------------------------------------
Una ficha AC-06 (esquema content/limits/discrimination) NO es auto-suficiente
para un dossier SUPRA: le faltan candidate_id, problema, claim_id y evidencia.
El adaptador propuesto (NO implementado) debe aportar el envolvente de campaña:

  ficha AC-06 {content{operacion,mecanismo}, limits{ruptura},
               discrimination{rival,prediccion_mecanismo,prediccion_rival}}
        |
        v  (adaptador propuesto en imp05_adapter.py — NO creado)
        |
  dossier SUPRA {
    candidate_id   <- "AC-06-<n>" (del bundle, no inventado)
    problema       <- objetivo de campaña (campo externo, no de la ficha)
    hipotesis      <- content.operacion / mecanismo
    mecanismo      <- content.mecanismo
    prueba_discriminante.alternativa_explicativa <- discrimination.rival
    prueba_discriminante.resultado_favorable_mecanismo <- prediccion_mecanismo
    prueba_discriminante.resultado_favorable_alternativa <- prediccion_rival
    supuestos      <- [limits.ruptura] (UNKNOWN != 0)
    claim_id / mechanism_version / protocol_version <- calculados por preparar_dossier
    interpretacion_provenance.interpreter_backend <- "DECLARED_UNVERIFIED"
  }

Nota de honestidad: la ficha académica aporta REPRESENTACIÓN, no evidencia
funcional. El dossier debe conservar limitations (p.ej.
REPRESENTATION_ONLY_NOT_FUNCTIONAL_TEST, PREDICTIONS_NOT_DISTINCT) y nunca
promover a PASS.

4. PARCHES PROPUESTOS (NO APLICADOS)
------------------------------------
Ningún cambio de runtime se aplica en esta fase. Dos opciones de parche,
ambas pendientes de aprobación IMP-10:

  OPCIÓN A (recomendada, mínima): un módulo de laboratorio
    docs/research/triz-inventiva/imp05_supra_preservation/adapter.py
    que convierte una ficha + contexto de campaña en el dict `entry` que
    preparar_dossier ya acepta. NO toca src/. El dossier resultante se
    preserva en storage temporal de laboratorio, no en la base productiva.

  OPCIÓN B (NO recomendada ahora): añadir un helper a supra_dossier.py.
    Rechazada por ahora porque mezcla conocimiento académico con el contrato
    de dossier del producto y ampliaría la superficie de runtime sin IMP-10.

5. PRUEBAS AISLADAS (VERIFICADAS POR EJECUCIÓN)
-----------------------------------------------
docs/research/triz-inventiva/imp05_supra_preservation/tests/test_supra_roundtrip_lab.py
Ejecución: .venv/Scripts/python.exe -m pytest <ruta> -p no:randomly
Resultado: 8 passed (REAL_EXIT=0).
Cobertura de AC:
  * Objeto semántico/orden/estado conservados en serialización ->
    test_roundtrip_preserves_semantic_object.
  * Persistir/leer NO ejecuta ni valida hipótesis -> idem (estado
    SUPRA_EJECUCION_PENDIENTE / NO_EJECUTADA).
  * Misma ID/mismo payload no sobrescribe -> test_same_id_same_payload_*.
  * Misma ID/payload distinto se rechaza, no se sobrescribe ->
    test_same_id_different_payload_is_rejected_not_overwritten.
  * Rechazo de versión de envelope desconocida ->
    test_client_rejects_unknown_envelope_version.
  * Receipt con lineage alterado se rechaza ->
    test_client_rejects_lineage_mismatch.
  * El write path no invoca modelo (use_model=False, sin provider/model) ->
    test_client_does_not_send_model_by_default.

6. NO VERIFICADO / LÍMITES
--------------------------
- No se ejecutó contra SUPRA real ni se probó un reinicio del producto: una
  prueba de disco local NO acredita SUPRA real (AC explícito de la tarjeta).
- No se probó corrupción/restart del almacenamiento de SUPRA (solo del
  almacenamiento local de laboratorio). Un harness de SUPRA con doble
  identificado y storage temporal pendiente en IMP-05b si se autoriza.
- El adaptador ficha->dossier NO existe todavía; las pruebas ejercitan el
  contrato de preservación con un entry construido a mano, no la conversión.
