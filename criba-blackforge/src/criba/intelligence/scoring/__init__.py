"""IIE scoring techniques (T104 confidence, T111 feasibility, ...).

Package marker: the scoring modules here are IIE technique implementations that
feed the canonical MCDA consumer (`criba.mcda.score`). Without this file the
directory is only a namespace package, which some import mechanisms (and the
snapshot test runner) do not resolve.
"""
from __future__ import annotations

__all__: list[str] = []
