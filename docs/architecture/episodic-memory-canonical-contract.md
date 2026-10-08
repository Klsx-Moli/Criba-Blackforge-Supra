# Contrato Canónico de Memoria Episódica — Estado y Límites

- TARGET_MAIN_SHA: 15bc237be5555fcc38bc8a25f80724473c13435b
- BRANCH_AUDIT: hermes/cbs-pr8-11-convergence-audit @ 15bc237
- TIMESTAMP_UTC: 2026-10-08
- AUTOR: Hermes (writer)

## HALLAZGO CENTRAL

La misión original pide un "contrato canónico de memoria episódica" y reconciliar
PR #8–#11 sobre "episodic replay / reliability / consensus / VOI / shadow pricing".
Ninguno de esos contratos existe en los PR #8–#12 reales (ver
pr-8-11-convergence-matrix.md, SC-01). Los PR reales cubren:

- BLACKFORGE safety / authz fail-closed (PR8)
- BLACKFORGE durable agentic audit / persistence (PR9)
- intérprete causal / evidence_context / UI (PR10)
- BLACKFORGE v1 broker / DefensiveCase / slice authz (PR11)
- documentación de continuidad (PR12)

No hay módulo de memoria episódica, replay, VOI, regret, shadow pricing ni
consensus en los diffs. Este documento NO define un contrato inventado; define
los INVARIANTES que cualquier propuesta futura de memoria episódica debe cumplir
antes de ser considerada para integración, y declara el estado actual como
NO_EXISTE_EN_PR.

## Invariantes exigibles (a aplicar si/se cuando exista propuesta)

| Invariante | Dónde debería implementarse | PR que lo afecta hoy | Test hoy | Prueba adversarial | Estado |
|------------|------------------------------|----------------------|----------|---------------------|--------|
| Memoria vacía no rompe el flujo | (propuesta futura) | ninguno | N/A | N/A | UNKNOWN |
| Datos legacy se cargan o fallan con diagnóstico | (propuesta) | PR9 persistence (adyacente) | test_storage_decision_evidence (REPORTED) | no verificado | UNKNOWN |
| Episodios duplicados no degradan silenciosamente el ranking | (propuesta) | ninguno | N/A | N/A | UNKNOWN |
| Ranking determinista con config+entradas deterministas | (propuesta) | PR10 determinism tests (REPORTED) | test_interprete_pipeline_determinismo | no verificado | UNKNOWN |
| Fuentes fiable/no-fiable no crean ciclo auto-confirmación sin observación externa | (propuesta) | PR10 evidence_context (UNKNOWN coverage) | test_source_evidence_context (REPORTED) | no verificado | UNKNOWN |
| Coste/VOI/regret con unidades/semántica declaradas | (propuesta) | ninguno | N/A | N/A | UNKNOWN |
| Costes cero/negativos/ausentes/extremos con comportamiento definido | (propuesta) | ninguno | N/A | N/A | UNKNOWN |
| kwargs de proveedor/modelo no se silencian ni cambian de significado | model_config / model_runtime | PR10 model_config.py (+4) | test_model_config (REPORTED) | no verificado | UNKNOWN |
| Decisiones y procedencia observables sin secretos | PR11 evidence origin / PR9 audit | PR9, PR11 | test_blackforge_v1_*, test_storage | no verificado | PARTIAL |
| Documentación separa MAIN/EXPERIMENTAL/PLANNED/NOT_VALIDATED | docs | PR12 (continuity) | none | N/A | PARTIAL |
| No se declara mejora empírica sin benchmark fuera de muestra | (propuesta) | ninguno | N/A | N/A | UNKNOWN |

## Decisión

NO se redacta un contrato canónico de memoria episódica porque no hay
implementación ni propuesta reproducida en los PR actuales. Hacerlo sería
inventar una capacidad (violación de regla dura). Se deja como PLANTILLA de
aceptación para cuando aparezca una propuesta real con diff reproducible.

## UNVERIFIED
- Todos los "tests" citados son REPORTED_BY_PR, no ejecutados en esta sesión.
- La semántica de PR9/PR11 en cuanto a procedencia observable no fue inspeccionada
  internamente; se cita por descripción de commit, no verificada.
