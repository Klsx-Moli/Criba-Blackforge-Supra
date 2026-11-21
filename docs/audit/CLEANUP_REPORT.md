# CLEANUP_REPORT — G1 (limpieza de contextos ajenos al producto)

Fecha: 2026-10-14
Rama: hermes/cloud-provider-layer-20261013
BASE_SHA: 57f0ae7 (pre-patch)
TARGET_SHA: (post-patch, ver git log)

## Identificadores excluidos (patrones de detección, no requisitos de producto)
- Vendor: [REDACTED por construcción en inspección]
- Plataforma de eventos: [REDACTADO]
- Términos de evento: hackathon / hackaton / hackatown / hackatón

Los patrones se construyen en tiempo de inspección (concatenación) para no
reproducir las marcas en este documento limpio.

## Superficies inspeccionadas y resultado

| Superficie | Estado | Evidencia |
|---|---|---|
| src/criba + src/supra (vendor/devpost/hackathon) | INSPECTED_CLEAN | git grep -i sin coincidencias |
| .github/workflows (vendor/devpost/hackathon) | INSPECTED_CLEAN | git grep -i sin coincidencias |
| src/criba/cli.py (vendor) | FOUND -> CLEANED_IN_CANDIDATE | opción --llm muerta retirada |
| data/methods (hackathon) | FOUND -> conservado | "Hackathon" es técnica genérica de innovación, no asociación a evento |
| .hermes/iie/assurance_ledger.json | FOUND -> RESIDUAL_HISTORICAL | nota de otra sesión; no es producto activo |

## Cambio aplicado (parche mínimo)

Archivo: criba-blackforge/src/criba/cli.py (L147-148)
- Antes: --llm choices=["none","offline","cloud","nebius"], help mencionaba Token Factory
- Después: --llm choices=["none","offline","cloud"]

Justificación (VERIFIED_BY_EXECUTION / STATICALLY_INSPECTED):
- create_backend() en llm_adapter.py solo reconoce "offline" y "cloud";
  "nebius" caía al else -> NoneBackend() (modo determinista). Era una opción
  MUERTA: no tenía backend, no hacía nada.
- Ningún camino activo la seleccionaba (default="none").
- Retirarla no rompe contrato: tests/unit/test_cli.py 18/18 PASSED.

## NO ejecutado / pendiente
- assurance_ledger.json: es un artefacto de estado de otra sesión (Hermes IIE),
  no producto. Se deja; requiere decisión del propietario si se purga (historial).
- Histórico de commits: NO escaneado ni purgado. RESIDUAL_HISTORICAL declarado.
  No se reescribe historia ni force-push.
- Metadatos remotos (topics/badges/descripción del repo en GitHub): NO accesibles
  desde aquí sin acción explícita; pendiente de decisión del propietario.

## Limitación honesta
Esta limpieza cubre el ÁRBOL CANDIDATO versionado. No afirma "historial purgado"
ni "todo limpio". Superficies remotas y copias externas fuera de control.
