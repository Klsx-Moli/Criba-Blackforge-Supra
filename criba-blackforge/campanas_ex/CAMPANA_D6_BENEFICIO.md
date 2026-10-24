# Campaña D6 — Beneficio Adaptativo

## Objetivo
Resolver D6 (beneficio adaptativo) de UNRESOLVED a RESOLVED con evidencia.

## Contexto
D6 = las ideas generadas por el sistema producen beneficio medible
respecto a no usar el sistema (baseline).
Actualmente UNRESOLVED.

## Pasos

### 1. Localizar métricas de beneficio existentes
```bash
cd criba-blackforge
grep -rn "beneficio\|benefit\|adaptive\|adaptativo" src/ tests/ docs/ --include="*.py" --include="*.md" | head -30
```

### 2. Definir baseline
- ¿Qué pasa sin el sistema? (ideas aleatorias, ideas humanas, no ideas).
- Definir métrica de comparación.

### 3. Diseñar experimento
- Grupo control: sin sistema.
- Grupo experimental: con sistema.
- Métrica: calidad de ideas (según criterio definido).

### 4. Ejecutar experimento (con proveedor simulado)
- Generar ideas con sistema (SUPRA_USE_MODEL=false).
- Generar ideas baseline (aleatorias o sin sistema).
- Comparar métricas.

### 5. Resolver D6
- Si beneficio > 0 con significancia → D6 = RESOLVED.
- Registrar evidencia.

## Evidencia requerida
- Baseline definido.
- Experimento ejecutado.
- Métrica de beneficio medida.
- Significancia estadística.
- Tests pasando.
