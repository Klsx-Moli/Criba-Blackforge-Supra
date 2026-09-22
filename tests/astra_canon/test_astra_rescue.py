"""ASTRA-015/016: rescue is scoped to evaluator/protocol/conditions."""

from criba.rescate import Bloqueo, Complemento, probar_rescate


def objects():
    return (Bloqueo("a", "A", "condition", "change"), Complemento("b", "B", "transform"))


def test_astra_016_rescued_wording_is_scoped_and_no_new_capability_claim():
    a, b = objects()
    result = probar_rescate(
        a,
        b,
        lambda mechanism, context: 0.9 if "+" in mechanism else 0.2,
        contexto="conditions C",
        evaluator_id="E1",
        protocol_id="P1",
    )
    assert result.verdict == "RESCUED"
    assert result.evaluator_id == "E1" and result.protocol_id == "P1"
    assert "under evaluator E1 and protocol P1" in result.reason
    assert "new capability" not in result.reason.lower()
    assert "capacidad" not in result.reason.lower()


def test_astra_016_not_rescued_does_not_invent_unmeasured_explanation():
    a, b = objects()
    result = probar_rescate(
        a, b, lambda mechanism, context: 0.2, evaluator_id="E1", protocol_id="P1"
    )
    assert result.verdict == "NOT_RESCUED"
    assert "longer explanation" not in result.reason.lower()
    assert "explicación más larga" not in result.reason.lower()
