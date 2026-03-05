"""Thermodynamic phase classification and parameter derivation.

Consolidates all phase-dependent logic (previously scattered across
MemoryStorageBlock, ForefrontKing, and system.py) into a single source
of truth.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal


PhaseLabel = Literal["Rigid", "Flexible", "Chaotic"]


@dataclass(frozen=True, slots=True)
class PhaseState:
    """All phase-dependent parameters derived from ``T_g``.

    Attributes:
        t_g: Glass-transition temperature in ``[0.1, 0.9]``.
        phase: Human-readable phase label.
        decay_factor: Memory decay rate.
        reinforcement_amount: Memory reinforcement magnitude.
        decision_threshold: Action-selection confidence threshold.
        capacity_multiplier: Cognitive capacity multiplier.
    """

    t_g: float
    phase: PhaseLabel
    decay_factor: float
    reinforcement_amount: float
    decision_threshold: float
    capacity_multiplier: float


def compute_phase(t_g: float) -> PhaseState:
    """Derive all phase-dependent parameters from *T_g*.

    Phase boundaries::

        T_g < 0.4  → Rigid    (tight control, low decay)
        0.4 ≤ T_g ≤ 0.6  → Flexible (balanced)
        T_g > 0.6  → Chaotic  (loose control, high creativity)

    Args:
        t_g: Glass-transition temperature, will be clamped to ``[0.1, 0.9]``.

    Returns:
        A :class:`PhaseState` instance.
    """
    t_g = max(0.1, min(0.9, t_g))

    if t_g < 0.4:
        return PhaseState(
            t_g=t_g,
            phase="Rigid",
            decay_factor=0.005,
            reinforcement_amount=0.05,
            decision_threshold=0.80,
            capacity_multiplier=0.8,
        )

    if t_g <= 0.6:
        return PhaseState(
            t_g=t_g,
            phase="Flexible",
            decay_factor=0.01,
            reinforcement_amount=0.1,
            decision_threshold=0.65,
            capacity_multiplier=1.0,
        )

    return PhaseState(
        t_g=t_g,
        phase="Chaotic",
        decay_factor=0.02,
        reinforcement_amount=0.15,
        decision_threshold=0.55,
        capacity_multiplier=1.2,
    )


def compute_t_g(
    input_complexity: float,
    memory_complexity: float,
    h_env: float,
    h_sys: float,
) -> float:
    """Compute the glass-transition temperature.

    Ported from v1 ``system.py._update_glass_transition_temp``.

    Args:
        input_complexity: ``token_count / 100``, clamped ``[0, 1]``.
        memory_complexity: ``activated_concept_count / 10``, clamped ``[0, 1]``.
        h_env: Environmental entropy (mean_delta_e / 2), clamped ``[0, 1]``.
        h_sys: System wave entropy, clamped ``[0, 1]``.

    Returns:
        ``T_g`` in ``[0.1, 0.9]``.
    """
    input_complexity = max(0.0, min(1.0, input_complexity))
    memory_complexity = max(0.0, min(1.0, memory_complexity))
    h_env = max(0.0, min(1.0, h_env))
    h_sys = max(0.0, min(1.0, h_sys))

    computational_complexity = (input_complexity + memory_complexity) / 2.0
    base = 0.4 + 0.3 * computational_complexity - 0.2 * h_env
    entropy_feedback = 0.1 * math.sin(h_sys * math.pi)
    return max(0.1, min(0.9, base + entropy_feedback))
