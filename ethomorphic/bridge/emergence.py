"""Emergent concept detection and creation.

Detects novel conceptual patterns from ECWF wave states and creates new
concepts in the memory backend.  Surprise-scoring (preferring semantically
distant co-activations) is preserved from the v1 implementation.
"""

from __future__ import annotations

import hashlib
import itertools
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ethomorphic.bridge.bridge import EthomorphicBridge


def _combo_hash(combo_key: str) -> str:
    """Return the first 6 hex characters of the SHA-256 of *combo_key*."""
    return hashlib.sha256(combo_key.encode()).hexdigest()[:6]


def detect_and_create_emergent_concepts(
    bridge: EthomorphicBridge,
    wave_output: np.ndarray,
    t: float,
    *,
    threshold: float = 0.15,
    semantic_similarity_fn: Optional[Any] = None,
) -> List[str]:
    """Detect and create emergent concepts from wave patterns.

    When *semantic_similarity_fn* is provided it should accept two concept
    labels and return a float in ``[-1, 1]``.  When available, concept
    combinations with **low** similarity (surprising co-activations) are
    preferred.

    Each emergent concept name includes a unique 6-character hash suffix
    derived from its ``combo_key`` to prevent name collisions.

    Args:
        bridge: The :class:`EthomorphicBridge` instance.
        wave_output: Output from an ECWF computation.
        t: Current time parameter.
        threshold: Minimum magnitude scalar for concept creation.
        semantic_similarity_fn: Optional ``(str, str) -> float`` callable.

    Returns:
        List of newly created concept labels (empty if none created).
    """
    ecwf = bridge.ecwf
    memory = bridge.memory

    cog_dims = ecwf.num_cognitive_dims
    eth_dims = ecwf.num_ethical_dims

    cog_state = np.ones((1, 1, cog_dims)) * 0.5
    eth_state = np.ones((1, 1, eth_dims)) * 0.5
    cog_sens, eth_sens = ecwf.compute_sensitivities(cog_state, eth_state, t)

    # Sensitivity-based entropy and magnitude
    sens_vector = np.abs(np.concatenate([cog_sens.flatten(), eth_sens.flatten()]))
    sens_norm = sens_vector / (sens_vector.sum() + 1e-10)
    entropy = float(-np.sum(sens_norm * np.log(sens_norm + 1e-10)))
    magnitude_scalar = float(sens_vector.mean())

    # Entropy guard – too low or too high blocks emergence
    if entropy < 0.3 or entropy > 3.0:
        return []

    # Strongest dimensions
    cog_strongest = set(int(i) for i in np.argsort(cog_sens.flatten())[-2:])
    eth_strongest = set(int(i) for i in np.argsort(eth_sens.flatten())[-2:])

    # Concepts matching those dimensions
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

    # Score concepts – stability from memory
    scored: List[Tuple[str, float]] = []
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

    # Surprise scoring when semantic similarity is available
    use_semantic = semantic_similarity_fn is not None and len(scored) > 3
    if use_semantic:
        concept_names = [c for c, _ in scored]
        surprise_scored: List[Tuple[str, float]] = []
        for concept, strength in scored:
            sims = [
                semantic_similarity_fn(concept, other)
                for other in concept_names
                if other != concept
            ]
            avg_sim = float(np.mean(sims)) if sims else 0.0
            blended = 0.5 * strength + 0.5 * (1.0 - avg_sim)
            surprise_scored.append((concept, blended))
        surprise_scored.sort(key=lambda x: (-x[1], x[0]))
        top_concepts = [c for c, _ in surprise_scored[:3]]
    else:
        scored.sort(key=lambda x: (-x[1], x[0]))
        top_concepts = [c for c, _ in scored[:3]]

    # Naming pair – most distant pair if semantic available
    naming_pair = top_concepts[:2]
    if use_semantic and len(top_concepts) >= 2:
        pairs = []
        for ca, cb in itertools.combinations(top_concepts, 2):
            pairs.append((semantic_similarity_fn(ca, cb), ca, cb))
        if pairs:
            pairs.sort(key=lambda x: x[0])
            _, c1, c2 = pairs[0]
            naming_pair = [c1, c2]

    # Deduplication via combo_key
    combo_key = "_x_".join(sorted(top_concepts))

    if combo_key in bridge._emergent_combo_keys:
        return []

    if magnitude_scalar <= threshold:
        return []

    # Register emergence combo key before any other writes
    bridge._emergent_combo_keys.add(combo_key)

    # Build unique name with hash suffix
    suffix = _combo_hash(combo_key)
    concept_base = f"Emergent_{'_'.join(naming_pair)}"
    new_concept = f"{concept_base}_{suffix}"

    # Assign dimension mappings (fallback to strongest dims)
    dimensions: List[Tuple[str, int, float]] = []
    rng = np.random.default_rng()
    for dim in cog_strongest:
        dimensions.append(("cognitive", dim, 0.8 + float(rng.random()) * 0.2))
    for dim in eth_strongest:
        dimensions.append(("ethical", dim, 0.7 + float(rng.random()) * 0.3))
    bridge.concept_dimension_mapping[new_concept] = dimensions

    # Add to memory
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

    # Connect to matched concepts
    for concept in matched_concepts:
        memory.connect(new_concept, concept, 0.6)

    # Connect to prior emergent concepts that share parent concepts.
    new_parent_set = set(top_concepts)
    for existing_emergent in memory.get_emergent_nodes():
        if existing_emergent == new_concept:
            continue
        existing_data = memory.get_concept(existing_emergent) or {}
        existing_meta = existing_data.get("metadata", {})
        if not isinstance(existing_meta, dict):
            continue
        existing_parents = existing_meta.get("parent_concepts", [])
        if not isinstance(existing_parents, list):
            continue
        overlap = new_parent_set.intersection(existing_parents)
        if not overlap:
            continue
        overlap_ratio = len(overlap) / max(1, len(new_parent_set))
        memory.connect(new_concept, existing_emergent, 0.6 * overlap_ratio)

    return [new_concept]


def assign_emergent_concept_mappings(
    bridge: EthomorphicBridge,
    new_concept: str,
    parent_concepts: List[str],
) -> List[Tuple[str, int, float]]:
    """Assign dimension mappings for an emergent concept by averaging parents.

    Falls back to :meth:`EthomorphicBridge.assign_concept_mappings` when
    parent mappings are unavailable.

    Args:
        bridge: The bridge instance.
        new_concept: Name of the emergent concept.
        parent_concepts: Parent concept labels.

    Returns:
        List of ``(type, dim_idx, weight)`` tuples.
    """
    parent_mappings = [
        bridge.concept_dimension_mapping[c]
        for c in parent_concepts
        if c in bridge.concept_dimension_mapping
    ]

    if not parent_mappings:
        return bridge.assign_concept_mappings(new_concept)

    # Average weights per (type, dim_idx)
    accum: Dict[Tuple[str, int], List[float]] = {}
    for mappings in parent_mappings:
        for mtype, dim_idx, weight in mappings:
            accum.setdefault((mtype, dim_idx), []).append(weight)

    dimensions = [
        (mtype, dim_idx, float(np.mean(weights)))
        for (mtype, dim_idx), weights in accum.items()
    ]

    bridge.concept_dimension_mapping[new_concept] = dimensions
    return dimensions
