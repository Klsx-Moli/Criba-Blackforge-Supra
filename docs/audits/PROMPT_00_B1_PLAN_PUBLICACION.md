# PROMPT 00 — B1: Plan de publicación controlada para CI remoto

**Fecha:** 2026-10-20 (quinta sesión — preparación, sin ejecución)
**Estado:** PLAN. **Ningún push ejecutado.**
**Rama candidata:** `reconcile/candidate-fix-20261020`

---

## 1. Preflight read-only

| Comprobación | Valor |
|---|---|
| Raíz | `C:/ASTRA_WORK/Criba-Blackforge-Supra` |
| Rama local | `reconcile/candidate-fix-20261020` |
| HEAD completo | `2cae687917779bd764230cc23fc1bc9a5819b53b` |
| `main` local | `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b` |
| `origin/main` | `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b` |
| Escritor concurrente | **Ninguno** (solo procesos del propio Hermes) |
| Backup | `bundle_20261020.bundle`, MD5 `1b799fc50ddcde91810a255351212b50` |

**Discrepancia con el último checkpoint:** ninguna. El HEAD coincide con el documentado (`2cae687`).

**WIP sin commitear (NO se publicaría — Git no empuja el working tree):**

```
 M criba-blackforge/src/criba/blackforge_broker.py     (solo CRLF, numstat vacío)
 M criba-blackforge/src/criba/blackforge_case.py       (solo CRLF, numstat vacío)
?? .hermes/
?? criba-blackforge/.hermes/iie/checkpoints/P10.md
```

Estos cambios son ajenos a la tarea y **no** se incluyen en el push: Git solo transmite commits.

---

## 2. Relación de ancestros (petición 2)

**HEAD remoto de la rama origen de PR #23:**

```
git ls-remote origin refs/heads/integrate/shadow-supra-final
b27ccd63fd3f25c445ddc88e8ecb8300a25a6e90	refs/heads/integrate/shadow-supra-final
```

**¿Se movió desde la última observación?** **NO.** Última observación registrada `b27ccd6…`; ahora `b27ccd6…`. Idéntico.

**¿La candidata es descendiente de ese commit?**

```
git merge-base --is-ancestor b27ccd6 HEAD   -> SI
commits que la candidata añade sobre el remoto:  10
commits del remoto que la candidata no tiene:    0
```

**Conclusión:** la candidata es descendiente directo con **0 commits divergentes**. Un push es **avance rápido** y **no requiere `--force`**.

**Estado de la PR #23 (consultado a GitHub):**
`state=OPEN`, `mergeable=MERGEABLE`, `baseRefName=main`, `headRefName=integrate/shadow-supra-final`, `headRefOid=b27ccd6…`.

---

## 3. Plan de publicación (petición 3)

**Estrategia: actualizar la rama origen de la PR #23.** Sin PR nueva, sin fusión, sin reescritura.

### 3.1 Comando previsto

```bash
git push origin HEAD:integrate/shadow-supra-final
```

- **Avance rápido** confirmado (`b27ccd6` es ancestro de `HEAD`, 0 divergentes).
- **Sin `--force`.** No sería necesario; forzar sería un error.
- **No crea otra PR.** La PR #23 existente pasa a apuntar al nuevo HEAD y dispara CI sobre la candidata.
- **No fusiona nada.** `main` queda intacto.

### 3.2 SHA exacto que se publicaría

```
2cae687917779bd764230cc23fc1bc9a5819b53b
```

### 3.3 Referencia remota que se actualizaría

