"""Public version surfaces must stay aligned with package metadata."""

from __future__ import annotations

import tomllib
from pathlib import Path

import criba
from criba.api import Handler, create_app


def test_public_version_surfaces_match_project_metadata() -> None:
    root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["version"] == criba.__version__
    assert Handler.server_version == f"CRIBA/{criba.__version__}"
    assert create_app().version == criba.__version__
