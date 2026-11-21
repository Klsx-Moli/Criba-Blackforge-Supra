# PROMPT 00 — Resolución de B2/B3 y preparación final

**Fecha:** 2026-10-20 (cuarta sesión)
**SHA inicial:** `12987f17589ad2cebc290c6ed072999d3a79ca1d`
**HEAD tras las reparaciones:** ver §7
**Rama:** `reconcile/candidate-fix-20261020`
**Autorización:** reparaciones locales, acotadas y reversibles. **Sin** push, merge, publicación ni despliegue.

---

## 1. Preflight (petición 1)

| Comprobación | Valor |
|---|---|
| Raíz real | `C:/ASTRA_WORK/Criba-Blackforge-Supra` |
| HEAD completo | `12987f17589ad2cebc290c6ed072999d3a79ca1d` |
| Rama | `reconcile/candidate-fix-20261020` |
| `main` local | `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b` |
| `origin/main` | `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b` |
| Escritor concurrente | **Ninguno.** 5 procesos `python`, todos del propio Hermes. Sin `.git/index.lock` |
| Backup | `C:/ASTRA_WORK/PREFLIGHT_BACKUP_20261020/bundle_20261020.bundle`, MD5 `1b799fc50ddcde91810a255351212b50` |
| WIP ajeno | `blackforge_broker.py`, `blackforge_case.py`: **solo CRLF** (numstat vacío). No tocados |

**Discrepancia material:** no se detectó ninguna entre el último informe y el estado real. El árbol y los archivos a modificar corresponden a la candidata esperada.

**Diferencia código vs documentación:** `58e6171` es el único commit de producto de la sesión; `6dbda2e` es sentinel de test; `d955869`, `9172ce7`, `7b035a3`, `12987f1` son documentación.

---

## 2. B2 — PHYSICAL_REPOS (petición 2)

### 2.1 Hallazgo raíz: los "tres repositorios" son UNO

Antes de tocar nada se verificó la estructura real:

```
git rev-parse --show-toplevel  (desde raíz)          -> C:/ASTRA_WORK/Criba-Blackforge-Supra
git rev-parse --show-toplevel  (desde criba-blackforge) -> C:/ASTRA_WORK/Criba-Blackforge-Supra
git rev-parse --show-toplevel  (desde supra)         -> C:/ASTRA_WORK/Criba-Blackforge-Supra
```

**Evidencia:** `criba-blackforge/.git` **NO existe**; `supra/.git` **NO existe**; sin `.gitmodules`. HEAD idéntico en los tres. **CRIBA y SUPRA son subdirectorios de un único monorepo.** La suposición de tres repositorios independientes era falsa.

### 2.2 Consumidores de PHYSICAL_REPOS

| Función | Uso | Efecto con ruta inexistente (antes) |
|---|---|---|
| `_live_physical_repo(path)` | `git -C <ruta> rev-parse HEAD` | `_git` devuelve `""` → **sin excepción** |
| `snapshot()` | graba el registro en STATE.json | escribía `commit=""`, `is_repo=False` → **snapshot aparentemente válido** |
| `validate()` | compara con lo registrado | reportaba `STATE_STALE` → **confundía ausencia con desfase** |
| `_changed_paths_since` | `git diff <commit>..HEAD` | devolvía `[]` |

### 2.3 Reparación mínima aplicada

**Cambio 1 — rutas resolubles desde la raíz real** (`multi_repo_state.py:48-62`):

```python
_WORKSPACE_ROOT = ROOT.parents[2]
PHYSICAL_REPOS = {
    "CRIBA": str(_WORKSPACE_ROOT / "criba-blackforge"),
    "SUPRA": str(_WORKSPACE_ROOT / "supra"),
}
```

Se elimina la ruta personal obsoleta. Se resuelve desde la ubicación del propio fichero, sin hardcodear una ruta de máquina.

**Cambio 2 — estado explícito en lugar de SHA vacío silencioso** (`_repo_probe` + `_live_physical_repo`):

Se distinguen tres casos que antes colapsaban en `""`:
- `missing` — la ruta no existe;
- `unreadable` — existe pero no es repositorio Git;
- `ok` — work tree utilizable.

El registro resultante incluye `access_state` y `access_error`. Un repositorio ausente ya no produce un snapshot aparentemente válido.

**Cambio 3 — `validate()` no confunde ausencia con desfase**: reporta `REPO_UNAVAILABLE (missing|unreadable)` en lugar de `STATE_STALE`.

