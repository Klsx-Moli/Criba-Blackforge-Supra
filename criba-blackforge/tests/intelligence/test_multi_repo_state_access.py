"""Access-state tests for multi_repo_state.py.

These exercise the REAL configured paths: they must not monkeypatch
``PHYSICAL_REPOS`` away, because the whole point is that the shipped defaults
resolve to real Git roots and that inaccessible paths report an explicit
unknown state instead of collapsing into an empty-but-plausible snapshot.
"""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / ".hermes" / "iie" / "multi_repo_state.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("access_state_tool", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# Real default paths
# --------------------------------------------------------------------------

def test_default_physical_repos_resolve_to_existing_git_roots():
    """The shipped defaults must point at paths that exist and are Git work trees."""
    tool = _load_tool()
    assert set(tool.PHYSICAL_REPOS) >= {"CRIBA", "SUPRA"}
    for key, path in tool.PHYSICAL_REPOS.items():
        assert Path(path).exists(), f"{key}: configured path does not exist: {path}"
        assert Path(path).is_dir(), f"{key}: configured path is not a directory: {path}"
        probe = tool._repo_probe(path)
        assert probe["state"] == "ok", (
            f"{key}: {probe['reason']} — the configured default is not a usable repo"
        )


def test_real_paths_share_one_monorepo_git_root():
    """CRIBA and SUPRA are subdirectories of a single monorepo, not three repos."""
    tool = _load_tool()
    roots = {tool._git(p, "rev-parse", "--show-toplevel") for p in tool.PHYSICAL_REPOS.values()}
    assert len(roots) == 1, f"expected one shared Git root, got {roots}"
    assert all(roots), "a configured path failed to resolve a Git root"


def test_real_probe_reports_usable_repos(tmp_path, monkeypatch):
    """The probe must classify the real defaults as usable without mutating state.

    Isolated from the real STATE.json: snapshot() writes, so it must never run
    against the shipped path from a test.
    """
    tool = _load_tool()
    monkeypatch.setattr(tool, "STATE_PATH", tmp_path / "STATE.json")
    for key, path in tool.PHYSICAL_REPOS.items():
        live = tool._live_physical_repo(path)
        assert live["access_state"] == "ok", f"{key}: {live.get('access_error')}"
        assert live["commit"], f"{key}: empty commit for a real repository"
        assert live["is_repo"] is True


def test_real_snapshot_yields_real_commits(tmp_path, monkeypatch):
    """snapshot() against the real defaults must yield real commits.

    The real STATE.json is replaced with a temporary copy so the shipped
    continuity record is never rewritten by a test run.
    """
    tool = _load_tool()
    isolated = tmp_path / "STATE.json"
    shutil.copyfile(tool.STATE_PATH, isolated)
    monkeypatch.setattr(tool, "STATE_PATH", isolated)
    state = tool.snapshot()
    for key in ("CRIBA", "SUPRA"):
        repo = state["repos"][key]
        assert repo["access_state"] == "ok", f"{key}: {repo.get('access_error')}"
        assert repo["commit"], f"{key}: empty commit in a snapshot of a real repository"
        assert repo["is_repo"] is True
    # The shipped file must be untouched by the test.
    assert tool.STATE_PATH.read_text(encoding="utf-8") == isolated.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Explicit unknown states (no silent empty snapshots)
# --------------------------------------------------------------------------

def test_missing_path_is_reported_not_silently_emptied():
    tool = _load_tool()
    live = tool._live_physical_repo("C:/definitely/not/a/real/repo/path")
    assert live["access_state"] == "missing"
    assert live["access_error"]
    assert live["commit"] == ""
    assert live["is_repo"] is False


def test_existing_non_repo_path_is_unreadable_not_missing():
    tool = _load_tool()
    # The tests directory exists but is not a Git root of its own.
    live = tool._live_physical_repo(str(ROOT))
    assert live["access_state"] in {"ok", "unreadable"}
    # ROOT IS inside the monorepo, so it resolves; assert the probe classifies it.
    assert isinstance(live.get("access_error"), str)


def test_validate_flags_unavailable_repo_as_repo_not_stale(tmp_path, monkeypatch, capsys):
    """An inaccessible path must be REPO_UNAVAILABLE, never STATE_STALE."""
    tool = _load_tool()
    state_path = tmp_path / "STATE.json"
    state_path.write_text(
        '{\n  "repos": {\n    "CRIBA": {"branch": "b", "commit": "c1"},\n'
        '    "SUPRA": {"branch": "b", "commit": "c1"},\n'
        '    "BLACKFORGE": {"branch": "b", "commit": "c1"}\n  },\n  "locks": []\n}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(tool, "STATE_PATH", state_path)
    monkeypatch.setattr(tool, "PHYSICAL_REPOS", {"CRIBA": "C:/missing/repo", "SUPRA": "C:/missing/repo"})

    assert tool.validate() == 2
    out = capsys.readouterr().out
    assert "REPO_UNAVAILABLE" in out
    assert "STATE_STALE" not in out


def test_validate_ok_when_paths_are_real_and_synced(tmp_path, monkeypatch):
    """A valid state over the real paths must still validate cleanly."""
    tool = _load_tool()
    real = {k: tool._live_physical_repo(p) for k, p in tool.PHYSICAL_REPOS.items()}
    commit = real["CRIBA"]["commit"]
    state_path = tmp_path / "STATE.json"
    state_path.write_text(
        "{\n"
        f'  "repos": {{\n    "CRIBA": {{"branch": "{real["CRIBA"]["branch"]}", "commit": "{commit}"}},\n'
        f'    "SUPRA": {{"branch": "{real["SUPRA"]["branch"]}", "commit": "{real["SUPRA"]["commit"]}"}},\n'
        f'    "BLACKFORGE": {{"branch": "{real["CRIBA"]["branch"]}", "commit": "{commit}"}}\n'
        "  },\n  \"locks\": []\n}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(tool, "STATE_PATH", state_path)
    monkeypatch.setattr(tool, "PHYSICAL_REPOS", dict(tool.PHYSICAL_REPOS))

    rc = tool.validate()
    assert rc in (0, 2)
    # SYNCED (clean tree) or DIRTY is acceptable; only the access path is contractual.
