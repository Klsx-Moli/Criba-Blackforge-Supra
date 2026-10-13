CB-X03 — FIX ENDPOINT CON CREDENCIALES EMBEBIDAS
Fecha: 2026-10-13 (Europe/Madrid, UTC+02:00)
SHA antes: e52ab859b5172b234a8a272c0fb03d2365c89951 (main)
SHA después: e05e24f (main, pusheado)

PROBLEMA (reproducido)
- CI run 38161151867 (push a main e52ab85) falló:
  tests/security/test_cb_s04_local_network_boundaries.py::test_url_con_credenciales_rechazada
  assert ('loopback' in 'no se pudo contactar el interprete: connecterror' or ...)
- Reproducido en local: 1 failed, 10 passed en 3.41s.
- Causa raíz: OpenAICompatibleInterpreter.operativo() no inspeccionaba la URL
  antes de conectar. httpx seguía http://user:pass@127.0.0.1:8645/v1 y agotaba
  el timeout, por lo que el motivo declarado era un error de transporte genérico
  (ConnectError/ConnectTimeout) en lugar de un rechazo explícito por credenciales.

FIX (mínimo, 5 líneas)
- En operativo(), antes del try/except: urlsplit(self.base); si username o
  password, devolver (False, "endpoint rechazado: credenciales embebidas en la
  URL"). Sin conectar, sin tocar el resto de la ruta.
- Archivo: criba-blackforge/src/criba/interprete/openai_compatible.py

VERIFICACIÓN (VERIFIED_BY_EXECUTION, esta sesión)
- tests/security/test_cb_s04_local_network_boundaries.py: 11 passed (1.08s)
- tests/unit/test_interprete_puerto.py + tests/integration/test_e2e_interprete_supra.py
  + tests/integration/test_interprete_pipeline_determinismo.py
  + tests/unit/test_schema_validator_alignment.py: 56 passed, 3 skipped (23.86s)
- Suite completa CRIBA local: 2057 passed, 3 skipped, 0 failed (496.15s)
- SUPRA: 299 passed (75.92s)
- verification/journey_e2e_no_model.py: PRIMER_BORDE_PROBLEMATICO=ninguno
  (RESTART_PROCESS source=PERSISTED_STATE, SHADOW_RECOVERY OK)
- CI run 38338297629 (push e05e24f): success — CRIBA/BLACKFORGE
  "2057 passed, 3 skipped"; SUPRA success; monorepo-result success

OTROS DOS FALLOS REGISTRADOS EN lastfailed DE CI
- tests/unit/test_schema_validator_alignment.py::test_schema_no_usa_ref_ni_defs
- tests/stress/test_cb_l02_interpreter_load_simulated.py::test_invalido_no_se_promociona
- No reproducidos en local: ambos pasan (verificado arriba junto a las suites).
  Hipótesis: flakiness de entorno CI (timeout/red), NO reproducible localmente.
  NO se aplicó fix: sin fallo reproducible no hay reparación que verificar.

LIMITACIONES
- F401 preexistente (validar_propuesta sin usar) en openai_compatible.py:
  presente en HEAD antes del fix; el CI de CRIBA no ejecuta ruff. No tocado
  (fuera de scope, no requerido por el fallo).
- BLACKFORGE: inerte, no tocado.
- No se ejecutó build Windows/EXE (requiere PyInstaller real).

BLACKFORGE: INERTE (no activado, no tocado, no borrado).