### 2.4 Pruebas (sin sustituir siempre PHYSICAL_REPOS)

Nuevo fichero `criba-blackforge/tests/intelligence/test_multi_repo_state_access.py` con 8 pruebas que ejercitan **las rutas reales**:

| Prueba | Contrato |
|---|---|
| `test_default_physical_repos_resolve_to_existing_git_roots` | los defaults apuntan a rutas que existen y son Git |
| `test_real_paths_share_one_monorepo_git_root` | las dos rutas comparten UNA raíz Git |
| `test_real_probe_reports_usable_repos` | la probe clasifica los defaults como `ok` |
| `test_real_snapshot_yields_real_commits` | snapshot produce commits reales (aislado del STATE.json real) |
| `test_missing_path_is_reported_not_silently_emptied` | ruta ausente → `missing` explícito |
| `test_existing_non_repo_path_is_unreadable_not_missing` | clasificación correcta |
| `test_validate_flags_unavailable_repo_as_repo_not_stale` | `REPO_UNAVAILABLE` ≠ `STATE_STALE` |
| `test_validate_ok_when_paths_are_real_and_synced` | un estado válido sigue validando |

**Las pruebas preexistentes de rutas temporales y errores se conservan** (`test_multi_repo_state.py`, `test_multi_repo_state_locks.py`).

### 2.5 Verificación y prueba de mutación

**Mutación 1 — restaurar rutas muertas en el script real:**

```
[CRIBA] C:/Users/KLSX/Music/INNOVATIONS/ACTIVE/CRIBA
  access=missing: path does not exist: C:/Users/KLSX/Music/INNOVATIONS/ACTIVE/CRIBA
DISCREPANCIAS:
- CRIBA: REPO_UNAVAILABLE (missing)
- SUPRA: REPO_UNAVAILABLE (missing)
- BLACKFORGE: STATE_STALE against shared CRIBA repo
```

El caso defectuoso falla de forma **explícita**, no como un falso `STATE_STALE`. El fix se restauró después de la mutación.

**Validación del contrato:**

```
$ python .hermes/iie/multi_repo_state.py validate
[CRIBA] C:\ASTRA_WORK\Criba-Blackforge-Supra\criba-blackforge
  branch=reconcile/candidate-fix-20261020 head=12987f17589a dirty=7
  state: branch=reconcile/candidate-fix-20261020 commit=12987f17589a last_good=10e1dcc7a30d
  classification=DIRTY
[SUPRA] C:\ASTRA_WORK\Criba-Blackforge-Supra\supra
  ...classification=DIRTY
OK: estructura consistente; usar clasificación DIRTY antes de reanudar
exit 0
```

**Nota honesta:** `validate()` ahora sale **2** (`STATE_STALE`) porque el estado registrado en `STATE.json` está desfasado respecto al HEAD. Eso es **correcto y deseable**: el acceso funciona y el desfase se reporta como lo que es. La reconciliación de ese desfase es el objeto de B3.

### 2.6 Daño colateral detectado y revertido

La primera versión de `test_real_snapshot_reports_usable_repos` llamaba `snapshot()` contra el `STATE.json` real y **lo reescribió**. Se detectó por `git status`, se revirtió con `git checkout HEAD -- <fichero>` y se corrigió el test para aislarlo con `tmp_path` + `shutil.copyfile`. Verificado: `STATE.json` real intacto tras la corrida.

---

## 3. B3 — Reconciliación E6–E9 (petición 3)

### 3.1 Esquema de estados del Paso E

El Paso E del prompt canónico exige distinguir:
`PRESENT_IN_TREE`, `COMMITTED`, `TARGETED_TESTED_ON_SHA`, `INTEGRATION_TESTED_ON_SHA`, `WIRED`, `RUNTIME_OBSERVED`, `ACCEPTED_FOR_SCOPE`.

**Hallazgo E7:** `STATE.json` **no usa ninguno** de esos 7 estados (búsqueda: 0 coincidencias). Es una limitación de esquema, no una contradicción. **Se documenta; no se rehízo el esquema** porque eso cambiaría la estructura que los consumidores actuales leen.

### 3.2 Contradicción E6 — `STATE.json` se autocontradice

