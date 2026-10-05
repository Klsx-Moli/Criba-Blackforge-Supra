# REGISTRO DE DECISIONES — BLACKFORGE / CRIBA / SUPRA

Fuente de cada decisión: SRC-P1 (§4), SRC-P2 (RESPUESTAS 1/2 + síntesis),
SRC-P3 (mandato v2). Estados: proposed / accepted_for_design / implemented /
wired / verified / retired. NINGUNA decisión de diseño acredita por sí sola
implementación.

## D1 · Producto BLACKFORGE = motor de investigación defensiva por expedientes
- Texto: unidad de trabajo = pregunta de seguridad acotada sobre activo
  autorizado, con observaciones, hipótesis rivales y prueba discriminante.
  Puede terminar útilmente en UNKNOWN/INDETERMINATE.
- Fuente: SRC-P2 §1/§2, SRC-P3 §7.
- Estado: accepted_for_design. No implementado como producto.
- Sustituye a: "otro chatbot con catálogo" / "score universal de seguridad".

## D2 · Arquitectura mínima: núcleo + Shadow + broker + executor + registro
- Texto: núcleo local razona y propone; broker = único punto de autoridad y
  despacho; executor restringido = operaciones tipadas en laboratorio; registro
  durable distingue propuesta/permiso/acción/evidencia; separación en permisos
  del SO (no basta otro proceso con los mismos accesos).
- Fuente: SRC-P2 §B/§síntesis, SRC-P3 §7.
- Estado: partially implemented en PR #11 (case+broker+slice);
  wired: NO (nada del producto activo pasa por el broker); verified: parcial
  (sólo contra executor sintético).

## D3 · Tres ejes independientes (no hay un único SUCCESS)
- Texto: autorización / ejecución / conclusión separadas. Plan DRAFT->READY,
  autorización NONE->GRANTED->EXPIRED/REVOKED/CONSUMED, ejecución
  NOT_STARTED->RESERVED->DISPATCHED->COMPLETED/FAILED/OUTCOME_UNKNOWN,
  evidencia UNVERIFIED->ACCEPTED/INVALID/INCOMPLETE, conclusión
  NOT_EVALUATED->SUPPORTS_H1/SUPPORTS_H2/INDETERMINATE.
- Fuente: SRC-P2 §C, SRC-P3 §8.
- Estado: implemented (4 enums) + verified (41 tests) en PR #11.

## D4 · Llave física: autoridad acotada, no configuración
- Texto: la llave acredita que una credencial ENROLADA respondió a un desafío
  ligado a una aprobación concreta. Objeto aprobado: identidad del aprobador,
  instalación, case_id, revisión, digest del plan, acciones y orden, objetivos,
  entorno, límites, vigencia, duración máxima, versión de política, nonce de un
  solo uso. Presencia física != verificación de usuario. No autoenrolamiento.
- Fuente: SRC-P2 §D, SRC-P3 §10.
- Estado: proposed. NOT implemented. No existe credencial real.
- Sustituye a: enabled=true, authorized=true, prompt del LLM, casilla GUI,
  HTTP 2xx, workflow completado, "poseer cualquier llave".

## D5 · Frontera de alcance S0/S1/S2/S3
- S0: examinar artefactos aportados, sin interacción con el objetivo.
- S1: hipótesis, planes, comparaciones; sin ejecución sobre el objetivo.
- S2: comprobaciones acotadas en laboratorio aislado autorizado.
- S3: cambios reversibles expresamente permitidos en ese laboratorio.
- S2/S3 requieren llave + autorización verificable. Producción fuera de v1.
- S0/S1 sin llave sólo tras reactivación explícita de ese alcance.
- Fuente: SRC-P2 §frontera Q4, SRC-P3 §6.
- Estado: proposed. HARD_PAUSE vigente: S0/S1 NO habilitados.

## D6 · Recuperación: reserva transaccional != exactly-once externo
- Texto: caída tras posible efecto -> OUTCOME_UNKNOWN; reconciliar por
  observación; no repetir a ciegas. No exigir un tipo concreto de error
  concurrente (BEGIN IMMEDIATE puede dar SQLITE_BUSY); exigir ausencia de doble
  consumo/despacho con errores preservados.
- Fuente: SRC-P2 §C, SRC-P3 §11.
- Estado: implemented + verified (test_neg_08, mut_08) en PR #11.

## D7 · Doce invariantes normativos
1. Toda afirmación distingue observación/inferencia/propuesta/desconocimiento.
2. Fuente recuperada NO se convierte en evidencia de ejecución.
3. UNKNOWN no aporta seguridad/reward/diversidad/mérito.
4. Corrección conserva identidad e historial e invalida derivados incompatibles.
5. Toda hipótesis declara precondiciones y alternativas.
6. Prueba discriminante fija predicciones y regla ANTES de interpretar.
7. Control ligado a activo, mecanismo y efecto comprobable.
8. Score operacional != riesgo calibrado ni validez científica.
9. Toda acción S2/S3 atraviesa el mismo punto de autorización.
10. Autorización liga identidad/acción/alcance/vigencia/límites; el texto del
    usuario no la concede.
