# CBS F35 — Persistencia compartida de modelos: writers, diálogo y ruta autorizada

**Base auditada:** F34 `428b011cb502c927d8fdf9aa4c5af0bafbb2dbd4`.
**Rama de trabajo:** `campaign/cbs-final-32-40`; `main` y ASTRA fuera del alcance.
**No incluye** cambios en `model_runtime._assert_requested_model` ni copia commits del handoff.

## F35-R01 (P1, código corregido) — Colisión entre escritores de models.json.tmp

**Contrato:** dos interfaces CRIBA y BLACKFORGE comparten `model_config_path()` y deben poder escribir sin compartir un archivo temporal mutable entre procesos. El reemplazo tiene que ser atómico para cada escritor; CAS multiwriter es una propiedad **distinta**.

**Producer→persistencia→consumer:** `ModelSettingsDialog._save` o `_activate_ollama_choice` → `model_config.save_model_settings` → `models.json` → `load_model_settings` → `LocalLlamaInterpreter` / ventanas compartidas.

**Defecto comprobado estáticamente:** el código F34 usaba `temporary = target.with_suffix(target.suffix + ".tmp")`; todos los escritores empleaban exactamente el mismo `models.json.tmp`. Una concurrencia con dos writes completos antes de `os.replace` deja un único path: el primer `replace` elimina el source temporal y el segundo falla `FileNotFoundError`. Además el contenido intermedio puede mezclar escrituras.

**VERIFIED_BY_ME (reproducción aislada, no checkout):** ejecución Python con dos threads sincronizados en la frontera `os.replace`:
- Etapa antigua compartida: 1 path temporal, un writer `FileNotFoundError`, otro `ok`.
- Etapas `mkstemp` distintas: 2 paths, ambos `ok`, JSON final válido de uno de los writers.
Esto prueba la carrera del archivo temporal, pero NO ejecuta el módulo del repo ni demuestra ausencia de *lost update* lógico.

**Fix publicado:** `save_model_settings` crea `tempfile.mkstemp` único en el directorio de destino, serializa antes de crear el temporal, escribe y hace `flush`/`fsync`, `os.replace` a la ruta original, y elimina únicamente el temporal propio en `finally`. Rechaza reemplazar un symlink y conserva el fichero antiguo cuando `os.replace` falla. No importa credenciales ni toca modelos.

**Pruebas:** `test_model_config_atomic_writer.py`: barrera determinista para 2 escritores (debería fallar con la implementación antigua), rollback + limpieza sin borrar temporales ajenos, datos no JSON serializables, symlinks (skip sólo si Windows impide crearlos). **NOT_EXECUTED** en el repo/Windows.

## F35-R02 (P1, código corregido) — Dialogo guardaba configuración obsoleta o normalizada

**Contrato:** un editor modal de `models.json` no puede destruir cambios hechos por otro editor después de abrirlo, ni normalizar silenciosamente archivos corruptos, futuros o con campos desconocidos.

**Defecto real:** `ModelSettingsDialog.__init__` llamaba `load_model_settings()`, loader tolerante; `_save` llamaba directamente `save_model_settings(self.settings)`. No había comparación de disco al guardar. Existía protección F30 para activación Ollama, **pero no para el editor general**.

**Fix publicado:** `_read_shared_settings_snapshot` captura ruta y bytes iniciales (máximo 1 MiB), rechaza symlinks, formato antiguo/ambiguo según `_editable_model_settings_bytes`; antes de `_save` se vuelve a leer y se comparan path, bytes y seguridad. Si cambian, el diálogo permanece abierto y avisa sin modificar disco. `_save` usa la misma ruta fijada al abrir el diálogo.

**Pruebas:** `test_model_settings_dialog_stale.py`: dos editores abiertos sobre archivo ausente (no lost update entre los dos), archivo corrupto/futuro/oversized, modificación por otro editor tras abrir, cambio de `CRIBA_MODEL_CONFIG`, reader de tamaño limitado. Todo sin inferencia. **NOT_EXECUTED** por falta de PySide6 local.

## F35-R03 (P1, código corregido) — Ollama validaba A pero guardaba en B

