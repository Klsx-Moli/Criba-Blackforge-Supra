"""ASTRA-031 sentinel: algorithmic names never overclaim implementation."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_astra_031_pareto_and_map_elites_are_explicitly_heuristic():
    text = (
        ROOT / "src" / "criba" / "blackforge_orthogonal" / "compositor.py"
    ).read_text(encoding="utf-8")
    assert "no calcula un frente Pareto real" in text
    assert "no implementa MAP-Elites completo" in text
    assert "not full MAP-Elites" in text
