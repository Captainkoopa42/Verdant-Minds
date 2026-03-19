"""Unit tests for reactive VCult condition evaluation."""

from __future__ import annotations

from cultivation.schemas import ScaffoldContext
from cultivation.spec_conditions import ConditionEvaluator, SystemState


def _state(**kwargs) -> SystemState:
    context = ScaffoldContext(
        total_nodes=100,
        emergent_count=kwargs.pop("emergent_count", 0),
        basin_count=kwargs.pop("basin_count", 0),
        basin_emergent_distribution=kwargs.pop("basin_emergent_distribution", {"basin_0": 3}),
        top_concepts=["ethics", "causality"],
        recent_emergents=["Emergent_1"],
        earlier_share=kwargs.pop("earlier_share", 1.0),
        cycle=kwargs.pop("cycle", 0),
        dormant_basin_count=kwargs.pop("dormant_basin_count", 0),
        t_g=kwargs.pop("t_g", 0.5),
        recent_bud_events=kwargs.pop("recent_bud_events", []),
    )
    return SystemState(
        scaffold_context=context,
        cycle=context.cycle,
        phase_cycle=kwargs.pop("phase_cycle", context.cycle),
        emergent_rate_history=kwargs.pop("emergent_rate_history", []),
        self_referential_count=kwargs.pop("self_referential_count", 0),
        last_bud_cycle=kwargs.pop("last_bud_cycle", None),
    )


def test_simple_comparisons() -> None:
    evaluator = ConditionEvaluator()

    assert evaluator.evaluate("emergent_count >= 50", _state(emergent_count=60)) is True
    assert evaluator.evaluate("emergent_count >= 50", _state(emergent_count=30)) is False
    assert evaluator.evaluate("basin_count >= 3", _state(basin_count=3)) is True


def test_rolling_average() -> None:
    evaluator = ConditionEvaluator()
    state = _state(emergent_rate_history=[0.2] * 20, cycle=20)
    high_state = _state(emergent_rate_history=[0.7] * 20, cycle=20)

    assert evaluator.evaluate("emergent_rate < 0.5 for 20 cycles", state) is True
    assert evaluator.evaluate("emergent_rate < 0.5 for 20 cycles", high_state) is False


def test_combinators() -> None:
    evaluator = ConditionEvaluator()
    state = _state(emergent_count=60, basin_count=3)
    partial = _state(emergent_count=60, basin_count=1)
    failed = _state(emergent_count=10, basin_count=1)

    assert evaluator.evaluate({"all": ["emergent_count >= 50", "basin_count >= 3"]}, state) is True
    assert evaluator.evaluate({"all": ["emergent_count >= 50", "basin_count >= 3"]}, partial) is False
    assert evaluator.evaluate({"any": ["emergent_count >= 50", "basin_count >= 3"]}, partial) is True
    assert evaluator.evaluate({"any": ["emergent_count >= 50", "basin_count >= 3"]}, failed) is False


def test_temporal_conditions() -> None:
    evaluator = ConditionEvaluator()

    assert evaluator.evaluate("latest_bud_within 3 cycles", _state(cycle=50, last_bud_cycle=48)) is True
    assert evaluator.evaluate("latest_bud_within 3 cycles", _state(cycle=50, last_bud_cycle=40)) is False
    assert evaluator.evaluate("no_bud_for 10 cycles", _state(cycle=50, last_bud_cycle=40)) is True
    assert evaluator.evaluate("no_bud_for 10 cycles", _state(cycle=50, last_bud_cycle=48)) is False