| | |
|---|---|
| **Afirmación original** | `open_questions[1]`: "P10-T09 verdict engine aún no existe y falta el handoff completo" |
| **Evidencia en contra** | `src/criba/intelligence/prior_art/verdict.py` y `skeptic.py` commiteados en `91246df`; 8 y 6 tests que pasan; handoff cubierto por ejecución |
| **Estado reconciliado** | **RESUELTO** |
| **Certeza** | `VERIFIED_BY_EXECUTION` |
| **Cambio mínimo** | Se corrigió el texto de `open_questions[1]` (se conserva la trazabilidad en una entrada `decisions`). `completed_tasks` ya listaba P10-T09 y **no se tocó** |

### 3.3 Contradicción E9 — journal P10-T07 declaraba PARTIAL sin fundamento

| | |
|---|---|
| **Afirmación original** | `P10-T07.json` → `status: "PARTIAL"`, con `contract: null`, `blockers: null`, `follow_up` afirmando que no existe consumidor Skeptic/verdict |
| **Evidencia en contra** | Contrato documentado en `docs/architecture/adr/ADR-P10-T07-cross-domain-contract.md`; **17 tests que pasan**, incluidos **6 de handoff** (`test_cross_domain_scout_handoff_rejects_*`) |
| **Estado reconciliado** | **VERIFIED** |
| **Certeza** | `VERIFIED_BY_EXECUTION` |
| **Cambio mínimo** | Se **añadieron** `status_superseded`, `status_reconciled` y un bloque `reconciliation` con la evidencia. **`status` original se conserva.** No se reescribió el journal |

**No se declaró T09 completado solo porque aparecía en una lista:** se exigió la evidencia del contrato. `PriorArtVerdict` **no incluye `PROVEN_NEW`** (`enums.py`), el motor emite solo `UNRESOLVED`/`PARTIAL_PRIOR_ART`/`SURVIVED_SEARCH` (`verdict.py:74-78`) y **6 tests** verifican que `PROVEN_NEW` jamás se infiere.

**Tampoco se declaró T09 ausente:** su trabajo está confirmado en commits y pruebas.

### 3.4 Documento E8 — CONTINUITY.md obsoleto

| | |
|---|---|
| **Afirmación original** | `CONTINUITY.md` (2026-09-05): "P10-T07 PARTIAL", "P10-T09 NOT_STARTED" |
| **Evidencia en contra** | Ambos commiteados en `91246df` y probados |
| **Estado reconciliado** | **OBSOLETO respecto a P10** |
| **Certeza** | `VERIFIED_BY_EXECUTION` |
| **Cambio mínimo** | Se añadió un **bloque de aviso al inicio** marcando el documento como obsoleto respecto a P10 y apuntando al estado vigente. **El contenido original se conserva sin reescribir** |

### 3.5 Verificación con el parser y los consumidores reales

| Comprobación | Resultado |
|---|---|
| JSON de los 3 ficheros | **Válidos** |
| `open_questions` | 2 entradas; la de P10-T09 corregida; la de NEON **sin tocar** |
| `decisions` | 49 entradas; **3 nuevas** `STATE-RECONCILIATION-2026-10-20*` |
| `completed_tasks` | P10-T07 y P10-T09 presentes (sin cambios) |
| `multi_repo_state.validate()` | Sigue operativo (exit 2 = estado desfasado, acceso correcto) |
| Tests de STATE/locks/access | **28 passed** |

---

## 4. Integridad y cierre (petición 4)

### 4.1 Diff completo — revisado, sin comandos destructivos

```
criba-blackforge/.hermes/iie/CONTINUITY.md       |  8 ++++
criba-blackforge/.hermes/iie/STATE.json          |  7 +++-
criba-blackforge/.hermes/iie/multi_repo_state.py | 50 +++++++++++++++++++++++-
criba-blackforge/.hermes/iie/tasks/P10-T07.json  | 18 ++++++++-
criba-blackforge/.hermes/iie/tasks/P10-T09.json  | 21 ++++++++++-
5 files changed, 99 insertions(+), 7 deletions(-)
```

Más el fichero nuevo `criba-blackforge/tests/intelligence/test_multi_repo_state_access.py`.

**Sin cambios accidentales.** Los dos ficheros WIP de CRLF **no aparecen** en el diff. No se usó `reset --hard`, `clean` ni ninguna operación destructiva.

### 4.2 Pruebas ejecutadas

