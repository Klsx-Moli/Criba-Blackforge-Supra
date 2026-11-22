"""F26 forensic evidence: raw byte copies, conservative replay, no repair/POST.

Real filesystem/journal locks and JSONL. No Qt, network, model or remote calls.
Tests include damaged-but-parseable records and fresh process verification.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from criba import dossier_batch as batch
from criba import supra_dossier as sd
from criba.dossier_batch_forensics import (
    FILES, SNAPSHOT_SCHEMA, crear_snapshot_forense,
    inspeccionar_journal, main, verificar_snapshot_forense,
)
from criba.dossier_batch_recovery import _readback
from test_dossier_batch_phase15_integration import (
    ENDPOINT, lookup, prepared,
)


def source(tmp_path):
    root = tmp_path / "source"
    key, originals = prepared(root)
    return root, key, originals


def backup(tmp_path):
    return tmp_path / "preserved-raw-evidence"


def bytes_before(root):
    return {name: (root / name).read_bytes() for name in FILES}


def assert_untouched(root, before):
    assert bytes_before(root) == before


def test_known_journal_is_locally_replayable_not_remote_or_scientifically_validated(tmp_path):
    root, key, _ = source(tmp_path)
    before = bytes_before(root)
    report = inspeccionar_journal(root)
    assert report["classification"] == "REPLAY_VALID_LOCAL_ONLY"
    assert report["local_replay_parseable"] is True
    assert report["remote_execution_proven"] is False
    assert report["scientific_validation_proven"] is False
    assert report["event_count"] == 3
    assert report["batch_count"] == 1
    assert report["requires_partial_event_reader"] is False
    assert report["requires_dispatch_event_reader"] is False
    for name in FILES:
        assert report["files"][name]["sha256"] == hashlib.sha256(before[name]).hexdigest()
    assert_untouched(root, before)


def test_explicit_raw_snapshot_preserves_exact_original_bytes_and_verifies(tmp_path):
    root, _key, _ = source(tmp_path)
    before = bytes_before(root)
    out = backup(tmp_path)
    result = crear_snapshot_forense(root, out)
    assert result["status"] == "RAW_BYTES_PRESERVED_NOT_RESTORED"
    assert result["authorizes_post"] is False
    assert out.is_dir()
    assert {name: (out / name).read_bytes() for name in FILES} == before
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == SNAPSHOT_SCHEMA
    assert manifest["authorizes_post"] is False
    assert manifest["remote_execution_proven"] is False
    assert manifest["scientific_validation_proven"] is False
    check = verificar_snapshot_forense(out)
    assert check["status"] == "RAW_BYTES_MATCH_MANIFEST_ONLY"
    assert check["scientific_validation_proven"] is False
    assert_untouched(root, before)


def test_corrupt_tail_backup_preserves_damage_without_repair_or_promotion(tmp_path):
    root, key, originals = source(tmp_path)
    with (root / batch.JOURNAL).open("ab") as output:
        output.write(b'{"event":')
    before = bytes_before(root)
    assert inspeccionar_journal(root)["classification"] == "JOURNAL_UNTERMINATED_TAIL"
    result = crear_snapshot_forense(root, backup(tmp_path))
    assert result["classification"] == "JOURNAL_UNTERMINATED_TAIL"
    assert (backup(tmp_path) / batch.JOURNAL).read_bytes() == before[batch.JOURNAL]
    assert verificar_snapshot_forense(backup(tmp_path))[
        "status"
    ] == "RAW_BYTES_MATCH_MANIFEST_ONLY"
    assert_untouched(root, before)


def test_read_only_inspection_refuses_to_create_missing_source_dir(tmp_path):
    missing = tmp_path / "absent"
    with pytest.raises(ValueError, match="existing real directory"):
        inspeccionar_journal(missing)
    assert not missing.exists()


def test_missing_journal_is_unknown_not_empty_pass(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "dossiers.jsonl").write_text('{"dossier_id":"draft-1"}\n', encoding="utf-8")
    report = inspeccionar_journal(root)
    assert report["classification"] == "JOURNAL_MISSING"
    assert report["local_replay_parseable"] is False
    assert report["batch_count"] is None
    result = crear_snapshot_forense(root, backup(tmp_path))
    assert result["classification"] == "JOURNAL_MISSING"
    manifest = json.loads((backup(tmp_path) / "manifest.json").read_text())
    assert manifest["files"][batch.JOURNAL] == {
        "present": False, "bytes": 0, "sha256": None,
    }
    assert verificar_snapshot_forense(backup(tmp_path))[
        "status"
    ] == "RAW_BYTES_MATCH_MANIFEST_ONLY"


def test_never_overwrite_existing_snapshot_directory(tmp_path):
    root, _, _ = source(tmp_path)
    out = backup(tmp_path)
    crear_snapshot_forense(root, out)
    manifest = (out / "manifest.json").read_bytes()
    with pytest.raises(ValueError, match="must not exist"):
        crear_snapshot_forense(root, out)
    assert (out / "manifest.json").read_bytes() == manifest


def test_snapshot_inside_source_is_forbidden(tmp_path):
    root, _, _ = source(tmp_path)
    dest = root / "backup-inside"
    with pytest.raises(ValueError, match="outside original"):
        crear_snapshot_forense(root, dest)
    assert not dest.exists()


@pytest.mark.parametrize("mutation", [
    lambda b: b + b'{"event":',
    lambda b: b.replace(b'"batch_id":', b'"batch_id":"x","batch_id":', 1),
    lambda b: b.replace(b'"schema":', b'"schema":"wrong","schema":', 1),
    lambda b: b.replace(b'"event":', b'"event":NaN,"old_event":', 1),
])
def test_corrupt_bytes_do_not_get_repaired_during_snapshot(tmp_path, mutation):
    root, _, _ = source(tmp_path)
    path = root / batch.JOURNAL
    path.write_bytes(mutation(path.read_bytes()))
    before = bytes_before(root)
    status = inspeccionar_journal(root)["classification"]
    assert status not in ("REPLAY_VALID_LOCAL_ONLY", "VALID_EMPTY_HISTORY")
    crear_snapshot_forense(root, backup(tmp_path))
    assert_untouched(root, before)
    assert (backup(tmp_path) / batch.JOURNAL).read_bytes() == before[batch.JOURNAL]


def test_future_unknown_event_is_not_silently_skipped_or_migrated(tmp_path):
    root, key, _ = source(tmp_path)
    sd._append_historial(root / batch.JOURNAL, batch._event(
        "REMOTE_FUTURE_CUSTOM/99", key, unknown_claim="do-not-execute",
    ))
    before = bytes_before(root)
    report = inspeccionar_journal(root)
    assert report["classification"] == "UNSUPPORTED_EVENT_VERSION"
    assert report["local_replay_parseable"] is False
    crear_snapshot_forense(root, backup(tmp_path))
    assert_untouched(root, before)
    assert verificar_snapshot_forense(backup(tmp_path))["authorizes_post"] is False


def test_other_schema_is_reported_as_unsupported_not_repaired(tmp_path):
    root, _, _ = source(tmp_path)
    path = root / batch.JOURNAL
    path.write_bytes(
        path.read_bytes().replace(
            batch.SCHEMA.encode(), b"criba-dossier-batch/99", 1,
        )
    )
    assert inspeccionar_journal(root)["classification"] == "UNSUPPORTED_JOURNAL_SCHEMA"


def test_json_complete_but_unterminated_final_line_is_not_authority(tmp_path):
    root, _, _ = source(tmp_path)
    path = root / batch.JOURNAL
    path.write_bytes(path.read_bytes().rstrip(b"\n"))
    before = path.read_bytes()
    assert inspeccionar_journal(root)["classification"] == "JOURNAL_UNTERMINATED_TAIL"
    assert path.read_bytes() == before


def test_parseable_local_dossier_tampering_is_separate_from_journal_parse(tmp_path):
    root, _, _ = source(tmp_path)
    path = root / "dossiers.jsonl"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "mechanism-1", "fabricated-mechanism",
        ), encoding="utf-8",
    )
    report = inspeccionar_journal(root)
    assert report["classification"] == "DOSSIER_HISTORY_MISMATCH"
    assert report["event_count"] == 3
    assert report["local_replay_parseable"] is False


def test_torn_dossier_history_line_not_ignored_by_forensic_classification(tmp_path):
    root, _, _ = source(tmp_path)
    with (root / "dossiers.jsonl").open("ab") as file:
        file.write(b'\n{"dossier_id":')
    assert inspeccionar_journal(root)["classification"] == "DOSSIER_HISTORY_PARSE_INVALID"


def test_removed_dossier_history_cannot_be_treated_as_zero_evidence(tmp_path):
    root, _, _ = source(tmp_path)
    (root / "dossiers.jsonl").unlink()
    report = inspeccionar_journal(root)
    assert report["classification"] == "DOSSIER_HISTORY_MISSING"
    assert report["local_replay_parseable"] is False


def test_event_reader_requirement_for_partial_get_not_backward_compatible(tmp_path):
    root, key, original = source(tmp_path)
    row = _readback(original[0], lookup(original[0]))
    assert row is not None
    assert batch.registrar_readback_parcial(key, row, root, endpoint=ENDPOINT)
    report = inspeccionar_journal(root)
    assert report["classification"] == "REPLAY_VALID_LOCAL_ONLY"
    assert report["requires_partial_event_reader"] is True
    assert report["remote_execution_proven"] is False


def test_event_reader_requirement_for_dispatch_claim(tmp_path):
    root, key, original = source(tmp_path)
    batch.reclamar_inicio_envio_remoto(key, original, root, endpoint=ENDPOINT)
    report = inspeccionar_journal(root)
    assert report["requires_dispatch_event_reader"] is True
    assert report["remote_execution_proven"] is False


@pytest.mark.parametrize("mutator", [
    lambda m: m.__setitem__("files", None),
    lambda m: m.__setitem__("files", []),
    lambda m: m.__setitem__("files", {}),
    lambda m: m.__setitem__("authorizes_post", True),
    lambda m: m.__setitem__("remote_execution_proven", True),
    lambda m: m.__setitem__("scientific_validation_proven", True),
    lambda m: m["files"]["dossiers.jsonl"].__setitem__("present", 1),
    lambda m: m["files"]["dossiers.jsonl"].__setitem__("sha256", "a" * 64),
    lambda m: m["files"]["dossiers.jsonl"].__setitem__("bytes", -1),
])
def test_mutated_manifest_refused_even_if_file_bytes_are_intact(tmp_path, mutator):
    root, _, _ = source(tmp_path)
    out = backup(tmp_path)
    crear_snapshot_forense(root, out)
    manifest_path = out / "manifest.json"
    contents = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutator(contents)
    manifest_path.write_text(
        json.dumps(contents, ensure_ascii=False, sort_keys=True), encoding="utf-8",
    )
    with pytest.raises(ValueError):
        verificar_snapshot_forense(out)


def test_manifest_duplicate_keys_and_nan_are_not_accepted(tmp_path):
    root, _, _ = source(tmp_path)
    out = backup(tmp_path)
    crear_snapshot_forense(root, out)
    path = out / "manifest.json"
    raw = path.read_text(encoding="utf-8")
    path.write_text(raw.replace('"schema":', '"schema":"x","schema":', 1))
    with pytest.raises(ValueError, match="forensic manifest is malformed"):
        verificar_snapshot_forense(out)
    path.write_text(raw.replace('"authorizes_post": false', '"authorizes_post": NaN'))
    with pytest.raises(ValueError, match="forensic manifest is malformed"):
        verificar_snapshot_forense(out)


def test_snapshot_data_bitflip_detected_after_creation(tmp_path):
    root, _, _ = source(tmp_path)
    out = backup(tmp_path)
    crear_snapshot_forense(root, out)
    path = out / batch.JOURNAL
    content = bytearray(path.read_bytes())
    content[0] ^= 1
    path.write_bytes(content)
    with pytest.raises(ValueError, match="digest mismatch"):
        verificar_snapshot_forense(out)


def test_incomplete_snapshot_without_manifest_is_never_accepted(tmp_path):
    out = backup(tmp_path)
    out.mkdir()
    (out / "dossiers.jsonl").write_bytes(b'{"dossier_id":"orphan"}\n')
    with pytest.raises(ValueError, match="manifest missing"):
        verificar_snapshot_forense(out)


def test_extra_file_in_snapshot_rejected_as_noncanonical(tmp_path):
    root, _, _ = source(tmp_path)
    out = backup(tmp_path)
    crear_snapshot_forense(root, out)
    (out / "added-forged-evidence.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="missing or unexpected"):
        verificar_snapshot_forense(out)


def test_sourced_symlink_is_rejected_if_os_allows_symlinks(tmp_path):
    root, _, _ = source(tmp_path)
    (root / "dossiers.jsonl").unlink()
    try:
        (root / "dossiers.jsonl").symlink_to(tmp_path / "external.jsonl")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported by local filesystem")
    with pytest.raises(ValueError, match="symlink"):
        inspeccionar_journal(root)


def test_missing_source_and_snapshot_are_not_created_by_verification(tmp_path):
    path = backup(tmp_path)
    with pytest.raises(ValueError, match="unavailable"):
        verificar_snapshot_forense(path)
    assert not path.exists()


def test_repeat_snapshot_race_only_one_writer_wins_no_overwrite(tmp_path):
    root, _, _ = source(tmp_path)
    out = backup(tmp_path)

    def attempt(_):
        try:
            crear_snapshot_forense(root, out)
            return "CREATED"
        except (OSError, ValueError):
            return "REJECTED"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, (1, 2)))
    assert sorted(results) == ["CREATED", "REJECTED"]
    assert verificar_snapshot_forense(out)["status"] == "RAW_BYTES_MATCH_MANIFEST_ONLY"


def test_separate_python_process_can_verify_backup_after_restart(tmp_path):
    root, _, _ = source(tmp_path)
    out = backup(tmp_path)
    crear_snapshot_forense(root, out)
    child = (
        "import json,sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0,sys.argv[1])\n"
        "from criba.dossier_batch_forensics import verificar_snapshot_forense\n"
        "print(json.dumps(verificar_snapshot_forense(Path(sys.argv[2]))))\n"
    )
    run = subprocess.run(
        [sys.executable, "-c", child,
         str(Path(__file__).resolve().parents[2] / "src"), str(out)],
        check=True, capture_output=True, text=True, timeout=20,
    )
    assert json.loads(run.stdout)["authorizes_post"] is False


def test_cli_inspect_and_verify_only_report_local_raw_evidence(tmp_path, capsys):
    root, _, _ = source(tmp_path)
    rc = main(["--source", str(root), "--inspect"])
    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert report["classification"] == "REPLAY_VALID_LOCAL_ONLY"
    out = backup(tmp_path)
    rc = main(["--source", str(root), "--snapshot-out", str(out)])
    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert report["authorizes_post"] is False
    rc = main(["--verify-snapshot", str(out)])
    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert report["status"] == "RAW_BYTES_MATCH_MANIFEST_ONLY"


def test_cli_corrupt_source_snapshot_created_but_nonzero_status(tmp_path, capsys):
    root, _, _ = source(tmp_path)
    with (root / batch.JOURNAL).open("ab") as output:
        output.write(b'{"torn":')
    out = backup(tmp_path)
    rc = main(["--source", str(root), "--snapshot-out", str(out)])
    result = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert result["classification"] == "JOURNAL_UNTERMINATED_TAIL"
    assert out.exists()
    assert verificar_snapshot_forense(out)["status"] == "RAW_BYTES_MATCH_MANIFEST_ONLY"



def test_recursion_bomb_in_journal_is_classified_without_running_any_repair(tmp_path):
    root, _, _ = source(tmp_path)
    path = root / batch.JOURNAL
    attack = b'{"schema":"' + batch.SCHEMA.encode() + b'","x":' + (
        b"[" * 2000 + b"0" + b"]" * 2000
    ) + b"}\n"
    path.write_bytes(attack)
    raw = path.read_bytes()
    report = inspeccionar_journal(root)
    assert report["classification"] == "JOURNAL_PARSE_INVALID"
    assert report["local_replay_parseable"] is False
    assert path.read_bytes() == raw


def test_deeply_nested_dossier_json_is_not_silently_skipped(tmp_path):
    root, _, _ = source(tmp_path)
    path = root / "dossiers.jsonl"
    with path.open("ab") as out:
        out.write(b'{"dossier_id":"extra","nested":' + b"[" * 2000
                  + b"0" + b"]" * 2000 + b"}\n")
    report = inspeccionar_journal(root)
    assert report["classification"] == "DOSSIER_HISTORY_PARSE_INVALID"


def test_valid_but_uncertain_remote_state_is_not_implicitly_zero(tmp_path):
    root, _, _ = source(tmp_path)
    report = inspeccionar_journal(root)
    assert report["unknown_remote_batches"] == 1
    assert report["uncommitted_batches"] == 0
    assert report["remote_execution_proven"] is False


def test_incomplete_prepared_is_locally_parseable_but_not_committed(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    originals = dossiers()
    key = batch._batch_id("phase15-run", "Synthetic recovery problem")
    sd._append_historial(
        root / batch.JOURNAL,
        batch._event(
            "PREPARED", key, run_id="phase15-run",
            problema="Synthetic recovery problem",
            fingerprint=batch._fingerprint(originals),
            dossiers=originals,
        ),
    )
    report = inspeccionar_journal(root)
    # No dossier history exists: this incomplete write remains non-authoritative.
    assert report["classification"] == "DOSSIER_HISTORY_MISSING"
    assert report["local_replay_parseable"] is False



def test_snapshot_verifier_does_not_count_absent_evidence_as_verified_file(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "dossiers.jsonl").write_bytes(b'{"dossier_id":"orphan"}\n')
    out = backup(tmp_path)
    crear_snapshot_forense(root, out)
    result = verificar_snapshot_forense(out)
    assert result["files_verified"] == 1
    assert result["absences_recorded"] == 1
    assert result["recorded_source_classification"] == "JOURNAL_MISSING"
    assert result["authorizes_post"] is False


@pytest.mark.parametrize("mutation", [
    lambda m: m["files"]["dossiers.jsonl"].__setitem__("scientific_pass", True),
    lambda m: m.__setitem__("scientific_pass", True),
    lambda m: m.__setitem__("created_utc", 42),
    lambda m: m.__setitem__("source_classification", None),
])
def test_unknown_manifest_claims_are_not_accepted_as_raw_evidence(tmp_path, mutation):
    root, _, _ = source(tmp_path)
    out = backup(tmp_path)
    crear_snapshot_forense(root, out)
    manifest = out / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    mutation(data)
    manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest|inventory"):
        verificar_snapshot_forense(out)



def test_oversized_manifest_is_rejected_before_json_parse(tmp_path):
    root, _, _ = source(tmp_path)
    out = backup(tmp_path)
    crear_snapshot_forense(root, out)
    path = out / "manifest.json"
    with path.open("ab") as handle:
        handle.write(b" " * (128 * 1024))
    with pytest.raises(ValueError, match="exceeds inspection limit"):
        verificar_snapshot_forense(out)


def test_recursive_manifest_is_classified_as_malformed(tmp_path):
    root, _, _ = source(tmp_path)
    out = backup(tmp_path)
    crear_snapshot_forense(root, out)
    path = out / "manifest.json"
    path.write_bytes(b'{"schema":' + b"[" * 1500 +
                     b"0" + b"]" * 1500 + b"}")
    with pytest.raises(ValueError, match="forensic manifest is malformed"):
        verificar_snapshot_forense(out)



@pytest.mark.parametrize("fake", [
    "", "UNKNOWN", "PASS", "CERTIFIED_SUCCESS", "POST_DELIVERED",
    "SCIENTIFIC_VALIDATED", "READY_FOR_POST", "REPLAY_AUTHORIZED",
])
def test_forged_source_classification_cannot_be_launched_as_valid_snapshot(
    tmp_path, fake,
):
    root, _, _ = source(tmp_path)
    out = backup(tmp_path)
    crear_snapshot_forense(root, out)
    path = out / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["source_classification"] = fake
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest schema invalid"):
        verificar_snapshot_forense(out)



@pytest.mark.parametrize("bad", [
    [], {}, {"claim": "PASS"}, ["REPLAY_VALID_LOCAL_ONLY"], None,
    False, True, float("nan"), float("inf"), 0, 1,
])
def test_nonhashable_or_invalid_classification_fails_closed_no_typeerror(
    tmp_path, bad,
):
    root, _, _ = source(tmp_path)
    out = backup(tmp_path)
    crear_snapshot_forense(root, out)
    manifest_path = out / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["source_classification"] = bad
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8",
    )
    with pytest.raises(ValueError, match="forensic manifest schema invalid"):
        verificar_snapshot_forense(out)


@pytest.mark.parametrize("bad", [
    "PASS", "POST_DELIVERED", "SCIENTIFIC_VALIDATED", "tomorrow",
    "2026-11-22", "2026-11-22T12:00:00",
    "2026-11-22T12:00:00+02:00",
])
def test_invalid_or_non_utc_manifest_timestamp_fails_closed(tmp_path, bad):
    root, _, _ = source(tmp_path)
    out = backup(tmp_path)
    crear_snapshot_forense(root, out)
    manifest_path = out / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["created_utc"] = bad
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8",
    )
    with pytest.raises(ValueError, match="forensic manifest schema invalid"):
        verificar_snapshot_forense(out)



@pytest.mark.parametrize("bad_record", [
    {},
    {"dossier_id": None},
    {"dossier_id": 0},
    {"dossier_id": ""},
    {"dossier_id": " dossier-whitespace "},
    [],
])
def test_parseable_dossier_lines_with_ignored_identity_are_not_fully_valid(
    tmp_path, bad_record,
):
    root, _, _ = source(tmp_path)
    path = root / "dossiers.jsonl"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(bad_record) + "\n")
    report = inspeccionar_journal(root)
    assert report["classification"] == "DOSSIER_HISTORY_PARSE_INVALID"
    assert report["local_replay_parseable"] is False
