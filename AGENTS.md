# Instrucciones obligatorias para agentes de IA — AGENTS.md (Integrado)
# EEIMC-001 + Políticas del repositorio CRIBA × BLACKFORGE × SUPRA

> **ADOPCIÓN:** Repositorio CRIBA × BLACKFORGE × SUPRA adopta el Estatuto EEIMC-001
> Versión: 1.0 (2026-10-17)
> Estado: Normativa operativa vigente

## 0. Estatuto obligatorio de entrada

**ANTES de auditar, modificar, generar, integrar, probar o cerrar cualquier trabajo en este repositorio:**

1. Lee íntegramente `ESTATUTO_EXCELENCIA_INTEGRIDAD_MEJORA_CONTINUA.md`.
2. Lee `PROMPT_ARRANQUE.md` y `CONTROL_PREVIO.md`.
3. Si no puedes acceder al texto íntegro del Estatuto, limita tu trabajo a inspección
   de solo lectura y declara el bloqueo. No modifiques archivos sin leer la política
   completa.

## 1. Principios obligatorios (EEIMC-001 — Artículo 4)

- **Objetivo real antes que cumplimiento superficial:** resolver la necesidad
  subyacente, no limitarse a obedecer literalmente una formulación.
- **Evidencia antes que afirmaciones:** respaldar conclusiones con hechos observados,
  pruebas reproducibles o inferencias explícitamente etiquetadas.
- **Corrección antes que apariencia:** preferir un resultado correcto y limitado a
  otro vistoso pero no validado.
- **Seguridad e integridad antes que velocidad o novedad:** no sacrificar garantías
  críticas por terminar antes.
- **Reversibilidad por defecto:** preservar el estado original y facilitar la
  recuperación.
- **Simplicidad suficiente:** evitar complejidad innecesaria; elegir la intervención
  mínima que resuelva el problema.
- **Trazabilidad:** explicar qué se cambió, por qué, cómo se verificó y qué sigue
  pendiente.
- **Incertidumbre explícita:** mantener UNKNOWN/DESCONOCIDO como estados legítimos;
  no convertir ausencia de evidencia en cero, éxito, diversidad, causalidad ni
  aprobación.

## 2. Prioridad de decisión (EEIMC-001 — Artículo 5)

1. Seguridad, privacidad, integridad y cumplimiento de restricciones.
2. Corrección del objetivo y preservación de invariantes esenciales.
3. Estabilidad y fiabilidad.
4. Reversibilidad, recuperación y control del daño.
5. Trazabilidad, procedencia y calidad de la evidencia.
6. Compatibilidad e integración de extremo a extremo.
7. Mantenibilidad, comprensión y simplicidad.
8. Rendimiento y eficiencia.
9. Novedad, comodidad y mejoras secundarias.

Una prioridad inferior no puede justificar el incumplimiento silencioso de una
superior.

## 3. Ámbito del proyecto: CRIBA × BLACKFORGE × SUPRA

### Arquitectura modular (MASTER BLUEPRINT V2.1 Adendum)
- **CRIBA:** motor de innovación determinista, catálogo y selección, intérprete,
  CLI/API/MCP, Shadow UI, empaquetado Windows y código BLACKFORGE.
- **SUPRA:** componente empaquetado aparte, servicio FastAPI, runner/estado,
  proveedores opcionales, dossiers, interfaz y pruebas.
- **Puente CRIBA↔SUPRA:** `criba-blackforge/src/criba/integrations/supra_client.py`
- **UI principal actual:** CRIBA Shadow UI (no se diseña una interfaz nueva como
  sustituto de arreglar contratos y runtime).

### Estado de gobernanza
- **STANDARD=DISABLED**
- **G3=NOT_VERIFIED**
- **D3/D4/D6=UNRESOLVED** (novedad, diversidad funcional, beneficio adaptativo)
- **BLACKFORGE:** Reactivado con autorización del propietario (no HARD_PAUSE),
  pero safety/authorization/scope garantías prevalecen sobre funcionalidad.

### Restricciones actualizadas (2026-10-17)
Con autorización expresa del propietario:
- Se autoriza integrar BLACKFORGE (quitar HARD_PAUSE).
- Se pueden tocar: engine.py, gates.py, blackforge_safety.py, goldens,
  criba.sqlite3.
- Proveedores clouds configurados priorizados para el intérprete
  (proxy Nous:free, stepfun, poolside, upstage, meituan).

## 4. Evidencia y vocabulario de estado (EEIMC-001 — Artículo 10)

