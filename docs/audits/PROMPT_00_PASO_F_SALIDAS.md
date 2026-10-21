# PROMPT 00 — Paso F: Salidas exigidas

**Fecha:** 2026-10-20 (tercera sesión, continuación)
**SHA inicial de la sesión:** `d9558693932615055878a3bbfa526a9a4a209255`
**HEAD actual:** `7b035a3b664d2412e5fc95928fcca00f85146f36`
**Rama:** `reconcile/candidate-fix-20261020`

---

## 1. Aclaración de SHAs (petición 1)

**No hay dos commits rivales: hay un linaje de 5 commits.**

```
7b035a3  docs(prompt00): Paso E continuity contrast + honest state findings   <- HEAD actual
9172ce7  docs(prompt00): update checkpoint after i18n fix (Paso D)
58e6171  fix(shadow): align i18n keys with defined names and complete EN table <- UNICO commit de codigo de producto
d955869  docs: add PROMPT 00 checkpoint report with state and next actions
6dbda2e  checkpoint: fix import boundary sentinel to check real imports not substrings
b27ccd6  feat(shadow): scientific cycle, causal experiments, interpretation UI <- base (PR #23)
```

**Evidencia de la relación (verificada con Git, no por intuición):**

| Comprobación | Resultado |
|---|---|
| `git merge-base --is-ancestor 9172ce7 HEAD` | **SI** |
| `git merge-base --is-ancestor 9172ce7 7b035a3` | **SI** |
| `git rev-list --left-right --count 9172ce7...HEAD` | `0  1` |
| `git show --stat 7b035a3` | 2 ficheros, **solo documentación** |

**Diferencia entre el commit de código y los checkpoints documentales:**

- **`58e6171`** es el **único commit de código de producto** de esta sesión:
  `i18n.py` (+1 clave) y `shadow_window.py` (2 claves realineadas).
- **`6dbda2e`** es corrección de un **test/sentinel** (`test_blackforge_regression.py`).
- **`d955869`, `9172ce7`, `7b035a3`** son **solo documentación** (checkpoint, informe
  Paso E). No tocan producto.
- `9172ce7` y `7b035a3` están en el **mismo linaje**; `7b035a3` está exactamente
  **1 commit por delante**. Ninguno es un HEAD ajeno ni un commit huérfano.

---

## 2. Estado del árbol (petición 3)

| Dato | Valor |
|---|---|
| HEAD local completo | `7b035a3b664d2412e5fc95928fcca00f85146f36` |
| Rama | `reconcile/candidate-fix-20261020` |
| `main` local | `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b` |
| `origin/main` | `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b` (intacto) |
| HEAD remoto PR #23 | `b27ccd63fd3f25c445ddc88e8ecb8300a25a6e90` |
| ¿HEAD en `origin`? | **NO** (`git branch -r --contains HEAD` → vacío) |
| ¿`d955869` en `origin`? | **NO** (`git ls-remote` → 0) |

**Cambios pendientes (WIP preservado, sin tocar):**

```
 M criba-blackforge/src/criba/blackforge_broker.py     (solo CRLF, numstat vacío)
 M criba-blackforge/src/criba/blackforge_case.py       (solo CRLF, numstat vacío)
?? .hermes/
?? criba-blackforge/.hermes/iie/checkpoints/P10.md
```

**Procesos activos:** 5 procesos `python`, todos del propio Hermes (agente, venv,
tooling). **Ningún escritor externo.** Sin `index.lock` de Git.

**Backups:**

| Artefacto | Estado |
|---|---|
| `C:/ASTRA_WORK/PREFLIGHT_BACKUP_20261020/bundle_20261020.bundle` | 14.334.541 bytes |
| MD5 | `1b799fc50ddcde91810a255351212b50` (verificado, coincide con el informe previo) |
| `remote_refs.json`, `branch_manifest.json`, `wip_files/` | Presentes |
| Stashes | Ninguno |

---

## 3. Salidas exigidas por PROMPT 00 (Paso F) — con ubicación

El prompt canónico exige 7 salidas. Cada una está cubierta y su ubicación es:

