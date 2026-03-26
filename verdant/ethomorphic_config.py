"""Verdant-side configuration hooks for the read-only ``ethomorphic`` package.

This module exposes the subset of ECWF and bridge/emergence behavior that can
be parameterized from Verdant without modifying upstream ``ethomorphic`` source.
"""

from __future__ import annotations

import hashlib
import itertools
import time
from dataclasses import asdict, dataclass, fields
from typing import Any

import numpy as np

from ethomorphic.bridge.bridge import EthomorphicBridge
from ethomorphic.bridge.emergence import link_emergent_to_existing_emergents
from ethomorphic.ecwf.core import ECWFCore


@dataclass(frozen=True)
class SweepabilityRecord:
    """Metadata describing how Verdant exposes an ethomorphic parameter."""

    mode: str
    sweepable: bool
    source: str
    reason: str


@dataclass(frozen=True)
class EthomorphicParams:
    """Parameters Verdant can pass through to ethomorphic initialization/runtime.

    Defaults are chosen to reproduce the current Verdant behavior when no custom
    configuration is supplied.
    """

    # ECWF dimensions/dynamics (constructor arguments in ethomorphic.ecwf.core)
    num_cognitive_dims: int = 5
    num_ethical_dims: int = 5
    num_facets: int = 7
    adaptive_rate: float = 0.1
    feedback_factor: float = 0.05
    initial_amplitude: float = 1.0

    # Emergence / bridge thresholds (hard-coded upstream, exposed in Verdant)
    emergence_entropy_min: float = 0.3
    emergence_entropy_max: float = 3.0
    emergence_magnitude_threshold: float = 0.15
    co_activation_threshold: float = 0.2

    # Connection controls (not constructor args upstream; enforced in Verdant)
    connection_weight_threshold: float = 0.0
    max_connections_per_concept: int | None = None


SWEEPABILITY: dict[str, SweepabilityRecord] = {
    "num_cognitive_dims": SweepabilityRecord(
        mode="constructor_arg",
        sweepable=True,
        source="ethomorphic/ecwf/core.py",
        reason="Passed directly to ECWFCore(num_cognitive_dims=...).",
    ),
    "num_ethical_dims": SweepabilityRecord(
        mode="constructor_arg",
        sweepable=True,
        source="ethomorphic/ecwf/core.py",
        reason="Passed directly to ECWFCore(num_ethical_dims=...).",
    ),
    "num_facets": SweepabilityRecord(
        mode="constructor_arg",
        sweepable=True,
        source="ethomorphic/ecwf/core.py",
        reason="Passed directly to ECWFCore(num_facets=...).",
    ),
    "adaptive_rate": SweepabilityRecord(
        mode="constructor_arg",
        sweepable=True,
        source="ethomorphic/ecwf/core.py",
        reason="Passed directly to ECWFCore(adaptive_rate=...).",
    ),
    "feedback_factor": SweepabilityRecord(
        mode="constructor_arg",
        sweepable=True,
        source="ethomorphic/ecwf/core.py",
        reason="Passed directly to ECWFCore(feedback_factor=...).",
    ),
    "initial_amplitude": SweepabilityRecord(
        mode="post_init_override",
        sweepable=True,
        source="ethomorphic/ecwf/core.py",
        reason="Verdant rescales ECWF amplitude_factors after construction.",
    ),
    "emergence_entropy_min": SweepabilityRecord(
        mode="verdant_wrapper",
        sweepable=True,
        source="ethomorphic/bridge/emergence.py",
        reason="Verdant re-implements the upstream emergence guard with a configurable lower bound.",
    ),
    "emergence_entropy_max": SweepabilityRecord(
        mode="verdant_wrapper",
        sweepable=True,
        source="ethomorphic/bridge/emergence.py",
        reason="Verdant re-implements the upstream emergence guard with a configurable upper bound.",
    ),
    "emergence_magnitude_threshold": SweepabilityRecord(
        mode="verdant_wrapper",
        sweepable=True,
        source="ethomorphic/bridge/emergence.py",
        reason="Verdant uses a configurable magnitude threshold in its emergence wrapper.",
    ),
    "co_activation_threshold": SweepabilityRecord(
        mode="verdant_wrapper",
        sweepable=True,
        source="ethomorphic/bridge/bridge.py",
        reason="Verdant bridge hooks use a configurable activation cutoff.",
    ),
    "connection_weight_threshold": SweepabilityRecord(
        mode="verdant_wrapper",
        sweepable=True,
        source="ethomorphic/bridge/bridge.py",
        reason="Verdant bridge hooks can skip low-strength co-activation edges.",
    ),
    "max_connections_per_concept": SweepabilityRecord(
        mode="verdant_wrapper",
        sweepable=True,
        source="ethomorphic/bridge/bridge.py",
        reason="Verdant bridge hooks can cap per-cycle co-activation fan-out.",
    ),
}


