# Intérprete de CRIBA–BLACKFORGE–SUPRA: referencias del historial ASTRA

**Fecha del documento:** 17 de octubre de 2026  
**Propósito:** reunir en un único Markdown las referencias del historial de conversaciones relacionadas con el intérprete de CRIBA–BLACKFORGE–SUPRA y su conexión con la arquitectura científica causal de ASTRA.

> **Nota sobre la evidencia:** este documento compila las referencias que se recuperaron y resumieron en la conversación. No es una transcripción literal íntegra de cada chat ni una auditoría actual del repositorio. Las menciones a conceptos, nombres de funciones, estados y códigos no demuestran por sí solas que estén implementados o conectados en el código vigente.

## 1. Resumen ejecutivo

Sí existen referencias en el historial relacionadas con el intérprete de CRIBA–BLACKFORGE–SUPRA y su relación con la arquitectura científica causal de ASTRA. El hilo conductor no es solo un intérprete de lenguaje, sino la definición de una frontera entre:

- la interpretación y generación de propuestas;
- la validación determinista de esas propuestas;
- la procedencia de la evidencia;
- la autorización de acciones;
- la ejecución efectiva y persistencia de resultados;
- la comunicación honesta del estado a la interfaz.

La decisión arquitectónica descrita es que **el modelo puede interpretar y proponer, pero no debe decidir por sí solo qué está validado, autorizado o realmente ejecutado**. Esas afirmaciones deben estar respaldadas por mecanismos verificables del sistema.

La información recuperada documenta conceptos y problemas relevantes, pero no basta para afirmar que la especificación completa esté recuperada ni que toda la arquitectura esté integrada y verificada en el repositorio actual.

## 2. Conversaciones del historial relevantes

### 2.1. «ASTRA 6 — Decisión existencial del producto» / arquitectura científica causal

**Periodo indicado en el historial:** septiembre de 2026, con referencias específicas atribuidas al 5 de octubre.

Temas relevantes:

- intérprete LLM con procedencia;
- preparación de protocolos antes de ejecutar;
- generación de hipótesis y borradores por el LLM;
- validación, permisos, estados y evidencia dependientes de mecanismos deterministas;
- evitar presentar una inferencia, una señal o una hipótesis como evidencia causal demostrada.

La separación conceptual propuesta puede expresarse así:

1. El modelo interpreta el material disponible y propone hipótesis o borradores.
2. El sistema registra qué evidencia recibió y cuál es su procedencia.
3. Validadores deterministas comprueban los contratos, restricciones y condiciones aplicables.
4. Los controles de autorización deciden si una acción está permitida.
5. El sistema registra qué se ejecutó realmente y qué resultado se observó.
6. La interfaz comunica el estado efectivo, incluidos los fallos y las incertidumbres.

Esta secuencia es una síntesis arquitectónica de las referencias, no una afirmación de que exista ya una implementación completa de cada paso.

### 2.2. «ASTRA Reconcile» / integración y verificación CRIBA → SUPRA

**Periodo indicado:** 24–29 de septiembre de 2026.

El historial recoge una cadena de extremo a extremo parecida a esta:

`CRIBA → dossier → SupraClient → HTTP → SUPRA → persistencia → reinicio → consulta desde la UI`

En otras referencias técnicas aparecen etapas adicionales, recogidas en la sección 4.

Preocupaciones señaladas:

- conservar el significado de los datos entre componentes;
- evitar pérdidas semánticas durante la serialización y el transporte;
- verificar los contratos que conectan productores y consumidores;
- mantener consistencia de identidad entre versiones y suites de evaluación;
- comprobar la persistencia y la recuperación tras reiniciar;
- no dar por probada la integración productiva únicamente porque exista código o porque una prueba aislada pase.

### 2.3. Referencia del 21 de septiembre: «evidencia → intérprete → propuesta»

El historial refiere una cadena conceptual que distingue entre:

- evidencia recuperada;
- evidencia entregada al intérprete;
- uso de la evidencia documentado;
- efecto causal.

También indica que el recorrido productivo completo todavía figuraba como pendiente de verificar en aquel momento.

La distinción es importante: disponer de una evidencia no demuestra que el intérprete la haya recibido; haberla recibido no demuestra que la haya utilizado; documentar su uso no demuestra por sí solo un efecto causal.

### 2.4. Referencias del 30 de septiembre al 1 de octubre: recorrido técnico

Se documentó una cadena de integración más detallada:

`CRIBA → mechanism → dossier → serializer → SupraClient → HTTP/API → SUPRA → state → persistence → restart → GET/result`

Estas referencias centran la atención en la conservación de semántica y la comprobación del resultado después de reiniciar. La existencia de cada elemento en esta descripción histórica no confirma por sí misma que todos estén conectados correctamente en la versión actual.