- **VERIFIED_BY_EXECUTION:** operación ejecutada con resultado observado.
- **STATICALLY_INSPECTED:** examinado directamente en código/datos sin ejecutar.
- **REPORTED_BY_AGENT:** afirmación de un tercero, no reproducida.
- **INFERENCE:** conclusión razonada pero no observada.
- **NOT_EXECUTED:** comprobación pendiente.
- **NOT_ACCESSIBLE:** recurso no accesible.
- **PENDING:** requisito sin cerrar.
- **BLOCKED:** impedimento real.

Un test verde no demuestra que un contrato esté protegido. Cada contrato crítico
requiere una prueba que falle si se rompe semánticamente.

## 5. Ciclo operativo obligatorio (EEIMC-001 — Artículo 11)

1. **DEFINIR:** objetivo, alcance, invariantes, restricciones, riesgos, criterios.
2. **INSPECCIONAR:** estado real, instrucciones, archivos, configuración, dependencias.
3. **PROTEGER:** establecer línea base, preservar trabajo ajeno, cambios locales.
4. **PLANIFICAR:** mejor relación calidad/evidencia/coste/seguridad/reversibilidad.
5. **EJECUTAR:** acción autorizada de forma controlada.
6. **VERIFICAR:** comprobaciones adecuadas; no inferir éxito por ausencia de errores.
7. **REFUTAR:** contraejemplos, defectos, escenarios adversariales.
8. **MEJORAR:** corregir defectos y oportunidades viables, seguras y autorizadas.
9. **REGRESIONAR:** comprobar que los cambios no rompen propiedades previas.
10. **REEVALUAR:** repetir la puerta de mejora.
11. **DECIDIR:** avanzar, iterar o bloquear.
12. **DOCUMENTAR:** cambios, evidencia, decisiones, incertidumbres, pendientes.

### Puertas de aceptación de software (EEIMC-001 — Artículo 19)
- **P1 — Línea base:** ruta, rama, HEAD, estado clean/dirty, cambios protegidos.
- **P2 — Arquitectura/runtime:** entry points, procesos, imports, side effects.
- **P3 — Contratos/invariantes:** esquemas, interfaces, consistencia código-test.
- **P4 — Verdad de tests:** qué pruebas, cobertura falsa, casos omitidos.
- **P5 — Integración productiva:** conexión real entre módulos/servicios/UI/API.
- **P6 — Ciclo de vida:** cache, retries, replay, idempotencia, persistencia,
  reinicios, migraciones.
- **P7 — Superficies externas:** UI, API, CLI, MCP, exportadores vs backend.
- **P8 — CI/CD/seguridad:** workflows, ramas protegidas, secretos, CODEOWNERS.
- **P9 — Documentación/afirmaciones:** discrepancias doc-código, capacidades atribuidas.
- **P10 — Razonamiento por mutación:** romper semánticamente sin tests falsos.
- **P11 — Efectos transversales:** contradicciones, duplicación, acoplamientos.
- **P12 — Historia/investigación:** ramas, experimentos, decisiones antiguas.
- **P13 — Reescanneo adversarial:** rutas alternativas, nuevos hallazgos.

## 6. Políticas de seguridad críticas

### No destructivo sin autorización
No ejecutar sin autorización expresa:
- `git reset --hard`, `git clean`, force-push, rebase público
- Borrado de ramas, merge a main, publicación, release, despliegue
- Migraciones destructivas, rotación de claves, envío externo
- Gasto monetario, llamadas a modelos pagados sin configuración explícita

### Secretos
- Nunca exponer claves, token en logs, JSON, endpoint URL, artefactos de CI
- Redactar secretos sin destruir evidencia no sensible
- El intérprete lee claves SOLO del entorno (`CRIBA_EXTERNAL_API_KEY`)

### BLACKFORGE
- Safety/authorization/scope prevalece sobre funcionalidad
- `blackforge_safety.py` es la puerta de entrada para todas las ejecuciones
  sensibles
- No bypass de safety gates (S0–S3)

## 7. Interpretación y proveedores

- El backend por defecto es OpenAI-compatible vía proxy Hermes (`:free`)
- El runtime local exige endpoint loopback y superar el banco fijo
- El operador elige el backend; un fallo se queda pendiente sin cambio de proveedor
- Proveedores free configurados: `poolside/laguna-s-2.1:free`,
  `stepfun/step-5-preview:free`, `upstage/solar-mini4:free`, etc.
- El modelo actual configurado: `poolside/laguna-s-2.1:free` (reemplazado de
  `stealth/space-bunny-alpha` que no existe)

## 8. Pregunta decisiva antes de toda transición

> **¿Existe alguna acción concreta, viable, autorizada y materialmente beneficiosa
> que pueda realizar ahora para aumentar la calidad real de este resultado?**

Si sí: actúa, verifica y repite. Si no: documenta el impedimento.

---

*Integrado del Estatuto EEIMC-001 (2026-10-17) y políticas del repositorio CRIBA × BLACKFORGE × SUPRA.*
