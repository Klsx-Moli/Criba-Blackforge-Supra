"""ASTRA-002/009: unknown structure never earns demonstrated diversity."""

from criba.diversity_selector import _structural_distance
from criba.similarity import classify

FIELDS = ("mechanism", "trust_model", "topology", "actor", "time_model")


def genome(**known):
    values = {field: ["unknown"] for field in FIELDS}
    values.update({field: [value] for field, value in known.items()})
    return {"genome": values}


def test_astra_002_known_same_and_known_distinct():
    same_a = genome(mechanism="m1", trust_model="t1", topology="x1", actor="a1", time_model="z1")
    same_b = genome(mechanism="m1", trust_model="t1", topology="x1", actor="a1", time_model="z1")
    distinct = genome(mechanism="m2", trust_model="t2", topology="x2", actor="a2", time_model="z2")
    assert _structural_distance(same_a, same_b) == 0.0
    assert _structural_distance(same_a, distinct) == 1.0


def test_astra_002_unknown_vs_known_and_unknown_vs_unknown_are_not_diverse():
    unknown = genome()
    known = genome(mechanism="m", trust_model="t", topology="x", actor="a", time_model="z")
    assert _structural_distance(unknown, known) == 0.0
    assert _structural_distance(unknown, unknown) == 0.0
    assert classify(unknown["genome"], unknown["genome"])["verdict"] == "insufficient_evidence"


def test_astra_009_partial_distance_uses_only_demonstrated_information():
    a = genome(mechanism="m1")
    b = genome(mechanism="m2")
    partial = _structural_distance(a, b)
    assert 0.0 < partial < 1.0
    assert _structural_distance(genome(), b) == 0.0


def test_astra_009_ablating_information_cannot_raise_demonstrated_diversity():
    full_a = genome(mechanism="m1", trust_model="t1", topology="x1")
    full_b = genome(mechanism="m2", trust_model="t2", topology="x2")
    ablated_a = genome(mechanism="m1")
    ablated_b = genome(mechanism="m2")
    assert _structural_distance(ablated_a, ablated_b) <= _structural_distance(full_a, full_b)
