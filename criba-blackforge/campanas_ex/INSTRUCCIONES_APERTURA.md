# Instrucciones de Apertura — Campañas EX

## Antes de empezar cualquier campaña

1. Confirmar que estás en `main` con working tree limpio:
   ```bash
   cd C:/ASTRA_WORK/Criba-Blackforge-Supra
   git status --short  # debe estar vacío
   git log -1 --oneline  # debe ser el último commit de main
   ```

2. Confirmar que el venv funciona:
   ```bash
   cd criba-blackforge
   .venv/Scripts/python.exe -m pytest tests/recovery/ -q -p no:randomly
   # Esperado: 21 passed
   ```

3. Leer el estado actual de campañas:
   ```bash
   cat campanas_ex/estado/ESTADO_CAMPANAS.json
   ```

4. Leer la ficha EX correspondiente en:
   `C:/ASTRA_WORK/CBS_CIERRE_INGENIERIA_EFECTIVA_20261024/CBS_CIERRE_INGENIERIA_EFECTIVA_20261024/03_TARJETAS_EXTENSION/EX##.md`

5. Crear branch de trabajo:
   ```bash
   git checkout -b campana/ex-XX-nombre
   ```

6. Registrar inicio en estado:
   ```json
   {"campana": "EX00", "status": "DOING", "started_at": "YYYY-MM-DDTHH:MM:SS", "writer": "modelo"}
   ```

## Reglas de ejecución

- Una campaña a la vez. No mezclar.
- No modificar código de producción sin test que falle antes (TDD).
- No activar STANDARD, executor real, ni proveedor real sin aprobación explícita.
- Cada cambio debe tener test de regresión.
- Registrar cada comando ejecutado con exit code y duración.
- Si un test falla, registrar el fallo. No ocultarlo ni ajustar umbrales.
- Distinguir PLANNED de EXECUTED de SCIENTIFICALLY_VALIDATED.

## Dónde escribir evidencia

- `campanas_ex/evidencia/EX##/` — logs, outputs, screenshots.
- `campanas_ex/estado/ESTADO_CAMPANAS.json` — estado operativo.
- Commits en branch `campana/ex-XX-nombre`.
