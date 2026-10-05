# Aplicación de la auditoría externa de Hermes

El informe examinó `main` en `15bc237`. Esta revisión se aplica sobre la rama de
Shadow/SUPRA `b91e43c`, con el nuevo contrato del intérprete. El objetivo es obtener
hipótesis específicas y contrastables, conservando los resultados que permiten
medir si realmente mejoran ideas. Ninguna etiqueta o score del modelo acredita
novedad, causalidad o aprendizaje.

| Hallazgo | Decisión y resultado |
| --- | --- |
| F01, dossier sin prueba discriminante | La prueba estructurada del intérprete alimenta los campos de SUPRA; el recorrido real Qt–HTTP–persistencia–reinicio está verificado. |
| F02, fingerprint con defaults | Vectores compartidos y validación del envelope mantienen la identidad compatible. |
| F03, timeout fijo | Se respeta el timeout del perfil en generación semántica y en el intérprete local. La interfaz permite editarlo. |
| F04, contenido nulo y presupuesto de reasoning | El transporte preserva diagnóstico y contabilidad. Presupuesto externo por defecto de 8192; reasoning optativo y explícito. Un contenido nulo queda pendiente. |
| F05, veredicto literal y score aceptados | El contrato rechaza autoasignaciones, exige tipos reales, mecanismo, restricciones y crítica completa. |
| F06, versiones incompatibles | Paquete, API y MCP usan la misma versión de distribución; el bundle incluye los metadatos. |
| F07, URLs antiguas | La rama actual ya utiliza Klsx-Moli/Criba-Blackforge-Supra. |
| F08, fallback que simula juicio | No hay sustitución silenciosa por heurísticas ni por otro proveedor. |
| F09, campos ignorados | Timeout, slots, tokens, temperatura y modo rápido se cablean al runtime correspondiente. `key_env` no es credencial local admitida; se documenta la variable externa válida. |
| F10, licencia de SUPRA | No se cambia una licencia mediante una reparación técnica: el texto requiere una decisión explícita del titular. Queda pendiente de esa decisión. |
| F11, entorno y pytest-timeout | SUPRA dispone de entorno propio y la CI instala sus dependencias bloqueadas para el recorrido real. No se agrega una dependencia sólo para aceptar una bandera del auditor. |
| Módulos sin consumidores productivos | Se conservan las APIs y pruebas; conectarlos artificialmente no probaría innovación. |

## Qué mejora y qué aún debe medirse

El flujo solicita operaciones específicas de ambas técnicas, cadena causal,
conocimiento previo, incertidumbre, baseline y alternativa explicativa con
predicciones distintas. Exige abstención ante restricciones imposibles y evita
que frases genéricas, errores de red o scores declarados se presenten como éxitos.
Esto mejora el contrato de salida y su auditabilidad; no demuestra que el modelo
genere ideas superiores.

El banco fijo es una puerta de admisión limitada. Sus positivos y negativos son
públicos y no constituyen un conjunto independiente para medir generalización.
Para acreditar ventaja hay que comparar, con el mismo modelo y presupuesto,
CRIBA y una propuesta directa, en problemas reservados; revisar a ciegas mecanismo,
factibilidad y utilidad; buscar antecedentes y ejecutar las pruebas discriminantes.
Las diferencias de una única pregunta del informe no justifican elegir un modelo
ganador ni declarar novedad. La arquitectura científica causal mantiene D3, D4,
D6 y D8 sin acreditar y AntiGoodhart OFF canónico.

Referencias técnicas: [reasoning y presupuesto de salida](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens),
[términos oficiales Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt).

## Evaluación local real de esta revisión

El 5 de octubre se arrancó temporalmente el GGUF configurado, Llama 3.1 8B Q4_K_M,
y se ejecutaron ocho peticiones (cuatro casos, dos repeticiones) con el perfil real:
timeout 120 s, salida máxima 2600 tokens, temperatura 0.45 y modo rápido.
El banco no fue superado: sólo el caso irrelevante produjo abstención correcta en
ambas repeticiones. Los otros tres quedaron en ERROR por incumplir el contrato.
La tasa de respuestas válidas fue 0.25; la abstención correcta, 1/3. La consistencia
1.0 incluye errores repetidos y no expresa calidad. No se ejecutó una referencia.

El modelo inventó restricciones en el positivo, ignoró evidencia contradictoria y
sostuvo que podía transferir registros sin transmitir datos. No se atribuyen éxitos
ni novedad a esas salidas. El informe completo conserva los ocho textos y motivos en
`C:\ASTRA_WORK\VERIFICATION\interpreter-hardening-20261004\hermes-audit-local-bank-after.json`.
El servidor propiedad de la evaluación se cerró al terminar. Space Bunny a través
de un proxy disponible para CRIBA no fue evaluado; usarlo dentro de Hermes no crea
ese endpoint automáticamente.
