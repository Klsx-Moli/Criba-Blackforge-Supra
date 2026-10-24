# Campaña STANDARD — Activación del Estándar Canónico con Evidencia Científica

## Objetivo
Activar STANDARD (actualmente DISABLED) con evidencia científica suficiente.
STANDARD es el modo de operación canónico del sistema que requiere validación
de las métricas D3 (novedad), D4 (diversidad funcional) y D6 (beneficio adaptativo).

## Prerequisitos
- D3, D4, D6 deben estar RESOLVED (no UNRESOLVED).
- G3 Anti-Goodhart debe estar VERIFIED.
- Piloto (EX12) debe estar completado con resultados positivos.
- Prerregistro (EX13) debe estar completado.

## Pasos

### 1. Verificar prerequisitos
```bash
cd criba-blackforge
grep -r "STANDARD" src/criba/ | head
grep -r "STANDARD=DISABLED\|STANDARD = DISABLED" . --include="*.py" --include="*.md" | head
```

### 2. Localizar el gate de STANDARD
```bash
grep -rn "STANDARD" src/ tests/ docs/ | grep -i "disabled\|enabled\|gate\|standard=" | head -20
```

### 3. Verificar que D3/D4/D6 están RESOLVED
- Leer resultado de campañas D3_NOVEDAD, D4_DIVERSIDAD, D6_BENEFICIO.
- Si alguno está UNRESOLVED → bloquear. No activar STANDARD.

### 4. Verificar G3
- Leer resultado de campaña G3_ANTIGOODHART.
- Si G3=NOT_VERIFIED → bloquear.

### 5. Si todos los prerequisitos cumplen:
- Cambiar STANDARD de DISABLED a ENABLED en el punto de configuración identificado.
- Ejecutar tests completos.
- Verificar que no hay regresión.
- Registrar evidencia.

### 6. Si algún prerequisito no cumple:
- Registrar bloqueo exacto.
- No activar STANDARD.
- Crear ficha hija con la brecha.

## Archivos a modificar (a identificar en paso 2)
- A determinar durante la campaña.

## Tests de verificación
```bash
.venv/Scripts/python.exe -m pytest tests/ -q -p no:randomly --timeout=120
```

## Evidencia requerida
- Prerequisitos verificados (D3/D4/D6 RESOLVED, G3 VERIFIED).
- Tests completos pasando.
- Diff mínimo y reversible.
- Commit y PR.
