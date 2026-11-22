# CBS F29 — «Cargar modelo»: Hermes, OpenCode, Ollama y GGUF

**Estado del corte:** IMPLEMENTED (UI/catalog read-only) / EVIDENCE_PENDING (PySide6/Windows); **OpenCode inference NOT_IMPLEMENTED**.
**Base:** F28 `05c6cb6622cfb99a763817257806a9b9a95b8fd3`. Cambios exclusivamente en Shadow UI, su puente de acciones, descubrimiento de catálogos y regresiones; motor ASTRA sin cambios. G0 NO-GO, P0 semántico OPEN.

## Operación deseada de la interfaz

En la tarjeta **Generación → Intérprete** y en la cabecera, al abrir Shadow se ve **Cargar modelo**, sin ningún modelo remoto/autenticación asumidos. El desplegable inicial contiene:
1. Cargar modelo — sin selección, NO ejecutable;
2. Hermes — sincronización GET del proxy local en `127.0.0.1:8645/v1/models`;
3. OpenCode — consulta GET de `127.0.0.1:4096/provider`, **catálogo solamente**;
4. Ollama — consulta GET de `127.0.0.1:11434/api/tags`;
5. GGUF local — conserva acceso al gestor de perfiles llama.cpp/Ollama y al banco obligatorio.

**Sin conexión automática al arrancar.** Elegir un origen hace una consulta de catálogo GET limitada a 1 MiB, timeout 3 s, sin proxies HTTP ni redirecciones, sin shell ni variables de credenciales. La UI muestra hasta 500 modelos anunciados, sin etiquetas `free`, sin inferir un permiso de inferencia a partir de la lista.

Hermes: al seleccionar un modelo del catálogo, el puente existente llama al intérprete OpenAI-compatible con el ID seleccionado. Se exige que `CRIBA_EXTERNAL_BASE_URL` apunte al **proxy Hermes**; de lo contrario se bloquea antes de la mutación. Hermes posee OAuth y gestiona su refresh: CRIBA no abre `~/.hermes/auth.json`, no copia API keys y no persiste tokens en models.json.

Ollama: seleccionar explícitamente un modelo crea o reutiliza un perfil con backend ollama, endpoint `http://127.0.0.1:11434`, auto_start=False y activa ese perfil en models.json usando el escritor actual. La instancia real de LocalLlamaInterpreter continúa sometida al banco; selección local != banco superado. No se sobreescribe un perfil distinto.

OpenCode: la API `/provider` permite consultar proveedores, modelos y estado `connected` **reportado**, pero no da un endpoint compatible `/v1/chat/completions`. Esta fase no lee `auth.json`, ni inyecta prompts en una sesión con permisos/herramientas, ni asume que una conexión permite inferencia. Por eso sus modelos aparecen con estado **NO EJECUTABLE** al seleccionarlos y `Inventar` falla cerrado antes de crear el worker. Un adaptador de sesiones necesitará contrato de herramientas prohibidas, ejecución aislada, provenance y presupuesto; no implementar a ciegas en ASTRA.

## Preparación operacional en el PC (el operador, sin detener SUPRA)

Hermes: configurar login en Hermes con `hermes model` o `hermes portal` y arrancar `hermes proxy start` por la vía normal de Hermes. `hermes proxy status` ayuda a revisar adaptadores. El proxy oficial soporta Nous y xAI como adaptadores de inferencia a la fecha de la documentación inspeccionada; **el catálogo de todos los providers que Hermes conoce no equivale a soporte por el proxy**. No copiar refresh tokens ni establecer secrets en el repositorio.

OpenCode: `opencode auth list` o `opencode auth list --format json` muestra autenticaciones desde OpenCode; `opencode serve --hostname 127.0.0.1 --port 4096` permite el catálogo local. No iniciar servidor automáticamente desde CRIBA, ni exponerlo en `0.0.0.0`, ni introducir una API key en el UI. Si OpenCode server requiere contraseña, esta versión informa de catálogo inaccesible: no elude Basic Auth.