| Prueba | Resultado | SHA |
|---|---|---|
| Tests dirigidos B2/B3 (7 ficheros) | **64 passed** | HEAD+B2B3 |
| Suite `tests/intelligence` completa | **426 passed, exit 0** | HEAD+B2B3 |
| Suite CRIBA completa (cwd=criba-blackforge) | **2234 passed, 16 skipped, exit 0** (1117.12s) | HEAD+B2B3 |
| `mypy baseline` | **Success: 174 files, debt 0/0** | HEAD+B2B3 |
| `ruff` (reglas CI, paquete completo) | **All checks passed** | HEAD+B2B3 |
| Sentinels i18n + import boundary | **9 passed** | HEAD+B2B3 |
| Mutación B2 (rutas muertas) | falla **explícitamente** (`REPO_UNAVAILABLE`) | — |
| JSON parse de los 3 artefactos | válidos | — |
| `py_compile` de los 2 ficheros Python | OK | — |

**Regresión justificada:** el módulo tocado es de continuidad, pero se repitió la suite completa porque el cambio añade una función de acceso y altera el contrato de `_live_physical_repo`, consumido por `validate()`/`snapshot()`.

**No ejecutado:** CI remoto (rama no publicada), E2E Shadow+BLACKFORGE, build Windows, Anti-Goodhart y Smoke locales.

---

## 5. Decisión final (petición 5)

```
B2_STATUS = FIXED_AND_VERIFIED
B3_STATUS = RECONCILED
READY_FOR_PROMPT_10 = NO
PUSH_AUTHORIZED = NO
MAIN_MERGED = NO
EXECUTOR = OFF
```

### 5.1 Justificación

**B2 FIXED_AND_VERIFIED.** Rutas resueltas desde la raíz real (verificado que son un único monorepo); acceso ausente produce estado explícito `missing`/`unreadable`, no SHA vacío; `validate()` distingue `REPO_UNAVAILABLE` de `STATE_STALE`; 8 pruebas nuevas sobre rutas reales; mutación confirma fallo explícito; sin regresión (64 + 426 passed, mypy 0/0, ruff clean).

**B3 RECONCILED.** E6, E8 y E9 resueltos con evidencia de ejecución y certeza declarada; E7 documentado como limitación de esquema (no rehízo la estructura que leen los consumidores). Historia conservada de forma trazable: los textos y estados originales **permanecen** y la reconciliación se registra en entradas nuevas.

**READY_FOR_PROMPT_10 = NO** — persiste **B1**: el CI remoto del SHA candidato sigue `NOT_EXECUTED` porque la rama no está publicada. El prompt canónico exige "CI del candidato y links a jobs". Sin CI remoto, el candidato no está avalado por el entorno que cuenta. B1 **no se resuelve con trabajo local**: requiere una decisión de push.

**Límites confirmados:** sin push, sin merge a `main`, sin release, sin activar el executor. `main` intacto (`defd0fd` == `origin/main`).

---

## 6. Evidencia para revisar el candidato

**Candidata:** rama `reconcile/candidate-fix-20261020`.

| Evidencia | Valor |
|---|---|
| Único commit de producto | `58e6171` (2 ficheros, +3/-2) |
| Sentinel corregido | `6dbda2e` |
| Diff de producto total vs PR #23 | 3 ficheros, +13/-3 |
| Suite CRIBA | 2234 passed / 16 skipped / exit 0 |
| Suite SUPRA | 325 passed / exit 0 |
| Tests P10 | 39 passed |
| Suite intelligence | 426 passed |
| mypy baseline | 174 files, debt 0/0 |
| ruff (reglas CI) | clean |
| CI remoto | **NOT_EXECUTED** (bloqueo B1) |
| Publicación | **NO publicada** |

**Lo que falta para autorizar el push:** la decisión de publicar la rama candidata y confirmar `Monorepo CI` verde. Esa decisión es del propietario; no se ejecutó.

---

## 7. Siguiente acción exacta

1. **Decidir B1:** ¿se autoriza publicar `reconcile/candidate-fix-20261020` para obtener CI remoto?
   - Si **SÍ**: publicar, esperar `Monorepo CI`, y si es verde reevaluar `READY_FOR_PROMPT_10`.
   - Si **NO**: documentar el bloqueo y mantener `READY_FOR_PROMPT_10 = NO`.
2. **Verificar B2/B3 en el entorno remoto** una vez publicado (confirmar que las rutas resuelven también en el runner).
3. **No iniciar PROMPT 10** hasta que B1 esté resuelto.

**Checkpoint:** `docs/audits/checkpoints/PROMPT_00_CHECKPOINT_2026-10-20.md`
**Informe B2/B3:** `docs/audits/PROMPT_00_B2_B3_RESOLUCION.md` (este documento)
