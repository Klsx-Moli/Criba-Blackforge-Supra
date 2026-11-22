# Congelacion de versiones efectivas — G0 correspondencia semantica

Estado: **DRAFT_NOT_APPROVED**. Este documento NO autoriza ejecucion.
Solo congela que fichero y que hash son la version EFECTIVA local, para
que el prerregistro no cite hashes de un paquete que ya no es el vigente.

## Por que existe

El `PREREGISTRATION_DRAFT.md` del paquete externo
(`research/cbs-semantic-g0-draft-20261122`, commit 28727ba) cita hashes
del **paquete inicial**. El propio texto lo advierte y pide reconciliar y
congelar la version local efectiva. Esto lo hace, sin sobrescribir su
documento ni el de ASTRA.

## Versiones efectivas verificadas (2026-11-22)

### 2.1 Laboratorio semantico (ASTRA, WIP sin commitear)

| Fichero | Hash citado (paquete inicial) | Hash EFECTIVO local | Estado |
|---|---|---|---|
| `benchmarks/innovation/semantic_cases.py` | `af9e945eaa558d28be9a123d63c59380b11636bbff28dd389b46d048415aedfa` | `af9e945eaa558d28be9a123d63c59380b11636bbff28dd389b46d048415aedfa` | COINCIDE |
| `benchmarks/innovation/semantic_lab.py` | `ef07d1950c3a90fa7065a7a4714b61e5c27baf1036274b16560ad58f8ee4d5e1` | `e0692a16559309e34a47af4c6dd8987695df1d978c2da6cd1d0956ae40623ca6` | DIFIERE — WIP de ASTRA, es la version real |

### 2.2 Corpus y manifiesto del gate

| Fichero | Hash EFECTIVO | Estado |
|---|---|---|
| `pilot_cases.json` | `fad4b6fc0ac3a421d3475864ed7daef37be38cfa03c3551c7ff5b46a234c4c14` | COINCIDE con el declarado |
| `pilot_gate.py` (gate externo) | `69d1d283b2be5cb9334a8c4c46416fe7d42a4667572a3a69c1858c402a276abe` | version efectiva |

### 2.3 Adaptadores y ledger (trabajo de ERNIE)

| Fichero | Hash EFECTIVO | Rol |
|---|---|---|
| `src/criba/storage.py` | `d89a1ea1abee9738a123218f0d2c190eac067a1237019f879f90e14f5e04aad8` | Ledger K3 + reparaciones de concurrencia |
| `benchmarks/innovation/semantic_critic_bridge.py` | `2a4e84acb17e74d4c08e229fc1e7ed83b7d5ddfa659aa1e69436b32b93d033c9` | Puente a la MISMA llamada de critica |
| `benchmarks/innovation/semantic_ledger_gate.py` | `d6e965901847b4332209b894accf361c93c96f1f5ad68842d7e8bfa81ffb67d4` | Normalizador ledger -> gate |
| `benchmarks/innovation/semantic_bridge_test_data.py` | `df889dd58370d2c23ad5d72d87a3011538d28ca5e86ceea5f442baaa00d8443e` | Datos puente desde semantic_cases |

## 3. Decision

- La version EFECTIVA de `semantic_lab.py` es `e0692a16…`.
  El hash `ef07d195…` corresponde al paquete inicial y **no** debe
  usarse como referencia de la implementacion actual.
- No se ha sobrescrito ningun fichero de ASTRA ni del paquete externo
  para "hacer coincidir" los hashes. La discrepancia se declara, no se
  oculta.
- `semantic_cases.py` y `pilot_cases.json` coinciden exactamente.
- El gate externo queda como REFERENCE, no como fuente de verdad, hasta
  que el propietario firme una version unica.

## 4. Transporte efectivo (verificado, no asumido)

- `_pedir` monta el mensaje como `[{"role":"system","content":_SYSTEM},
  {"role":"user","content":prompt}]` (openai_compatible.py:647-649).
- `semantic_critic_bridge.mensaje_compuesto()` produce ese MISMO mensaje:
  comparacion byte a byte verificada (`identicos: True`).
- `_SYSTEM` = 208 chars; prompt de critica del caso base = 2764 chars.
- sha256 del mensaje compuesto base = `0ffc210904158d29…` (no es secreto).

## 5. Configuracion del interprete (leida de openai_compatible.py)

