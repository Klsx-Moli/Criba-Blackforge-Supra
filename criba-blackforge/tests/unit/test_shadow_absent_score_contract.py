"""Shadow ranking: absent value is not a measurement.

`_build_ranking_rows` must surface `value_score=None` when an idea carries no
convergence, instead of defaulting to 0.0 (which would render as a measurement of
zero). The gauge must distinguish that state visually from a real 0.0.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from criba.ui.actions import _build_ranking_rows
from criba.ui.widgets import ValueScoreGauge


def _packet(*ideas: dict) -> dict:
    return {"innovation": {"ideas": list(ideas)}}


def test_idea_without_convergence_reports_absent_score() -> None:
    rows = _build_ranking_rows(_packet(
        {"id": "i1", "title": "T", "description": "D", "convergence": {}}
    ))
    assert rows[0]["value_score"] is None, "ausencia no debe convertirse en 0.0"
    assert rows[0]["evaluada"] is False


def test_idea_with_convergence_reports_real_score() -> None:
    rows = _build_ranking_rows(_packet(
        {"id": "i1", "title": "T", "description": "D",
         "convergence": {"value_score": 0.181, "novelty": 0.4333}}
    ))
    assert rows[0]["value_score"] == 0.181
    assert rows[0]["convergencia"] == 0.4333
    assert rows[0]["evaluada"] is True


def test_zero_score_is_preserved_as_a_measurement() -> None:
    """A real 0.0 must survive: it is a measurement, not absence."""
    rows = _build_ranking_rows(_packet(
        {"id": "i1", "title": "T", "description": "D",
         "convergence": {"value_score": 0.0, "novelty": 0.0}}
    ))
    assert rows[0]["value_score"] == 0.0
    assert rows[0]["evaluada"] is True


def test_missing_convergence_key_is_absent_not_zero() -> None:
    rows = _build_ranking_rows(_packet({"id": "i1", "title": "T", "description": "D"}))
    assert rows[0]["value_score"] is None


def test_gauge_distinguishes_absent_from_zero(qapp) -> None:
    gauge = ValueScoreGauge()
    gauge.set_score(None)
    assert gauge._no_value is True
    gauge.set_score(0.0)
    assert gauge._no_value is False
    gauge.set_score(0.5)
    assert gauge._no_value is False


def test_gauge_renders_without_error_when_absent(qapp) -> None:
    """The paint path must not crash on the absent state."""
    gauge = ValueScoreGauge()
    gauge.set_score(None)
    gauge.resize(200, 200)
    gauge.repaint()
    assert gauge._no_value is True
