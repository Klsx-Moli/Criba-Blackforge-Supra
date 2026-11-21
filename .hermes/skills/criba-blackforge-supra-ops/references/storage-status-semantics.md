# Storage status semantics (SUPRA)

Este documento codifica el significado real de los estados de almacenamiento
que expone SUPRA, medidos contra el servidor real. Sirve para escribir tests
que documenten la garantía verdadera y no una suposición.

## status_source

| Valor | Cuándo aparece | Qué garantiza (y lo que NO) |
|---|---|---|
| `PERSISTED_STATE` | GET directo del proyecto después de un restart limpio (el proceso SUPRA fue terminado y relanzado; la caché del proceso anterior está vacía). | El estado proviene del artefacto en disco. **Garantía real de durabilidad.** |
| `IN_PROCESS_MEMORY_CACHE` | GET inmediatamente después de un LIST (el LIST puebla la caché del servidor). | El estado vino de la caché del proceso actual, **no** de una lectura fresca del disco. NO es garantía de durabilidad por sí solo. |

### Pitfall clave
`IN_PROCESS_MEMORY_CACHE` aparece tanto después de un LIST (caché poblada) como
después de crear el proyecto en el proceso actual. No usarlo como evidencia de
durabilidad. La garantía real viene de `persisted_artifact_status`.

## persisted_artifact_status

| Valor | Garantía |
|---|---|
| `VERIFIED_FROM_ARTIFACT` | El servidor leyó el artefacto de disco y lo verificó como parseable/correcto. **Esto es lo que acredita durabilidad**, incluso si `status_source` es `IN_PROCESS_MEMORY_CACHE` (porque LIST lo pobló). |
| `MATCHES_CACHE` | Tras un LIST, el servidor compró que el artefacto en disco coincide con lo que tiene en caché. **Acredita que el artefacto existe y es legible.** |
| `MISSING` | El artefacto no está en disco. |
| `UNVERIFIABLE` | El artefacto existe pero está corrupto/no parseable (`error_kind` detalla). |

## Regla de oro para tests
Un test que demuestre "recuperación durable" debe comprobar
`persisted_artifact_status IN (VERIFIED_FROM_ARTIFACT, MATCHES_CACHE)`,
nunca sólo `status_source == PERSISTED_STATE`.

## Contrato de idempotencia / conflicto
|- Same project_id + same payload → `idempotent_replay: true`, no duplica, preserva `created_at`.
|- Same project_id + payload diferente → **409 Conflict**, no sobrescribe, preserva el artefacto original.

## Recovery del lado Shadow: restart → readback (K13 / K15)

Un corte vertical verdadero requiere verificar **ambos** lados de la persistencia:
el del servidor SUPRA (GET tras restart del proceso SUPRA) **y** el del cliente
Shadow (recovery de dossier tras restart de Shadow).

### Distinción crítica: recovery del server vs recovery del cliente

| Tipo | Qué restart | Qué artéfacto se readbackea | Cómo verificar |
|---|---|---|---|
| **Server-side recovery** | Proceso SUPRA detenido y relanzado | Artefacto en disco de SUPRA (`SUPRA_STORAGE_DIR`) | GET `/projects/{pid}` → `status_source == PERSISTED_STATE` |
| **Client-side recovery** | Proceso Shadow detenido y relanzado | Dossier local de Shadow (receipt en `CRIBASHADOW_HOME`) | `_load_latest_supra()` → hash del dossier match con el pre-restart |

### Pitfall clave
Ver el server-side recovery passa (`PERSISTED_STATE` tras restart del proceso
SUPRA) **NO** acredita el client-side recovery. El dossier puede existir en disco
de SUPRA pero no estar disponible para Shadow tras su restart, si
`_load_latest_supra()` no recupera el receipt local o el hash no coincide.

### Gating de readback tras restart de Shadow
Un test E2E de recovery debe cubrir **ambas** aristas:

1. **Produce:** Shadow arranca → `activate()` → POST de dossier → receipt con
   `status_source=PERSISTED_STATE`, `persisted_artifact_status=VERIFIED_FROM_ARTIFACT`.
2. **Detén:** termina el proceso Shadow (el thread daemon de SupraServer muere con él).
3. **Reinicia:** Shadow arranca de nuevo (nuevo proceso, single-instance lock, data_root).
4. **Readback:** `ShadowWindow.on_restore_latest_supra(window)` o
   `_load_latest_supra()` recupera el receipt desde `CRIBASHADOW_HOME`.
5. **Verifica:** el hash del dossier readbackeado coincide con el SHA256 del
   dossier pre-restart (content_hash o hash del artefacto). **No basta con**
   ver que el receipt existe; el contenido debe ser idéntico.

### Qué NO basta
- `status_source == PERSISTED_STATE` solo en el GET de SUPRA: verifica durabilidad
  del server, NO recovery del cliente.
- Stub de cliente (`MockSupraClient`): no exercisea el path real de readback.
- `_load_latest_supra()` existe en `actions.py` pero no tiene un test E2E de
  restart-real de Shadow. Este es el gap de K13.
