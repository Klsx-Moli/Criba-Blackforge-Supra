# CRIBA BLACKFORGE — CHECKPOINT

**Fecha:** 2026-08-25 (verano romance, UTC+02:00)
**Rama:** feat/gguf-semantic-integration
**Commit:** cd49109
**Tests:** 500 pasando, 0 fallos
**Portable:** dist/CRIBA-Blackforge/ (CRIBA.exe + BLACKFORGE.exe + CRIBA-CLI.exe)

> ⚠️ **Sección histórica — no borrar.** Describe el estado de 2026-08-25.
> Para el estado verificado el 2026-11-21, ver la sección
> "Checkpoint 2026-11-21" al final de este documento.

---

## Estado del plan de fases

| Fase | Módulo | Estado | Tests |
|------|--------|--------|-------|
| P1 Fundación | engine, context, task, constraints, output | ✅ Existente | 347 |
| P2 Personas | personas.py | ✅ Existente | — |
| P3 Ensemble | ensemble.py | ✅ Activo | 22 |
| P4 Cadena 6 fases | chain.py | ✅ Activo | 25 |
| P5 Adversarial | adversarial_self.py | ✅ Activo | 17 |
| P6 Blackforge | blackforge_* | ✅ Existente | — |
| P7 Gates | gates.py | ✅ Activo | — |
| P8 Logging | logging.py | ✅ Activo | 26 |
| P9 Latencia | latency.py | ✅ Activo | 20 |
| P10 Métricas | metrics.py | ✅ Activo | 15 |
| Integración | hybrid.py | ✅ Activo | 20 |
| Persistencia | storage (chain) | ✅ Activo | 8 |
| GUI | actions (híbrido) | ✅ Activo | — |

## Feature flags activos

```python
FEATURES = {
    "context_layer_v2": False,
    "compound_personas": False,
    "ensemble_analysis": True,
    "six_stage_chain": True,
    "adversarial_self_reinforcement": True,
    "human_review_gates": True,
    "blackforge_extended_context": True,
    "deterministic_validation": True,
    "structured_logging": True,
    "quality_feedback_loop": True,
}
```

## Ciclo evolutivo operativo

```
ideas → ensemble (P3) → cadena (P4) → adversarial (P5)
   ↓                                       ↓
conocimiento ← métricas (P10) ← logging (P8)
   ↓
nuevas ideas (mejora continua)
```

## Verificación (ejecutada esta sesión)

- `pytest tests/unit/ -q` → 500 passed, 0 failures
- `CRIBA-CLI.exe --help` → exit 0
- GUI offscreen → arranca, navHibrido presente
- `run_hybrid(packet)` → stages=['ensemble','chain','adversarial'], confidence=confirmed
- Portable rebuild → CRIBA.exe (8.7MB), BLACKFORGE.exe (8.7MB), CRIBA-CLI.exe (9.5MB)

## Próximas acciones recomendadas

1. **Tests GUI offscreen del pipeline híbrido** — verificar flujo completo con clicks
2. **LLM real** — activar backend GGUF vía llama.cpp para redacción semántica
3. **Pantalla de resultados híbridos** — expandir GUI para mostrar acuerdos, emergentes, tesis/antítesis

---

# Checkpoint 2026-11-21

**Rama de trabajo:** `hermes/cbs-receipt-fix-20261121`
**Línea base (TARGET_SHA):** `5978d33b2fcd23def901ba96b855036f0203cd39` (rama `main`)
**Commits propios:** `d79de53`, `6b6cb88`, `383d53c` — los tres en la rama de
trabajo. **Cero commits en `main`.**
**BLACKFORGE:** HARD_PAUSE respetado. No iniciado, no modificado, no simulado.

## Verificación ejecutada (no leída, ejecutada)

