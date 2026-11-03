import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest

_support_spec = importlib.util.spec_from_file_location(
    "cbs_e01v2_support", Path(__file__).with_name("cbs_e01v2_helpers.py")
)
assert _support_spec is not None and _support_spec.loader is not None
_support = importlib.util.module_from_spec(_support_spec)
_support_spec.loader.exec_module(_support)
dossier, invoke = _support.dossier, _support.invoke


def test_disk_roundtrip_across_finished_then_new_process(home):
    original = dossier()
    writer = invoke(home, "save", payload=original)
    assert writer["ok"], writer
    assert (home / "dossiers" / "dossiers.jsonl").is_file()
    reader = invoke(home, "load", identity=original["dossier_id"])
    assert reader["ok"] and reader["value"] == original
    assert reader["module_path"] == writer["module_path"]
    assert reader["mode"] == writer["mode"]
    assert reader["value"]["unknown"] is None
    assert reader["value"]["measured_zero"] == 0.0
    assert reader["value"]["estado"] == "SUPRA_EJECUCION_PENDIENTE"
    assert reader["value"]["prueba_discriminante"]["estado_prueba"] == "NO_EJECUTADA"


def test_explicit_directory_not_default_home(home, tmp_path):
    target = tmp_path / "explicit"
    original = dossier()
    assert invoke(home, "save", payload=original, directory=target)["ok"]
    assert (target / "dossiers.jsonl").is_file()
    assert not (home / "dossiers" / "dossiers.jsonl").exists()
    assert (
        invoke(home, "load", identity=original["dossier_id"], directory=target)["value"] == original
    )


def test_home_isolation(home, tmp_path):
    original = dossier()
    assert invoke(home, "save", payload=original)["ok"]
    other = invoke(tmp_path / "other", "load", identity=original["dossier_id"])
    assert other["ok"] and other["value"] is None


def test_idempotence_across_processes(home):
    original = dossier()
    assert invoke(home, "save", payload=original)["ok"]
    assert invoke(home, "save", payload=original)["ok"]
    assert len((home / "dossiers" / "dossiers.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_timestamp_only_does_not_change_context(home):
    original = dossier()
    assert invoke(home, "save", payload=original)["ok"]
    changed = deepcopy(original)
    changed["creado_at"] = "2026-10-25T01:00:00+00:00"
    assert invoke(home, "save", payload=changed)["ok"]
    assert invoke(home, "load", identity=original["dossier_id"])["value"] == original


def test_same_id_different_content_rejected(home):
    original = dossier()
    assert invoke(home, "save", payload=original)["ok"]
    changed = deepcopy(original)
    changed["mecanismo"] = "otro contenido"
    result = invoke(home, "save", payload=changed)
    assert not result["ok"] and result["error_type"] == "ValueError"
    assert invoke(home, "load", identity=original["dossier_id"])["value"] == original


def test_missing_dossier_is_none_not_fabricated(home):
    result = invoke(home, "load", identity="missing")
    assert result["ok"] and result["value"] is None
    assert not (home / "dossiers" / "dossiers.jsonl").exists()


def test_latest_after_separate_process_writes(home):
    first = dossier("first")
    second = dossier("second")
    assert invoke(home, "save", payload=first)["ok"]
    assert invoke(home, "save", payload=second)["ok"]
    assert invoke(home, "latest")["value"] == second
    assert invoke(home, "load", identity="first")["value"] == first


def test_empty_latest(home):
    result = invoke(home, "latest")
    assert result["ok"] and result["value"] is None


@pytest.mark.parametrize("identity", [None, "", "  ", 17, True])
def test_empty_or_invalid_identity_rejected(home, identity):
    result = invoke(home, "save", payload=dossier(identity))
    assert not result["ok"] and result["error_type"] == "ValueError"
    assert not (home / "dossiers" / "dossiers.jsonl").exists()
