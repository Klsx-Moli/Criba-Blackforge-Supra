# REGISTRO DE CONFLICTOS

Cada conflicto: conflict_id · fuentes · tipo · alcance · resolución propuesta ·
autoridad necesaria. No se resuelve por recencia, nombre de rama, elocuencia,
cantidad de tests ni preferencia del agente.

## C-01 · main vs rama de trabajo (baseline ambiguo)
- Fuentes: origin/main = 15bc237; rama activa = 2dc0094 (19 commits por delante).
- Tipo: divergencia de baseline.
- Alcance: todo el producto activo.
- Estado: NO es conflicto real una vez medido: la rama activa PARTE de main
  actual (merge-base = 15bc237) y sólo añade trabajo. main no contiene Shadow
  UI, ni version.py, ni los fixes del intérprete.
- Resolución propuesta: el baseline operativo es la RAMA DE TRABAJO, no main.
  Integrar a main exige PR + revisión; no hacer merge por recencia.
- Autoridad: usuario / PR review.

## C-02 · Shadow UI "no existe en el monorepo" vs "existe"
- Fuentes: skill criba-blackforge-supra-ops ("Shadow UI NO está en el
  monorepo, medido sobre main"); medición propia.
- Tipo: contradicción de estado por SHA.
- Alcance: UI.
- Medido: shadow_ui/ = 0 ficheros en origin/main; 28 en codex/interpreter-
  hardening-20261004 y en hermes/astra/shadow-supra-20261002; 0 en
  astra/blackforge-dossier-20261005.
- Resolución: AMBAS ciertas — depende del SHA. Sobre main no existe; en la rama
  activa SÍ. La afirmación de la skill describe main; hay que anclarla al SHA.
- Autoridad: ninguna pendiente (hecho medido). Corregir la skill al SHA.

## C-03 · Baseline de tests "1495 passed" vs "1737 passed"
- Fuentes: skill (1495 sobre main); medición propia en rama activa.
- Tipo: cifra histórica vs actual.
- Resolución: la cifra de la skill era de main; la rama activa da 1737 passed /
  3 skipped. Re-medir siempre; no copiar el número.
- Autoridad: ninguna (hecho).

## C-04 · Identidad de versión: unificada vs literal
- Fuentes: skill dice "regla INCUMPLIDA, version.py NO EXISTE"; medición propia.
- Medido: en main NO existe version.py y hay literales 0.1.0; en la rama activa
  version.py EXISTE y __init__/api/mcp lo consumen (0.3.0 desde pyproject).
- Resolución: la regla está CUMPLIDA en la rama activa e INCUMPLIDA en main. El
  pendiente real es integrar la rama; la skill debe anclarse al SHA.
- Autoridad: ninguna (hecho).

## C-05 · Estado del paquete Windows (EXE)
- Fuentes: final-verification.json (desktop_passed=true, rev 6ab032f) vs
  desktop-smoke-final/result.json (passed=false, exit 2) vs desktop-smoke-audit
  y desktop-smoke-clean (passed=true).
- Tipo: evidencia material contradictoria entre artefactos.
- Alcance: M5 / paquete.
- Resolución propuesta: NO declarar el paquete OK. Re-ejecutar el smoke del EXE
  contra el HEAD activo y registrar un único veredicto con su SHA.
- Autoridad: writer (Hermes) para re-medir; usuario para aceptar M5.

## C-06 · B01 (fingerprint del dossier) "resuelto remotamente" vs estado
- Fuentes: SRC-P1 §2.3 ("SCORING-01/miscal_x resuelto remotamente"; B01
  corregido).
- Medido: existe contrato de fingerprint en ambos lados (service.py y
  supra_client.py) y tests; el M2 E2E pasa end-to-end, lo que implica que el
  fingerprint cruza bien en esa ruta.
- Resolución: B01 está protegido en la rama activa por ejecución (M2 E2E), no
  sólo por reporte. Mantener.
- Autoridad: ninguna.

## C-07 · "6 campos vacíos del protocolo discriminante" (join roto) vs M2 E2E
- Fuentes: skill ("preparar_dossier desde entry REAL deja 6 campos vacíos;
  SUPRA responde 422 siempre") vs test M2 E2E que asevera NO obligación vacía
  (líneas 293-299) y pasa.
- Tipo: contradicción de estado / posible fix posterior.
- Medido: el test M2 recorre la ruta real y exige cada campo de
  prueba_discriminante no vacío; pasa (7 passed). Y supra_dossier.py ahora
  DERIVA los campos de fuente declarada con `raise` si falta (líneas 92-130).
- Resolución: en la rama activa el join parece CERRADO para la ruta M2. La
  afirmación de la skill describe una revisión anterior. Verificar con el test
  dirigido (ya verde) y anclar la skill al SHA.
- Autoridad: ninguna (hecho medido), pero conviene re-confirmar el caso "entry
  REAL de inventar()" fuera de la ruta del test antes de cerrar la skill.

## C-08 · "HARD_PAUSE vigente" vs ramas BLACKFORGE con cambios
- Fuentes: SRC-P3 §6 ("la existencia de ramas no acredita autorización");
  PR #11 abierta con 3318 líneas nuevas.
- Tipo: alcance/autorización.
- Resolución: PR #11 es un merge request (no mergeado). HARD_PAUSE sigue
  vigente: no hay llave, no hay executor real, execution_enabled=False. El
  código no ejecuta nada. Mantener pausa; el merge es decisión del usuario.
- Autoridad: usuario.

## C-09 · Tarjeta M2 "done" vs verificación en el HEAD activo
- Fuentes: kanban t_84ce5ac2 = done (workspace reconcile-15bc237, AUSENTE);
  test M2 en la rama activa = 7 passed.
- Tipo: aceptación por workspace histórico.
- Resolución: el "done" del board no acredita el HEAD activo por sí solo; el
  test M2 ejecutado AHORA en la rama activa sí lo acredita. Mantener M2
  aceptado sobre evidencia vigente, no sobre el board.
- Autoridad: ninguna (hecho).

## C-10 · Incógnita crítica H (administrador local hostil) sin resolver
- Fuentes: SRC-P2 §H; SRC-P1 §4.2.H.
- Tipo: decisión de alcance de amenaza.
- Resolución: PENDIENTE de respuesta del usuario. Hasta entonces, asumir SO y
  broker confiables y NO prometer resistencia a admin hostil.
- Autoridad: usuario (decisión explícita requerida).

## C-11 · "CRIBA_SUPRA_MASTER_CONTINUITY incluido íntegro" — AFIRMACIÓN FALSA
- Fuente: mi propio índice (10_INDICE_FUENTES.md, versión previa).
- Corrección del usuario: el primer mega prompt REFORMULÓ/COMPACTÓ ese
  documento; no lo reprodujo literalmente.
- Resolución: SRC-02 = original NO disponible; existe versión reformulada en
  SRC-P1 §2; NO acredita conservación literal. Corregido en el índice. El
  fichero fuente (00_SOURCE_…) NO se modifica; la corrección vive en el índice.
- Autoridad: ninguna (hecho).

## C-12 · "Medición independiente" — CALIFICADOR INCORRECTO
- Fuente: mi propio título previo "ESTADO VERIFICADO … medición independiente".
- Corrección del usuario: Hermes ejecutó las pruebas, pero es el writer; no es
  un verificador independiente. Título correcto: "Estado observado y pruebas
  ejecutadas por Hermes".
- Resolución: retitulado; nota de independencia añadida; plantilla de registro
  de ejecuciones aplicada (80_REGISTRO_EJECUCIONES.md).
- Autoridad: ninguna (hecho).

## C-13 · M2 "PASS" vs OFFSCREEN != Windows verificado
- Fuente: mi clasificación previa ("VERIFIED_BY_EXECUTION" como criterio de
  aceptación M2) vs el documento de continuidad (M2 no se demuestra sólo con
  GUI offscreen).
- Resolución: reclasificado como M2_INTEGRATION_OFFSCREEN = PASS reportado;
  M2_GUI_VISIBLE = NO ACREDITADO; M2_ACCEPTANCE = PENDIENTE.
- Autoridad: usuario/writer para ejecutar la comprobación en escritorio real.

## C-14 · "Divergió" — EXPRESIÓN IMPRECISA
- Fuente: mi redacción previa ("HEAD NO es ancestro de main (divergió)").
- Corrección: `origin/main...HEAD = 0 19` con merge-base = main significa 19
  commits por delante SIN integrar; no hay commits exclusivos de main.
- Resolución: reformulado a "desciende del main observado y añade 19 commits
  aún no integrados".
- Autoridad: ninguna (hecho).

## C-15 · Búsqueda "AUSENTE" vs "NO LOCALIZADO"
- Fuente: mi redacción previa ("AUSENTE — no hallado").
- Corrección: no hallado en una búsqueda ACOTADA != inexistente en todo el
  equipo. La búsqueda se limitó a C:\ASTRA_WORK y Desktop.
- Resolución: reformulado a "NO LOCALIZADO en las rutas buscadas", con la
  limitación declarada.
- Autoridad: usuario (para indicar dónde buscar los originales).
