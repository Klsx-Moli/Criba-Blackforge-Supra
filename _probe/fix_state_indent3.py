"""Dedent exactly lines 594..598 of state.py.

The patch tool keeps emitting the replacement body deeper than the enclosing
``for``/``with`` blocks. This normalises that one range and asserts the module
parses afterwards.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

TARGET = Path(sys.argv[1])
START, END = 594, 598

lines = TARGET.read_text(encoding="utf-8").splitlines(keepends=True)
assert lines[START - 1].strip() == 'if (self.storage_dir / f"{pid}.json").exists():', repr(
    lines[START - 1]
)
assert lines[END - 1].strip().endswith(')'), repr(lines[END - 1])

fixed = list(lines)
for index in range(START - 1, END):
    fixed[index] = "    " + fixed[index].lstrip()

TARGET.write_text("".join(fixed), encoding="utf-8")
ast.parse(TARGET.read_text(encoding="utf-8"))
print(f"OK {TARGET.name}: normalized lines {START}..{END}, module parses")