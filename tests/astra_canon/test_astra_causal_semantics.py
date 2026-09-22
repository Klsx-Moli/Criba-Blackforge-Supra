"""Behavioral sentinels for ASTRA-030 causal composition semantics."""

import pytest

from criba.causal_v2 import (
    BASE_STATE,
    Axis,
    CausalState,
    FamilySpec,
    InteractionType,
    OperatorType,
    compose_interventions,
)


def _invert_spec(*, preconditions=()):
    return FamilySpec(
        family_id="F",
        name="invert",
        operator=OperatorType.INVERT,
        primary_axis=Axis.AX09_ESTRUCTURA,
        preconditions=tuple(preconditions),
    )


def test_astra_030_preconditions_are_preserved_when_not_evaluated():
    state = CausalState()
    intervention = state.apply(_invert_spec(preconditions=("approved",)), target="x")
    assert intervention.preconditions == ("approved",)
    assert intervention.precondition_status == "NOT_EVALUATED"
    assert intervention.unmet_preconditions == ("approved",)


def test_astra_030_explicitly_unsatisfied_precondition_blocks_application():
    state = CausalState()
    with pytest.raises(ValueError, match="preconditions no satisfechas"):
        state.apply(
            _invert_spec(preconditions=("approved",)),
            target="x",
            context={"satisfied_preconditions": []},
        )
    assert state.interventions == []
    assert state.vector == BASE_STATE


def test_astra_030_cancelling_interaction_materializes_only_when_composed():
    state = CausalState()
    spec = _invert_spec()
    state.apply(spec, target="x")
    state.apply(spec, target="x")
    assert any(kind == InteractionType.CANCELLING for _, _, kind in state.interactions)
    compose_interventions(state)
    assert state.vector[Axis.AX09_ESTRUCTURA] == BASE_STATE[Axis.AX09_ESTRUCTURA]
