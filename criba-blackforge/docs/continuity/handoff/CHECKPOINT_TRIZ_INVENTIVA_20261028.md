# CHECKPOINT — Campaña ACADEMICO-TRIZ-INVENTIVA (FUSIÓN TRIZ+KOESTLER)
# Continuidad de campaña, NO reabre hitos. NO sobrescribe HANDOFF_PAUSA.md.
# Estado de preparación original: PREPARED_NOT_INTEGRATED. SCIENTIFIC_BENEFIT_NOT_ESTABLISHED.
# Estado vigente: sección 15 — recuperación offline acotada; aceptación real bloqueada, 12/12; READY_FOR_PUSH=NO.

Fecha: 2026-10-28
Writer: Hermes (sesión Nous/ornith-1.5-122b:free). Modelo de sesión != intérprete del producto.

## 1. OBJETIVO Y AUTORIZACIÓN VIGENTE
- Convertir fuentes TRIZ+Koestler en material utilizable por el intérprete:
  fichas, operadores, entradas al intérprete, mapping, validador, fixtures y
  pruebas aisladas. NO solo bibliografía.
- Autorización: LOCAL PREPARATION ONLY. Escritura solo en el candidato.
- IMP-10 (integración productiva) NO AUTORIZADO: solo diff propuesto.
- Prohibido: runtime productivo, servicios, llamadas del producto a modelos,
  instalaciones, commit/push/PR/merge, reabrir hitos, promover D3/D4/D6/G3/STANDARD.

## 2. WORKSPACE / RAMA / HEAD / MOMENTO
- Candidato: C:\ASTRA_WORK\cbs-candidate\criba-blackforge
- Rama: hermes/cbs-t00-candidate-20261025
- HEAD: 5e89959a0dfc3337663970a4aff74364f2702482
- Observado: 2026-10-28. Baseline dirty (PRE-EXISTENTE, protegido, NO de esta campaña):
  14 tracked modificados + 10 untracked reales (24 entradas).
  Corrección del manifiesto histórico: no perpetuar "15+6=24"; la composición real
  es 14 modificados + 10 untracked.

## 3. UBICACIONES
- Payload operativo: C:\Users\KLSX\Downloads\HERMES_FUSION_TRIZ_KOESTLER_CRIBA_BLACKFORGE_SUPRA_SHADOW.md
  (BEGIN_MASTER_FUSED_PAYLOAD líneas 2126-8455; SOLO este bloque es operativo).
- Normas: AGENTS.md, PROMPT_ARRANQUE.md, CONTROL_PREVIO.md, ESTATUTO (candidato).
- Mapa de tarjetas: docs/research/triz-inventiva/campaign_manifest.json

## 4. TARJETA ACTUAL / COMPLETADAS / PENDIENTES
- AC-00/IMP-00: COMPLETADO (informe read-only + mapping REUSE/EXTEND/NEW/DUPLICATE).
- IMP-01: COMPLETADO (35 fuentes -> sources.jsonl, con provenance).
- IMP-02: COMPLETADO (mapping a contrato real + validador aislado).
- IMP-03: COMPLETADO (8 operadores -> operators.jsonl; fixtures; plantilla intérprete).
- IMP-04 (parcial): COMPLETADO en laboratorio aislado (cadena validador+fixtures+
  mapeo intérprete con dobles identificados). NO es E2E productivo.
- IMP-05: COMPLETADO (SPEC.md + 8 pruebas round-trip/conflictos; STORAGE TEMPORAL
  + httpx mock; NO SUPRA real). 8 passed, REAL_EXIT=0.
- IMP-06: COMPLETADO (SPEC.md view-model + plan de pruebas UI; NO runtime).
- IMP-07: COMPLETADO (BLACKFORGE_HANDOFF_SPEC + casos de seguridad; NO ejecutado).
- IMP-08: COMPLETADO (pruebas negativas del validador; 25 passed). Ampliar en IMP-05/06/07b.
- IMP-09: COMPLETADO (piloto del operador A4-OP-FIX-01, control de fijación, sobre
  el PUERTO REAL determinista engine.activate + preparar_dossier + validador).
  10 passed, REAL_EXIT=0. Sin LLM/servicio. Veredicto: FIXATION_OBSERVED=False
  (gap=-1; sembrar 1 mecanismo no reduce la diversidad de 94 ideas). Prueba de
  SOFTWARE del operador + encaje con puerto; NO de utilidad. SCIENTIFIC_BENEFIT
  NOT_ESTABLISHED.
