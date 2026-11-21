MODAL_LINUX_GATE_REPORT — decision operador 2026-10-14

1. GATES (separados, segun decision operador)

   gate_windows_full    AUTORITATIVO — suite local Windows con el venv del
                        proyecto. Es el gate que manda para CRIBA/SUPRA.
   gate_modal_mypy      PASS — mypy_scoped en Modal, 167 source files limpios.
   gate_modal_pytest_linux  EXPERIMENTAL — 25 failed / 2037 passed / 8 skipped
                        con seed fija 1. NO es gate verde.
   gate_modal_smoke     POR CREAR — imports, Qt offscreen, arranque CRIBA y
                        SUPRA en Linux, minimo.

2. PYTEST_FULL EN MODAL: NO VERDE — por decision, no por descuido

   Pasan en Windows es evidencia de clasificacion, no convierte la suite Linux
   en verde. Los 25 fallos tienen mensaje REAL del JUnit XML (no hipotesis):
   VERIFIED_OBSERVED = 24, INFERRED = 1 (lottery hash_seed).

   Resumen por causa:
     10  ENTORNO-UVICORN-AUSENTE     ModuleNotFoundError: uvicorn (imagen)
      3  ENTORNO-CRIBA-NO-INSTALADO  ModuleNotFoundError: criba (subprocesos)
     10  ENTORNO-VENV-WINDOWS        OSError Errno 8 Exec format error
                                      supra/.venv/Scripts/python.exe (Windows
                                      dentro de contenedor Linux)
      2  ENTORNO-GIT-AUSENTE         FileNotFoundError: git (debian_slim)
      1  ENTORNO-MUTMUT-API          Config.reset no existe en mutmut 3.8
      2  ENTORNO-ENCODING            cp1252 no existe en Linux (lottery CLI)
      1  REVISAR                     race barrier anti_goodhart (UNKNOWN_REVISAR)
     ---
     25  TOTAL

   Detalle test por test: MODAL_LINUX_GATE_REPORT.json (machine-readable).

3. SEGFAULT Qt (rc=-11) — hallazgo, no excusa

   QT_QPA_PLATFORM=offscreen NO lo elimina: reaparece con seed 2/12345 y,
   cuando el paquete queda instalado (-e), tambien con seed 1. Estado:
   VERIFIED_OBSERVED el rc, CAUSA_NO_AISLADA. Hiptotesis sin verificar: con
   criba importable, Qt se carga de verdad. Proximo paso: pytest_file por
   archivo GUI hasta el test exacto; medir QT_QPA_PLATFORM=minimal o xvfb.

   Decisión: NO se marca ninguna causa como verificada sin reproduccion
   aislada. El segfault queda ABIERTO.

4. VENV DE SUPRA EN LINUX — decision

   Prohibido /nonexistent como solucion permanente (decision operador 4d):
   RETIRADO del runner. El -e install de criba se hace en runtime porque
   add_local_dir es la ultima operacion de la imagen (en build-time
   /workspace no existe; un intento en build fallo con "Distribution not
   found"). Falta crear el venv Linux real de SUPRA o skip motivado en los
   tests E2E — es trabajo pendiente, no hecho.

5. FIXES EN EL RUNNER (commit en rama aislada, sin merge a main)

   tipos-PyYAML, libs Qt, git, deps Python (uvicorn, PyYAML, hypothesis,
   mutmut, jsonschema, pytest-qt/timeout/cov), offscreen, --seed, JUnit XML
   -> failures[], pip install -e en runtime. main=defd0fd intacto.

6. BLACKFORGE

   HARD_PAUSE respetado: no inicializado, sin key fisica, sus tests (sentinel
   BLACKFORGE) no bloquean el producto activo.

7. G2

   NO avanzado. Pendiente de esta decision y del runner estar commiteados y
   documentados — que es lo que hace este informe.