### 2.5. Auditoría del intérprete y Shadow UI: 2 y 11 de octubre

El historial contiene instrucciones para no restaurar sin más el intérprete legacy ni su antigua capa de proveedores.

También identifica un problema de estado: el endpoint `/models` responde con HTTP 503 y la aplicación puede quedar en `PENDIENTE_INTERPRETACION`, junto con el mensaje «falta superar el banco local», sin explicar claramente qué condición concreta ha fallado.

En las referencias aparece el nombre `LocalLlamaInterpreter.operativo()`.

**Límite de esta evidencia:** el nombre de una función o la descripción de un fallo en el historial no prueba el estado actual de su implementación, su cobertura de tests ni su conexión con la UI.

## 3. Arquitectura conceptual del intérprete

La arquitectura que se desprende de las referencias separa responsabilidades que no deberían confundirse.

### 3.1. Interpretación

El intérprete procesa el material que se le entrega y puede generar hipótesis, interpretaciones o propuestas. Debe quedar claro qué entrada recibió y qué resultado produjo.

### 3.2. Procedencia de la evidencia

Se necesita conservar, como mínimo conceptualmente:

- qué evidencia se recuperó;
- qué evidencia se proporcionó al intérprete;
- qué salida produjo el intérprete;
- qué evidencia dice utilizar la salida, si esa relación está disponible;
- qué validaciones posteriores se realizaron;
- qué acciones se ejecutaron y qué resultados se observaron.

No debe inferirse automáticamente una relación causal por el mero orden temporal de estos pasos.

### 3.3. Validación determinista

Los contratos de datos, invariantes, permisos, restricciones y condiciones de ejecución deben comprobarse mediante mecanismos definidos y verificables. El modelo no puede autocertificar que su propia salida es válida, segura o ejecutada.

### 3.4. Ejecución y persistencia

La propuesta del intérprete debe distinguirse de la acción autorizada, de la acción intentada y del resultado observado. La persistencia debe comprobarse, incluida la lectura posterior y la recuperación tras un reinicio cuando corresponda.

### 3.5. Estado visible en la interfaz

La interfaz debe reflejar el estado real del sistema, no una etiqueta optimista ni un estado fantasma. Un fallo al consultar `/models`, una puerta de validación local no superada, un timeout y una salida truncada son causas distintas y no deberían reducirse a un mensaje genérico.

## 4. Recorrido de extremo a extremo mencionado

El recorrido técnico más explícito recuperado en el historial es:

```text
CRIBA
  → mechanism
  → dossier
  → serializer
  → SupraClient
  → HTTP/API
  → SUPRA
  → state
  → persistence
  → restart
  → GET/result
  → UI
```

Este recorrido debe entenderse como una **lista de fronteras de integración que hay que verificar**, no como una garantía de que el flujo completo funcione actualmente.

Preguntas de verificación asociadas:

1. ¿Qué contrato produce CRIBA y qué invariantes exige el dossier?
2. ¿El serializador preserva todos los campos semánticamente relevantes?
3. ¿`SupraClient` transmite el mismo contenido que recibió, sin mutaciones imprevistas?
4. ¿La API de SUPRA valida el contenido, los identificadores y el estado de forma explícita?
5. ¿Qué se guarda y con qué identidad/versionado?
6. ¿Una lectura posterior devuelve el mismo resultado semántico?
7. ¿La recuperación tras reinicio conserva los estados necesarios?
8. ¿La Shadow UI presenta el resultado persistido y distingue los fallos de cada etapa?
9. ¿Los tests cubren la cadena completa o solamente componentes aislados?

## 5. Diagnóstico del estado de interpretación

El problema concreto señalado en el historial combina dos elementos:

- `/models` devuelve HTTP 503;
- aparece el mensaje «falta superar el banco local» y el sistema puede permanecer en `PENDIENTE_INTERPRETACION`.

El riesgo es que el usuario vea un estado genérico que no explique el bloqueo real. La recomendación registrada fue hacer que el intérprete informe con claridad por qué no puede interpretar y que la UI presente la causa de forma comprensible.

### 5.1. Códigos de diagnóstico mencionados como propuestas

En el historial aparecen los siguientes códigos propuestos:

- `PROVIDER_HTTP_503`
- `LOCAL_MODEL_GATE_NOT_PASSED`
- `PROVIDER_TIMEOUT`
- `OUTPUT_TRUNCATED`
- `INTERPRETATION_VALIDATION_FAILED`

**Importante:** son códigos propuestos en el historial; no se ha confirmado aquí que todos existan en el código actual.

### 5.2. Principios para estados honestos

