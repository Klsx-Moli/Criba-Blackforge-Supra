from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import threading

import pytest

REPO = Path(__file__).resolve().parents[3]
TOOL = REPO / "criba-blackforge/.hermes/iie/multi_repo_state.py"
GATE = REPO / "scripts/check_eeimc_state.sh"
SHELL = shutil.which("sh")


def load_tool(tmp_path):
    spec = importlib.util.spec_from_file_location("lote4_tool", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.STATE_PATH = tmp_path / "STATE.json"
    module.STATE_PATH.write_text(json.dumps({"repos": {}, "locks": []}), encoding="utf-8")
    return module


def gate_environment(tmp_path, state=None, python="real", output="", code=0):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    script = repo / "scripts/check_eeimc_state.sh"
    shutil.copyfile(GATE, script)
    target = repo / "criba-blackforge/.hermes/iie/STATE.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"current": {"phase": "P11"}} if state is None else state), encoding="utf-8")
    binary = tmp_path / "bin"
    binary.mkdir()
    for name in ("dirname", "grep"):
        source = Path(shutil.which(name))
        shutil.copy2(source, binary / name)
        # MSYS coreutils need their runtime DLLs beside them when PATH is
        # restricted to this directory; dirname also loads the gettext DLL.
        # Without them the process exits 127, the gate falls back to the cwd
        # and the test produces a false red on Windows.
        for runtime in source.parent.glob("msys-*.dll"):
            shutil.copy2(runtime, binary / runtime.name)
    if python != "absent":
        executable = binary / "python3"
        if python == "real":
            executable.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
        else:
            executable.write_text("#!/bin/sh\nprintf '%s\\n' '" + output + "'\nexit " + str(code) + "\n")
        executable.chmod(0o755)
    return script, target, {**os.environ, "PATH": str(binary)}


def invoke_gate(script, env, cwd):
    if SHELL is None:
        pytest.skip("POSIX shell unavailable")
    return subprocess.run([SHELL, str(script)], env=env, cwd=cwd, capture_output=True, text=True, timeout=10)


@pytest.mark.parametrize("phase", [1, True, [], {}, " ", "P11\nEEIMC_STATE_OK", "P11\rP12"])
def test_gate_rejects_invalid_phase(tmp_path, phase):
    script, _, env = gate_environment(tmp_path, {"current": {"phase": phase}})
    assert invoke_gate(script, env, tmp_path).returncode != 0


@pytest.mark.parametrize("field,value", [
    ("branch", 4), ("branch", ["main"]), ("branch", "main\nEEIMC_STATE_OK"),
    ("commit", 4), ("commit", ["hash"]), ("commit", "hash\nEEIMC_STATE_OK"),
])
def test_gate_rejects_bad_metadata_instead_of_no_interpreter_success(tmp_path, field, value):
    state = {"current": {"phase": "P11"}, "last_good_state": {"commit": "abc"}}
    if field == "branch":
        state["current"][field] = value
    else:
        state["last_good_state"][field] = value
    script, _, env = gate_environment(tmp_path, state)
    assert invoke_gate(script, env, tmp_path).returncode != 0


@pytest.mark.parametrize("output,code", [
    ("prefix EEIMC_STATE_OK suffix", 0), ("EEIMC_STATE_OK_BUT_NOT_EXECUTED", 0),
    ("EEIMC_STATE_OK", 37), ("EEIMC_STATE_OK\nEEIMC_STATE_FAIL", 0),
    ("EEIMC_STATE_FAIL\nEEIMC_STATE_OK", 0), ("", 0), ("", 127),
])
def test_gate_requires_exact_ok_and_successful_exit(tmp_path, output, code):
    script, _, env = gate_environment(tmp_path, python="fake", output=output, code=code)
    assert invoke_gate(script, env, tmp_path).returncode != 0


def test_gate_without_interpreter_is_not_green(tmp_path):
    script, _, env = gate_environment(tmp_path, python="absent")
    result = invoke_gate(script, env, tmp_path)
    assert result.returncode == 2
    assert "NOT_ACCESSIBLE" in result.stdout


@pytest.mark.parametrize("raw", ['{"current":{"phase":"P11","phase":"P12"}}', '{"current":{"phase":"P11"},"x":NaN}', '{'])
def test_gate_rejects_ambiguous_or_nonstandard_json(tmp_path, raw):
    script, target, env = gate_environment(tmp_path)
    target.write_text(raw)
    assert invoke_gate(script, env, tmp_path).returncode != 0


@pytest.mark.parametrize("location", ["root", "subproject", "unrelated"])
def test_valid_gate_works_from_any_cwd_without_mutating_state(tmp_path, location):
    script, target, env = gate_environment(tmp_path)
    before = target.read_bytes()
    cwd = {"root": script.parent.parent, "subproject": target.parents[2], "unrelated": tmp_path}[location]
    result = invoke_gate(script, env, cwd)
    assert result.returncode == 0, result.stdout + result.stderr
    assert target.read_bytes() == before


@pytest.mark.parametrize("repo", ["UNKNOWN", "criba", " ", "CRIBA "])
def test_unknown_lock_repo_rejected(tmp_path, repo):
    tool = load_tool(tmp_path)
    before = tool.STATE_PATH.read_bytes()
    with pytest.raises(ValueError):
        tool.acquire_lock(repo, "src/a.py", "h", "r")
    assert tool.STATE_PATH.read_bytes() == before


@pytest.mark.parametrize("path", [
    "/src/a.py", "C:/src/a.py", r"C:\src\a.py", "C:src/a.py", r"\\server\share\a.py",
    "src/a.py.", "src/a.py ", "src/a.py:stream", "src/../a.py",
])
def test_noncanonical_lock_path_rejected(tmp_path, path):
    tool = load_tool(tmp_path)
    with pytest.raises(ValueError):
        tool.acquire_lock("CRIBA", path, "h", "r")


@pytest.mark.parametrize("locks", [None, {}, "locks", [None], [{}], [{"repo": None, "path": "src/a.py", "holder": "h", "acquired_at": "t", "reason": "r"}]])
def test_malformed_coordination_record_cannot_grant_new_lock(tmp_path, locks):
    tool = load_tool(tmp_path)
    tool.STATE_PATH.write_text(json.dumps({"repos": {}, "locks": locks}))
    before = tool.STATE_PATH.read_bytes()
    with pytest.raises(ValueError):
        tool.acquire_lock("CRIBA", "src/new.py", "new", "r")
    assert tool.STATE_PATH.read_bytes() == before


@pytest.mark.parametrize("token", [True, False, "3", 0, -1, None])
def test_invalid_existing_fence_token_is_not_coerced(tmp_path, token):
    tool = load_tool(tmp_path)
    tool.STATE_PATH.write_text(json.dumps({"repos": {}, "locks": [{
        "repo": "CRIBA", "path": "src/old.py", "holder": "h", "acquired_at": "t", "reason": "r", "token": token,
    }]}))
    with pytest.raises(ValueError):
        tool.acquire_lock("CRIBA", "src/new.py", "new", "r")


@pytest.mark.parametrize("sequence", [True, "4", -1, None])
def test_invalid_lock_sequence_is_not_coerced(tmp_path, sequence):
    tool = load_tool(tmp_path)
    tool.STATE_PATH.write_text(json.dumps({"repos": {}, "locks": [], "lock_seq": sequence}))
    with pytest.raises(ValueError):
        tool.acquire_lock("CRIBA", "src/a.py", "h", "r")


def test_legacy_tokenless_lock_remains_usable(tmp_path):
    tool = load_tool(tmp_path)
    tool.STATE_PATH.write_text(json.dumps({"repos": {}, "locks": [{
        "repo": "CRIBA", "path": "src/old.py", "holder": "legacy", "acquired_at": "t", "reason": "r",
    }]}))
    assert not tool.acquire_lock("CRIBA", "src/old.py", "other", "r")
    assert tool.acquire_lock("CRIBA", "src/new.py", "new", "r")
    assert tool.release_lock("CRIBA", "src/old.py", "legacy")


def test_alias_parent_conflicts_and_disjoint_scopes(tmp_path):
    tool = load_tool(tmp_path)
    assert tool.acquire_lock("CRIBA", "src/criba", "a", "r")
    assert not tool.acquire_lock("BLACKFORGE", "src/criba/a.py", "b", "r")
    assert tool.acquire_lock("SUPRA", "src/a.py", "b", "r")


def test_recovery_fences_stale_token(tmp_path):
    tool = load_tool(tmp_path)
    assert tool.acquire_lock("CRIBA", "src/a.py", "a", "r")
    old = json.loads(tool.STATE_PATH.read_text())["locks"][0]["token"]
    current = tool.recover_lock("CRIBA", "src/a.py", "b", "r")
    assert current["token"] > old
    assert not tool.release_lock("CRIBA", "src/a.py", "b", old)
    assert tool.release_lock("CRIBA", "src/a.py", "b", current["token"])


def test_thread_race_has_single_winner(tmp_path):
    tool = load_tool(tmp_path)
    barrier = threading.Barrier(4)
    def worker(index):
        barrier.wait()
        return tool.acquire_lock("CRIBA", "src/a.py", f"h-{index}", "r")
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(worker, range(4))) == 1


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def git_fixture(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Isolated test")
    git(repo, "config", "user.email", "isolated@example.invalid")
    meta = repo / "criba-blackforge/.hermes/iie/checkpoint.json"
    meta.parent.mkdir(parents=True)
    meta.write_text("{}")
    (repo / "supra").mkdir()
    (repo / "supra/keep").write_text("base")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD")
    meta.write_text('{"checkpoint":1}')
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "metadata")
    return repo, base, git(repo, "rev-parse", "HEAD")


