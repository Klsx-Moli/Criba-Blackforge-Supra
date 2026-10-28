"""conftest del laboratorio IMP-05.

Expone el directorio padre (docs/research/triz-inventiva) en sys.path para que
`import lab...` resuelva sin tocar el pythonpath de runtime (pyproject.toml).
Aislado: solo afecta a la colección de este directorio de laboratorio.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))
