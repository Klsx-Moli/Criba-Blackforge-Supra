# PROMPT 00 CHECKPOINT — 2026-10-20 (REANUDACIÓN)

## Fecha y hora local
2026-10-20 ~17:00 (Hora de verano romance, UTC+02:00)

## Estado del repositorio

- **Rama:** reconcile/candidate-fix-20261020
- **SHA inicio (checkpoint previo):** d9558693932615055878a3bbfa526a9a4a209255
- **SHA final (esta sesión):** 58e617130078bddc0e9aebf4f0a9c1797ac2c123
- **main intacto:** defd0fd == origin/main (sin tocar, sin push, VERIFICADO)

## Contraste checkpoint previo vs Git real

El checkpoint previo declaraba HEAD checkpoint = 6dbda2e. El Git real mostraba
d955869 = 6dbda2e + 1 commit docs (el propio informe del checkpoint).
**Discrepancia resuelta:** el HEAD real prevaleció y se confirmó que el commit
adicional era únicamente el informe del checkpoint. Sin trabajo perdido.

## Cambios realizados (commit 58e6171)

| Archivo | Cambio | Procedencia |
|---------|--------|-------------|
| criba-blackforge/src/criba/ui/i18n.py | +1 clave EN `shadow.exp_result` | PROMPT_00 Paso D |
| criba-blackforge/shadow_ui/shadow_window.py | 2 claves realineadas a la forma con punto | PROMPT_00 Paso D |

**Diff total:** 2 archivos, +3/-2 líneas. Mínimo, sin cambios accidentales.

### Defecto 1 — tabla EN incompleta (causa raíz confirmada por Git)
El commit b27ccd6 añadió 4 claves al bloque ES (`interpretacion.titulo`,
`interpretacion.sub`, `mas_expandir`, `exp_result`) pero solo 3 al bloque EN.
La tabla EN tenía 88 claves `shadow.*` frente a 89 en ES.
**Fix:** `"shadow.exp_result": "Click to run"` en el bloque EN.

### Defecto 2 — claves huérfanas en el consumidor (causa raíz confirmada por Git)
`shadow_window.py` enlazaba `shadow.interpretacion_titulo` y
`shadow.interpretacion_sub` (guion bajo), pero `i18n.py` solo define la forma
con punto (`shadow.interpretacion.titulo` / `.sub`). `i18n.t()` hace fallback a
la propia clave, así que la ventana renderizaba **nombres de clave crudos** en vez
de texto.
**Decisión de diseño:** se corrigió el consumidor, no el diccionario. La convención
con punto es la dominante (`shadow.nav.*.sub`, `shadow.bf_card.sub`,
`shadow.footer.modelo_off.sub`, `shadow.detail.vacio.desc`) y la que usa el
propio test del sentinel.
**Fix:** 2 llamadas `bind_text` repuntadas a la forma con punto.

## Alcance del fallo i18n (P13 — reescaneo adversarial)

Sondeo exhaustivo de referencias i18n en `shadow_ui/*.py` contra las claves
definidas:
- `shadow_window.py`: 2 referencias huérfanas → corregidas.
- `shadow_context.py`: 8 referencias, todas definidas.
- **Total huérfanas tras el fix: 0.** No hay más claves rotas.

## Verificación ejecutada (criba-blackforge/.venv, Python 3.11.15)

| Prueba | Resultado | SHA |
|--------|-----------|-----|
| test_shadow_i18n_keys.py | **6 passed** (antes: 3 failed / 3 passed) | 58e6171 |
| Mutación 1: borrar `shadow.exp_result` de EN | 2 tests en rojo | 58e6171 |
| Mutación 2: renombrar clave en el consumidor | test de ventana en rojo | 58e6171 |
| Regresión dirigida UI/Shadow (5 ficheros) | **43 passed** | 58e6171 |
| Suite completa criba-blackforge/tests/unit | **1310 passed, 11 skipped, exit 0** | 58e6171 |
| sentinel ×3 corridas + seed fija 12345 | 6 passed cada una | 58e6171 |

**Los 11 skipped** son todos de `test_scientific_cycle.py` y se deben a que el
servicio SUPRA externo en `http://127.0.0.1:9479` no está disponible (HTTP 000,
comprobado). **No están relacionados con este cambio.**

**Prueba de mutación:** el sentinel detecta ambos defectos que existe para
cazar, así que la cobertura no es falsa en este contrato.

## Pruebas NO ejecutadas

- Suite SUPRA completa (`supra/tests`, 29 ficheros) — no ejecutada en esta sesión.
- E2E Shadow + BLACKFORGE.
- Build Windows / packaging.
- CI del SHA 58e6171 (no ejecutada).

## WIP preservado

- **Bundle:** C:/ASTRA_WORK/PREFLIGHT_BACKUP_20261020/bundle_20261020.bundle
- **MD5 verificado:** 1b799fc50ddcde91810a255351212b50 (coincide con el informe previo)
- **WIP files:** C:/ASTRA_WORK/PREFLIGHT_BACKUP_20261020/wip_files/
- **Remote refs:** C:/ASTRA_WORK/PREFLIGHT_BACKUP_20261020/remote_refs.json
- Sin stashes. Sin procesos de pytest interrumpidos (los 3 procesos python
  activos eran el propio Hermes).

## Cambios no atribuibles a esta sesión

`blackforge_broker.py` y `blackforge_case.py` aparecen como modificados en el
árbol de trabajo. Verificado: **solo cambios de fin de línea (CRLF→LF)**, sin
diff de contenido (`git diff --ignore-all-space` vacío). No se tocaron ni se
incluyeron en el commit. Se preservan tal cual.

## Estado de PROMPT 00

**COMPLETADO** el Paso D (i18n). Pendientes de esta sesión:
- Paso E: estado/continuidad honesta.
- Paso F: salidas exigidas.

## Siguiente acción exacta

1. Paso E — estado/continuidad honesta. Revisar `docs/continuity/` y el contrato
   de continuidad CBS contra el estado real del repo.
2. Paso F — salidas exigidas. Comprobar que las salidas declaradas de PROMPT 00
   se producen de verdad (no por nombre de variable).

## Límites respetados

- NO merge a main. NO push. NO release.
- NO activación del executor de BLACKFORGE.
- NO borrado de WIP, backups, ramas ni worktrees.
- NO se descartaron cambios anteriores.
- NO se avanzó a PROMPT 07 ni PROMPT 10.
- NO se declaró DONE: quedan Pasos E y F sin ejecutar.

