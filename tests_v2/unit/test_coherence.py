"""Unit tests for ethomorphic.coherence.invariants."""

from __future__ import annotations

import pytest

from ethomorphic.coherence.invariants import CoherenceResult, compute_coherence


# ---------------------------------------------------------------------------
# Triangle validity
# ---------------------------------------------------------------------------

class TestTriangleValidity:
    """Tests for triangle inequality at alpha = 1.0."""

    def test_valid_at_alpha1_with_zeros(self) -> None:
        result = compute_coherence(
            wave_entropy=0.0,
            ethical_overall_score=0.0,
            magnitude=0.0,
        )
        assert result.triangle_valid is True

    def test_valid_at_alpha1_with_moderate_values(self) -> None:
        result = compute_coherence(
            wave_entropy=0.5,
            ethical_overall_score=0.5,
            magnitude=0.5,
            principle_scores={"a": 0.5, "b": 0.5},
        )
        # At alpha=1 the metric is just |a-b| which always satisfies triangle inequality
        assert result.triangle_valid is True

    def test_valid_at_alpha1_with_spread(self) -> None:
        result = compute_coherence(
            wave_entropy=0.3,
            ethical_overall_score=0.8,
            magnitude=0.6,
            principle_scores={"care": 0.9, "justice": 0.1, "autonomy": 0.5},
            activated_count=5,
            novelty_score=0.4,
        )
        assert result.triangle_valid is True


# ---------------------------------------------------------------------------
# HCI
# ---------------------------------------------------------------------------

class TestHCI:
    """Tests for the Housed Contradiction Index."""

    def test_hci_positive_with_spread(self) -> None:
        result = compute_coherence(
            wave_entropy=0.5,
            ethical_overall_score=0.7,
            magnitude=0.8,
            principle_scores={"a": 0.9, "b": 0.1},
        )
        assert result.hci > 0

    def test_hci_zero_when_no_activations(self) -> None:
        result = compute_coherence(
            wave_entropy=0.0,
            ethical_overall_score=0.0,
            magnitude=0.0,
            activated_count=0,
        )
        assert result.hci == 0.0

    def test_hci_from_entropy_when_no_principles(self) -> None:
        # No principle_scores but activated_count > 0 → fallback HCI
        result = compute_coherence(
            wave_entropy=0.5,
            ethical_overall_score=0.3,
            magnitude=0.6,
            activated_count=3,
        )
        assert result.hci > 0

    def test_hci_clamped_to_01(self) -> None:
        result = compute_coherence(
            wave_entropy=1.0,
            ethical_overall_score=1.0,
            magnitude=1.0,
            principle_scores={"a": 1.0, "b": 0.0},
            activated_count=10,
        )
        assert 0.0 <= result.hci <= 1.0


# ---------------------------------------------------------------------------
# Alpha-critical estimation
# ---------------------------------------------------------------------------

class TestAlphaCritical:
    """Tests for alpha_critical estimation."""

    def test_alpha_critical_none_when_no_violations(self) -> None:
        # All zero inputs → no violations at any alpha
        result = compute_coherence(
            wave_entropy=0.0,
            ethical_overall_score=0.0,
            magnitude=0.0,
        )
        assert result.alpha_critical is None

    def test_alpha_critical_is_float_when_present(self) -> None:
        result = compute_coherence(
            wave_entropy=0.9,
            ethical_overall_score=0.1,
            magnitude=0.8,
            principle_scores={"a": 0.95, "b": 0.05},
            novelty_score=0.9,
            activated_count=8,
        )
        if result.alpha_critical is not None:
            assert isinstance(result.alpha_critical, float)
            assert result.alpha_critical > 0

    def test_violation_rates_populated(self) -> None:
        result = compute_coherence(
            wave_entropy=0.5,
            ethical_overall_score=0.5,
            magnitude=0.5,
        )
        assert 1.0 in result.violation_rates
        assert len(result.violation_rates) == 7  # default grid size


# ---------------------------------------------------------------------------
# CoherenceResult structure
# ---------------------------------------------------------------------------

class TestCoherenceResultStructure:
    """Verify the result dataclass fields."""

    def test_fields_present(self) -> None:
        result = compute_coherence(
            wave_entropy=0.5,
            ethical_overall_score=0.5,
            magnitude=0.5,
        )
        assert isinstance(result, CoherenceResult)
        assert hasattr(result, "triangle_valid")
        assert hasattr(result, "hci")
        assert hasattr(result, "violation_rate")
        assert hasattr(result, "alpha_critical")
        assert hasattr(result, "triple_pqr")

    def test_triple_pqr_keys(self) -> None:
        result = compute_coherence(
            wave_entropy=0.3,
            ethical_overall_score=0.6,
            magnitude=0.4,
        )
        assert set(result.triple_pqr.keys()) == {"p", "q", "r"}
