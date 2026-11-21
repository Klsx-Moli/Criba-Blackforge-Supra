# Smoke offline dual-domain (funcional, NO científico)

Fecha de ejecución: 2026-11-02.
Comando: `.venv\Scripts\python.exe benchmarks/innovation/run_dual_domains_smoke.py`
Salida: `benchmarks/innovation/smoke_dual_domains.json`.

## Qué se ejecutó

- 10 problemas smoke (`problems_smoke.json`: G01–G05 generales, B01–B05 BLACKFORGE).
- 4 condiciones por problema = **40 runs**, todos `status=OK`:
  - `A_DIRECT` / `B_STRONG_PROMPT`: stub determinista local; sólo validan schema/runner/métricas. **No simulan un modelo real ni su calidad.**
  - `C_CRIBA`: `run_criba_selection` real (lotería estratificada + selector diversity-aware sobre el catálogo CRIBA).
  - `D_BLACKFORGE`: `blackforge_fn` real (lotería + selector diversity-aware sobre el catálogo BLACKFORGE de 723 registros).
- Semilla explícita `seed=7`; sin red, sin modelo, sin llamadas a proveedor.

## Resultado observado

- `runs=40`, `status_counts={OK: 40, UNAVAILABLE: 0}`.
- `criba_ok=10`, `blackforge_ok=10`, `direct_ok=10`, `strong_ok=10`.
- Los candidatos de C/D son cruces estructurados con `methods/classes/genome/family`; `prueba_concreta` puede ser `None` en D porque el adaptador mide selección, no síntesis interpretada.
- `structural_diversity=0.0` en este smoke con `n=3` y genomas sintéticos/stub: el informe **no** interpreta eso como falta de diversidad real; el pool de 3 finalistas y los genomas del stub/directo son insuficientes para esa conclusión.

## Límites explícitos

- Esto es **funcionalidad**, no evidencia de superioridad. No hay baseline de modelo real, no hay revisores humanos ciegos, no hay preregistro verificado ni dataset de 30 problemas.
- `scientific_advantage` sigue siendo `NOT_ESTABLISHED`; AntiGoodhart sigue OFF; D3/D4/D6 siguen `UNRESOLVED`.
- El presupuesto live del ledger `physical_budget_LIVE_STEPFUN.sqlite3` está **12/12 agotado**; no se ejecutaron más llamadas de modelo en esta fase.
- La comparación «mejor que un modelo» requiere: ledger nuevo/autorizado, mismo modelo y presupuesto para A/B, dataset preregistrado ≥30 problemas (o aprobación explícita de N=10 exploratorio), revisiones ciegas independientes y criterios causales preregistrados.

## Regresiones asociadas

- `tests/unit/test_lottery_stratified.py`: estrato residual honesto para métodos sin `thinking_class` (BLACKFORGE participa en estratificado mixto).
- `tests/unit/test_shared_invention_service.py`: motor/servicio compartido con los 5 modos y catálogo combinado real.
- `tests/unit/test_functional_proposal_journey.py`: Shadow y BLACKFORGE despachan los 5 modos al mismo `run_invention`.
- `tests/unit/test_harness.py`, `tests/unit/test_benchmark_harness.py`: condición `D_BLACKFORGE` real y smoke 10×4.
- `tests/unit/test_product_value_evaluation.py`: pares CRIBA/BLACKFORGE/DIRECT con denominadores separados.
