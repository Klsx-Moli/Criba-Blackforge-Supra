"""conftest del laboratorio IMP-09.

Añade docs/research/triz-inventiva al sys.path para que `validator.validador`
resuelva como paquete, sin tocar el pythonpath de runtime (pyproject.toml).
Aislado: solo afecta a la colección de este directorio de laboratorio.
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
# imp09_pilot_protocol/tests -> imp09_pilot_protocol -> triz-inventiva
_ROOT = _HERE.parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