- IMP-10: NO AUTORIZADO (integración mínima productiva; solo diff propuesto).
- IMP-11: PENDIENTE (cierre de fase).

## 5. ARCHIVOS DE ESTA CAMPAÑA (nuevos, aislados) vs TRABAJO PREVIO
- Nuevos (todos bajo docs/research/triz-inventiva/):
  _payload_extract.json, campaign_manifest.json
  sources/sources.jsonl (35)
  operators/operators.jsonl (8: OP-TRIZ-01/02/03, OP-BIS-01/02/03, OP-EXP-01, OP-CRIT-01)
  findings/cards.jsonl (70: 24 IMPLEMENTATION_TASK + 2 WORKFLOW + 44 ACADEMIC_FINDING)
  validator/validador.py, validator/__init__.py
  fixtures/fixtures.py, fixtures/__init__.py
  interpreter/TEMPLATE_INTERPRETER_INPUT.md
  tests/test_validador.py, tests/conftest.py, tests/_last_run.txt
  imp05_supra_preservation/SPEC.md, imp05_supra_preservation/tests/test_supra_roundtrip_lab.py
  imp06_shadow_ui/SPEC.md
  imp07_blackforge_handoff/SPEC.md
  imp09_pilot_protocol/SPEC.md, imp09_pilot_protocol/tests/conftest.py,
  imp09_pilot_protocol/tests/test_pilot_fixation_control.py
- Trabajo previo PROTEGIDO (NO tocado): los 14 modificados + 10 untracked de la
  baseline. No se ha hecho commit/stash/reset/clean/checkout.

## 6. REPARACIONES APLICADAS (steer 2026-10-28, sin debilitar contrato)
- validate_cards: detección INDEPENDIENTE de duplicado (CARD_DUPLICATE_ID, una vez
  por id) + resolución de dependencias adelantadas; validación de tipo de ID y
  depends_on (error de validación, no traceback).
- _is_unknown: marcadores DELIMITADOS (None, "", "UNKNOWN", "UNKNOWN: …");
  "UNKNOWNLAND" NO se reconoce. No se extrapola a otros campos.
- validate_inventive_card: valida el ESQUEMA ANIDADO REAL (content/limits/
  discrimination); sin defaults, sin `a or b`; la ficha NO usa prueba.alternativa
  (ese campo es del contrato del intérprete).
- validate_sources: SRC_LICENSE_UNKNOWN / SRC_READING_UNKNOWN son AVISOS (warnings),
  no errores: UNKNOWN es estado legítimo del material documental.

## 7. NO VERIFICADO / PENDIENTE
- round-trip real de SUPRA (IMP-05): no ejecutado; una prueba de disco local NO
  acredita SUPRA real ni un reinicio del producto (AC explícito de la tarjeta).
- IMP-05b: corrupción/restart del almacenamiento de SUPRA (doble identificado +
  storage temporal) — pendiente si se autoriza.
- Shadow UI operativa: no modificada; solo mapping de diseño (IMP-06).
- BLACKFORGE handoff real: no ejecutado; ningún grant registrado ni dispatch (IMP-07).
- Puerto/adaptador real del intérprete: REPORTED (AGENTS.md candidato), no verificado
  por ejecución esta sesión.
- Beneficio inventivo: NO establecido (SCIENTIFIC_BENEFIT_NOT_ESTABLISHED).

## 8. COMANDOS Y RESULTADOS (evidencia)
- Comando: cd C:/ASTRA_WORK/cbs-candidate/criba-blackforge/docs/research/triz-inventiva
  && .venv/Scripts/python.exe -m pytest tests/test_validador.py -p no:randomly -q
