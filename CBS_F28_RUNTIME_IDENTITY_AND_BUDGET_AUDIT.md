# CBS F28 — Runtime, identidad efectiva, autorización y contabilidad física

**Corte:** posterior a F27, base `09f1bd1f57aa4f4ce3e0e589e2839f71117f6880`.
**Clasificación:** F28 IN_PROGRESS / EVIDENCE_PENDING. G0 NO-GO; P0 semántico OPEN.
**Límites:** sin modificación de ASTRA, sin conexión a proveedores, sin inferencias, sin gasto, sin despliegue, sin tocar main/handoff. Inspección de blobs remotos y ejercicio aislado de un contrato pequeño; NO es suite de checkout ni aceptación de Windows.

## F28.1 — Diagnóstico de la ejecución de Uvicorn que muestra Hermes

Un comando `python -m uvicorn supra_agentic.service:app --host 127.0.0.1 --port ...` es un proceso de servidor de duración indefinida. El rótulo del terminal «iniciando» o el tiempo de ejecución no constituye traceback. No matar ni lanzar una segunda instancia sin comprobar antes PID, puerto y `GET /health`.

El endpoint documentado de desarrollo es `http://127.0.0.1:8080`, mientras `criba_shadow_main.SupraServer` puede escoger puerto efímero; jamás asumir el 8080 si el comando está truncado. `SUPRA_ENDPOINT` selecciona el backend al que se conecta CRIBA; borrar esa variable solo en el proceso del servidor no configura automáticamente todos los consumidores. No realizar POST para diagnosticar arranque.

