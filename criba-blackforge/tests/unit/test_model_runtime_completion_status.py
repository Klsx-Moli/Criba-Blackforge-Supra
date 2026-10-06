"""Completion metadata is authoritative even if the visible JSON looks valid."""

from __future__ import annotations

import json

import pytest
from criba import model_runtime
from criba.model_config import ModelProfile, ModelSettings


@pytest.mark.parametrize("backend", ["llama_cpp", "ollama"])
def test_truncated_completion_is_rejected_before_json_validation(monkeypatch, backend):
    # A closed JSON prefix can remain after output truncation. Parsing that
    # prefix must not erase the backend's explicit incompleteness metadata.
    complete_prefix = json.dumps({"ideas": [{
        "candidate_id": "I01", "title": "Revisión recuperable",
        "description": "Conserva el intento original y contrasta el resultado persistido.",
        "mechanism": "La identidad persistida evita confundir intentos diferentes.",
        "experiment": "Reentrega el mismo episodio y cuenta los efectos durables.",
    }]})
    response = (
        {"choices": [{"finish_reason": "length", "message": {"content": complete_prefix}}]}
        if backend == "llama_cpp"
        else {"done_reason": "length", "message": {"content": complete_prefix}}
    )
    monkeypatch.setattr(model_runtime, "_http_json", lambda *a, **kw: response)
    profile = ModelProfile(backend=backend, max_output_tokens=2048)
    with pytest.raises(model_runtime.ModelRuntimeError, match="truncada.*2048"):
        model_runtime._generate_once(profile, "system", "public prompt")


@pytest.mark.parametrize("backend", ["llama_cpp", "ollama"])
@pytest.mark.parametrize("reason", ["stop", None])
def test_completed_or_legacy_response_remains_accepted(monkeypatch, backend, reason):
    response = (
        {"choices": [{"finish_reason": reason, "message": {"content": '{"ideas": []}'}}]}
        if backend == "llama_cpp"
        else {"done_reason": reason, "message": {"content": '{"ideas": []}'}}
    )
    monkeypatch.setattr(model_runtime, "_http_json", lambda *a, **kw: response)
    actual = model_runtime._generate_once(ModelProfile(backend=backend), "system", "prompt")
    assert actual == '{"ideas": []}'


def test_truncation_preserves_deterministic_candidates_and_explains_limit(monkeypatch):
    profile = ModelProfile(max_output_tokens=2048)
    settings = ModelSettings(enabled=True, active_profile_id=profile.id, profiles=[profile])
    monkeypatch.setattr(model_runtime, "ensure_profile_available", lambda *a, **kw: None)
    monkeypatch.setattr(model_runtime, "_http_json", lambda *a, **kw: {
        "choices": [{"finish_reason": "length", "message": {"content": None}}],
    })
    original = [{
        "id": "I01", "title": "Candidato original",
        "description": "Sin evidencia ejecutada",
    }]
    actual, metadata = model_runtime.enhance_ideas_with_model(
        "Recuperar la identidad del intento", original, product="CRIBA", settings=settings,
    )
    assert actual == original
    assert metadata["status"] == "fallback"
    assert "truncada" in metadata["error"] and "2048" in metadata["error"]
    assert "semantic_source" not in actual[0]
