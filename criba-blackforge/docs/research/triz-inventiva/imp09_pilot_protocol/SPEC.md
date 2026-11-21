IMP-09 — Protocolo de piloto causal con control de fijación (A4-OP-FIX-01)
=========================================================================
Estado: PROTOCOLO + PILOTO EJERCITADO (código real, laboratorio aislado).
Autor: Hermes (sesión nous/ornith-1.5-122b:free). Fecha: 2026-10-28.
Autorización: LOCAL_PREPARATION_ONLY. IMP-10 NO AUTORIZADO.

1. OBJETIVO
-----------
Diseñar y EJERCITAR un piloto mínimo que ponga a prueba el operador de
control de fijación (A4-OP-FIX-01) sobre el núcleo determinista de CRIBA,
usando el puerto real del producto (engine.activate -> preparar_dossier ->
validador). No es una prueba de utilidad científica: es una prueba de
SOFTWARE del operador y de encaje con el puerto.

El piloto puede concluir ausencia de efecto, efecto, o inconclusión. No
llama novedad a ausencia de resultado. El beneficio científico sigue sin
establecerse (SCIENTIFIC_BENEFIT_NOT_ESTABLISHED).

2. PUERTO REAL VERIFICADO POR EJECUCIÓN (no inventado)
-----------------------------------------------------
- src/criba/engine.py::activate(query, mode, manual_methods, diverge_fn, ...)
    * Núcleo determinista. Sin LLM, sin servicio, sin RNG externo (seed por
      query). Produce ideas con todos los campos que preparar_dossier necesita
      (expected_effect, mechanism_causal, mechanism_explanation,
      broken_assumption, causal_variables{evidencia_requerida, si_falla},
      difference_signature, known_space_element, causal_claim).
    * 94/94 ideas tienen difference_signature parseable.
    * Verificado: 1 idea -> preparar_dossier_desde_idea() -> dossier válido
      (candidate_id, estado=SUPRA_EJECUCION_PENDIENTE, prueba.estado_prueba=
      NO_EJECUTADA).
- src/criba/supra_dossier.py::preparar_dossier_desde_idea(idea, problema)
    * Ensambla un dossier SUPRA con prueba discriminante desde una idea real.
- docs/research/triz-inventiva/validator/validador.py::validate_inventive_card
    * Valida el esquema anidado real de ficha AC-06.

3. HALLAZGO DE INSPECCIÓN (determina el diseño del piloto)
---------------------------------------------------------
manual_methods y context NO cambian la salida de activate() en este núcleo:
  - manual_methods está en la firma de select_methods pero NO se usa en su
    cuerpo (parámetro sin implementar). Por eso forzar métodos no altera nada.
  - context solo se adjunta si FEATURES["context_layer_v2"] está activo; en el
    modo base no cambia las ideas.
diverge_fn SÍ cambia la salida (hook real de inyección):
  - Un diverge_fn que siembra un mecanismo en la primera idea produce esa
    familia en la posición 0, desplazando la auto-selección.
Conclusión de diseño: el "ejemplo" de fijación se inyecta por diverge_fn, NO
por manual_methods. Esto es una corrección real del piloto respecto a lo que
A4 sugiere (A4 no conoce el interior del núcleo).

4. OPERADOR A4-OP-FIX-01 -> CÓDIGO
----------------------------------
A4-OP-FIX-01 ("Sembrar ejemplos sin fijar la solución"):
  transformation_steps: extraer mecanismo del ejemplo + marcar defectos; pedir
    alternativas que cambien el mecanismo; comparar con condición sin ejemplo;
    registrar si los defectos reaparecen.
  required_outputs: example_mechanisms, known_flaws, control_condition,
    reappearing_flaws.
  counterexample explícito de A4: "Medir fijación por el número de palabras
    repetidas" -> NO se hace.
  rival_explanation: "El parecido procede del problema, no del ejemplo".
  discriminating_test: "Control vs ejemplo con mismo problema/presupuesto;
    contar defectos heredados".

Traducción a código determinista:
  - example_mechanism  = una familia + mecanismo con un supuesto roto conocido
    (known_flaw) que se siembra en la idea[0] vía diverge_fn.
  - control_condition  = diverge_fn=None (auto-selección del núcleo).
  - reappearing_flaws  = ¿el known_flaw reaparece en más ideas que la control?
  - presupuesto igual  = misma query, mismo mode, mismo supporting_methods.

