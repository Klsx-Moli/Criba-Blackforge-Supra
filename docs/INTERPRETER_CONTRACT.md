# Intérprete de CRIBA y límites de sus resultados

La interpretación de un cruce debe explicar operaciones concretas para el problema,
respetar sus restricciones y distinguir hipótesis de observaciones. Una respuesta
fluida o una etiqueta del modelo no acredita esa calidad ni demuestra causalidad.

## Ruta de interpretación

El puerto `InterpreterPort` alimenta tanto `inventar`/Shadow como el bloque opcional
de `engine.activate`. El backend externo usa el endpoint OpenAI-compatible elegido
por el operador. El backend local usa un runtime loopback real y comparte el mismo
contrato; requiere superar un banco fijo antes de admitir propuestas.

1. La propuesta declara pertinencia o abstención motivada. Se validan tipos reales:
   `null`, listas convertidas en texto, citas inexistentes y autoasignaciones de
   scores/veredictos no pasan el contrato.
2. Una propuesta pertinente necesita cadena causal, aportación específica de las
   dos técnicas, supuestos, evidencia entregada citada por índice, conocimiento
   previo, incertidumbre y antecedentes pendientes de búsqueda.
3. La prueba declara métrica, baseline, umbral numérico, condición de fracaso,
   alternativa explicativa y predicciones diferentes de H1/H2 bajo la misma
   intervención. Su suficiencia científica requiere revisión y preregistro;
   rellenar esos campos no ejecuta ni valida el experimento.
4. Otra petición critica la propuesta y responde las once preguntas
   epistemológicas. Una palabra clave no cubre una pregunta. Objeciones,
   restricciones no respetadas o crítica ausente dejan la interpretación pendiente.
5. La propuesta y la crítica conservan salida original, modelo pedido/reportado,
   endpoint sin credenciales, request ID y hashes de prompt/salida. No se cambia
   de proveedor automáticamente al fallar.

La crítica puede usar `CRIBA_CRITIC_MODEL`; por defecto emplea el mismo modelo.
Siempre se etiqueta `independent_validation=False`, incluso cuando los modelos
difieren. `CRITIQUED` significa crítica automática completa, no aprobación humana,
ejecución acreditada, novedad verificada ni validación científica.

## Persistencia, historial y contabilidad

SQLite guarda entrada, resultado, crítica, procedencia y cada intento dentro de
una transacción. Las semillas ausentes y cero tienen identidades distintas. Un
pendiente se reintenta; un éxito sólo se reutiliza tras revalidar contenido,
versión de contrato y huella del prompt actual, dentro de la misma ejecución.
Los registros antiguos se conservan como `LEGACY_UNVERIFIED`; un score desconocido
se escribe como `NULL`. Un JSON de caché dañado se conserva para diagnóstico y se
invalida. La escritura concurrente no acredita dos veces una misma identidad.

Los dossiers transmiten diagnósticos en `interpretacion` y los preservan en el
receipt de planificación de SUPRA. La identidad de un dossier antiguo sin ese
campo se mantiene compatible con `criba-supra/1`. La recepción sigue significando
`NOT_EXECUTED` y `NOT_VALIDATED`. Los hashes prueban correspondencia de contenido,
no verdad empírica. Ante un fallo al guardar una transición, SUPRA restaura también
las instancias que ya había entregado a sus consumidores.

La contabilidad de peticiones incluye propuesta y crítica de cada intento de
candidato, incluidos sustitutos rechazados, sólo cuando el puerto proporciona el
recuento. No representa el presupuesto total: búsqueda, referencias externas,
admisión local y aprendizaje tienen ámbitos diferentes. La admisión local publica
su propio informe y número de peticiones.

## Banco y comprobación del runtime

Desde `criba-blackforge`:

```powershell
.\.venv\Scripts\python.exe scripts/check_interpreter.py
.\.venv\Scripts\python.exe scripts/check_interpreter.py --evaluate
.\.venv\Scripts\python.exe scripts/check_interpreter.py --backend local_llama
```

El banco tiene un caso pertinente, uno irrelevante, uno contradicho por evidencia
y uno imposible por restricciones. Exige dos repeticiones, abstención correcta en
negativos y consistencia del mecanismo en el positivo. Un fallo de red no cuenta
como abstención. La comparación con una referencia es opcional y queda desconocida
si no se ejecuta. Superar este banco limitado no demuestra calidad general ni
ventaja respecto a otro modelo; haría falta un conjunto independiente más amplio.

Configuración externa actual por defecto:

```text
CRIBA_EXTERNAL_BASE_URL=http://127.0.0.1:8645/v1
CRIBA_EXTERNAL_MODEL=stealth/space-bunny-alpha
CRIBA_EXTERNAL_TIMEOUT_S=120
CRIBA_EXTERNAL_MAX_TOKENS=8192
```

Las credenciales se leen del entorno y nunca se incluyen en el paquete ni la
procedencia. El proxy debe estar activo para ejecutar una prueba con Space Bunny.
El nombre de un modelo utilizado por el agente de Hermes no implica que ese proxy
esté disponible para la aplicación.

Los parámetros se fijan al construir el intérprete y se guardan en su procedencia
y en la identidad de caché. Cambiar el límite de salida, temperatura o política de
razonamiento obliga a generar de nuevo. `CRIBA_EXTERNAL_REASONING_EFFORT` es optativo:
se envía sólo si se configura, y el modelo debe admitir el valor elegido. Para
OpenRouter se utiliza `reasoning.effort`; para otros endpoints, `reasoning_effort`.
Un `none` global no sería válido para todos los modelos.

El intérprete local respeta `timeout`, `max_output_tokens`, `temperature` y
`reasoning` del perfil habilitado en `models.json`, sin heredar los límites del
proveedor externo. El modo rápido pide desactivar thinking. `parallel_slots` se
aplica al arrancar un servidor llama.cpp administrado por CRIBA; no reconfigura
servidores ya activos ni controla el paralelismo de Ollama. El contexto total de
llama.cpp se comparte entre slots. `key_env` no pertenece al contrato de perfiles
locales: las credenciales externas usan `CRIBA_EXTERNAL_API_KEY`.

Para arrancar el perfil local exclusivamente durante una evaluación:

```powershell
.\.venv\Scripts\python.exe scripts/check_interpreter.py --backend local_llama --start-local --evaluate --output admission.json
```

El proceso cierra únicamente servidores que haya arrancado él. El informe guarda
cada respuesta original, crítica, diagnóstico y procedencia para revisar por qué
un modelo pasa o falla; no convierte una respuesta fallida en una idea sintética.

## Relación con la arquitectura científica causal

Este cambio sigue el enfoque del chat «Arquitectura científica causal»: identidad
estable, ausencia de promoción semántica y revalidación del historial al leer o
reiniciar. No acredita D3 (novedad), D4 (diversidad funcional), D6 (beneficio de
aprendizaje/OPE) ni D8 (juez independiente). AntiGoodhart OFF sigue siendo canónico;
no se activa STANDARD ni se conectan diagnósticos observacionales al RNG, priors,
memoria o decisiones. La crítica del intérprete es una etapa explícita de esa ruta,
no un mecanismo para habilitar el observador AntiGoodhart.

Pruebas principales: `test_interpreter_hardening.py`, `test_interprete_puerto.py`,
`test_shadow_interpreter_journey.py`, `test_m2_vertical_slice_e2e.py`, vectores
compartidos de envelope y `supra/tests/test_state_persistence_atomicity.py`.
