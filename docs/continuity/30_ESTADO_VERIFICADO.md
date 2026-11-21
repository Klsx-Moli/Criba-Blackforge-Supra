# ESTADO OBSERVADO Y PRUEBAS EJECUTADAS POR HERMES

OBSERVED_AT: 2026-10-05 (Europe/Madrid), sesión Hermes.
Método: inspección de git + ejecución de sondas y tests sobre los worktrees
locales. Cada dato lleva su nivel de evidencia.

NOTA DE INDEPENDENCIA (precisión obligatoria): los resultados de este documento
los EJECUTÓ Hermes, que es también el writer conforme al mandato. Por tanto son
EVIDENCIA REPORTADA POR HERMES, no verificación por un tercero independiente.
El usuario no los ha ejecutado. No deben presentarse como "verificación
independiente". Un verificador independiente real es el rol de las cinco ASTRA
(read-only) o el usuario; aquí no se ha usado ninguno.

Niveles usados: VERIFIED_BY_EXECUTION (ejecutado por Hermes, aquí) ·
STATICALLY_INSPECTED · CI_REVIEW · REPORTED_BY_AGENT · HISTORICAL ·
EVIDENCE_PENDING · NOT_EXECUTED · UNKNOWN.

## 0. REGISTRO DE EJECUCIONES (formato exigido)

Cada ejecución de este documento se registra con la plantilla:
comando · CWD/worktree · TARGET_SHA · estado del árbol antes/después ·
intérprete/entorno · inicio/fin · exit code · archivo de stdout/stderr ·
resultado · limitaciones.

Los registros parciales están en [80_REGISTRO_EJECUCIONES.md](80_REGISTRO_EJECUCIONES.md).
La plantilla anterior es de referencia, no una afirmación de que todos sus
campos o salidas completas estén conservados. Las limitaciones clave:
- Todas las ejecuciones de GUI usaron QT_QPA_PLATFORM=offscreen. OFFSCREEN NO
  es escritorio Windows verificado. La GUI VISIBLE no queda acreditada aquí.
- stdout/stderr se capturaron por `tail` en el flujo del comando, no en fichero
  aparte salvo donde se indica. El exit code procede de pytest.
- Ninguna ejecución fue presenciada por un tercero independiente.

---

## 1. ANCLAJE GIT

Remoto: https://github.com/Klsx-Moli/Criba-Blackforge-Supra.git

| ref | SHA observado | evidencia |
|---|---|---|
| origin/main | 15bc237be5555fcc38bc8a25f80724473c13435b | VERIFIED (git ls-remote) |
| worktree principal HEAD (rama codex/interpreter-hardening-20261004) | 2dc009485848b55ada5009986fe7e78d67c31ade | VERIFIED |
| hermes/astra/shadow-supra-20261002 | b91e43c1a6261e6a7c7583460478fd87a3367c1f | VERIFIED (git ls-remote) |
| astra/blackforge-dossier-20261005 | 3244879e7b2a2b4510dd997f4a343e26b1811b1b | VERIFIED (worktree iso-dossier) |
| reconcile/local-vs-remote | 0a05119282ef0a2090e624207fe83a000e6f5e6e | VERIFIED |

Relación de la rama activa con main:

    git rev-list --left-right --count origin/main...HEAD  ->  0  19
    merge-base(origin/main, HEAD) = 15bc237  (= main actual)

Formulación correcta (precisión pedida): la rama activa DESCIENDE del main
observado (merge-base = main) y añade 19 commits aún NO INTEGRADOS en él. La
comparación no muestra ningún commit exclusivo de main, así que "divergió" es
impreciso; lo correcto es "19 commits por delante de main, sin integrar".

Interpretación: la rama de trabajo ACTIVA (codex/interpreter-hardening)
parte del main actual y añade 19 commits. NO está integrada en main.

Worktrees presentes:

    C:/ASTRA_WORK/Criba-Blackforge-Supra   2dc0094 [codex/interpreter-hardening-20261004]
    C:/ASTRA_WORK/iso-dossier              3244879 [astra/blackforge-dossier-20261005]
    C:/ASTRA_WORK/iso-pr8-safety           65a58e5 [astra/blackforge-safety/dfca79-auth-state-failclosed]
    C:/ASTRA_WORK/iso-pr9-persistence      1a98b7e (detached HEAD)

Árbol del worktree principal: LIMPIO (git status --short vacío) al medir.

