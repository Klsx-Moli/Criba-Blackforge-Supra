# CBS-FINAL — Fase 07: reconciliación G0 y puerta de decisión (NO-GO)

**Estado a 22-11-2026: `G0=DRAFT_NOT_APPROVED`, `P0_SEMANTIC=OPEN`, `NO_GO` para inferencias A/B/C.** Este documento **no es un consentimiento ni una firma**. La rama CBS-FINAL no ha ejecutado modelos reales ni ha modificado ASTRA, BLACKFORGE o `main`.

## 1. Fuentes reconciliadas, sin reescribir la historia

| Activo | SHA256 de bytes congelados | Conclusión |
|---|---|---|
| `semantic_lab.py` efectivo | `e0692a16559309e34a47af4c6dd8987695df1d978c2da6cd1d0956ae40623ca6` | Versión ASTRA vigente en la transferencia; difiere del paquete inicial `ef07d195…` mencionado en el borrador externo |
| `semantic_cases.py` | `af9e945eaa558d28be9a123d63c59380b11636bbff28dd389b46d048415aedfa` | Misma versión citada en ambos documentos |
| `pilot_cases.json` | `fad4b6fc0ac3a421d3475864ed7daef37be38cfa03c3551c7ff5b46a234c4c14` | 18/18 entradas con digest de contenido coincidente, **referencias del autor, no gold** |
| `pilot_gate.py` | `69d1d283b2be5cb9334a8c4c46416fe7d42a4667572a3a69c1858c402a276abe` | Agenda acumulativa A=16, B=36, C=108; umbrales, no autenticación |

Verificaciones ejecutadas en sandbox contra los mismos bytes de los objetos Git del remoto: 58 variantes de desarrollo, 18 seleccionadas, 3 raíces, referencias autorales 5 SUPPORT / 11 REJECT / 2 UNRESOLVED; los hashes de los 18 registros `digest(case)` coinciden. El plan A contiene exactamente ocho variantes previamente elegidas, un par S0/S1 por variante, con orden prefijado estable. **Ninguna raíz ni variante cuenta como referencia científica independiente.**

`PREREGISTRATION_DRAFT.md` (paquete original) y `VERSIONES_EFECTIVAS_G0.md` (checkpoint de ERNIE) se conservan como historia, sin editarlos para aparentar que todo coincide. El segundo contiene descripciones de `semantic_critic_bridge.py`, `storage.py` y `_assert_requested_model` que **ya no son una descripción comprobada del código actual**: fases 02 y 05 modificaron storage/bridge en la rama acumulativa; fase 04 comprobó que el runtime remoto no acreditaba `/props.model_path`. Sus afirmaciones pertenecen a la versión anterior de la transferencia, no deben usarse para autorizar el estado actual.

## 2. Matriz única de puertas y decisiones

| Puerta | Evidencia exigible antes de inferencias | Estado hoy |
|---|---|---|
| Integridad de versiones | SHA de los cuatro artefactos y pares problema→propuesta | **CONSISTENT_DEVELOPMENT_ONLY** |
| Alcance diagnóstico | Tres problemas y A=16; límites de inferencia científica | **PROPUESTO**, no firmado |
| Referencias independientes | Tres revisores competentes ciegos, al menos una fuente independiente del productor del contrato, divergencias y fuentes por eje | **PENDING**, no hay gold |
| Equidad S0/S1 | Información factual equivalente, mismo candidato congelado y restricciones, diferencias de método explícitas | **BLOCKED** (fase 06) |
| Normalización S0 | Contrato y traducción explícita de booleanos/objeciones/UNKNOWN/ERROR/NOT_RUN | **UNMAPPED** |
| Juez/modelo | Identidad efectiva de pesos, runtime, versión, sesión y parámetros verificados | **NOT_ATTESTED**, alias no basta |
| Tokenización/contexto | Tokens reales de ambos prompts y esquema de salida; no truncamiento | **NOT_MEASURED** |
| Una llamada por slot | Eliminar retry de HTTP, truncamiento, fallback y cualquier reintento implícito en ruta productiva | **NOT_WIRED**; simulación fase 03 no es producción |
| Contabilidad física | Reserva durable antes del POST, intentos, timeouts y respuestas, consumo incierto explícito | **NOT_PROVIDER_CERTIFIED**; `physical_calls` es proxy |
| Permiso del propietario | Aprobación consciente de versión exacta, informe comparativo, fuentes/jueces, condiciones, presupuesto y coste | **NOT_GRANTED** |
| B y C | Decisión expresa independiente posterior; nunca avance por umbrales de A | **NOT_AUTHORIZED** |
| Integración / publicación | Regresión y entorno Windows + autorización específica de diff y release | **NOT_APPROVED** |

