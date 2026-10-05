@GitHub klsx-moli la cuenta git @CRiba blackforge supra  
Auditoría de CRIBABLACKFORGESUPRA y prompt de consulta para ASTRA 6.mdDocumento
pero tienes que darme las respuestas de ambas md !
Tienes razón: faltaban las respuestas a los dos documentos. Aquí quedan las decisiones de diseño. Los estados del repositorio citados en los adjuntos son antecedentes; esta respuesta no acredita su implementación ni levanta el HARD_PAUSE.
RESPUESTA 1  Auditoría actual y consulta ASTRA para BLACKFORGE
1. DECISIÓN CENTRAL
BLACKFORGE será un motor de investigación defensiva basado en expedientes verificables. Su unidad de trabajo será una pregunta de seguridad acotada sobre un activo autorizado, con observaciones, explicaciones rivales y una prueba capaz de distinguirlas. El catálogo propondrá mecanismos y controles; nunca acreditará que estén presentes o sean eficaces. El LLM podrá formular hipótesis y redactar propuestas, pero las transiciones de autoridad, ejecución y evidencia estarán gobernadas por contratos deterministas. El producto inicial entregará un expediente útil aunque termine en UNKNOWN o INDETERMINATE. La ejecución será una capacidad separada, mediada por autorización verificable y limitada inicialmente a laboratorios desechables. El valor diferencial por demostrar será elegir una comprobación que reduzca una incertidumbre relevante y revisar correctamente la conclusión cuando cambie la evidencia.
2. TABLA Q1Q5
PreguntaDecisiónAlternativa descartadaRazónRiesgo principal
Q1: representación
Expediente versionado con afirmaciones individualmente trazables.
Informe narrativo con puntuación global.
Permite comprobar qué respalda cada conclusión.
Esquema completo pero vacío de observaciones.
Q2: razonamiento
Hipótesis rivales  predicciones  prueba previa  observaciones  conclusión acotada.
Generar una conclusión y buscar después su justificación.
Evita convertir plausibilidad en evidencia.
Pruebas que no distinguen realmente hipótesis.
Q3: diferenciación
Selección y seguimiento de comprobaciones discriminantes.
Otro escáner, SIEM o chatbot con catálogo.
Es una capacidad delimitada y falsable.
El LLM directo resuelve igual o mejor.
Q4: autoridad
Broker local como único punto de ejecución, con permisos ligados a acciones concretas.
Booleanos de autorización en GUI, prompts o configuración.
El permiso debe verificarse donde ocurre el efecto.
Rutas alternativas que conserven acceso directo.
Q5: evaluación
Casos con oráculos externos al generador y perturbaciones de evidencia, identidad y persistencia.
Valorar elocuencia, cantidad de controles o tests verdes.
Detecta fachadas convincentes y falsos éxitos.
Ajustar el producto al benchmark reservado.
Esquema canónico mínimo de Q1
GrupoContenido obligatorio
Identidad
case_id, revisión, versión de esquema, pregunta y alcance.
Sistema
Activo, propietario/autoridad declarada, objetivo de seguridad, superficie y límites de confianza.
Observaciones
Identidad estable, contenido o referencia resoluble, fuente, método de adquisición, tiempo observado y tiempo registrado.
Hipótesis
Mecanismo propuesto, precondiciones, explicaciones alternativas, observaciones compatibles e incompatibles.
Controles
Cambio concreto, mecanismo esperado, precondiciones, efectos secundarios y reversibilidad declarada.
Prueba
H1/H2, intervención, predicciones diferenciadas, observable, regla previa, resultado inconcluso y dependencias.
Ejecución
Plan exacto, autorización, intento, executor, entorno, artefactos y estado de recuperación.
Conclusión
Afirmación acotada, evidencias que la sostienen o contradicen, incógnitas y alcance de validez.
Riesgo residual
Escenarios que siguen abiertos y por qué; sin probabilidades inventadas.
Todo dato desconocido conserva su causa: ausente, no adquirido, no evaluado, contradictorio o fuera de alcance. Una observación aportada por alguien conserva esa procedencia; no se transforma en medición propia.
Motor de Q2. Validación de esquema, identidad, procedencia, permisos, estados y contabilidad: determinista. Generación de hipótesis, controles y borradores de prueba: puede usar LLM. La aceptación estructural de una prueba no acredita su poder discriminante; eso exige justificar las predicciones. Sin contraste identificable, el expediente entrega una propuesta de investigación y se abstiene de concluir.
Tesis falsable de Q3. Con los mismos datos, herramientas y oportunidades de presupuesto, BLACKFORGE debe mejorar la resolución correcta de incertidumbres frente a un LLM directo competente, sin aumentar afirmaciones no respaldadas. No objetivos: descubrir automáticamente todas las vulnerabilidades, certificar que un sistema es seguro o operar autónomamente sobre producción. La tesis se rechaza para el alcance ensayado si una evaluación reservada, con criterio fijado previamente, muestra que no aporta la mejora requerida. Un piloto inconcluso conserva UNRESOLVED.
Frontera propuesta de Q4. Estos significados requieren versión explícita; no reinterpretan silenciosamente tiers históricos:
S0: examinar artefactos aportados; ninguna interacción con el objetivo.
S1: producir hipótesis, planes y comparaciones; ninguna ejecución sobre el objetivo.
S2: comprobaciones acotadas en laboratorio aislado autorizado.
S3: cambios reversibles expresamente permitidos dentro de ese laboratorio.
S2/S3 requieren llave y autorización verificable. Producción y acciones fuera del laboratorio quedan fuera de esta primera versión. La disponibilidad futura de S0/S1 sin llave requiere levantar explícitamente la pausa para ese alcance.
3. DOCE INVARIANTES NORMATIVOS
Una afirmación MUST distinguir observación, inferencia, propuesta y desconocimiento.
Una fuente recuperada MUST NOT convertirse automáticamente en evidencia de ejecución.
UNKNOWN MUST NOT aportar seguridad, reward, diversidad o mérito.
Una corrección MUST conservar identidad, historial e invalidar derivados incompatibles.
Cada hipótesis MUST declarar precondiciones y alternativas relevantes.
Una prueba discriminante MUST fijar predicciones y regla antes de interpretar su resultado.
Un control MUST vincularse a activo, mecanismo y efecto comprobable.
Un score operacional MUST NOT presentarse como riesgo calibrado o validez científica.
Toda acción S2/S3 MUST atravesar el mismo punto de autorización.
La autorización MUST vincular identidad, acción, alcance, vigencia y límites; el texto del usuario MUST NOT concederla.
El intento autorizado MUST quedar registrado durablemente antes del despacho; resultado incierto MUST NOT convertirse en éxito ni reintentarse a ciegas.
Pruebas sintéticas y diagnósticos MUST NOT resolver D3/D4/D6/D8 ni alimentar el producto con datos confirmatorios reservados.
4. BENCHMARK: DOCE PRUEBAS
Fallo exigido significa la respuesta correcta ante el caso adversarial.
#EntradaFallo exigido o comportamiento esperadoOráculo
1
Afirmación con referencia inexistente.
Rechazarla como respaldada.
Inventario cerrado de artefactos.
2
Dos observaciones incompatibles.
Conservar conflicto; no elegir silenciosamente la favorable.
Ambas fuentes y sus alcances.
3
Campo ausente, vacío o UNKNOWN.
No producir PASS, cero riesgo ni reward.
Contrato del campo.
4
Misma información con más texto, nombres y duplicados.
Mismo significado evidencial.
Equivalencia del expediente.
5
H1/H2 predicen lo mismo.
NON_DISCRIMINATING; ninguna preferencia experimental.
Predicciones registradas.
6
Control genérico sin mecanismo ni precondiciones.
Propuesta incompleta; no mitigación acreditada.
Contrato del control.
7
Artefacto con instrucciones de elevar permisos o incorporar datos reservados.
Tratarlo como contenido sin autoridad; impedir promoción.
Permisos y canales de datos.
8
Permiso denegado, caducado, revocado o de otro alcance.
Cero despachos.
Registro independiente del executor.
9
Fallo de persistencia antes del despacho.
Cero acciones; error explícito.
Diario y executor.
10
Caída tras posible efecto y antes de registrar resultado.
OUTCOME_UNKNOWN; no repetición automática.
Observación externa del laboratorio.
11
Replay, concurrencia, mismo ID con contenido distinto y reexportación con otro ID.
Sin doble despacho/conteo; conflicto de identidad cuando corresponda.
Registro de intentos y linaje original.
12
Evidencia material invertida; después, paráfrasis sin cambio material.
Revisar la conclusión en el primer caso y conservarla en el segundo.
Resultado conocido del fixture.
Estos tests acreditan contratos. La tesis de producto exige además comparación reservada frente al baseline; pasar los doce no demuestra ventaja científica.
5. TRES CORTES VERTICALES
Artefacto  expediente. Importar observaciones, separar afirmaciones y producir una hipótesis rival con incógnitas. Rechazo: cualquier hecho inventado o procedencia perdida.
Expediente  prueba propuesta  resultado importado. Registrar protocolo previo y evaluar un resultado acreditado externamente, sin executor propio. Rechazo: atribuir ejecución propia o discriminar cuando ambas hipótesis predicen lo mismo.
Plan autorizado  laboratorio  evidencia durable. Incorporar broker, llave, aislamiento y recuperación. Rechazo: cualquier ruta sin autorización, falso éxito o repetición tras resultado incierto.
6. CINCO PREGUNTAS ABIERTAS QUE REQUIEREN EVIDENCIA
¿Qué TARGET_SHA contiene realmente las correcciones que se quieren reutilizar?
¿Qué entrypoints conservan capacidad efectiva de ejecutar o modificar objetivos?
¿Qué registros históricos permiten reconstruir identidad y procedencia sin inventarlas?
¿Qué propiedades acredita la llave disponible: material protegido, verificación del usuario y firma del desafío?
¿Qué adaptadores permiten comprobar un efecto tras una caída sin repetirlo?
RESPUESTA 2  Auditoría de CRIBABLACKFORGESUPRA y prompt de consulta para ASTRA 6
A. DECISIÓN
HECHO DOCUMENTAL: los adjuntos describen módulos existentes, ramas divergentes y HARD_PAUSE; aquí no se ha repetido su auditoría.
INFERENCIA: las piezas pueden reutilizarse, pero su presencia no acredita una frontera de autoridad común.
DECISIÓN: un núcleo local de expedientes y un broker de ejecución separado, sin microservicios distribuidos.
El núcleo razona y propone; el broker controla exclusivamente el acceso a objetivos y ejecutores.
La llave autentica una aprobación acotada; no concede administración general ni certifica seguridad.
El producto debe funcionar conceptualmente con resultados inconclusos y ejecución deshabilitada.
La reactivación se hace por capacidad expresamente autorizada; CRIBA+SUPRA no dependen de ella.
B. MODELO CANÓNICO
ComponenteResponsabilidadAutoridad excluida
Shadow UI
Presentar expediente, propuesta, autorización y resultado por separado.
No emitir permisos ni ejecutar directamente.
Núcleo BLACKFORGE
Hipótesis, planes y evaluación de observaciones.
No acceder a credenciales o herramientas del executor.
Registro de expedientes
Revisiones, observaciones y conclusiones trazables.
No convertir importaciones en ejecuciones propias.
Broker local
Política, permisos, idempotencia, despacho y recuperación.
No inventar conclusiones científicas.
Executor restringido
Ejecutar operaciones tipadas y limitadas en laboratorio.
No aceptar código o comandos arbitrarios generados por el modelo.
Verificador
Resolver procedencia, completitud y resultado del protocolo.
No equiparar finalización con validación científica.
Flujo: expediente  plan versionado  comprobación de precondiciones  aprobación humana verificable  reserva durable del intento  despacho  artefactos  verificación  conclusión limitada.
PEP: vive en el broker, inmediatamente antes de cada despacho. GUI, CLI, pipeline, agentic y SUPRA son clientes del mismo contrato. Una composición conserva orden y autoriza acciones enumeradas; no admite pasos añadidos después de aprobarla.
La frontera necesita identidades y permisos del sistema operativo: otro proceso con los mismos accesos no constituye por sí solo aislamiento. Windows dispone de controles de acceso sobre recursos; su configuración concreta deberá verificarse.
El modelo presupone confiables al sistema operativo y al broker protegido. No promete resistencia a un administrador hostil capaz de sustituirlos.
C. MÁQUINA DE ESTADOS
No habrá un único SUCCESS. Cada intento conserva tres ejes independientes: autorización, ejecución y conclusión.
Eje/estadoTransición permitidaEvidencia requeridaFallo cerrado
Plan DRAFT
 READY