- python: C:\ASTRA_WORK\cbs-candidate\criba-blackforge\.venv\Scripts\python.exe (3.11.15)
- pytest 9.1.1.
- Resultado validador: 25 passed in 0.51s. REAL_EXIT=0.
- Localizador: docs/research/triz-inventiva/tests/_last_run.txt
- IMP-05: .venv/Scripts/python.exe -m pytest
  docs/research/triz-inventiva/imp05_supra_preservation/tests/test_supra_roundtrip_lab.py -p no:randomly
  -> 8 passed, REAL_EXIT=0. STORAGE TEMPORAL + httpx.MockTransport; NO SUPRA real.
- IMP-09: .venv/Scripts/python.exe -m pytest
  docs/research/triz-inventiva/imp09_pilot_protocol/tests/test_pilot_fixation_control.py -p no:randomly
  -> 10 passed, REAL_EXIT=0. PUERTO REAL determinista (engine.activate + dossier + validador);
  sin LLM/servicio. Veredicto piloto: FIXATION_OBSERVED=False (gap=-1).

## 9. SIGUIENTE ACCIÓN
- IMP-09b (si se autoriza): mejorar la potencia del piloto de fijación. El
  núcleo determinista (94 ideas/query fijas) no es sustrato adecuado; un piloto
  con poder requeriría un generador de una idea a la vez o un LLM (implica
  servicio/no-determinismo, fuera de alcance actual).
- IMP-05b (si se autoriza): harness de SUPRA con doble identificado y storage
  temporal; probar corrupción/restart del almacenamiento de SUPRA.
- IMP-06b (si se autoriza): pruebas de mapping view-model deterministas (T-14
  estados: loading/empty/error/stale/retry/doble envío) sin arrancar la UI productiva.
- IMP-11: cierre de fase.
- IMP-10 (NO AUTORIZADO): integración mínima productiva; solo diff propuesto.

## 10. PROCESOS PROPIOS
- Ninguno activo al cierre de este checkpoint.

## 11. REANUDACIÓN POSTERIOR — 2026-10-28 (sesión actual)
Esta sección es posterior al registro anterior; no lo convierte en ejecución de
esta sesión. HEAD observado: acaace748788ef465b4b43178424a76c1ee3cb31, misma rama.
Estado: INCOMPLETO. IMP-11 no cerrado; beneficio científico NO establecido.

- Dirección incorporada a cuatro documentos de arranque del candidato; backups
  y baseline de entrada (18 tracked + 10 untracked) conservados bajo
  docs/research/triz-inventiva/evidence/resume_20261028/.
- Maestro idéntico al payload local; MD base preservado en el maestro.
- A3/A4 extraídos con hashes exactos; checkers locales: 24 y 28 tests, exit 0;
  payloads sin errores, con 7/8 avisos de derechos legítimos. Manifest incremental:
  docs/research/triz-inventiva/supplements/manifest.json. NO integración runtime.
- Baseline de campaña reproducida: 4 failed, 46 passed. Reparado el doble de
  lab/imp05_supra_roundtrip.py: workflow BLOCKED, sandbox NOT_REPORTED y planning
  receipt preservado, sin fabricar ejecución ni tocar el cliente del producto.
- Reproducción real del recorte a 200 caracteres en LotteryEngine. Adaptador
  aislado lab/cross_packet.py + tests conserva operaciones y rechaza conflictos
  de ID sin cambiar sorteo/score. No consumidor productivo conectado.
- Propuesta IMP-10-A exacta, NO APLICADA:
  docs/research/triz-inventiva/imp10_integration/lossless_operations.diff.
  Solo lottery.py (cuatro recortes de descripción) y contrato.py (assertions
  frágiles frente a JSON escapado). Proyección en memoria probada con semillas
  0/1/42 conservando RNG/scores/identidad. git apply --check PASS.
- Última regresión: 57 passed in 2.65s, exit 0. Evidencia:
  evidence/resume_20261028/campaign_with_proposal.log y .xml.
  Es laboratorio, NO recorrido GUI/cloud/producto validado.
- WIP ajeno a los cuatro documentos de arranque seguía con hashes de entrada
  al verificarse antes del cierre. No se ha hecho commit/push/merge.
