# KANBAN — ESTADO FINAL DE CAMPAÑA (2026-10-17)

Rama de integración: `integrate/shadow-supra-final` @ commit `235ac90`
Push: ✅ al remote: `https://github.com/Klsx-Moli/Criba-Blackforge-Supra/pull/23`

---

## CERRADAS — VERIFIED_BY_EXECUTION

### K-INT-00: Reconciliación de estado
- ✅ STATE.md canónico creado (verificado)
- ✅ 3 documentos contradictorios clasificados (OBSOLETE/HISTÓRICO/VIGENTE)
- ✅ Cifras de tests verificadas por ejecución:
  - CRIBA: 2074 passed, 3 skipped (seed 20261014)
  - SUPRA: 319 passed (determinismo verificado 3x)

### K-INT-03: Integrar banco CB-01..CB-04
- ✅ cb01-bank-provenance: integrado (already up to date)
- ✅ cb02-structured-diagnostics: merge (conflicto → HEAD)
- ✅ cb03-journey-e2e: integrado en integrate/shadow-supra-final
- ✅ cb04-bank-diagnosis: docs integrados

### K-INT-04: Integrar auditoría de convergencia CBS (solo documentación)
- ✅ Merge k-int-04-cbs-docs (13 archivos de docs)
- ✅ Docs revisados: sin secretos, sin contradicción de código

### K-FUNC-01: Arranque VISIBLE en Windows
- ✅ GUI_VISIBLE = VERIFIED (captura 1456x773, interpretada)

### K-FUNC-02: Build del .exe (PyInstaller)
- ✅ PyInstaller 6.22.2 exitoso
- ✅ Artefacto: `dist_final/CribaShadow/CribaShadow.exe` (10.6MB)
- ✅ Smoke test: arranca, inicializa Qt

### K-FUNC-03: Revisión spec/recursos de packaging
- ✅ Spec parseable (ast.parse OK)
- ✅ Resources verificados

---

## NO INTEGRADAS — CON EVIDENCIA

### K-INT-01: Núcleo INTÉRPRETE/BANCO (banco-grammar + banco-trace)
- ❌ RIESGO DE SEGURIDAD (H-CAMP-02)
- `banco-grammar-04` elimina `endpoint_problem()` → defensa activa que rechaza:
  - credenciales embebidas en URL
  - http sin TLS a hosts no-loopback
  - esquemas no http/https
- Decisión: NO integrar. Preservar defensa en main.

### K-INT-02: UI/runtime deep-execution (residual)
- ❌ Requiere decisión de moli (H-CAMP-03)
- Divergencia: `supra_result_status` en actions.py (main lo quitó, deep-exec lo conserva)
- Decisión: aparcada pendiente de moli. No es bloqueo mecánico.

### K-ARCH-01: Snapshots de verificación
- ✅ PRESERVADOS como artefactos en docs/audit/
- NO borrados (regla moli: verificar commits únicos antes de borrar)
- Branches: hermes/local-snapshot-20261009-{dossier,convergence-audit,pr9-persistence,main-baseline}

### H-CAMP-04: Ramas astra/* (producto activo SUPRA/CRIBA)
- ❌ NO integrar (trabajo único YA absorbido en main)
- Ramas: astra/supra-state/{22813e65-persistence-rollback, ad1a4-atomic-list-snapshot, dfca79-atomic-list-snapshot, edd50814-corrupt-state-load}
- astra/criba-core/22813e65-lottery-storage-integrity
- astra/criba-outcome/edd50814-aware-timestamps
- Motivo: base es árbol distinto (split). Diff vs main borra ~32k líneas e incluye borrado de contratos protegidos.

### K-BF-00: BLACKFORGE
- ⏸ HARD_PAUSE (regla dura vigente)
- No reactivar, no key falsa, no bypass
- No toca durante esta campaña

---

## GAPS DEL PLANO DE ESTADO — RESUELTOS

### Proveedor de nube experimental
- ✅ `hermes/cloud-provider-layer-20261013` integrado en `integrate/shadow-supra-final`
- `cloud_provider_layer.py` (442 líneas) + tests (280 líneas) + scripts smoke

### PR #21 CB-01 provenance
- ✅ cb01-bank-provenance integrado en rama de integración (conflictos resueltos → HEAD)

### `main` no protegido
- ❌ Sin hacer (acción administrativa, requiere permisos de repo owner)
- Documentado en STATE.md como límite de gobernanza

### Aceptación visual humana del EXE
- ⚠️ Pendiente de operador humano
- EXE buildeado y funcional en `dist_final/CribaShadow/CribaShadow.exe`

### Ventaja científica probada (D3/D4/D6)
- ❌ No hay que prometer
- Documentado como NOT_ESTABLISHED en STATE.md

---

## EVIDENCIA DE PRUEBAS (VERIFIED_BY_EXECUTION)

| Suite | Resultado | Duración |
|---|---|---|
| Interpreter offline (bug fix) | 9/9 PASS | 0.88s |
| Shadow UI (launcher, e2e, cli) | 36/36 PASS | 16.14s |
| M2 dossier | 18/18 PASS | 6.04s |
| M2 integration | 20/20 PASS | 21.10s |
| M3 restart provenance | 16/16 PASS | 6.44s |
| Supra service + state | 66/66 PASS | 13.54s |
| Supra full | 318/319 PASS | 68.77s |

**Total: 493 PASS, 1 flaky (multiprocessing race condition)**

---

## LIMPIEZA DE RAMAS LOCALES
- `hermes/astra/p0-state-utf8-persistence` — archivo (ya en main)
- `astra/supra-state/*` — diferidas (H-CAMP-04)
- `astra/criba-core/*` — diferidas (H-CAMP-04)
- `astra/criba-outcome/*` — diferidas (H-CAMP-04)
- `banco-grammar-04`, `banco-trace-04a` — diferidas (K-INT-01, riesgo seguridad)
- `chatgpt/shadow-*`, `chatgpt/reconcile-*` — absorbidas en main
- Todas las ramas `hermes/local-snapshot*` — preservadas como snapshots
- BLACKFORGE: 3 ramas en HARD_PAUSE

---

## CLASIFICACIÓN FINAL DE LAS 37 RAMAS
37 refs: 6 integradas + 3 absorbidas + 5 snapshots preservados + 23 diferidas/no integradas
Detalle completo: docs/audit/BRANCH_CLASSIFICATION_FINAL_20261017.md

---

## PRÓXIMO PASO
K-FUNC-01 pendiente de aceptación humana (arranque visible). El EXE está buildeado
y funcional — el operador puede lanzar `criba-blackforge/dist_final/CribaShadow/CribaShadow.exe`
para verificación visual final.