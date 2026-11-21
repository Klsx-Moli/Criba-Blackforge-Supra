# ESTADO DE BRAZOS Y BLOQUEOS — PROMPT 10

**Fecha:** 2026-10-22 · **SHA observado:** `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0`
**Entorno:** Python 3.11.15 (`criba-blackforge/.venv/Scripts/python.exe`), Windows 11.

Vocabulario: `FACT`, `INFERENCE`, `NOT_EXECUTED`, `NOT_ACCESSIBLE`. Estados admitidos: `EXECUTABLE`, `BLOCKED`, `NOT_VERIFIED`.

---

## 1. Brazo A_DIRECT

| Campo | Valor | Clasificación |
|---|---|---|
| Código de ejecución | `benchmarks/innovation/harness.py` `run_condition()`; condición `A_DIRECT` con plantilla «Genera N soluciones innovadoras para: {problema}» | FACT |
| Dependencia real | `model_fn` (param inyectable) | FACT (`inspect.signature`) |
| Backend necesario | LLM (Ollama local / proxy Hermes / cloud) | FACT |
| Disponibilidad de `model_fn` | **ninguno**: Ollama 11434→000, proxy 8645→000, SUPRA 8000→000, 9479→000; `CRIBA_EXTERNAL_API_KEY` ausente | FACT (curl 2026-10-22) |
| Evidencia de ejecución efectiva | `A_DIRECT sin model_fn → status UNAVAILABLE` | FACT |
| Limitaciones | sin backend no hay generación; **no** se simula | — |
| **Estado** | **`BLOCKED`** (sin backend LLM; no es observación) | FACT |

## 2. Brazo B_STRONG_PROMPT

| Campo | Valor | Clasificación |
|---|---|---|
| Código de ejecución | `harness.py` `run_condition()`; plantilla de prompt fuerte en `harness.py:30` | FACT |
| Dependencia real | `model_fn` | FACT |
| Backend necesario | LLM | FACT |
| Disponibilidad | **ninguno** (mismos 000) | FACT |
| Evidencia de ejecución efectiva | **no ejecutado** | NOT_EXECUTED |
| **Estado** | **`BLOCKED`** (sin backend LLM; no es observación) | FACT |

## 3. Brazo C_CRIBA

| Campo | Valor | Clasificación |
|---|---|---|
| Código de ejecución | `criba_fn()` en `benchmarks/innovation/criba_adapter.py:18`; `select_finalists` en `criba/diversity_selector.py` | FACT |
| Dependencia real | `criba_fn` (inyectable), determinista offline | FACT |
| Evidencia de ejecución efectiva | 4 candidatos generados; reproducible por seed (hash idéntico 2 corridas) | FACT |
| Estado | **`EXECUTABLE`** (tratamiento) | FACT |

---

## 4. Contraste de superioridad

**`FACT`:** los brazos A y B están `BLOCKED` por falta de backend LLM. El único contraste ejecutable es **C_CRIBA contra sí mismo bajo variaciones controladas** (semillas).

**Consecuencia:** el **contraste de superioridad previsto (CRIBA vs prompt fuerte congelado) NO es ejecutable** en el estado actual.

**Regla aplicada:** los experimentos de reproducibilidad interna de C_CRIBA **quedan separados** del contraste de superioridad. No se usan para concluir ventaja **ni** ausencia de ventaja comparativa. Un brazo bloqueado **no constituye una observación experimental**.

**No se hizo:** instalar paquetes, conectar servicios, solicitar credenciales, cambiar proveedores ni alterar configuración para habilitar brazos.

---

## 5. Lista exacta de bloqueos que impiden ejecutar el piloto

| ID | Bloqueo | Evidencia | Estado |
|---|---|---|---|
| B1 | Dataset de 30 problemas inexistente (solo 10) | `problems_smoke.json` = 10 | FACT |
| B2 | Sin criterio de resolución por problema | claves `{id,perfil,texto}`; endpoint 1/0 no evaluable | FACT |
| B3 | Sin construcción de 4 candidatos con etiquetas de control/positivo/negativo | `criba_fn` devuelve 4 sin etiquetas | FACT |
| B4 | Sin instrumento de evaluación funcional independiente del scorer | harness mide diversidad/estructura | FACT |
| B5 | Preregistro no aprobado | `PREREGISTRO_BORRADOR` estado NO APROBADO | FACT |
| B6 | Ledger definitivo no creado / esquema en CONFLICT | `CONCILIACION_LEDGER` | FACT |
| B7 | Brazos A y B bloqueados (sin backend LLM) | curl 000 | FACT |
| B8 | F3/F4/F5: ranking no discrimina; contabilidad incompleta | `DEFECTOS_F2_F5` | FACT |

---

## 6. Estado

```
A_DIRECT_STATUS          = BLOCKED (sin backend LLM)
B_STRONG_PROMPT_STATUS   = BLOCKED (sin backend LLM)
C_CRIBA_STATUS           = EXECUTABLE (tratamiento; sin contraste de superioridad)
PILOT_EXECUTION_ALLOWED  = NO
```

**No se declara superioridad ni ausencia de superioridad.** `BLOCKED` y `NOT_EXECUTED` no equivalen a «CRIBA no funciona» ni a «CRIBA no es superior».
