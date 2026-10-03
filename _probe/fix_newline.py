"""Append the missing trailing newline flagged by ruff W292."""
from __future__ import annotations

import sys
from pathlib import Path

target = Path(sys.argv[1])
text = target.read_text(encoding="utf-8")
if not text.endswith("\n"):
    target.write_text(text + "\n", encoding="utf-8")
    print(f"OK {target.name}: trailing newline added")
else:
    print(f"OK {target.name}: already ends with a newline")