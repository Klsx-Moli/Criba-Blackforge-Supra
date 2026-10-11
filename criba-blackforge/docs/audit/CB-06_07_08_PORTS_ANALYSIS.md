CB-06/07/08 — ANÁLISIS DE PORTS DE PRs ABIERTOS (sin merge, trabajo preservado)
================================================================================

SHA analizado: main = 6b3d02b9639466e0dcfd594a66b0744bb46abe57
Fecha: 2026-10-11 (UTC)
Decisión: NO se fusiona ningún PR abierto en esta campaña. Se documenta por qué.


RESUMEN DE PRs ABIERTOS Y SU VEREDICTO
--------------------------------------

PR #10 — codex/interpreter-hardening-20261004 (73 ficheros, núcleo del intérprete)
  VEREDICTO: SUPERSEDED por main.
  Evidencia: main tiene MÁS contenido que la rama en los ficheros clave:
    - contrato.py: main 418 líneas vs codex 234
    - banco.py:     main 325 líneas vs codex 170
    - puerto.py:    main 233 líneas vs codex 229
  El endurecimiento del intérprete (validación de contrato, KIND_SCHEMA/
  KIND_DOMAIN, banco) ya está absorbido y superado en main vía PRs #16-#20.
  Fusionar sería un merge backwards que rompería el contrato científico.
  ACCIÓN: no mergear. La rama se preserva intacta como histórico.

PR #12 — hermes/cbs-continuity-memory (docs/continuity, 12 ficheros)
  VEREDICTO: DOCUMENTACIÓN de otra línea de trabajo.
  No es código de producto; mezclarla en esta campaña ampliaría el alcance sin
  verificación de aceptación. Se preserva la rama.
  ACCIÓN: no mergear (fuera de alcance; no es un bloqueo del recorrido real).

PR #13 — chatgpt/shadow-supra-reliability (Windows smoke, 10 ficheros)
  Base: codex/interpreter-hardening-20261004 (SUPERSEDED, ver #10).
  VEREDICTO: SUPERSEDED. main YA tiene .github/workflows/shadow-windows-build-smoke.yml.
  ACCIÓN: no mergear.

PR #14 — chatgpt/shadow-exe-journey (EXE E2E gate, 9 ficheros)
  Base: chatgpt/shadow-supra-reliability (que a su vez se apoya en codex superseded).
  VEREDICTO: SUPERSEDED / dependiente de base obsoleta.
  ACCIÓN: no mergear.

PR #15 — chatgpt/reconcile-hermes-deep (truncated-model guard, 4 ficheros)
  VEREDICTO: YA ABSORBIDO en main.
  Evidencia: el truncated-model guard está en main/src/criba/model_runtime.py y
  su test test_model_runtime_completion_status.py existe en main y PASA (7/7).
  ACCIÓN: no mergear (trabajo ya integrado).

PR #8 — astra/blackforge-safety (autorización BLACKFORGE, 2 ficheros)
  VEREDICTO: BLACKFORGE. PROHIBIDO tocar sin autorización explícita de moli.
  ACCIÓN: apartado. No se ejecuta, habilita, ni fusiona. Rama preservada.

PR #11 — astra/blackforge-dossier (BLACKFORGE v1, 6 ficheros)
  VEREDICTO: BLACKFORGE. PROHIBIDO tocar sin autorización explícita de moli.
  ACCIÓN: apartado. No se ejecuta, habilita, ni fusiona. Rama preservada.


PRINCIPIO APLICADO
------------------

"Preservar trabajo útil" NO obliga a fusionar: obliga a no PERDER trabajo. Las
ramas de todos los PRs abiertos siguen intactas en el remoto; su contenido no
se ha borrado ni reescrito. Fusión sólo cuando el gate de la tarjeta está GREEN
Y el contenido no está ya superseded — ninguno de estos PRs cumple ambas.

Ningún PR abierto representa una función única ausente de main que el recorrido
real necesite: el núcleo (intérprete, contrato, storage, SUPRA, smoke Windows)
ya está en main y cubierto por los gates CB-* de esta campaña.


TARJETAS CB-09 (robustez de persistencia)
------------------------------------------

CB-09 queda cubierto por tests existentes + gates nuevos, sin fichero nuevo:
  - tests/unit/test_dossier_integrity.py: identidad, conflictos, ambigüedad,
    idempotencia, huérfanos, timestamps.
  - tests/unit/test_lottery*.py + test_storage_*.py: persistencia SQLite.
  - CB-I03 (roundtrip SUPRA en disco) + CB-R01 (recuperación local) + CB-L03
    (carga de storage): integridad, rollback, ausente/corrupto/vacío.
No se crea un test duplicado: el megaprompt pide no ampliar alcance.