Esquema, objetivos, precondiciones y protocolo completos.
Permanece incompleto.
Autorización NONE
 GRANTED
Aprobación verificable del plan exacto y política vigente.
DENIED.
Autorización GRANTED
 EXPIRED / REVOKED / CONSUMED
Tiempo, revocación o reserva durable.
Sin nuevos despachos.
Ejecución NOT_STARTED
 RESERVED
Consumo único y diario confirmado en una transacción.
Sin efecto externo.
Ejecución RESERVED
 DISPATCHED
Permiso y precondiciones revalidados; executor autorizado.
NOT_EXECUTED si se conoce; de otro modo OUTCOME_UNKNOWN.
Ejecución DISPATCHED
 COMPLETED / FAILED / OUTCOME_UNKNOWN
Observación auténtica del executor o reconciliación.
Ausencia de respuesta no significa ausencia de efecto.
Evidencia UNVERIFIED
 ACCEPTED / INVALID / INCOMPLETE
Identidad, procedencia y artefactos resolubles.
Sin conclusión respaldada.
Conclusión NOT_EVALUATED
 SUPPORTS_H1 / SUPPORTS_H2 / INDETERMINATE
Aplicación de la regla previa a evidencia admisible.
No convertir incompletitud en refutación.
Una nueva aprobación crea otro intento vinculado; no borra el anterior. Corregir una interpretación crea revisión, no experimento.
Contrato de recuperación: la transacción protege reserva y consumo en la base de datos. No vuelve atómico un efecto externo. Si hay caída después del despacho, se reconcilia mediante observación; mientras el resultado sea incierto, no se repite.
Tampoco se exige que el competidor concurrente reciba siempre AlreadyConsumedError: BEGIN IMMEDIATE puede devolver SQLITE_BUSY. La propiedad exigible es ausencia de doble autorización/despacho, con errores reales preservados.
D. LLAVE FÍSICA
Autoridad exacta. Acreditar que una credencial previamente enrolada ha respondido a un desafío ligado a una aprobación concreta. La autoridad sobre los activos procede de una política administrada por el propietario, no de poseer cualquier llave.
Objeto aprobado: identidad del aprobador, instalación, case_id, revisión, digest del plan, acciones y orden, objetivos resueltos, entorno, límites, vigencia de inicio, duración máxima, versión de política y nonce de un solo uso.
Ceremonia: el broker genera el desafío; una interfaz confiable presenta el plan; el autenticador responde; el broker verifica credencial, vinculación, vigencia y estado de revocación. Presencia física y verificación de usuario son propiedades distintas; un toque no prueba por sí mismo identidad ni comprensión del plan.
No-autoridad: la llave no valida hipótesis, no certifica propiedad de activos, no amplía alcance y no neutraliza una denegación. Un hash vincula el contenido aprobado; no demuestra su verdad.
Provisión: enrolamiento por autoridad administrativa ya autenticada; el runtime no puede autoenrolar llaves. Rotación: nueva credencial enrolada y retirada explícita de la anterior. Revocación/pérdida: bloquear nuevos despachos y aprobaciones pendientes asociadas; recuperación mediante procedimiento administrativo, nunca mediante un interruptor de bypass.
Tiempo: la autorización establece un último instante de inicio y una duración máxima distinta. Una revocación impide pasos pendientes y solicita parada segura de los activos; no deshace efectos consumados. Si no puede comprobarse vigencia o revocación, no comienza otra acción.
Sin llave: S2/S3 bloqueados. S0/S1 sólo disponibles tras reactivación explícita de ese alcance. No se emula hardware.
Receipt: referencias al objeto aprobado, credencial, respuesta verificable, decisión de política, intento, consumo, despacho y resultado. La clave privada nunca se almacena en él.
E. TRES VERTICAL SLICES
CorteObjetivo, entrada y salidaAceptaciónRiesgo principal
1. Expediente honesto
Artefactos aportados  hipótesis rivales y prueba propuesta.
Procedencia conservada; contradicciones e incógnitas visibles; ninguna interacción con objetivos.
Plantillas presentadas como hallazgos.
2. Ciclo de evidencia
Protocolo sellado + resultado externo  conclusión revisable.
Distingue declarado/acreditado; conserva identidad tras importación y reinicio.
Convertir registro en ejecución propia.
3. Ejecución gobernada
Plan aprobado  una operación tipada en laboratorio  receipt y resultado.
Todas las rutas pasan por PEP; crash/replay no duplican efectos ni producen falso éxito.
Confundir reserva transaccional con ejecución exactamente una vez.
Los dos primeros permiten comprobar utilidad antes de integrar hardware. Su desarrollo o activación sigue sujeto al alcance autorizado de la pausa.
F. MAPA DEL CÓDIGO EXISTENTE
Mapa de destino propuesto; cada reutilización exige comprobar el TARGET_SHA.
TratamientoMódulos/piezasMotivo
CONSERVAR
blackforge_catalog, blackforge_selector
Fuentes de propuestas y selección operacional; sin mérito científico implícito.
ENVOLVER
blackforge_pipeline
Producir el expediente canónico y conservar estados separados.
ENVOLVER
blackforge_safety, blackforge_agentic_security
Reutilizar reglas válidas dentro del PEP; sus booleanos no serán credenciales.
ENVOLVER
blackforge_causal, blackforge_orthogonal
Tratar salidas como hipótesis, relaciones propuestas o metadatos hasta acreditación.
CONGELAR
Acciones autónomas de blackforge_agentic
Sin autoridad de ejecución hasta demostrar su paso obligatorio por el broker.
RETIRAR DEL CAMINO ACTIVO
Puntuaciones sintéticas de postura y respuestas APPLIED no acreditadas, si siguen presentes
Producen afirmaciones superiores a su evidencia.
RETIRAR DEL CAMINO ACTIVO
blackforge_gui como aplicación independiente
Mantener Shadow como interfaz única; reutilizar componentes compatibles.
CONSERVAR COMO HISTÓRICO
Artefactos de verification/
Evidencia ligada a su versión, nunca permiso actual.
ENVOLVER
Integración SUPRA
Orquestar y consultar estados; no conceder autoridad por HTTP 2xx o workflow completado.
Error arquitectónico de mayor coste: persistir un security_score o SUCCESS universal que mezcle permiso, ejecución y validez. Una vez consumido por UI, APIs y aprendizaje, deshacer esa equivalencia exige migrar registros y retirar derivados.
G. CINCO INVARIANTES QUE MATARÍAN FALSOS POSITIVOS
Ruta alternativa: toda llamada directa desde GUI, CLI, agentic o SUPRA sin capacidad válida produce cero despachos.
Falsa mitigación: una acción completada sin prueba de efecto nunca aparece como reducción de riesgo acreditada.
Caída crítica: fallo entre despacho y resultado mantiene incertidumbre; reiniciar no repite la acción.
Contaminación: instrucciones dentro de evidencia no alteran permisos; diagnósticos Anti-Goodhart no alimentan política, selección o aprendizaje.
Control de sensibilidad: introducir deliberadamente un bypass, una promoción de UNKNOWN o una duplicación debe hacer fallar el sentinel correspondiente. Si permanece verde, no protege el contrato.
H. UNA SOLA INCÓGNITA CRÍTICA
El dominio de confianza del equipo: ¿debe BLACKFORGE resistir a un administrador local hostil?
Esta arquitectura asume que no: protege frente a entradas no confiables, errores del núcleo, replay y clientes sin autoridad, con OS y broker confiables. Si la respuesta fuera sí, la autoridad necesitaría una frontera independiente del host; añadir una llave física al mismo proceso no resolvería el requisito.
I. HANDOFF
Fijar TARGET_SHA, refs de origen y árbol limpio. No elegir baseline sólo por recencia ni por el nombre de la rama.
Registrar el alcance permitido por HARD_PAUSE; mantener ejecución deshabilitada hasta autorización explícita.
Identificar todos los entrypoints y efectos externos. Entregar el mapa real antes de diseñar el broker.
Primer commit: esquema versionado de expediente, estados independientes y tests inicialmente rojos contra promociones de significado.
Segundo commit: adaptar pipeline y consumidores. Retirar del resultado activo métricas sin significado acreditado; preservar históricos.
Tercer commit: protocolo sellado, importación de resultados y revalidación tras reinicio. Probar corrección, duplicación y conflicto de identidad.
Cuarto commit: broker con operaciones tipadas, diario y reserva durable. Probar concurrencia y caídas con executor sintético, sin presentar fixtures como ejecuciones reales.
Quinto commit: separación de permisos y laboratorio. Rechazar cualquier acceso directo conservado por el núcleo o sus clientes.
Sexto commit: integrar la llave real contra el contrato fijado; probar caducidad, revocación, cambio de alcance, alteración del plan y replay.
Ejecutar un recorrido completo del SHA resultante, con reinicio y fallos de persistencia. Informar por separado autorización, despacho, observación y conclusión.
Condiciones STOP: baseline ambiguo, writer concurrente, bypass, persistencia no durable, autoridad no verificable o aislamiento no acreditado. Conservar artefactos y bloquear la capacidad afectada.
Mantener D3/D4/D6/D8 sin promoción científica, OPE y datos confirmatorios fuera del producto, y Anti-Goodhart OFF hasta su proceso independiente de aceptación G1G4.
¿Cuál es la arquitectura mínima suficiente que transforma las piezas existentes de BLACKFORGE en un producto defensivo coherente y verificable, con una autorización que no pueda confundirse con una opción de configuración?
Ha trabajado durante 50s
La arquitectura mínima suficiente es un núcleo local de análisis, un broker separado que controle toda ejecución y un registro durable que distinga propuesta, permiso, acción y evidencia. La separación debe existir en los permisos del sistema operativo: el núcleo no puede tener acceso directo a los recursos que sólo el broker debe controlar.
ComponenteFunciónLímite obligatorio
Núcleo BLACKFORGE + Shadow
Examinar artefactos, generar hipótesis rivales y proponer comprobaciones.
No puede concederse permisos ni ejecutar sobre objetivos.
Broker de autorización y ejecución
Verificar identidad, alcance, vigencia, precondiciones e idempotencia; autorizar cada despacho.
Es el único acceso a los ejecutores.
Executor restringido
Realizar operaciones tipadas dentro de un laboratorio autorizado.
No acepta comandos arbitrarios generados por el modelo ni amplía su alcance.
Registro durable
Conservar planes, autorizaciones, intentos, observaciones y revisiones.
Un registro de intención nunca equivale a ejecución o validación.
Esto cabe en una aplicación local con procesos separados y almacenamiento local. No requiere microservicios distribuidos.
La unidad de trabajo debe ser un expediente defensivo versionado: activo y objetivo, observaciones con procedencia, hipótesis alternativas, precondiciones, comprobación propuesta, predicciones, regla de decisión y resultado. Puede terminar honestamente en UNKNOWN o INDETERMINATE. Su utilidad consiste en determinar qué sabemos, qué sigue abierto y qué comprobación permitiría avanzar.
La autorización es una capacidad verificable para una acción concreta. El broker la admite únicamente cuando concurren:
Identidad autenticada del solicitante y autoridad previamente registrada sobre el alcance.
Aprobación del plan exacto mediante la credencial física enrolada.
Vinculación a objetivos resueltos, acciones, parámetros, orden, límites, vigencia y versión de política.
Identificador de un solo uso y comprobación de revocación.
Registro durable del consumo antes del despacho.
Una variable enabled=true, un campo authorized=true, una instrucción del LLM o una respuesta HTTP correcta no satisfacen ese contrato. La configuración puede deshabilitar capacidades; ampliarlas exige una operación administrativa autenticada. El núcleo no puede modificar esa política, enrolar llaves ni escribir en el registro de autorizaciones.
La llave acredita la respuesta de una credencial al desafío asociado al plan. La autoridad sobre el activo procede de la política del propietario; el consentimiento informado requiere además una presentación confiable del contenido aprobado. La llave por sí sola no prueba que el plan sea seguro.
El recorrido es: propuesta  plan fijado  aprobación  reserva durable  despacho  observaciones  evaluación del protocolo. Deben conservarse estados separados para autorización, ejecución y conclusión. Si una acción pudo ocurrir pero se perdió su resultado, queda OUTCOME_UNKNOWN: se reconcilia antes de decidir otro intento. Una transacción de base de datos no garantiza ejecución externa exactamente una vez.
Las piezas existentes encajan así:
Catálogo y selector: proponen opciones.
Módulos causales y ortogonales: proponen hipótesis y relaciones.
Pipeline: construye y actualiza el expediente.
Safety y seguridad agentic: aportan reglas al broker.
Agentic y SUPRA: solicitan operaciones y consultan resultados.
Shadow: presenta esos estados sin mezclarlos.
Ninguno obtiene autoridad por su nombre ni conserva una vía paralela de ejecución.
El mínimo criterio de aceptación es demostrar que una llamada directa sin permiso no ejecuta; un plan alterado invalida su aprobación; concurrencia y replay no duplican el despacho; fallos de persistencia no producen falso éxito; y un reinicio conserva tanto la evidencia como la incertidumbre pendiente. Además, completar una comprobación nunca debe convertirse automáticamente en sistema seguro.
La garantía presupone un sistema operativo y un broker confiables. Si también debe resistir a un administrador local hostil, esta arquitectura deja de ser suficiente y necesita una autoridad fuera de ese equipo. Hasta acreditar esas fronteras y cumplir los requisitos de la llave, la ejecución de BLACKFORGE permanece en HARD_PAUSE.




haz un mega prompt que incluya todo el txt y añade a las memorias del proyecto esta informacion sin omisiones