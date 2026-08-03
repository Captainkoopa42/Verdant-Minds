from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

import numpy as np

from .models import Modality


def _normalize_complex(state: np.ndarray) -> np.ndarray:
    state = np.asarray(state, dtype=np.complex128)
    norm = np.linalg.norm(state)
    return state if norm == 0 else state / norm


def complex_similarity(left: np.ndarray, right: np.ndarray) -> float:
    left = np.asarray(left, dtype=np.complex128).reshape(-1)
    right = np.asarray(right, dtype=np.complex128).reshape(-1)
    denominator = np.linalg.norm(left) * np.linalg.norm(right) + 1e-12
    return float(np.abs(np.vdot(left, right)) / denominator)


@dataclass
class PlumbingTestSubstrate:
    """
    Contract test only.

    This is not the production ECWF/MemoryWeb. It exposes the same kind of
    before/after/delta boundary so the CognitiveChunk plumbing can be tested
    before wiring it to the real Verdant substrate.
    """

    feature_dim: int = 512
    state_dim: int = 128
    seed: int = 7741
    field_state: np.ndarray = field(
        default_factory=lambda: np.zeros(128, dtype=np.complex128)
    )
    memory_counts: dict[str, int] = field(default_factory=dict)

    def reset(self) -> None:
        self.field_state = np.zeros(self.state_dim, dtype=np.complex128)

    def _projection(self, modality: Modality) -> tuple[np.ndarray, np.ndarray]:
        modality_seed = int.from_bytes(
            hashlib.blake2b(
                modality.value.encode("utf-8"),
                digest_size=8,
            ).digest(),
            "little",
        )
        rng = np.random.default_rng(self.seed ^ modality_seed)
        scale = 1.0 / math.sqrt(self.feature_dim)
        real = rng.normal(
            0.0,
            scale,
            size=(self.feature_dim, self.state_dim),
        )
        imag = rng.normal(
            0.0,
            scale,
            size=(self.feature_dim, self.state_dim),
        )
        return real, imag

    def experience_effect(
        self,
        features: np.ndarray,
        modality: Modality,
    ) -> np.ndarray:
        real_projection, imag_projection = self._projection(modality)
        real = np.tanh(3.0 * (features @ real_projection))
        imag = np.tanh(3.0 * (features @ imag_projection))
        return _normalize_complex(real + 1j * imag)

    def apply_experience(
        self,
        features: np.ndarray,
        modality: Modality,
        signature: str,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        before = self.field_state.copy()
        effect = self.experience_effect(features, modality)
        if np.linalg.norm(before) == 0:
            after = effect
        else:
            after = _normalize_complex(0.72 * before + 0.65 * effect)
        self.field_state = after
        self.memory_counts[signature] = self.memory_counts.get(signature, 0) + 1
        delta = after - before
        return before, after, delta
