# CBS F39 — JSON/identidad del perfil y entrada de coincidencias científicas

**Base F38:** `de635095d4507f44dff245d877a84e96c9ca6669`.
**Rama:** `campaign/cbs-final-32-40` (ninguna intervención en main, ASTRA, handoff o servidor SUPRA).
**Estado:** código y tests publicados; pytest, Ruff, mypy y UI Windows **NOT_EXECUTED**. No implica GO.

## F39-M01 · P1 · Configuración JSON ambigua activaba un intérprete

**Ruta:** `load_model_settings(path)` → `load_model_settings_bytes(raw)` → `ModelSettings.enabled/active_profile` → CRIBA/BLACKFORGE. El lector de F38 era tolerante; Python `json.loads` aceptaba claves duplicadas y los literales no JSON `NaN/Infinity`. Un archivo con `"enabled":false,"enabled":true` terminaba habilitado (última clave). `schema_version=2` se normalizaba a 1 sin retirar `enabled=True`.

**Fix:** lectura con `object_pairs_hook` que rechaza duplicados a cualquier profundidad y `parse_constant` que rechaza NaN/Infinity; versiones explícitas desconocidas, bool o string no se habilitan. Se permite la ausencia de `schema_version` en archivos heredados para compatibilidad; hay test que lo fija. El parser tolerante para campos individuales existentes permanece.

**Tests:** 9 mutaciones de JSON (clave enabled duplicada, campo model duplicado, NaN/+inf/-inf, versión 2/bool/texto); 1 caso legacy compatible. Ninguna requiere inferencia.

## F39-M02 · P1 · Identidad activa desconocida normalizada al primer modelo

**Ruta:** `ModelSettings.active_profile()` retorna primer perfil si active_profile_id no coincide. Anteriormente, el lector podía poner enabled=True con id activo ausente, falso, extranjero o con espacios; la llamada productiva ejecutaría otro GGUF en lugar del solicitado. Dos perfiles del mismo id se reparaban sustituyendo uno por UUID, pero podían continuar habilitados.

**Fix:** cuando enabled=True, exigir id activo de tipo str, exacto (sin trim ni truncamiento) y presente en perfiles. Además, los IDs de perfiles en disco deben ser únicos, texto exacto de hasta 120 caracteres y sin contenedores. Ante ambigüedad, preservar perfiles editables y reparar IDs legados, pero dejar `enabled=False`. No toca defaults de modelo ni borra ficheros.

**Tests:** 5 mutaciones del id activo, 1 caso disabled legacy editable, 4 mutaciones del id de perfil, 1 duplicado con modelos diferentes, refuerzo de test histórico de IDs duplicados. Esto no establece identidad física `/props.model_path`, que sigue P1 OPEN.

## F39-S01 · P1 · Similarity fuera de dominio contaminaba las coincidencias

**Ruta:** `PriorArtVerdictEngine.assess` recibía objetos `PriorArtMatch` con `similarity` declarado 0..1 pero sin validación runtime. NaN/±infinito, negativos, >1, bool, texto y listas podían provocar orden no determinista, errores tardíos o reportes inválidos.

**Fix:** antes de ordenar, comprobar doc tipo EvidenceDocument y similarity `int/float` no bool, finita para float y dentro de 0..1. Rechazar con `MATCH_SIMILARITY_INVALID` y `TypeError` explícito para doc inválido, sin reinterpretar scores ni cambiar los umbrales de novedad.

**Tests:** 10 mutantes de valor y tipo, 5 valores legítimos (0, 0.0, 0.5, 1, 1.0), un doc falsificado; conserva PARTIAL_PRIOR_ART para matches válidos. NO establece relevancia semántica ni pertenencia de cada coincidencia al lote de fuentes.

## F39-S02 · P1 · Generadores de una pasada borraban coincidencias

**Ruta:** `assess(matches: Sequence)` primero hacía `any(... for match in matches)`, después `sorted(matches, ...)`. Si un consumidor rompía el tipo anotado y pasaba un generador, `any` lo agotaba; `sorted` obtenía cero coincidencias y podía devolver `SURVIVED_SEARCH` en vez de `PARTIAL_PRIOR_ART`, precisamente un falso resultado verde.

**Fix:** rechazar tipos no Sequence, str/bytes y los generadores de una pasada ANTES de iterarlos; no convertirlos silenciosamente en lista, para que quede visible la violación de contrato.

**Tests:** 1 generador válido que antes se vaciaba y 3 argumentos no secuencia (None, str, bytes); deben devolver TypeError, no SURVIVED_SEARCH.

## PASS10 · deuda adversarial abierta (no falsa solución)

- **P1/EVIDENCE_PENDING:** `run_prior_art_mutation_loop` conserva `current_matches` de rondas previas; por eso NO se puede exigir sin más que todas las coincidencias aparezcan en `results` de la ronda actual. Falta un contenedor de linaje de coincidencias acumuladas con `round_id`/source, identidad documental y fingerprint; buscar consumer y tests antes de modificar.
- **P1 OPEN:** los matchers pueden pasar `PriorArtMatch` con documentos que no pertenecen ni a una ronda conocida; el API pública no acredita pertenencia material. No confundir `EvidenceDocument.provenance != None` con relevancia del mecanismo.
- **P1 OPEN:** CAS de `models.json` entre último check y os.replace; F35–F37 reducen carreras pero no lock interproceso.
- **P1 OPEN:** GGUF alias nominal no es identidad física del archivo; trabajo en `iso-fixid-20261122` sigue local, sin commit ni autorización para transferir.
- **P0 OPEN:** F05-03/caso duchas con REVIEW_SUPPORTED y referencia REJECT, reportado por Ernie; ruta/corpus no publicado, esta fase NO lo repara.
- **G0 NO-GO:** ciencia no acreditada. F31 tuvo 46 FAIL, 2786 PASS, 20 SKIP (REPORTED_BY_AGENT). Cualquier suite F39 sigue NOT_EXECUTED.

## Plan de verificación exacto

Sobre un worktree Windows NUEVO del SHA final de F39, sin alterar los worktrees de F30/F31/Ernie:
```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
python -B -m pytest -p no:cacheprovider -q tests/unit/test_model_config.py tests/unit/test_model_config_atomic_writer.py
python -B -m pytest -p no:cacheprovider -q tests/intelligence/test_prior_art_verdict_engine.py tests/intelligence/test_prior_art_mutation_loop.py
python -B -m pytest -p no:cacheprovider -q tests/unit/test_model_settings_dialog_stale.py tests/unit/test_phase29_shadow_source_selector.py
python -B -m pytest -p no:cacheprovider -q tests/unit/test_chain_memory_lock_scope.py tests/unit/test_offline_intelligence_store_isolation.py
git diff --check
```
También Ruff, mypy contra el baseline conocido de 32 errores y registro por nodo de FAIL/SKIP. No ejecutar gasto ni modelos reales, no publicar a main, no declarar PASS de lo no ejecutado.

**Evidencia:** `STATICALLY_INSPECTED` fuentes GitHub y diff, `VERIFIED_BY_ME` SHA/commits publicados por conector; `NOT_EXECUTED` tests F39; `NOT_ACCESSIBLE` PC Windows/servidor; `REPORTED_BY_AGENT` F31 de Ernie.