- El propietario pide integrar lo conveniente con Shadow; 'main' no se toma
  como permiso de merge. La respuesta a la aprobación exacta de IMP-10-A fue
  'tu que aconsejas': NO se considera aprobación. Se recomienda ese cambio
  mínimo antes de una refactorización grande o de unir ramas a ciegas.
- Próxima decisión: aprobación concreta de IMP-10-A; después aplicar y probar
  el camino compartido UI/intérprete/conservación. Continúan pendientes la
  cadena completa A3/A4, GUI visible y llamadas reales con permiso específico.
- Coste: medium para pasos congelados de patch/test; high para decisiones de
  integración/arquitectura. Modelo/proveedor NO cambiados automáticamente.

Informe de continuidad y comandos completos:
docs/research/triz-inventiva/ESTADO_FUNCIONAL_Y_SIGUIENTE_CAMBIO_20261028.txt.
El mutex cooperativo propio se libera al terminar; no acredita exclusión frente
a editores ajenos al protocolo. Medir hashes y estado al retomar.

## 12. ESTADO VIGENTE — IMP-10-A APLICADO (2026-10-28)
Autorización posterior del propietario: «adelante tienes yolo», en respuesta a
la recomendación de aplicar el diff exacto IMP-10-A. Ya no está pendiente su
aprobación; no volver a pedirla ni reabrir su preparación.

COMPLETADO para IMP-10-A; INCOMPLETO para el recorrido entero del producto.
Rama/HEAD sin cambios: hermes/cbs-t00-candidate-20261025 / acaace7. Sin commit.

Aplicado exactamente, con hashes posteriores iguales a la propuesta:
- src/criba/lottery.py: eliminados los cuatro recortes de descripción a 200.
- src/criba/interprete/contrato.py: retirados asserts que rechazaban datos JSON
  legítimos con comillas/saltos; validación contractual y safety sin cambios.
- Nuevo tests/unit/test_lossless_operations_contract.py: cuatro regresiones
  sobre runtime real; RED 4 failed -> GREEN 4 passed.
- Adaptados dos tests de laboratorio: el antes se carga desde snapshot
  inmutable y las entradas legacy truncadas se etiquetan como fixtures. No
  se exige que el bug siga presente en el runtime corregido.

Evidencia ejecutada después de aplicar:
- Regresión relacionada: 137 passed in 58.73s, exit 0 (JUnit: 0 failures/errors/skips).
- Campaña: 57 passed in 2.85s, exit 0 (JUnit: 0 failures/errors/skips).
- Puente Shadow/intérprete: 2 passed in 1.53s con dobles explícitos. Comprueba
  contrato y una instancia por run; NO renderizado ni cloud real.
- Test nuevo: ruff PASS. Módulos modificados: ruff sin diagnósticos añadidos
  respecto al snapshot previo (lottery 8->8, contrato 1->1; deuda no corregida).
- Proyección histórica: RNG/scores/identidad conservados con seeds 0/1/42.
- Catálogo empaquetado cargado: 6870 registros. Sus dos descripciones más largas
  (230/230 caracteres) llegan completas al prompt. Muestra: 6224 caracteres
  frente a 6164 con el recorte anterior (+60); sin llamada a modelo.
- git apply --reverse --check PASS; solo inspección, sin revertir.
- WIP protegido fuera de los objetivos autorizados: hashes de entrada intactos.

Logs, XML, comandos y hashes:
docs/research/triz-inventiva/evidence/imp10a_apply/COMMANDS.txt
docs/research/triz-inventiva/evidence/imp10a_apply/applied_report.json

No se modificó RNG, selector, scoring, proveedor, UI o controles sensibles.
No se llamó cloud, ejecutó BLACKFORGE, instaló, publicó ni fusionó main.
No se cambió el modelo/effort de la sesión automáticamente.
A3/A4 continúan preparados, no integrados. GUI visible, inferencia cloud real,
recuperación completa del producto y beneficio inventivo siguen NO VERIFICADOS.

Siguiente borde funcional: recorrer Shadow -> inventar -> intérprete elegido ->
propuesta legible -> guardar/recuperar, reutilizando capacidades y WIP existentes.
No rehacer T00 ni unir ramas a ciegas. Una futura llamada cloud o cambio fuera
 del diff aprobado requiere el permiso específico que siga vigente.

