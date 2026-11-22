# CBS-FINAL-32/40 — registro canónico de campaña

Estado inicial: 2026-11-22. Rama de trabajo acumulativa: `campaign/cbs-final-32-40`.
Baseline inmutable de transferencia: `757519c480390167f22df60d7ef2da79215d1a72` (`handoff/cbs-final-20261122`).
Main observado: `1304649b781c335e66016b480ed7d7797fa6f359`.
La referencia de progreso es el HEAD remoto de la rama de campaña, no un SHA autorreferencial escrito antes del commit.
Preservar el handoff, su matriz original, todos los materiales locales, los checkpoints y las 26 tareas anteriores. Esta campaña no renumera ni cancela esas tareas.

## Reglas de ejecución y aceptación

- Usuario autoriza desarrollo incremental en GitHub; no merge a main, despliegue, gasto, borrado, force-push ni modificación de ASTRA. BLACKFORGE diferido para la campaña. No arrancar inferencia sin autorización G0 correspondiente. No publicar secretos, datos personales, DB, modelos o binarios.
- Leer EEIMC-001, AGENTS, PROMPT_ARRANQUE y CONTROL_PREVIO. Sus blobs en la transferencia son idénticos a los previamente leídos en main (e31cd169, 8a753c79, 2f4060da, 4ec8b1f3). No rebajar puertas. Mantener Shadow como interfaz principal y CRIBA como motor de invención, SUPRA como desarrollo y verificación.
- Cada ciclo: comprobar HEAD y trabajo nuevo, delimitar contrato, reproducir, agregar regresión, reparar cuando sea autorizado y viable, ejecutar pruebas, mutar/refutar, revisar diff, registrar evidencia y siguiente punto. No afirmar pruebas no ejecutadas. Ramas auxiliares solo si necesarias; mantener rama de campaña acumulativa.
- Estados: VERIFIED_BY_EXECUTION, STATICALLY_INSPECTED, REPORTED_BY_AGENT, NOT_EXECUTED, NOT_ACCESSIBLE. Diferenciar SOURCE, WIRED, EXECUTED, TESTED, PACKAGED_VERIFIED. Un test sintético no demuestra inferencia, causalidad, novedad ni rendimiento. Los porcentajes de fases no son funcionalidad.
- G0=DRAFT_NOT_APPROVED; P0_SEMANTIC=OPEN; SCIENTIFIC_ADVANTAGE=NOT_ESTABLISHED; DESKTOP_VISUAL_ACCEPTANCE=NOT_VERIFIED. No cambiar esos estados mediante documentación o pruebas estructurales.
- La aceptación final requiere recorrido real en Shadow: problema -> generar/inventar -> interpretar -> evaluar -> desarrollar en SUPRA -> guardar -> cerrar -> reiniciar -> recuperar -> exportar; errores, cancelaciones, modelos y recuperación; compilación y arranque EXE Windows desde entorno aislado, verificación visual, CI y regresión. Sin acceso al PC, separar lo pendiente para ERNIE y no declarar completitud.

## Fase 01 — Consolidación canónica y reproducibilidad del handoff

Resultado dentro del alcance: COMPLETADO para la corrección de portabilidad del gate y establecimiento de baseline; campaña IN_PROGRESS, aceptación productiva pendiente.
Baseline comparado con main: ahead 3, behind 0, 22 archivos. Transferencia sin check runs registrados; main 5/5 informado y verificado previamente, no equivalente a CI de candidata. 156 dirigidos, 1791 unitarios/8 skips, Ruff F/E9 y mypy son REPORTED_BY_AGENT, no pruebas propias de toda la rama. La suite 1791 pertenece al worktree ASTRA, no al SHA de transferencia. No se reclasifica como aceptación de EXE.

### Reparación F01-01 (P1 reproducibilidad)
`criba-blackforge/tests/unit/test_k3_ledger_gate.py` usaba una ruta absoluta de otro worktree Windows. Un test omitido, otro falla por import; los registros del supuesto test de integración se construían manualmente. El gate de referencia no está en el árbol transferido.
Reproducción: archivos exactos del remoto, verificados con git hash-object: normalizador 3dcd28a193d650f7f640e72ebc098949e0393e3f; test original 80e699068efb3a0b3d401b2a458af5ae40cdb3a2; gate 74cac16e6e5458c076afeab22cef643e401fecc9; casos 25a6b77fdf2e99b5b71a97142ee9eb1d5d712d50. Entorno Linux aislado Python/pytest, sin clon completo por DNS inaccesible; reconstrucción byte a byte de esos cuatro archivos.
Antes: 11 passed, 1 failed (ModuleNotFoundError), 1 skipped.
Cambio: incorporar los cinco blobs exactos de `28727ba494640ef32e04ada576eb26e14cca65be` en `docs/research/semantic-correspondence/g0-draft/`; no editar sus reglas; importar gate desde ruta de checkout con runpy (sin contaminación sys.path/sys.modules), usar normalizar_lote real, sin skip, probar A/B/C (16/36/108), slot inesperado y recibo sintético sin promoción.
Después: 16 passed, 0 failed, 0 skipped desde raíz de Criba y desde /tmp con PYTHONPATH. Dos mutaciones detectadas (manifiesto alterado y normalizador que retorna lista vacía: 5 fallos cada una), módulo ambiente impostor no cargado (5 passed). Restaurado 16 passed. compileall dirigido PASS. Test modificado blob 1296fc9f606b54be6ea5d083f36b1954d3d2580a. Sin llamadas LLM ni datos reales. No suite completa, Ruff/mypy o CI de esta fase ejecutados. Esta es una reparación de laboratorio y tests habilitante G3, no de semántica productiva.

