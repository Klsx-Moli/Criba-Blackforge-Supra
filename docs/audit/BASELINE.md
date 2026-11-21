# F0 — LÍNEA BASE

Fecha: 2026-10-13 (UTC)
Operador: Hermes (autoridad amplia; solo lectura en F0)
Directorio: C:\ASTRA_WORK

## 1. Repos localizados (VERIFIED_BY_EXECUTION — find .git, git remote)

La tarea menciona "dos repos separados". REALIDAD MEDIDA:

- Repo canónico: C:\ASTRA_WORK\Criba-Blackforge-Supra (monorepo criba-blackforge/ + supra/)
  - remote origin: https://github.com/Klsx-Moli/Criba-Blackforge-Supra.git
  - HEAD (worktree principal): 09ce339 rama hermes/cloud-provider-layer-20261013
  - Worktrees asociados (git worktree list):
    - Criba-Blackforge-Supra-main-baseline  b845aeb [hermes/local-snapshot-20261009-main-baseline]
    - iso-deep-execution-20261005           2f534f9 [hermes/deep-execution-20261005]
    - iso-dossier                           cfe60fa [hermes/local-snapshot-20261009-dossier]
    - iso-main-4332ff1                      ca5bb59 [hermes/mono03-supra-license]
    - iso-pr8-safety                        65a58e5 [astra/blackforge-safety/dfca79-auth-state-failclosed]
    - iso-pr9-persistence                   5e9ee71 [hermes/local-snapshot-20261009-pr9-persistence]
    - iso-valida-17                         9a8af79 (detached HEAD)
  - git status: limpio (sin cambios sin commitear en el worktree principal)
  - stashes: ninguno

- eval-cbs-20261005-0030: .git independiente PERO mismo remote (Klsx-Moli/Criba-Blackforge-Supra).
  HEAD 62ff6f8. No es un repo remoto distinto: es un clon/snapshot local del mismo upstream.

- reconcile-15bc237/criba-blackforge: .git independiente con origin = path local
  (C:/ASTRA_WORK/Criba-Blackforge-Supra). HEAD 9a8af79. Snapshot local, no remoto.

CONCLUSIÓN F0.1: NO existen dos repos remotos separados. Solo hay un remoto real
(Klsx-Moli/Criba-Blackforge-Supra) más snapshots/worktrees locales. La premisa
"dos repos separados" de la tarea es INCORRECTA (VERIFIED_BY_EXECUTION).

## 2. Remoto klssxx/Criba-Blackforge (VERIFIED_BY_EXECUTION)

git ls-remote https://github.com/klssxx/Criba-Blackforge.git -> "Repository not found".
NO EXISTE. El remoto real es Klsx-Moli/Criba-Blackforge-Supra.
Discrepancia de la tarea anotada; no se crea ni se asume ese remoto.

## 3. Estado remoto vs local (VERIFIED_BY_EXECUTION)

- origin/main remoto HEAD: defd0fd (merge PR#22, 2026-10-13T20:49:46Z)
- local main == origin/main (fast-forward limpio tras el merge)
- rama de trabajo: hermes/cloud-provider-layer-20261013, HEAD 09ce339 (pusheada)
- CI (gh run list, Klsx-Moli/Criba-Blackforge-Supra):
  - último run en main: success (Monorepo CI, 3m42s, 2026-10-13T20:49:49Z)
  - runs previos en audit/fase0-fase1: success x3, 1 failure (ya superado)

## 4. Discrepancia versión paquete 0.3.0 vs runtime 0.1.0

- criba-blackforge/pyproject.toml: version = "0.3.0" (VERIFIED_BY_EXECUTION)
- criba runtime instalado (criba-blackforge/.venv): importlib.metadata version("criba") = 0.3.0
- supra pyproject: 1.0.0; supra runtime: 1.0.0 (coinciden)
- src/criba/version.py deriva de importlib.metadata (o pyproject en fallback): no hay 0.1.0 hardcodeado.

CONCLUSIÓN F0.2: la discrepancia 0.3.0 vs 0.1.0 descrita en la tarea NO se reproduce
en el estado actual (VERIFIED_BY_EXECUTION: paquete y runtime ambos 0.3.0). Si el
0.1.0 venía de un ejecutable/dist antiguo, no está en el árbol actual. Pendiente
confirmar contra el EXE en dist/ (Fase F1), no asumir.

## 5. Identidad común suite/build SHA

- No hay mecanismo de "suite_sha / build_sha" común en el árbol
  (grep build_sha/suite_sha/git_sha: sin resultados). STATICALLY_INSPECTED.
- dist/ y build/ existen (CribaShadow.exe presente). La identidad del build vs
  el commit queda por verificar en F1.

## 6. Registro histórico CRIBA/MiMo (Fase 1 terminada, 319 tests PASS, mypy strict limpio)

RE-VERIFICADO POR EJECUCIÓN, no asumido:
- Suite SUPRA: 319 passed (ejecutada en esta sesión de trabajo).
- Suite CRIBA: pendiente de re-ejecución en F1 (la tarea exige no asumir el histórico).
- mypy strict: pendiente de re-verificación en F1/F6.

## 7. Estados de verificación (NO alterados)

- STANDARD=DISABLED, G3=NOT_VERIFIED, D3/D4/D6 sin resolver (governance/ANTI_GOODHART_STATUS.yaml).
- BLACKFORGE: INERTE.
- CRIBA = descubrimiento, SUPRA = ejecutor, SUPRA Google-native (Vertex/ADK/Cloud Run) intacto.

## 8. Cambios locales sin commitear

Ninguno en el worktree principal (git status limpio).

## SIGUIENTE PUNTO EXACTO (F1)

1. Rama de respaldo de cambios locales (git tag o branch) — SOLO si aparecen
   cambios locales; ahora no hay.
2. Verificar versión común PC/GitHub/EXE/CI: leer versión del EXE dist/CribaShadow
   y contrastar con pyproject 0.3.0 y con origin/main.
3. Re-ejecutar suite CRIBA + mypy strict para re-verificar el registro histórico
   (no asumir los 319 ni el mypy limpio de CRIBA).
4. Puerta F1: mismo SHA/versión en las cuatro ubicaciones.

## SHAs de referencia (VERIFIED_BY_EXECUTION)

- Criba-Blackforge-Supra HEAD: 09ce33907221b32ac8856009fc2e78de8bbb2d95
- origin/main: defd0fd9955c5aaf3f7ff8b23fdf016639ed062b
- rama trabajo: hermes/cloud-provider-layer-20261013 @ 09ce339
