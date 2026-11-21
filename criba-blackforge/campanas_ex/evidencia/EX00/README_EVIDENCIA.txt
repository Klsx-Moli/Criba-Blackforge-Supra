EX00 — Revalidar alcance exigible del canon completo
====================================================
Fecha: 2026-10-25
Branch: campana/ex-00-revalidar-alcance
Base commit: 5e89959 (main)
Writer: hermes (Beam)

ACCION: Revalidacion READ-ONLY del canon T001-T130. No se modifico technique_registry.yaml ni fichas.
Fuente canonica: data/intelligence/technique_registry.yaml (canon_version 2026-09-08.3, 130 IDs).
Fuente auditoria: docs/handoff/K10_technique_audit_matrix.txt (130 filas, K10 DONE).

CLASIFICACION POR ID (autoridad = status del canon + consumer real):
  MVP_IMPLEMENTED: 29  (status=IMPLEMENTED, codigo resoluble, tests reales, guard trazabilidad pasa)
  EXTENSION_PROMOTION_CANDIDATE: 2  (T054, T061: modulo+test+adapter existen, pero canon los declara PLANNED;
                                    consumer execute_technique los rechaza; promocion requiere attestation A2 / owner)
  EXTENSION_SHADOW_BYPASS: 2  (T104, T111: PLANNED en canon pero consumer real via mcda_adapter Shadow bypass;
                              gap de arquitectura, ADR pendiente)
  EXTENSION_MODULE_ONLY: 42  (modulo existe, sin test dedicado ni consumer)
  RESEARCH_NO_CODE: 55  (sin modulo, sin test; construccion nueva requerida)

NO se bajo ningun requisito ni se promovio PLANNED por presencia de handler.
T054/T061 siguen PLANNED en el canon (verificado: technique_registry.yaml).
T063 sigue IMPLEMENTED (gateway para P10-T11, verificado).
STANDARD sigue DISABLED; executor real OFF; proveedor real OFF (sin cambio).

VERIFICACION:
  - guard trazabilidad: tests/intelligence/test_technique_runtime_traceability.py + test_canon_operator_chain.py = 38 passed
  - recovery baseline: 21 passed
  - anti-goodhart: 23 passed
  - canon count: 130 (validate() sin errores)
  - implemented: 29 (sin cambio)

ARCHIVOS GENERADOS:
  - campanas_ex/evidencia/EX00/clasificacion_canon.csv (v1)
  - campanas_ex/evidencia/EX00/clasificacion_canon_v2.csv (clasificacion autoritativa)
  - campanas_ex/evidencia/EX00/resumen_clasificacion.json
  - campanas_ex/evidencia/EX00/README_EVIDENCIA.txt

CONCLUSION: EX00 DONE_VERIFIED (revalidacion, sin cambios de codigo de produccion).
