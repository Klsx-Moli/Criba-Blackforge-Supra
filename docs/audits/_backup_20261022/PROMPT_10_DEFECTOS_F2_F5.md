# EXPEDIENTE DE DEFECTOS F2–F5 — selector CRIBA

**Estado: EXPEDIENTE DE DIAGNÓSTICO.** No modifica código productivo.
**SHA de código observado:** `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0`
**Regla:** cualquier corrección posterior debe tener **SHA propio** y **evaluación separada**. No se cambian criterios después de observar resultados para favorecer a CRIBA.

---

## F2 — Semilla aparentemente ignorada

**Reproducción mínima (ejecutada):**
```python
select_blackforge(seed=1, session_size=12, profile='hybrid').to_dict()['selected_ids']
select_blackforge(seed=2, ...), select_blackforge(seed=3, ...)
```
**Resultado observado:** `seeds 1/2/3 → mismo selected_ids` (`True`). Verificado también 8/8 seeds idénticos.
**Ámbito:** `criba-blackforge/src/criba/blackforge_selector.py` `select_blackforge()` — la selección de sesión BLACKFORGE es **invariante a `seed`**.
**Criterio de resolución propuesto:** si `seed` es parámetro documentado como semilla de reproducibilidad, su invarianza es defecto; si el diseño es **deliberadamente determinista por perfil**, entonces `seed` es parámetro muerto y debe documentarse o retirarse. **Pendiente de decisión de diseño del propietario** (no se infiere).
**Prueba de regresión propuesta:** test que fije `seed` y verifique que el `selected_ids` **cambia** (o documente explícitamente que no debe cambiar) — nunca un test que codifique la invarianza actual como correcta sin decisión.
**Estatus:** CONFIRMADO (invarianza verificada). Resolución: PENDIENTE DE DECISIÓN.

---

## F3 — Cuatro candidatos con puntuación idéntica

**Reproducción mínima (ejecutada):**
```python
criba_fn('Detectar abuso de permisos en agentes autonomos', seed=7, n_candidatos=4)
```
**Resultado observado:** `scores = [0.349, 0.349, 0.349, 0.349]` → `todos iguales: True`.
**Ámbito:** `criba-blackforge/benchmarks/innovation/criba_adapter.py` `criba_fn()` + `criba/diversity_selector.py` `select_finalists()`.
**Causa observada:** con `batch_size = max(8, n*2) = 8`, el pool de cruces produce **un único valor de score** (0.349); `select_finalists` recorta por `quality_floor` y no discrimina. Con `batch_size=16` el pool sí muestra dos scores (0.417/0.349), pero `criba_fn` fija `batch_size = max(8, n_candidatos*2)`.
**Criterio de resolución propuesto:** si el piloto exige que el ranking discrimine entre los 4 candidatos, el pool debe tener **variabilidad de score real**; el `batch_size` del adapter debe producir candidatos con mérito diferenciado, o declararse que el ranking no discrimina y que la selección es por orden de entrada (lo que invalida el piloto).
**Prueba de regresión propuesta:** test que verifique que los N candidatos devueltos tienen **al menos dos valores de score distintos** (o que el informe declare empate explícito con su regla).
**Estatus:** CONFIRMADO. Resolución: PENDIENTE (bloquea el endpoint del piloto).

---

## F4 — Desempate dependiente del orden de entrada

**Reproducción mínima (ejecutada):**
```python
pool = get_top_ideas(16); s1 = select_finalists(pool, 4)
shuffled = pool[:]; random.Random(1).shuffle(shuffled); s2 = select_finalists(shuffled, 4)
```
**Resultado observado:** `pool barajado cambia seleccion: True` (los objetos elegidos cambian).
**Ámbito:** `criba/diversity_selector.py` `select_finalists()`; `tiebreak_rule = "deterministic idea_id order among equal operational utility; tie-break is not scientific superiority"`.
**Criterio de resolución propuesto:** la regla de desempate **ya declara** que no es superioridad científica, pero el orden de entrada del pool depende de `LotteryEngine.get_top_ideas`, que es determinista por seed. Si el pool es fijo por seed, la selección es reproducible; pero **no** es invariante a reordenaciones del pool. El criterio: o (a) el desempate se hace sobre un **contenido** canónico (hash del candidato), o (b) se declara que la selección depende del orden de generación y eso se registra como limitación. **No** se corrige silenciosamente.
**Prueba de regresión propuesta:** test que verifique invarianza del conjunto seleccionado ante permutaciones del pool (si se adopta (a)) o test que fije y documente la dependencia (si se adopta (b)).
**Estatus:** CONFIRMADO. Resolución: PENDIENTE DE DECISIÓN (a) vs (b).

