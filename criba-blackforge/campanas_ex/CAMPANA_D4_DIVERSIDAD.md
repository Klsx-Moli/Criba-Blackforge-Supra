# Campaña D4 — Diversidad Funcional

## Objetivo
Resolver D4 (diversidad funcional) de UNRESOLVED a RESOLVED con evidencia.

## Contexto
D4 = diversidad de las ideas generadas (no solo léxica, sino funcional:
diferentes mecanismos, diferentes dominios, diferentes enfoques).
Actualmente UNRESOLVED.

## Pasos

### 1. Localizar métricas de diversidad existentes
```bash
cd criba-blackforge
grep -rn "diversidad\|diversity\|diverse" src/ tests/ docs/ --include="*.py" --include="*.md" | head -30
```

### 2. Identificar qué se mide actualmente
- Buscar en tests/intelligence/test_t104_t111_scoring.py.
- Buscar en src/criba/intelligence/scoring/.

### 3. Definir métrica de diversidad funcional
- No solo distinct strings, sino distinct mechanisms/domains/approaches.
- Usar clustering o categorización.
- Definir umbral.

### 4. Implementar medición (si no existe)
- Crear test que mida diversidad de un conjunto de ideas.
- Ejecutar.
- Registrar métrica.

### 5. Ejecutar campaña
- Generar N ideas.
- Medir diversidad funcional.
- Registrar distribución.

### 6. Resolver D4
- Si métrica ≥ umbral → D4 = RESOLVED.
- Registrar evidencia.

## Evidencia requerida
- Métrica de diversidad funcional definida y medida.
- Distribución de scores.
- Tests pasando.
