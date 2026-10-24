"""Shared pytest config for the retrybox pilot fixture.

Ensures the `retrybox` package (under participant_repo/src) is importable
for both participant_repo/tests and evaluator/ without polluting the
production test suite.
"""
import sys
from pathlib import Path

_PARTICIPANT_SRC = Path(__file__).parent / "participant_repo" / "src"
_src = str(_PARTICIPANT_SRC.resolve())
if _src not in sys.path:
    sys.path.insert(0, _src)
