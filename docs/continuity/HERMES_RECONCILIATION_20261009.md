# Reconciliación Hermes → GitHub / CRIBA–SUPRA / 2026-10-09

**Rama de trabajo:** `chatgpt/reconcile-hermes-deep-20261009` (base exacta: `chatgpt/shadow-exe-journey-20261008` @ `14ec9d28077197a8e5038a52c87265a6a6997c7e`).
**Rama `main` examinada:** `15bc237be5555fcc38bc8a25f80724473c13435b`.
**Alcance:** integración selectiva y preservación de pruebas; **sin merge a main**, sin activación de BLACKFORGE, sin cambios al motor científico causal ASTRA.
**Evidencia:** `FACT` = GitHub consultado directamente; `REPORTED_BY_HERMES` = inventario local que esta sesión remota no puede corroborar en el PC; `NOT_EXECUTED` = no se ha probado aún en la rama reconciliada.

## Descubrimiento y clasificación

- `FACT`: cinco ramas `hermes/local-snapshot-20261009-{convergence-audit,main-baseline,dossier,pr9-persistence,eval-cbs}`, más `hermes/audit-snapshot-20261009`, están publicadas. El inventario de Hermes afirma 7 worktrees principales, otros 2 MSYS y que no quedaban commits locales inéditos. Es **REPORTED_BY_HERMES**, no una comprobación independiente de los discos locales.
- `FACT`: las ramas snapshot son *un commit de adición de archivo* sobre su base respectiva. Cuatro incorporan `criba-blackforge/verification/blackforge_selector_report.json` (~1133 líneas cada una); `dossier` incorpora `scripts/no_leak_plugin.py` (5 líneas). El informe de auditoría incorpora `docs/continuity/HERMES_LOCAL_GITHUB_SNAPSHOT_20261009.md` (376 líneas). Los reports catalog/safety que cita Hermes ya están en las ramas base, **no son cambios nuevos** en las comparaciones de instantáneas.
- `FACT`: la rama `hermes/deep-execution-20261005` diverge de la línea `#13 → #14` después de `2dc009485848b55ada5009986fe7e78d67c31ade`: **9 commits exclusivos**, **16 rutas modificadas** respecto a ese ancestro.
- `FACT`: la rama `hermes/cbs-continuity-memory-20261005` diverge del mismo ancestro: **4 commits**, **12 rutas** de documentación/continuidad. Corresponde a PR #12; sus descripciones de contratos son fuentes históricas, no pruebas de funcionamiento.
- `FACT`: `hermes/cbs-pr8-11-convergence-audit` contiene **13 documentos de auditoría** ausentes de la rama #14. Incluyen una recomendación de integrar BLACKFORGE #8/#9/#11. Esa recomendación histórica NO prevalece sobre `HARD_PAUSE`.

### Cadena de PR y ramas

| Unidad | Base actual | Decisión |
| --- | --- | --- |
| #8, #9, #11 | main | Mantener **sin merge**, BLACKFORGE `HARD_PAUSE`. Preservar el código en sus ramas, revisarlo sólo sin ejecutarlo. |
| #10 | hermes/astra/shadow-supra-20261002 | Conservar; descendiente de main, incluye Shadow/SUPRA e intérprete. |
| #12 | #10 | Posponer documentos de continuidad; verificar integridad de corpus antes de elevarlos a canon. |
| #13 | #10 | Conservar la configuración de instancia única/identidad SUPRA y evaluación descriptiva sin resultados reales. |
| #14 | #13 | Base técnica acumulativa: CI del SHA original verde; E2E EXE ≠ revisión visual humana ni ventaja experimental. |
| deep-execution (9 commits) | #10 | **Seleccionar cambios uno a uno**; no copiar archivos completos sobre #14 ni fusionar sin validar invariantes. |
| snapshots de 2026-10-09 | sus respectivas ramas | Conservar evidencias y trazabilidad; no insertar reportes duplicados ni código BLACKFORGE en la rama de producto. |

**Corrección de una conclusión del documento antiguo:** para la cadena #10→#13→#14, la comparación `main...#14` verificó `ahead_by=55`, `behind_by=0` sobre `main` `15bc237`. La rama es descendiente lineal de main; **no hace falta reescribir/force-rebasear las PR existentes por obligación Git**. Sí hacen falta una revisión de integración y CI en el objetivo final `main`, especialmente porque el workflow de Windows anterior filtraba ramas temporales por nombre.

