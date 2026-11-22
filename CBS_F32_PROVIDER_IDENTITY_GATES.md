# CBS F32 — Identidad efectiva, coste y replay de selección

**Base de este ciclo:** F31 `6bef11aef156132883b2ef89e94d58c3c37021e7`.
**Trabajo aislado:** `campaign/cbs-final-32-40`. Main, ASTRA, handoff y procesos Uvicorn siguen fuera del alcance.
**Estado:** código y pruebas publicados, sin suite PySide6 en Windows: **IMPLEMENTED / EVIDENCE_PENDING, NO-MERGE**.

## Hallazgo F32-R01 — Mutaciones de coste por fuera del snapshot F31

**Contrato:** consentimiento Hermes en Shadow identifica *qué modelo/ruta y parámetros de petición* fueron autorizados. La autorización de inferencia no equivale a precio garantizado ni a un número máximo de POST físicos.

**Ruta efectiva:** `on_inventar` -> diálogo modal -> `Worker(_task)` -> `_run_inventar` -> `OpenAICompatibleInterpreter`; para refinamiento `on_protocolo_operativo` -> worker -> `refinar_propuesta` -> `completar_json`.

**Defecto:** F31 vigilaba endpoint, key, provider, model, critic y fallback, pero no `CRIBA_EXTERNAL_MAX_TOKENS`, `CRIBA_EXTERNAL_CRITIQUE_MAX_TOKENS`, timeout, effort, temperatura de crítica, seed, modo decodificación ni límites/reintentos de refinamiento. Con un cambio mientras la tarea estaba en cola se podían usar parámetros distintos a los inicialmente aprobados; durante el modal de Inventar F31 tampoco miraba esos parámetros.

**Fix publicado:** `_hermes_run_env_snapshot` amplía la identidad a las variables de petición conocidas:
`CRIBA_EXTERNAL_BASE_URL`, `CRIBA_EXTERNAL_API_KEY`, `CRIBA_EXTERNAL_PROVIDER`, `CRIBA_EXTERNAL_MODEL`, `CRIBA_CRITIC_MODEL`, `CRIBA_EXTERNAL_FALLBACK_LOCAL`, `CRIBA_EXTERNAL_TIMEOUT_S`, `CRIBA_EXTERNAL_MAX_TOKENS`, `CRIBA_EXTERNAL_REASONING_EFFORT`, `CRIBA_EXTERNAL_CRITIQUE_MAX_TOKENS`, `CRIBA_EXTERNAL_CRITIQUE_TEMPERATURE`, `CRIBA_EXTERNAL_CRITIQUE_TIMEOUT_S`, `CRIBA_EXTERNAL_CRITIQUE_REASONING_EFFORT`, `CRIBA_EXTERNAL_SEED`, `CRIBA_CONSTRAINED_DECODING`, `CRIBA_REFINEMENT_MAX_TOKENS` y `CRIBA_ACCEPTANCE_NO_RETRIES`. Inventar compara el snapshot **antes y después del modal**, y ambos workers lo comprueban **antes de construir/correr** la ruta de modelo. Sin copiar tokens OAuth ni exponer credenciales en trazas.

**Falsación:** sentinels de mutación por campo remoto en colas de Inventar y refinamiento + siete mutaciones durante modal (max tokens, timeout, reasoning, decoding, retry). **Escrito; NOT_EXECUTED.** El snapshot detecta deriva entre dos checkpoints, no configura un límite de crédito ni congela todo el proceso o cada POST. Si el entorno cambia y se restablece entre dos checkpoints, es posible un A-B-A.

## Hallazgo F32-L01 — El perfil local podía cambiar después de encolar

**Contrato:** elegir modelo GGUF/Ollama en Shadow fija una identidad de ejecución; el worker posterior no debe interpretar con un perfil compartido distinto sin avisar.

**Ruta efectiva:** selector `local_llama` -> comprobación UI -> cola -> `LocalLlamaInterpreter.__init__` -> `load_model_settings()` y overrides del entorno. El constructor de intérprete consulta el archivo al ejecutarse, no al seleccionar.