PowerShell, read-only:
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'uvicorn.*supra_agentic' } | Select-Object ProcessId,CommandLine
Get-NetTCPConnection -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess
# Sustituir por puerto comprobado y SOLO después:
Invoke-RestMethod "http://127.0.0.1:8080/health"
```
`unset SUPRA_ENDPOINT && PYTHONPATH=src python ...` es sintaxis de Bash (Git Bash/MSYS); no copiar literalmente a PowerShell. La ruta de Downloads indicada por el operador estaba truncada: su contenido es NOT_ACCESSIBLE, no inferir error.

## F28.2 — P1 autenticación cruzada de servicio y proveedor, reparación de bajo riesgo

**Contrato:** `SUPRA_API_TOKEN` es el bearer que verifica `supra/src/supra_agentic/service.py` para la API SUPRA. `SUPRA_API_KEY` es credencial del proveedor de inferencia en `supra/src/supra_agentic/providers/__init__.py`. El cliente `criba-blackforge/src/criba/integrations/supra_client.py` leía `SUPRA_API_KEY` y lo adjuntaba como `Authorization: Bearer ...` a SUPRA.

**Impacto del defecto:** con ambas variables definidas, enviar al servicio la clave del proveedor en lugar del token del servicio da un HTTP 401; también arriesga revelar una credencial de proveedor al hostname de SUPRA configurado. No se dispone de evidencia de exposición real.

**Fix mínimo publicado:** `SupraClientConfig.from_env` ahora obtiene `api_key` desde `SUPRA_API_TOKEN`. El constructor explícito `SupraClientConfig(api_key=...)` sigue admitiendo un bearer elegido por el caller. `SUPRA_API_KEY` continúa disponible solamente para el backend proveedor; no se cambia SUPRA ni ASTRA.

**Regresión añadida:** `criba-blackforge/tests/integration/test_f28_supra_auth_env.py`, 3 funciones / 6 casos tras parametrización. Usa `httpx.MockTransport`, sin tráfico ni modelos. Contrasta token y provider key distintos, ausencia de token, ausencia de ambos, cliente explícito y repetición de configuración. Es código publicado, **NOT_EXECUTED en checkout**. Un ejercicio aislado reconstruyendo la clase y el header pasó 4/4 escenarios, lo que NO acredita el módulo completo.

**Migración:** si un operador usaba erróneamente `SUPRA_API_KEY` para autenticar CRIBA hacia SUPRA, deberá definir `SUPRA_API_TOKEN` con el token del servicio. No copiar una API key del proveedor a esta variable. Nunca registrar ni publicar valores secretos.

## F28.3 — P1 distinción entre modelo elegido y pesos efectivamente cargados

`src/criba/model_runtime.py:ensure_profile_available` usa `/api/tags` o `/v1/models` y alias; esos nombres no son prueba de GGUF en memoria. `benchmarks/innovation/model_identity_preflight.py` ya distingue `REPORTED_PATH_MATCH`, `loaded_file_identity=NOT_VERIFIED`, `authorization=NOT_GRANTED`; la captura no autentica el host ni la memoria. No promocionar alias, respuesta `model`, igualdad de SHA local o ruta declarada a identidad de pesos cargados.

**Contradicción entre superficies:** `src/criba/model_config.py:load_model_settings` repara IDs duplicados aleatoriamente y `ModelSettings.active_profile` retorna el primer perfil si no encuentra el ID solicitado. El preflight independiente rechaza selección ausente, IDs duplicados o ambigüedad. `tests/unit/test_model_config.py:test_duplicate_profile_ids_are_repaired` *protege* el comportamiento tolerante; `test_model_identity_preflight.py` protege el rechazo. Por tanto, no realizar un cambio global de política sin una migración explícita y pruebas GUI; en una auditoría estricta el resultado es BLOCKED/UNKNOWN, no identidad acreditada.

**Riesgo pendiente / STATICALLY_INSPECTED:** `LocalLlamaInterpreter.operativo()` reutiliza `gate_report["passed"]` tras comprobar el modo de decodificación, pero en ese branch no vincula el gate al modelo y endpoint actuales del objeto. Deben probarse mutaciones de `model`, `base`, configuración y proceso entre dos llamadas. No se modifica el intérprete/ASTRA en F28.

## F28.4 — P1 contabilidad física de solicitudes al intérprete

`src/criba/interprete/openai_compatible.py:_pedir` devuelve `model_requests=1` por llamada lógica, mientras `_post_chat_completion` admite hasta cuatro intentos HTTP bajo Tenacity si `CRIBA_ACCEPTANCE_NO_RETRIES` no vale `1`. La propia `proponer` puede hacer otra llamada lógica por truncamiento y otra fase de crítica; `analizar_caso` usa el transporte reintentable. Por tanto, `model_requests` NO es un contador autenticado de POST físicos y `completion_tokens` reportados tampoco son coste económico acreditado. Un modelo configurado como gratuito no acredita ausencia de coste real.

`shadow_invention_probe.py` tiene un guard explícito de aceptación con presupuesto 12 y deshabilita reintentos por excepción HTTP bajo ese modo. Sin embargo, las rutas normales no heredan automáticamente ese guard y los retries de truncamiento ocurren en otra capa. Los tests existentes de 429 con no-retries no prueban todas las rutas de truncamiento/reintento. Un contador físico fiable requiere registro antes de cada intento de transporte, IDs durables, cuotas y respuesta/coste reportados por el proveedor; la simulación offline de `semantic_transport_journal.py` declara `provider_consumption=None` y `authorization=NOT_GRANTED`, lo cual es correcto.

**No tocar el intérprete sin autorización**: es zona ASTRA/semántica protegida. No aumentar llamadas físicas «para medir»; reproducir con `httpx.MockTransport`, tests dirigidos y un presupuesto 0 de proveedores reales.

## F28.5 — Gates y próximos contratos

- VERIFIED_BY_ME (aislado): matriz de cuatro escenarios token/clave/headers con HTTP simulado, 4/4 PASS. No equivale al módulo integrado.
- STATICALLY_INSPECTED: fuentes, interacciones, fijación del client bearer, entrypoints, documentación, pruebas publicadas y ramas.
- NOT_EXECUTED: pytest nuevo de checkout íntegro, tests ASTRA, Ruff, mypy, PySide6, Windows, CI, GET al servicio del usuario, y verificación de un GGUF cargado.
- NOT_ACCESSIBLE: terminal del usuario, contenido de `C:\Users\KLSX\Downloads…` y su traceback real.
- P1 abierto: identidad activa y modelo efectivamente servido, contador físico ante retries, invalidación del banco tras cambio de modelo. P1 autenticación cliente/proveedor implementado, EVIDENCE_PENDING.
- Mantener G0 NO-GO y P0 OPEN. No merge, no publicar secretos, no convertir health=200 en ejecución, no inferir calidad científica o identidad de pesos, no reiniciar la única instancia Uvicorn solo para cerrar F28.
- Próximo paso material: ejecutar tests F27/F28 en worktree aislado y verificar Windows sin tocar el checkout protegido. Después, instrumentación de llamadas y revisión de invalidación del gate solo bajo autorización del motor ASTRA.
