# CBS FINAL HANDOFF — punto de entrada para ChatGPT

**Campaña:** CBS-FINAL-32/40 (~3240 iteraciones)
**Fecha de transferencia:** 2026-11-22
**Repo:** https://github.com/Klsx-Moli/Criba-Blackforge-Supra
**Rama de transferencia:** `handoff/cbs-final-20261122`
**Checkpoint local de origen:** `exp/astra-semantic-73f198c` @ `73f198c`
**Estado científico:** G0 = `DRAFT_NOT_APPROVED` · P0 semántico = `OPEN`
**Visibilidad:** público. No cambiar.

---

## 1. Qué es esta rama y qué NO es

Esta rama es una **candidata integrada y coherente** construida desde `main`
remoto (`1304649`) más el trabajo verificado de ERNIE y ASTRA. Es punto de
entrada para continuar la campaña.

**NO es:**
- No es `main`. No se ha fusionado nada a main.
- No es "todo el WIP convertido en candidato". Los desarrollos experimentales
  siguen aislados en sus ramas/worktrees.
- No aprueba G0, no cierra P0, no autoriza fases B/C, no autoriza llamadas.

---

## 2. Estado real del producto

| Componente | Estado | Evidencia |
|---|---|---|
| CRIBA (motor determinista) | **VERIFIED** | suite completa verde, tests del engine |
| Intérprete (OpenAI-compatible) | **VERIFIED** localmente | `test_model_runtime_identity.py` 6/6, mutación detectada |
| Shadow UI (interfaz canónica) | **WIRED / TESTED offscreen** | `test_shadow_three_wiring.py`; `desktop_visual_acceptance = NOT_VERIFIED` |
| SUPRA | **TESTED** (servicio FastAPI, runner) | suite supra |
| BLACKFORGE | **DEFERRED** (no reactivar en esta campaña) | safety gates intactos |
| Ledger K3 semántico | **TESTED** | 6/6 carrera real, 11/11 reserva, 13/13 gate |
| Puente de crítica semántica | **TESTED** | 14/14, mensaje byte a byte idéntico a producción |
| Contabilidad física | **LIMITATIONS DECLARED** | 12/12 pruebas adversariales documentan límites |
| CBS-500 / benchmark semántico | **EVIDENCE_PENDING** | corpus del pack presente, sin ejecutar |

**Último EXE verificado:** `APPS/CribaShadow_20261122/CribaShadow.exe`
sha256 `e53e256985d861bdb41671d2ec17a55c9ce24cdd3764b629f9da2b8d4311dbc3`
(probado sólo offscreen; la GUI real queda `NOT_VERIFIED`).

---

## 3. Rama y HEAD exactos

```
main remoto          = 1304649b781c335e66016b480ed7d7797fa6f359
rama transferencia   = handoff/cbs-final-20261122
HEAD transferencia   = 930b7eb (se rellena con el SHA completo al publicar)
```

Construcción (3 commits sobre main):
1. `463a0d9` — fix(shadow): cablear Generar y Hybrid (aportado desde 73f198c).
2. `d0d1fb6` — feat(cbs): ledger K3, concurrencia SQLite y puente de crítica.
3. `930b7eb` — docs(cbs): CBS_FINAL_HANDOFF.md y matriz de capacidades.

Divergencia respecto a main: **3 commits**, todos verificados, ninguno fusionado.

---

## 4. Mapa de ramas y worktrees relevantes

**Remotas que debes conocer:**
- `origin/main` = `1304649`
- `origin/research/cbs-semantic-g0-draft-20261122` @ `28727ba` — prerregistro G0
  externo (ChatGPT). **Ya reconciliado**: ver §6.
- `origin/fix/storage-decision-evidence-race-20261122` @ `9729983` —
  reparación de `record_decision` (ChatGPT). **Ya integrada** en `storage.py`.