Comandos desde `criba-blackforge`:
```sh
python -m pytest -q tests/unit/test_k3_ledger_gate.py
python -m compileall -q tests/unit/test_k3_ledger_gate.py ../docs/research/semantic-correspondence/g0-draft/pilot_gate.py
```

### Conciliación del handoff (sin sobrescribir su documento histórico)

| ID | Hallazgo | Estado |
|---|---|---|
| F01-02 P1 | El handoff §6.3 atribuye BEGIN IMMEDIATE de record_event a ERNIE como novedad respecto de main. Main exacto ya lo tiene (storage.py blob a624a0e9..., línea 250); transferencia añade comentarios, busy timeout y otras rutas. | STATICALLY_INSPECTED; corrección de atribución, no volver a reparar por esa afirmación. |
| F01-03 P0 candidato | El handoff §5 y matriz dicen que _assert_requested_model contrasta /props.model_path y que test_model_runtime_identity.py existe. En transferencia, model_runtime.py blob b547a9aa0b2d2ba97731d5b2ed70b34461c5dec4, líneas 189–195, 312–338, solo verifica /v1/models (o /api/tags) y alias. El árbol completo no contiene ese test. | STATICALLY_INSPECTED, no reproduccion dinámica aún. Identidad real de GGUF NOT_VERIFIED. Solicitar recuperación de reparación local o reconstruir con pruebas dirigidas. |
| F01-04 P0 candidato | normalizar_slot toma el primer recibo con request_sha coincidente; no comprueba body_sha256 == receipt_sha256, ni intento, ni STATUS del recibo. El if final y su retorno alternativo son equivalentes. Extrae labels autorreportadas desde múltiples campos. | STATICALLY_INSPECTED. Fase 02: reproducir con almacenamiento, puentes y hashes reales antes de corregir. |
| F01-05 P1 | El banco de 500 y cbs_corpus.py/test_cbs_corpus_adapter.py no están en árbol transferido; el laboratorio de 58 variantes sí. El gate 18 casos es público, desarrollo, no holdout independiente. | NOT_ACCESSIBLE para el adaptador local. Recuperar código exacto y decidir preservación de reserved; no fingir integración. |
| F01-06 P1 | Matriz marca PACKAGED_VERIFIED en varias capacidades sin build del SHA transferido, EXE con hash reportado y smoke offscreen únicamente; no hay acreditación visual o artefacto de ese SHA. | REPORTED_BY_AGENT; verificar después localmente y separar build/source. |
| F01-07 P1 | Contabilidad física inferida de recibos cerrados, llamadas perdidas/duplicadas no demostrables; límite documentado por ERNIE, no resuelto. | Fase 02/03: distinguir intentos de envío observados, incertidumbre y consumo proveedor. No prometer prueba por recibos únicamente. |
| F01-08 P1 | Contrato de targets de Shadow con constante literal declarada en handoff. | REPORTED_BY_AGENT; inspeccionar en fase UI. |

## Plan de fases (orientativo, no presupuesto de calidad)

01 baseline, reproducibilidad y campaña (esta fase). 02 integridad del recibo y lector del ledger; 03 contabilidad de transporte y presupuesto; 04 recuperar/certificar identidad modelo y completar alcance local transferido; 05 contrato semántico experimental y adjudicación; 06 comparabilidad S0/S1 y preflight; 07 criterios G0/autorizaciones y pruebas físicas cuando proceda; 08 interpretación de fallos y estados; 09 integración controlada en productor-consumidor tras autorización; 10 validación del contrato semántico y rutas alternativas.
11 persistencia de sesión y evidencia; 12 deduplicación/replay; 13 cache, migraciones y versiones; 14 recuperación y exportación.
15 inventario del motor y cruces operativos; 16 generación y diversidad sin proxies inválidos; 17 interpretación del cruce y propuesta; 18 evaluación y comparación con baseline sin claims no demostrados.
19 Shadow targets reales; 20 flujo generar/inventar; 21 acciones, cancelación, retry y errores; 22 selección/modelos/estado; 23 historial, recuperación y UX.
24 puente SUPRA; 25 dossieres y contratos; 26 runner, errores, recuperación; 27 journey integrado.
28 runtime local/cloud autorizado; 29 rendimiento y recursos; 30 seguridad y robustez; 31 regresión/CI y empaquetado; 32 aceptación final real y handoff.
33–40 reserva de ciclos adicionales por hallazgos o puertas pendientes. Si una fase revela P0/P1 se puede reordenar con justificación. Las fases que requieren autorizaciones/inferencia/local se conservan bloqueadas mientras se sigue con trabajo independiente.

## Siguiente acción exacta

Fase 02: comprobar el contrato persistido de semantic_reservations/semantic_receipts y su unión con semantic_critic_bridge, semantic_lab y semantic_ledger_gate. Reproducir recibo de mismo request pero distinto body_sha, STALE con mismo request, mismo request en scopes/attempts distintos, cuerpo alterado, recibo ausente, campos contradictorios y filtro corrupto parseable. No tratar un hash de request como hash de respuesta ni etiqueta declarada como veredicto acreditado. Crear sentinelas que fallen sobre el código actual; reparar experimentalmente y verificar almacenamiento -> lector -> gate, sin activar productor productivo ni hacer inferencias. Mantener el gate reproducible. Si falta evidencia local, registrar exactamente y continuar con lo accesible.

Local pendiente: conservar los 33 worktrees y WIP. No cambiar de rama con árbol sucio. Git fetch de la rama de campaña y worktree aislado para inspección; aún no cherry-pick sobre árbol de ERNIE. Solicitar más adelante el diff exacto de model_runtime.py/test_model_runtime_identity.py y cbs_corpus.py/tests, sin subir datos sensibles ni reserved. No exigir otra ejecución local durante las primeras fases remotas.
