# CBS F30 — Re-scan adversarial: consentimiento, perfiles compartidos y journal

**Base exacta:** `42c1dd4638fad619ec3a5eba1eb43cd36e85dd17` (F29).
**Rama:** `campaign/cbs-final-32-40`. **Estado F30:** cambios PUBLICADOS; ejecución de pruebas integrada **EVIDENCE_PENDING**.
**Límites:** main `1304649b781c335e66016b480ed7d7797fa6f359`, handoff `757519c480390167f22df60d7ef2da79215d1a72` y ASTRA sin cambios. No se han iniciado modelos, proveedores, servidores, CI pagado ni acciones sobre el Windows del usuario.

## 1. Regression / F27 F13 — JSONL torn tail

En `criba-blackforge/src/criba/dossier_batch.py:_events`, F27 introdujo rechazo estricto de cualquier tail JSONL sin salto de línea final: decisión correcta para replay. Sin embargo, el mensaje `batch journal unterminated final JSONL record` incumplía el contrato existente `tests/unit/test_dossier_batch_phase13.py:test_torn_commit_tail_fails_closed_and_preserves_bytes` (`match="journal corrupt"`).

**Fix mínimo:** `batch journal corrupt: unterminated final JSONL record`; preserva el rechazo estricto y satisface tanto el diagnóstico histórico como los nuevos tests F27 que esperan `unterminated`. **STATICALLY_INSPECTED; NOT_EXECUTED en checkout**.

## 2. P1 — Activación Ollama puede sobrescribir cambios ajenos

`actions._activate_ollama_choice` recuperaba modelos.json antes de `QMessageBox.question`, y escribía ese estado después del bucle Qt modal. Si otra superficie del programa o un proceso modificaba la selección o configuración mientras el diálogo estaba abierto, la confirmación podía activar un perfil no asociado a la selección o reemplazar cambios ajenos.

**Mitigación publicada:** capturar el índice+userData exactos y bytes de modelos.json antes de abrir el modal; comprobar de nuevo ambos después, denegar si hay deriva. Para un archivo existente, `_editable_model_settings_bytes` rechaza objeto malformado/duplicado, versión distinta, enabled no booleano, perfil activo ausente, IDs duplicados, NaN/Infinity y otras ambigüedades ANTES de pedir confirmación o reescribir. No se cambian las rutinas de lectura legacy del modelo ni ASTRA.

**Límite residual:** lectura/comprobación/escritura no son una transacción bloqueada cross-process; un escritor entre la última comparación y `os.replace` aún puede introducir una carrera TOCTOU. No elevarlo a atomicidad o a sincronización segura entre instancias hasta incorporar un lock/versionado compartido.

**Tests publicados:** `tests/unit/test_phase29_shadow_source_selector.py` incorpora mutación de selección, mutación de disco durante modal y 7 estados corruptos parseables/JSON inválido. **NOT_EXECUTED** en Python+PySide6 Windows.

## 3. P1 — Un modelo externo sin etiqueta Hermes podía saltar consentimiento

El guard de F29 dependía inicialmente de un rol Qt `UserRole+1 == "hermes"`. Si otra ruta añadía una opción `("openai_compatible", model)` sin ese rol, `Inventar` podía realizar inferencias externas sin su confirmación de gasto ni comprobar un crítico oculto.

**Fix:** consentimiento de cuota desconocida y verificación `CRIBA_CRITIC_MODEL` dependen ahora del *backend efectivo* `openai_compatible` de un selector Shadow, no del texto visible ni del rol decorativo. El proxy Hermes sigue restringido a loopback en `_hermes_proxy_base_ok`, con `CRIBA_EXTERNAL_API_KEY` vacío; ausencia de rol no crea permiso. Test de combo remoto manual sin UserRole y negativo con crítico ajeno.

**Límite:** este guard cubre `on_inventar` en Shadow, no todos los callers no gráficos de `OpenAICompatibleInterpreter` ni garantiza máximo de POSTs físicos. Un modelo puede cobrar por petición/reintento aunque el UI pida un consentimiento. F28 P1 contabilidad sigue OPEN.

## 4. P1 — «Protocolo operativo» era una segunda ruta de gasto

`actions.on_protocolo_operativo` construye un intérprete desde `sheet["interpreter"]` y llama a `refinar_propuesta -> interprete.completar_json` mediante worker. La autorización anterior de `Inventar` NO abarcaba esta segunda operación, cuya identidad proviene de la propuesta persistida, no necesariamente de la selección actual del desplegable.

**Fix en Shadow únicamente:** si backend del sheet es externo, exigir que `model_requested` esté identificado, proxy Hermes válido y confirmación específica que muestre el nombre del modelo y coste/cuota NO verificados. Antes de crear/cancelar un worker, verificar después del modal la misma entrada, sheet, run_id, query, problema, selección y configuración de endpoint/credenciales. Cancelación o deriva dejan el worker sin empezar. La ventana clásica sin selector conserva su ruta histórica para no provocar una regresión no solicitada.

**Tests publicados:** rechazo de autorización, cambio de problema/entrada/modelo/endpoint durante modal, y aprobación que alcanza solo el límite previo al worker sin inferencia real. **NOT_EXECUTED**.

## 5. Compatibilidad oficial de proveedores, sin copiar secretos