- 42 ramas en `origin` (histórico de PRs #12/#21/#23/#27/#47/#48/#49).

**Worktrees locales a conservar (no borrar):**
```
C:/ASTRA_WORK/cbs-semantic-astra-73f198c   exp/astra-semantic-73f198c  (origen de este trabajo)
C:/ASTRA_WORK/cbs-handoff-final            handoff/cbs-final-20261122  (esta rama)
C:/ASTRA_WORK/cbs-g0-review                28727ba (detached)          (paquete G0 externo)
C:/ASTRA_WORK/iso-storage-race             9729983 (detached)          (reparación externa)
C:/ASTRA_WORK/iso-fixid-20261122           1304649 (detached)          (verificación mypy)
+ ~28 worktrees históricos más (ver `git worktree list`)
```

---

## 5. Decisiones científicas y arquitectónicas de ASTRA (preservar)

- **Correspondencia semántica:** el laboratorio (`semantic_lab.py`,
  `semantic_cases.py`) es material estructural de investigación, **no
  evidencia**. Ninguna lectura semántica se convierte en score, reward o
  promoción. Verificado estáticamente: cero imports desde `src/` y `shadow_ui/`.
- **Identidad:** un alias (`criba-local`) NO acredita identidad. Se contrasta
  la ruta real del GGUF vía `/props.model_path` (`_assert_requested_model`).
- **Puente de crítica:** debe reutilizar la MISMA llamada de producción
  (`prompt_critica` + `_SYSTEM`), no inventar una segunda. Produce byte a byte
  el mensaje que `_pedir` envía.
- **Hashe de mensaje compuesto:** protege QUÉ se envió; `observed_model`
  acredita QUÉ respondió (si se congela con evidencia de host).
- **Contabilidad física:** un registro normalizado NO demuestra cuántas
  llamadas físicas ocurrieron. `physical_calls=1` es inferencia, no prueba.
  Ver §9 y `docs/research/semantic-correspondence/VERSIONES_EFECTIVAS_G0.md` §10.

---

## 6. Cambios incorporados de ChatGPT (reconciliados, no sobrescritos)

### 6.1 Prerregistro G0 (`28727ba`, rama `research/cbs-semantic-g0-draft-20261122`)
- 5 ficheros en `docs/research/semantic-correspondence/g0-draft/`.
- **Verificado por ERNIE:** 16/16 tests OK, plan 16/36/108 exacto,
  manifiesto `pilot_cases.json` `fad4b6fc…` íntegro, 18 casos con 5/11/2.
- **Reconciliación:** los 18 casos existen en el laboratorio ASTRA (18/18) y
  las 18 etiquetas coinciden. No había nada que sobrescribir.
- **Discrepancia declarada:** el prerregistro cita `semantic_lab.py`
  `ef07d195…` (paquete inicial); el efectivo es `e0692a16…` (WIP ASTRA).
  Documentado en `VERSIONES_EFECTIVAS_G0.md`.

### 6.2 Reparación de concurrencia (`9729983`, rama `fix/storage-decision-evidence-race-20261122`)
- Una línea: `BEGIN IMMEDIATE` en `record_decision` antes del SELECT.
- **Verificado por ERNIE:** el defecto existía en la versión local
  (4 fallos reproducidos); integrado sin duplicar (record_event ya lo tenía).
- 7/7 regresiones externas pasan.

### 6.3 Corrección de diagnóstico
ChatGPT afirmó que `record_event` ya tenía `BEGIN IMMEDIATE` en main
`1304649`. **Falso**: en main estaba diferido; lo aportó ERNIE en el ciclo
anterior. No atribuir esa protección a la reparación externa.

---

## 7. Cambios realizados por ERNIE (verificados)

### 7.1 `storage.py` (+234/-1 sobre main)
- Tablas `semantic_reservations` y `semantic_receipts` (migración aditiva,
  `SCHEMA_VERSION` intacta).
- `reserve_semantic_attempt` / `close_semantic_attempt` /
  `semantic_attempt_status` / `load_semantic_receipts`.
- **5 sentencias `BEGIN IMMEDIATE`**, 0 diferidos, en las cinco rutas
  read-modify-write:
  - `record_event` (línea ~279)
  - `record_decision` (línea ~344) — reparación externa integrada
  - `save_chain_memory` (línea ~399) — defecto reproducido y reparado por ERNIE
  - `reserve_semantic_attempt` (línea ~599)
  - `close_semantic_attempt` (línea ~655)
- **Defecto real encontrado en `save_chain_memory`:** dos hilos con el mismo
  campo/valor producían 2 filas duplicadas (SELECT + INSERT no atómicos).
  Reparado con `BEGIN IMMEDIATE`; verificado con `test_storage_rmw_race.py`.

### 7.2 `benchmarks/innovation/` (módulos nuevos)
| Fichero | Hash sha256 | Rol |
|---|---|---|
| `semantic_lab.py` | `e0692a16…` | Laboratorio (ASTRA, WIP) |
| `semantic_cases.py` | `af9e945e…` | 58 casos |
| `semantic_critic_bridge.py` | `2a4e84ac…` | Puente misma crítica |
| `semantic_ledger_gate.py` | `d6e96590…` | Normalizador ledger→gate |
| `semantic_bridge_test_data.py` | `df889dd5…` | Datos del puente |

### 7.3 Tests nuevos
`test_semantic_lab.py` (49), `test_k3_semantic_reservation.py` (11),
`test_k3_semantic_bridge.py` (14), `test_k3_semantic_no_evidence.py` (10),
`test_k3_semantic_isolation.py` (4), `test_k3_sqlite_race.py` (6),
`test_k3_ledger_gate.py` (13), `test_k3_contabilidad_fisica.py` (12),
`test_storage_concurrent_decision.py` (7, externas), `test_storage_rmw_race.py` (3),
`test_shadow_three_wiring.py` (aportado con 463a0d9).

---

## 8. Contratos que deben preservarse

1. **`_pedir` monta `[system=_SYSTEM, user=prompt]`** — el puente debe
   reproducir eso exactamente, o el hash de mensaje diverge.
2. **`_assert_requested_model` contrasta `/props.model_path`**, no el alias.
3. **PK `(scope, attempt)` en reservas** y `(scope, attempt, body_sha256)` en
   recibos: no cambiar sin migración y sin actualizar el normalizador.
4. **`semantic_receipts.status`** refleja el estado AL INSERTAR, no el cierre
   posterior (el vigente puede quedar `ACTIVE`). No reinterpretar como bug.
5. **Un slot = una llamada; cero reintentos.** Un problema de transporte no se
   convierte en abstención.
6. **`physical_calls` se cuenta por recibo cerrado**, no por veredicto.
7. **El laboratorio no se importa desde `src/`** (ver
   `test_k3_semantic_isolation.py`): es material de investigación, no evidencia.

---

## 9. Hallazgos P0 / P1 / P2

### P0 (abierto, semántico)
- **Correspondencia semántica del intérprete no validada.** El validador
  rechaza restricciones no verificadas (correcto), pero la crítica aprobó una
  vez una propuesta de registros para un problema de duchas
  (`restricciones_respetadas: True`). P0 sigue `OPEN` hasta demostrar
  correspondencia y consumidor productivo con evidencia real.
- **Contabilidad física no prueba llamadas.** Declarado como límite, no
  corregible desde el ledger (ver §11 de `VERSIONES_EFECTIVAS_G0.md`).

### P1
- **Shadow GUI real no verificada.** Sólo offscreen. `desktop_visual_acceptance
  = NOT_VERIFIED`.
- **Fases B/C sin autorizar** (36/108 llamadas).

### P2
- **Suite completa del repo:** 1791 passed / 8 skipped / 0 failed en el
  worktree ASTRA (ver §10). En esta rama: 156 passed dirigidos.
- **Posibles duplicados** entre ramas históricas (no resuelto, documentado).

---

## 10. Tests ejecutados y resultados (real, no inferido)

En la rama de transferencia (`handoff/cbs-final-20261122`):

| Comprobación | Resultado |
|---|---|
| Tests dirigidos (storage+semantic+K3+shadow) | **156 passed** en 101 s |
| Ruff (F,E9) sobre lo tocado | **All checks passed** |
| mypy gate del repo | **0/0/0, 183 ficheros, Success** |
| compileall (`storage.py`, `benchmarks/innovation/`) | **rc=0** |
| `git diff --check` | limpio |

En el worktree ASTRA (verificado previamente):
- Suite completa `tests/unit`: **1791 passed, 8 skipped, 0 failed** (8m08s).
- Carrera SQLite real: 6/6 estable × 3 ejecuciones.
- Contabilidad física adversarial: 12/12.
- Mutación `BEGIN IMMEDIATE→BEGIN`: 4 fallos detectados (test sirve).
- 7/7 regresiones externas de `record_decision`.
- 14/14 puente de crítica (mensaje byte a byte idéntico a producción).
- 18/18 casos del gate existen en el laboratorio ASTRA, etiquetas coincidentes.

---

## 11. Fallos conocidos y limitaciones

1. **Un recibo insertado sin llamada real es indistinguible** de uno real:
   `semantic_receipts` no guarda `transport_id`, bytes, tokens ni latencia.
2. **`physical_calls=1` es inferencia**, no prueba de respuesta del proveedor.
3. **Llamada interrumpida / timeout tras enviar** no deja recibo: aparece como
   `NOT_RUN`, no como `ERROR`. No distingue "no llamé" de "llamé y no llegó".
4. **Dos cuerpos con el mismo `body_sha256`** colisionan en la PK: el segundo
   `INSERT OR IGNORE` se ignora. Correcto para cuerpo repetido, pero el
   recuento de recibos ≠ recuento de llamadas.
5. **Modelo solicitado ≠ identidad acreditada.** Se necesita `/props`.
6. **pytest-qt:** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` rompe `qapp`/`qtbot`
   (falsos `fixture not found`). Usar `QT_QPA_PLATFORM=offscreen` sin ese flag.
7. **`pytest-current` del temp del sistema** da `PermissionError` (WinError 5):
   usar `--basetemp` propio.
8. **`tests/fixtures/retrybox_pilot`** rompe el discovery
   (`ModuleNotFoundError: retrybox`): usar `--ignore=tests/fixtures`.
9. **8 tests skipped** en la suite completa (no todos ejecutados; ver reporte).
10. **`scientific_advantage: NOT_ESTABLISHED`** y
    **`desktop_visual_acceptance: NOT_VERIFIED`** vigentes.

---

## 12. Autorizaciones pendientes

**Firma G0 consolidada** (una sola respuesta):
`C:\Users\KLSX\Desktop\CBS_AUTORIZACION_G0_CONSOLIDADA_20261122.txt`

Seis decisiones: alcance (3 problemas, fase A 16 slots), juez (mismo modelo),
modelo/parámetros (por `/props`), semillas (27183/314159/161803), presupuesto
(16 llamadas, cero reintentos), versión congelada (`semantic_lab e0692a16`).

Sin esa firma: **no se ejecutan fases A/B/C**. G0 sigue `DRAFT_NOT_APPROVED`.

Otras pendientes:
- Decisión sobre los 15 perfiles que comparten `18080` con `auto_start=False`.
- Alinear criterio del probe de invención (`estado=="PROPUESTA"`) con el del
  validador (rechaza restricciones no verificadas).
- C2/C3 (mensajes de indisponibilidad/estado en UI) y `auxiliary.goal_judge`
  con timeout coherente (4096 tok / 8,5 tok/s = 482 s vs 30 s).

---

## 13. Deuda técnica

- El gate de targets no valida widgets reales (literal `12`): binding declarado
  y no construido pasaría el audit. Documentado, no corregido.
- `save` / `save_invention` / `save_blackforge_session` son INSERT puros con
  UUID (sin RMW): no requieren `BEGIN IMMEDIATE`, pero conviene documentarlo.
- Ramas históricas duplicadas (~42 en origin, ~33 worktrees). No limpiar sin
  inventario y autorización.
- Falta `pytest.ini`/config que declare `pytest-qt` en `addopts` para que la
  suite Qt funcione sin flags manuales.

---

## 14. Trabajo que requiere necesariamente el PC local

- **Verificación de GUI real** (`desktop_visual_acceptance`): sólo offscreen
  hasta ahora. Requiere DISPLAY.
- **Empaquetado del `.exe`** de CribaShadow desde Criba (`APPS/...`).
- **Servidor local de inferencia** (llama-server en `:8080`): actualmente
  caído; requiere GPU local (RX 570 8 GB, un solo modelo residente).
- **Fases A/B/C**: requieren inferencia local y firma G0.

---

## 15. Primera tarea recomendada para ChatGPT

1. **No redesplegar main.** Partir de `handoff/cbs-final-20261122`.
2. **Reconciliar P0 semántico con evidencia real**, no con tests sintéticos:
   demostrar correspondencia consulta↔hipótesis con el consumidor productivo
   aceptando por razones válidas.
3. **Cerrar la contabilidad física** si es viable (añadir al recibo
   `transport_id`, bytes, tokens, latencia y `observed_model`), o declararla
   explícitamente como límite firmado.
4. **Verificar Shadow GUI real** en el PC local (offscreen no basta).
5. **Emitir el prerregistro G0 definitivo** con la versión `e0692a16` y la
   autorización consolidada antes de cualquier llamada.

---

## 16. Referencias exactas

- **Estatuto:** `ESTATUTO_EXCELENCIA_INTEGRIDAD_MEJORA_CONTINUA.md` (raíz).
- **Handoff ASTRA original:** `ASTRA_SEMANTIC_HANDOFF.md` (en worktree ASTRA).
- **Versiones efectivas:** `docs/research/semantic-correspondence/VERSIONES_EFECTIVAS_G0.md`.
- **Paquete G0 externo:** `docs/research/semantic-correspondence/g0-draft/`
  (en `28727ba`, no en esta rama).
- **Informes ERNIE (local, Desktop, NO publicados):**
  `CBS_G0_PREFLIGHT_CERRADO_20261122.txt`,
  `CBS_SUITE_COMPLETA_FALSOS_NEGATIVOS_20261122.txt`,
  `CBS_AUTORIZACION_G0_CONSOLIDADA_20261122.txt`,
  `CBS_SEMANTIC_K3_CERRADO_20261122.txt`,
  `CBS_G0_CICLO_CERRADO_20261122.txt`.
- **Hashes de artefactos:** §7.2 y §13 de `VERSIONES_EFECTIVAS_G0.md`.

---

## 17. Continuidad y restricciones vigentes

- G0 **no** se considera aprobado por esta transferencia.
- P0 semántico **no** se cierra por pruebas sintéticas.
- **No reactivar BLACKFORGE** durante la campaña CBS-FINAL-32/40.
- No llamadas de pago, no despliegues, no merges a main, no borrados.
- No iniciar desarrollo paralelo tras completar la transferencia.
- Preservar estados científicos, restricciones y evidencias locales.