## 13. ESTADO VIGENTE — LOTE NUEVO Y ACEPTACIÓN FALLIDA (2026-10-29)

INCOMPLETO / NO APTO PARA PUBLICAR. READY_FOR_PUSH = NO.
Misma rama hermes/cbs-t00-candidate-20261025 y HEAD acaace748788ef465b4b43178424a76c1ee3cb31.
La autorización posterior de integración y push condicional figura en AUTORIZACION_LOCAL_20261028.txt;
no usar las prohibiciones iniciales de este checkpoint como si no hubieran sido ampliadas.
El nuevo permiso de inferencia NO es permiso nuevo de publicación.

- Autorización incremental literal: evidence/functional_integration/lot_20261029_035722/authorization_NEW_LOT.txt.
  Solo poolside/laguna-s-2.1:free, Nous existente; máximo 12 intentos nuevos. Usados/reservados 3;
  9 no usados. Consumo anterior e histórico UNKNOWN. No reinicializar el ledger.
- Original del protocolo inválido recuperado del write_file de la sesión y preservado, con
  corrección trazable. No se presupone consumo anterior cero ni se borra evidencia.
- Guard nativo sobre HTTP real y upstream sintético: 9 comprobaciones PASS, sin inferencia;
  incluye retry, concurrencia, reserva durable antes de recepción, intento 13 y error de ledger.
- Suite normal: perfil de enhancer aislado, frontera de sockets en pytest, cinco tests de
  inferencia requieren opt-in explícito. No es un sandbox de procesos arbitrarios.
- Corregidos handles SQLite y espera Qt: callback local 30 s, HTTP de test 5 s, pytest 60 s;
  no se aumentaron los timeouts productivos.
- Catálogo: legacy 7201 intacto + 27 registros padre/A3/A4 (8/9/10); cada registro llega
  al prompt y SQLite con un proposer sintético explícito. Datos compilados y ejecutados
  coinciden por SHA. Transporte acreditado, NO ejecución científica de las técnicas.
- Inventario offline de 2424 casos cubierto por particiones y regresiones: 2405 passed,
  16 skipped (5 inferencia, 11 SUPRA:4880 ausente), 3 xfailed (canon PLANNED).
  Cero rojos vigentes en ese agregado; NO hubo otro monolítico final en un único proceso.
  Dos continuaciones por nodeids fallaron en colección; no se cuentan como producto probado.
  El resto se ejecutó tras colección canónica completa; 68 passed en la última partición.
- Ruff de los 12 targets de guard/probe pasa; mypy: 181 ficheros, cero issues/deuda nueva.
- Aceptación del EXE: botón real Shadow -> 3 entradas pendientes sin propuesta válida.
  Aplicación exit=3, runner exit=2. No se ejecutaron BLACKFORGE ni guardado/reinicio reales.
  El rechazo completo no quedó guardado: causa exacta UNKNOWN. No se regeneró para reparar
  lectura de informe. El probe actualizado conserva diagnóstico acotado (20 tests PASS).
- EXE actual reconstruido (exit=0) y arranque STARTUP_SMOKE_PASS (exit=0), sin más inferencia.
  SHA actual bd098fd7167e76d359837e0eeb798a5bfc0db74d5e6998af42e6b53bb4cc8597.
  No transferir al nuevo EXE la evidencia del intento fallido sobre el binario anterior.
- Efecto declarado: el primer run heredó LOCALAPPDATA y añadió una entrada sintética pendiente
  al ledger normal del producto, run_id dcae89bdd1bb4a1594adfd54789802c7. Preservada, no borrada.
  Driver futuro corregido para aislar también LOCALAPPDATA; sin nueva inferencia de ese ajuste.
- Todos los procesos registrados de esta sesión terminaron; proxy propio parado, 8645 cerrado.
  Sin commit/push/merge, sin cambios globales de Hermes ni borrado/reversión de WIP.

