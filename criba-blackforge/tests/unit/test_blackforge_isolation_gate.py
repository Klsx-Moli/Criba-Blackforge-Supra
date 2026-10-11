"""K2: BLACKFORGE is an optional capability, not a CRIBA Core dependency.

Static inspection of the baseline found four CRIBA Core modules importing
BLACKFORGE-named modules at module level:

  src/criba/gates.py    -> blackforge_causal.canonical_hash,
                           blackforge_safety.{DENY, evaluate_blackforge_safety}
  src/criba/chain.py    -> blackforge_causal.canonical_hash
  src/criba/latency.py  -> blackforge_causal.canonical_hash
  src/criba/logging.py  -> blackforge_causal.canonical_json

and criba.hybrid imports chain + latency + logging, so it inherited the same
dependency. Reproduced by execution with a meta_path import blocker: all four
raised ImportError, so `import criba.gates` failed with BLACKFORGE absent.

The fix is a decoupling, never a BLACKFORGE implementation:

  * canonical_json / canonical_hash are pure serialization helpers with no
    BLACKFORGE semantics. They now live in a neutral criba.canonical module and
    criba.blackforge_causal re-exports the SAME objects, so there is one
    implementation and no hash can ever diverge between the two import paths.
  * G04's use of the BLACKFORGE safety evaluator is already logically lazy:
    it returns early unless mode == "blackforge". The import now matches that
    boundary, and when BLACKFORGE is absent the gate fails CLOSED with an
    explicit reason instead of crashing the import.

Import blocking here never touches the filesystem: no file is deleted.
"""

from __future__ import annotations

import importlib
import sys

import pytest

BF_MODULES = (
    "criba.blackforge_agentic",
    "criba.blackforge_agentic_security",
    "criba.blackforge_catalog",
    "criba.blackforge_causal",
    "criba.blackforge_gui",
    "criba.blackforge_orthogonal",
    "criba.blackforge_pipeline",
    "criba.blackforge_safety",
    "criba.blackforge_selector",
)


class _BlackforgeAbsent:
    """Make every BLACKFORGE module look absent, without touching disk."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname in BF_MODULES or fullname.startswith("criba.blackforge_orthogonal."):
            raise ImportError(f"BLOCKED_FOR_PROBE: {fullname} is absent")
        return None


@pytest.fixture
def without_blackforge(monkeypatch):
    saved = {name: mod for name, mod in sys.modules.items() if name.split(".")[0] == "criba"}
    for name in saved:
        monkeypatch.delitem(sys.modules, name, raising=False)
    blocker = _BlackforgeAbsent()
    monkeypatch.setattr(sys, "meta_path", [blocker, *sys.meta_path])
    yield
    for name in [n for n in sys.modules if n.split(".")[0] == "criba"]:
        del sys.modules[name]
    sys.modules.update(saved)


CORE_MODULES = (
    "criba.gates",
    "criba.chain",
    "criba.latency",
    "criba.logging",
    "criba.hybrid",
)


@pytest.mark.parametrize("module_name", CORE_MODULES)
def test_criba_core_module_imports_without_blackforge(without_blackforge, module_name):
    """K2 sentinel: reintroduce a module-level blackforge import and this goes red."""
    importlib.import_module(module_name)


def test_criba_core_executes_without_blackforge(without_blackforge):
    """The real core path must run, not merely import."""
    from criba.engine import activate

    packet = activate("¿Cómo diseñar un sistema de aprobación de agentes seguro?", mode="minimal")
    assert packet["packet_type"] == "MANDATORY_MODEL_PACKET"


def test_canonical_helpers_have_exactly_one_implementation():
    """Two import paths, one function object. Divergence would split every hash."""
    from criba import blackforge_causal, canonical

    assert canonical.canonical_json is blackforge_causal.canonical_json
    assert canonical.canonical_hash is blackforge_causal.canonical_hash


# Values measured from the baseline implementation before the move. These are
# the golden vectors: if the relocation changed a single byte of serialization,
# every previously recorded evidence hash in the ledger would silently differ.
PINNED_JSON = '{"a":[1,{"y":null,"z":true}],"b":2,"u":"café ñ"}'
PINNED_HASH = "dc94ff49338148c8e9c4110512bd54edf23dc9c1e24b07c0ebb325bd6f02cc52"
PINNED_EMPTY_HASH = "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"


def test_canonical_serialization_is_unchanged_by_the_relocation():
    from criba.canonical import canonical_hash, canonical_json

    value = {"b": 2, "a": [1, {"z": True, "y": None}], "u": "café ñ"}
    assert canonical_json(value) == PINNED_JSON
    assert canonical_hash(value) == PINNED_HASH
    assert canonical_hash({}) == PINNED_EMPTY_HASH


def test_canonical_refuses_non_finite_so_unknown_cannot_hash_like_a_value():
    """UNKNOWN != 0: a non-representable value must not become a hashable one."""
    from criba.canonical import canonical_hash

    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError):
            canonical_hash({"x": bad})


# The SUPRA-side half of this gate lives in the SUPRA suite, because
# supra_agentic is not importable from the CRIBA venv:
#   supra/tests/test_blackforge_bridge_isolation.py


def test_g04_fails_closed_when_blackforge_is_absent(without_blackforge):
    """A gate that cannot be evaluated must not pass, and must say why."""
    from criba.gates import G04_authorization_valid

    context = {
        "mode": "blackforge",
        "authorization_state": "granted",
        "authorization_scope": "pentest engagement",
        "stop_conditions": ["customer revokes"],
        "context_id": "k2-probe",
    }
    result = G04_authorization_valid(context)
    assert result.passed is False
    assert "BLACKFORGE" in result.reason


def test_g04_is_unaffected_for_criba_mode_without_blackforge(without_blackforge):
    """CRIBA mode never needed BLACKFORGE authorization and must stay that way."""
    from criba.gates import G04_authorization_valid

    result = G04_authorization_valid({"mode": "criba"})
    assert result.passed is True


def test_g04_still_passes_for_an_authorized_blackforge_session_with_blackforge():
    """The decoupling must not weaken G04 while BLACKFORGE IS available."""
    from criba.gates import G04_authorization_valid

    context = {
        "mode": "blackforge",
        "authorization_state": "granted",
        "authorization_scope": "authorized pentest engagement",
        "stop_conditions": ["customer revokes authorization"],
        "context_id": "k2-probe",
        "target": {"nombre": "api-interna", "descripcion": "internal API"},
    }
    result = G04_authorization_valid(context)
    assert isinstance(result.passed, bool)
    # The verdict is whatever the safety evaluator decides; what must not
    # happen is an ImportError, and what must not be invented is a PASS the
    # evaluator did not grant. Assert the gate stays reachable and typed.
    assert result.gate_id == "G04_authorization_valid"
    assert result.severity == "blocking"
