# Campañas EX — Extensión Científica (PROGRAM_FULL_CLOSED)

## Propósito
Esta carpeta contiene campañas ejecutables para cerrar el alcance extendido (PROGRAM_FULL_CLOSED)
del proyecto CRIBA × BLACKFORGE × SUPRA. Cada campaña es independiente y puede ser ejecutada
por cualquier modelo/agente que siga las instrucciones de apertura y cierre.

## Alcance
- EX00–EX17: 18 tarjetas de extensión científica/BLACKFORGE.
- STANDARD: activación del estándar canónico (actualmente DISABLED).
- D3/D4/D6: novedad, diversidad funcional, beneficio adaptativo (actualmente UNRESOLVED).
- G3: Anti-Goodhart readiness (actualmente NOT_VERIFIED).

## Prerequisitos
- MVP completado (PRODUCT_ACCEPTED=true) — VERIFICADO.
- Repo en main, branch `main`, working tree limpio.
- Python 3.11 venv en `criba-blackforge/.venv/`.
- PyInstaller 6.22.2 instalado.
- Tests base pasando (recovery 21, shadow identity 18).

## Estructura
```
campanas_ex/
├── README.md                          (este archivo)
├── INSTRUCCIONES_APERTURA.md          (cómo empezar una campaña)
├── INSTRUCCIONES_CIERRE.md            (cómo cerrar y verificar)
├── CAMPANA_EX_FULL.md                 (todas las EX00-EX17 en lotes)
├── CAMPANA_STANDARD.md                (activación STANDARD con evidencia)
├── CAMPANA_D3_NOVEDAD.md              (novedad científica)
├── CAMPANA_D4_DIVERSIDAD.md           (diversidad funcional)
├── CAMPANA_D6_BENEFICIO.md            (beneficio adaptativo)
├── CAMPANA_G3_ANTIGOODHART.md         (Anti-Goodhart readiness)
└── estado/                            (estado operativo de campañas)
    └── ESTADO_CAMPANAS.json
```

## Reglas
1. No mezclar campañas. Una campaña a la vez.
2. Cada campaña produce evidencia verificable (tests, logs, hashes).
3. No activar STANDARD, executor real, ni proveedor real sin aprobación explícita.
4. Distinguir PLANNED de EXECUTED de SCIENTIFICALLY_VALIDATED.
5. No inventar resultados. Si un test falla, registrar el fallo, no ocultarlo.
