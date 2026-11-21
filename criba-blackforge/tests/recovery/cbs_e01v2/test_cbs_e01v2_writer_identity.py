import importlib.util
from pathlib import Path

import pytest

_support_spec = importlib.util.spec_from_file_location(
    "cbs_e01v2_support", Path(__file__).with_name("cbs_e01v2_helpers.py")
)
assert _support_spec is not None and _support_spec.loader is not None
_support = importlib.util.module_from_spec(_support_spec)
_support_spec.loader.exec_module(_support)
dossier, invoke = _support.dossier, _support.invoke


@pytest.mark.parametrize(
    "identity",
    [" dossier-ef04-valid", "dossier-ef04-valid ", "\tdossier-ef04-valid", "dossier-ef04-valid\n"],
)
def test_writer_rejects_outer_whitespace_in_identity(home, identity):
    result = invoke(home, "save", payload=dossier(identity))
    assert not result["ok"] and result["error_type"] == "ValueError", result
