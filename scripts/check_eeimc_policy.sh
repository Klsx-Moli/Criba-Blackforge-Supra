#!/bin/sh
# EEIMC-001 — Comprobación de presencia e identidad de la política.
#
# Verifica que el Estatuto existe en la ruta canónica, que declara su versión y
# que el punto de entrada (AGENTS.md) sigue presente. NO demuestra que un modelo
# haya leído el contenido (EEIMC-001 Art. 23.4): solo comprueba existencia e
# identidad, y deja constancia del hash para trazabilidad.
#
# Uso: scripts/check_eeimc_policy.sh    (desde la raíz del repositorio)
set -eu

# El script resuelve la raíz del repositorio a partir de su propia ubicación, de
# modo que funciona igual si se invoca desde la raíz, desde criba-blackforge/ o
# desde un hook de pre-commit con cualquier cwd.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$REPO_ROOT"

POLICY="ESTATUTO_EXCELENCIA_INTEGRIDAD_MEJORA_CONTINUA.md"
ENTRY="AGENTS.md"

fail() {
    echo "ERROR: $1" >&2
    exit 1
}

[ -f "$POLICY" ] || fail "EEIMC-001: falta la política canónica '$POLICY'"
[ -f "$ENTRY" ] || fail "EEIMC-001: falta el punto de entrada '$ENTRY'"

# La versión declarada debe existir: un documento sin versión no es auditable
# (EEIMC-001 Art. 24.1).
grep -qE '^\*\*Versión:\*\*[[:space:]]*[0-9]' "$POLICY" \
    || fail "EEIMC-001: '$POLICY' no declara una versión numérica (Art. 24.1)"

# El punto de entrada debe apuntar a la política: un AGENTS.md que no la
# referencia no obliga a leerla (EEIMC-001 Art. 23.1-23.2).
grep -qF "$POLICY" "$ENTRY" \
    || fail "EEIMC-001: '$ENTRY' no referencia '$POLICY' (Art. 23.1)"

# Los ficheros que el punto de entrada ordena leer deben existir; si falta uno,
# un agente que cumpla Art. 3.4 queda bloqueado en solo-lectura.
for required in PROMPT_ARRANQUE.md CONTROL_PREVIO.md; do
    grep -qF "$required" "$ENTRY" || continue
    [ -f "$required" ] \
        || fail "EEIMC-001: '$ENTRY' exige leer '$required' pero no existe"
done

if command -v sha256sum >/dev/null 2>&1; then
    hash=$(sha256sum "$POLICY" | cut -d' ' -f1)
elif command -v shasum >/dev/null 2>&1; then
    hash=$(shasum -a 256 "$POLICY" | cut -d' ' -f1)
else
    hash="unavailable"
fi

version=$(grep -m1 -E '^\*\*Versión:\*\*' "$POLICY" | sed 's/[*]//g; s/Versión:[[:space:]]*//')
echo "EEIMC-001: política presente | versión=$version | sha256=$hash"
echo "EEIMC-001: NOTA — existencia y hash no demuestran lectura del contenido (Art. 23.4)."
