# ASTRA CANON

ASTRA_CANON protege contratos e invariantes, no archivos, pesos, heurísticas ni implementaciones concretas. Una implementación puede sustituirse si conserva el contrato. Debilitar un contrato exige decisión versionada, evidencia y revisión.

## Estados

- `CANON`: contrato obligatorio y no debilitado silenciosamente.
- `CANON_WITH_LIMITATIONS`: contrato obligatorio con límites explícitos; los límites no son permiso para sobreafirmar.
- `RESEARCH_ONLY`: hipótesis o capacidad no promovida a producto ni a claim científico.
- `UNRESOLVED`: pregunta científica abierta. No equivale a fallo, cero, resultado parcial ni evidencia negativa.

## Madurez de una capacidad

- `implemented`: existe código.
- `wired`: un entry point real alcanza ese código.
- `tested`: una prueba ejecutada contrasta un contrato definido.
- `scientifically supported`: evidencia válida bajo evaluador, protocolo y condiciones declarados respalda el claim acotado.
- `canon ready`: contrato versionado, mapeado y protegido por sentinels; no implica superioridad científica.

`code exists != scientifically validated`. Un nombre algorítmico, una estructura completa o una restricted execution no elevan por sí mismos la certeza.

## Autoridad científica preservada

- D3_NOVELTY = UNRESOLVED.
- D4_FUNCTIONAL_DIVERSITY = UNRESOLVED.
- D6_ADAPTIVE_BENEFIT = STILL_UNRESOLVED.
- SCIENTIFIC_ADVANTAGE_OF_CRIBA = NOT_ESTABLISHED.
- Anti-Goodhart Runtime no se implementa en esta misión. ASTRA-032 registra G1-G4 y STANDARD permanece deshabilitado hasta superar el gate de `docs/ASTRA_ANTI_GOODHART_ENTRY_GATE.md`.

## Reproducibilidad

Una semilla y el hash de un store son dependencias mínimas conocidas de algunos componentes, no un cierre global. Deben cerrarse todas las influencias reales aplicables: clock/evaluation time, policy version, corpus, configuration, provider, ordering, code version y external state.

## Evidencia y ejecución

RETRIEVED, DELIVERED, DOCUMENTED_AS_USED y CAUSAL_INFLUENCE_DEMONSTRATED son estados distintos. CLAIM, TEST, OBSERVATION, EVIDENCE y RESULT también. `RESTRICTED_EXECUTION_VERIFIED` acredita únicamente que esa ejecución restringida pasó su prueba; no valida científicamente una hipótesis.

## Protección operativa

La suite `tests/astra_canon/` es centinela de contrato. No se cambian expected values para legitimar una implementación incompatible. Research Vault, fallos históricos, protocolos originales y resultados negativos se preservan.

CODEOWNERS identifica revisores, pero sin branch protection/ruleset no bloquea cambios por sí solo.


## Revalidación histórica y derivados

Los registros históricos se preservan como evidencia de lo que el sistema
registró, pero una semántica anterior no conserva automáticamente permiso para
influir en decisiones actuales. Cuando cambian reglas de acreditación o learning:

- el registro fuente permanece;
- rewards/priors/lecciones incompatibles quedan inactivos;
- restart/replay/migration no los reactiva;
- una revalidación explícita bajo la semántica vigente es necesaria para volver
  a hacerlos learning-eligible.

Correcciones y reexportaciones conservan la identidad del episodio y su primera
fecha efectiva; no crean ensayos nuevos ni rejuvenecen evidencia.
