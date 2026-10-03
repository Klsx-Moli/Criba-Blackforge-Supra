"""Fix the class-body indentation of the get_project block in state.py.

The M3 edit landed the method bodies at 12 spaces while the enclosing ``def``
sits at 4, so the module no longer parses. This dedents exactly lines
137..209 (1-indexed, inclusive) by four spaces and asserts that the result
parses, so the repair cannot silently touch anything else.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

TARGET = Path(sys.argv[1])
START, END = 137, 209

lines = TARGET.read_text(encoding="utf-8").splitlines(keepends=True)
assert len(lines) >= END, f"file too short: {len(lines)} lines"
assert lines[START - 1].lstrip().startswith('"""Retrieve a project state by ID.'), repr(
    lines[START - 1]
)
assert lines[END - 1].rstrip().endswith("else ARTIFACT_DIVERGES"), repr(lines[END - 1])

fixed = list(lines)
for index in range(START - 1, END):
    line = fixed[index]
    if line.strip():
        assert line.startswith("    "), f"line {index + 1} cannot be dedented: {line!r}"
        fixed[index] = line[4:]

TARGET.write_text("".join(fixed), encoding="utf-8")
ast.parse(TARGET.read_text(encoding="utf-8"))
print(f"OK {TARGET.name}: dedented lines {START}..{END}, module parses")