def resolve_ethomorphic_params(
    params: EthomorphicParams | None,
    *,
    cognitive_dims: int,
    ethical_dims: int,
    wave_facets: int,
) -> EthomorphicParams:
    """Merge legacy VerdantConfig fields with optional EthomorphicParams."""

    base = EthomorphicParams(
        num_cognitive_dims=cognitive_dims,
        num_ethical_dims=ethical_dims,
        num_facets=wave_facets,
    )
    if params is None:
        return base

    merged = asdict(base)
    defaults = EthomorphicParams()
    provided = asdict(params)
    for key, value in provided.items():
        if key in {"num_cognitive_dims", "num_ethical_dims", "num_facets"}:
            base_value = merged[key]
            default_value = getattr(defaults, key)
            if base_value != default_value and value == default_value:
                continue
        merged[key] = value
    return EthomorphicParams(**merged)


def apply_ecwf_params(
    *,
    random_state: int | None,
    params: EthomorphicParams,
) -> ECWFCore:
    """Construct an ECWF instance and apply Verdant-side overrides."""

    ecwf = ECWFCore(
        num_cognitive_dims=params.num_cognitive_dims,
        num_ethical_dims=params.num_ethical_dims,
        num_facets=params.num_facets,
        feedback_factor=params.feedback_factor,
        adaptive_rate=params.adaptive_rate,
        random_state=random_state,
    )
    if params.initial_amplitude != 1.0:
        ecwf.amplitude_factors = ecwf.amplitude_factors * float(params.initial_amplitude)
    return ecwf


def configure_bridge_runtime(bridge: EthomorphicBridge, params: EthomorphicParams) -> None:
    """Attach configurable Verdant runtime parameters to a bridge instance."""

    bridge._verdant_ethomorphic_params = params
    bridge._verdant_co_activation_threshold = float(params.co_activation_threshold)
    bridge._verdant_connection_weight_threshold = float(params.connection_weight_threshold)
    bridge._verdant_max_connections_per_concept = (
        None
        if params.max_connections_per_concept in (None, 0)
        else int(params.max_connections_per_concept)
    )


def get_ethomorphic_params_from_bridge(bridge: EthomorphicBridge) -> EthomorphicParams:
    """Return bridge-bound params or the Verdant defaults."""

    params = getattr(bridge, "_verdant_ethomorphic_params", None)
    return params if isinstance(params, EthomorphicParams) else EthomorphicParams()


def params_report_rows() -> list[dict[str, Any]]:
    """Return a serializable parameter inventory for reporting."""

    defaults = EthomorphicParams()
    rows: list[dict[str, Any]] = []
    for field in fields(EthomorphicParams):
        meta = SWEEPABILITY[field.name]
        rows.append(
            {
                "name": field.name,
                "default": getattr(defaults, field.name),
                "sweepable": meta.sweepable,
                "mode": meta.mode,
                "source": meta.source,
                "reason": meta.reason,
            }
        )
    return rows


