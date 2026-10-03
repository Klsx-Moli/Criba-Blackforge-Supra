"""Fix the class-body indentation of list_projects_with_errors in state.py.

Same repair as the get_project block: the patch tool emitted the signature
continuation and the whole body four spaces too deep. Dedents exactly lines
542..603 (1-indexed, inclusive) and asserts the module still parses.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

TARGET = Path(sys.argv[1])
START, END = 542, 603

lines = TARGET.read_text(encoding="utf-8").splitlines(keepends=True)
assert len(lines) >= END, f"file too short: {len(lines)} lines"
assert lines[START - 1].strip() == "self, limit: int = 50", repr(lines[START - 1])
assert lines[END - 1].rstrip().endswith(
    "return project_snapshot, [dict(item) for item in load_errors]"
), repr(lines[END - 1])

fixed = list(lines)
for index in range(START - 1, END):
    line = fixed[index]
    if line.strip():
        assert line.startswith("    "), f"line {index + 1} cannot be dedented: {line!r}"
        fixed[index] = line[4:]

TARGET.write_text("".join(fixed), encoding="utf-8")
ast.parse(TARGET.read_text(encoding="utf-8"))
print(f"OK {TARGET.name}: dedented lines {START}..{END}, module parses")