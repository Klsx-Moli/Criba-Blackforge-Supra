"""M1 sentinel: no shadow.* key may render raw in the Shadow UI.

Regression reproduced on 2026-10-02 while migrating Shadow UI into the
monorepo. The migration first copied only the 20 shadow.* keys that a literal
`_t("shadow.*")` grep could see, and the live window still rendered 36 raw
keys, because the window also references keys through indirection that no
literal scan sees. The window is the only place that proves this, so both a
static and a live assertion are required.

Mutation sentinel: delete any single shadow.* entry from _STRINGS and the live
test below goes red. Rename a key in shadow_window.py and the static test goes
red.
"""

from __future__ import annotations

import pathlib
import re

import pytest
from criba.ui import i18n

SHADOW_UI = pathlib.Path(__file__).resolve().parents[2] / "shadow_ui"
_LITERAL = re.compile(r'(?:_t|bind_text|bind_placeholder|bind_glyph)\(\s*[\'"]([A-Za-z0-9_.]+)[\'"]')


def _tables() -> dict[str, dict]:
    return dict(i18n._STRINGS.items())


@pytest.mark.parametrize("lang", ["es", "en"])
def test_every_literal_shadow_key_exists_in_both_languages(lang: str) -> None:
    tables = _tables()
    referenced = {
        key
        for name in ("shadow_window.py", "shadow_context.py")
        if (SHADOW_UI / name).exists()
        for key in _LITERAL.findall((SHADOW_UI / name).read_text(encoding="utf-8"))
    }
    assert referenced, "no shadow.* keys found; the scanner itself is broken"
    for other, table in tables.items():
        missing = sorted(key for key in referenced if key not in table)
        assert not missing, f"{lang} scan: keys missing from {other}: {missing}"


@pytest.mark.parametrize("lang", ["es", "en"])
def test_both_languages_define_the_same_shadow_keys(lang: str) -> None:
    tables = _tables()
    shadow_sets = {
        other: {k for k in table if isinstance(k, str) and k.startswith("shadow.")}
        for other, table in tables.items()
    }
    assert len(shadow_sets) >= 2, "expected at least ES and EN"
    reference = next(iter(shadow_sets.values()))
    for other, keys in shadow_sets.items():
        assert keys == reference, f"{lang}: shadow.* set differs in {other}"


def test_shadow_keys_are_not_empty() -> None:
    """A key that exists but is blank renders as nothing, which is worse."""
    for lang, table in _tables().items():
        blank = sorted(
            key for key, value in table.items()
            if isinstance(key, str) and key.startswith("shadow.") and not str(value).strip()
        )
        assert not blank, f"{lang}: blank shadow.* values: {blank}"


def test_shadow_window_reports_no_raw_key_when_rendered() -> None:
    """Live assertion: construct the real window and read what it actually shows."""
    qapp = pytest.importorskip("PySide6.QtWidgets")
    import os
    import sys

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    repo_src = pathlib.Path(__file__).resolve().parents[2] / "src"
    for path in (str(SHADOW_UI), str(repo_src)):
        if path not in sys.path:
            sys.path.insert(0, path)

    app = qapp.QApplication.instance() or qapp.QApplication(sys.argv)
    from shadow_window import ShadowWindow

    window = ShadowWindow()
    window.show()
    app.processEvents()
    try:
        raw: set[str] = set()
        for widget in window.findChildren(object):
            for attr in ("text", "placeholderText", "toolTip"):
                try:
                    value = getattr(widget, attr)()
                except Exception:
                    continue
                if isinstance(value, str) and value.startswith("shadow."):
                    raw.add(value)
        assert not raw, f"raw i18n keys rendered in the live window: {sorted(raw)}"
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()