## Código reconciliado selectivamente en esta rama

1. **Completitud de modelos locales:** portada de `hermes/deep-execution-20261005` la comprobación de `done_reason == "length"` (Ollama) y `finish_reason == "length"` (llama.cpp) en `criba.model_runtime._generate_once`. Las salidas truncadas no pasan por resultado completo aunque el JSON aparente válido. No se modifica la política científica de ASTRA ni el intérprete externo.
2. **Regresión asociada:** copiado con procedencia del mismo commit Hermes `tests/unit/test_model_runtime_completion_status.py`, que cubre truncamiento, respuesta completa/legada y recuperación determinista ante error. Ejecución pendiente de CI en la PR reconciliada.
3. **CI Windows:** workflow actualizado para dispararse en PR hacia `main` o la rama #14, entre otras bases de cadena, por rutas de código relevantes, y ejecutar **siempre** el smoke y recorrido GUI→SUPRA→persistencia→reinicio cuando se active. Ya no depende de un nombre exacto de rama de origen para ejecutar el gate. Evidencias todavía etiquetadas como capturas de `QWidget.grab()`, no auditoría humana.

### Qué se ha conservado pero NO se ha aplicado automáticamente

- `deep-execution`: cambios en `ui/actions.py`, `shadow_window.py`, `model_settings_dialog.py`, `supra_dossier.py`, pruebas de selección/recuperación e integración M2; requieren reconciliar sus interacciones con el código más nuevo de la PR #14. La propuesta de mejora asíncrona crea un worker desde otro worker y modifica un paquete compartido; antes de portarla, evaluar afinidad Qt, cancelación, orden de callbacks, fallback y persistencia de provenance, más los tests correspondientes. **No llamar BUG confirmado sin reproducción**.
- `#12`: fuentes literales/estado histórico que pueden contener `CORPUS_INTEGRITY=INCOMPLETE`. Conservar la rama como evidencia separada hasta resolver referencias incompletas.
- Snapshots: informes de selector, seguridad/catálogo BLACKFORGE y `no_leak_plugin.py`. Son materiales para auditoría, no para habilitar BLACKFORGE.
- `#8/#9/#11`: implementar no equivale a activar; en esta fase no se portan. Validar semántica de authorization/broker y storage legacy únicamente cuando se quite explícitamente `HARD_PAUSE`.

## Gates pendientes

- `NOT_EXECUTED` en esta rama al redactar: CI CRIBA/SUPRA en HEAD reconciliado; Windows EXE E2E en HEAD reconciliado; aceptación visual humana 1024×697 y pantallas normales; prueba experimental CRIBA vs LLM directo.
- Problemas conocidos previos: controles BLACKFORGE de Shadow aún muestran rutas de arranque; deben cambiar a `En construcción` antes del release. En 1024×697 el centro necesita validación visual de legibilidad. `supra/LICENSE` termina en sección 6, requiere decisión del titular antes de distribución pública.
- La suite no demuestra novedad, generalización ni mejora sobre un LLM directo. `D3/D4/D6/D8` siguen no acreditados, `AntiGoodhart` OFF.

## Fuentes primarias

- [Informe de sincronización Hermes](https://github.com/Klsx-Moli/Criba-Blackforge-Supra/blob/hermes/audit-snapshot-20261009/docs/continuity/HERMES_LOCAL_GITHUB_SNAPSHOT_20261009.md)
- [Rama deep-execution](https://github.com/Klsx-Moli/Criba-Blackforge-Supra/tree/hermes/deep-execution-20261005)
- [Auditoría de convergencia](https://github.com/Klsx-Moli/Criba-Blackforge-Supra/tree/hermes/cbs-pr8-11-convergence-audit/docs)
- [PR #10](https://github.com/Klsx-Moli/Criba-Blackforge-Supra/pull/10)
- [PR #12](https://github.com/Klsx-Moli/Criba-Blackforge-Supra/pull/12)
- [PR #13](https://github.com/Klsx-Moli/Criba-Blackforge-Supra/pull/13)
- [PR #14](https://github.com/Klsx-Moli/Criba-Blackforge-Supra/pull/14)

**No fusionar con main ni publicar release** hasta confirmar CI del SHA reconciliado, revisión manual de Shadow y alcance decidido sobre BLACKFORGE. Las ramas originales quedan intactas.