| # | Salida exigida | Estado | Ubicación |
|---|---|---|---|
| 1 | SHA/base inicial y SHA candidato final | **HECHO** | §1 y §2 de este informe; checkpoint |
| 2 | Tabla branches/PRs/commits con decisión KEEP/PORT/REJECT/DEFER/VERIFY | **HECHO** | §4 |
| 3 | Cambios por archivo con procedencia | **HECHO** | §5 |
| 4 | Tests exactos ejecutados, exit code, resultado y SHA; separar históricos de actuales | **HECHO** | §6 |
| 5 | CI del candidato y links a jobs | **HECHO (con limitación declarada)** | §7 |
| 6 | Estado anterior frente a reconciliado y preguntas abiertas | **HECHO** | §8 y §9 |
| 7 | Próximo ticket exacto, sin inventar DONE | **HECHO** | §11 |

**Documentos entregados en esta sesión:**

- `docs/audits/PROMPT_00_PASO_E_CONTINUIDAD.md` — informe Paso E (13 verificaciones).
- `docs/audits/PROMPT_00_PO_F_SALIDAS.md` — este informe Paso F.
- `docs/audits/checkpoints/PROMPT_00_CHECKPOINT_2026-10-20.md` — checkpoint recuperable.

---

## 4. Tabla de branches/PRs/commits y decisión

| Referencia | SHA real | Commits vs main | Decisión | Fundamento |
|---|---|---|---|---|
| `main` | `defd0fd` | — | **KEEP** | Base intacta; no se toca |
| PR #23 `integrate/shadow-supra-final` | `b27ccd6` | 0 behind / **118 ahead** | **KEEP** | Rama base de la candidata; contiene el código producto |
| Candidata `reconcile/candidate-fix-20261020` | `7b035a3` | 0 behind / **122 ahead** | **KEEP** | Candidata actual; 4 commits locales sobre #23 |
| #8 `astra/blackforge-dossier-20261005` | `3244879` | 2 únicos | **ALREADY_ABSORBED** | `d87440b` **es ancestro** del candidato |
| #9 `astra/blackforge-safety/dfca79-auth-state-failclosed` | `65a58e5` | 6 únicos | **ALREADY_ABSORBED** | `c8b7273` **es ancestro** del candidato |
| #11 `astra/blackforge-persistence/15bc23-durable-agentic-audit` | `1a98b7e` (solo `origin/`) | 17 únicos | **VERIFY** | `1a98b7e` es ancestro del candidato, pero la rama **no existe en local**; su contenido no se reanalizó en esta sesión |

**Commits de la candidata (4):** `6dbda2e`, `d955869`, `58e6171`, `9172ce7`, `7b035a3`
(los 5 listados en §1; `6dbda2e` es el sentinel, `58e6171` el producto, el resto docs).

---

## 5. Cambios por archivo con procedencia

