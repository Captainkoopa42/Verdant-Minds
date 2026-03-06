"""Deterministic perturbation engine for cultivation prompts."""

from __future__ import annotations

import random


class PerturbationEngine:
    """Injects deterministic lexical perturbations by seed and cycle."""

    _MARKERS = [
        "focus-on-causality",
        "preserve-ambiguity",
        "enforce-traceability",
        "challenge-assumptions",
        "bound-novelty",
        "increase-contrast",
    ]

    def perturb(self, text: str, *, seed: int, cycle_index: int) -> str:
        """Return a reproducibly perturbed prompt string."""
        rng = random.Random((seed + 1) * 100_003 + cycle_index * 7_919)
        marker = self._MARKERS[rng.randrange(len(self._MARKERS))]
        if rng.random() < 0.5:
            return f"{text} [perturbation:{marker}]"
        return f"[perturbation:{marker}] {text}"
