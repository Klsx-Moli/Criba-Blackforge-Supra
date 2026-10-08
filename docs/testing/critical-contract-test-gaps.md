# Huecos Críticos de Tests por Contrato

- TARGET_MAIN: 15bc237
- TIMESTAMP_UTC: 2026-10-08
- AUTOR: Hermes (writer; clasificación por inspección de diffs/metadata, NO ejecución)

NOTA: todos los "tests encontrados" son por presencia de archivo en el diff de PR
(gh pr view files) o mención en commit body. No se ejecutó ninguna suite (NOT_RUN).
Los conteos son REPORTED_BY_PR.

## Matriz por contrato

| Contrato | Tests encontrados | Cobertura aparente | Ausencia relevante | Riesgo | Prioridad test futura |
|----------|-------------------|--------------------|--------------------|--------|----------------------|
| authz fail-closed (PR8) | test_blackforge_safety.py (+67); commit cita 188 passed dirigidos, mutation accreditation | directa + mutación (fail-closed block elimina 3 tests) | replay/reintento no aplica (PR8 no persiste); integración con broker no testeada | BAJO | CBS-K5: test de frontera PR8<->PR11 |
| DefensiveCase / broker (PR11) | test_blackforge_v1_mutations.py (+355), test_blackforge_v1_negative10.py (+571), synthetic_lab.py; commit cita 26 negativos + 15 mutación + 1545 suite | negativa + mutación + round-trip JSON + determinismo | corrupción de tabla broker (WAL roto) no citada; boot_epoch en entorno real no testeado fuera de unit | MEDIO | CBS-K5: test de replay de nonce en entorno persistente |
| persistence round-trip (PR9) | test_storage_decision_evidence.py (+113), test_blackforge_agentic.py (+106), test_blackforge_pipeline.py (+23) | guardar/recargar/append/atomicidad concurrente | columna legacy (BD preexistente sin evidence_json) no cubierta; crash/WAL recovery no ejecutado | MEDIO | CBS-K6: round-trip + corrupción + reinicio |
| reinicio / recuperación (PR9/PR11) | PR11 journal fsync; PR9 WAL; ningún test de crash explícito citado | implícita | recovery ante kill durante BEGIN IMMEDIATE no verificada | MEDIO | CBS-K6: test de recovery |
| datos legacy (PR9) | none citado para BD legacy | AUSENTE | carga de esquema previo a SCHEMA_VERSION=1 | ALTO | CBS-K6: fixture legacy |
| defaults (PR9/PR8) | PR9 evidence_json DEFAULT '[]'; PR8 AuthorizationState PENDING default | parcial | default de PR11 AuthorizationAxis.NONE no testeado como bloqueo | BAJO | CBS-K5 |
| corrupción / datos parciales (PR9) | test_storage: "reject fabricated history sessions", "bind packet to session identity" | validación de campos | JSON corrupto en packet_json no citado | MEDIO | CBS-K6 |
| negativo / acceso denegado (PR8/PR11) | PR8 DENY por clase/estado; PR11 negative10 | fuerte en ambos | caso "autorización desconocida" en PR11 solo vía slice (SnapshotError), no en broker | BAJO | CBS-K5 |
| acoplamiento interpreter line (PR10) | test_interpreter_hardening (+461), test_source_evidence_context (+276), test_source_refresh_hardening (+147), test_refresh_sources (+268), test_shadow_interpreter_journey | amplia pero en base shadow-supra | NO verificada contra main (base distinta); determinismo parcial | ALTO | CBS-K7: tras split, tests contra main |
| continuidad documental (PR12) | none (docs) | N/A | no es testeable; límite de evidencia declarado | N/A | CBS-K8: cierre documental |

## Riesgos agregados

- ALTO: datos legacy PR9 (sin test), acoplamiento PR10 a main (base distinta, no verificado).
- MEDIO: recovery/crash PR9+PR11, corrupción parcial, round-trip PR9 no ejecutado.
- BAJO: authz PR8/PR11 individual (bien cubiertos por mutación/negativos reportados).

## Prioridad de ejecución futura (sin ejecutar ahora)

1. CBS-K4: baseline de main (suite CRIBA/BLACKFORGE/SUPRA) para comparar.
2. CBS-K5: tests críticos authz/broker (frontera PR8<->PR11, nonce replay).
3. CBS-K6: persistencia PR9 (round-trip, legacy, corrupción, reinicio).
4. CBS-K7: tras split de PR10, tests contra main.

## UNVERIFIED
- Ningún test ejecutado en esta sesión (NOT_RUN).
- Conteos REPORTED_BY_PR no reproducidos.
- Cobertura real (líneas/branches) desconocida.
