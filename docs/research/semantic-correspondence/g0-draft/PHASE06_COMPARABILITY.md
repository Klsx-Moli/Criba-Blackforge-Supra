# CBS-FINAL — F06: comparabilidad S0/S1 y preflight (borrador de investigación)

**Estado: BLOCKED / G0 DRAFT_NOT_APPROVED / P0 semántico OPEN.**
No concede autorización, ejecuta llamadas ni cambia el motor productivo. Las referencias del corpus son hipótesis del autor, no gold independiente. Este documento no reemplaza el prerregistro `PREREGISTRATION_DRAFT.md` ni los contratos científicos de ASTRA.

## 1. Fuentes verificadas del checkout de campaña

- `src/criba/interprete/contrato.py`, blob `977fafa15c56b226b04f2b5af79962c4e54f683a`: `prompt_critica`, `_datos_prompt`, `restricciones_de`, `schema_critica`, `validar_critica`, `separar_errores_critica`.
- `benchmarks/innovation/semantic_lab.py`, blob `5f9b9c8121b7d4499bc50c713b986b68e785ae12`: `Trial`, `direct_request`, `project_proposal`, `evaluate`.
- `benchmarks/innovation/semantic_cases.py`, blob `cc713aee9d7198fdef38e4d9bbf5e351ff6eee95`: casos y etiquetas de **desarrollo**. Ninguna referencia se envía al revisor.
- `benchmarks/innovation/semantic_critic_bridge.py`, tras F05: fail closed para hash del prompt DIRECT/BLIND frente al prompt productivo distinto.
- `docs/research/semantic-correspondence/g0-draft/pilot_gate.py`, blob `74cac16e6e5458c076afeab22cef643e401fecc9`: programa A con 8 casos × 2 brazos = 16 slots. El gate solo calcula umbrales en registros aportados; no autentica inferencias.

Los módulos fuente de los dos primeros apartados fueron inspeccionados en GitHub. En el sandbox, `semantic_lab.py` y `semantic_cases.py` son los blobs exactos, pero `contrato.py` es una **dependencia mínima de pruebas**, no el original. Por tanto, no se declara que las 50 pruebas nuevas hayan ejecutado el generador productivo auténtico; esa integración deberá ejecutarse en checkout íntegro.

## 2. Desigualdad material constatada

| Dimensión | S0 — crítica actual | S1 — crítica ASTRA | Control necesario |
|---|---|---|---|
| Problema | `PROBLEMA` | `query` | Igualdad exacta de contenido |
| Restricciones | `RESTRICCIONES OBLIGATORIAS` y `BLOQUEO IDENTIFICADO` | `restrictions` | Igualdad exacta y contexto de bloqueo explicable |
| Candidato | `PROPUESTA A CRITICAR` completo | `project_proposal` de 6 campos + claims | Congelar un paquete semántico común, sin perder campos materiales |
| Cruce/dominio/evidencia/contención | Presente, potencialmente informativo | No se incluye en `direct_request` | Igualar hechos o prerregistrar explícitamente un control diferente |
| Estrategia | Booleanos + objeciones + Q1–Q11 | Correspondencia por ejes/citas | Única variable experimental; freeze de las dos instrucciones |
| Resultado | `validar_critica` distingue errores y rechazo | `evaluate` distingue SUPPORTS/CONTRADICTS/UNKNOWN | Regla de adjudicación S0 preregistrada, con ERROR/NOT_RUN y sin promoción de UNKNOWN |
| Control de carga | `max_tokens` y retries de producción | valores propuestos, no observados | Igualdad efectiva, tokenizer, ventana, latencia, uso y 1 POST físico por slot |
| Juez/independencia | Alias declarado | Alias declarado | Misma identidad efectiva acreditada; no usar juez autoreferencial como gold |

**Regla de no-equivalencia:** la coincidencia del hash de solicitud del laboratorio con un `CritiqueCall` no demuestra que el prompt productivo sea el mismo. F05 lo bloquea. Igualar ambos hashes mediante un renombrado sería un falso arreglo.

La proyección S1 omite campos presentes en las propuestas de desarrollo, como `pertinencia`, `aportacion_por_tecnica`, `evidencia_citada` y `novedad`. Parte de `prueba` y de las restricciones se conserva por transformación, pero el mensaje completo no es biyectivo. Esto no demuestra que esos campos mejoren el resultado, sí demuestra asimetría informativa.

## 3. Instrumento creado

`benchmarks/innovation/semantic_pair_preflight.py`: inspector read-only y fail closed. Admite un `Trial` de laboratorio, el texto S0 capturado desde `prompt_critica`, el texto S1 canónico EXACTO y parámetros efectivos declarados para ambos brazos. `inspect_production_pair` obtiene S0 de `contrato.prompt_critica` en un checkout completo y S1 de `direct_request`, pero no invoca el intérprete ni red.

