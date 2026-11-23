# CBS F36 — Identidad física GGUF, enmienda handoff y ruta Ollama

Base de campaña F35: 2588bb8c62bb4ac75532c6628413b96bd5395770.
main: 1304649b781c335e66016b480ed7d7797fa6f359 (sin tocar).
handoff: 4297b63971927d5254f6099479a3eccbeaf876f2 (rectificación verificada).

## F36-I01 — P1: identidad física GGUF NO acreditada

STATICALLY_INSPECTED: src/criba/model_runtime.py:_assert_requested_model sólo compara IDs nominales de /v1/models usando _served_model_ids y _model_is_served. La ruta real /props.model_path no se compara con profile.gguf_path. Un alias correcto servido por un GGUF distinto puede superar esta validación. IDENTIFICADOR != ARCHIVO FÍSICO != CAPACIDAD CIENTÍFICA.

REPORTED_BY_AGENT + handoff §7.4 INSPECTED: cuatro piezas siguen sin commit en C:/ASTRA_WORK/iso-fixid-20261122: src/criba/model_runtime.py (M), tests/unit/test_model_runtime_identity.py (??), benchmarks/innovation/cbs_corpus.py (??), tests/unit/test_cbs_corpus_adapter.py (??). No se copiaron ni publicaron; no hay acceso directo al worktree Windows desde aquí.

REQUISITOS para transferencia, exclusivamente con autorización explícita del usuario: verificar status y diff completos, preservar cambios locales, revisar path canónico Windows, /props ausente/malformado, alias falso, mismo alias con otro GGUF, symlinks, basename collisions, fallos del backend, compatibilidad con llama.cpp; ejecutar las 6 regresiones de Ernie y tests negativos de mutación, hacer commit en rama aislada, comparar contra campaña actual antes de integración. No se autoriza commit/merge solo por la declaración de existencia de un fix.

F01-02 RECONCILIADO: Storage.record_event ya ejecuta BEGIN IMMEDIATE en main 1304649; la contribución adicional de Ernie fue timeout=30/busy_timeout, no la sentencia existente. Evitar reparación redundante.

## F36-I02 — P1: read settings de B con consentimiento en A

Ruta productiva: actions._activate_ollama_choice guardaba config_path desde model_config_path(), fotografiaba bytes A, pero después cargaba con load_model_settings() sin ruta. Si CRIBA_MODEL_CONFIG cambiaba durante esa ventana, el loader podía leer B y la escritura fijada de F35 todavía guardaría ese estado en A. Detectar deriva al final no vincula el origen de settings si hay cambios de entorno A-B-A.

FIX F36 publicado: load_model_settings(config_path), misma ruta exacta para snapshot, parse y save. Test nuevo test_f36_ollama_reads_exact_snapshotted_config_path observa los argumentos del loader y verifica que se usa la ruta consentida. No realiza peticiones externas. El cambio es mínimo y NO toca el pendiente model_runtime.py de Ernie.

ESTADO: STATICALLY_INSPECTED; nuevo test PySide6 NOT_EXECUTED. Sin compare-and-swap multi-proceso; permanece la ventana de modificación posterior al último check, y la lectura desde un archivo no convierte su contenido en verdad criptográfica.

## Puertas de aceptación

F31 Windows: 46 FAIL / 2786 PASS / 20 SKIP (REPORTED_BY_AGENT). F32–F36 cambios publicados, tests y CI actuales NO EXECUTED/NO RUNS. F28 conteo físico P1 OPEN. GGUF identidad real P1 OPEN. G0 NO-GO científico y P0 semántico OPEN. No declarar AUDIT COMPLETE ni GO.

Próximo: reconciliar F34 Windows de Ernie, comprobar F35/F36 en worktree nuevo de SHA exacto; solicitar primero evidencia read-only de los cuatro archivos locales antes de cualquier transferencia. Mantener main, ASTRA, Uvicorn y worktrees ajenos intactos.
