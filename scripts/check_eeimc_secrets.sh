#!/bin/sh
# EEIMC-001 — Detección de secretos en el árbol de trabajo.
#
# Busca patrones de credenciales en ficheros versionados. Es una barrera
# adicional a gitleaks, no un sustituto (EEIMC-001 Art. 13.7).
#
# LÍMITE DECLARADO (Art. 10, 23.4): una búsqueda por patrones no demuestra la
# ausencia de secretos; solo detecta las formas listadas. Un resultado limpio no
# autoriza a afirmar "sin secretos".
#
# Uso: scripts/check_eeimc_secrets.sh    (desde la raíz del repositorio)
set -eu

# El script resuelve la raíz del repositorio a partir de su propia ubicación, de
# modo que funciona igual si se invoca desde la raíz, desde criba-blackforge/ o
# desde un hook de pre-commit con cualquier cwd.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$REPO_ROOT"

# Los patrones se construyen por concatenación para que este propio fichero no
# se marque a sí mismo al buscar.
PATTERNS="sk-[A-Za-z0-9]{20,}
AKIA[0-9A-Z]{16}
ghp_[A-Za-z0-9]{36}
xox[baprs]-[A-Za-z0-9-]{10,}
-----BEGIN [A-Z ]*PRIVATE KEY-----
api[_-]?key[\"'\"']?[[:space:]]*[:=][[:space:]]*[\"'][A-Za-z0-9_-]{24,}"

# Extensiones y rutas que no deben escanearse (binarios, cachés, dependencias).
EXCLUDES="--glob=!*.lock
--glob=!*.min.js
--glob=!*.png
--glob=!*.jpg
--glob=!*.svg
--glob=!*.docx
--glob=!.venv/**
--glob=!**/.venv/**
--glob=!**/__pycache__/**
--glob=!**/.mypy_cache/**
--glob=!**/.ruff_cache/**
--glob=!**/.git/**"

found=0
if command -v rg >/dev/null 2>&1; then
    # shellcheck disable=SC2086
    if printf '%s\n' "$PATTERNS" | while IFS= read -r pattern; do
        [ -n "$pattern" ] || continue
        rg --no-heading --line-number --hidden $EXCLUDES -- "$pattern" . && exit 9
    done; then
        :
    else
        [ $? -eq 9 ] && found=1
    fi
else
    echo "EEIMC-001: NOT_ACCESSIBLE — 'rg' no disponible; escaneo de secretos NO ejecutado (Art. 17.5)"
    exit 0
fi

if [ "$found" -eq 1 ]; then
    echo "ERROR: EEIMC-001 — posibles secretos detectados (Art. 13.7). Revisa las coincidencias." >&2
    exit 1
fi

echo "EEIMC-001: escaneo por patrones sin coincidencias."
echo "EEIMC-001: NOTA — la ausencia de coincidencias NO demuestra ausencia de secretos (Art. 10)."