| Referencia | Antes | Después |
|---|---|---|
| `refs/heads/integrate/shadow-supra-final` (origen PR #23) | `b27ccd63fd3f25c445ddc88e8ecb8300a25a6e90` | `2cae687917779bd764230cc23fc1bc9a5819b53b` |

**Protección de ramas:** ni `integrate/shadow-supra-final` ni `main` están protegidas en GitHub (`HTTP 404 Branch not protected`). El push directo es posible; `main` no se toca de todos modos.

### 3.4 Los 10 commits que llegarían

```
2cae687 docs(prompt00): checkpoint update - B2/B3 resolved, B1 remains
b297884 docs(prompt00): B2/B3 resolution report
17cb658 docs(iie): reconcile P10-T07/T09 state artifacts (E6/E8/E9)
8d729c8 fix(iie): resolve PHYSICAL_REPOS from the real workspace root
12987f1 docs(prompt00): Paso F required outputs + PHYSICAL_REPOS finding
7b035a3 docs(prompt00): Paso E continuity contrast + honest state findings
9172ce7 docs(prompt00): update checkpoint after i18n fix (Paso D)
58e6171 fix(shadow): align i18n keys with defined names and complete EN table
d955869 docs: add PROMPT 00 checkpoint report with state and next actions
6dbda2e checkpoint: fix import boundary sentinel to check real imports not substrings
```

### 3.5 Diff que llegaría

```
13 files changed, 1489 insertions(+), 10 deletions(-)
```

**Desglose:**

| Categoría | Archivos | Líneas |
|---|---|---|
| **Código de producto** | `shadow_window.py`, `i18n.py` | +3 / −2 |
| **Tests** | `test_blackforge_regression.py`, `test_multi_repo_state_access.py` (nuevo) | +159 / −1 |
| **Tooling de continuidad** | `multi_repo_state.py` (B2) | +48 / −2 |
| **Artefactos de estado** | `STATE.json`, `CONTINUITY.md`, `P10-T07.json`, `P10-T09.json` (B3) | +51 / −5 |
| **Documentación** | 4 informes/checkpoint | +1228 / −0 |

### 3.6 Impacto sobre la PR #23

- La PR pasa de `b27ccd6` a `2cae687` (10 commits, avance rápido).
- **No cambia su base** (`main`) ni su estado (OPEN).
- **CI se re-ejecuta automáticamente** sobre el nuevo HEAD.
- El diff de producto es mínimo: 2 ficheros de producto (`i18n.py` +1, `shadow_window.py` 2 claves) y 1 sentinel de test.

---

## 4. Workflows que se ejecutarían realmente (petición 5)

### 4.1 Monorepo CI (`ci.yml`)

**Trigger:** `pull_request` (sin filtro de ramas). **Se ejecuta en cualquier PR**, incluida la #23.

| Job | Runner | Comando |
|---|---|---|
| `criba-blackforge` | windows-2025 | `uv run --locked pytest -q` + mypy baseline + ruff |
| `criba-blackforge-linux` | ubuntu-24.04 | `pytest -q` + mypy gate (**`continue-on-error: true`** — informativo) |
| `supra` | windows-2025 | `pytest -q --no-header` + `ruff check .` + `mypy src/supra_agentic` |
| `result` | — | agregador |

**Los 8 tests nuevos de B2 corren bajo este gate** (`tests/intelligence/test_multi_repo_state_access.py` está bajo `tests/`). **Verificado en local:** CRIBA completo 2234 passed, mypy debt 0/0, ruff clean.

### 4.2 Anti-Goodhart RETRYBOX Gate (`anti-goodhart.yml`)

**Trigger:** `pull_request` (sin filtro). Se ejecuta.

### 4.3 Shadow Windows Build Smoke (`shadow-windows-build-smoke.yml`)

**Este workflow SÍ tiene filtro de ramas** y `integrate/shadow-supra-final` **no** está en la lista:

```yaml
on:
  pull_request:
    branches:
      - main
      - codex/interpreter-hardening-20261004
      - chatgpt/shadow-supra-reliability-20261008
      - chatgpt/shadow-exe-journey-20261008
    paths: [...]
```

**Evidencia de que sí se ejecutó en la práctica:** 5 runs de este workflow en `integrate/shadow-supra-final` (39194815283, 39160808594, 39153712731, 39145220809, 39143557046). El evento fue `pull_request`. El filtro de ramas se evalúa contra la **base** (`main`), no contra la rama de origen.

**Además, mi diff toca una ruta del filtro `paths`:** `criba-blackforge/shadow_ui/shadow_window.py` coincide con `criba-blackforge/shadow_ui/**`. Así que el trigger por rutas también se cumple.

**Conclusión:** el Smoke se ejecutará, pero **no se afirma como garantía** — se confirmará por el `run list` posterior al push.

### 4.4 Qué NO ocurrirá

- No se crea PR nueva.
- No se fusiona con `main`.
- No se publica release.
- No se activa el executor de BLACKFORGE.

---

## 5. Verificación posterior al push (no ejecutada)

Tras el push, la verificación se hará **leyendo GitHub**, no inferida:

```bash
gh run list --repo Klsx-Moli/Criba-Blackforge-Supra \
  --branch integrate/shadow-supra-final --limit 6
gh pr view 23 --repo Klsx-Moli/Criba-Blackforge-Supra \
  --json headRefOid,statusCheckRollup
```

**Criterio de éxito:** `Monorepo CI` verde (los 4 fallos históricos eran exactamente los corregidos). Si `criba-blackforge` falla, se inspecciona el log del job y se compara con el diff.

**Riesgo declarado:** el job `criba-blackforge-linux` es `continue-on-error: true` (informativo). Sus fallos **no** bloquean el merge; no deben interpretarse como bloqueo ni como verde.

---

## 6. Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| CI falla en un test nuevo bajo Windows | Baja | Los 8 tests nuevos pasan localmente en Windows; se inspeccionará el log si ocurre |
| El Smoke no se dispara | Baja | Confirmado que se disparó 5 veces en esa rama; se verificará por `run list` |
| Ruta de B2 no resuelve en el runner | Media | `ROOT.parents[2]` es relativo a la ubicación del script; en el checkout de Actions la estructura `criba-blackforge/.hermes/iie/` se mantiene. **Se verificará tras el push** |
| El job Linux falla (informativo) | Alta | No bloquea; se documenta como no-bloqueante |
| Interpretar la creación de la ref como CI verde | — | **Prohibido.** Solo `run list` con conclusión `completed` cuenta como evidencia |

---

## 7. Resumen del plan

| Campo | Valor |
|---|---|
| SHA a publicar | `2cae687917779bd764230cc23fc1bc9a5819b53b` |
| Referencia a actualizar | `refs/heads/integrate/shadow-supra-final` |
| Desde | `b27ccd63fd3f25c445ddc88e8ecb8300a25a6e90` |
| Tipo | Avance rápido (10 commits, 0 divergentes) |
| Comando | `git push origin HEAD:integrate/shadow-supra-final` |
| Fuerza | **No requerida; no se usará `--force`** |
| PR afectada | #23 (OPEN, base `main`) |
| `main` | **No se toca** (`defd0fd` intacto) |
| Release | No |
| Executor BLACKFORGE | OFF |

**Autorización requerida:** explícita antes de ejecutar el push. **No se ha ejecutado ningún push, ni merge, ni release.**

---

## 8. Estado de decisión (sin cambios)

```
READY_FOR_PROMPT_10 = NO      # hasta que el CI remoto esté verde
PUSH_AUTHORIZED = NO          # se solicita autorización explícita
MAIN_MERGED = NO
EXECUTOR = OFF
```

**Siguiente acción exacta:** conceder o denegar la autorización de push. Si se concede, ejecutar el comando de §3.1 y verificar con los comandos de §5.
