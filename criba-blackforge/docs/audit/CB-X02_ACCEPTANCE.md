CB-X02 — GATE DE RELEASE Y ACEPTACIÓN FINAL (veredicto honesto)
===============================================================

SHA inicial de la campaña (main): 6b3d02b9639466e0dcfd594a66b0744bb46abe57
SHA final (rama de trabajo):      4ac6ae5 (origin/cb01-bank-provenance-work)
Commits de la campaña:            19 por delante de main
Fecha:                            2026-10-11 (UTC)
Suite completa criba-blackforge:  2053 passed, 3 skipped
Mypy:                             baseline enforced (0 nuevos)
Ruff:                             limpio en todos los ficheros nuevos

VEREDICTO GLOBAL: GO_WITH_LIMITS
No es PASS GLOBAL: hay áreas con gates abiertos que requieren autorización
explícita o entorno no disponible (proveedor real, BLACKFORGE, EXE Windows).
Declarar PASS sería un éxito falso; el megaprompt lo prohíbe.


VEREDICTO POR ÁREA
------------------

1. INTEGRACIÓN — GO
   - CB-03 journey E2E sin modelo: 31 boundaries, PRIMER_BORDE_PROBLEMATICO=ninguno
     (Shadow→CRIBA→dossier→SUPRA→disco→GET/LIST→reinicio real→recuperación).
   - CB-I01 contrato intérprete↔dossier↔SUPRA: 9 tests (11 casos + invariantes).
   - CB-I06 aislamiento BLACKFORGE ante fallo: 4 tests. BLACKFORGE inerte.

2. FUNCIONAL — GO
   - CB-02 diagnóstico estructurado: 21 tests (17 códigos canónicos).
   - CB-I02 cancelación cooperativa: 7 tests. Sin deadlock, sin fabricar.
   - CB-L01 generación determinista: 9 tests (>=80 ideas, identidades únicas).

3. PERSISTENCIA — GO
   - CB-I03 roundtrip SUPRA en disco: 15 tests (ausente≠corrupto≠vacío, rollback,
     lineage, LIST coherente).
   - CB-R01 recuperación local: 11 tests. CB-L03 carga 100 proyectos: 8 tests.
   - CB-R02 backend caído/retry: 7 tests. CB-09 cubierto sin duplicar.

4. DIAGNÓSTICO/UX — GO (con límite de UI real no verificada)
   - CB-02 classify() con next_action y procedencia saneada.
   - LÍMITE: no se verificó render visual en Windows (CB-H01 sin hacer).

5. SEGURIDAD — GO (con gate BLACKFORGE abierto)
   - CB-S01 anti-fugas: 6 tests (escáner sobre verification/ real).
   - CB-S03 entradas hostiles: 25 tests (inyección, path traversal, goodhart).
   - CB-S04 red/puertos: 11 tests (503≠suspendido, loopback, credenciales).
   - ABIERTO: CB-S02 autorización BLACKFORGE — prohibido sin autorización de moli.

6. EXE/DISTRIBUCIÓN — NO_GO (no ejecutado, requiere build+smoke Windows)
   - CB-D01/D02/X01 no ejecutados: requieren PyInstaller + smoke real en Windows.
   - main YA tiene el workflow shadow-windows-build-smoke.yml, pero no se corrió
     un build+smoke en esta campaña.

7. VALOR CIENTÍFICO — GO (banco diagnosticado, no calibrado)
   - CB-04 causa raíz del banco: problema de prompt/contrato (mecanismo causal +
     restricciones), NO del validador ni la capacidad. Recomendación documentada,
     no ejecutada (cambiar el prompt es decisión de moli).


GATES OBLIGATORIOS — ESTADO
---------------------------

GATE-BASE ............ GREEN (CB-00, CB-01)
GATE-JOURNEY ......... GREEN (CB-03)
GATE-CONTRACT ........ GREEN (CB-I01)
GATE-UI .............. GREEN (CB-02, CB-I02) — UI real no verificada
GATE-PERSISTENCE ..... GREEN (CB-I03, CB-R01, CB-L03)
GATE-LOCAL ........... N/A (intérprete local gate existente; no recalibrado)
GATE-PROVIDER ........ BLOQUEADO (CB-I04: requiere proveedor autorizado)
GATE-SECURITY ........ PARCIAL (CB-S01, CB-S03 GREEN; CB-S02 BLACKFORGE abierto)
GATE-NETWORK ......... GREEN (CB-S04)
GATE-STRESS-UI ....... GREEN (CB-L01) / PARCIAL (CB-L04 no ejecutado)
GATE-STRESS-INTERP ... GREEN (CB-L02; CB-L05 solapado con CB-S04/CB-R02)
GATE-STRESS-STORAGE .. GREEN (CB-L03)
GATE-STRESS-RESOURCES . BLOQUEADO (CB-L06: forzar OOM/disco no autorizado)
GATE-CAPACITY ........ GREEN (CB-L07 documento honesto de límites)
GATE-PACKAGE ......... NO_GO (requiere build PyInstaller + smoke)
GATE-DEPLOY .......... NO_GO (depende de package)
GATE-EXE ............. NO_GO (requiere Windows real)
GATE-RELEASE ......... este informe
GATE-PUBLISH ......... BLOQUEADO (requiere autorización explícita de moli)
GATE-HUMAN ........... PENDIENTE (CB-H01: sólo el propietario)


TARJETAS APARTADAS (requieren autorización/entorno — NO son fallos)
-------------------------------------------------------------------

- CB-I04 proveedor OpenAI-compatible real: necesita endpoint/modelo autorizados.
- CB-S02, CB-11 autorización BLACKFORGE: prohibido tocar sin moli.
- CB-D05 publicación: requiere autorización explícita.
- CB-H01 aceptación humana: sólo el propietario puede confirmar.
- CB-X01/CB-D0x EXE Windows: requieren build+smoke real en Windows.


RIESGOS Y LIMITACIONES DECLARADAS
---------------------------------

- No se verificó la UI real en Windows ni el EXE empaquetado.
- No se calibró el prompt del intérprete (decisión de moli tras CB-04).
- BLACKFORGE permanece inerte; su autorización no se ha tocado.
- Los PRs abiertos (#8/#10-#15) están superseded o son BLACKFORGE; no mergeados.
- Cifras de capacidad son single-proceso en el equipo del propietario, con
  backend simulado donde no hay proveedor real (ver CB-L07).


TRABAJO PRESERVADO
------------------

- 19 commits pusheados a origin/cb01-bank-provenance-work (respaldo remoto).
- Ramas cb02/cb03/cb04 locales: su contenido ya está integrado aquí.
- Todos los PRs abiertos siguen intactos en el remoto (nada borrado).