Evidencia actual (rutas relativas al proyecto):
- docs/research/triz-inventiva/evidence/functional_integration/lot_20261029_035722/FINAL_STATE.json
- misma carpeta: INFORME_FINAL.txt, final-snapshot.json (rutas/hashes), offline-partition-coverage.json,
  packaged-acceptance.json, physical_budget_NEW_LOT.sqlite3 y package-startup-final.json.
- dist-final/CribaShadow/ conserva la carpeta onedir completa.
- Copia legible del informe: C:/Users/KLSX/Desktop/CBS_ESTADO_FUNCIONAL_20261029_0454.txt.

Siguiente acción: clasificar por qué el proveedor dejó pendientes las propuestas usando evidencia
existente y casos locales del contrato. No repetir inferencia solo para recuperar diagnóstico
perdido; no reiniciar contador. La aceptación real de ambas interfaces sigue abierta, y con ella
la reconstrucción limpia/revisión de publicación. Beneficio científico NO ESTABLECIDO.

## 14. ESTADO VIGENTE — 12/12 AGOTADOS, CAUSA REGISTRADA (2026-10-29 05:35 +01:00)

BLOQUEADO / READY_FOR_PUSH=NO. HEAD y rama no cambiados. Sin commit/push.
El propietario confirmó un intento instrumentado y reiteró autonomía YOLO; no se aumentó
el presupuesto ni se interpretó como permiso de cambiar proveedor, pagar o rebajar gates.

- Mismo ledger physical_budget_NEW_LOT.sqlite3: 12 reservas, saldo 0, integridad ok,
  IDs 1..12. Consumo anterior e histórico UNKNOWN. NO reiniciar ni crear cupo implícito.
- Intento 4..6: modelo responde abstención por evidencia vacía/calidad BASURA del cruce.
- Se probó que el contrato permite hipótesis condicional con evidencia_citada=[];
  se aclaró ideación vs validación y se mantuvieron intactos los siete validadores/esquemas.
  PROMPT_VERSION=proponer-v2-547c4e5a0c5b23b9; prueba por hash AST preservada.
- Intento 7..9: dos rechazos de contrato (nombres de técnicas en mecanismo y restricciones
  no copiadas/comprobadas exactamente), un timeout. Ninguna propuesta válida.
- Intento final 10..12: ruta JSON Schema existente, sin soporte anunciado por el modelo.
  Dos rechazos de restricciones, uno además sin explicación rival; un timeout.
  No se acreditó cumplimiento de schema. Ninguna propuesta válida; no fallback.
- No se ejecutaron BLACKFORGE ni guardado/reinicio con proveedor real.
- Gates locales: 21 del probe, 88 regresiones relacionadas, frontera 5 tests PASS.
  Contrato.py: sin nuevos diagnósticos Ruff frente a snapshot (1->1); no rebajar validaciones.
- Build nuevo exit=0; aplicación exit=3 y runner exit=2. No equiparar build con funcionar.
- Proxy detenido, 8645 cerrado; procesos de aceptación y build finalizados.

Evidencia actual: docs/research/triz-inventiva/evidence/functional_integration/
lot_20261029_035722/shadow-diagnostic-exception/FINAL_STATE_BUDGET_EXHAUSTED.json,
validator-preservation.json, prompt-regression.xml y los tres subreportes.
Informe humano: C:/Users/KLSX/Desktop/CBS_DIAGNOSTICO_20261029_0535.txt.
Snapshot anterior del contrato: misma carpeta, patch-before/contrato.py; no se ha revertido.
El EXE dist-prompt-fix/CribaShadow/CribaShadow.exe tiene SHA
 d7b9f752513cb103988202c533afc769671bfcd9405a801edf07169449620c21.

Siguiente paso: no hacer inferencia adicional bajo el lote agotado. Para continuar la
aceptación real se requiere un lote incremental explícito distinto, sin reiniciar este,
o una decisión explícita sobre otro modelo/proveedor. No promover READY_FOR_PUSH ni
beneficio científico por pruebas locales. No repetir auditoría general ni las suites ya medidas.

## 15. RECUPERACIÓN OFFLINE — CAUSA INMEDIATA Y LÍMITE PROBATORIO (2026-10-29)

