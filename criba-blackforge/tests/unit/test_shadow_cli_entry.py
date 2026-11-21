"""The public 'criba gui' command must launch only the canonical Shadow UI."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from criba.cli import main


def test_criba_gui_dispatches_to_shadow_launcher(monkeypatch):
    seen = []

    def run(args, *, check):
        seen.append((args, check))
        return subprocess.CompletedProcess(args, returncode=7)

    monkeypatch.setattr(subprocess, "run", run)
    code = main(["gui"])
    assert code == 7
    assert len(seen) == 1
    argv, check = seen[0]
    assert check is False
    assert argv[0] == sys.executable
    assert Path(argv[1]).name == "criba_shadow_main.py"
    assert Path(argv[1]).is_file()


def test_criba_gui_fails_explicitly_when_shadow_not_in_package(monkeypatch, capsys):
    # If the actual packaged install lacks Shadow, an old UI is never launched.
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    called = []

    def forbidden(*_args, **_kwargs):
        called.append(True)
        raise AssertionError("no old UI or subprocess allowed")

    monkeypatch.setattr(subprocess, "run", forbidden)
    assert main(["gui"]) == 2
    assert not called
    assert "Shadow" in capsys.readouterr().err


def test_legacy_database_flag_does_not_silently_select_wrong_shadow_state(monkeypatch, capsys):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("launch must fail before a process is started")

    monkeypatch.setattr(subprocess, "run", forbidden)
    assert main(["--database", "user-legacy.sqlite3", "gui"]) == 2
    message = capsys.readouterr().err
    assert "--database" in message
    assert "CRIBASHADOW_HOME" in message
