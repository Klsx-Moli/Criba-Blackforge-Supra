# Instrucciones de Cierre — Campañas EX

## Antes de cerrar una campaña

1. Ejecutar todos los tests afectados:
   ```bash
   cd criba-blackforge
   .venv/Scripts/python.exe -m pytest tests/ -q -p no:randomly --timeout=120
   ```

2. Verificar que no hay regresiones en tests existentes (comparar con baseline: 39 passed en recovery+shadow).

3. Verificar mypy en archivos modificados:
   ```bash
   .venv/Scripts/python.exe -m mypy src/criba/<archivos_modificados> --no-error-summary
   ```

4. Verificar git diff (solo cambios de la campaña):
   ```bash
   git diff --stat
   git diff
   ```

5. Actualizar estado:
   ```json
   {"campana": "EX00", "status": "DONE_VERIFIED", "evidence": ["test X passed", "log Y"], "completed_at": "YYYY-MM-DDTHH:MM:SS"}
   ```

6. Commit y push:
   ```bash
   git add -A
   git commit -m "campana(EX##): descripcion corta"
   git push origin campana/ex-XX-nombre
   ```

7. Crear PR hacia main:
   ```bash
   gh pr create --base main --head campana/ex-XX-nombre --title "EX##: descripcion" --body "..."
   ```

8. Esperar CI verde antes de mergear.

## Criterio de DONE_VERIFIED

- Tests nuevos pasan.
- Tests existentes no regresionan.
- mypy limpio en archivos modificados.
- Evidencia documentada (logs, hashes, outputs).
- No se activó STANDARD, executor real, ni proveedor real sin aprobación.

## Criterio de BLOCKED

- Si un test falla y no se puede resolver en 3 intentos → BLOCKED_TECHNICAL.
- Si requiere aprobación externa (proveedor, STANDARD, executor) → PENDING_APPROVAL.
- Si el alcance es mayor de lo estimado → crear ficha hija BUG-xxx y reestimar.
