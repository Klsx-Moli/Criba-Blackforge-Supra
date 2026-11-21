# AUDITORÍA DEL CAMBIO DE LA SKILL `anti-goodhart-validation`

**Fecha:** 2026-10-22 · **Alcance:** documental (sin revertir ni sobrescribir).

Vocabulario: `FACT`, `INFERENCE`, `NOT_EXECUTED`, `NOT_ACCESSIBLE`.

---

## 1. Ubicación real

| Elemento | Ruta | ¿Dentro del repo? |
|---|---|---|
| Skill | `C:\Users\KLSX\AppData\Local\hermes\skills\anti-goodhart-validation\SKILL.md` | **NO** (fuera del repo, en el perfil Hermes) |
| Referencia añadida | `...\references\selector-pilot-prep-artifacts.md` (6050 B, mtime 2026-10-22 18:45:24) | NO |
| Referencia añadida | `...\references\selector-pilot-preflight.md` (7518 B, mtime 2026-10-22 18:46:32) | NO |
| Referencia añadida | `...\references\pre_confirmatory_gate_format.md` (4885 B, mtime 2026-10-22 18:18) | NO |

**`FACT`:** la skill **no** está en `C:\ASTRA_WORK\Criba-Blackforge-Supra`. `find . -path "*anti-goodhart-validation*"` en el repo → vacío. El directorio `skills/` **no es un repositorio git** (`git rev-parse` → fatal).

## 2. Cambio exacto

**`NOT_ACCESSIBLE`:** no existe **copia previa** de `SKILL.md` (sin `SKILL.md.bak*`, sin git, sin snapshot utilizable). Por tanto **no es posible un diff byte a byte contra la versión previa**.

**`FACT` (estado actual):** `SKILL.md` = 32825 B, mtime **2026-10-22 18:53:40**; 507 líneas; 25 referencias en disco.

**`FACT` (contenido del cambio):**
- Línea 349: nueva sección 26 que exige auditar las precondiciones del piloto antes de ejecutarlo y remite a `references/selector-pilot-preflight.md`.
- Líneas 491/493: **duplicado** de la entrada `selector-pilot-preflight.md` (la misma referencia listada dos veces con distinto texto descriptivo).
- Línea 495: entrada de `selector-pilot-prep-artifacts.md`.
- Línea 496: entrada de `pre_confirmatory_gate_format.md`.

**`FACT` (integridad de referencias):** de las 15 referencias citadas en `SKILL.md`, **todas existen**. 10 referencias en disco **no** están citadas (no es defecto: son referencias huérfanas preexistentes).

## 3. ¿Modifica instrucciones ejecutables, criterios o solo documentación?

**`FACT` + `INFERENCE`:** el cambio **añade** orientación procedimental y **referencias de consulta**. No altera:
- Umbrales, márgenes ni criterios de decisión canónicos (el margen +20 pp y los estados semánticos siguen viniendo del prompt canónico, no de la skill).
- Código ejecutable (la skill es Markdown; no hay scripts modificados).
- El canónico `PROMPT_10_PILOTO_SELECTOR_CRIBA.md` (intacto).

**`INFERENCE`:** el cambio **refuerza** las precondiciones que los informes ya aplicaron (dataset N, criterio de resolución, instrumento independiente, ledger, brazo ejecutable). **No introduce** criterios nuevos que contradigan el canónico. La skill remite al canónico, no lo sustituye.

## 4. Modificaciones no declaradas

**`FACT`:** no se encontró modificación de código de producto ni de artefactos canónicos. **No se detectó** ninguna modificación no declarada en los informes previos.

## 5. Discrepancias detectadas

| # | Discrepancia | Gravedad | Acción |
|---|---|---|---|
| D1 | Entrada duplicada de `selector-pilot-preflight.md` (líneas 491 y 493) | Baja (documental) | se documenta; **no** se corrige automáticamente |
| D2 | 10 referencias en disco sin citar en `SKILL.md` | Informativa | preexistente; no se toca |
| D3 | No hay copia previa → diff imposible | Limitación | se declara `NOT_ACCESSIBLE`; no se infiere contenido previo |

## 6. Verificación de hashes

| Archivo | MD5 |
|---|---|
| `SKILL.md` | `f1ec2bbd24448184efeaf7da85a9d0f2` |
| `references/selector-pilot-prep-artifacts.md` | `8a5396e684df96035e4d24fcfd784e6e` |
| `references/selector-pilot-preflight.md` | `7ce9f9c408cd1bbee6eb8baa227ef345` |
| `references/pre_confirmatory_gate_format.md` | `7a6d00f000d27f825989b561b320239e` |

## 7. Decisión

**No se revierte ni se sobrescribe** el cambio (instrucción explícita). **No se considera aprobado** por el mero hecho de haberse generado: su alcance se documenta aquí y queda pendiente de validación humana. El cambio es **documental/procedimental**, no altera criterios científicos ni código ejecutable.
