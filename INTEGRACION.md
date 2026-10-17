# Guía de integración del Estatuto EEIMC-001

## Objetivo

Incorporar una norma de trabajo común a un repositorio, carpeta, aplicación o agente de IA. La integración más robusta combina el texto íntegro, instrucciones de entrada y controles observables. Copiar un archivo sin conectar las instrucciones del agente no obliga técnicamente a que este lo lea.

## Paquete

- `ESTATUTO_EXCELENCIA_INTEGRIDAD_MEJORA_CONTINUA.md`: norma maestra legible por humanos y agentes.
- `AGENTS.md`: instrucción de entrada orientativa para agentes que respetan archivos de instrucciones por repositorio.
- `PROMPT_ARRANQUE.md`: mensaje inicial reusable cuando la plataforma no descubre automáticamente el archivo de instrucciones.
- `CONTROL_PREVIO.md`: checklist breve para inicio y cierre de tareas.
- `ESTATUTO_EXCELENCIA_INTEGRIDAD_MEJORA_CONTINUA.docx`: edición de lectura y distribución.

## Instalación básica en un repositorio

1. Copia el Estatuto íntegro a la raíz del repositorio, sin resumirlo ni cambiar su identificador.
2. Integra el contenido de `AGENTS.md` en el archivo de instrucciones que use tu plataforma. Si ya existe, conserva su contenido y fusiona las reglas; no lo sobrescribas a ciegas.
3. Coloca `CONTROL_PREVIO.md` en una ruta visible para revisiones y plantillas de tarea.
4. Si la herramienta no carga instrucciones de repositorio automáticamente, incorpora `PROMPT_ARRANQUE.md` a la configuración del agente o al inicio de la sesión.
5. Confirma que un agente pueda localizar y leer el documento completo. Si la política excede el contexto disponible, configura recuperación por secciones y exige completar la lectura antes de permitir cambios.
6. Añade gates técnicos adecuados al proyecto: comprobación de presencia/versionado, plantilla de PR con pruebas ejecutadas, revisión de evidencias o bloqueos de despliegue. No afirmes que una verificación de archivo garantiza la obediencia del modelo.
7. Verifica la integración con una tarea de prueba de solo lectura: el agente debe identificar versión, objetivo, límites de autorización, etiquetas de evidencia y puerta de mejora sin cambiar archivos.

## Integración con otras plataformas

- Mantén el Estatuto en una ruta canónica y estable.
- En el mensaje de sistema, instrucciones del proyecto o configuración equivalente, ordena leer la ruta canónica antes de trabajar.
- En plataformas que admitan varias instrucciones, conserva también sus reglas específicas en vez de eliminarlas.
- En tareas lanzadas por automatizaciones, scripts o IDE, incluye un paso explícito que cargue las instrucciones y falle de forma segura si el documento no está disponible.
- Para carpetas sin control de versiones, guarda una copia de la política, una huella de versión y una copia de seguridad antes de modificar instrucciones existentes.
- Para aplicaciones que usan agentes por API, carga el Estatuto en el contexto de instrucciones de servidor o como política versionada recuperada al inicio de cada tarea. No confíes únicamente en que el usuario lo adjunte a veces.

## Niveles de obligatoriedad

**Nivel 1 — Documental:** el archivo existe; no garantiza que el agente lo lea.

**Nivel 2 — Instruccional:** el punto de entrada del agente exige leer la política y seguirla.

**Nivel 3 — Verificable:** además de lo anterior, el agente debe producir evidencias y pasar checklists de tarea o revisión.

**Nivel 4 — Parcialmente automatizado:** las operaciones de escritura, merge o despliegue pasan por wrappers, hooks, revisión humana o gates de CI que pueden bloquear acciones cuando faltan requisitos verificables.

No existe un método universal que, mediante un documento estático, garantice que cualquier modelo obedecerá absolutamente. El nivel 4 proporciona controles técnicos observables, pero también depende de la cobertura y configuración del entorno.

## Política de cambios

- No reemplaces una política previa sin leerla y comparar su alcance.
- No elimines instrucciones de seguridad, permisos o reglas específicas de la plataforma.
- Revisa primero `git status`, los cambios existentes y las diferencias.
- Mantén un registro de versión y cambios.
- Toda excepción debe ser explícita, de alcance limitado y autorizada.

## Prueba de aceptación de la integración

La integración se considera **VERIFICADA EN EL ALCANCE PROBADO** solo si se ha comprobado que:

1. el agente descubre la ruta correcta;
2. puede leer la política completa;
3. reconoce las restricciones y no se atribuye permisos adicionales;
4. realiza una inspección inicial de solo lectura;
5. propone criterios de aceptación y pruebas apropiadas;
6. aplica la puerta adversarial antes de cerrar;
7. informa con veracidad de lo ejecutado y lo pendiente;
8. los controles automáticos existentes bloquean los casos que se hayan configurado para bloquear.

La prueba demuestra solo el comportamiento observado en ese entorno y versión; no certifica todos los modelos ni todas las tareas futuras.
