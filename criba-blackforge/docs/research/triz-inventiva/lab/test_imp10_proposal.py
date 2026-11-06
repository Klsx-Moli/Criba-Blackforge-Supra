"""Comprueba el diff IMP-10 en memoria; NO modifica módulos del producto."""
from __future__ import annotations

import difflib
import hashlib
import json
import types
from pathlib import Path

import pytest

BUNDLE = Path(__file__).resolve().parents[1]
REPO = BUNDLE.parents[3]
EVIDENCE_BUNDLE = BUNDLE / "evidence" / "resume_20261028" / "before"

pytestmark = pytest.mark.skipif(
    not EVIDENCE_BUNDLE.is_dir(),
    reason=(
        "Historical IMP-10 evidence bundle is not versioned; current contract is "
        "covered by tests/unit/test_lossless_operations_contract.py"
    ),
)


def _projected():
    metadata = BUNDLE / "imp10_integration" / "lossless_operations.json"
    assert metadata.is_file(), "Falta la propuesta exacta IMP-10, todavía no aplicada"
    specification = json.loads(metadata.read_text(encoding="utf-8"))
    modules = {}
    diffs = []
    for change in specification["changes"]:
        baseline_path = BUNDLE / "evidence/resume_20261028/before" / change["path"]
        original = baseline_path.read_text(encoding="utf-8")
        assert hashlib.sha256(original.encode()).hexdigest() == change["before_sha256"]
        current = (REPO / change["path"]).read_text(encoding="utf-8")
        assert hashlib.sha256(current.encode()).hexdigest() in {
            change["before_sha256"], change["after_sha256"],
        }, "El módulo real difiere tanto de la baseline como del diff aprobado"
        baseline_module = types.ModuleType(change["test_module"] + "_before")
        baseline_module.__package__ = change["test_package"]
        exec(compile(original, change["path"] + " [IMMUTABLE_BEFORE]", "exec"),
             baseline_module.__dict__)
        modules["before_" + Path(change["path"]).stem] = baseline_module
        projected = original
        for replacement in change["replacements"]:
            assert projected.count(replacement["old"]) == replacement["count"]
            projected = projected.replace(replacement["old"], replacement["new"])
        assert hashlib.sha256(projected.encode()).hexdigest() == change["after_sha256"]
        diffs.extend(difflib.unified_diff(
            original.splitlines(keepends=True), projected.splitlines(keepends=True),
            fromfile="a/" + change["path"], tofile="b/" + change["path"],
        ))
        module = types.ModuleType(change["test_module"])
        module.__package__ = change["test_package"]
        exec(compile(projected, change["path"] + " [PROPOSED_NOT_APPLIED]", "exec"),
             module.__dict__)
        modules[Path(change["path"]).stem] = module
    patch = BUNDLE / "imp10_integration" / "lossless_operations.diff"
    assert patch.read_text(encoding="utf-8") == "".join(diffs)
    return modules


@pytest.mark.parametrize("seed", [0, 1, 42])
def test_exact_proposal_preserves_rng_scores_and_identity(seed):
    projected = _projected()
    methods = [
        {"id": "A", "title": "A", "family": "restricciones",
         "description": "Operación íntegra de separación temporal. " * 20 + "COLA_A"},
        {"id": "B", "title": "B", "family": "analogias",
         "description": "Operación íntegra de transferencia relacional. " * 20 + "COLA_B"},
    ]
    old = projected["before_lottery"].LotteryEngine.from_methods(
        methods, seed=seed, storage=None,
    )
    new = projected["lottery"].LotteryEngine.from_methods(methods, seed=seed, storage=None)
    before = old.generate_ideas_from_batch(old.methods)[0]
    after = new.generate_ideas_from_batch(new.methods)[0]
    assert old.rng.getstate() == new.rng.getstate()
    for key in before.keys() - {"method1_desc", "method2_desc"}:
        assert before[key] == after[key], key
    assert after["method1_desc"] == methods[0]["description"]
    assert after["method2_desc"] == methods[1]["description"]
    prompt = projected["contrato"].prompt_propuesta("Problema de prueba", after, {}, [])
    assert "COLA_A" in prompt and "COLA_B" in prompt


def test_exact_proposal_handles_quoted_and_multiline_operations():
    projected = _projected()
    idea = {
        "method1_desc": '"Separar" sin perder la condición\nni sus límites',
        "method2_desc": '"Transferir" la relación, no su nombre\nni apariencia',
    }
    # Conserva la reproducción histórica sobre el snapshot previo, no sobre el fix.
    with pytest.raises(AssertionError):
        projected["before_contrato"].prompt_propuesta("Problema de prueba", idea, {}, [])
    prompt = projected["contrato"].prompt_propuesta("Problema de prueba", idea, {}, [])
    recovered = json.loads(prompt.split("\nDATOS:\n", 1)[1])
    assert recovered["CRUCE"] == idea
