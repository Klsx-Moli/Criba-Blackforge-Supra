"""F35: shared model settings must not share an unsafe staging filename.

These tests never open Ollama, Hermes, a GGUF file, or the user's profile.
"""
from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

import criba.model_config as config
from criba.model_config import (
    ModelProfile,
    ModelSettings,
    default_model_settings,
    load_model_settings,
    save_model_settings,
)


def _settings(model: str) -> ModelSettings:
    profile = ModelProfile(id=f"profile-{model}", name=model, model=model)
    return ModelSettings(
        schema_version=1,
        enabled=True,
        active_profile_id=profile.id,
        profiles=[profile],
    )


def test_two_parallel_saves_use_distinct_temps_and_valid_final_json(
    tmp_path, monkeypatch,
) -> None:
    """Deterministically fail old shared models.json.tmp implementation.

    Both writers are stopped at os.replace. Old code used exactly one .tmp,
    so two successful replacements are impossible at this barrier.
    """
    destination = tmp_path / "models.json"
    original_replace = os.replace
    replace_gate = threading.Barrier(2, timeout=10)
    seen: list[str] = []
    seen_lock = threading.Lock()

    def synchronized_replace(source, target):
        with seen_lock:
            seen.append(str(source))
        replace_gate.wait()
        return original_replace(source, target)

    monkeypatch.setattr(config.os, "replace", synchronized_replace)
    with ThreadPoolExecutor(max_workers=2) as pool:
        completed = list(
            pool.map(
                lambda name: save_model_settings(_settings(name), destination),
                ("writer-a", "writer-b"),
            )
        )
    assert completed == [destination, destination]
    assert len(seen) == 2
    assert seen[0] != seen[1], "each writer must have its own temporary path"
    assert all(not (tmp_path / p).exists() for p in (".models.json.writer-a.tmp",))
    assert list(tmp_path.glob(".models.json.*.tmp")) == []

    raw = json.loads(destination.read_text(encoding="utf-8"))
    assert raw["enabled"] is True
    assert raw["active_profile_id"] in {"profile-writer-a", "profile-writer-b"}
    assert raw["profiles"][0]["id"] == raw["active_profile_id"]
    assert load_model_settings(destination).active_profile().model in {
        "writer-a", "writer-b"
    }


def test_failed_replace_keeps_previous_settings_and_cleans_only_own_temp(
    tmp_path, monkeypatch,
) -> None:
    destination = tmp_path / "models.json"
    save_model_settings(_settings("original"), destination)
    previous = destination.read_bytes()
    sentinel = tmp_path / ".models.json.other-writer.tmp"
    sentinel.write_bytes(b"must not delete another writer")

    def denied_replace(_source, _target):
        raise PermissionError("synthetic Windows locked target")

    monkeypatch.setattr(config.os, "replace", denied_replace)
    with pytest.raises(PermissionError, match="synthetic Windows"):
        save_model_settings(_settings("attempted"), destination)

    assert destination.read_bytes() == previous
    assert sentinel.read_bytes() == b"must not delete another writer"
    assert list(tmp_path.glob(".models.json.*.tmp")) == [sentinel]


def test_unserializable_profile_does_not_leave_a_temp_file(tmp_path) -> None:
    destination = tmp_path / "models.json"
    settings = default_model_settings()
    settings.profiles[0].model = object()  # type: ignore[assignment]
    with pytest.raises(TypeError):
        save_model_settings(settings, destination)
    assert not destination.exists()
    assert list(tmp_path.glob(".models.json.*.tmp")) == []


def test_writes_do_not_silently_replace_model_config_symlinks(
    tmp_path,
) -> None:
    target = tmp_path / "real.json"
    save_model_settings(_settings("original"), target)
    before = target.read_bytes()
    linked = tmp_path / "linked.json"
    try:
        linked.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("OS does not permit creating a symlink here")

    with pytest.raises(OSError, match="symlink"):
        save_model_settings(_settings("should-not-replace-link"), linked)
    assert linked.is_symlink()
    assert target.read_bytes() == before
