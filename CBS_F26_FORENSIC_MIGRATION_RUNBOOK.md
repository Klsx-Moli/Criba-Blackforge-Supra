# CBS F26 — Protocolo forense y compatibilidad del journal

**Estado:** IMPLEMENTED / EVIDENCE_PENDING. Sin reparación automática,
truncado, reenvío POST, esquema downcast ni promociones de UNKNOWN.

## Fuente real

La fuente contiene dossier_batches.jsonl y dossiers.jsonl en el directorio
que utiliza realmente Shadow. Si CRIBASHADOW_HOME está configurada, se usa su
subcarpeta dossiers; de lo contrario LOCALAPPDATA/CRIBA-Blackforge/dossiers
(con el fallback descrito por supra_dossier._dossiers_dir).

El lector normal de dossiers tolera filas JSONL corruptas. El inspector F26
NO las ignora. Trabaja bajo el lock existente; si no existe, puede crearse
el sidecar .dossiers.jsonl.lock. No se modifica ninguno de los dos JSONL.
No borrar nunca ese sidecar, porque divide la coordinación entre procesos.

Los respaldos guardan contenido potencialmente sensible sin cifrado nuevo:
no subirlos al repositorio, no publicarlos y conservarlos en carpeta privada.

## Comandos de PowerShell, tras detener Shadow y demás workers

Sustituir F26_HEAD_VERIFICADO por el SHA exacto del checkpoint final. Ejecutar
en un worktree NUEVO, separado del checkout local protegido.

    git status --short
    git fetch origin campaign/cbs-final-32-40
    git worktree add --detach "C:\ASTRA_WORK\cbs-final-review-26" F26_HEAD_VERIFICADO
    cd "C:\ASTRA_WORK\cbs-final-review-26\criba-blackforge"

    if ($env:CRIBASHADOW_HOME) { $sourceDir = Join-Path $env:CRIBASHADOW_HOME "dossiers" } else { $sourceDir = Join-Path $env:LOCALAPPDATA "CRIBA-Blackforge\dossiers" }
    if (-not (Test-Path -LiteralPath $sourceDir -PathType Container)) { throw "Journal inexistente; no crear uno nuevo." }

    uv run --locked python -m criba.dossier_batch_forensics --source "$sourceDir" --inspect

    $backupParent = "C:\ASTRA_WORK\backup"
    if (-not (Test-Path -LiteralPath $backupParent -PathType Container)) { throw "Crear primero carpeta externa de backup privado." }
    $backup = Join-Path $backupParent ("cbs-forensic-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
    if (Test-Path -LiteralPath $backup) { throw "Backup ya existente: no sobrescribir." }

    uv run --locked python -m criba.dossier_batch_forensics --source "$sourceDir" --snapshot-out "$backup"
    uv run --locked python -m criba.dossier_batch_forensics --verify-snapshot "$backup"

El snapshot copia los dos JSONL byte a byte fuera de la fuente. Es create-only:
no sobreescribe archivos. El manifiesto SHA256 se escribe y sincroniza al
FINAL. Si hay corte previo, el directorio queda incompleto y NO es aceptable.

Un snapshot de fuente corrupta puede existir aunque el comando devuelva
exit 2; la salida no constituye aprobación de la fuente. Verificar con
exit 0 significa únicamente RAW_BYTES_MATCH_MANIFEST_ONLY, nunca
autenticidad independiente, entrega HTTP, ejecución o éxito científico.

## Compatibilidad entre versiones / downgrade

El esquema externo sigue siendo criba-dossier-batch/1, pero las versiones
antiguas no conocen todos los tipos de evento. NO basta comparar schema.

- requires_dispatch_event_reader=true: hay REMOTE_DISPATCH_STARTED.
- requires_partial_event_reader=true: hay REMOTE_PARTIAL_READBACK_OBSERVED;
  un lector anterior a F25 no debe abrir el journal productivo.
- UNSUPPORTED_EVENT_VERSION o UNSUPPORTED_JOURNAL_SCHEMA: STOP.
- JOURNAL_PARSE_INVALID, JOURNAL_REPLAY_INVALID y
  JOURNAL_UNTERMINATED_TAIL: STOP; no salvar solo el prefijo aparentemente sano.
- DOSSIER_HISTORY_PARSE_INVALID, DOSSIER_HISTORY_MISMATCH o
  DOSSIER_HISTORY_MISSING: STOP; no ocultar filas dañadas.
- JOURNAL_MISSING o INSPECTION_SIZE_LIMIT: no interpretar como cero lotes/PASS.

Para estudiar una versión antigua, usar worktree aislado y una COPIA de los
datos, nunca el directorio original con otra versión de la GUI.

## Recuperación manual controlada

1. Detener cualquier worker o consola que utilice la misma fuente.
2. Inspeccionar y crear snapshot explícito incluso con estado de error.
3. Verificar la copia desde otro proceso y conservar el manifiesto.
4. Conservar fuente, copia, SHA de código, bytes originales y error reportado.
5. Investigar solo en una copia aislada. No truncar JSONL, borrar locks,
   reescribir el esquema, saltar eventos, forzar POST o ejecutar reset/clean.
6. Una futura restauración requiere autorización explícita, regresión
   reproducible y plan reversible. F26 no implementa restauración automática.

HASH != TRUTH. UNKNOWN != NOT_ATTEMPTED. READABLE_LOCAL != POST_ENTREGADO.
PLANIFICACION_REGISTRADA != EJECUCION != VALIDACION_CIENTIFICA.

## Gates abiertos

F26 queda EVIDENCE_PENDING hasta ejecutar pytest completo, Python 3.10 en
Windows, Ruff, mypy, integración Shadow y CI. G0 NO-GO y P0 semántico OPEN.
No merge a main, downgrade productivo ni migración sobre journal original.
