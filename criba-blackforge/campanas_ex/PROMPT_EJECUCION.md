# PROMPT DE EJECUCIÓN — Campañas EX / STANDARD / D3 / D4 / D6 / G3

## Instrucción para el modelo

Eres un ingeniero de software senior. Tu tarea es ejecutar las campañas de extensión
científica del proyecto CRIBA × BLACKFORGE × SUPRA que están en la carpeta
`campanas_ex/` de este repositorio.

### Contexto del proyecto
- Repo: C:/ASTRA_WORK/Criba-Blackforge-Supra
- Branch actual: main
- MVP: PRODUCT_ACCEPTED (completado)
- 58 tarjetas CIERRE cerradas
- 18 tarjetas EX (extensión) pendientes
- STANDARD=DISABLED, D3/D4/D6=UNRESOLVED, G3=NOT_VERIFIED

### Archivos de referencia
- `campanas_ex/README.md` — estructura y reglas
- `campanas_ex/INSTRUCCIONES_APERTURA.md` — cómo empezar
- `campanas_ex/INSTRUCCIONES_CIERRE.md` — cómo cerrar
- `campanas_ex/estado/ESTADO_CAMPANAS.json` — estado operativo
- `campanas_ex/CAMPANA_EX_FULL.md` — campaña EX00–EX17
- `campanas_ex/CAMPANA_STANDARD.md` — activación STANDARD
- `campanas_ex/CAMPANA_D3_NOVEDAD.md` — novedad
- `campanas_ex/CAMPANA_D4_DIVERSIDAD.md` — diversidad funcional
- `campanas_ex/CAMPANA_D6_BENEFICIO.md` — beneficio adaptativo
- `campanas_ex/CAMPANA_G3_ANTIGOODHART.md` — Anti-Goodhart
- `C:/ASTRA_WORK/CBS_CIERRE_INGENIERIA_EFECTIVA_20261024/CBS_CIERRE_INGENIERIA_EFECTIVA_20261024/03_TARJETAS_EXTENSION/` — fichas originales EX00–EX17

### Tu tarea
1. Lee `campanas_ex/README.md` y `campanas_ex/INSTRUCCIONES_APERTURA.md`.
2. Lee `campanas_ex/estado/ESTADO_CAMPANAS.json`.
3. Lee la ficha EX correspondiente en `03_TARJETAS_EXTENSION/`.
4. Ejecuta las campañas en el orden recomendado del estado JSON.
5. Para cada campaña:
   a. Crea branch `campana/ex-XX-nombre`.
   b. Ejecuta los pasos de la campaña.
   c. Verifica con tests.
   d. Actualiza estado.
   e. Commit y push.
   f. Crea PR.
6. No activar STANDARD, executor real, ni proveedor real sin aprobación explícita.
7. Distinguir PLANNED de EXECUTED de SCIENTIFICALLY_VALIDATED.
8. Registrar evidencia en `campanas_ex/evidencia/EX##/`.

### Orden de ejecución recomendado
EX00 → EX01 → EX02 → EX03 → EX04 → EX05 → EX06 → EX07 → EX08 → EX11 → EX09 → EX10 → EX12 → EX13 → EX14 → EX15 → EX16 → EX17 → D3_NOVEDAD → D4_DIVERSIDAD → D6_BENEFICIO → G3_ANTIGOODHART → STANDARD

### Reglas
- Una campaña a la vez.
- No mezclar campañas.
- TDD: test que falla antes de implementar.
- No ajustar umbrales para aparentar éxito.
- Registrar fallos, no ocultarlos.
- Evidencia verificable (logs, hashes, outputs).

### Comandos base
```bash
cd C:/ASTRA_WORK/Criba-Blackforge-Supra
git status --short  # debe estar vacío
cd criba-blackforge
.venv/Scripts/python.exe -m pytest tests/recovery/ -q -p no:randomly  # baseline: 21 passed
```

### Inicio
Empieza por EX00. Lee la ficha, crea el branch, ejecuta.
