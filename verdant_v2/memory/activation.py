"""Spreading activation as a standalone function.

Ported from v1 ``MemoryWeb.activate_concepts`` but decoupled from the
graph class so it can be reused with any ``MemoryWeb`` instance.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from verdant_v2.memory.graph import MemoryWeb


def spread_activation(
    graph: MemoryWeb,
    seeds: List[str],
    strength: float = 0.7,
    spread_factor: float = 0.5,
    max_depth: int = 3,
    threshold: float = 0.1,
) -> Dict[str, float]:
    """Run spreading activation from *seeds* through *graph*.

    Breadth-first propagation where activation decays by
    ``connection_weight * spread_factor`` at each hop.

    Args:
        graph: The memory web to activate over.
        seeds: Starting concept labels.
        strength: Initial activation for each seed.
        spread_factor: Multiplicative decay per hop.
        max_depth: Maximum propagation depth.
        threshold: Minimum activation to propagate.

    Returns:
        Mapping of concept label → activation level.
    """
    return graph.activate_concepts(
        seeds,
        strength=strength,
        spread_factor=spread_factor,
        max_depth=max_depth,
        threshold=threshold,
    )
