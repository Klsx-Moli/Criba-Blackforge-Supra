"""T061 wired into the real product consumer, not just a test-local registry.

`criba.intelligence.execution._INPUT_ADAPTERS` is the dispatch table the runtime
uses to resolve a technique id to its implementation. T061 must be resolvable
there, with the evidence-bounded adapter, and must return candidates tagged with
the T061 operator.
"""
from __future__ import annotations

import importlib

from criba.intelligence.contracts import EvidenceDocument
from criba.intelligence.execution import _INPUT_ADAPTERS


def test_t061_is_registered_in_the_runtime_dispatch_table() -> None:
    assert "T061" in _INPUT_ADAPTERS, "T061 must be wired in _INPUT_ADAPTERS"
    target = _INPUT_ADAPTERS["T061"][0]
    assert target.endswith("recombination.substitute_attributes"), target


def test_t061_adapter_resolves_evidence_and_returns_t061_candidates() -> None:
    """The real adapter resolves documents and the operator tags its output."""
    docs = [
        EvidenceDocument(doc_id="d1", metadata={"attributes": {"material": "steel"}}),
        EvidenceDocument(doc_id="d2", metadata={"attributes": {"material": "glass"}}),
    ]
    args, kwargs = _INPUT_ADAPTERS["T061"][1]("problem", {}, docs)
    module_name, func_name = _INPUT_ADAPTERS["T061"][0].rsplit(".", 1)
    handler = getattr(importlib.import_module(module_name), func_name)
    candidates = handler(*args, **kwargs)
    assert candidates, "T061 must propose candidates from explicit attributes"
    assert all(c.operators == ("T061",) for c in candidates)


def test_t061_adapter_returns_empty_without_evidence() -> None:
    """No documents, no candidates: the adapter never invents evidence."""
    args, kwargs = _INPUT_ADAPTERS["T061"][1]("problem", {}, [])
    module_name, func_name = _INPUT_ADAPTERS["T061"][0].rsplit(".", 1)
    handler = getattr(importlib.import_module(module_name), func_name)
    assert handler(*args, **kwargs) == []


def test_t054_is_registered_in_the_runtime_dispatch_table() -> None:
    """T054 shares recombination.py with T061 but has its own contract and handler."""
    assert "T054" in _INPUT_ADAPTERS
    target = _INPUT_ADAPTERS["T054"][0]
    assert target.endswith("recombination.recombine_technologies"), target


def test_t054_adapter_returns_t054_candidates_from_explicit_technologies() -> None:
    docs = [
        EvidenceDocument(doc_id="d1", metadata={"technologies": {"laser": {}}}),
        EvidenceDocument(doc_id="d2", metadata={"technologies": {"mirror": {}}}),
    ]
    args, kwargs = _INPUT_ADAPTERS["T054"][1]("problem", {}, docs)
    module_name, func_name = _INPUT_ADAPTERS["T054"][0].rsplit(".", 1)
    handler = getattr(importlib.import_module(module_name), func_name)
    candidates = handler(*args, **kwargs)
    assert candidates and all(c.operators == ("T054",) for c in candidates)