**Defecto:** F29 validaba `active_profile()` antes de encolar; un editor simultáneo podía reemplazar `models.json`, y la tarea encolada aceptaba el perfil nuevo. `CRIBA_LOCAL_MODEL`/`CRIBA_LOCAL_BASE` preexistentes podían también desviar el runtime del perfil visible. `on_protocolo_operativo` construía un intérprete local basado en el perfil **actual**, aun cuando `sheet["interpreter"]["model_requested"]` describía el modelo original.

**Fix publicado:**
- `_shadow_local_active_identity` exige perfil activo y que los overrides de base/modelo coincidan con él (comparación de endpoint tolerante al sufijo `/v1`, sin aceptar hosts diferentes).
- Antes de Inventar, la interfaz rechaza overrides de identidad contradictorios.
- Antes de Protocolo operativo, la rama Shadow rechaza refinar cuando el modelo local almacenado en la propuesta difiere del perfil activo.
- `_local_run_state_snapshot` lee a lo sumo 1 MiB del archivo compartido, captura ruta y overrides, y el worker comprueba la misma fotografía antes de generar. No imprime contenidos ni modifica archivo. El modelo local todavía debe superar su banco.
- El editor clásico y el motor ASTRA no se alteran.

**Falsación:** seis mutaciones de perfil/override/config y sobrelímite en cola Inventar, tres en cola refinamiento, tres casos de mismatch de origen y un sentinel del límite de lectura. Test fixture elimina overrides heredados del PC. **Escrito; NOT_EXECUTED.**

**Límite:** comparación pre-despacho y no CAS/lock; modificaciones de archivos realizadas después del checkpoint o interrupciones durante guardado todavía requieren protección de persistencia e idempotencia. Un perfil de Ollama descargado no equivale a modelo disponible ni banco PASS.

## Integridad y verificación

| Etiqueta | Estado |
|---|---|
| VERIFIED_BY_ME | SHAs, diffs y contenido remoto de fuentes por conector GitHub |
| STATICALLY_INSPECTED | Call sites de Shadow, constructor de LocalLlamaInterpreter, campos de ModelProfile, sentinels introducidos |
| NOT_EXECUTED | PySide6 / pytest de GUI y suite de regresión, Ruff y mypy |
| NOT_ACCESSIBLE | Windows del usuario, trabajos reales de Ernie, tokens OAuth, upstream Hermes efectivo |
| OPEN (P1) | Nº físico de POST y reintentos; atribución upstream; CAS/lock de modelos.json; configuración alterada durante llamada ya iniciada |
| OPEN (P0/G0) | Semántica científica y bloqueo G0 sin promocionar |

## Secuencia requerida para cerrar

1. **Ernie ya recibió F31** con el commit fijo `6bef11aef156132883b2ef89e94d58c3c37021e7`: no cambiar el SHA de ese encargo en curso ni su worktree.
2. Reconciliar el resultado F31; si hay fallos, preservar traceback, repro, minimal fix y regresión.
3. Crear **otro worktree** de la última rama F32 (SHA concreto del nuevo informe) sin detener Uvicorn, sin manipular procesos y con un path nuevo.
4. Ejecutar `test_phase29_shadow_source_selector.py`, `test_phase29_interpreter_sources.py`, `test_refinamiento.py`, `test_gui_inventar.py`, suite F27/F28/F30/F31 y tests offline; después Ruff, mypy y diff-check; cualquier test de proveedor externo debe permanecer mockeado/deshabilitado.
5. Revisar de nuevo la selección visible y procedencia del modelo a 1366×768 y 1920×1080; sin pruebas afirmadas como verdes si se omitieron o el plugin Qt no estaba instalado.
6. NO_MERGE a main; G0/semántica no se alteran. Cerrar F32 solo con evidencia de Windows y re-scan de regresiones.

Referencias locales: `CBS_F30_ADVERSARIAL_CONTINUITY.md`, `CBS_F31_WINDOWS_EXECUTION_HANDOFF.md`, `CBS_FINAL_CAMPAIGN.md`.
