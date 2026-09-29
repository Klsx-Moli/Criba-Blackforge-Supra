"""ASTRA-004/027/032/035 scope and firewall guards."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

_FORBIDDEN_RESEARCH_MARKERS = {
    "hidden_eval",
    "ground_truth",
    "holdout_registry",
    "candidate_set_registry",
    "selector_trial",
}


def _python_semantic_tokens(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tokens: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            tokens.extend(alias.name.casefold() for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            tokens.append((node.module or "").casefold())
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            tokens.append(node.value.casefold())
    return tokens


def test_astra_004_product_runtime_has_no_hidden_evaluation_dependency():
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        for token in _python_semantic_tokens(path):
            if any(marker in token for marker in _FORBIDDEN_RESEARCH_MARKERS):
                offenders.append(f"{path.relative_to(ROOT)}: {token[:120]}")
    assert offenders == []


def test_astra_032_anti_goodhart_runtime_is_isolated_and_standard_disabled():
    decisional_paths = [
        SRC / "criba" / "engine.py",
        SRC / "criba" / "lottery.py",
        SRC / "criba" / "inventar.py",
        SRC / "criba" / "model_runtime.py",
        SRC / "criba" / "diversity_selector.py",
        SRC / "criba" / "intelligence" / "outcome_store.py",
    ]
    offenders: list[str] = []
    for path in decisional_paths:
        for token in _python_semantic_tokens(path):
            if "anti_goodhart" in token:
                offenders.append(f"{path.relative_to(ROOT)}: {token[:120]}")
    assert offenders == []

    status = (ROOT / "governance" / "ANTI_GOODHART_STATUS.yaml").read_text(
        encoding="utf-8"
    )
    assert "STANDARD: DISABLED" in status
    assert "G3_DEPLOYMENT_ISOLATION_NOT_VERIFIED" in status