| Parametro | Valor por defecto en codigo | Fuente |
|---|---|---|
| `base` | `http://127.0.0.1:8645/v1` | `CRIBA_EXTERNAL_BASE_URL` o default |
| `model` | `poolside/laguna-s-2.1:free` | `CRIBA_EXTERNAL_MODEL` o default |
| `critic_model` | = `model` | `CRIBA_CRITIC_MODEL` o herencia |
| `timeout_s` | `TIMEOUT_POR_DEFECTO` | `CRIBA_EXTERNAL_TIMEOUT_S` o default |
| `max_tokens` | `MAX_TOKENS` | `CRIBA_EXTERNAL_MAX_TOKENS` o default |
| `temperature` | `TEMPERATURA` | constante |

- La `api_key` se lee SOLO del entorno (`CRIBA_EXTERNAL_API_KEY`) y nunca
  se escribe en logs ni en procedencia. **No se copia al manifiesto.**
- Los defaults propuestos para el prerregistro (max_tokens=2600,
  temperature=0.25, reasoning_effort=none, enable_thinking=false) NO estan
  verificados contra el backend: son propuestas, no observadas.

## 6. Plan exacto de 16 slots (fase A)

Verificado con `pilot_gate.py plan --phase A` sobre `pilot_cases.json`:

- 16 slots = 8 variantes x 2 brazos (S0/S1) x 1 repeticion.
- Desglose: 8 S0 + 8 S1.
- Fases B = 36, C = 108 (acumulativas, NO autorizadas).
- Un slot = como maximo una llamada fisica. Cero reintentos declarados.

## 7. Modelo solicitado vs modelo realmente observado

- **Solicitado**: el que declare `CRIBA_EXTERNAL_MODEL` / `model` en el
  momento de ejecutar.
- **Observado**: el que devuelva `/props` del servidor (`model_path`,
  `n_params`). Se congela en el recibo como `observed_model`, NO se asume.
- En la ultima verificacion el servidor local en `:8080` NO respondio
  (caido). Estado: **DESCONOCIDO** para este momento. No se declara un
  modelo activo sin evidencia fresca de `/props`.

## 8. Identidad del runtime

- `_assert_requested_model` contrasta la ruta real del GGUF
  (`/props.model_path`), no solo el alias. Verificado con
  `test_model_runtime_identity.py` (6 passed, mutacion detectada).
- Un alias (`criba-local`) NO acredita identidad por si solo.
- El hash del mensaje compuesto protege QUE se envio; el `observed_model`
  acredita QUE respondio (si se congela con evidencia de host).

## 9. Presupuesto y politica de reintentos

- Fase A: maximo 16 llamadas fisicas, tope 60 min de pared declarado.
- Un slot = una llamada; sin retries internos ni rama de fallback.
- Un problema de transporte NO se convierte en abstencion.
- B y C NO se activan por superar A: requieren presupuesto y decision
  explicita.

## 10. Limites de la contabilidad fisica (declarados, no ocultos)

Estos son hallazgos de la verificacion adversarial. El sistema NO puede
probar algunas cosas desde el ledger; se declaran como limitaciones:

1. Un recibo insertado sin llamada real es **indistinguible** de uno real:
   `semantic_receipts` no guarda transport_id, bytes, tokens ni latencia.
2. `physical_calls=1` es una **inferencia** del normalizador (recibo
   cerrado), no una prueba de que el proveedor respondio.
3. El recibo del intento VIGENTE queda con `status="ACTIVE"` en
   `semantic_receipts` (no "CLOSED"): el `status` de la tabla refleja el
   estado al insertar, no el cierre posterior. No afecta al recuento, pero
   debe conocerse al auditar.
4. Dos cuerpos con el mismo `body_sha256` colisionan en la PK
   `(scope, attempt, body_sha256)`: el segundo `INSERT OR IGNORE` se
   ignora. Es correcto para "mismo cuerpo repetido", pero implica que el
   recuento de recibos no equivale a recuento de llamadas.
5. Una llamada interrumpida o con timeout tras enviar no deja recibo:
   aparece como `NOT_RUN`, no como `ERROR`. No se distingue de "no llamo".
6. El modelo solicitado no es identidad acreditada; se necesita `/props`.

## 11. Alcance

Los 18 casos del gate existen en el laboratorio ASTRA (18/18) y las 18
etiquetas coinciden. No hay solapamiento que reconciliar en contenido,
solo la version del modulo de laboratorio.

## 12. Pendiente de autorizacion

Este documento no concede inferencia, no aprueba fases B/C, y no cambia
el estado DRAFT_NOT_APPROVED. La ejecucion de la fase A requiere firma
explicita del propietario sobre version + manifiesto + campos + fuente
de autorizacion.