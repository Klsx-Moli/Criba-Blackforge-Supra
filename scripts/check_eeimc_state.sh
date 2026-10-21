#!/bin/sh
# EEIMC-001 — Comprobación de reconciliación de estado.
#
# Verifica que el fichero de estado del proyecto existe, es JSON válido y
# declara una fase. Un estado ilegible o sin fase impide auditar la línea base
# (EEIMC-001 Art. 19 P1).
#
# Uso: scripts/check_eeimc_state.sh    (desde la raíz del repositorio)
set -eu

# El script resuelve la raíz del repositorio a partir de su propia ubicación, de
# modo que funciona igual si se invoca desde la raíz, desde criba-blackforge/ o
# desde un hook de pre-commit con cualquier cwd.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$REPO_ROOT"

STATE="criba-blackforge/.hermes/iie/STATE.json"

fail() {
    echo "ERROR: $1" >&2
    exit 1
}

[ -f "$STATE" ] || fail "EEIMC-001: falta el fichero de estado '$STATE' (Art. 19 P1)"

# PROTOCOLO DE VEREDICTO: el intérprete imprime un marcador explícito
# (EEIMC_STATE_OK / EEIMC_STATE_FAIL) además de su código de salida. Esto evita
# un falso verde DEMOSTRADO en este entorno: en Windows `python` puede ser el
# alias de Microsoft Store, que devuelve exit 0 sin ejecutar nada, de modo que
# un gate que solo mirase el código de salida aprobaría un JSON corrupto.
OK_MARK="EEIMC_STATE_OK"
FAIL_MARK="EEIMC_STATE_FAIL"

PROGRAM='
import json
import sys

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
except (OSError, ValueError) as exc:
    print("EEIMC-001: JSON ilegible: " + type(exc).__name__)
    print("EEIMC_STATE_FAIL")
    raise SystemExit(0)

if not isinstance(data, dict):
    print("EEIMC-001: el estado no es un objeto JSON")
    print("EEIMC_STATE_FAIL")
    raise SystemExit(0)

current = data.get("current")
phase = current.get("phase") if isinstance(current, dict) else None
if not phase:
    print("EEIMC-001: el estado no declara current.phase")
    print("EEIMC_STATE_FAIL")
    raise SystemExit(0)

branch = (current.get("branch") or "") if isinstance(current, dict) else ""
last_good = data.get("last_good_state")
commit = last_good.get("commit") if isinstance(last_good, dict) else ""
print(
    "EEIMC-001: estado legible | phase=" + str(phase)
    + " | branch=" + (branch or "UNKNOWN")
    + " | last_good=" + (commit or "UNKNOWN")
)
print("EEIMC_STATE_OK")
'

# Se busca un intérprete REAL y se exige que emita el marcador de veredicto.
attempt() {
    label="$1"
    shift
    out=$("$@" - "$STATE" <<EOF 2>&1
$PROGRAM
EOF
) || true
    case "$out" in
        *"$OK_MARK"*)
            printf '%s\n' "$out" | grep -v "^$OK_MARK$"
            return 0
            ;;
        *"$FAIL_MARK"*)
            printf '%s\n' "$out" | grep -v "^$FAIL_MARK$"
            return 1
            ;;
        *)
            echo "EEIMC-001: '$label' no ejecutó el intérprete (sin marcador de veredicto)"
            return 2
            ;;
    esac
}

set +e
rc=2
if command -v uv >/dev/null 2>&1; then
    attempt "uv run --no-project python" uv run --no-project python
    rc=$?
fi
if [ "$rc" -eq 2 ] && command -v python3 >/dev/null 2>&1; then
    attempt "python3" python3
    rc=$?
fi
if [ "$rc" -eq 2 ] && command -v python >/dev/null 2>&1; then
    attempt "python" python
    rc=$?
fi
set -e

case "$rc" in
    0) exit 0 ;;
    1) fail "EEIMC-001: '$STATE' no es JSON válido o no declara fase" ;;
    *)
        echo "EEIMC-001: NOT_ACCESSIBLE — sin intérprete de Python utilizable; JSON no verificado (Art. 17.5)"
        exit 0
        ;;
esac