**Procedencia: trabajo de esta sesión (no de #8/#9/#11).**

| Archivo | Cambio | Procedencia |
|---|---|---|
| `criba-blackforge/src/criba/ui/i18n.py` | +1 clave EN `shadow.exp_result` | Defecto propio de `b27ccd6`, corregido en `58e6171` |
| `criba-blackforge/shadow_ui/shadow_window.py` | 2 claves realineadas (guion bajo → punto) | Defecto propio de `b27ccd6`, corregido en `58e6171` |
| `criba-blackforge/tests/unit/test_blackforge_regression.py` | sentinel por imports reales, no substring | Defecto propio de `b27ccd6`, corregido en `6dbda2e` |
| `docs/audits/checkpoints/PROMPT_00_CHECKPOINT_2026-10-20.md` | checkpoint | documentación |
| `docs/audits/PROMPT_00_PASO_E_CONTINUIDAD.md` | informe Paso E | documentación |
| `docs/audits/PROMPT_00_PO_F_SALIDAS.md` | este informe | documentación |

**Diff de producto vs PR #23:** `2 ficheros, +3/-2` (solo los dos primeros de la tabla).
**Ningún archivo de #8/#9/#11 se portó:** su trabajo ya está absorbido en el árbol.

---

## 6. Pruebas vinculadas a su SHA

### 6.1 Ejecutadas localmente (VERIFIED_BY_EXECUTION, SHA `7b035a3`)

| Prueba | Resultado | Exit | Tiempo | Cómo se lanzó |
|---|---|---|---|---|
| Suite CRIBA completa | **2226 passed, 16 skipped** | 0 | 941.72s | cwd=`criba-blackforge` (como CI) |
| Suite SUPRA completa | **325 passed, 2 warnings** | 0 | 52.98s | cwd=`supra` |
| Tests P10 (T07/T08/T09/T10) | **39 passed** | 0 | 3.86s | `-p no:randomly` |
| Sentinel import boundary | **3 passed** | 0 | 5.30s | `-p no:randomly` |
| Sentinel i18n Shadow | **6 passed** | 0 | 1.70s | `-p no:randomly` |
| **mypy baseline gate** | **Success: 174 source files, debt 0/0** | 0 | ~304s | `scripts/check_mypy_baseline.py` |
| **ruff gate (reglas CI)** | **All checks passed** | 0 | — | `--select E9,F63,F7,F82,F601,F811,B023` |
| Tests multi_repo_state | **20 passed** | 0 | 4.39s | — |

### 6.2 Pruebas NO ejecutadas en esta sesión

| Prueba | Motivo |
|---|---|
| CI remoto del SHA candidato | Rama no publicada. **No se hizo push** |
| Anti-Goodhart RETRYBOX Gate | No reejecutado localmente (solo existe como workflow) |
| Shadow Windows Build Smoke | No reejecutado localmente |
| E2E Shadow + BLACKFORGE | No ejecutado |
| Build Windows / PyInstaller | No ejecutado |
| #11 persistence (17 commits) | Rama ausente en local; contenido no analizado |
| `integrate_auto.ps1` | Solo parseado, no ejecutado |

### 6.3 Limitación declarada del scout simulado

En T10 (`test_prior_art_mutation_loop.py`) el `scout` usa `_DummySource` /
`_DummyTransport`: fuentes **simuladas en frontera**. Es una prueba de **contrato**,
no E2E con fuentes externas reales. Se conserva el recuento real (39) y qué valida
cada fichero (§3 del informe Paso E). No se amplió el alcance.

---

## 7. CI del candidato (con limitación explícita)

**CI remoto histórico de la rama PR #23** (run `39194815285`, 2026-10-19T03:28Z):

```
4 failed, 2186 passed, 38 skipped
```

Los 4 fallos y su causa:

| Fallo | Causa raíz |
|---|---|
| `test_both_languages_define_the_same_shadow_keys[es]` | clave `shadow.exp_result` ausente en la tabla EN |
| `test_both_languages_define_the_same_shadow_keys[en]` | asimetría ES/EN en el conjunto `shadow.*` |
| `test_shadow_window_reports_no_raw_key_when_rendered` | claves huérfanas `shadow.interpretacion_titulo`/`_sub` |
| `test_criba_engine_does_not_import_blackforge_on_load` | sentinel por inspección textual (substring ≠ import) |

Jobs hermanos **en verde**: Anti-Goodhart RETRYBOX Gate, Shadow Windows Build Smoke.

**CI del candidato local: `NOT_EXECUTED`.** La rama `reconcile/candidate-fix-20261020`
no está publicada; no tiene runs. **No se afirmó que el CI esté verde para el
candidato.** No se confunden las suites locales superadas (§6.1) con CI remoto.

**Cruzamiento honesto:** el CI remoto falló en exactamente las rutas que tocan los
commits locales. El árbol local contiene esas correcciones. **Hasta ahí llega la
afirmación** — no se afirma publicación ni verde remoto.

---

## 8. Hallazgos E6–E9 y PHYSICAL_REPOS

### 8.1 Defectos CONFIRMADOS (con evidencia ejecutada)

| ID | Hallazgo | Evidencia | Clasificación |
|---|---|---|---|
| **E6** | `STATE.json` se autocontradice: `open_questions` dice que P10-T09 no existe, `completed_tasks` lo lista y `verdict.py` está commiteado (`91246df`) | `validate`/`json.loads` sobre el fichero real | **DEFECTO CONFIRMADO — documentación de estado** |
| **E8** | `CONTINUITY.md` (2026-09-05) declara P10-T07 PARTIAL y P10-T09 NOT_STARTED; ambos están commiteados y con tests que pasan | `git log -1` de cada módulo + 39 tests pasan | **DOCUMENTO OBSOLETO** |
| **E9** | Journal `P10-T07.json` dice `PARTIAL`; T08/T09/T10 dicen `VERIFIED` | lectura de los 4 journals | **DEFECTO CONFIRMADO — documentación de estado** |
| **E7** | `STATE.json` no usa ninguno de los 7 estados mínimos que exige el Paso E | búsqueda de las 7 cadenas → 0 presentes | **DEFECTO CONFIRMADO — esquema de estado** |
| **PHYSICAL_REPOS** | `multi_repo_state.py` apunta a rutas muertas; `validate()` devuelve **exit 2** | ejecución real de `validate()` | **DEFECTO CONFIRMADO — ver §8.3** |

### 8.2 Inferencias (etiquetadas como tales)

| ID | Inferencia | Por qué es inferencia |
|---|---|---|
| I1 | Los artefactos E6–E9 quedaron desalineados por la **migración** del workspace (`C:\Users\KLSX\Music\INNOVATIONS` → `C:\ASTRA_WORK`) | Coherente con `migration.status=PARTIAL` y con `PHYSICAL_REPOS`, pero **no** se ha rastreado el commit exacto que rompió la alineación |
| I2 | `P10-T07.json` quedó en PARTIAL por una **actualización parcial durante la migración** | Plausible; no verificado commit a commit |

### 8.3 PHYSICAL_REPOS — clasificación y causa demostrada

**Clasificación: `CONTINUITY_TOOLING`.** No es `PRODUCT_RUNTIME`.

**Contrato actual (verificado en código):**

```python
ROOT = Path(__file__).resolve().parent          # .hermes/iie/
STATE_PATH = ROOT / "STATE.json"               # el STATE.json que consume
PHYSICAL_REPOS = {
    "CRIBA":  "C:/Users/KLSX/Music/INNOVATIONS/ACTIVE/CRIBA",   # NO EXISTE
    "SUPRA":  "C:/Users/KLSX/Music/INNOVATIONS/ACTIVE/SUPRA",   # NO EXISTE
}
```

**Consumidores y funciones que tocan esas rutas:**

| Función | Uso de `PHYSICAL_REPOS` | Efecto con ruta inexistente |
|---|---|---|
| `_live_physical_repo(path)` | `git -C <ruta> rev-parse HEAD` | `_git` devuelve `""` si `returncode != 0` → **sin excepción** |
| `snapshot()` | graba `live` en STATE.json | escribe `commit=""`, `is_repo=False` → **estado vacío** |
| `validate()` | compara con lo registrado | reporta `STATE_STALE` → **exit 2** |
| `_changed_paths_since` | `git diff <commit>..HEAD` | devuelve `[]` si no resuelve |

**Causa demostrada (no inferida):** `_git` hace `return "" ` en caso de error
(`multi_repo_state.py:202`). Una ruta inexistente **no lanza excepción**: produce un
registro vacío silencioso. La ruta de ejecución es:

```
snapshot()/validate()  ->  _live_physical_repo(ruta_muerte)  ->  _git(...) -> ""
  ->  {"commit": "", "is_repo": False}  ->  STATE_STALE (exit 2)
```

**Evidencia ejecutada:**

```
$ python .hermes/iie/multi_repo_state.py validate
[CRIBA] C:/Users/KLSX/Music/INNOVATIONS/ACTIVE/CRIBA
  branch= head= dirty=0
  state: branch=feat/iie-master commit=10e1dcc7a30d last_good=10e1dcc7a30d
DISCREPANCIAS:
- CRIBA: STATE_STALE (recorded commit != HEAD)
- SUPRA: STATE_STALE (recorded commit != HEAD)
- BLACKFORGE: STATE_STALE against shared CRIBA repo
$ echo $?
2
```

**Simulación de `snapshot()` (en copia temporal, sin tocar el real):** grabaría
`{"commit": "", "is_repo": false}`. Es decir, **ni `snapshot()` ni `validate()`
pueden repararse sin corregir `PHYSICAL_REPOS`**.

**¿Existe test que ejercite esas rutas?** Sí, pero **no ese contrato**:
`test_multi_repo_state.py:39` y `test_multi_repo_state_locks.py:194,224` hacen
`monkeypatch.setattr(tool, "PHYSICAL_REPOS", {"CRIBA": "C:/fake"})` — es decir,
**sustituyen** las rutas antes de ejercitarlas. Verifican locking y validación
estructural, **no** que las rutas reales resuelvan a repositorios vivos. Por eso el
defecto no lo detecta ninguna prueba actual.

**Separación de efectos (lo que se pidió):**

| Ámbito | Efecto | Evidencia |
|---|---|---|
| **Continuidad de Hermes** | `validate()` no sirve para reanudar con garantía: siempre dice STALE. La herramienta de reanudación está ciega | exit 2 ejecutado |
| **Producto CRIBA/SUPRA en ejecución** | **Ninguno.** `src/`, `shadow_ui/` y `supra/src` **no importan** `multi_repo_state`. Los feature flags están **todos en false**. | `grep -rn multi_repo_state src shadow_ui` → vacío; `feature_flags` activos: NINGUNO |

**Prueba que permitiría refutar el hallazgo:** ejecutar `snapshot()` sobre una copia
de `STATE.json` y comprobar que `validate()` devuelve 0 con rutas reales. Con las
rutas actuales, `snapshot()` **peora** el estado (sobrescribe `commit` con `""`),
y `validate()` devuelve 2. El hallazgo, por tanto, **no queda refutado**.

**NO se repararon las rutas** (instrucción explícita): solo se documentó el contrato,
la causa y la prueba de refutación.

---

## 9. Preguntas abiertas sin resolver

1. **E6/E7/E8/E9:** ¿adopta `STATE.json` los estados mínimos del Paso E y se
   reconcilia con el SHA candidato? ¿Pasan `CONTINUITY.md` y `P10-T07.json` a
   histórico? **Decisión del propietario.**
2. **PHYSICAL_REPOS:** ¿se corrigen las rutas a `C:\ASTRA_WORK\...` o se declara
   la herramienta obsoleta? **Decisión del propietario.**
3. **#11 persistence:** su contenido (17 commits) no se reanalizó en local.
4. **Publicación:** la candidata no está publicada; el CI remoto no la cubre.

---

## 10. Preservación de evidencia y skills (petición 2)

**Sin modificar** durante esta inspección: `STATE.json`, `CONTINUITY.md`,
`P10-T07.json`, `P10-T09.json` y el código de producto.

**Estado de la skill `repository-blueprint-audit` y su referencia:**

| Ruta | Estado |
|---|---|
| `C:\Users\KLSX\AppData\Local\hermes\skills\software-development\repository-blueprint-audit\SKILL.md` | 10.701 bytes, mtime 2026-10-20 23:06 |
| `...\references\criba-audit-pitfalls-2026-09.md` | 5.442 bytes, mtime **2026-10-20 23:11** |

**Alcance del cambio de la referencia:** añade 9 secciones de "trampas verificadas"
de auditoría CRIBA. Las relevantes para esta sesión:

- **§6** — fallos fantasma por cwd incorrecto: documenta exactamente los 2 fallos que
  aparecieron en la corrida desde la raíz del repo.
- **§7** — artefactos de estado que se contradicen a sí mismos: documenta E6.
- **§8** — un grep de un símbolo no es cobertura de ejecución: documenta el estándar
  aplicado a la cadena T07→T10.
- **§9** — el estado de publicación es parte de cada afirmación: documenta la
  limitación de no afirmar CI verde para una rama local.

**No se hicieron más modificaciones de skills** y no se revirtió ningún cambio.

---

## 11. Decisión de estabilidad y gates exigibles

### 11.1 Decisión

```
READY_FOR_PROMPT_10 = NO
```

**Justificación:** la candidata es técnicamente sólida en el eje producto, pero
**dos gates exigibles por PROMPT 00 no están superados**, y ambos son condición de
pilotabilidad, no cosmética.

### 11.2 Qué SÍ está superado

| Gate | Estado | Evidencia |
|---|---|---|
| Suite CRIBA completa (como CI) | **PASS** | 2226 passed / 16 skipped / exit 0 |
| Suite SUPRA completa | **PASS** | 325 passed / exit 0 |
| Tests P10 | **PASS** | 39 passed |
| Sentinel i18n | **PASS** | 6 passed |
| Sentinel import boundary | **PASS** | 3 passed |
| mypy baseline | **PASS** | 174 files, debt 0/0 |
| ruff (reglas CI) | **PASS** | All checks passed |
| Diff sin cambios accidentales | **PASS** | +3/-2 en 2 ficheros de producto |
| main intacto | **PASS** | `defd0fd` == `origin/main` |

### 11.3 Gates que FALTAN (bloqueos concretos)

| # | Bloqueo | Por qué impide el piloto | Siguiente acción verificable |
|---|---|---|---|
| **B1** | **CI remoto del SHA candidato: `NOT_EXECUTED`.** La rama no está publicada y no hay runs que demuestren verde en el entorno de CI | Sin CI remoto, las 4 correcciones no están verificadas **en el entorno que cuenta**. El piloto no puede arrancar sobre un SHA no avalado por CI | Publicar la rama candidata y confirmar `Monorepo CI` verde. **Requiere autorización del propietario** (push). No se hizo push |
| **B2** | **PHYSICAL_REPOS roto (`validate()` → exit 2).** La herramienta de reanudación de Hermes no puede determinar el estado real de los repos | Si el piloto se interrumpe, **no se puede reanudar con garantía** desde el estado de continuidad. Es el mecanismo que PROMPT 00/Paso E establecen para no perder trabajo | Corregir `PHYSICAL_REPOS` a `C:\ASTRA_WORK\Criba-Blackforge-Supra` y verificar `validate() == 0`. **Decisión del propietario** |
| **B3** | **E6–E9 sin reconciliar.** Los artefactos de estado se contradicen y no usan el esquema que el Paso E exige | El estado declarado no es fiable: un operador que lea `CONTINUITY.md` creería que P10-T09 no existe cuando sí existe. Riesgo de decisión errónea | Corrección de los artefactos, alineada al SHA candidato. **Decisión del propietario** |

**B1 es el bloqueo duro.** B2 y B3 son de continuidad: no afectan a la ejecución
del producto (evidencia en §8.3), pero sí a la capacidad de reanudar y a la
fiabilidad del estado declarado.

### 11.4 Lo que NO bloquea

- Los 2 fallos `cwd`-dependientes de la corrida desde la raíz: **no son del producto**
  (el test es byte-idéntico a la base y pasa 30/30 desde el cwd de CI).
- Los feature flags desactivados: es el estado declarado, no un defecto.
- La ausencia de rama #11 en local: su trabajo está absorbido (verificado por
  `git merge-base --is-ancestor`).

---

## 12. Siguiente acción exacta

**No se inicia PROMPT 10 desde esta tarea.**

La siguiente acción verificable, en orden:

1. **Decidir sobre B1:** ¿se autoriza publicar la rama candidata
   `reconcile/candidate-fix-20261020` (`7b035a3`) para obtener CI remoto?
   - Si **NO**: el piloto permanece bloqueado en B1; documentar el bloqueo y detenerse.
   - Si **SÍ**: publicar, esperar `Monorepo CI`, y si es verde pasar al paso 2.
2. **Decidir sobre B2/B3:** ¿se autoriza corregir `PHYSICAL_REPOS` y reconciliar
   los artefactos E6–E9?
   - Si **SÍ**: aplicar las correcciones, reejecutar `validate()` (debe dar 0) y
     actualizar `STATE.json`/`CONTINUITY.md`/`P10-T07.json` alineados a `7b035a3`.
   - Si **NO**: declararlos deuda aceptada y documentarla.

**No se hizo merge a `main`, ni push, ni release, ni se activó el executor de
BLACKFORGE. No se reinició PROMPT 00. No se añadió ningún cambio de producto para
justificar trabajo adicional.**