## 2. PRs ABIERTAS (gh pr list)

| PR | rama | estado |
|---|---|---|
| 11 | astra/blackforge-dossier-20261005 | OPEN |
| 10 | codex/interpreter-hardening-20261004 | DRAFT |
| 9 | astra/blackforge-persistence/15bc23-durable-agentic-audit | DRAFT |
| 8 | astra/blackforge-safety/dfca79-auth-state-failclosed | DRAFT |

## 3. PRODUCTO ACTIVO (CRIBA + SUPRA) — verificado por ejecución

### 3.1 Suite completa CRIBA (rama activa 2dc0094)

    QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
    ->  1737 passed, 3 skipped, 1 warning in 441.60s
    collect-only: 1740 tests

VERIFIED_BY_EXECUTION. Baseline histórico "1495 passed" (skill) era de main;
la rama activa tiene 1737 verdes. No se reprodujo ningún rojo.

### 3.2 Slice vertical real M2 (comprobación automatizada)

    pytest tests/integration/test_m2_vertical_slice_e2e.py -q
    ->  7 passed in 15.87s

El test recorre, SIN mocks en la ruta certificada: ShadowWindow (offscreen) ->
botón real -> actions.on_supra_vertical -> núcleo CRIBA determinista -> dossier
real -> SupraClient real (httpx/TCP) -> uvicorn SUPRA real (subprocess) ->
persistencia en disco -> GET -> reinicio del servidor -> GET.
VERIFIED_BY_EXECUTION (por Hermes).

CLASIFICACIÓN PRUDENTE DE M2 (corrección de un exceso previo):

    M2_INTEGRATION_OFFSCREEN:
      PASS reportado por Hermes; salida y SHA vinculados (7 passed @ 2dc0094).
    M2_GUI_VISIBLE:
      NO ACREDITADO. La ventana se ejecutó offscreen; el documento de
      continuidad exige que M2 no se demuestre sólo con GUI offscreen y que
      OFFSCREEN != escritorio Windows verificado.
    M2_ACCEPTANCE:
      PENDIENTE de comprobar los criterios restantes (visibilidad efectiva en
      escritorio Windows real, loading/error visibles, double-submit/retry
      conocidos como UX, no sólo como contrato).

Es decir: el test acredita la INTEGRACIÓN real por la ruta completa con un
servidor real y persistencia en disco, pero NO cierra M2 como milestone visible.

### 3.3 M3 restart/replay

    CRIBA: pytest tests/ -k "m3 or restart or replay"  ->  12 passed
    SUPRA: pytest test_b03_replay_restart_contract.py test_m3_restart_provenance_contract.py
           ->  15 passed

VERIFIED_BY_EXECUTION. Distingue AUSENTE de CORRUPTO: ver §3.4.

### 3.4 SUPRA — canales de estado y distinción ausente/corrupto

`state.get_project_with_provenance` devuelve
(posture, provenance, artifact_status, error_kind) con provenance
PROVENANCE_MEMORY_CACHE | PROVENANCE_ARTIFACT y artifact_status
ARTIFACT_MISSING | ARTIFACT_UNVERIFIABLE | ARTIFACT_MATCHES_CACHE |
ARTIFACT_DIVERGES. Un cache hit NO se publica como PERSISTED_STATE.
STATICALLY_INSPECTED (state.py). La conducta HTTP (404 ausente vs 500/409
corrupto) ya está protegida por los tests de restart/corrupt de §3.3.

### 3.5 Arranque SUPRA sin llave BLACKFORGE

    SUPRA_STORAGE_DIR=<scratch> GET /health        -> 200 healthy
    GET /api/v1/projects                            -> 200 count=0 storage_errors=[]

VERIFIED_BY_EXECUTION. SUPRA arranca y sirve sin key BLACKFORGE.

### 3.6 Shadow UI

- `criba-blackforge/shadow_ui/` PRESENTE en la rama activa (28 ficheros) y en
  hermes/astra/shadow-supra-20261002. AUSENTE en origin/main.
- `python shadow_ui/entrypoint.py --audit` -> callbacks_found 20,
  callbacks_missing ninguno, window_type ShadowWindow, targets_total 26/26 OK.
  VERIFIED_BY_EXECUTION.
- Arranque offscreen de ShadowWindow SIN módulos BLACKFORGE -> OK
  (sonda con blocker en sys.meta_path). VERIFIED_BY_EXECUTION.