- No confundir un error HTTP del proveedor con una validación local no superada.
- No confundir timeout con salida truncada.
- No etiquetar como interpretado un resultado cuya validación haya fallado.
- No mantener indefinidamente un estado pendiente sin causa, transición o diagnóstico verificable.
- No declarar operativo un intérprete solo porque el proceso o el endpoint estén disponibles.
- Hacer que el estado de la UI derive de datos de estado observables del backend, en lugar de reconstruirlo mediante suposiciones.

Estos puntos son criterios de diseño y verificación; no certifican que estén todos implantados.

## 6. Relación con BLACKFORGE y la Shadow UI

La decisión arquitectónica reflejada en el historial del 2 de octubre era mantener BLACKFORGE en `HARD_PAUSE` y permitir que CRIBA Shadow UI y SUPRA funcionasen sin depender de él.

También se indicaba que no debía restaurarse sin más el intérprete legacy `interprete/servicio.py` ni su antigua capa de proveedores.

La consecuencia arquitectónica es que la disponibilidad de CRIBA y SUPRA no debería quedar falsamente vinculada a componentes de BLACKFORGE que están pausados o fuera del alcance activo. La UI necesita mostrar esa separación de forma explícita.

**Límite:** la referencia refleja una decisión de diseño histórica; para determinar si la rama actual la respeta hay que inspeccionar el repositorio y ejecutar las pruebas pertinentes.

## 7. Estado de conocimiento: documentado frente a no confirmado

| Elemento | Estado según las referencias recuperadas | Qué falta para elevar la confianza |
|---|---|---|
| Intérprete LLM con procedencia | Documentado conceptualmente | Especificación completa y contrato verificable |
| Separación LLM / validación determinista | Documentada conceptualmente | Inspección de implementación y pruebas adversariales |
| Cadena CRIBA → SUPRA y persistencia | Documentada | Ejecución de extremo a extremo sobre la versión vigente |
| Conservación del significado entre componentes | Preocupación explícita | Tests de contrato producer → serializer → transport → consumer |
| Estados epistémicos y evidencia | Documentados conceptualmente | Esquemas, transiciones e invariantes actuales |
| Diagnóstico de errores del intérprete | Problema identificado; códigos propuestos | Verificar códigos implementados y su propagación hasta la UI |
| `LocalLlamaInterpreter.operativo()` | Nombre mencionado en el historial | Confirmar existencia, comportamiento y callers actuales |
| `PENDIENTE_INTERPRETACION` | Estado problemático mencionado | Reproducir el fallo y confirmar su estado actual |
| Integración productiva de extremo a extremo | No confirmada por estas referencias | Pruebas reales, persistencia, reinicio y consulta desde UI |
| BLACKFORGE en `HARD_PAUSE` | Decisión de diseño histórica | Comparar con configuración, runtime y ramas actuales |

## 8. Búsquedas recomendadas dentro del historial

Las expresiones literales más útiles para encontrar las conversaciones originales son:

- `intérprete LLM con procedencia`
- `LocalLlamaInterpreter.operativo()`
- `evidencia → intérprete → propuesta`
- `INTERPRETATION_VALIDATION_FAILED`
- `PENDIENTE_INTERPRETACION`
- `falta superar el banco local`
- `/models` y `HTTP 503`
- `CRIBA → mechanism → dossier`
- `SupraClient`
- `ASTRA 6 — Decisión existencial del producto`
- `ASTRA Reconcile`

Las conversaciones más relevantes señaladas por las referencias recuperadas son «ASTRA 6 — Decisión existencial del producto», las notas del 21 de septiembre, las del 30 de septiembre al 1 de octubre y la auditoría del intérprete/Shadow UI de los días 2 y 11 de octubre de 2026.

## 9. Conclusión

Sí existen antecedentes de una arquitectura conceptual para el intérprete causal de CRIBA–BLACKFORGE–SUPRA. Los elementos más importantes son la procedencia de la evidencia, la separación entre propuesta del LLM y validación determinista, la preservación semántica en la cadena CRIBA → SUPRA, la persistencia verificable y los estados honestos de la Shadow UI.

No obstante, el historial resumido no basta para asegurar que la especificación esté completa, que todos los códigos de error estén implementados ni que la integración esté funcionando de extremo a extremo.

La siguiente comprobación técnicamente sólida sería contrastar estas referencias con el repositorio canónico y la rama activa: inspeccionar los entrypoints y contratos del intérprete, trazar el flujo real hasta SUPRA y la UI, reproducir el caso `/models` HTTP 503, revisar persistencia y reinicios, y ejecutar tests dirigidos y de integración. Hasta entonces, las afirmaciones sobre el comportamiento actual deben permanecer como **no verificadas**.