---

## F5 — Pérdida del informe de selección

**Reproducción mínima (ejecutada):**
```python
import inspect; src = inspect.getsource(criba_adapter.criba_fn)
# finalists, _report = select_finalists(pool, n_candidatos)  ->  _report no se usa
criba_fn(...)[0].keys()  # ['classes','description','genome','idea_id','methods','score','title']
```
**Resultado observado:** el `report` de `select_finalists` (con `tie_sets`, `discarded_by_floor`, `quality_floor`, `pool_size`, `valid_size`, `opportunity_accounting`) es **descartado**; `criba_fn` devuelve solo 7 campos y pierde la contabilidad de selección.
**Ámbito:** `criba_adapter.py:18` `criba_fn()`.
**Criterio de resolución propuesto:** el piloto exige **contabilizar todas las oportunidades** (canónico §5: candidatos descartados no desaparecen de la contabilidad). Perder `discarded_by_floor`/`tie_sets` rompe esa exigencia. Corrección: que `criba_fn` (o el harness) **persista el `report` completo** por episodio.
**Prueba de regresión propuesta:** test que verifique que el artefacto del episodio incluye `pool_size`, `valid_size`, `discarded_by_floor` y `tie_sets`.
**Estatus:** CONFIRMADO. Resolución: PENDIENTE (bloquea la contabilidad del piloto).

---

## Tabla de estado

| ID | Defecto | Reproducción | Observado | Criterio de resolución | Regresión propuesta | Estatus |
|---|---|---|---|---|---|---|
| F2 | Semilla ignorada | ejecutada | 8/8 seeds idénticos | PENDIENTE DE DECISIÓN (diseño) | test de varianza/declaración | CONFIRMADO |
| F3 | 4 candidatos mismo score | ejecutada | 0.349×4 | PENDIENTE (bloquea endpoint) | test de ≥2 scores distintos | CONFIRMADO |
| F4 | Desempate por orden de entrada | ejecutada | barajar cambia selección | PENDIENTE (a) o (b) | test de invarianza o fijación | CONFIRMADO |
| F5 | Report de selección perdido | ejecutada | 7 campos, report descartado | PENDIENTE (bloquea contabilidad) | test de campos de report | CONFIRMADO |

**Regla de cierre:** ninguno se cierra sin SHA propio, prueba de regresión ejecutada y evaluación separada. **Ninguno se corrige en esta fase.**

---

## ACTUALIZACIÓN 2026-10-22 (conciliación) — F2 y F4 matizados

**F2 — cierre documentado, NO por decreto.** `FACT`: el contrato real del parámetro está escrito en `criba-blackforge/src/criba/blackforge_selector.py:9`:
> *"deterministic stable ordering; seed is recorded for API/report compatibility but does not currently perturb ranking"*

Y el test existente (`tests/unit/test_blackforge_selector.py:43`) se llama `test_different_seed_may_vary_but_keeps_quotas` — verifica **cuotas**, no variación. **Conclusión:** F2 **no es un defecto**: la invarianza a `seed` es **diseño documentado** (semilla registrada solo para compatibilidad de API/informe). `F2_STATUS = NOT_A_DEFECT` (por contrato). El piloto debe registrar igualmente la regla (canónico §4 bullet 5).

**F4 — matización importante.** La reproducción original barajó el pool manualmente, lo que **no** es una operación del producto. `FACT` (verificado): con el pool determinista de `LotteryEngine.get_top_ideas` (seed fija), el orden de `select_finalists` es **estable entre corridas** (`[idea_id]` idéntico). Por tanto F4 **no** es «desempate dependiente del orden de entrada» en el flujo real; es una **fragilidad potencial** si el pool se reordena por una vía no determinista. `F4_STATUS = CONFIRMED_LIMITATION (no defecto activo)`.

**F3 y F5 — sin cambios.** Ambos siguen CONFIRMADOS y bloqueantes: el ranking no discrimina entre los 4 candidatos (F3) y el report de selección se descarta (F5).