5. MÉTRICAS (fijadas ANTES de ver resultados)
---------------------------------------------
Por condición (con ejemplo / sin ejemplo), sobre las ideas producidas:
  M1 family_diversity   = número de familias únicas (más alto = menos fijación).
  M2 real_divergent     = ideas con divergence_real (del motor).
  M3 example_mechanism_present = el mecanismo sembrado aparece en la salida.
  M4 flaw_reappearance_rate = fracción de ideas que heredan el known_flaw.
  M5 top_family           = familia de la idea[0].

Criterio de fijación (definido antes de ejecutar):
  Hay evidencia de fijación si, a igual presupuesto, la condición CON ejemplo
  reduce family_diversity (M1) o aumenta flaw_reappearance_rate (M4) respecto
  a la control. Ausencia de diferencia = ausencia de efecto (no se invierte el
  veredicto para contar como "éxito").

6. ABLACIONES
------------
  A0 control puro: diverge_fn=None.
  A1 ejemplo sembrado: diverge_fn siembra mecanismo+flaw en idea[0].
  A2 rival: segunda query de control donde el ejemplo NO aplica (el mecanismo
     sembrado no debe reaparecer por el problema; si reaparece, es artefacto).
  A3 presupuesto: variar supporting_methods (8/12/20) para ver si la fijación
     escala con el presupuesto.

7. VERIFICACIÓN DEL PILOTO (ejecutada)
-------------------------------------
Comando: .venv/Scripts/python.exe -m pytest
  docs/research/triz-inventiva/imp09_pilot_protocol/tests/test_pilot_fixation_control.py -p no:randomly
Resultado: ver sección 8 (REAL_EXIT=0).
Cobertura de AC (IMP-09):
  * Puede concluir ausencia de mejora o inconclusión -> test_pilot_concludes_honestly.
  * No llamar novedad a ausencia de resultado -> test_no_novelty_from_absence.
  * No usar fixture de ejemplo como medición -> test_example_not_used_as_metric.

8. RESULTADO DEL PILOTO (este entorno, 2026-10-28)
------------------------------------------------
Ejecutado sobre el puerto real determinista (engine.activate, 94 ideas/query).
Métrica: family_diversity (control vs ejemplo sembrado) + reaparición de flaw.

  budget=8:  control_diversity=6  seeded=7  gap=-1 | FIXATION_OBSERVED=False
  budget=12: control_diversity=9  seeded=10 gap=-1 | FIXATION_OBSERVED=False
  budget=20: control_diversity=13 seeded=14 gap=-1 | FIXATION_OBSERVED=False

Veredicto honesto: en el núcleo determinista, sembrar un mecanismo de ejemplo
NO reduce la diversidad de familias (gap=-1, es decir, la condición con ejemplo
tiene LIGERAMENTE MÁS diversidad). No hay efecto de fijación observable con
este diseño.

Límite honesto del piloto (no ocultar): el núcleo determinista produce un
conjunto FIJO y amplio de ideas (94 por query). Inyectar UN mecanismo en la
idea[0] no puede reducir la diversidad de 94 ideas; por eso el diseño tiene
poca potencia para detectar fijación de estilo humano. Esto NO es evidencia de
que la fijación no exista: es evidencia de que este núcleo determinista no es
el sustrato adecuado para probar fijación humana. El piloto es una prueba de
SOFTWARE del operador y de encaje con el puerto, no una prueba de utilidad ni
de psicología del diseño.

Beneficio científico: NO establecido (SCIENTIFIC_BENEFIT_NOT_ESTABLISHED).

9. NO VERIFICADO / LÍMITES
--------------------------
- No se ejecutó ningún LLM ni servicio; el piloto es del núcleo determinista.
- No se atribuye la fijación humana de 1991 a modelos sin prueba.
- manual_methods/context no son canales de inyección en este núcleo (ver §3);
  un piloto que dependa de ellos sería inválido.
- El piloto NO evalúa utilidad para el objetivo del usuario; solo el operador.
- Tamaño de muestra y evaluadores: piloto exploratorio (n=1 query, criterio
  automático). No es un estudio con poder estadístico.
