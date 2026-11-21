# Campaña G3 — Anti-Goodhart Readiness

## Objetivo
Verificar G3 (Anti-Goodhart) de NOT_VERIFIED a VERIFIED sin activar.

## Contexto
G3 = el sistema no optimiza métricas proxy en lugar de la métrica real.
Anti-Goodhart protocol existe (ANTI_GOODHART_G3_PROTOCOL.md, ANTI_GOODHART_RUNTIME.md).
Actualmente NOT_VERIFIED.

## Pasos

### 1. Leer protocolo existente
```bash
cd criba-blackforge
cat docs/ANTI_GOODHART_G3_PROTOCOL.md
cat docs/ANTI_GOODHART_RUNTIME.md
```

### 2. Verificar tests existentes
```bash
.venv/Scripts/python.exe -m pytest tests/astra_canon/test_anti_goodhart_runtime.py -q -p no:randomly
```

### 3. Verificar que métricas no son optimizadas como proxy
- Revisar scoring en src/criba/intelligence/scoring/.
- Verificar que no hay gaming de métricas.
- Verificar que los tests de anti-goodhart cubren los casos críticos.

### 4. Ejecutar campaña de verificación
- Ejecutar todos los tests anti-goodhart.
- Verificar que no hay métrica que se pueda "hackear" trivialmente.
- Registrar gaps.

### 5. Resolver G3
- Si todos los tests pasan y no hay gaps críticos → G3 = VERIFIED.
- Si hay gaps → registrar y crear fichas hija.

## Evidencia requerida
- Tests anti-goodhart pasando.
- Revisión de métricas (no proxy optimization).
- Gaps documentados.
