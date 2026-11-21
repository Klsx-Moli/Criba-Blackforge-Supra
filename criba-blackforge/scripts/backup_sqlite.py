"""Backup SQLite con SHA-256 e integridad verificada.

Uso:
    python backup_sqlite.py <origen> <destino>

El destino NO debe existir. Si existe, el script falla sin sobrescribir.
El origen se abre en modo read-only. No se modifica el origen.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Calcula SHA-256 de un fichero leyendo por bloques."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_sqlite(origen: str, destino: str) -> dict:
    """Backup de una base SQLite con verificación.

    Args:
        origen: ruta de la base SQLite (se abre read-only).
        destino: ruta del fichero de backup (NO debe existir).

    Returns:
        dict con destino, sha256, integrity y size.

    Raises:
        FileExistsError: si el destino ya existe.
        Exception: si el backup o la verificación fallan.
    """
    origen_path = Path(origen)
    destino_path = Path(destino)

    if not origen_path.exists():
        raise FileNotFoundError(f"origen no existe: {origen}")
    if destino_path.exists():
        raise FileExistsError(f"destino ya existe, no se sobrescribe: {destino}")

    # Backup con conexiones cerradas correctamente
    src = sqlite3.connect(f"file:{origen_path}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(destino_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    # Verificar la copia
    check = sqlite3.connect(str(destino_path))
    try:
        result = check.execute("PRAGMA integrity_check;").fetchone()
    finally:
        check.close()

    integrity = result[0] if result else "unknown"
    sha = sha256_file(destino_path)
    size = destino_path.stat().st_size

    return {
        "destino": str(destino_path),
        "sha256": sha,
        "integrity": integrity,
        "size": size,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Uso: {sys.argv[0]} <origen> <destino>", file=sys.stderr)
        return 1

    origen = sys.argv[1]
    destino = sys.argv[2]

    try:
        result = backup_sqlite(origen, destino)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"DESTINO: {result['destino']}")
    print(f"SHA256: {result['sha256']}")
    print(f"INTEGRITY: {result['integrity']}")
    print(f"SIZE: {result['size']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
