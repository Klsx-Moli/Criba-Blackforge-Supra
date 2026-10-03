"""Which packages does each component's venv actually have?

The vertical slice needs PySide6 + httpx in the CRIBA venv and fastapi +
uvicorn in the SUPRA venv; this prints reality instead of guessing.
"""
from __future__ import annotations

import importlib
import sys

print("python:", sys.executable)
for name in ("PySide6", "httpx", "pytest", "fastapi", "uvicorn", "pydantic"):
    try:
        mod = importlib.import_module(name)
        print(f"  {name:10s} OK  {getattr(mod, '__version__', '')}")
    except Exception as exc:
        print(f"  {name:10s} MISSING  {type(exc).__name__}")