def detect_and_create_emergent_concepts_with_params(
    bridge: EthomorphicBridge,
    wave_output: np.ndarray,
    t: float,
    *,
    params: EthomorphicParams | None = None,
    semantic_similarity_fn: Any | None = None,
) -> list[str]:
    """Verdant-side configurable wrapper around ethomorphic emergence logic."""

    del wave_output  # Upstream implementation also derives emergence from sensitivities.
    active_params = params or get_ethomorphic_params_from_bridge(bridge)
    ecwf = bridge.ecwf
    memory = bridge.memory

    cog_dims = ecwf.num_cognitive_dims
    eth_dims = ecwf.num_ethical_dims

    cog_state = np.ones((1, 1, cog_dims)) * 0.5
    eth_state = np.ones((1, 1, eth_dims)) * 0.5
    cog_sens, eth_sens = ecwf.compute_sensitivities(cog_state, eth_state, t)

    sens_vector = np.abs(np.concatenate([cog_sens.flatten(), eth_sens.flatten()]))
    sens_norm = sens_vector / (sens_vector.sum() + 1e-10)
    entropy = float(-np.sum(sens_norm * np.log(sens_norm + 1e-10)))
    magnitude_scalar = float(sens_vector.mean())

    if entropy < active_params.emergence_entropy_min or entropy > active_params.emergence_entropy_max:
        return []

    cog_strongest = set(int(i) for i in np.argsort(cog_sens.flatten())[-2:])
    eth_strongest = set(int(i) for i in np.argsort(eth_sens.flatten())[-2:])

    matched_concepts: set[str] = set()
    for concept, mappings in bridge.concept_dimension_mapping.items():
        if concept.startswith("Emergent_"):
            continue
        for mtype, dim_idx, _weight in mappings:
            if mtype == "cognitive" and dim_idx in cog_strongest:
                matched_concepts.add(concept)
            elif mtype == "ethical" and dim_idx in eth_strongest:
                matched_concepts.add(concept)

    if len(matched_concepts) < 2:
        return []

    scored: list[tuple[str, float]] = []
    for concept in matched_concepts:
        data = memory.get_concept(concept)
        stability = 0.5
        if data is not None:
            raw = data.get("stability", 0.5)
            try:
                stability = float(raw)
            except (TypeError, ValueError):
                stability = 0.5
        scored.append((concept, stability))

    use_semantic = semantic_similarity_fn is not None and len(scored) > 3
    if use_semantic:
        concept_names = [c for c, _ in scored]
        surprise_scored: list[tuple[str, float]] = []
        for concept, strength in scored:
            sims = [
                semantic_similarity_fn(concept, other)
                for other in concept_names
                if other != concept
            ]
            avg_sim = float(np.mean(sims)) if sims else 0.0
            surprise_scored.append((concept, 0.5 * strength + 0.5 * (1.0 - avg_sim)))
        surprise_scored.sort(key=lambda item: (-item[1], item[0]))
        top_concepts = [c for c, _ in surprise_scored[:3]]
    else:
        scored.sort(key=lambda item: (-item[1], item[0]))
        top_concepts = [c for c, _ in scored[:3]]

    naming_pair = top_concepts[:2]
    if use_semantic and len(top_concepts) >= 2:
        pairs: list[tuple[float, str, str]] = []
        for ca, cb in itertools.combinations(top_concepts, 2):
            pairs.append((float(semantic_similarity_fn(ca, cb)), ca, cb))
        if pairs:
            pairs.sort(key=lambda item: item[0])
            _, c1, c2 = pairs[0]
            naming_pair = [c1, c2]

    combo_key = "_x_".join(sorted(top_concepts))
    if combo_key in bridge._emergent_combo_keys:
        return []
    if magnitude_scalar <= active_params.emergence_magnitude_threshold:
        return []

    bridge._emergent_combo_keys.add(combo_key)
    suffix = hashlib.sha256(combo_key.encode("utf-8")).hexdigest()[:6]
    new_concept = f"Emergent_{'_'.join(naming_pair)}_{suffix}"

    dimensions: list[tuple[str, int, float]] = []
    rng = np.random.default_rng()
    for dim in cog_strongest:
        dimensions.append(("cognitive", dim, 0.8 + float(rng.random()) * 0.2))
    for dim in eth_strongest:
        dimensions.append(("ethical", dim, 0.7 + float(rng.random()) * 0.3))
    bridge.concept_dimension_mapping[new_concept] = dimensions

    memory.add_concept(
        new_concept,
        stability=0.5,
        metadata={
            "origin": "wave_emergence",
            "creation_time": time.time(),
            "entropy": entropy,
            "magnitude": magnitude_scalar,
            "parent_concepts": top_concepts,
            "combo_key": combo_key,
        },
    )
    for concept in matched_concepts:
        memory.connect(new_concept, concept, 0.6)

    link_emergent_to_existing_emergents(memory, new_concept, top_concepts)
    return [new_concept]
