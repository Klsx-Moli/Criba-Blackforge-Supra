# CBS F38 — Un informe escéptico rechazado no es evidencia de supervivencia

Base: campaña F37 HEAD 351bccb138fde141417d650cfed2c92c79f38e0c.
Alcance: criba-blackforge/src/criba/intelligence/prior_art/verdict.py + tests/intelligence/test_prior_art_verdict_engine.py. Sin cambios en motores ASTRA, scoring central, G0 ni repos históricos.

## Hallazgo F38-01 — P1 (guard defensivo directo, no equivalencia con F05-03)

Contrato: el veredicto del escéptico sólo puede ser requires_experiment o survives_with_conditions para el productor PriorArtSkeptic actual. Un consumidor que recibe reject / rejected / UNKNOWN / PROVEN_NEW / None / [] / vacío no debe emitir SURVIVED_SEARCH por la mera ausencia de entradas en matches.

Rutas STATICALLY_INSPECTED: CrossDomainScout.validate_downstream_handoff rechaza reject, pero PriorArtVerdictEngine.assess() es una API pública y run_prior_art_mutation_loop._assess llama directamente a verdict_engine.assess(...) sin invocar ese validador. PriorArtSkeptic.review produce de forma normal las dos variantes conocidas, de modo que un guard que las conserve no cambia el camino legítimo. Un informe construido directamente como PriorArtSkepticReport puede contener un verdict arbitrario: la dataclass no valida en __post_init__.

Antes: assess validaba únicamente candidate_id, resultados, matches y coverage_limitations; ignoraba skeptic.verdict y emitía SURVIVED_SEARCH cuando existían documentos con provenance, sin gaps ni matches. Esto podría promover un informe explícitamente rechazado en la API pública; NO demuestra que F05-03 de Ernie use esta misma ruta.

Corrección F38: prior_art/verdict.py verifica str y conjunto permitido {requires_experiment, survives_with_conditions}, emite ValueError SKEPTIC_VERDICT_INVALID si no se cumple. Rechaza contradiction cuando requires_experiment sin evidence_gaps ni problemas estructurales daría cobertura vacía (SKEPTIC_VERDICT_CONTRADICTION). Mantiene la clasificación existente para reportes válidos: UNRESOLVED ante gaps, PARTIAL_PRIOR_ART ante matches, SURVIVED_SEARCH sin ambos, que sigue sin probar novedad científica.

Regression tests publicados: siete mutantes de verdict inválido {reject, rejected, PROVEN_NEW, UNKNOWN, '', None, []}; uno con requires_experiment pero 0 gaps; uno de control positivo con un source vacío que permanece UNRESOLVED. Se conservaron las pruebas originales que aceptan informes legítimos. NOT_EXECUTED en Python del checkout/Windows; comprobar que los mutantes fallarían en el commit base, no basta con que tests nuevos estén verdes.

## Refutación y límites explícitos

- La ruta normal PriorArtSkeptic.review nunca emite reject; este guard protege principalmente interfaces públicas, adaptación futura y reportes construidos/mutados. Sin un caller que inyecte un verdict rechazado, no declarar P0 productivo explotable ni probar que ocurrió F05-03. Clasificación P1 contrato defensivo en frontera pública.
- F05-03 reportado por Ernie: citas auténticas con REVIEW_SUPPORTED y referencia REJECT, caso de duchas. No hay un archivo F05-03 identificado en el árbol de la campaña (inspección tree / search) y el corpus local cbs_corpus.py no está publicado. Su causalidad y ruta de producto quedan EVIDENCE_PENDING; no renombrar, borrar ni normalizar el caso para hacer pasar el banco.
- El motor de prior-art no interpreta la semántica de similitud por sí solo; matches lo aporta la etapa anterior. SURVIVED_SEARCH no significa PROVEN_NEW ni VALIDATED. No afirmar que esta corrección resuelve el problema científico transversal G0.
- Un informe con survives_with_conditions falsificado y sin gaps puede pasar si los resultados aparentan cobertura; falsación de procedencia criptográfica y relevancia semántica siguen fuera del alcance de F38.

## Evidencia / gates

STATICALLY_INSPECTED: código exacto de PriorArtVerdictEngine, PriorArtSkeptic, CrossDomainScout, mutation_loop y nuevos sentinels. VERIFIED_BY_ME: estado remoto y commits publicados por conector GitHub. NOT_EXECUTED: pytest de F38, Ruff, mypy y CI. REPORTED_BY_AGENT: F31 Windows (46 FAIL, 2786 PASS, 20 SKIP); F05-03/ corpus privado. NOT_ACCESSIBLE: archivos no commiteados de iso-fixid y procesos Windows.

Gate Windows: python -B -m pytest -p no:cacheprovider -q tests/intelligence/test_prior_art_verdict_engine.py tests/intelligence/test_prior_art_skeptic.py tests/intelligence/test_prior_art_mutation_loop.py ; repetir tests dirigido F33–F37, Ruff/mypy contra baseline, registrar SHA y FAIL/SKIP. No inferencias externas ni validación experimental inventada.

Veredicto: F38 IMPLEMENTED / EVIDENCE_PENDING, NO-MERGE. P0 ciencia F05-03 y G0 NO-GO permanecen abiertos.