- Comprueba delimitadores y JSON estrictos (claves duplicadas, NaN y campos indebidos), metadata de referencia en el payload, igualdad de pregunta, restricciones y candidato, pérdidas de proyección, contexto S0 exclusivo, divergencia de configuración/formatos, retries y límite de tokens declarado.
- Devuelve huellas de mensajes, conteos de **bytes UTF-8** (NO tokens), diferencias explícitas y `status=BLOCKED`. `normalize_s0_diagnostic` devuelve solo `UNMAPPED` hasta fijar un mapeo que respete semántica del rechazo y de la incertidumbre. Ningún `True` ni una puntuación convierte la propuesta en verdad.
- Siempre declara `G0_NOT_APPROVED`, `MODEL_LOAD_IDENTITY_UNATTESTED`, `PROVIDER_DISPATCH_UNVERIFIED`, `S0_OUTCOME_MAPPING_NOT_VALIDATED`, `INDEPENDENT_REFERENCE_PENDING`, `OUTPUT_SCHEMA_DIFFERS`; ni coincidencia de metadatos ni hashes concede GO.
- No lee `pilot_cases.json` con etiquetas, no usa `reserved`, no crea recibos ni toca SQLite, no hace llamadas a proveedores y no introduce imports en runtime de producto.

Los tests de F06 sobre S0 usan una **captura sintética de su estructura de datos**. No se deben divulgar como tamaño real de prompts productivos, resultado de modelo, ni confirmación de que la llamada S0 fue efectivamente enviada.

## 4. Protocolo de resolución propuesto (requiere aprobación científica)

1. Congelar los **mismos hechos del problema, restricciones, propuesta íntegra y fuentes** para ambos brazos, y versionar el paquete. Como opción a estudiar: ambas críticas reciben el mismo JSON de hechos; solo cambia el método de razonamiento y el esquema de respuesta. Eso crearía una variante nueva de S0 respecto del crítico productivo, que deberá declararse como tal; no llamarla «S0 actual» sin comprobar equivalencia.
2. Congelar `system`, `user`, `response_format`, `schema`, versión, renderizador, tokens medidos con tokenizer del proveedor, modelo efectivo, seed soportada, ventana de contexto, timeout, temperatura y retries realmente deshabilitados. Registrar parámetros **observados** y no solo propuestos.
3. Preinscribir interpretación de S0 con tres estados: rechazo por contradicción explícita, evidencia insuficiente y error de formato/transporte; definir cómo se relacionan con S1 sin convertir un `False` o un error en un rechazo científico correcto. Mantener el reporte completo, caso por caso, con errores y faltantes.
4. Requerir adjudicación de referencias independientes, supervisada por el propietario, con al menos una fuente competente externa, registro de desacuerdos y no equiparar variantes a problemas independientes. Las 18 etiquetas son desarrollo, no holdout. El modelo crítico no puede juzgar su propio rendimiento sin independencia.
5. Congelar un solo plan de 16 slots A con orden determinista, sin retries, sin llamadas extra ni gasto; B y C necesitan nuevas autorizaciones. No usar el campo histórico `physical_calls` de los recibos como gasto acreditado. Un timeout incierto bloquea el presupuesto.
6. Las transferencias legítimas deben seguir siendo posibles: no mejorar el score simplemente rechazando todos los casos. Mantener 2 transferencias y los casos UNKNOWN del conjunto, pero no utilizar sus referencias como instrucciones al juez. Informar false accepts y pérdidas de transferencias por raíz, no por variantes como muestras independientes.
7. Comprobar la ruta exacta `producer → serialized payload → HTTP transport → receipt → ledger → normalizer → gate → report` y una ejecución Windows en entorno aislado antes de inferencias G0. Sin identidad de modelo ni fuentes congeladas, `BLOCKED`.

## 5. Evidencia de esta fase

- **208 pruebas dirigidas PASS** en sandbox Python, incluyendo las 158 heredadas y 50 nuevas sobre casos de desarrollo, integridad de mensajes, parámetros, diferencias, falsos metadatos de referencia y fallo cerrado. `compileall` dirigido PASS.
- **12/12 mutaciones materialmente diferentes detectadas**, incluidas autoconceder GO, omitir referencias, ignorar diferencias de candidato, aceptar S1 no canónico, ignorar ventana, convertir modelo a acreditado y forzar `SUPPORT` para S0. Un primer mutante redundante sobrevivió y fue sustituido por una mutación que desactiva toda la validación de parámetros. Se reejecutó la suite tras restaurar.
- **NO EJECUTADO**: generador productivo real íntegro, suite completa, Ruff/mypy/CI, inferencias, Windows/GUI, tokenizador real, identidad de pesos y adjudicación humana competente.
- **NO HABILITA** ninguna llamada A/B/C. P0 permanece OPEN y ventaja científica NOT_ESTABLISHED.

## 6. Siguiente acción

Fase 07: consolidar permisos G0, discrepancias de versiones, preflight de fuentes y decisión de aprobación única. No firmar por defecto. Si la comparabilidad S0/S1 y la integración real siguen bloqueadas, documentar NO-GO operativo para inferencias y seguir en paralelo tareas offline útiles de corrección, recuperación e interfaz sin abandonar el plan.
