"""Ethomorphic AI – ethical state vector construction and field modulation.

This module contains the core Ethomorphic IP:

1. **Ethical state vector construction** – translating symbolic ethical
   concept activations into a numerical ethical state vector aligned with
   the ECWF dimension space.

2. **Ethical field modulation** – computing ``E(t) · Ψ``, the element-wise
   product of the ethical field with the wave function, ensuring that all
   cognitive processing is ethically modulated.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ethomorphic.ecwf.core import ECWFCore


# ---------------------------------------------------------------------------
# Ethical state construction
# ---------------------------------------------------------------------------

def build_ethical_state(
    concepts: List[str],
    concept_dimension_mapping: Dict[str, List[Tuple[str, int, float]]],
    num_ethical_dims: int,
    *,
    stability_lookup: Optional[Dict[str, float]] = None,
) -> np.ndarray:
    """Construct an ethical state vector from concept activations.

    Translates symbolic ethical concepts into a mathematical vector in the
    ECWF ethical dimension space using the provided mapping.

    Args:
        concepts: Active concept labels.
        concept_dimension_mapping: Mapping of concept → list of
            ``(type, dim_idx, weight)`` tuples.
        num_ethical_dims: Number of ethical dimensions in the ECWF.
        stability_lookup: Optional mapping of concept label to stability
            score.  Defaults to ``0.5`` for missing concepts.

    Returns:
        Normalised ethical state vector of shape ``(num_ethical_dims,)``.
    """
    state = np.zeros(num_ethical_dims)

    for concept in concepts:
        mappings = concept_dimension_mapping.get(concept)
        if mappings is None:
            continue

        stability = 0.5
        if stability_lookup and concept in stability_lookup:
            stability = stability_lookup[concept]

        for mtype, dim_idx, weight in mappings:
            if mtype == "ethical" and dim_idx < num_ethical_dims:
                state[dim_idx] += weight * stability

    mx = np.max(state)
    if mx > 0:
        state /= mx

    return state


# ---------------------------------------------------------------------------
# Ethical field modulation  E(t) · Ψ
# ---------------------------------------------------------------------------

def compute_ethical_field(
    ethical_state: np.ndarray,
    t: float,
    *,
    modulation_frequency: float = 1.0,
    baseline: float = 0.5,
) -> np.ndarray:
    """Compute the time-dependent ethical field ``E(t)``.

    The field oscillates around *baseline* with an amplitude controlled by
    the ethical state vector magnitude, enabling smooth ethical influence
    that evolves over time.

    Args:
        ethical_state: Ethical state vector of shape ``(num_ethical_dims,)``.
        t: Time parameter.
        modulation_frequency: Oscillation frequency.
        baseline: Baseline ethical presence (0 = no ethics, 1 = full).

    Returns:
        Ethical field vector of the same shape as *ethical_state*.
    """
    amplitude = np.linalg.norm(ethical_state)
    # Oscillate each dimension with a phase offset proportional to its index
    phases = np.arange(len(ethical_state)) * (2 * np.pi / max(len(ethical_state), 1))
    field = baseline + amplitude * ethical_state * np.sin(modulation_frequency * t + phases)
    # Clamp to [0, 1]
    return np.clip(field, 0.0, 1.0)


def modulate_wave(
    psi: np.ndarray,
    ethical_field: np.ndarray,
    ecwf: ECWFCore,
) -> np.ndarray:
    """Apply ethical field modulation to a wave function: ``E(t) · Ψ``.

    The ethical field is projected to match the wave function shape via
    the ethical wave numbers of the ECWF, then multiplied element-wise
    with the wave function output.

    Args:
        psi: Complex wave function array from :meth:`ECWFCore.compute_ecwf`.
        ethical_field: Ethical field vector of shape ``(num_ethical_dims,)``.
        ecwf: The ECWF core (used for dimension alignment).

    Returns:
        Ethically modulated wave function of the same shape as *psi*.
    """
    # Project the ethical field to a scalar modulation factor per facet,
    # then average to get a single modulation scalar.
    # This preserves the v1 pattern where ethics scales the wave amplitude.
    modulation = float(np.mean(ethical_field))
    return psi * modulation


# ---------------------------------------------------------------------------
# Full ethomorphic pass
# ---------------------------------------------------------------------------

def ethomorphic_pass(
    ecwf: ECWFCore,
    cognitive_state: np.ndarray,
    ethical_concepts: List[str],
    concept_dimension_mapping: Dict[str, List[Tuple[str, int, float]]],
    t: float,
    *,
    stability_lookup: Optional[Dict[str, float]] = None,
    modulation_frequency: float = 1.0,
    baseline: float = 0.5,
) -> Dict[str, Any]:
    """Run a full ethomorphic processing pass.

    1. Build the ethical state vector from concepts.
    2. Compute the ECWF wave function.
    3. Compute the ethical field ``E(t)``.
    4. Modulate: ``E(t) · Ψ``.

    Args:
        ecwf: The ECWF engine.
        cognitive_state: Cognitive input of shape ``(1, 1, num_cognitive_dims)``
            or ``(num_cognitive_dims,)``.
        ethical_concepts: Active ethical concept labels.
        concept_dimension_mapping: Concept-to-dimension mappings.
        t: Time parameter.
        stability_lookup: Optional concept → stability mapping.
        modulation_frequency: Ethical field oscillation frequency.
        baseline: Ethical field baseline.

    Returns:
        Dictionary with ``psi_raw``, ``ethical_state``, ``ethical_field``,
        ``psi_modulated``, and ``entropy``.
    """
    ethical_state = build_ethical_state(
        ethical_concepts,
        concept_dimension_mapping,
        ecwf.num_ethical_dims,
        stability_lookup=stability_lookup,
    )

    # Ensure proper shapes
    if cognitive_state.ndim == 1:
        cognitive_state = cognitive_state.reshape(1, 1, -1)
    e_input = ethical_state.reshape(1, 1, -1)

    psi_raw = ecwf.compute_ecwf(cognitive_state, e_input, t)

    ethical_field = compute_ethical_field(
        ethical_state,
        t,
        modulation_frequency=modulation_frequency,
        baseline=baseline,
    )

    psi_mod = modulate_wave(psi_raw, ethical_field, ecwf)

    return {
        "psi_raw": psi_raw,
        "ethical_state": ethical_state,
        "ethical_field": ethical_field,
        "psi_modulated": psi_mod,
        "entropy": ecwf.calculate_entropy(psi_mod),
    }
