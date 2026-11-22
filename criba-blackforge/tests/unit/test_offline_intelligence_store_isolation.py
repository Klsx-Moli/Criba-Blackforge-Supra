"""F34: pytest must never open the user's production intelligence DB."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from criba.intelligence.refresh import default_store


@pytest.mark.parametrize("_case", [1, 2])
def test_default_intelligence_store_is_inside_unique_pytest_tmp_path(
    tmp_path: Path, _case: int,
) -> None:
    # Autouse fixture from tests/conftest.py must run before the first access.
    base = tmp_path / "isolated-appdata"
    assert os.environ.get("LOCALAPPDATA") == str(base)
    expected = base / "CRIBA-Blackforge" / "intelligence.sqlite3"
    assert not expected.exists()
    store = default_store()
    assert store is not None, "test store must be writable, not silently None"
    try:
        assert store.path == expected
        assert expected.is_relative_to(tmp_path)
        assert expected.is_file()
    finally:
        store.close()


def test_model_and_intelligence_settings_both_isolated(tmp_path: Path) -> None:
    from criba.model_config import model_config_path

    assert model_config_path() == tmp_path / "isolated-model-settings.json"
    assert Path(os.environ["LOCALAPPDATA"]) == tmp_path / "isolated-appdata"
