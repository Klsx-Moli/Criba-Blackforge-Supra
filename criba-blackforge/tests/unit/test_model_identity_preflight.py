"""Host captures are metadata, not provider authentication (no live models)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from benchmarks.innovation import model_identity_preflight as identity


def inputs(tmp_path):
    # Tiny synthetic file checks IO and hashing, not a loadable GGUF model.
    chosen = tmp_path / "selected.gguf"
    chosen.write_bytes(b"GGUFsynthetic-A")
    profile = {"id": "p", "backend": "llama_cpp", "model": "criba-local",
               "endpoint": "http://127.0.0.1:8080", "gguf_path": str(chosen)}
    config = {"schema_version": 1, "enabled": True, "active_profile_id": "p",
              "profiles": [profile]}
    capture = {"route": "local_llama", "effective_endpoint": "http://127.0.0.1:8080/v1",
               "effective_model": "criba-local", "models": {"data": [{"id": "criba-local"}]},
               "props": {"model_path": str(chosen), "model_alias": "criba-local",
                         "build_info": "fixture-1", "is_sleeping": False}}
    return chosen, config, capture


def assert_unverified(actual):
    assert actual["loaded_file_identity"] == "NOT_VERIFIED"
    assert actual["authorization"] == "NOT_GRANTED"
    assert actual["source"] == "HOST_CAPTURE_ONLY"


def test_matching_path_and_explicit_file_hash_are_different_claims(tmp_path):
    path, config, capture = inputs(tmp_path)
    light = identity.assess(config, capture)
    assert light["status"] == "REPORTED_PATH_MATCH"
    assert light["file_sha256"] is None
    full = identity.assess(config, capture, hash_file=True)
    assert full["file_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert full["status"] == light["status"]
    assert full["response_model"] == "NOT_OBSERVED"
    assert_unverified(full)
    assert_unverified(light)


def test_same_alias_other_gguf_does_not_open_untrusted_path(tmp_path, monkeypatch):
    chosen, config, capture = inputs(tmp_path)
    other = chosen.with_name("different.gguf")
    other.write_bytes(b"GGUFsynthetic-A")  # even identical bytes do not prove same load
    capture["props"]["model_path"] = str(other)
    def forbidden(*args):
        raise AssertionError("must not read a server-supplied path")
    monkeypatch.setattr(identity, "_local_file", forbidden)
    actual = identity.assess(config, capture)
    assert (actual["status"], actual["reason"]) == ("BLOCKED", "reported_path_differs")
    assert_unverified(actual)


@pytest.mark.parametrize("patch,reason", [
    ({"enabled": False}, "local_model_disabled"),
    ({"enabled": 1}, "local_model_disabled"),
    ({"schema_version": 2}, "unsupported_config_schema"),
    ({"schema_version": True}, "unsupported_config_schema"),
    ({"active_profile_id": "missing"}, "ambiguous_or_missing_active_profile"),
    ({"active_profile_id": ""}, "invalid_selection"),
    ({"profiles": [None]}, "invalid_profiles"),
])
def test_corrupt_and_stale_selection_never_falls_back(tmp_path, patch, reason):
    _, config, capture = inputs(tmp_path)
    actual = identity.assess({**config, **patch}, capture)
    assert actual["status"] == "BLOCKED"
    assert actual["reason"] == reason
    assert_unverified(actual)


def test_duplicate_ids_not_silently_reassigned(tmp_path):
    _, config, capture = inputs(tmp_path)
    config["profiles"].append({**config["profiles"][0], "model": "other"})
    assert identity.assess(config, capture)["reason"] == "ambiguous_or_missing_active_profile"


@pytest.mark.parametrize("field,value,reason", [
    ("effective_model", "other-model", "effective_model_mismatch"),
    ("effective_model", None, "effective_model_mismatch"),
    ("effective_endpoint", "http://127.0.0.1:8081/v1", "effective_endpoint_mismatch"),
    ("effective_endpoint", "http://127.0.0.1/v1", "effective_endpoint_mismatch"),
    ("effective_endpoint", "http://127.0.0.1:0/v1", "invalid_endpoint"),
    ("effective_endpoint", "http://127.0.0.1:8080/v1?x=1", "invalid_endpoint"),
    ("effective_endpoint", "http://user:secret@127.0.0.1:8080/v1", "invalid_endpoint"),
    ("effective_endpoint", "http://127.0.0.1:8080\n/v1", "invalid_endpoint"),
    ("effective_endpoint", "http://example.com:8080/v1", "invalid_endpoint"),
    ("effective_endpoint", "http://127.0.0.1:8080/wrong/v1", "invalid_endpoint"),
    ("route", "external", "incompatible_backend_or_route"),
    ("response_model", "other", "response_model_mismatch"),
    ("response_model", None, "response_model_mismatch"),
])
def test_effective_route_not_selected_label(tmp_path, field, value, reason):
    _, config, capture = inputs(tmp_path)
    actual = identity.assess(config, {**capture, field: value})
    assert actual["status"] == "BLOCKED" and actual["reason"] == reason
    assert_unverified(actual)
    assert "secret" not in json.dumps(actual)


@pytest.mark.parametrize("models,status,reason", [
    ({"data": [{"id": "other"}]}, "BLOCKED", "absent_or_ambiguous_alias"),
    ({"data": [{"id": "criba-local"}, {"id": "criba-local"}]},
     "BLOCKED", "absent_or_ambiguous_alias"),
    ({"data": [{"id": "criba-local"}, {"id": "other"}]},
     "UNKNOWN", "multi_model_catalog_requires_routed_evidence"),
    ({"data": [{"id": "criba-local"}, None]}, "UNKNOWN", "invalid_catalog"),
    ({"data": [{"id": " criba-local "}]}, "UNKNOWN", "invalid_catalog"),
    ({"data": []}, "UNKNOWN", "missing_catalog"),
    ({"data": {}}, "UNKNOWN", "missing_catalog"),
])
def test_catalog_does_not_prove_loaded_model(tmp_path, models, status, reason):
    _, config, capture = inputs(tmp_path)
    actual = identity.assess(config, {**capture, "models": models})
    assert actual["status"] == status and actual["reason"] == reason
    assert_unverified(actual)


@pytest.mark.parametrize("props,reason", [
    (None, "missing_model_path"), ({}, "missing_model_path"),
    ({"model_path": "relative.gguf"}, "path_not_comparable_on_this_host"),
    ({"model_path": "//server/share/model.gguf"}, "path_not_comparable_on_this_host"),
    ({"model_path": r"\\server\share\model.gguf"}, "path_not_comparable_on_this_host"),
    ({"model_path": ["/model.gguf"]}, "path_not_comparable_on_this_host"),
    ({"model_path": "/folder/../model.gguf"}, "path_not_comparable_on_this_host"),
    ({"model_path": "/bad\x00.gguf"}, "path_not_comparable_on_this_host"),
])
def test_props_absent_or_untrusted_path_is_unknown(tmp_path, props, reason):
    _, config, capture = inputs(tmp_path)
    actual = identity.assess(config, {**capture, "props": props})
    assert actual["status"] == "UNKNOWN" and actual["reason"] == reason
    assert_unverified(actual)


@pytest.mark.parametrize("field,value,reason", [
    ("model_alias", "other", "props_alias_mismatch"),
    ("is_sleeping", True, "runtime_sleeping_or_state_unknown"),
    ("is_sleeping", "false", "runtime_sleeping_or_state_unknown"),
    ("build_info", {}, "invalid_build_info"),
])
def test_matching_filepath_not_enough_for_contradictory_props(tmp_path, field, value, reason):
    _, config, capture = inputs(tmp_path)
    capture["props"][field] = value
    actual = identity.assess(config, capture)
    assert actual["reason"] == reason and actual["status"] != "REPORTED_PATH_MATCH"


@pytest.mark.parametrize("kind", ["missing", "directory", "not-gguf"])
def test_local_selected_file_checked_not_just_path(tmp_path, kind):
    path, config, capture = inputs(tmp_path)
    path.unlink()
    if kind == "directory":
        path.mkdir()
    if kind == "not-gguf":
        path.write_bytes(b"not a model")
    actual = identity.assess(config, capture)
    assert actual["status"] == "UNKNOWN"
    assert actual["reason"] == "local_file_unavailable_or_changed"


def test_file_replaced_during_read_is_unknown(tmp_path, monkeypatch):
    path, config, capture = inputs(tmp_path)
    old_stat = Path.stat
    reads = 0
    def changing_stat(self, *args, **kwargs):
        nonlocal reads
        if self == path:
            reads += 1
            if reads == 2:
                path.write_bytes(b"GGUFdifferent")
        return old_stat(self, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", changing_stat)
    assert identity.assess(config, capture, hash_file=True)["status"] == "UNKNOWN"


def test_repeated_capture_cannot_certify_restart_or_loaded_weights(tmp_path):
    path, config, capture = inputs(tmp_path)
    before = identity.assess(config, capture, hash_file=True)
    same = identity.assess(config, capture, hash_file=True)
    assert identity.compare(before, same) == "NO_CHANGE_OBSERVED"
    capture["props"]["build_info"] = "fixture-2"
    assert identity.compare(before, identity.assess(config, capture, hash_file=True)) == "CHANGED"
    capture["props"]["build_info"] = "fixture-1"
    path.write_bytes(b"GGUFsynthetic-B")
    changed = identity.assess(config, capture, hash_file=True)
    assert changed["file_sha256"] != before["file_sha256"]
    assert identity.compare(before, changed) == "CHANGED"
    assert identity.compare(before, {"status": "REPORTED_PATH_MATCH"}) == "UNKNOWN"
    assert_unverified(changed)


def test_exact_response_model_report_not_attestation(tmp_path):
    _, config, capture = inputs(tmp_path)
    capture["response_model"] = "criba-local"
    actual = identity.assess(config, capture)
    assert actual["response_model"] == "REPORT_MATCH"
    assert_unverified(actual)


def test_ollama_catalog_only_and_not_compatible_with_local_llama_route(tmp_path):
    _, config, capture = inputs(tmp_path)
    config["profiles"][0].update(backend="ollama", endpoint="http://127.0.0.1:11434",
                                 model="qwen")
    capture.update(effective_model="qwen", effective_endpoint="http://127.0.0.1:11434",
                   models={"models": [{"name": "qwen:latest", "digest": "a" * 64}]})
    assert identity.assess(config, capture)["reason"] == "incompatible_backend_or_route"
    capture["route"] = "synthesis"
    actual = identity.assess(config, capture)
    assert actual["status"] == "CATALOG_ONLY"
    assert_unverified(actual)
    capture["models"]["models"].append({"name": "qwen"})
    assert identity.assess(config, capture)["reason"] == "absent_or_ambiguous_alias"


@pytest.mark.parametrize("raw", ['{"model":"a","model":"b"}', '[NaN]', '[Infinity]'])
def test_capture_parser_rejects_ambiguous_json(raw):
    with pytest.raises(ValueError):
        identity._strict_json(raw)


def test_capture_requires_effective_api_base_not_just_profile_url(tmp_path):
    _, config, capture = inputs(tmp_path)
    capture["effective_endpoint"] = config["profiles"][0]["endpoint"]
    assert identity.assess(config, capture)["reason"] == "invalid_endpoint"


def test_synthesis_ipv6_not_supported_by_existing_runtime(tmp_path):
    _, config, capture = inputs(tmp_path)
    config["profiles"][0]["endpoint"] = "http://[::1]:8080"
    capture.update(route="synthesis", effective_endpoint="http://[::1]:8080")
    assert identity.assess(config, capture)["reason"] == "unsupported_synthesis_endpoint"


def test_ollama_catalog_contradictory_names_unknown(tmp_path):
    _, config, capture = inputs(tmp_path)
    config["profiles"][0].update(backend="ollama", endpoint="http://127.0.0.1:11434",
                                 model="qwen")
    capture.update(route="synthesis", effective_model="qwen",
                   effective_endpoint="http://127.0.0.1:11434",
                   models={"models": [{"name": "qwen", "model": "different"}]})
    actual = identity.assess(config, capture)
    assert actual["status"] == "UNKNOWN"
    assert actual["reason"] == "contradictory_catalog_entry"
