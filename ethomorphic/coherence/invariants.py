"""Coherence invariant computation.

Standalone port of ``_compute_coherence_invariants`` from Verdant v1's
``UnifiedSystem``.  All metric-space triangle-inequality logic, HCI
(Housed Contradiction Index), and alpha-critical estimation are preserved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CoherenceResult:
    """Result of a coherence invariant computation."""

    triangle_valid: bool
    """Whether the triangle inequality holds at alpha = 1.0."""

    hci: float
    """Housed Contradiction Index – measures tension held within the system."""

    violation_rate: float
    """Fraction of sampled triples that violate the triangle inequality at alpha = 1.0."""

    alpha_critical: Optional[float]
    """Estimated alpha value where violations first exceed 5%, or ``None``."""

    triple_pqr: Dict[str, float]
    """Primary (p, q, r) triple used for reporting."""

    sampled_triplets: List[Dict[str, float]] = field(default_factory=list)
    """All sampled triples."""

    violation_rates: Dict[float, float] = field(default_factory=dict)
    """Violation rate at each tested alpha value."""


def compute_coherence(
    wave_entropy: float,
    ethical_overall_score: float,
    magnitude: float,
    *,
    phase: float = 0.0,
    principle_scores: Optional[Dict[str, float]] = None,
    activated_count: int = 0,
    novelty_score: float = 0.0,
    mean_delta_e: float = 0.0,
    alpha_grid: Optional[List[float]] = None,
) -> CoherenceResult:
    """Compute coherence invariants from wave, ethics, and memory telemetry.

    All inputs are clamped to ``[0, 1]`` internally to match the v1
    implementation.

    Args:
        wave_entropy: ECWF entropy value.
        ethical_overall_score: Overall ethics evaluation score.
        magnitude: Wave function magnitude.
        phase: Wave function phase.
        principle_scores: Per-principle ethics scores (name → value).
        activated_count: Number of activated memory concepts.
        novelty_score: Novelty score from memory retrieval.
        mean_delta_e: Mean ethical delta.
        alpha_grid: Alpha values to test (defaults to
            ``[0.8, 0.9, 1.0, 1.05, 1.1, 1.15, 1.2]``).

    Returns:
        :class:`CoherenceResult` dataclass.
    """
    eps = 1e-9

    def clamp01(v: float) -> float:
        return max(0.0, min(1.0, v))

    def tau_alpha(a: float, b: float, alpha: float) -> float:
        return abs(a - b) ** alpha

    def is_triangle_valid(a: float, b: float, c: float, alpha: float) -> bool:
        d_ab = tau_alpha(a, b, alpha)
        d_bc = tau_alpha(b, c, alpha)
        d_ac = tau_alpha(a, c, alpha)
        return (
            d_ab <= d_bc + d_ac + eps
            and d_bc <= d_ab + d_ac + eps
            and d_ac <= d_ab + d_bc + eps
        )

    entropy = clamp01(wave_entropy)
    phase_c = clamp01(phase)
    mag = clamp01(magnitude)
    overall = clamp01(ethical_overall_score)
    novelty = clamp01(novelty_score)
    activated_norm = clamp01(activated_count / 10.0)

    if principle_scores and len(principle_scores) >= 1:
        p_values = [clamp01(v) for v in principle_scores.values()]
        p_mean = sum(p_values) / len(p_values)
    else:
        p_values = []
        p_mean = 0.0

    # HCI calculation
    if len(p_values) >= 2:
        sorted_p = sorted(p_values)
        spread = clamp01(sorted_p[-1] - sorted_p[0])
        hci = clamp01(spread * mag)
    elif activated_count > 0:
        hci = clamp01(entropy * mag * 2.0)
    else:
        hci = 0.0

    # Sampled triples
    sampled = [
        {"p": entropy, "q": overall, "r": mag},
        {"p": entropy, "q": p_mean, "r": activated_norm},
        {"p": novelty, "q": overall, "r": phase_c},
        {"p": mag, "q": novelty, "r": activated_norm},
        {"p": entropy, "q": clamp01(mean_delta_e / 2.0), "r": overall},
    ]

    grid = alpha_grid or [0.8, 0.9, 1.0, 1.05, 1.1, 1.15, 1.2]
    v_rates: Dict[float, float] = {}

    for alpha in grid:
        violations = 0
        for trip in sampled:
            if not is_triangle_valid(trip["p"], trip["q"], trip["r"], alpha):
                violations += 1
        v_rates[alpha] = violations / max(1, len(sampled))

    vr_at_1 = v_rates.get(1.0, 0.0)
    tri_valid = vr_at_1 <= 0.0

    alpha_crit: Optional[float] = None
    for alpha in grid:
        if v_rates[alpha] > 0.05:
            alpha_crit = float(alpha)
            break

    return CoherenceResult(
        triangle_valid=tri_valid,
        hci=hci,
        violation_rate=vr_at_1,
        alpha_critical=alpha_crit,
        triple_pqr={"p": entropy, "q": overall, "r": mag},
        sampled_triplets=sampled,
        violation_rates=v_rates,
    )