Ollama: iniciar el servicio local normal y elegir el modelo que anuncie `/api/tags`; el banco seguirá siendo condición de ejecución.

No se usa Laguna S 2.1 como opción fija ni se promete que `:free` siga disponible. `interprete/seleccion.py:FREE_MODELS` y el default legacy de `OpenAICompatibleInterpreter` todavía tienen valores históricos por compatibilidad y por el bloqueo de cambios al motor ASTRA; el selector productivo Shadow no los usa. **Esto es una deuda explícita:** otros entrypoints que instancien el intérprete sin modelo podrían conservar el default antiguo; deben recibir un contrato/migración aparte, no una sustitución silenciosa.

## Invariantes / regresiones

- Ninguna petición ni proceso local al crear ShadowWindow; el operador debe escoger origen.
- Sólo tres GETs loopback fijos, sin redirects ni proxies. Nada de `POST`, shell o lectura de `auth.json`.
- No conectar un modelo libre por una marca de precio obsoleta; respuesta `model.id` no acredita coste, acceso, autenticación ni pesos.
- Nunca reutilizar un resultado de catálogo tardío si el operador ya cambió de origen.
- Denegar `Inventar` cuando no hay modelo, el origen no está seleccionado, OpenCode no tiene adaptador, o el proxy Hermes seleccionado apunta a otra URL.
- Seleccionar Ollama persiste **sólo tras acción explícita**, reutiliza perfil ya existente y mantiene aceptación del banco.
- No mostrar secretos (credenciales del CLI, errores upstream, tokens OAuth) en la UI o su journal.
- Pruebas escritas: `test_phase29_interpreter_sources.py` (descubrimiento puro y JSON adversarial), `test_phase29_shadow_source_selector.py` (Qt-gated), y ajustes de tres suites legacy que confundían DEFAULT con ready. Son código publicado pero **NOT_EXECUTED en el checkout íntegro**; PySide6 no disponible en el contenedor de esta sesión. No hay validación Windows ni captura visual acreditada.

## Verificaciones necesarias antes de integrar

```powershell
cd C:\ASTRA_WORK\Criba-Blackforge-Supra
git status --short --branch
git fetch origin campaign/cbs-final-32-40
git worktree add --detach C:\ASTRA_WORK\cbs-f29-review <SHA_VERIFICADO>
cd C:\ASTRA_WORK\cbs-f29-review\criba-blackforge
uv run --locked python -m pytest -q tests/unit/test_phase29_interpreter_sources.py tests/unit/test_phase29_shadow_source_selector.py tests/unit/test_interpreter_selector_startup.py tests/unit/test_shadow_interpreter_journey.py tests/unit/test_functional_proposal_journey.py
uv run --locked python -m pytest -q tests/unit
uv run --locked ruff check src shadow_ui tests
uv run --locked mypy src
git diff --check
```

Si hay cambios locales, protegerlos antes de fetch/merge; jamás reset/clean/force-push. No detener Uvicorn SUPRA para comprobar un catálogo. No hacer POST de prueba a proveedores de pago; precios, cuotas y autorización son UNKNOWN hasta evidencia del proveedor.


## Reconciliación adversarial posterior al primer corte F29

