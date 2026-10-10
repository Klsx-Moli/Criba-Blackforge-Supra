"""Regression: the GUI wrapper must not promote runtime outcomes to success."""
from copy import deepcopy

import pytest
from criba import model_runtime
from criba.model_config import ModelSettings
from criba.ui.actions import _enhance_packet_async


def test_disabled_runtime_is_not_promoted_by_wrapper(monkeypatch):
    monkeypatch.setattr(model_runtime, "load_model_settings", lambda: ModelSettings(enabled=False))
    packet = {
        "original_query": "Save water",
        "innovation": {
            "ideas": [
                {"id": "I1", "title": "Original", "convergence": {"value_score": 0.7}}
            ]
        },
        "semantic_generation": {"status": "pending"},
    }
    original = deepcopy(packet["innovation"]["ideas"])
    _enhance_packet_async(packet)
    assert packet["semantic_generation"]["status"] == "disabled"
    assert packet["innovation"]["ideas"] == original


@pytest.mark.parametrize("status", ["fallback", "partial", "disabled", "ok"])
def test_wrapper_preserves_runtime_metadata(monkeypatch, status):
    metadata = {"status": status, "backend": "test", "error": "original cause", "enhanced_count": 0}
    def enhance(packet):
        packet["semantic_generation"] = deepcopy(metadata)
        return packet
    monkeypatch.setattr(model_runtime, "enhance_criba_packet", enhance)
    packet = {"semantic_generation": {"status": "pending"}}
    _enhance_packet_async(packet)
    assert packet["semantic_generation"] == metadata
