from __future__ import annotations

import json

from criba.model_config import (
    ModelProfile,
    ModelSettings,
    active_model_label,
    load_model_settings,
    load_model_settings_bytes,
    model_config_path,
    save_model_settings,
)


def test_model_settings_round_trip_without_secrets(tmp_path, monkeypatch) -> None:
    target = tmp_path / "models.json"
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(target))
    profile = ModelProfile(
        name="Qwen local",
        gguf_path=str(tmp_path / "qwen.gguf"),
        server_path=str(tmp_path / "llama-server.exe"),
        reasoning="deep",
        timeout=120.0,
        parallel_slots=2,
    )
    settings = ModelSettings(
        enabled=True,
        active_profile_id=profile.id,
        profiles=[profile],
    )

    assert model_config_path() == target
    assert save_model_settings(settings) == target
    loaded = load_model_settings()
    assert loaded.enabled
    assert loaded.active_profile() is not None
    assert loaded.active_profile().name == "Qwen local"  # type: ignore[union-attr]
    assert loaded.active_profile().reasoning == "deep"  # type: ignore[union-attr]
    assert loaded.active_profile().timeout == 120.0  # type: ignore[union-attr]
    assert loaded.active_profile().parallel_slots == 2  # type: ignore[union-attr]
    assert "api_key" not in target.read_text(encoding="utf-8")
    assert active_model_label(loaded) == "Qwen local · deep"


def test_malformed_settings_fail_closed_to_deterministic(tmp_path) -> None:
    target = tmp_path / "broken.json"
    target.write_text(
        json.dumps({"enabled": True, "profiles": "bad"}), encoding="utf-8"
    )

    loaded = load_model_settings(target)
    assert not loaded.enabled
    assert loaded.active_profile() is not None
    assert active_model_label(loaded) == "Determinista"


def test_profile_values_are_bounded_and_wrong_json_types_do_not_escape(
    tmp_path,
) -> None:
    target = tmp_path / "hostile.json"
    target.write_text(
        json.dumps(
            {
                "enabled": "true",
                "profiles": [
                    {
                        "id": [],
                        "name": {"unexpected": "container"},
                        "endpoint": None,
                        "model": ["not", "text"],
                        "auto_start": "false",
                        "context_size": 999_999,
                        "gpu_layers": -4,
                        "temperature": "NaN",
                        "max_output_tokens": "invalid",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    loaded = load_model_settings(target)
    profile = loaded.active_profile()

    assert not loaded.enabled
    assert profile is not None
    assert profile.name == "Modelo GGUF local"
    assert profile.endpoint == "http://127.0.0.1:8080"
    assert profile.model == "criba-local"
    assert profile.auto_start is True
    assert profile.context_size == 131_072
    assert profile.gpu_layers == -1
    assert profile.temperature == 0.45
    assert profile.max_output_tokens == 2400


def test_duplicate_profile_ids_are_repaired(tmp_path) -> None:
    target = tmp_path / "duplicates.json"
    target.write_text(
        json.dumps(
            {
                "enabled": True,
                "active_profile_id": "same",
                "profiles": [
                    {"id": "same", "name": "Primero"},
                    {"id": "same", "name": "Segundo"},
                ],
            }
        ),
        encoding="utf-8",
    )

    loaded = load_model_settings(target)

    assert [profile.name for profile in loaded.profiles] == ["Primero", "Segundo"]
    assert len({profile.id for profile in loaded.profiles}) == 2
    assert loaded.active_profile() is loaded.profiles[0]


def test_model_settings_snapshot_decoder_matches_file_reader_without_reopening(
    tmp_path, monkeypatch,
) -> None:
    target = tmp_path / "models.json"
    settings = ModelSettings(
        enabled=True,
        profiles=[ModelProfile(
            id="snapshot-stable", model="local:latest",
            name="Snapshot name", temperature=0.0,
        )],
        active_profile_id="snapshot-stable",
    )
    save_model_settings(settings, target)
    captured = target.read_bytes()
    expected = load_model_settings(target).to_dict()

    # The exact captured bytes remain usable after the path vanishes.
    target.unlink()
    assert load_model_settings_bytes(captured).to_dict() == expected
    assert load_model_settings(target).enabled is False


def test_model_settings_snapshot_reader_is_tolerant_only_for_reads() -> None:
    for invalid in (b"not-json", b"\xff", b"[]", b'{"profiles": []}'):
        result = load_model_settings_bytes(invalid)
        assert not result.enabled
        assert result.active_profile() is not None
    assert not load_model_settings_bytes(None).enabled