def test_real_monorepo_metadata_advance_is_recognized(tmp_path):
    repo, base, head = git_fixture(tmp_path)
    tool = load_tool(tmp_path)
    paths = tool._changed_paths_since(str(repo / "criba-blackforge"), base)
    assert paths == ["criba-blackforge/.hermes/iie/checkpoint.json"]
    assert tool._is_metadata_only_advance(paths)


def test_future_record_is_not_a_metadata_advance(tmp_path):
    repo, base, future = git_fixture(tmp_path)
    git(repo, "checkout", "--detach", base)
    tool = load_tool(tmp_path)
    assert tool._changed_paths_since(str(repo / "criba-blackforge"), future) == []


@pytest.mark.parametrize("paths,expected", [
    ([".hermes/iie/STATE.json"], True), (["criba-blackforge/.hermes/iie/STATE.json"], True),
    (["criba-blackforge/.hermes/iie/STATE.json", "supra/src/service.py"], False), ([], False),
])
def test_metadata_predicate_never_hides_product_changes(tmp_path, paths, expected):
    assert load_tool(tmp_path)._is_metadata_only_advance(paths) is expected


def test_snapshot_does_not_mint_last_good_from_unverified_head(tmp_path):
    repo, base, head = git_fixture(tmp_path)
    tool = load_tool(tmp_path)
    tool.PHYSICAL_REPOS = {"CRIBA": str(repo / "criba-blackforge"), "SUPRA": str(repo / "supra")}
    state = tool.snapshot()
    assert state["repos"]["CRIBA"]["commit"] == head
    assert state["repos"]["CRIBA"]["last_good_commit"] == ""
    assert state["repos"]["SUPRA"]["last_good_commit"] == ""
    assert state["repos"]["BLACKFORGE"]["last_good_commit"] == ""


def test_snapshot_preserves_previously_recorded_last_good(tmp_path):
    repo, base, head = git_fixture(tmp_path)
    tool = load_tool(tmp_path)
    tool.PHYSICAL_REPOS = {"CRIBA": str(repo / "criba-blackforge"), "SUPRA": str(repo / "supra")}
    tool.STATE_PATH.write_text(json.dumps({"repos": {"CRIBA": {"last_good_commit": base, "last_good_tests": ["reported historically"]}}, "locks": []}))
    state = tool.snapshot()
    assert state["repos"]["CRIBA"]["last_good_commit"] == base
    assert state["repos"]["CRIBA"]["last_good_tests"] == ["reported historically"]
    assert state["repos"]["BLACKFORGE"]["last_good_commit"] == ""