**Importante:** Cualquier archivo que diga `approved: true`, hash perfecto o supuesto nombre/firma del propietario es solamente una **afirmación**, no un mecanismo de autenticación. El preflight de esta fase nunca puede emitir `GO`, `PREREGISTRATION_APPROVED` ni autorizar una llamada. La aprobación requiere una decisión explícita comprobable fuera de este checker, y aun así los bloqueos materiales deben repararse primero.

## 3. Demostración de falsa cobertura del gate

Al enviar al `pilot_gate.py` registros **sintéticos** para los 16 slots de A, con etiquetas copiadas del propio manifiesto y `physical_calls=1` inventado para cada slot, devuelve `THRESHOLDS_MET_ONLY`. Eso es correcto en su contrato limitado: valida una forma/umbrales, **no** llamadas efectivas, autenticidad de los recibos, independencia del juez, eficacia ni comparabilidad. Esta fase añade una prueba que reproduce el falso «aprobado» si alguien promocionara el campo a permiso. Incluso con 16/16 resultados sintéticos perfectos, la nueva puerta devuelve siempre `NO_GO`.

No enviar el manifiesto, `case_id`, variantes ni referencias al evaluador. Los casos publicados solo sirven para diagnóstico de desarrollo. Cualquier confirmación independiente requiere un protocolo diferente y datos no contaminados.

## 4. Inspección offline reproducible

Desde `criba-blackforge` en un checkout completo, sin proveedores:

```sh
python -m benchmarks.innovation.g0_authorization_preflight
python -m pytest -q tests/unit/test_g0_authorization_preflight.py
```

El informe emite SHA256 bruto esperado/observado, distribución de casos y agenda, discrepancias, decisión `NO_GO`, permiso `NOT_GRANTED_BY_THIS_TOOL`, consumo proveedor `null` y puertas independientes aún pendientes. Requiere los cuatro archivos exactos: ante corrupción, falta de archivo, cambio de versión, desplazamiento de modelo Python importado o cambio de agenda queda bloqueado. No usa una copia anterior de `VERSIONES_EFECTIVAS_G0.md` como autoridad de ejecución.

Si el propietario conserva un formulario local `CBS_AUTORIZACION_G0_CONSOLIDADA_20261122.txt`, su existencia o contenido **no han sido examinados por ChatGPT**. No se sustituirá por un JSON público ni se inventará su firma. Una futura solicitud de aprobación se hará solo después de reparar S0/S1 y acreditar las verificaciones locales.

## 5. Siguiente trabajo concreto sin esperar una firma prematura

Fase 08: investigar en la ruta productiva cómo una propuesta pasa a `PROPUESTA`, `PENDIENTE`, `ABSTENER`, ERROR y `UNRESOLVED` en intérprete, store/cache, Shadow, export y SUPRA. Reproducir transiciones sin inferencias: fallo de crítica, excepción, resultado obsoleto, respuesta parcial, cache legacy y retry. Añadir pruebas/productor-consumidor según alcance seguro, sin convertir UNKNOWN en éxito ni en cero. La prioridad científica G0 permanece bloqueada mientras avanza la funcionalidad offline. No cambiar motor ASTRA, reactivar BLACKFORGE, publicar ni fusionar `main`.