| Comprobación | Resultado |
|---|---|
| `tests/unit` completo con SUPRA arriba | **1607 passed, 19 skipped, 0 failed** (541.50 s) |
| `test_scientific_cycle.py` | 11 passed |
| `test_gui_inventar` + `test_gui_query_sync` | 8 passed |
| `test_nueva_idea_aviso.py` (nuevo) | 5 passed |
| `test_gui_inventar` aislado ×8 | 8/8 passed → no es flaky |
| `.exe` empaquetado, prueba causal | banner real + 0 AttributeError |

## Defectos corregidos

| Commit | Defecto | Prueba causal |
|---|---|---|
| `d79de53` | `KeyError: 'execution_status'` en el receipt de `scientific_cycle` | base falla, fix pasa |
| `6b6cb88` | `AttributeError: '_Signals' object has no attribute 'finished'` en `model_settings_dialog.py:450` | log: 3 → 0 |
| `383d53c` | "Definir problema" con campo vacío cerraba el diálogo en silencio | banner en pantalla |
| `6f3b746` | `criba hybrid` sin cablear: subcomando en parser sin rama en `main()` → "Comando desconocido: hybrid" | RED→GREEN; CLI real empaquetada exit 0 |

## Builds finales (post-`6f3b746`, VERIFIED_BY_EXECUTION)

- `dist/CRIBA-Blackforge/`: `CRIBA.exe` + `BLACKFORGE.exe` + `CRIBA-CLI.exe`
  (spec `CRIBA-Blackforge.spec`, catálogo `imports/blackforge_v2` y `data/`
  empaquetados). `CRIBA-CLI.exe hybrid --query "边缘"` → HybridResult JSON con
  `final_confidence: confirmed`, exit 0. `CRIBA-CLI.exe blackforge --query ...`
  → packet `blackforge_headless_packet` status OK, exit 0.
- `dist/CribaShadow/CribaShadow.exe`: `verify_shadow_bundle_journey.py` →
  **BUNDLED_E2E_PASS**, `project_id astram2605ea28268`, GET 200, restore
  tras reinicio real del proceso, exit 0.
- Tests de contrato del fix hybrid: `test_hybrid_cli_contract.py` 3 passed;
  regresión `test_hybrid.py` + `test_blackforge_agentic.py` 37 passed.

## M2 / M3

- **M2** VERIFICADO — `test_m2_vertical_slice_e2e.py` 8 passed en worktree aislado,
  dossier `dossier-8c3f36b72c57472ab2bca7060c34ea2d`, transporte REAL_HTTP, GET 200.
- **M3** VERIFICADO — `test_m3_restart_replay_e2e.py` 15 passed, el mismo
  `project_id` sobrevive al reinicio real del proceso.

## Sigue abierto

1. **Flujo GUI completo hasta generar ideas: NO VERIFICADO.** El `type_text` por
   PostMessage no llega al `QTextEdit`; la escalada a `foreground` está bloqueada
   por falta de consentimiento. Verificado el rechazo del campo vacío, no el
   recorrido hasta el dossier.
2. **`desktop_visual_acceptance`: NOT_VERIFIED.** Evidencia por UIAutomation y
   log, no inspección visual humana. `vision_analyze` estuvo caído (HTTP 404).
3. **Superioridad de CRIBA: `NOT_ESTABLISHED`** en utilidad global
   (Art. 26). Establecido solo en originalidad percibida.
4. **Cambios ajenos sin commitear en `main`** (14 elementos): inventariados,
   copiados byte a byte, **no modificados**. Requieren decisión del propietario.
5. **Sonda `LocalLlamaInterpreter`:** `passed=False`,
   `schema_response_rate 0.25`, `correct_abstention_rate 0.33`. El GGUF no
   sostiene el contrato JSON.
6. **Revisión ASTRA: BLOQUEADA.** No disponible en esta sesión. Lo entregado es
   autorrevisión, no revisión independiente.

## Siguiente paso exacto

Autorizar `delivery_mode: foreground` en el diálogo "Nueva idea" y teclear el
problema base → generar ideas → ejecutar en SUPRA → recuperar dossier por GET.
Eso cierra M2/M3 por GUI, que es lo único que falta para el recorrido completo.