**Contrato:** el consentimiento para activar un modelo Ollama en un archivo compartido A no autoriza sobrescribir otra ruta B.

**Defecto:** `_activate_ollama_choice` guardaba `config_path = model_config_path()`, comparaba los bytes de A antes/después del modal Qt, pero llamaba `save_model_settings(settings)` **sin pasar la ruta**. El save reconsultaba `CRIBA_MODEL_CONFIG`; si el entorno cambiaba durante el diálogo, podía escribir otro destino sin verificar.

**Fix:** antes de activar, el código valida `model_config_path()==config_path`, rechaza symlinks y llama `save_model_settings(settings, config_path)` con ruta fija. Se mantiene el guard de selección y bytes. Tests parametrizados con archivo inicial existente/no existente y cambio de variable de entorno **durante** el `QMessageBox.question`. Deberían fallar en F34 y proteger F35. **NOT_EXECUTED**.

## Límites y falsación residual

1. **OPEN P1**: comprobación de snapshot + `os.replace` NO constituye CAS/lock transaccional entre procesos. Sigue existiendo ventana TOCTOU posterior a la última comparación: un segundo editor puede reemplazar el archivo y luego ser sobrescrito. Requiere compare-and-swap real con lock cross-platform + versionado y tests multi-proceso antes de declarar conflicto resuelto.
2. **OPEN**: `_activate_ollama_choice` lee archivos potencialmente grandes antes del check; a diferencia del diálogo general todavía no tiene límite de lectura 1 MiB ni un snapshot de filesystem inmutable. Requiere acotación en un siguiente ciclo.
3. **OPEN**: la identidad real de GGUF en `model_runtime._assert_requested_model` no está probada mediante `/props.model_path`. El handoff remoto `4297b63971927d5254f6099479a3eccbeaf876f2` reconoce que el fix/test están **sin commitear en worktree local** separado. NO tocar ese worktree ni considerar el fix integrado.
4. No se han ejecutado llamadas HTTP a Hermes/Ollama, no se ha afirmado precio gratuito, ni se ha promovido resultado científico o banco local.
5. F31 Windows tuvo 46 FAIL / 2786 PASS / 20 SKIP, según Ernie; F34 pruebas correctoras y F35 siguen EVIDENCE_PENDING. No declarar green ni AUDIT COMPLETE.

## Evidencia clasificada

| Etiqueta | Qué se verificó |
|---|---|
| VERIFIED_BY_ME | SHAs/estado remoto por conector; experimento aislado de dos escritores de archivo temporal en Python |
| STATICALLY_INSPECTED | Rutas reales de save, UI general, activación Ollama, model config, tests y diff |
| REPORTED_BY_AGENT | Suite Windows F31 de Ernie, mypy, Ruff, Uvicorn, CRLF y worktrees |
| NOT_EXECUTED | pytest real F35, GUI PySide6, mypy/Ruff reales F35, CI de campaña |
| NOT_ACCESSIBLE | Windows actual del usuario, procesos Hermes/Ernie y sus cambios sin commitear |

## Gate F35 y sincronización segura

- Primero reconciliar cualquier informe Windows F34 en su **SHA fijo**; no mezclarlo con cambios F35 y no volver a arrancar dos suites completas en paralelo.
- Después en otro worktree nuevo del SHA final F35, con `git status` previo y sin sobrescribir ramas activas:
  - `python -m pytest -q tests/unit/test_model_config.py tests/unit/test_model_config_atomic_writer.py`
  - `python -m pytest -q tests/unit/test_model_settings_dialog.py tests/unit/test_model_settings_dialog_stale.py tests/unit/test_phase29_shadow_source_selector.py`
  - `python -m pytest -q tests/unit/test_functional_proposal_journey.py tests/unit/test_offline_intelligence_store_isolation.py tests/unit/test_chain_memory_lock_scope.py`
  - comprobar skip/xfail; Ruff, mypy contra baseline y `git diff --check`; en ninguna ruta usar modelos reales.
- Nunca `reset --hard`, `clean`, force push, merge main o despliegue; no reiniciar Uvicorn SUPRA. Hasta esas pruebas, F35 = **IMPLEMENTED / EVIDENCE_PENDING / NO-MERGE**.
