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

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite JSON constant")


path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle, object_pairs_hook=unique_object, parse_constant=reject_constant)
except (OSError, ValueError) as exc:
    print("EEIMC-001: JSON ilegible: " + type(exc).__name__)
    print("EEIMC_STATE_FAIL")
    raise SystemExit(1)

if not isinstance(data, dict):
    print("EEIMC-001: el estado no es un objeto JSON")
    print("EEIMC_STATE_FAIL")
    raise SystemExit(1)

current = data.get("current")
phase = current.get("phase") if isinstance(current, dict) else None
if not isinstance(phase, str) or not phase.strip():
    print("EEIMC-001: el estado no declara current.phase")
    print("EEIMC_STATE_FAIL")
    raise SystemExit(1)

branch = current.get("branch", "")
last_good = data.get("last_good_state", {})
if not isinstance(last_good, dict):
    print("EEIMC-001: last_good_state no es un objeto")
    print("EEIMC_STATE_FAIL")
    raise SystemExit(1)
commit = last_good.get("commit", "")
if not isinstance(branch, str) or not isinstance(commit, str):
    print("EEIMC-001: branch/commit deben ser texto")
    print("EEIMC_STATE_FAIL")
    raise SystemExit(1)
if any("\n" in value or "\r" in value for value in (phase, branch, commit)):
    print("EEIMC-001: phase/branch/commit deben ocupar una sola linea")
    print("EEIMC_STATE_FAIL")
    raise SystemExit(1)
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
    command_rc=0
    out=$("$@" - "$STATE" <<EOF 2>&1
$PROGRAM
EOF
) || command_rc=$?
    if printf '%s\n' "$out" | grep -Fqx "$FAIL_MARK"; then
        printf '%s\n' "$out" | grep -v "^$FAIL_MARK$"
        return 1
    fi
    if printf '%s\n' "$out" | grep -Fqx "$OK_MARK"; then
        if [ "$command_rc" -ne 0 ]; then
            echo "EEIMC-001: '$label' emitió OK pero terminó con error $command_rc"
            return 1
        fi
        printf '%s\n' "$out" | grep -v "^$OK_MARK$"
        return 0
    fi
    echo "EEIMC-001: '$label' sin marcador exacto de veredicto"
    return 2
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
        exit 2
        ;;
esac
