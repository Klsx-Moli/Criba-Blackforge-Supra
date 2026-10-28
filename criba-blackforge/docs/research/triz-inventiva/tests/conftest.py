"""conftest para las pruebas aisladas de la campaña TRIZ+Koestler.

Añade al sys.path los directorios de la campaña para que los imports
`fixtures.fixtures` y `validator.validador` resuelvan sin instalar nada.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]  # docs/research/triz-inventiva

# La raiz de la campaña debe estar en el path para que `fixtures.fixtures`
# y `validator.validador` resuelvan como paquetes.
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
