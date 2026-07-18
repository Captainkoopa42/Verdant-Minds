"""Ethical Cognitive Wave Function (ECWF) core implementation.

Represents cognitive and ethical states as quantum-inspired wave functions,
enabling probabilistic reasoning, uncertainty representation, and
dynamic evolution of mental states.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class ECWFCore:
    """Ethical Cognitive Wave Function (ECWF) engine.

    Computes quantum-inspired wave functions over configurable cognitive and
    ethical dimension spaces.  All mathematical operations are identical to
    the original Verdant v1 implementation; the only structural change is that
    ``num_cognitive_dims`` and ``num_ethical_dims`` are **required** constructor
    parameters with no hardcoded default.
    """

    def __init__(
        self,
        num_cognitive_dims: int,
        num_ethical_dims: int,
        *,
        num_facets: int = 7,
        feedback_factor: float = 0.05,
        adaptive_rate: float = 0.1,
        random_state: Optional[int] = None,
    ) -> None:
        """Initialise the ECWF core.

        Args:
            num_cognitive_dims: Number of cognitive dimensions (required).
            num_ethical_dims: Number of ethical dimensions (required).
            num_facets: Number of wave facets (basis states).
            feedback_factor: Feedback influence strength.
            adaptive_rate: Rate of parameter adaptation.
            random_state: Random seed for reproducibility.
        """
        self.num_cognitive_dims = num_cognitive_dims
        self.num_ethical_dims = num_ethical_dims
        self.num_facets = num_facets
        self.feedback_factor = feedback_factor
        self.adaptive_rate = adaptive_rate

        self.random_state = random_state
        self.rng = np.random.RandomState(random_state)

        self._initialize_parameters()

        self.past_states: List[np.ndarray] = []

        self.cognitive_dim_names = [f"C{i + 1}" for i in range(num_cognitive_dims)]
        self.ethical_dim_names = [f"E{i + 1}" for i in range(num_ethical_dims)]

        self.dimension_meanings: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Parameter initialisation
    # ------------------------------------------------------------------

    def _initialize_parameters(self) -> None:
        """Initialise wave function parameters."""
        self.k = self.rng.uniform(-1, 1, size=(self.num_facets, self.num_cognitive_dims))
        self.m = self.rng.uniform(-1, 1, size=(self.num_facets, self.num_ethical_dims))
        self.omega = self.rng.uniform(0, 2 * np.pi, size=self.num_facets)
        self.phi = self.rng.uniform(0, 2 * np.pi, size=self.num_facets)
        self.amplitude_factors = self.rng.uniform(0.8, 1.2, size=self.num_facets)

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    def compute_ecwf(
        self, x_input: np.ndarray, e_input: np.ndarray, t: float
    ) -> np.ndarray:
        """Compute the Ethical Cognitive Wave Function.

        Args:
            x_input: Cognitive input tensor of shape ``(..., num_cognitive_dims)``.
            e_input: Ethical input tensor of shape ``(..., num_ethical_dims)``.
            t: Time parameter.

        Returns:
            Complex wave function output of shape ``(...)``.
        """
        result = np.zeros(x_input.shape[:-1], dtype=complex)

        for i in range(self.num_facets):
            amplitude = self._calculate_amplitude(x_input, e_input, t, i)

            cognitive_phase = np.tensordot(x_input, self.k[i], axes=([-1], [-1]))
            ethical_phase = np.tensordot(e_input, self.m[i], axes=([-1], [-1]))

            phase = (
                2 * np.pi * (cognitive_phase + ethical_phase)
                - self.omega[i] * t
                + self.phi[i]
            )

            result += amplitude * np.exp(1j * phase)

        # Memory effect from past states
        if self.past_states:
            weights = np.exp(-0.1 * np.arange(len(self.past_states)))
            weights = weights / weights.sum()
            memory_effect = np.average(self.past_states, axis=0, weights=weights)
            result += 0.1 * memory_effect

        self.past_states.append(result)
        if len(self.past_states) > 20:
            self.past_states.pop(0)

        return result

    def _calculate_amplitude(
        self, x: np.ndarray, e: np.ndarray, t: float, i: int
    ) -> np.ndarray:
        """Calculate amplitude for facet *i*.

        Args:
            x: Cognitive input.
            e: Ethical input.
            t: Time parameter.
            i: Facet index.

        Returns:
            Amplitude array matching the batch dimensions.
        """
        cognitive_term = np.sum(x**2, axis=-1) / self.num_cognitive_dims
        ethical_term = np.sum(e**2, axis=-1) / self.num_ethical_dims

        min_dims = min(self.num_cognitive_dims, self.num_ethical_dims)
        x_min = x[..., :min_dims]
        e_min = e[..., :min_dims]
        interaction_term = np.sum(x_min * e_min, axis=-1)

        feedback_term = self.feedback_factor * np.sin(interaction_term + t)
        adaptive_term = self.adaptive_rate * np.tanh(cognitive_term - ethical_term)

        amplitude = (
            self.amplitude_factors[i]
            * np.exp(-(cognitive_term + 2 * ethical_term) / (2 * (i + 1)))
            * (1 + 0.5 * np.sin(3 * t) + feedback_term + adaptive_term)
        )

        return np.maximum(amplitude, 1e-10)

    # ------------------------------------------------------------------
    # Entropy
    # ------------------------------------------------------------------

    def calculate_entropy(self, psi: np.ndarray) -> float:
        """Calculate the Shannon entropy of the wave function.

        Args:
            psi: Wave function state (complex array).

        Returns:
            Entropy value (higher means more uncertainty).
        """
        p = np.abs(psi) ** 2
        p_sum = np.sum(p)

        if p_sum == 0:
            return 0.0

        p = p / p_sum
        entropy = -np.sum(p * np.log2(p + 1e-10))
        return float(entropy)

    # ------------------------------------------------------------------
    # Sensitivities
    # ------------------------------------------------------------------

    def compute_sensitivities(
        self, x_input: np.ndarray, e_input: np.ndarray, t: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute sensitivity of the wave function to input dimensions.

        Args:
            x_input: Cognitive input.
            e_input: Ethical input.
            t: Time parameter.

        Returns:
            Tuple of ``(cognitive_sensitivities, ethical_sensitivities)``,
            each normalised to ``[0, 1]``.
        """
        baseline = self.compute_ecwf(x_input, e_input, t)

        cognitive_sens = np.zeros_like(x_input)
        ethical_sens = np.zeros_like(e_input)

        delta = 1e-5

        for i in range(self.num_cognitive_dims):
            x_perturbed = x_input.copy()
            x_perturbed[..., i] += delta
            perturbed = self.compute_ecwf(x_perturbed, e_input, t)
            cognitive_sens[..., i] = np.abs((perturbed - baseline) / delta)

        for i in range(self.num_ethical_dims):
            e_perturbed = e_input.copy()
            e_perturbed[..., i] += delta
            perturbed = self.compute_ecwf(x_input, e_perturbed, t)
            ethical_sens[..., i] = np.abs((perturbed - baseline) / delta)

        cognitive_max = np.max(cognitive_sens)
        ethical_max = np.max(ethical_sens)

        if cognitive_max > 0:
            cognitive_sens /= cognitive_max
        if ethical_max > 0:
            ethical_sens /= ethical_max

        return cognitive_sens, ethical_sens

    # ------------------------------------------------------------------
    # Parameter updates
    # ------------------------------------------------------------------

    def update_parameters(
        self,
        cognitive_influence: np.ndarray,
        ethical_influence: np.ndarray,
        factor: float = 0.1,
    ) -> None:
        """Update wave function parameters based on external influence.

        Args:
            cognitive_influence: Influence vector for cognitive dimensions.
            ethical_influence: Influence vector for ethical dimensions.
            factor: Scaling factor for parameter updates.
        """
        if np.max(np.abs(cognitive_influence)) > 0:
            cognitive_influence = cognitive_influence / np.max(np.abs(cognitive_influence))
        if np.max(np.abs(ethical_influence)) > 0:
            ethical_influence = ethical_influence / np.max(np.abs(ethical_influence))

        for i in range(self.num_facets):
            self.k[i] += factor * cognitive_influence * self.rng.normal(
                0, 0.1, size=self.k[i].shape
            )
            self.m[i] += factor * ethical_influence * self.rng.normal(
                0, 0.1, size=self.m[i].shape
            )

            avg_influence = (
                np.sum(cognitive_influence) + np.sum(ethical_influence)
            ) / 2
            self.omega[i] += factor * avg_influence * self.rng.normal(0, 0.1)
            self.phi[i] += factor * avg_influence * self.rng.normal(0, 0.1)

    # ------------------------------------------------------------------
    # Serialisation  (chunked JSON)
    # ------------------------------------------------------------------

    def to_state_dict(self, *, include_past_states: bool = False) -> Dict[str, Any]:
        """Serialise ECWFCore parameters into a JSON-compatible dictionary.

        The dictionary is structured in *chunks* (parameters, metadata,
        optional history) so that consumers can stream or store them
        independently.

        Args:
            include_past_states: Whether to include the past-state history.

        Returns:
            JSON-serialisable dictionary.
        """
        state: Dict[str, Any] = {
            "metadata": {
                "num_cognitive_dims": self.num_cognitive_dims,
                "num_ethical_dims": self.num_ethical_dims,
                "num_facets": self.num_facets,
                "feedback_factor": self.feedback_factor,
                "adaptive_rate": self.adaptive_rate,
                "random_state": self.random_state,
                "dimension_meanings": dict(self.dimension_meanings),
                "rng_state": self._serialize_rng_state(self.rng.get_state()),
            },
            "parameters": {
                "k": self.k.tolist(),
                "m": self.m.tolist(),
                "omega": self.omega.tolist(),
                "phi": self.phi.tolist(),
                "amplitude_factors": self.amplitude_factors.tolist(),
            },
        }

        if include_past_states:
            serialized: List[Dict[str, Any]] = []
            for arr in self.past_states:
                arr = np.asarray(arr)
                serialized.append(
                    {"real": np.real(arr).tolist(), "imag": np.imag(arr).tolist()}
                )
            state["history"] = {"past_states": serialized}

        return state

    @classmethod
    def from_state_dict(cls, state: Dict[str, Any]) -> "ECWFCore":
        """Reconstruct an ECWFCore from a dictionary produced by :meth:`to_state_dict`.

        Args:
            state: State dictionary.

        Returns:
            A new ``ECWFCore`` instance with restored parameters.
        """
        meta = state.get("metadata", state)  # support flat dicts too
        params = state.get("parameters", state)

        instance = cls(
            num_cognitive_dims=int(meta["num_cognitive_dims"]),
            num_ethical_dims=int(meta["num_ethical_dims"]),
            num_facets=int(meta.get("num_facets", 7)),
            feedback_factor=float(meta.get("feedback_factor", 0.05)),
            adaptive_rate=float(meta.get("adaptive_rate", 0.1)),
            random_state=meta.get("random_state"),
        )

        instance.k = np.array(params["k"], dtype=float)
        instance.m = np.array(params["m"], dtype=float)
        instance.omega = np.array(params["omega"], dtype=float)
        instance.phi = np.array(params["phi"], dtype=float)
        instance.amplitude_factors = np.array(params["amplitude_factors"], dtype=float)

        instance.dimension_meanings = dict(meta.get("dimension_meanings", {}))
        rng_state = meta.get("rng_state")
        if isinstance(rng_state, dict):
            instance.rng.set_state(cls._deserialize_rng_state(rng_state))

        # Restore history if present
        history = state.get("history", {})
        for past in history.get("past_states", []):
            real = np.array(past["real"], dtype=float)
            imag = np.array(past["imag"], dtype=float)
            instance.past_states.append(real + 1j * imag)

        return instance

    @staticmethod
    def _serialize_rng_state(state: tuple[Any, ...]) -> Dict[str, Any]:
        """Serialize NumPy RandomState state into JSON-friendly metadata."""
        return {
            "bit_generator": str(state[0]),
            "keys": state[1].tolist(),
            "pos": int(state[2]),
            "has_gauss": int(state[3]),
            "cached_gaussian": float(state[4]),
        }

    @staticmethod
    def _deserialize_rng_state(state: Dict[str, Any]) -> tuple[Any, ...]:
        """Restore NumPy RandomState state from JSON-friendly metadata."""
        return (
            str(state["bit_generator"]),
            np.array(state["keys"], dtype=np.uint32),
            int(state["pos"]),
            int(state["has_gauss"]),
            float(state["cached_gaussian"]),
        )

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def create_wave_function(
        self,
        x_input: Optional[np.ndarray] = None,
        e_input: Optional[np.ndarray] = None,
        t: float = 0.0,
    ) -> np.ndarray:
        """Backward-compatible wrapper returning an ECWF state tensor."""
        if x_input is None:
            x_input = np.zeros((1, self.num_cognitive_dims), dtype=float)
        if e_input is None:
            e_input = np.zeros((1, self.num_ethical_dims), dtype=float)
        return self.compute_ecwf(x_input, e_input, t)

    def set_dimension_meanings(
        self,
        cognitive_meanings: Optional[Dict[int, str]] = None,
        ethical_meanings: Optional[Dict[int, str]] = None,
    ) -> Dict[str, str]:
        """Set semantic meanings for dimensions.

        Args:
            cognitive_meanings: Mapping of cognitive dimension index to meaning.
            ethical_meanings: Mapping of ethical dimension index to meaning.

        Returns:
            The updated dimension-meanings dictionary.
        """
        self.dimension_meanings = {}

        if cognitive_meanings:
            for idx, meaning in cognitive_meanings.items():
                if 0 <= idx < self.num_cognitive_dims:
                    self.dimension_meanings[f"C{idx + 1}"] = meaning

        if ethical_meanings:
            for idx, meaning in ethical_meanings.items():
                if 0 <= idx < self.num_ethical_dims:
                    self.dimension_meanings[f"E{idx + 1}"] = meaning

        return self.dimension_meanings
