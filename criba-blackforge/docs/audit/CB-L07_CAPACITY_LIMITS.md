CB-L07 — INFORME DE CAPACIDAD Y LÍMITES (medidos, no promesas)
================================================================

SHA de la rama de trabajo: a84e1071078d55fba54ef8da9ccd99921aaaf540
Fecha de medición: 2026-10-11 (UTC)
Entorno: Windows 11, Python 3.11.15, pytest 9.1.1, uv 0.12.15
Hardware: equipo de desarrollo del propietario (KLSX). NO es hardware de servidor.


1. QUÉ SE MIDIÓ Y CÓMO
-----------------------

Los límites siguientes provienen de ejecuciones REALES de los harnesses de los
gates CB-L*, no de extrapolaciones. Cada cifra indica el volumen ejercitado y
el entorno donde se ejecutó.

- CB-L01 (generación determinista): engine.activate real, volumen >= 80-92
  ideas por query. Determinismo verificado (mismo query → mismas identidades).
  Entorno: proceso Python local, sin GPU, sin red.

- CB-L02 (intérprete con backend simulado): _default_proponer real, 50
  peticiones secuenciales con mezcla válida/abstención/schema/truncamiento.
  Entorno: in-process, backend simulado (sin proveedor real).

- CB-L03 (SUPRA/storage durable): ProjectStateManager real contra disco,
  100 proyectos creados, persistidos, listados y recuperados tras reinicio
  simulado (manager fresco). Entorno: disco local (tmp_path), SQLite/JSON.

- CB-I03 (roundtrip storage): 15 casos de integridad contra disco real.

- Suite completa criba-blackforge: 2024 passed, 3 skipped (ver §4).


2. LÍMITES MEDIDOS
------------------

- Volumen de generación: >= 80 ideas por activación, estable y determinista.
  NO se midió un techo superior (no se ejecutó 1.000+ ideas por presupuesto
  de tiempo del entorno de desarrollo).

- Proyectos SUPRA concurrentes en disco: 100 verificados sin corrupción,
  sin mezcla de payloads, recuperación íntegra tras reinicio. NO se midió
  500/1.000 (el megaprompt lo permite como escenario opcional; aquí se abortó
  por presupuesto, no por fallo).

- Peticiones de intérprete secuenciales: 50 sin fuga de estado ni
  contaminación cruzada. Con backend SIMULADO; con proveedor real el límite
  depende de cuota/latencia del proveedor, no del motor.

- Tamaño de objetivo persistido: ~1.400 caracteres recuperados íntegros
  (salvo .strip() de espacios exteriores, normalización declarada).

- Timeout de intérprete: configurable; rango válido (0, 1800] segundos.
  Fuera de rango → configuración inválida explícita.


3. LO QUE NO ESTÁ PROBADO (honestidad)
--------------------------------------

- NO se midió latencia p50/p95/p99 real con proveedor externo: no hay
  proveedor autorizado en esta campaña (CB-I04 queda BLOQUEADO por diseño).
  Las cifraciones de latencia del código (test_latency) son de presupuesto
  interno, no de proveedor real.

- NO se ejecutó carga de 500/1.000 ideas ni 500/1.000 proyectos: abortada
  por presupuesto de tiempo del entorno, no por límite del producto.

- NO se probó en hardware de servidor, multi-usuario, ni con GPU. Todas las
  mediciones son single-proceso en el equipo del propietario.

- NO se midió memoria/RAM pico ni disco bajo presión (CB-L06 no ejecutado):
  requiere forzar OOM/disco lleno, que el megaprompt desaconseja sin
  autorización explícita de forzar fallos de recursos.

- NO se verificó el EXE de Windows (CB-X01/CB-D0x): requieren build PyInstaller
  y smoke real en Windows, fuera del alcance de esta campaña de tests.


4. ESTADO DE LA SUITE (evidencia)
---------------------------------

- Suite completa criba-blackforge: 2024 passed, 3 skipped.
- Mypy: baseline enforced (scripts/check_mypy_baseline.py).
- Ruff: limpio en todos los ficheros nuevos de los gates.
- Todos los commits de gates pusheados a origin/cb01-bank-provenance-work.


5. REGLA DE ESTE INFORME
------------------------

Ninguna cifra de arriba afirma "soporta N usuarios" ni "escala": no se definió
carga multi-usuario ni hardware de servidor. Son límites de un solo proceso en
el equipo del propietario, con backend simulado donde no hay proveedor real.
Distinguir siempre: SIMULADO (backend falso) vs LOCAL (disco real) vs REAL
(proveedor externo, NO ejercitado aquí).
