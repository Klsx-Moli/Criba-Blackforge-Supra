# HANDOFF — checkpoint para reanudar (reconciliado 2026-10-14)

Fecha: 2026-10-14
Rama aislada: hermes/cloud-provider-layer-20261013
HEAD documento: ver seccion SHAs (commit documental final registrado al cierre).
Remoto: Klsx-Moli/Criba-Blackforge-Supra
Writer: Hermes (unico). Worktree: C:\ASTRA_WORK\Criba-Blackforge-Supra

## Contexto
TAREA_LARGA_UNIFICADA_CRIBA_SUPRA_V3. Prioridad explicita de moli: verificacion
pesada a Modal, NO cargar GPU local. Rama aislada; NUNCA merge/push a main sin
OK explicito de moli. BLACKFORGE HARD_PAUSE (no inicializar, sin key, sus tests
no bloquean el producto activo).

## Regla de gates (vigente, decision operador 2026-10-14)
- gate_windows_full: AUTORITATIVO. Suite local Windows con el venv del proyecto.
  Es el unico gate que cierra milestones de CRIBA/SUPRA.
- gate_modal_mypy: gate de TIPOS. Resultado ligado al SHA verificado (abajo).
- gate_modal_pytest_linux: EXPERIMENTAL. NO sustituye al gate Windows.
  NO presentar pytest_full verde en Modal como requisito suficiente para G2.
- gate_modal_smoke: POR CREAR (no lanzado por este mandato).

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
- gate_modal_mypy: PASS sobre el codigo de la rama aislada tal como estaba al
  ejecutarse. mypy "Success: no issues found in 167 source files".
  Log: C:\ASTRA_WORK\modal_mypy_scoped_2.log. App: ap-A4bYls5AS7E4qRvzzdhkC5.
  Imagen: im-arkPf8idKZHRNIECaj25t7. NO re-verificado contra SHA posterior.
- gate_modal_pytest_linux: EXPERIMENTAL, NO verde. 25 failed / 2037 passed /
  8 skipped, seed 1. 25 fallos de ENTORNO Linux con mensaje real del JUnit XML
  (10 uvicorn ausente, 10 venv Windows Exec format errno 8, 3 criba no
  instalado, 2 git ausente, 1 mutmut API, 2 cp1252, 1 race barrier a revisar).
  Segfault Qt rc=-11 con seed 2/12345 y con -e install: rc VERIFIED, causa NO
  aislada. Detalle: docs/audit/MODAL_LINUX_GATE_REPORT.{json,md}.
  /nonexistent RETIRADO del runner (prohibido por operador).

## pytest_full en Modal — decision operador 2026-10-14 (NO verde)
25 failed / 2037 passed / 8 skipped, seed 1. Los 25 fallos son de ENTORNO
Linux con mensaje real del JUnit XML: 10 uvicorn ausente, 10 venv Windows
(Exec format error), 3 criba no instalado, 2 git ausente, 1 mutmut API,
2 encoding cp1252, 1 race barrier a revisar. NO es gate verde.
Segfault Qt (rc=-11) con seed 2/12345 y con -e install: VERIFIED el rc,
CAUSA_NO_AISLADA. /nonexistent RETIRADO del runner (prohibido por operador).
Detalle completo: docs/audit/MODAL_LINUX_GATE_REPORT.{json,md}.

Gates separados (decision operador):
  gate_windows_full   AUTORITATIVO — suite local Windows con venv proyecto.
  gate_modal_mypy     PASS.
  gate_modal_pytest_linux  EXPERIMENTAL — 25 fallos entorno documentados.
  gate_modal_smoke    POR CREAR — imports/Qt offscreen/arranque CRIBA-SUPRA.
BLACKFORGE HARD_PAUSE respetado. G2 NO avanzado hasta cerrar esta decision.

## Reconciliacion de board 2026-10-14 (shadow_ui)
Premisa "shadow_ui/ NO existe en el monorepo" era FALSA contra origin/main.
- t_1a76292e SHADOW-00: CERRADA como ALREADY-DONE (unidad de DECISION cumplida;
  migracion ya ejecutada). run #38. Alcance pendiente (arranque/wiring/packaging/
  E2E) NO propagado: vive en K3 / SHADOW-MIGRATE-01 / M2 / M3.
- t_2a1adba0 K3: REESCRITA a "Readiness funcional de la UI existente".
- t_6143a46a SHADOW-MIGRATE-01: REESCRITA a "verificacion de integracion
  canonica". Ambas quedan blocked; padres NO alterados.
Evidencia base: origin/main=defd0fd. shadow_ui/ presente (30 rutas). Commits
26e166c/0445e87/14ec9d2 en main. criba_shadow_main.py y CribaShadow.spec estan
en la RAIZ criba-blackforge/ (no en shadow_ui/). Ruta historica Music/INNOVATIONS
ya no existe en disco.
Detalle: C:\ASTRA_WORK\cierre_shadow00_20261014.txt

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
Tras reconciliar board+handoff (hecho), el siguiente trabajo es el primer
criterio funcional NO demostrado de K3: arranque visible de Shadow en Windows
(entrypoint shadow_ui/entrypoint.py o launcher criba_shadow_main.py) ejecutado
desde el venv del proyecto, comprobando que NO exige BLACKFORGE.
NO dar por verde M2/M3 sin releer su evidencia y SHA.

## Datos técnicos útiles
- Nous SIN saldo para modelos de pago (404 insufficient_credits): usar
  modelos :free vía proxy OAuth de Hermes (127.0.0.1:8645, bearer 'local',
  hermes proxy start --provider nous).
- Modelo free validado para banco: upstage/solar-mini4:free (reasoning none).
- CRIBA suite local: .venv/Scripts/python.exe -m pytest tests/ -q (8-20 min,
  NO usar salvo necesidad; usar Modal).
- mypy local: .venv/Scripts/python.exe -m mypy src/ (167 archivos, limpio).

## SHAs
- origin/main = defd0fd9955c5aaf3f7ff8b23fdf016639ed062b (NO tocar; base de toda
  la evidencia de board de esta sesion).
- rama aislada hermes/cloud-provider-layer-20261013: HEAD publicado al cierre de
  este handoff = <COMMIT_DOCUMENTAL_FINAL> (git rev-parse tras el commit de esta
  reconciliacion). Commits de la sesion sobre la rama: 106b546 (mypy PASS) ->
  eb24690 (gate Linux NO verde + runner) -> 5d1cabd (verificacion board shadow_ui)
  -> <COMMIT_DOCUMENTAL_FINAL> (cierre SHADOW-00 + reescritura K3/MIGRATE + este
  handoff reconciliado).
- El SHA de CODIGO verificado por gate_modal_mypy es el de la rama aislada en el
  momento de ejecucion (pre-eb24690); mypy NO se ha re-ejecutado contra HEAD actual.
