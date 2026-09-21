"""Condition 14 — mandatory unknown handling in genome similarity.

Covers every case in the gate. similarity() returns similarity + coverage and
NEVER classifies duplicate when coverage < MIN_DUPLICATE_COVERAGE.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pytest

from criba.similarity import MIN_DUPLICATE_COVERAGE, classify, genome_distance


def G(**kw):
    base = {"mechanism": ["unknown"], "topology": ["unknown"], "trust_model": ["unknown"],
            "actor": ["unknown"], "time_model": ["unknown"]}
    base.update(kw)
    return base


def test_all_unknown_similarity_zero():
    r = genome_distance(G(), G())
    assert r["similarity"] == 0.0
    assert r["coverage"] == 0.0


def test_empty_vs_complete_low_similarity():
    r = genome_distance(G(), G(mechanism=["verification"], topology=["mesh"],
                                trust_model=["evidence_based"], actor=["autonomous_agent"],
                                time_model=["ephemeral_per_operation"]))
    assert r["similarity"] < 0.5


def test_single_known_equal_field_low_coverage():
    r = genome_distance(G(mechanism=["verification"]), G(mechanism=["verification"]))
    # only mechanism known -> low coverage, but the known comparison itself
    # is an exact match. Unknown dimensions cannot manufacture dissimilarity.
    assert r["coverage"] < MIN_DUPLICATE_COVERAGE
    assert r["similarity"] == 1.0


def test_nearly_empty_is_insufficient_evidence_not_distinct():
    r = classify(G(), G())
    assert r["verdict"] != "probable_duplicate"
    assert r["verdict"] == "insufficient_evidence"


def test_unknown_sets_no_jaccard_one():
    # {"unknown"} vs {"unknown"} -> NOT Jaccard 1
    r = genome_distance(G(mechanism=["unknown"]), G(mechanism=["unknown"]))
    assert r["similarity"] == 0.0


def test_unknown_ignored_in_jaccard():
    a = G(mechanism=["verification", "unknown"])
    b = G(mechanism=["verification"])
    r = genome_distance(a, b)
    # unknown stripped; the only comparable field is an exact match.
    assert r["similarity"] == 1.0
    assert r["coverage"] < MIN_DUPLICATE_COVERAGE


def test_low_coverage_blocks_duplicate_even_if_partial_high():
    # same mechanism, everything else unknown -> high partial sim but coverage low
    r = classify(G(mechanism=["verification"]), G(mechanism=["verification"]))
    assert r["verdict"] != "probable_duplicate"


def test_coverage_in_output():
    r = genome_distance(G(mechanism=["verification"]), G(mechanism=["verification"]))
    for k in ("similarity", "coverage", "comparable_weight", "matching_fields",
              "different_fields", "unknown_fields"):
        assert k in r, f"falta {k} en salida de similitud"