- En Shadow, el botón de la cabecera **Cargar modelo** abre ahora el mismo selector de fuentes; la barra lateral **Modelos** conserva el editor clásico de perfiles.
- No se reclama coste cero: elegir un modelo remoto del catálogo de Hermes solicita un consentimiento explícito **en cada acción Inventar** antes de cualquier mutación. El aviso advierte de propuestas, crítica, reintentos y posibles consumos. La aceptación no equivale a un límite físico de requests ni a verificar precio/cuota, y puede haber otras superficies legacy no protegidas.
- El intérprete externo puede leer `CRIBA_CRITIC_MODEL` y enviar una segunda petición a un modelo invisible, incluido Laguna obsoleto. Para una elección de catálogo Hermes, si hay crítico distinto del elegido, se BLOQUEA antes del consentimiento de coste: no se disfraza de misma identidad. `CRIBA_EXTERNAL_API_KEY` debe estar vacío y `CRIBA_EXTERNAL_PROVIDER` debe ser el proxy esperado; no reenviar credenciales ajenas a Hermes.
- Activar un perfil Ollama afecta al `models.json` compartido con BLACKFORGE. Se ha añadido una **segunda confirmación explícita** antes de cambiarlo. Cancelar implica cero escrituras de configuración. Una selección Ollama conserva en el selector `(backend, model)` esperado en un rol Qt adicional; al ejecutar se compara con el perfil activo, incluido endpoint. Si deriva, BLOQUEADO antes de crear trabajo.
- El guard de Shadow habría roto la ventana `CribaMainWindow` sin dropdown (mismo `actions.on_inventar`). Se corrigió: el rechazo de «sin modelo» se aplica únicamente a un selector Shadow existente. La ruta clásica conserva su comportamiento histórico; **sus modelos legacy y precios deben seguir auditándose**.
- GET async: generación incremental `_model_source_generation` descarta respuestas tardías de A→B→A. Los callbacks de catálogo capturan `RuntimeError` de un selector Qt ya destruido; no fuerzan reapertura ni cambio de selección. Las consultas HTTP read-only pueden terminar después de cerrar ventana, pero sus respuestas no dan autoridad al usuario.
- Regresiones ampliadas: `test_phase29_shadow_source_selector.py` cubre consentimiento YES/NO para Ollama y Hermes, crítico ajeno, deriva de perfil entre selección y ejecución, y modelo por defecto ausente. `test_phase29_interpreter_sources.py` incluye GET sin proxy/redirección, límite 1MiB, JSON adversarial e IDs maliciosos. **Publicadas, NOT_EXECUTED** en checkout integral.
- LÍMITES explícitos: no hay adaptador de ejecución OpenCode ni sincronización de sus secretos; el proxy Hermes no da acceso automático a todos los providers de Hermes y sus adaptadores disponibles dependen de la versión; no hay presupuesto global per-POST ni claims de autenticación remota, cuotas, precio, peso GGUF residente, banco superado o uso real. ASTRA, main, handoff y Uvicorn del usuario permanecen sin cambios.


## F29 revisión de consentimiento y TOCTOU (adicional)

- Un diálogo `QMessageBox.question` abre un bucle Qt anidado: el operador o un callback pueden alterar selección, problema, modo/semilla, `CRIBA_CRITIC_MODEL`, endpoint o autorización entre el primer chequeo y la aceptación. La rama ahora guarda identidad completa ANTES del diálogo, comprueba los mismos valores DESPUÉS, y deniega como `consentimiento caducado` si cualquiera cambió. Un valor de semilla inválido durante el diálogo falla cerrado. Regresiones parametrizadas por mutación model/problem/critic/seed, PUBLICADAS y NOT_EXECUTED.
- Al lanzar el worker, `problem_snapshot` se copia al hilo productor, en lugar de leer `win.problem` dentro del worker tras un posible cambio de GUI. Esto no es una autorización para ejecutar inferencias: sigue haciendo falta seleccionar un modelo, respetar el banco y confirmar el coste desconocido.
- Se descartan resultados de catálogo que lleguen al `QComboBox` después de cerrar la ventana; las generaciones de consulta invalidan A→B→A, en lugar de comparar solo el nombre de origen.
- El protocolo actual de permisos cubre la ruta Shadow `Inventar`; otras llamadas a intérprete de la aplicación y la CLI heredada no quedan automáticamente cubiertas. Debe auditarse el límite de consumo por POST físico antes de afirmar protección global de presupuesto.
