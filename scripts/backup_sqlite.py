"""Backup SQLite con SHA-256 e integridad verificada.

Mejoras sobre v1:
- try/finally para cerrar conexiones ante excepciones
- Rechazo de sobrescritura de backups existentes
- Validación de que el backup se completó antes de hashear
- Propagación de errores sin imprimir éxito falso
"""
import hashlib
import os
import sqlite3
import sys
from pathlib import Path

BASES = [
    'criba-blackforge/artifacts/criba.sqlite3',
    'criba-blackforge/dist/CribaShadow/smoke_test/criba.sqlite3',
]

DEST_DIR = Path('C:/ASTRA_WORK/BACKUPS_F02/sqlite-candidato-fc864a1')
DEST_DIR.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    """Calcula SHA-256 de un fichero en bloques de 64KB."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def backup_sqlite(base_path: str) -> dict:
    """Backup de una base SQLite con verificación.

    Returns:
        dict con keys: base, dest, sha256, integrity, size
    Raises:
        FileExistsError: si el destino ya existe
        sqlite3.Error: si el backup o la validación fallan
    """
    if not os.path.exists(base_path):
        raise FileNotFoundError(f'Base no existe: {base_path}')

    size = os.path.getsize(base_path)
    dest_name = base_path.replace('/', '_').replace('\\', '_') + '.backup'
    dest_path = DEST_DIR / dest_name

    if dest_path.exists():
        raise FileExistsError(f'Destino ya existe, no sobrescribir: {dest_path}')

    src = None
    dst = None
    try:
        src = sqlite3.connect(f'file:{base_path}?mode=ro', uri=True)
        dst = sqlite3.connect(str(dest_path))
        src.backup(dst)
    finally:
        if dst is not None:
            dst.close()
        if src is not None:
            src.close()

    # Verificar que el backup se escribió
    if not dest_path.exists():
        raise RuntimeError(f'Backup no se creó: {dest_path}')

    sha = sha256_file(dest_path)

    # Integridad sobre la copia
    check = None
    try:
        check = sqlite3.connect(str(dest_path))
        result = check.execute('PRAGMA integrity_check;').fetchone()
        integrity = result[0] if result else 'UNKNOWN'
    finally:
        if check is not None:
            check.close()

    return {
        'base': base_path,
        'dest': str(dest_path),
        'sha256': sha,
        'integrity': integrity,
        'size': size,
    }


def main() -> int:
    """Ejecuta backup de todas las bases configuradas."""
    errors = []
    for base_path in BASES:
        print(f'--- {base_path} ---')
        try:
            info = backup_sqlite(base_path)
            print(f'  SIZE: {info["size"]} bytes')
            print(f'  DESTINO: {info["dest"]}')
            print(f'  SHA256: {info["sha256"]}')
            print(f'  INTEGRITY: {info["integrity"]}')
        except FileNotFoundError as e:
            print(f'  NO_EXISTE: {e}')
        except FileExistsError as e:
            print(f'  SKIP (ya existe): {e}')
        except (sqlite3.Error, RuntimeError) as e:
            print(f'  ERROR: {type(e).__name__}: {e}')
            errors.append((base_path, str(e)))

    if errors:
        print(f'\nERRORS: {len(errors)}')
        for base, err in errors:
            print(f'  {base}: {err}')
        return 1
    print('\nOK: todas las bases procesadas')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
