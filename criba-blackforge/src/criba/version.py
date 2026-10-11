"""Version from distribution metadata, shared by all public transports."""

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _version() -> str:
    try:
        return version("criba")
    except PackageNotFoundError:
        # A source checkout may be used before installation.
        project = Path(__file__).resolve().parents[2] / "pyproject.toml"
        try:
            with project.open("rb") as stream:
                value = tomllib.load(stream)["project"]["version"]
            return value if isinstance(value, str) else "0+unknown"
        except (OSError, KeyError, ValueError, TypeError):
            return "0+unknown"


__version__ = _version()
