# CB-04: Diagnóstico del banco local — análisis de causa raíz

**Fecha:** 2026-10-11  
**SHA repo:** 6b3d02b9639466e0dcfd594a66b0744bb46abe57  
**Rama:** cb04-bank-diagnosis  
**Artefactos fuente:** verification/local_bank_grammar.json, local_bank_nogrammar.json, local_bank_diagnostic.json

---

## 1. Resumen ejecutivo

El banco local falla de forma consistente en todos los modos (0–50% schema pass rate). La causa NO es el validador ni el grammar — es un problema de **prompt/contrato**: el modelo no comprende las reglas del mecanismo causal ni las restricciones obligatorias.

---

## 2. Datos clave

| Métrica | Sin grammar | Con grammar | Delta |
|---------|-------------|-------------|-------|
| Schema response rate | 25% | 50% | +25 pts |
| Correct abstention rate | 33% | 66% | +33 pts |
| Total passed | 0% | 0% | — |

**Observación:** El grammar mejora significativamente pero NO resuelve el problema de fondo. Sigue habiendo 0% de proposals válidas.

---

## 3. Análisis por dimensión

### 3.1 Schema / Estructura
- **Con grammar:** 50% de respuestas con esquema JSON válido
- **Sin grammar:** 25% (modelo se inventa campos o usa nombres incorrectos)
- **Diagnóstico:** 0% — el prompt sin grammar no logra ni el esquema base
- **Causa:** El prompt no especifica claramente el formato JSON esperado. El grammar impone `json_schema` y obliga al modelo a respetar los campos, pero no garantiza contenido correcto.

### 3.2 Dominio / Mecanismo causal
- **Patrón dominante:** "mecanismo repite nombres de técnicas" (presente en 16/16 intentos)
- **Ejemplo:**
  - Técnica: "Poka-Yoke y Retroalimentación"
  - Mecanismo generado: "La detección y prevención de errores de registro mediante Poka-Yoke y la retroalimentación inmediata..."
  - Problema: El mecanismo es una mera repetición de la técnica, no una explicación causal mecanicista
- **Causa raíz:** El prompt no distingue entre "técnica" (intervención) y "mecanismo" (proceso causal). El modelo, al no entender la diferencia, copia la técnica en el campo mecanismo.
- **Impacto:** 100% de los casos con mecanismo inválido son rechazados por el validador. Es el fallo #1.

### 3.3 Restricciones
- **Patrón:** "restricciones obligatorias no comprobadas exactamente" (presente en 12/16 intentos)
- **Ejemplo:**
  - Problema: "Eliminar segundas visitas SOLO con confirmación automática de registros."
  - Propuesta: "Confirmación automática + Recordatorios"
  - Problema: La restricción "SOLO" no se verificó. El modelo añadió una técnica no autorizada.
- **Causa raíz:** El prompt no incluye una fase de verificación de restricciones. El modelo genera técnicas sin comprobar que cumplan las restricciones explícitas del problema.
- **Impacto:** 75% de los casos con restricciones no verificadas son rechazados.

### 3.4 Abstención
- **Correcta:** 66% con grammar, 33% sin grammar
- **Incorrecta:** El modelo propone técnicas cuando debería abstenerse (ej: "Transferir registros entre sedes" — no hay conexión causal con cruce de técnicas)
- **Causa:** El prompt no define claramente cuándo abstenerse. El modelo tiende a proponer siempre.

---

## 4. Clasificación de la causa raíz

| Dimensión | Estado | Impacto |
|-----------|--------|---------|
| Schema/estructura | Parcial (grammar ayuda) | Medio |
| Mecanismo causal | **ROTO** | **Crítico** |
| Restricciones | **ROTO** | **Alto** |
| Abstención | Parcial | Medio |
| Truncamiento | No observado (max 1702 tokens) | — |
| Crítica | 1 fallo (json_invalido) | Bajo |

**Veredicto:** El problema es de **prompt/contrato**, no de validador ni de capacidad del modelo. El modelo:
1. No comprende la diferencia entre técnica (intervención) y mecanismo (causal).
2. No verifica restricciones antes de proponer.
3. Tiende a proponer siempre, incluso cuando debería abstenerse.

---

## 5. Recomendación

### Cambio mínimo necesario (no ejecutado en esta tarjeta)
1. **Prompt:** Añadir definición explícita de "mecanismo causal" con ejemplo. Añadir fase de verificación de restricciones antes de generar la propuesta.
2. **Grammar:** El grammar actual SÍ ayuda y debe mantenerse. No es la causa raíz.
3. **Validador:** No requiere cambios. Detecta correctamente los fallos.

### Propuesta de prompt mejorado (para CB-02/CB-I01)
```
## Mecanismo causal
Explica CÓMO la intervención produce el cambio observable. No repitas el nombre de la técnica. Describe el proceso paso a paso: qué cambia, por qué cambia, qué variable intermedia se afecta.

Ejemplo:
- Técnica: "Poka-Yoke"
- Mecanismo: "El sistema detecta el error en el momento de la entrada (variable intermedia: detección temprana), previene su propagación al registro oficial (variable intermedia: error bloqueado), y reduce la necesidad de corrección posterior (efecto observable: menos segundas visitas)."

## Verificación de restricciones
Antes de proponer, comprueba CADA restricción explícita del problema:
- ¿La restricción "SOLO X" limita las técnicas permitidas? Entonces NO añadas otras.
- ¿La restricción "debe incluir Y" exige una técnica? Entonces inclúyela.
- ¿Hay restricciones de factibilidad o contención? Compruébalas.

Si no puedes verificar una restricción, abstente.
```

---

## 6. Evidencia

- `verification/local_bank_grammar.json` — 8 intentos, 4 válidos (50%), 5 abstenciones correctas (66%)
- `verification/local_bank_nogrammar.json` — 8 intentos, 2 válidos (25%), 3 abstenciones correctas (33%)
- `verification/local_bank_diagnostic.json` — 8 intentos, 0 válidos (0%)

---

## 7. Estado de la tarjeta

**Criterio GREEN:** Informe con causa, evidencia, reproducción y recomendación. ✅

**SIGUIENTE:** CB-02 (diagnóstico estructurado) y CB-I01 (contrato intérprete↔dossier↔SUPRA) son las tarjetas que implementan la corrección del prompt/contrato identificada aquí.
