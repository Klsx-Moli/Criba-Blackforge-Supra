"""A callback deadline must fire before the enclosing canonical pytest deadline."""

import ast
from pathlib import Path


def test_callback_guard_fits_inside_sixty_second_pytest_deadline():
    source = Path(__file__).resolve().parents[1] / "integration/test_m2_vertical_slice_e2e.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "QTestClick")
    timers = [
        node.args[0].value
        for node in ast.walk(helper)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "singleShot"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    ]
    assert timers and max(timers) < 60_000
