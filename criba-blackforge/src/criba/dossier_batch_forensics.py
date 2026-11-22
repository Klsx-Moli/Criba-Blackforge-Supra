"""Non-destructive, offline forensics for versioned dossier journals.

Never repairs, truncates, migrates, posts or restores a journal. Snapshot
creation is explicit, outside the source directory, and records exact raw
bytes of both evidence files. A valid SHA256 proves byte equality only.
The existing cooperative lock may create its sidecar when first opened.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import dossier_batch as batch
from . import supra_dossier as sd

FILES = ("dossier_batches.jsonl", "dossiers.jsonl")
SNAPSHOT_SCHEMA = "criba-dossier-forensic-snapshot/1"
MAX_INSPECT_BYTES = 64 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 512 * 1024 * 1024
KNOWN_EVENTS = frozenset((
    "PREPARED", "LOCAL_COMMITTED", "REMOTE_UNKNOWN",
    "REMOTE_DISPATCH_STARTED", "REMOTE_PARTIAL_READBACK_OBSERVED",
    "REMOTE_READBACK_OBSERVED",
))


def _source(path: Path) -> Path:
    raw = Path(path).absolute()
    if raw.is_symlink() or not raw.is_dir():
        raise ValueError("forensic source must be an existing real directory")
    directory = raw.resolve(strict=True)
    for name in FILES:
        item = directory / name
        if item.is_symlink() or (item.exists() and not item.is_file()):
            raise ValueError("forensic source contains symlink/non-file evidence")
    return directory


def _digest(path: Path) -> dict[str, Any]:
    sha = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
            size += len(block)
    return {"present": True, "bytes": size, "sha256": sha.hexdigest()}


def _inventory(directory: Path) -> dict[str, dict[str, Any]]:
    return {
        name: (_digest(directory / name) if (directory / name).exists()
               else {"present": False, "bytes": 0, "sha256": None})
        for name in FILES
    }


def _inspect_locked(directory: Path) -> dict[str, Any]:
    files = _inventory(directory)
    report: dict[str, Any] = {
        "classification": "UNKNOWN", "local_replay_parseable": False,
        "remote_execution_proven": False, "scientific_validation_proven": False,
        "files": files, "event_count": None, "batch_count": None,
    }
    jpath, dpath = (directory / name for name in FILES)
    if not jpath.exists():
        report["classification"] = "JOURNAL_MISSING"
        return report
    if any(item["bytes"] > MAX_INSPECT_BYTES for item in files.values()):
        report["classification"] = "INSPECTION_SIZE_LIMIT"
        return report
    raw = jpath.read_bytes()
    if raw and not raw.endswith(b"\n"):
        report["classification"] = "JOURNAL_UNTERMINATED_TAIL"
        return report
    try:
        events = batch._events(jpath)
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        report["classification"] = (
            "UNSUPPORTED_JOURNAL_SCHEMA" if "schema mismatch" in str(exc)
            else "JOURNAL_PARSE_INVALID"
        )
        return report
    report["event_count"] = len(events)
    report["requires_partial_event_reader"] = any(
        e.get("event") == "REMOTE_PARTIAL_READBACK_OBSERVED" for e in events
    )
    report["requires_dispatch_event_reader"] = any(
        e.get("event") == "REMOTE_DISPATCH_STARTED" for e in events
    )
    if any(event.get("event") not in KNOWN_EVENTS for event in events):
        report["classification"] = "UNSUPPORTED_EVENT_VERSION"
        return report
    try:
        state = batch._state(events)
    except (ValueError, TypeError, KeyError, AttributeError,
            IndexError, RecursionError, OverflowError):
        report["classification"] = "JOURNAL_REPLAY_INVALID"
        return report
    report["batch_count"] = len(state)
    # The historical dossier reader deliberately skips corrupt JSONL rows.
    # A FORENSIC classification must NOT inherit that permissive behaviour.
    if not dpath.exists():
        report["classification"] = (
            "DOSSIER_HISTORY_MISSING" if state else "VALID_EMPTY_HISTORY"
        )
        return report
    try:
        with dpath.open("rb") as stream:
            for line in stream:
                row = json.loads(
                    line, object_pairs_hook=batch._unique_pairs,
                    parse_constant=batch._bad_constant,
                )
                if not isinstance(row, dict):
                    raise ValueError("invalid dossier history row type")
    except (ValueError, UnicodeDecodeError, RecursionError, OverflowError):
        report["classification"] = "DOSSIER_HISTORY_PARSE_INVALID"
        return report
    history, ambiguous, _ = sd._leer_historial(dpath)
    for entry in state.values():
        if not entry["committed"]:
            continue
        for dossier in entry["intent"]["dossiers"]:
            identity = dossier["dossier_id"]
            if (identity in ambiguous or identity not in history
                    or sd._contexto(history[identity]) != sd._contexto(dossier)):
                report["classification"] = "DOSSIER_HISTORY_MISMATCH"
                return report
    report["classification"] = "REPLAY_VALID_LOCAL_ONLY"
    report["local_replay_parseable"] = True
    # Counts are computed only from complete, parseable original evidence;
    # never default missing or corrupt files to zero local reservations.
    report["uncommitted_batches"] = sum(not x["committed"] for x in state.values())
    report["unknown_remote_batches"] = sum(
        x["remote"] == "UNKNOWN" for x in state.values()
    )
    # Locally valid batches can still be UNKNOWN remotely and scientifically.
    return report


def inspeccionar_journal(directory: Path) -> dict[str, Any]:
    """Inspect original evidence under writer lock; never change its JSONL."""
    root = _source(directory)
    with sd._historial_exclusive(root):
        return _inspect_locked(root)


def _destination(source: Path, out_dir: Path) -> Path:
    out = Path(out_dir).absolute()
    parent = out.parent.resolve(strict=True)
    if not parent.is_dir() or out.exists() or out.is_symlink():
        raise ValueError("snapshot destination must not exist; parent must exist")
    if parent == source or source in parent.parents:
        raise ValueError("snapshot must be outside original dossier directory")
    return parent / out.name


def crear_snapshot_forense(directory: Path, out_dir: Path) -> dict[str, Any]:
    """Explicit create-only raw backup; no rewriting or source repair.

    Manifest is written LAST; if interrupted, verification refuses an
    incomplete directory. An existing destination is never overwritten.
    """
    root = _source(directory)
    out = _destination(root, out_dir)
    with sd._historial_exclusive(root):
        analysis = _inspect_locked(root)
        if any(x["bytes"] > MAX_SNAPSHOT_BYTES for x in analysis["files"].values()):
            raise ValueError("forensic snapshot size limit exceeded")
        # mkdir(exist_ok=False) makes races fail without overwriting evidence.
        out.mkdir(mode=0o700, exist_ok=False)
        manifest: dict[str, Any] = {
            "schema": SNAPSHOT_SCHEMA,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "source_classification": analysis["classification"],
            "files": {},
            "remote_execution_proven": False,
            "scientific_validation_proven": False,
            "authorizes_post": False,
        }
        for name in FILES:
            entry = analysis["files"][name]
            if not entry["present"]:
                manifest["files"][name] = entry
                continue
            src, dst = root / name, out / name
            with src.open("rb") as inp, dst.open("xb") as output:
                shutil.copyfileobj(inp, output, 1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
            actual = _digest(dst)
            if actual != entry:
                # Leave an incomplete, non-authoritative archive for inspection.
                raise ValueError("source changed during forensic snapshot")
            manifest["files"][name] = actual
        manifest_path = out / "manifest.json"
        with manifest_path.open("x", encoding="utf-8") as file:
            json.dump(manifest, file, ensure_ascii=False, sort_keys=True, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        if os.name == "posix":
            # Durably publish the directory entries, not just file contents.
            handle = os.open(out, os.O_RDONLY)
            try:
                os.fsync(handle)
            finally:
                os.close(handle)
    return {
        "snapshot": str(out), "classification": analysis["classification"],
        "status": "RAW_BYTES_PRESERVED_NOT_RESTORED",
        "authorizes_post": False,
    }


def verificar_snapshot_forense(out_dir: Path) -> dict[str, Any]:
    """Offline verification of raw backup bytes, NOT truth of their claims."""
    raw = Path(out_dir).absolute()
    if raw.is_symlink() or not raw.is_dir():
        raise ValueError("snapshot directory unavailable or symlinked")
    root = raw.resolve(strict=True)
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("forensic manifest missing or symlinked")
    try:
        with manifest_path.open("r", encoding="utf-8") as stream:
            manifest = json.load(
                stream, object_pairs_hook=batch._unique_pairs,
                parse_constant=batch._bad_constant,
            )
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("forensic manifest is malformed") from exc
    if (not isinstance(manifest, dict)
            or manifest.get("schema") != SNAPSHOT_SCHEMA
            or not isinstance(manifest.get("files"), dict)
            or set(manifest["files"]) != set(FILES)
            or manifest.get("authorizes_post") is not False
            or manifest.get("remote_execution_proven") is not False
            or manifest.get("scientific_validation_proven") is not False):
        raise ValueError("forensic manifest schema invalid")
    inventory = manifest["files"]
    if any(not isinstance(inventory[name], dict)
           or type(inventory[name].get("present")) is not bool for name in FILES):
        raise ValueError("forensic inventory invalid")
    expected_names = {"manifest.json"} | {
        name for name in FILES if inventory[name]["present"]
    }
    if {item.name for item in root.iterdir()} != expected_names:
        raise ValueError("forensic snapshot contains missing or unexpected files")
    for name in FILES:
        expected = manifest["files"][name]
        if not isinstance(expected, dict) or type(expected.get("present")) is not bool:
            raise ValueError("forensic inventory invalid")
        path = root / name
        if not expected["present"]:
            if (type(expected.get("bytes")) is not int
                    or expected["bytes"] != 0
                    or expected.get("sha256") is not None):
                raise ValueError("forensic absence descriptor inconsistent")
            continue
        if (path.is_symlink() or not path.is_file()
                or type(expected.get("bytes")) is not int
                or expected["bytes"] < 0
                or not isinstance(expected.get("sha256"), str)):
            raise ValueError("forensic inventory invalid")
        digest = expected["sha256"]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("forensic SHA256 descriptor invalid")
        if _digest(path) != expected:
            raise ValueError("forensic snapshot digest mismatch")
    return {
        "status": "RAW_BYTES_MATCH_MANIFEST_ONLY", "files_verified": len(FILES),
        "source_classification": manifest.get("source_classification"),
        "authorizes_post": False,
        "scientific_validation_proven": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Forense offline JSONL; NO REPAIR/POST")
    parser.add_argument("--source", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect", action="store_true")
    mode.add_argument("--snapshot-out", type=Path)
    mode.add_argument("--verify-snapshot", type=Path)
    args = parser.parse_args(argv)
    if args.verify_snapshot is not None:
        result = verificar_snapshot_forense(args.verify_snapshot)
    else:
        if args.source is None:
            parser.error("--source is mandatory for inspection or snapshot")
        result = (
            inspeccionar_journal(args.source) if args.inspect
            else crear_snapshot_forense(args.source, args.snapshot_out)
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("classification") == "REPLAY_VALID_LOCAL_ONLY" or (
        result.get("status") == "RAW_BYTES_MATCH_MANIFEST_ONLY"
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