- Hermes subscription proxy: `http://127.0.0.1:8645/v1`, catálogo `GET /v1/models`, `POST /v1/chat/completions`, OAuth gestionado por Hermes. **Los adaptadores documentados** incluyen Nous Portal y xAI; esto NO implica que todos los proveedores CLI de Hermes estén disponibles por proxy, ni que el backend efectivo esté atestado. Referencia: https://hermes-agent.nousresearch.com/docs/user-guide/features/subscription-proxy
- OpenCode server: `GET /provider` devuelve `all`, `default`, `connected`; API de sesiones distinta a Chat Completions, potencialmente con herramientas y permisos. Autenticación del servidor mediante Basic opcional. No usar credenciales copiadas ni `POST /session/:id/message` hasta un contrato de sandbox, tool-denial, cuotas y attribution. Referencia: https://open-code.ai/en/docs/server
- Ollama: `GET /api/tags` no es comprobación de pesos cargados ni de admisión científica. `LocalLlamaInterpreter` mantiene banco antes de proponer; una selección/etiqueta no equivale a ready.

**Issue de provenance abierto:** `OpenAICompatibleInterpreter.provider` suele leerse desde `CRIBA_EXTERNAL_PROVIDER` con default `nous_oauth_subscription_proxy`; si Hermes proxy fuese xAI u otro upstream, esa etiqueta podría atribuir incorrectamente el proveedor real. No modificar motor ASTRA ni atribuir upstream por inferencia: reportar provider real como UNKNOWN hasta evidencia explícita, y estudiar contrato de enrutamiento.

## 6. Evidencia y continuidad

| Etiqueta | Alcance |
|---|---|
| VERIFIED_BY_ME | Referencias remotas/diff y fuentes inspeccionadas con conector GitHub; contraste documental Hermes/OpenCode; disponibilidad PySide6 no instalada en este entorno |
| STATICALLY_INSPECTED | Guards, mensajería, paths productivos, tests que deberían fallar ante mutaciones, compatibilidad F13 |
| NOT_EXECUTED | pytest dirigido/completo, tests Windows Qt, Ruff, mypy, screenshot Shadow, GET local real, proxy OAuth, CI de campaña |
| NOT_ACCESSIBLE | Terminal del usuario, base local del PC, credenciales locales, ejecución Uvicorn real |
| P1 OPEN | Atomicidad de actualización entre procesos; conteo físico de peticiones; provenance real de upstream; OpenCode no ejecutable por diseño |
| G0 / P0 | NO-GO / OPEN, sin cambios |

No afirmar test green, consumo cero, ninguna exposición previa, precio cero, auth sincronizada en OpenCode o identidad efectiva del modelo.

## 7. Pruebas exactas para Windows en worktree aislado

```powershell
cd C:\ASTRA_WORK\Criba-Blackforge-Supra
git status --short --branch
git fetch origin campaign/cbs-final-32-40
git worktree add --detach C:\ASTRA_WORK\cbs-f30-review <HEAD_F30_VERIFICADO>
cd C:\ASTRA_WORK\cbs-f30-review\criba-blackforge
uv run --locked python -m pytest -q tests/unit/test_dossier_batch_phase13.py tests/unit/test_dossier_phase27_cross_surface.py tests/unit/test_phase29_interpreter_sources.py tests/unit/test_phase29_shadow_source_selector.py tests/unit/test_gui_inventar.py tests/unit/test_refinamiento.py
uv run --locked python -m pytest -q tests/unit
uv run --locked ruff check src shadow_ui tests
uv run --locked mypy src
git diff --check
```

Para corregir una suite roja: REPRODUCE→TEST→FIX MÍNIMO→TEST DIRIGIDO→REGRESIÓN→STATIC→DIFF. No merge/push a main; todo en rama de campaña y sincronización local posterior, protegiendo cambios existentes. Sin lanzar pruebas que consuman proveedores externos.


## 8. False-coverage re-scan — silent normalization of known/unknown config fields

La primera protección de `_editable_model_settings_bytes` solo comprobaba versión, selección y IDs duplicados. Eso dejaba abiertas mutaciones en campos ordinarios (`backend` inválido, `context_size` negativo, `model` con espacios) y campos nuevos desconocidos. `ModelProfile.from_dict` los normalizaba o descartaba y `save_model_settings` sobrescribía los bytes originales. Por tanto, varios tests del primer grupo eran **FALSE_COVERAGE** respecto al contrato «no destruir configuraciones legacy».

**Fix adicional:** para un `models.json` existente, la activación desde catálogo Ollama exige exactamente las claves que conoce el esquema 1 actual y un roundtrip `asdict(ModelProfile.from_dict(profile)) == profile` para cada perfil, además de JSON estricto, IDs y active profile consistentes. Un archivo antiguo o futuro desconocido no se modifica desde el acceso rápido: se debe conservar y migrar explícitamente. No se altera `ModelProfile.from_dict` ni el editor clásico.

**Tests añadidos:** un archivo emitido por `save_model_settings` sí permite la operación; 7 mutaciones de campos desconocidos, omitidos, normalizados o enum inválido se rechazan antes de escribir. STATICALLY_INSPECTED; aún NOT_EXECUTED. Esto protege pérdida conocida de metadatos, no proporciona locks de proceso ni validación absoluta de contenido.
