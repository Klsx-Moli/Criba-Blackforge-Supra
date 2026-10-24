# PROPUESTA DE INTEGRACIÓN A MAIN — NO EJECUTADA

**Fecha:** 2026-10-23 · **Candidato local:** rama `reconcile/candidate-fix-20261020` @ `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0`
**Destino canónico:** `main` @ `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b`
**PR #23:** OPEN, head `b07147b`, base `main` — **no modificar**.

> Esta propuesta NO se ejecuta. No hay commit, push, merge ni cambio de rama.
> `MAIN_RECONCILED` NO está declarado: sólo existe el candidato local.

---

## 1. Contenido propuesto para main

### 1.1 Cambios de producto (working tree, sin commit)

| Archivo | Qué aporta | Evidencia |
|---|---|---|
| `criba-blackforge/src/criba/lottery.py` | F3: `family`/`genome` en el pool (pérdida contractual reparada) | RED→GREEN; mutación 5 failed; 6 tests |
| `criba-blackforge/src/criba/inventar.py` | F3: `family`/`family1`/`family2`/`genome` en entries | verificado con `invent(offline=True)` |
| `criba-blackforge/benchmarks/innovation/criba_adapter.py` | F5: informe ligado a la invocación + `family` | F5 13 passed |
| `criba-blackforge/benchmarks/innovation/harness.py` | F5: recoge informe del objeto, no de getter | F5 13 passed |
| `criba-blackforge/src/criba/intelligence/execution.py` | Canon: T061/T054 en `_INPUT_ADAPTERS` | wiring verificado |
| `criba-blackforge/src/criba/intelligence/invention/recombination.py` | Canon: T061 + T054 (NUEVO) | 38 passed + mutación acreditada |

### 1.2 Tests nuevos (untracked)

| Archivo | Tests |
|---|---|
| `tests/unit/test_lottery_family_delivery.py` | 6 |
| `tests/unit/test_selection_report_attribution.py` | 11 |
| `tests/unit/test_selection_report_persistence.py` | 11 |
| `tests/intelligence/test_t061_attribute_substitution.py` | 11 |
| `tests/intelligence/test_t061_wiring.py` | 5 |
| `tests/intelligence/test_t054_technological_recombination.py` | 6 |

### 1.3 Documentación

`docs/audits/CBS_SPRINT_LOCAL_F5_F3_INFORME.md`, `CBS_MAXIMUM_RECONCILIATION_CHECKPOINT.md`, `CBS_LEDGER_UNIFICADO_RECONCILIACION.md` → **conjunto documental**, no producto.

## 2. Procedencia

| Contenido | Procedencia | Sustituye | Conserva |
|---|---|---|---|
| F5 | delta local previo (no commit) | nada (era WIP) | `criba_fn` legacy |
| F3 | esta sesión (diagnóstico previo) | pool sin `family`/`genome` | `family1`/`family2`, scoring intacto |
| T061/T054 | esta sesión | `invention.recombination` ausente | T063 y resto de operators |

## 3. No publicar

- `.hermes/`, `P10.md`, `audits.rar`, `_backup_20261022/`, logs, locks.
- `build/`, `dist/`, `dist_final/` (artefactos de build, no fuente).
- Datos de usuario, `criba.sqlite3`, `supra_state/`.

## 4. Relación con PR #23

- PR #23 ya contiene el head `b07147b` y su base es `main`.
- El delta local (F5/F3/T061/T054) es **posterior** a ese head: sería un **avance rápido** sobre la misma rama, no una sustitución.
- **No se propone cerrar PR #23 ni crear otra**: no hay evidencia de sustitución, base incorrecta ni estrategia mejor justificada.

## 5. Riesgo y rollback

| Riesgo | Mitigación |
|---|---|
| F3 cambia decisiones de selección | Registrado: la consecuencia es legítima (family/genome ahora fluyen). Scoring intacto. |
| F5 rompe consumidores legacy | `criba_fn` preservado; 13 passed |
| T061/T054 rompen el dispatch | Cableado con adapter `_evidence_first`; 38 passed |
| Mutación T061 | Acreditada con snapshot (`PROVENANCE_VERIFIED`) |

**Rollback:** revertir el slice de los 5 ficheros modificados + eliminar los 2 nuevos (recombination.py) desde el patch preservado. Los tests nuevos son aditivos.

## 6. Gates pendientes antes de push

1. Revisión con SHA propio del delta (Hermes es writer, no verificador independiente).
2. `tests/intelligence` (448) y `tests/unit` (1327) — ya ejecutados y verdes.
3. No romper consumidores de `CribaResult`/`criba_fn` — verificado.
4. Confirmar que `blackforge_broker.py`/`blackforge_case.py` son EOL-only (verificado: byte-idénticos a HEAD).

## 7. Gates pendientes antes de merge

1. CI verde en la rama.
2. Aprobación explícita del propietario.
3. Aprobación del esquema ledger (PENDING — no inventada).
4. `PREREGISTRATION_STATUS = NOT_APPROVED` y `PILOT_EXECUTION_ALLOWED = NO` siguen vigentes: el merge no autoriza el piloto.

## 8. Estado

`MAIN_RECONCILED = NO` (sólo candidato local). Propuesta preparada, **no ejecutada**.
