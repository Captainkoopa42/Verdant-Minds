"""Unit tests for verdant_v2.thermodynamics.phase."""

from __future__ import annotations

import pytest
from verdant_v2.thermodynamics.phase import PhaseState, compute_phase, compute_t_g


class TestComputePhase:
    """Test compute_phase returns correct PhaseState for each regime."""

    def test_rigid_phase(self) -> None:
        ps = compute_phase(0.2)
        assert ps.phase == "Rigid"
        assert ps.decay_factor == pytest.approx(0.005)
        assert ps.reinforcement_amount == pytest.approx(0.05)
        assert ps.decision_threshold == pytest.approx(0.80)
        assert ps.capacity_multiplier == pytest.approx(0.8)

    def test_flexible_phase(self) -> None:
        ps = compute_phase(0.5)
        assert ps.phase == "Flexible"
        assert ps.decay_factor == pytest.approx(0.01)
        assert ps.reinforcement_amount == pytest.approx(0.1)
        assert ps.decision_threshold == pytest.approx(0.65)
        assert ps.capacity_multiplier == pytest.approx(1.0)

    def test_chaotic_phase(self) -> None:
        ps = compute_phase(0.8)
        assert ps.phase == "Chaotic"
        assert ps.decay_factor == pytest.approx(0.02)
        assert ps.reinforcement_amount == pytest.approx(0.15)
        assert ps.decision_threshold == pytest.approx(0.55)
        assert ps.capacity_multiplier == pytest.approx(1.2)


class TestBoundaryValues:
    """Test that boundary values are handled correctly."""

    def test_boundary_0_4_is_flexible(self) -> None:
        ps = compute_phase(0.4)
        assert ps.phase == "Flexible"

    def test_boundary_0_6_is_flexible(self) -> None:
        ps = compute_phase(0.6)
        assert ps.phase == "Flexible"

    def test_just_below_0_4_is_rigid(self) -> None:
        ps = compute_phase(0.39)
        assert ps.phase == "Rigid"

    def test_just_above_0_6_is_chaotic(self) -> None:
        ps = compute_phase(0.61)
        assert ps.phase == "Chaotic"


class TestClamping:
    """Test that extreme T_g values are clamped."""

    def test_very_low_clamped(self) -> None:
        ps = compute_phase(0.0)
        assert ps.t_g == pytest.approx(0.1)
        assert ps.phase == "Rigid"

    def test_very_high_clamped(self) -> None:
        ps = compute_phase(1.5)
        assert ps.t_g == pytest.approx(0.9)
        assert ps.phase == "Chaotic"


class TestComputeTg:
    """Test T_g computation."""

    def test_baseline(self) -> None:
        t_g = compute_t_g(0.0, 0.0, 0.0, 0.0)
        assert 0.1 <= t_g <= 0.9

    def test_high_complexity_raises_t_g(self) -> None:
        low = compute_t_g(0.0, 0.0, 0.0, 0.0)
        high = compute_t_g(1.0, 1.0, 0.0, 0.0)
        assert high > low

    def test_high_env_entropy_lowers_t_g(self) -> None:
        base = compute_t_g(0.5, 0.5, 0.0, 0.0)
        with_env = compute_t_g(0.5, 0.5, 1.0, 0.0)
        assert with_env < base

    def test_output_range(self) -> None:
        for ic in [0, 0.5, 1]:
            for mc in [0, 0.5, 1]:
                for he in [0, 0.5, 1]:
                    for hs in [0, 0.5, 1]:
                        t_g = compute_t_g(ic, mc, he, hs)
                        assert 0.1 <= t_g <= 0.9