- Sentinel i18n (`tests/unit/test_shadow_i18n_keys.py`) presente; 85 claves
  `shadow.` medidas en ui/i18n.py por ejecución.
- `on_blackforge` (actions.py:1104) NO inicializa BLACKFORGE: conmuta a la
  página de la ventana. STATICALLY_INSPECTED.

### 3.7 Desacoplamiento BLACKFORGE del núcleo (P0)

Sonda con blocker de import para `criba.blackforge*` en sys.meta_path:

    OK   criba.gates / chain / latency / logging / hybrid / canonical / ui.actions

Los siete importan sin BLACKFORGE. VERIFIED_BY_EXECUTION.
`tests/unit/test_blackforge_isolation_gate.py` presente y fija la identidad
`canonical.canonical_hash is blackforge_causal.canonical_hash` (líneas 99-100).
El único import perezoso de `blackforge_safety` está dentro de la rama
`mode != "blackforge"` (gates.py:275), fail-closed.

## 4. IDENTIDAD DE VERSIÓN

- `criba-blackforge/src/criba/version.py` EXISTE en la rama activa; deriva la
  versión de importlib.metadata con fallback a pyproject.toml.
- `__init__.py` y `api.py` la consumen (`from .version import __version__`;
  `FastAPI(version=__version__)`). mcp_server.py también.
- pyproject CRIBA: 0.3.0. pyproject SUPRA: 1.0.0.
- En origin/main NO existe version.py y sigue el literal "0.1.0" (__init__ y
  api.py). La unificación está SOLO en la rama activa, no en main.
STATICALLY_INSPECTED.

## 5. BLACKFORGE — HARD_PAUSE, y qué hay realmente

### 5.1 Estado del pause (medido)

- No existe llave física, ni ceremonia de desafío/respuesta, ni adaptador de
  laboratorio activo. Búsqueda de `key_security|enroll|challenge|physical_key`
  en todas las ramas remotas: SIN RESULTADOS. STATICALLY_INSPECTED.
- El broker nuevo (rama astra/blackforge-dossier) tiene
  `policy.execution_enabled = False` por defecto; `dispatch()` lanza
  CapabilityNotEnabled si no está habilitado; `enable_execution()` exige actor
  y razón, y `register_grant()` sólo marca grant despachable si
  `_has_credentialed_grant()` (credential_ref no vacío). Es decir: el código
  YA modela que sin credencial no hay despacho, y no hay credencial real.
- No hay executor real: sólo `SyntheticLabExecutor` (tests), marcado
  `synthetic: True` en cada salida, que NO ejecuta nada.
- HARD_PAUSE SIGUE VIGENTE. Nada de esto lo levanta.

### 5.2 Contenido real de la rama astra/blackforge-dossier-20261005 (PR #11)

Base = 15bc237 (main). Añade 6 ficheros, 3318 líneas:

    blackforge_case.py        (1026)  objeto canónico DefensiveCase
    blackforge_broker.py      ( 836)  broker: ledger sqlite + journal fsync
    blackforge_slice_authz.py ( 471)  primer slice declarativo
    tests/unit/synthetic_lab.py ( 59)
    tests/unit/test_blackforge_v1_mutations.py  (355)  15 mutaciones
    tests/unit/test_blackforge_v1_negative10.py (571)  26 negativos

NO modifica los módulos blackforge históricos (causal/selector/pipeline/
agentic siguen intactos y sin migrar).

Ejecutado por mí en worktree aislado (iso-dossier), con y sin fuga de módulos:

    PYTHONPATH=src pytest test_blackforge_v1_negative10.py test_blackforge_v1_mutations.py -q
    CON  editable-finder (fuga): 41 passed in 14.68s
    SIN  editable-finder (no_leak_plugin): 41 passed in 19.85s

VERIFIED_BY_EXECUTION. La fuga cuantificada del venv era de 2 módulos
(`canonical`, `version`, ausentes en esa rama) y NO alteró el resultado.

Elementos confirmados en el código de esa rama (STATICALLY_INSPECTED):
- Cuatro ejes independientes: WorkflowState, AuthorizationAxis, ExecutionAxis,
  EvaluationAxis. DISPATCHED != RUNNING documentado explícitamente.
- EvidenceOrigin: GENERATED / SIMULATED / DECLARED_EXTERNALLY /
  OBSERVED_ACCREDITED; sólo OBSERVED_ACCREDITED sostiene conclusión respaldada.
