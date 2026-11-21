# Campaña EX — Extensión Científica Completa (EX00–EX17)

## Objetivo
Cerrar el alcance extendido (PROGRAM_FULL_CLOSED) ejecutando las 18 tarjetas EX00–EX17
en lotes ordenados, con evidencia verificable.

## Lotes

### Lote 1 — Alcance y canon (EX00–EX01)
- EX00: Revalidar alcance exigible del canon completo.
  - Usar matriz T001–T130 existente (tests/intelligence/test_t104_t111_scoring.py, K10_technique_audit_matrix.txt).
  - Clasificar cada técnica como: MVP (ya cerrado), EXTENSIÓN (este lote), RESEARCH (fuera de scope).
  - No inferir trabajo restante del conteo 29/101.
  - Entregable: tabla clasificación por ID con autoridad, consumer, dependencia.

- EX01: Descomponer brechas reales del canon en lotes.
  - Usar resultado de EX00.
  - Crear fichas hijas para cada brecha real.
  - Estimar horas por lote.
  - Entregable: lista de lotes con estimación y dependencias.

### Lote 2 — Promoción de técnicas (EX02–EX04)
- EX02: Resolver promoción de T054 con autoridad.
  - Archivos: src/criba/intelligence/invention/recombination.py, tests/intelligence/test_t054_technological_recombination.py.
  - Verificar si T054 (recombinación tecnológica) tiene consumer real.
  - Si no tiene consumer → marcar como RESEARCH, no promover.
  - Si tiene consumer → verificar contrato y promover con evidencia.

- EX03: Resolver T061 y política de atributos tipados.
  - Archivos: src/criba/intelligence/mcda_adapter.py, tests/intelligence/test_t061_attribute_substitution.py, test_t061_wiring.py.
  - Verificar si T061 (sustitución de atributos) tiene wiring real.
  - Decidir política de atributos tipados.

- EX04: Verificar semántica T063 para prior art.
  - Buscar T063 en código y tests.
  - Verificar si tiene implementación o es solo plan.

### Lote 3 — Implementación y falsación (EX05–EX06)
- EX05: Implementar brecha concreta P10-T11.
  - Buscar referencias a P10, T11 en código/docs.
  - Si hay brecha real → implementar con TDD.
  - Si no hay brecha → marcar como NOT_REQUIRED.

- EX06: Falsación P10-T12 del pipeline vigente.
  - Buscar referencias a P10, T12.
  - Ejecutar falsación: ¿el pipeline actual cumple P10-T12?
  - Registrar resultado (PASS/FAIL) con evidencia.

### Lote 4 — MCDA y diversidad (EX07–EX08)
- EX07: Semántica MCDA T104–T111 y sensibilidad.
  - Archivos: src/criba/intelligence/scoring/, tests/intelligence/test_t104_t111_scoring.py.
  - Ejecutar tests existentes. Verificar sensibilidad.
  - Registrar métricas de sensibilidad.

- EX08: Diversidad y ScoreCard decisión de orden.
  - Buscar ScoreCard y diversidad en código.
  - Verificar si hay métrica de diversidad funcional.
  - Si no → implementar o marcar como gap.

### Lote 5 — BLACKFORGE (EX09–EX10)
- EX09: BLACKFORGE requisitos reales de reactivación.
  - Archivos: src/criba/blackforge_safety.py (si existe), blackforge_broker.py, blackforge_case.py.
  - Verificar qué requiere BLACKFORGE para reactivarse.
  - No reactivar sin aprobación.

- EX10: BLACKFORGE contratos fail-closed y auditoría offline.
  - Verificar contratos fail-closed existentes.
  - Ejecutar auditoría offline (sin proveedor real).

### Lote 6 — G3 y piloto (EX11–EX12)
- EX11: G3 Anti-Goodhart readiness sin activación.
  - Archivos: tests/astra_canon/test_anti_goodhart_runtime.py, ANTI_GOODHART_G3_PROTOCOL.md.
  - Verificar readiness (no activar).
  - Registrar gaps.

- EX12: Piloto selector preparación y viabilidad.
  - Verificar si hay piloto preparado.
  - Registrar viabilidad.

### Lote 7 — Evaluación y controles (EX13–EX14)
- EX13: Prerregistro y diseño de evaluación confirmatoria.
  - Crear protocolo de evaluación (no ejecutar).
  - Definir métricas, controles, hipótesis.

- EX14: Controles de integridad y gobierno que falten.
  - Verificar controles existentes.
  - Listar gaps.

### Lote 8 — Medición y diagnóstico (EX15–EX17)
- EX15: Medición y optimización de rendimiento.
  - Ejecutar benchmarks existentes.
  - Registrar métricas.

- EX16: Revisión de automejora fuera de alcance.
  - Revisar EX16 (automejora automática reportada).
  - Registrar como incidencia, no permiso.

- EX17: Diagnóstico de instrumentación faltante.
  - Listar qué instrumentación falta.
  - Crear plan de implementación.

## Comandos de verificación por lote
```bash
cd criba-blackforge
.venv/Scripts/python.exe -m pytest tests/ -q -p no:randomly --timeout=120
.venv/Scripts/python.exe -m mypy src/criba/<archivos> --no-error-summary
```

## Evidencia
- Cada lote produce: logs, tests, hashes, estado actualizado.
- Directorio: campanas_ex/evidencia/EX##/
