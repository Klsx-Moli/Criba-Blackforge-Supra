"""Offline comparison of model selection and already captured runtime metadata.

No network, process control, imports from production runtime, or inference.
A matching reported path is NOT evidence of the bytes loaded into memory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def _strict_json(raw: str) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def nonfinite(value: str) -> Any:
        raise ValueError("nonfinite JSON")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def _endpoint(value: Any, *, default_port: int, v1: bool = False) -> tuple[str, int]:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("invalid endpoint")
    if any(ord(c) <= 32 for c in value):
        raise ValueError("invalid endpoint whitespace")
    addr = urlsplit(value)
    paths = ("/v1", "/v1/") if v1 else ("", "/")
    host = addr.hostname
    if (addr.scheme != "http" or host is None or host not in ("localhost", "127.0.0.1", "::1")
            or addr.username is not None or addr.password is not None
            or addr.path not in paths or addr.query or addr.fragment
            or addr.netloc.endswith(":")):
        raise ValueError("unsupported endpoint")
    port = addr.port if addr.port is not None else default_port
    if not 1 <= port <= 65535:
        raise ValueError("invalid endpoint port")
    return host, port


def _gguf_path(value: Any) -> Path:
    # Never follow a server-supplied relative, UNC or device path. The capture
    # is data from the host, and this code only opens the selected local file.
    if (not isinstance(value, str) or not value or value != value.strip()
            or "\x00" in value or value.startswith(("\\\\", "//"))):
        raise ValueError("invalid model path")
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or path.suffix.casefold() != ".gguf":
        raise ValueError("expected absolute GGUF path on this host")
    return path


def _stat_key(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _local_file(path: Path, hash_file: bool) -> dict[str, Any]:
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("not a regular model file")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if _stat_key(opened) != _stat_key(before):
            raise ValueError("file changed before inspection")
        header = stream.read(4)
        if header != b"GGUF":
            raise ValueError("invalid GGUF magic")
        if hash_file:
            digest.update(header)
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        after = os.fstat(stream.fileno())
    if _stat_key(before) != _stat_key(after) or _stat_key(before) != _stat_key(path.stat()):
        raise ValueError("file changed during inspection")
    return {"stat": list(_stat_key(after)), "sha256": digest.hexdigest() if hash_file else None}


def assess(config: Any, capture: Any, *, hash_file: bool = False) -> dict[str, Any]:
    """Classify a host capture; never infer the effective model from a UI label.

    config is the raw models.json (before legacy fallback/normalization).
    capture must contain route, effective_endpoint, effective_model, models,
    and, for llama.cpp, props. Read no paths supplied by the server.
    """
    result: dict[str, Any] = {
        "status": "UNKNOWN", "reason": "missing_input", "source": "HOST_CAPTURE_ONLY",
        "loaded_file_identity": "NOT_VERIFIED", "authorization": "NOT_GRANTED",
        "file_sha256": None, "observation_sha256": None, "response_model": "NOT_OBSERVED",
    }

    def end(status: str, reason: str) -> dict[str, Any]:
        return {**result, "status": status, "reason": reason}

    if type(hash_file) is not bool or not isinstance(config, dict) or not isinstance(capture, dict):
        return end("BLOCKED", "invalid_input")
    if type(config.get("schema_version")) is not int or config["schema_version"] != 1:
        return end("BLOCKED", "unsupported_config_schema")
    if config.get("enabled") is not True:
        return end("BLOCKED", "local_model_disabled")
    profiles, selected = config.get("profiles"), config.get("active_profile_id")
    if not isinstance(profiles, list) or not isinstance(selected, str) or not selected.strip():
        return end("BLOCKED", "invalid_selection")
    if any(not isinstance(p, dict) or not isinstance(p.get("id"), str)
           or not p["id"].strip() for p in profiles):
        return end("BLOCKED", "invalid_profiles")
    ids = [p["id"] for p in profiles]
    if len(set(ids)) != len(ids) or selected not in ids:
        return end("BLOCKED", "ambiguous_or_missing_active_profile")
    profile = profiles[ids.index(selected)]
    backend, alias = profile.get("backend"), profile.get("model")
    route = capture.get("route")
    if (backend not in ("llama_cpp", "ollama") or route not in ("local_llama", "synthesis")
            or (route == "local_llama" and backend != "llama_cpp")):
        return end("BLOCKED", "incompatible_backend_or_route")
    if not isinstance(alias, str) or not alias or alias != alias.strip():
        return end("BLOCKED", "invalid_requested_model")
    if capture.get("effective_model") != alias:
        return end("BLOCKED", "effective_model_mismatch")
    default_port = 11434 if backend == "ollama" else 8080
    try:
        configured = _endpoint(profile.get("endpoint"), default_port=default_port)
        effective = _endpoint(capture.get("effective_endpoint"),
                              default_port=80 if route == "local_llama" else default_port,
                              v1=route == "local_llama")
    except ValueError:
        return end("BLOCKED", "invalid_endpoint")
    if route == "synthesis" and configured[0] == "::1":
        return end("BLOCKED", "unsupported_synthesis_endpoint")
    if configured != effective:
        return end("BLOCKED", "effective_endpoint_mismatch")
    models = capture.get("models")
    entries = models.get("data" if backend == "llama_cpp" else "models") if isinstance(
        models, dict) else None
    if not isinstance(entries, list) or not entries:
        return end("UNKNOWN", "missing_catalog")
    names = []
    for entry in entries:
        if not isinstance(entry, dict):
            return end("UNKNOWN", "invalid_catalog")
        if backend == "ollama":
            # Both fields may be present; divergent declarations are ambiguous.
            if "name" in entry and "model" in entry and entry["name"] != entry["model"]:
                return end("UNKNOWN", "contradictory_catalog_entry")
            name = entry.get("name") or entry.get("model")
        else:
            name = entry.get("id")
        if not isinstance(name, str) or not name or name != name.strip():
            return end("UNKNOWN", "invalid_catalog")
        names.append(name)
    accepted = (
        {alias, alias + ":latest"} if backend == "ollama" and ":" not in alias else {alias}
    )
    matching = [name for name in names if name in accepted]
    if len(matching) != 1:
        return end("BLOCKED", "absent_or_ambiguous_alias")
    if "response_model" in capture:
        if (not isinstance(capture["response_model"], str)
                or capture["response_model"] not in accepted):
            return end("BLOCKED", "response_model_mismatch")
        result["response_model"] = "REPORT_MATCH"
    if backend == "ollama":
        return end("CATALOG_ONLY", "ollama_tag_is_not_loaded_model_identity")
    if len(names) != 1:
        return end("UNKNOWN", "multi_model_catalog_requires_routed_evidence")
    props = capture.get("props")
    if not isinstance(props, dict) or not props.get("model_path"):
        return end("UNKNOWN", "missing_model_path")
    if "model_alias" in props and props["model_alias"] != alias:
        return end("BLOCKED", "props_alias_mismatch")
    if "is_sleeping" in props and props["is_sleeping"] is not False:
        return end("UNKNOWN", "runtime_sleeping_or_state_unknown")
    try:
        expected = _gguf_path(profile.get("gguf_path"))
        reported = _gguf_path(props["model_path"])
    except ValueError:
        return end("UNKNOWN", "path_not_comparable_on_this_host")
    # Conservative pathname comparison, not a claim that different lexical
    # paths imply different bytes. Only the expected path may be opened.
    if str(expected) != str(reported):
        return end("BLOCKED", "reported_path_differs")
    try:
        file = _local_file(expected, hash_file)
    except (OSError, ValueError):
        return end("UNKNOWN", "local_file_unavailable_or_changed")
    # Include the selected profile and non-secret observed build data. Hash
    # identifies the capture projection, not the live process or weights.
    build = props.get("build_info")
    if build is not None and not isinstance(build, str):
        return end("UNKNOWN", "invalid_build_info")
    projection = [selected, backend, route, configured, alias, str(expected), matching, build, file]
    result["file_sha256"] = file["sha256"]
    result["observation_sha256"] = hashlib.sha256(json.dumps(
        projection, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()
    return end("REPORTED_PATH_MATCH", "path_report_and_local_file_agree_not_loaded_bytes")


def compare(before: dict[str, Any], after: dict[str, Any]) -> str:
    """Detect changed captured identity, never certify continuity across a gap."""
    if (before.get("status") != "REPORTED_PATH_MATCH"
            or after.get("status") != "REPORTED_PATH_MATCH"):
        return "UNKNOWN"
    left, right = before.get("observation_sha256"), after.get("observation_sha256")
    if any(not isinstance(d, str) or len(d) != 64
           or any(c not in "0123456789abcdef" for c in d) for d in (left, right)):
        return "UNKNOWN"
    return "NO_CHANGE_OBSERVED" if left == right else "CHANGED"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--hash-gguf", action="store_true", help="Read the entire selected GGUF")
    args = parser.parse_args()
    try:
        result = assess(_strict_json(args.config.read_text(encoding="utf-8")),
                        _strict_json(args.capture.read_text(encoding="utf-8")),
                        hash_file=args.hash_gguf)
    except (OSError, ValueError, RecursionError):
        parser.exit(2, "Invalid local capture/config\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