- Journal con os.fsync por append antes del despacho (línea ~207).
- reserve() usa BEGIN IMMEDIATE; consumptions con nonce UNIQUE.
- dispatch(): excepción del executor -> ExecutionAxis.OUTCOME_UNKNOWN y NO
  reintento (OutcomeUnknown).
- pending_uncertainty(): lista lo que sigue incierto tras reinicio
  (OUTCOME_UNKNOWN / DISPATCHED / RESERVED); nunca lo resuelve en silencio.
- `record_declarative_result` existe para el camino declarativo: la máquina de
  estados no deja pasar por RUNNING un resultado no ejecutado.
- Slice authz con vocabulario CERRADO de verbos (SUPPORTED_VERBS); un comando
  dentro del snapshot se RECHAZA, no se ejecuta.
- `Attempt` sólo modela `actions: list[str]` (verbos), no código arbitrario.

### 5.3 Mapa de entrypoints con capacidad de ejecutar/modificar (pregunta abierta 2)

| entrypoint | capacidad real | evidencia |
|---|---|---|
| `supra_agentic/integrations/criba_bridge.py` | `subprocess.run` invoca CRIBA y BLACKFORGE headless | STATICALLY_INSPECTED; sólo lo consumen tests (test_blackforge_bridge_isolation.py) |
| `criba/model_runtime.py` | `subprocess.Popen` para arrancar llama-server local | STATICALLY_INSPECTED |
| `criba/cli.py` (`blackforge-gui`, `blackforge`) | lanza GUI/pipeline BLACKFORGE histórico | STATICALLY_INSPECTED |
| `criba/ui/app_bridge.py:48` | `subprocess` `-m criba.blackforge_gui` | STATICALLY_INSPECTED |
| `criba/blackforge_agentic.py::BlackforgeCapabilityLayer` | capa de capacidades agentic (CONGELAR por diseño) | STATICALLY_INSPECTED |

Ninguno pasa hoy por el broker nuevo: el broker vive sólo en la rama PR #11.

## 6. LICENCIA (MONO-03)

- `criba-blackforge/pyproject.toml`: `license = {text = "Apache-2.0"}` +
  classifier Apache. LICENSE completo (11560 bytes).
- `supra/LICENSE`: 85 líneas (truncada); `supra/pyproject.toml` NO declara
  campo license.
- Estado: BLOCKED_LEGAL_DECISION. Completar el texto exigiría SUPONER la
  intención. No bloquea el trabajo técnico.

## 7. EMPAQUETADO WINDOWS (M5 parcial)

- `C:\ASTRA_WORK\APPS\CribaShadow\CribaShadow.exe` existe (10586268 bytes,
  2026-10-05 03:32).
- Manifiesto `VERIFICATION/interpreter-hardening-20261004/final-verification.json`:
  revision 6ab032f, executable_sha256 C0EEE3...5548, desktop_passed true,
  test_records 1701 tests / 0 failures / 3 skipped.
- PERO el smoke DIR más reciente del paquete
  (`desktop-smoke-final/result.json`) dice passed=false, exit_code=2. Los
  resultados `desktop-smoke-audit` y `desktop-smoke-clean` dicen passed=true.
- Conclusión: el estado del EXE es CONTRADICTORIO entre artefactos y NO está
  re-verificado contra el HEAD activo (2dc0094). No afirmar "paquete OK".
  EVIDENCE_PENDING.

## 8. LO QUE **NO** ESTÁ VERIFICADO / DESCONOCIDO

- Estado del EXE contra el HEAD activo (2dc0094): NO_EXECUTED.
- SRC-01 y SRC-03 del corpus (archivo de valor y protocolo /33 completos):
  AUSENTES en disco.
- Configuración Windows real de ACL/aislamiento entre núcleo y broker:
  UNKNOWN (no medida).
- `run 33` / kanban board: el board vive en el perfil Hermes; las tarjetas
  M2 (t_84ce5ac2) y M3 (t_26481736/t_30266103) figuran done/todo/blocked en el
  board, pero el "done" de M2 procede del workspace histórico
  `C:\ASTRA_WORK\reconcile-15bc237` (ruta medida AUSENTE). El done NO acredita
  el HEAD activo por sí solo; el test M2 de §3.2 sí lo acredita en la rama
  activa.
