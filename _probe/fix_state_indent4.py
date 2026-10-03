"""Rewrite lines 594..598 of state.py at the correct class-body indentation.

Validates BEFORE writing this time, so a failed assertion cannot leave the
module unparseable.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

TARGET = Path(sys.argv[1])
START, END = 594, 598

REPLACEMENT = [
    '                if (self.storage_dir / f"{pid}.json").exists():\n',
    "                    continue\n",
    "                load_errors.append(\n",
    '                    {"project_id": pid, "error": "PERSISTED_ARTIFACT_MISSING"}\n',
    "                )\n",
]

lines = TARGET.read_text(encoding="utf-8").splitlines(keepends=True)
assert lines[START - 1].lstrip().startswith("if (self.storage_dir"), repr(lines[START - 1])
assert lines[END - 1].strip() == ")", repr(lines[END - 1])
assert len(REPLACEMENT) == END - START + 1, (len(REPLACEMENT), END - START + 1)

candidate = lines[: START - 1] + REPLACEMENT + lines[END:]
text = "".join(candidate)
ast.parse(text)  # validate BEFORE touching the file
TARGET.write_text(text, encoding="utf-8")
print(f"OK {TARGET.name}: rewrote lines {START}..{END} at class indentation, module parses")