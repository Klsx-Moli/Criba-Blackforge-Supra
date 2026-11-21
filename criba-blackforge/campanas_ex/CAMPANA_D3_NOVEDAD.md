# Campaña D3 — Novedad Científica

## Objetivo
Resolver D3 (novedad) de UNRESOLVED a RESOLVED con evidencia.

## Contexto
D3 = novedad de las ideas generadas por el sistema. Actualmente UNRESOLVED.
El sistema genera ideas via LLM, pero no se ha medido si son realmente novedosas
respecto al estado del arte.

## Pasos

### 1. Localizar métricas de novedad existentes
```bash
cd criba-blackforge
grep -rn "novedad\|novelty\|novel" src/ tests/ docs/ --include="*.py" --include="*.md" | head -30
```

### 2. Identificar qué se mide actualmente
- Buscar en tests/astra_canon/, tests/intelligence/, tests/unit/.
- Buscar en src/criba/intelligence/.

### 3. Definir métrica de novedad
- Comparar ideas generadas vs corpus de referencia.
- Usar embedding similarity o lexical overlap.
- Definir umbral de novedad.

### 4. Implementar medición (si no existe)
- Crear test que mida novedad de un conjunto de ideas.
- Ejecutar con corpus de referencia.
- Registrar métrica.

### 5. Ejecutar campaña
- Generar N ideas con el sistema.
- Medir novedad vs corpus.
- Registrar distribución de scores de novedad.

### 6. Resolver D3
- Si métrica ≥ umbral → D3 = RESOLVED.
- Si métrica < umbral → D3 = RESOLVED (con nota de bajo rendimiento) o BLOCKED.
- Registrar evidencia.

## Archivos esperados
- tests/intelligence/test_*novelty*.py (a crear si no existe)
- src/criba/intelligence/* (a modificar si falta métrica)

## Evidencia requerida
- Métrica de novedad definida y medida.
- Distribución de scores.
- Umbral y justificación.
- Tests pasando.
