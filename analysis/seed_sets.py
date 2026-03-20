#!/usr/bin/env python3
"""Utilities for deterministic concept seed-set generation."""

from __future__ import annotations

import random

MASTER_SEEDS = [
    "identity", "consciousness", "memory", "perception", "reasoning",
    "ethics", "autonomy", "creativity", "emotion", "language",
    "attention", "learning", "abstraction", "causality", "time",
    "space", "self", "other", "boundary", "emergence",
    "complexity", "entropy", "order", "chaos", "stability",
    "change", "growth", "decay", "connection", "isolation",
    "integration", "differentiation", "meaning", "purpose", "value",
    "belief", "knowledge", "uncertainty", "truth", "contradiction",
    "paradox", "duality", "unity", "recursion", "reflection",
    "awareness", "intention", "agency", "freedom", "constraint",
    "responsibility", "empathy", "compassion", "justice", "fairness",
    "trust", "cooperation", "competition", "survival", "adaptation",
    "evolution", "novelty", "tradition", "continuity", "discontinuity",
    "structure", "function", "pattern", "noise", "signal",
    "information", "communication", "understanding", "wisdom",
    "intuition", "logic", "imagination", "experience", "narrative",
    "coherence", "resonance", "harmony", "conflict", "resolution",
]


def get_seed_set(n: int, random_seed: int = 42, seed: int | None = None) -> list[str]:
    """Return a deterministic subset of ``n`` concepts from ``MASTER_SEEDS``.

    For ``n <= len(MASTER_SEEDS)``: choose first ``n`` concepts from a shuffled list.
    For ``n > len(MASTER_SEEDS)``: append numbered variants (e.g. ``identity_1``).
    Deterministic for a given ``(n, random_seed)`` pair.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    actual_seed = random_seed if seed is None else seed

    rng = random.Random(actual_seed)
    shuffled = list(MASTER_SEEDS)
    rng.shuffle(shuffled)

    if n <= len(shuffled):
        return shuffled[:n]

    out = list(shuffled)
    i = 0
    while len(out) < n:
        base = shuffled[i % len(shuffled)]
        suffix = (i // len(shuffled)) + 1
        out.append(f"{base}_{suffix}")
        i += 1
    return out