BLOQUEADO PARA ACEPTACIÓN REAL / READY_FOR_PUSH=NO. Mismo HEAD y rama; sin commit/push.
Orden vigente: resolver con evidencia existente, cero inferencias nuevas, sin renovar
lote, cambiar modelo/proveedor ni relajar contrato. Se mantienen 12/12 y saldo cero.

- Caso original EXE b9135d8b..., reservas 1..3, app=3/runner=2, 44.52 s:
  replay offline de las funciones de ESE ejecutable con el estado normalizado del
  ledger reproduce InventionProbe.poll:96 -> chosen_entry:33 -> ValueError por
  ausencia de propuesta válida. Tres pendientes con hipótesis/mecanismo vacíos.
  Registro correlacionado por tiempo/consulta: run_id dcae89bdd1bb4a1594adfd54789802c7,
  línea 431 del ledger normal, 2026-10-29T03:12:06+00:00. No es enlace criptográfico.
  Faltan error/provenance por candidato y respuesta/estado HTTP del intento original.
  Causa anterior (transporte/proveedor/parser/contrato) UNKNOWN; no atribuir por descarte.
  Replay de ESTADO capturado, no replay de respuesta HTTP ni captura del escritorio.
- Caso posterior separado EXE d7b9f752..., reservas 10..12: rechazo de restricciones,
  alternativa explicativa ausente en una respuesta y timeout 120030 ms. Diagnósticos
  retenidos, cuerpos no retenidos: no reproducirlos como si fueran respuestas capturadas
  ni transferir esas causas a reservas 1..3. Unión petición/candidato solo temporal.
- Defecto local de identidad demostrado: preserve_sheet omitía run_id y generated_at.
  Regresión sintética RED: 2 failed (KeyError run_id). Parche de solo esos dos campos;
  módulo dirigido GREEN: 8 passed. No conserva entrada privada ni salida bruta.
  Conexiones bloqueadas desde antes de importar pytest; 0 intentos de conexión.
  Siete validadores/esquemas AST idénticos al snapshot. No cambio de prompt ni gates.
- Replay ad hoc exit=0, nueve artefactos anteriores intactos por hash. Ruff final PASS
  en tres archivos; primera pasada tuvo cinco E501 del replayer, corregidos.
- Build de diagnóstico en directorios nuevos exit=0. EXE f5aa6653e7125904d58d6820d0d17badadf995a008788f1feef383ea2d2e5dd9.
  Método embebido verificado contra fuente sin arrancar la aplicación. Startup y
  aceptación de este EXE NOT_EXECUTED. Build no demuestra generación válida.
- Suite histórica 372 passed/1 failed conservada como fallida; catálogo 3 passed
  solo con su alcance previo, no repetido. Sin suite completa nueva ni aceptación.

Evidencia del tramo, bajo shadow-diagnostic-exception/offline-recovery-20261029/:
 identity-red.xml, identity-green.xml, replay-result-final.json, RECOVERY_STATE.json,
 INFORME_RECUPERACION_OFFLINE.txt, build-trace-identity.log y before/.
Informe humano: C:/Users/KLSX/Desktop/CBS_SHADOW_RECUPERACION_OFFLINE_20261029.txt.
Artefactos previos y FINAL_STATE_BUDGET_EXHAUSTED.json preservados sin reescritura.

Siguiente acción requiere una sola autorización concreta, todavía NO concedida:
hasta 12 intentos físicos adicionales (incluye retries/fallos/crítica), únicamente
poolside/laguna-s-2.1:free en http://127.0.0.1:8645/v1/chat/completions. Datos mínimos
sintéticos y operaciones pertinentes, sin corpus/código/secretos privados. Mantener
ledger anterior en 12; registro incremental vinculado solo tras autorización, nunca
reinicio. Hipótesis: propuesta válida+crítica con contrato íntegro y traza de run_id;
la mejora diagnóstica no acredita reparación generativa. Éxito = generar/mostrar/
guardar/restaurar en proceso nuevo sin nueva inferencia de recuperación para ambas
interfaces. Parar al primer recorrido fallido, cuota o ruta no gratuita/no disponible.
Sin autorización, detener inferencia. Generación y recuperación reales siguen pendientes.