11. Intento autorizado registrado durablemente ANTES del despacho; resultado
    incierto no se convierte en éxito ni se reintenta a ciegas.
12. Pruebas sintéticas/diagnósticos no resuelven D3/D4/D6/D8 ni alimentan el
    producto con datos confirmatorios reservados.
- Fuente: SRC-P2 §3, SRC-P3 (implícito §7-§12).
- Estado: mixed — parcialmente implemented en PR #11; sin cobertura en el
  producto activo.

## D8 · Benchmark de doce pruebas (contratos, no ventaja científica)
1 referencia inexistente · 2 observaciones incompatibles · 3 campo
ausente/vacío/UNKNOWN · 4 inflación de texto/duplicados · 5 H1/H2 no
discriminantes · 6 control genérico incompleto · 7 instrucciones maliciosas en
artefactos · 8 permiso denegado/caducado/revocado/fuera de alcance · 9 fallo de
persistencia antes de despacho · 10 caída tras posible efecto · 11
replay/concurrencia/conflictos/reexportación · 12 inversión material de
evidencia y paráfrasis equivalente.
- Fuente: SRC-P2 §4, SRC-P3 §12.
- Estado: implemented/verified PARCIAL en PR #11 (test_blackforge_v1_negative10
  cubre los 10 grupos; 26 tests + 15 mutaciones). Pasar los doce NO demuestra
  ventaja científica.

## D9 · Tesis falsable de producto (Q3)
- Con datos/herramientas/presupuesto comparables, BLACKFORGE debe mejorar la
  resolución correcta de incertidumbres frente a un LLM directo competente, sin
  aumentar afirmaciones no respaldadas. Criterio predefinido; piloto != eval
  confirmatoria; piloto inconcluso = UNRESOLVED.
- Fuente: SRC-P2 §tesis Q3, SRC-P3 §12.
- Estado: proposed. NOT tested.

## D10 · Tres cortes verticales BLACKFORGE
1. Artefacto -> expediente honesto (procedencia conservada; rechazo: hecho
   inventado o procedencia perdida).
2. Protocolo sellado + resultado externo -> conclusión revisable (rechazo:
   atribuir ejecución propia; discriminar sin contraste).
3. Plan autorizado -> laboratorio -> evidencia durable (rechazo: ruta sin
   autorización, falso éxito, repetición tras resultado incierto).
- Fuente: SRC-P2 §E/§5, SRC-P3 §13.
- Estado: cortes 1-2 sin executor propio = los ejecutables bajo pausa; corte 3
  bloqueado por falta de llave. Slice authz de PR #11 ≈ corte 3 declarativo.

## D11 · Mapa de tratamiento del código existente
- CONSERVAR: blackforge_catalog, blackforge_selector.
- ENVOLVER: blackforge_pipeline; blackforge_safety + blackforge_agentic_security
  (reglas dentro del PEP, sus booleanos NO son credenciales); blackforge_causal
  + blackforge_orthogonal (salidas = hipótesis hasta acreditación);
  integración SUPRA (orquesta, no concede autoridad por 2xx).
- CONGELAR: acciones autónomas de blackforge_agentic.
- RETIRAR DEL CAMINO ACTIVO: puntuaciones sintéticas de postura y respuestas
  APPLIED no acreditadas; blackforge_gui como app independiente.
- CONSERVAR COMO HISTÓRICO: artefactos de verification/.
- Error más caro a evitar: persistir un security_score/SUCCESS universal.
- Fuente: SRC-P2 §F. Estado: proposed; la rama activa NO ha migrado nada de esto.

## D12 · Cinco invariantes anti-falsos-positivos
1 ruta alternativa sin capacidad -> cero despachos · 2 acción sin prueba de
efecto != mitigación acreditada · 3 caída entre despacho y resultado mantiene
incertidumbre y no repite · 4 instrucciones en evidencia no alteran permisos ·
5 control de sensibilidad: introducir un bypass/promoción/duplicación DEBE
poner el sentinel en rojo.
- Fuente: SRC-P2 §G. Estado: 1,3,5 cubiertos parcialmente en PR #11; 2,4 en el
  núcleo de case (evidence origin gate).

## D13 · Incógnita crítica abierta (H)
- ¿Debe BLACKFORGE resistir a un administrador local hostil? La arquitectura
  ASUME que no (SO y broker confiables). Si la respuesta fuera sí, hace falta
  autoridad fuera del host; una llave local no lo resuelve.
- Fuente: SRC-P2 §H. Estado: UNRESOLVED — requiere decisión del usuario.

## D14 · Gobernanza y roles
- Hermes = único writer; 5 ASTRA read-only; ASTRA 6 = rótulo de consulta
  manual, no crea una sexta automatización ni concede autoridad.
- Fuente: SRC-P1 §2.4/§2.11, SRC-P3 §3. Estado: vigente.

## D15 · Prioridad de trabajo
- Carril A (producto): M2 real -> M3 restart/replay -> journeys ->
  Windows one-command -> licencia -> MVP package.
- Carril B (BLACKFORGE pausado): sólo continuidad/diseño/análisis; no desplaza
  al carril A; sin ejecución ni activación implícita.
- Fuente: SRC-P1 §2.9, SRC-P3 §13. Estado: vigente.
