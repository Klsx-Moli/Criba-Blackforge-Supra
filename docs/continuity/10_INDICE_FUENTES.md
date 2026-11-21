# ÍNDICE DE FUENTES — corpus CBS (CRIBA/BLACKFORGE/SUPRA)

OBSERVED_AT: 2026-10-05 (hora local del host KLSX, Europe/Madrid)
Recopilado por: Hermes (writer), a petición explícita del usuario.
Regla aplicada: se conservan los originales SIN resumirlos, corregirlos ni
sobrescribirlos; este índice NO sustituye a los originales.

## Fuentes presentes en este paquete (bytes literales)

| source_id | fichero | origen | bytes | sha256 | cobertura |
|---|---|---|---|---|---|
| SRC-P1 | 00_SOURCE_MEGAPROMPT_ASTRA6_literal.md | paste_1_191456.txt (adjunto usuario) | 42235 | 75bf76c85eb7fb4d5797397016c893c50dbbd89becd41a2311f3bab7630eb156 | ÍNTEGRA (360 líneas) |
| SRC-P2 | 01_SOURCE_RESPUESTAS_DISENO_literal.md | paste_2_192429.txt (adjunto usuario) | 26562 | 785ec7888666257e4470fe1693f993c0c593148f0fd16379ab87ba687b2bd362 | ÍNTEGRA (328 líneas) |
| SRC-P3 | 02_SOURCE_MANDATO_MAESTRO_v2_literal.md | paste_3_192448.txt (adjunto usuario) | 19400 | ab0a27637f44fcb625a0ccd8c2d38c812bc096a872fd82a34156bb6931ca9830 | ÍNTEGRA (529 líneas) |

Los tres ficheros son copias byte a byte de los adjuntos entregados por el
usuario en esta sesión. El hash cubre el fichero tal como quedó escrito en
disco; no se ha normalizado fin de línea ni codificación.

## Fuentes CITADAS por el corpus pero NO presentes en disco (medido 2026-10-05)

| source_id | nombre citado | citado en | estado |
|---|---|---|---|
| SRC-01 | ASTRA_MASTER_VALUE_ARCHIVE_MAXIMO_2026-10-02.txt (~74 KB) | SRC-P1 §3; SRC-P3 §2 | NO LOCALIZADO en las rutas buscadas (C:\ASTRA_WORK, Desktop; búsqueda acotada) |
| SRC-02 | CRIBA_SUPRA_MASTER_CONTINUITY_2026-10-02.txt | SRC-P1 §2; SRC-P3 §2 | Original NO DISPONIBLE. Existe una versión REFORMULADA/COMPACTADA dentro de SRC-P1 §2 — ver corrección abajo |
| SRC-03 | PROTOCOLO_33_MAXIMO_HISTORICO_PERPLEXITY.txt (~36 KB) | SRC-P1 §5; SRC-P3 §2 | NO LOCALIZADO en las rutas buscadas (búsqueda acotada) |
| SRC-04 | Conversación literal (RESPUESTA 1/2 + síntesis) | SRC-P3 §2 | PRESENTE parcialmente: SRC-P2 contiene RESPUESTA 1, RESPUESTA 2 y la síntesis final |

### CORRECCIÓN de una afirmación histórica previa (SRC-02)

La afirmación previa «CRIBA_SUPRA_MASTER_CONTINUITY incluido ÍNTEGRO dentro de
SRC-P1» era INCORRECTA. Procede de una reformulación/compactación: el primer
mega prompt (SRC-P1 §2) REESCRIBIÓ ese documento, no lo reprodujo literalmente.
Clasificación correcta:

    SRC-02:
      Original no disponible en el paquete local.
      Existe una versión reformulada/compactada en SRC-P1 §2.
      No acredita conservación literal ni cobertura sin omisiones.

El fichero fuente SRC-P1 (00_SOURCE_MEGAPROMPT_ASTRA6_literal.md) se conserva
SIN MODIFICAR: la afirmación histórica queda como antecedente y la corrección
vive aquí, no en el original. (Regla: añadir revisión y motivo, no borrar.)

### LIMITACIÓN de la búsqueda de fuentes ausentes

«NO LOCALIZADO» significa no hallado en las rutas efectivamente buscadas, NO
inexistente en todo el equipo. La búsqueda fue acotada (C:\ASTRA_WORK y
C:\Users\KLSX\Desktop). SRC-01 y SRC-03 podrían existir en otra ubicación no
explorada; recuperarlos requiere que el usuario indique dónde.

Consecuencia declarada, según la regla 9 de SRC-P3 §2:

    CORPUS_INTEGRITY = INCOMPLETE

Faltan los bytes originales de SRC-01, SRC-02 y SRC-03. Se dispone de resumen
(SRC-01, SRC-03) y de versión reformulada (SRC-02) dentro de SRC-P1. Ningún
resumen ni reformulación sustituye al original: hasta recuperar esos tres
ficheros no puede afirmarse cobertura sin omisiones del corpus completo.

## Verificación de copia byte a byte (origen -> destino)

Comparación EXPLÍCITA de cada adjunto original contra la copia escrita en este
paquete (mismo tamaño Y mismo SHA-256):

| origen (paste_*.txt) | bytes | sha256[:16] | destino | bytes | sha256[:16] | igual |
|---|---|---|---|---|---|---|
| paste_1_191456.txt | 42235 | 75bf76c85eb7fb4d | 00_SOURCE_MEGAPROMPT_ASTRA6_literal.md | 42235 | 75bf76c85eb7fb4d | SÍ |
| paste_2_192429.txt | 26562 | 785ec7888666257e | 01_SOURCE_RESPUESTAS_DISENO_literal.md | 26562 | 785ec7888666257e | SÍ |
| paste_3_192448.txt | 19400 | ab0a27637f44fcb6 | 02_SOURCE_MANDATO_MAESTRO_v2_literal.md | 19400 | ab0a27637f44fcb6 | SÍ |

Copia literal acreditada por comparación de origen y destino, no sólo por el
hash del destino. Ejecutado por Hermes (execute_code, 2026-10-05); no
verificado por un tercero independiente.

## Regla de uso

- SRC-P1, SRC-P2, SRC-P3 = HECHO DOCUMENTAL (decisión/propuesta histórica).
- Ninguno acredita implementación en el repositorio.
- Ninguno levanta HARD_PAUSE ni concede permisos.
- Toda afirmación de estado del repo debe re-medirse contra un SHA concreto.
