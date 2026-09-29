"""ASTRA B01 sentinels: persisted project state must be host-independent.

Constitutional contract under test
---------------------------------
Persisted project identity is evidence lineage, not cache. A project written by
one host must be byte-reproducible and re-readable by any other host, otherwise
`get_project` returns `None` for a project that demonstrably exists and the
system silently answers 404 / 409 / 500 as if lineage had never been recorded.

The defect class this module pins
---------------------------------
`_persist_project` wrote through `tempfile.NamedTemporaryFile(mode="w")` with no
`encoding=`. Text-mode files without an explicit encoding resolve to the *locale*
encoding (ANSI code page on Windows), while `get_project` reads back with
`encoding="utf-8"`. Any project whose serialized state contains a non-ASCII
character is therefore written as e.g. cp1252 byte 0xB7 and cannot be decoded as
UTF-8: `UnicodeDecodeError`, swallowed into `return None`, project gone.

Sentinel strength (false-coverage audit, ASTRA 49)
-------------------------------------------------
- `test_persisted_project_bytes_are_canonical_utf8` is byte-exact and asserts
  LF-only newlines, so it catches the `\r\n`-on-Windows divergence on any host.
- `test_persistence_survives_hostile_non_utf8_locale` runs the real persistence
  API in a subprocess with `-X utf8=0` and `LC_ALL=C`, forcing a non-UTF-8
  default encoding on Linux/macOS (ASCII) *and* Windows (cp1252). That is the
  only construction which makes an encoding regression manifest even on a UTF-8
  host, so it is the mutation-discriminating sentinel. It runs unconditionally:
  no skip, no xfail, no tolerant comparison.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from supra_agentic.state import ProjectStateManager

# A non-ASCII objective is the minimal realistic trigger: the persisted posture
# embeds it verbatim in `objective` and in the RECEIVED checkpoint summary.
NON_ASCII_OBJECTIVE = "Evaluar deriva térmica · envío real… ¿calibración?"

HOSTILE_LOCALE_SCRIPT = """
import sys
from pathlib import Path

from supra_agentic.models import CheckpointRecord, TaskmasterStage
from supra_agentic.state import ProjectStateManager

storage = Path(sys.argv[1])
objective = sys.argv[2]

manager = ProjectStateManager(storage)
posture = manager.create_project(objective, project_id="locale-probe")
posture.checkpoints.append(
    CheckpointRecord(
        stage=TaskmasterStage.RECEIVED,
        title="Manual · checkpoint",
        evidence_summary="resumen · con acentos —Mid·s",
        actor="human:locale-probe",
    )
)
manager._persist_project("locale-probe")

# Simulate a fresh process: authoritative state must reload from disk.
manager._projects.clear()
reloaded = manager.get_project("locale-probe")

if reloaded is None:
    raise SystemExit("PERSISTED_STATE_UNREADABLE_AFTER_CACHE_CLEAR")
if reloaded.objective != objective:
    raise SystemExit("OBJECTIVE_CORRUPTED_ACROSS_RESTART")
if not any("\\u00b7" in c.evidence_summary for c in reloaded.checkpoints):
    raise SystemExit("CHECKPOINT_CORRUPTED_ACROSS_RESTART")
print("ROUNDTRIP_OK")
"""


def _hostile_locale_env() -> dict[str, str]:
    """Environment that forces a non-UTF-8 default encoding for file writes."""
    env = dict(os.environ)
    for key in ("PYTHONUTF8", "PYTHONIOENCODING", "PYTHONCOERCECLOCALE"):
        env.pop(key, None)
    env.update({"LC_ALL": "C", "LANG": "C", "PYTHONUTF8": "0"})
    return env


def test_persisted_project_bytes_are_canonical_utf8() -> None:
    """On-disk bytes are exactly the canonical UTF-8 serialization, LF-only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ProjectStateManager(Path(tmpdir))
        posture = manager.create_project(NON_ASCII_OBJECTIVE, project_id="byte-contract")
        raw = (Path(tmpdir) / "byte-contract.json").read_bytes()

    assert raw == posture.model_dump_json(indent=2).encode("utf-8")
    assert b"\r\n" not in raw
    assert json.loads(raw.decode("utf-8"))["objective"] == NON_ASCII_OBJECTIVE


def test_project_with_non_ascii_state_survives_cache_clear() -> None:
    """Non-ASCII state must round-trip through disk on the running host."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ProjectStateManager(Path(tmpdir))
        manager.create_project(NON_ASCII_OBJECTIVE, project_id="roundtrip")

        manager._projects.clear()
        reloaded = manager.get_project("roundtrip")

    assert reloaded is not None, "persisted project became unreadable"
    assert reloaded.objective == NON_ASCII_OBJECTIVE


def test_persistence_survives_hostile_non_utf8_locale() -> None:
    """Real persistence under a forced non-UTF-8 locale must not lose lineage."""
    src_root = str(Path(__file__).resolve().parents[2] / "src")
    with tempfile.TemporaryDirectory() as tmpdir:
        completed = subprocess.run(
            [sys.executable, "-X", "utf8=0", "-c", HOSTILE_LOCALE_SCRIPT,
             tmpdir, NON_ASCII_OBJECTIVE],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            env={**_hostile_locale_env(), "PYTHONPATH": src_root},
        )
        artifacts = {
            path.name: path.read_bytes() for path in sorted(Path(tmpdir).glob("*.json"))
        }

    assert completed.returncode == 0, (
        "persistence lost project lineage under a non-UTF-8 locale:\n"
        f"stdout={completed.stdout!r}\nstderr={completed.stderr!r}"
    )
    assert "ROUNDTRIP_OK" in completed.stdout
    assert artifacts, "no project artifact was written"
    for name, raw in artifacts.items():
        # Every persisted artifact must be valid UTF-8 regardless of host locale.
        assert json.loads(raw.decode("utf-8"))["project_id"] == Path(name).stem
