from __future__ import annotations

import math

from .models import ThermodynamicPhase
from .metrics import clamp01

FORMULA_REVISION = "tg_v4_compat_1"


def compute_t_g(
    c_input: float,
    c_memory: float,
    h_env: float,
    h_sys: float,
) -> tuple[float, float, float, float]:
    """Compute the recovered V4 candidate glass-transition variable.

    Returns ``(t_g, computational_complexity, base_term, entropy_feedback)``.
    The law is copied from V4, but its inputs are supplied by versioned V5
    adapters and the output is measurement-only in EU01/T0.
    """

    c_input = clamp01(c_input)
    c_memory = clamp01(c_memory)
    h_env = clamp01(h_env)
    h_sys = clamp01(h_sys)
    computational_complexity = (c_input + c_memory) / 2.0
    base = 0.4 + 0.3 * computational_complexity - 0.2 * h_env
    entropy_feedback = 0.1 * math.sin(math.pi * h_sys)
    t_g = max(0.1, min(0.9, base + entropy_feedback))
    return t_g, computational_complexity, base, entropy_feedback


def classify_phase(t_g: float) -> ThermodynamicPhase:
    value = max(0.1, min(0.9, float(t_g)))
    if value < 0.4:
        return ThermodynamicPhase.RIGID
    if value <= 0.6:
        return ThermodynamicPhase.FLEXIBLE
    return ThermodynamicPhase.CHAOTIC


def cognitive_temperature(t_g: float, h_sys: float) -> float:
    return 1.0 - float(t_g) + clamp01(h_sys)
