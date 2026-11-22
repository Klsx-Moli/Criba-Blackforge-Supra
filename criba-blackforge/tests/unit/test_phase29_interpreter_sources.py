"""F29 source discovery: no cloud calls, token reading or inference."""
from __future__ import annotations

import pytest

from criba import interpreter_sources as sources


@pytest.mark.parametrize("source", ["hermes", "opencode", "ollama"])
def test_supported_sources_are_exact_pinned_local_urls(source):
    assert sources._URLS[source].startswith("http://127.0.0.1:")
    assert "@" not in sources._URLS[source]
    assert "?" not in sources._URLS[source]


def test_hermes_catalog_no_stale_free_price_or_token(monkeypatch):
    monkeypatch.setattr(
        sources, "_get_local_json",
        lambda source: {"data": [
            {"id": "provider/model", "pricing": {"prompt": 0}},
            {"id": "provider/model"},
            {"id": "laguna-retired"},
        ]},
    )
    catalog = sources.discover_models("hermes")
    assert [e.model_id for e in catalog.models] == [
        "provider/model", "laguna-retired"
    ]
    assert all(e.source == "hermes" for e in catalog.models)
    assert "NO verificados" in catalog.note
    assert not any("free" in e.model_id for e in catalog.models)


def test_opencode_connected_is_only_reported_catalog_status(monkeypatch):
    monkeypatch.setattr(
        sources, "_get_local_json", lambda source: {
            "connected": ["provider-a"],
            "all": [
                {"id": "provider-a", "models": {"model-x": {}, "model-y": {}}},
                {"id": "provider-b", "models": {"model-z": {}}},
            ],
        },
    )
    result = sources.discover_models("opencode")
    assert [(m.provider, m.model_id, m.connected_reported)
            for m in result.models] == [
                ("provider-a", "model-x", True),
                ("provider-a", "model-y", True),
                ("provider-b", "model-z", False),
            ]
    assert "no tiene adaptador" in result.note


def test_ollama_only_uses_name_or_model_and_deduplicates(monkeypatch):
    monkeypatch.setattr(
        sources, "_get_local_json", lambda source: {
            "models": [
                {"name": "qwen:8b"},
                {"model": "qwen:8b"},
                {"name": "llama:3b"},
                {"name": 123},
                None,
            ]
        },
    )
    assert [m.model_id for m in sources.discover_models("ollama").models] == [
        "qwen:8b", "llama:3b"
    ]


@pytest.mark.parametrize(
    ("source", "payload"),
    [
        ("hermes", {}),
        ("hermes", {"data": 4}),
        ("ollama", {"models": {}}),
        ("opencode", {"all": [], "connected": "one"}),
        ("opencode", {"all": {}}),
    ],
)
def test_malformed_catalog_does_not_fabricate_models(monkeypatch, source, payload):
    monkeypatch.setattr(sources, "_get_local_json", lambda _source: payload)
    with pytest.raises(ValueError):
        sources.discover_models(source)


@pytest.mark.parametrize("raw", [
    b'{"data":[],"data":[]}',
    b'{"data":[NaN]}',
    b'{"models":[Infinity]}',
])
def test_ambiguous_json_fails_closed(raw):
    with pytest.raises(ValueError):
        sources._strict_json(raw)


def test_unexpected_provider_never_opens_url(monkeypatch):
    monkeypatch.setattr(
        sources, "_get_local_json",
        lambda _: pytest.fail("no HTTP for unknown provider"),
    )
    with pytest.raises(ValueError, match="unsupported"):
        sources.discover_models("https://evil.invalid")


def test_catalog_limits_and_control_characters(monkeypatch):
    monkeypatch.setattr(
        sources, "_get_local_json", lambda source: {
            "data": [{"id": f"model-{i}"} for i in range(3000)]
            + [{"id": "bad\nmodel"}, {"id": " "}, {"id": 4}],
        },
    )
    assert len(sources.discover_models("hermes").models) <= sources._MAX_MODELS


def test_invalid_get_never_leaks_upstream_message(monkeypatch):
    def broken(_source):
        raise ValueError("secret-upstream-credential-abc123")
    monkeypatch.setattr(sources, "_get_local_json", broken)
    with pytest.raises(ValueError) as exc:
        sources.discover_models("hermes")
    assert "secret-upstream" not in str(exc.value)
