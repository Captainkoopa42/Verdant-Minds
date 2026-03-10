"""Unit tests for global graph density regulation."""

from __future__ import annotations

from verdant_v2.memory.basin_dynamics import regulate_density
from verdant_v2.memory.graph import MemoryWeb


def test_regulate_density_prunes_weakest_edges_to_target_ratio() -> None:
    memory = MemoryWeb()
    nodes = [f"n{i}" for i in range(5)]
    for n in nodes:
        memory.add_concept(n, stability=0.5, metadata={})

    for i, u in enumerate(nodes):
        for j, v in enumerate(nodes[i + 1 :], start=i + 1):
            memory.connect(u, v, weight=0.1 + 0.1 * (i + j))

    before_ratio = memory.graph.number_of_edges() / memory.graph.number_of_nodes()
    assert before_ratio > 1.0

    removed = regulate_density(memory, max_edge_ratio=1.0, prune_to_ratio=0.6)
    after_ratio = memory.graph.number_of_edges() / memory.graph.number_of_nodes()

    assert removed > 0
    assert after_ratio <= 0.6
    # Lowest-weight edge should be pruned first.
    assert not memory.graph.has_edge("n0", "n1")
