# HANDOFF — checkpoint para reanudar con /new + palabra

Fecha: 2026-10-14
Rama aislada: hermes/cloud-provider-layer-20261013
HEAD: 72a2155 (pusheada a origin, sin merge a main)
Remoto: Klsx-Moli/Criba-Blackforge-Supra
Writer: Hermes (único). Worktree: C:\ASTRA_WORK\Criba-Blackforge-Supra

## Contexto de la tarea
Ejecutando TAREA_LARGA_UNIFICADA_CRIBA_SUPRA_V3 (leer
C:\Users\KLSX\Downloads\TAREA_LARGA_UNIFICADA_CRIBA_SUPRA_V3.md).
Prioridad explícita de moli: mover verificación pesada a Modal, NO cargar GPU local.

## Estado de gates (V3)
- G0/F0 BASELINE: OK. BASE_SHA=defd0fd (main), sin stashes, diff limpio.
  docs/audit/BASELINE.md existe.
- F1/F6 fix flaky: OK. commit 57f0ae7. Suite CRIBA 2074 passed seed fija.
  Causa: hybrid compartía artifacts/criba.sqlite3; GUI usaba qWait que no
  bombea señales cross-thread de Qt (fix: fixture DB tmp_path + QEventLoop).
- G1 limpieza: OK. commit 4e47ea7. Retirada opción muerta --llm nebius
  (create_backend solo offline/cloud). test_cli 18/18. CLEANUP_REPORT.md.
  Histórico NO purgado (RESIDUAL_HISTORICAL declarado honesto).
- Modal runner: OK. commit 72a2155. .autoregen/cloud/modal_runner.py.
  probe_paths PASS en la nube (cwd=/workspace, montaje correcto).

## Estados NO alterados (respetar)
STANDARD=DISABLED, G3=NOT_VERIFIED, D3/D4/D6 sin resolver. BLACKFORGE inerte.
NUNCA merge/push main sin OK explícito de moli.

## En curso — mypy_scoped PASS en la nube (2026-10-14 09:0x)
1er intento (proc_d32d6eb3fa89): rc=1 — imagen Modal no incluía types-PyYAML;
  mypy: 1 error en 167 archivos (registry.py:81 "Library stubs not installed
  for yaml"). Fix en el runner (añadir types-PyYAML a uv_pip_install).
2o intento (proc_af68d66ebfc0): rc=0 — "Success: no issues found in 167
  source files". Log: C:\ASTRA_WORK\modal_mypy_scoped_2.log. App:
  ap-A4bYls5AS7E4qRvzzdhkC5. Imagen im-arkPf8idKZHRNIECaj25t7 ya cacheada.
Gate mypy_scoped PASS. Pendiente: pytest_full.

## Modal — cómo lanzar (reglas ya validadas)
- CLI: /c/Users/KLSX/AppData/Local/Programs/Python/Python312/python.exe -m modal
  (Python312 global, NO el venv; perfil klssxx, token OK).
- Desde C:\ASTRA_WORK\Criba-Blackforge-Supra.
- SIEMPRE: PYTHONUTF8=1 PYTHONIOENCODING=utf-8.
- UN gate a la vez (rate limits). Comando:
  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 "<python312>" -m modal run \
    .autoregen/cloud/modal_runner.py --gate <probe_paths|mypy_scoped|pytest_full|pytest_file>
  pytest_file admite --path tests/unit/test_x.py
- Imagen tarda ~15 min en construir la 1a vez (PySide6); luego cached.

## Siguiente punto exacto
1. mypy_scoped PASS en la nube (hecho: 2o intento, rc=0, 167 files).
2. pytest_full en Modal (suite 2074 — lo que más cargaba la GPU local).
   Comando: PYTHONUTF8=1 PYTHONIOENCODING=utf-8 "<python312>" -m modal run \
   .autoregen/cloud/modal_runner.py --gate pytest_full
   (imagen ya cacheada im-arkPf8idKZHRNIECaj25t7, lanzamiento <2 min).
3. Con pytest_full verde: cerrar G0/G1 y arrancar G2 de la V3.

## Datos técnicos útiles
- Nous SIN saldo para modelos de pago (404 insufficient_credits): usar
  modelos :free vía proxy OAuth de Hermes (127.0.0.1:8645, bearer 'local',
  hermes proxy start --provider nous).
- Modelo free validado para banco: upstage/solar-mini4:free (reasoning none).
- CRIBA suite local: .venv/Scripts/python.exe -m pytest tests/ -q (8-20 min,
  NO usar salvo necesidad; usar Modal).
- mypy local: .venv/Scripts/python.exe -m mypy src/ (167 archivos, limpio).

## SHAs
- main/defd0fd (no tocar).
- rama aislada 72a2155 (handoff anterior) — HEAD de trabajo actual e735f10
  (docs: HANDOFF checkpoint). Ambos sin merge a main.
- Pendiente de commit: fix types-PyYAML en .autoregen/cloud/modal_runner.py
  + actualización de este HANDOFF (mypy_scoped PASS).
- commits sesión: 57f0ae7 (F1) -> 4e47ea7 (G1) -> 72a2155 (Modal) -> e735f10 (handoff).
