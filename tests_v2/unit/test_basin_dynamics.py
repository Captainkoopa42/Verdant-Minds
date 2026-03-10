"""Unit tests for basin pruning dynamics."""

from __future__ import annotations

from verdant_v2.memory.basins import BasinInfo
from verdant_v2.memory.basin_dynamics import prune_basin_edges
from verdant_v2.memory.graph import MemoryWeb


def _make_two_community_web() -> tuple[MemoryWeb, BasinInfo, set[tuple[str, str]]]:
    memory = MemoryWeb()
    a_nodes = [f"a{i}" for i in range(6)]
    b_nodes = [f"b{i}" for i in range(6)]
    for n in a_nodes + b_nodes:
        memory.add_concept(n, stability=0.4, metadata={})

    for i, u in enumerate(a_nodes):
        for v in a_nodes[i + 1 :]:
            w = 0.8 if abs(i - int(v[1:])) <= 2 else 0.1
            memory.connect(u, v, w)

    for i, u in enumerate(b_nodes):
        for v in b_nodes[i + 1 :]:
            memory.connect(u, v, 0.75 if abs(i - int(v[1:])) <= 2 else 0.12)

    bridge_edges = {("a0", "b0"), ("a1", "b1"), ("a2", "b2")}
    for u, v in bridge_edges:
        memory.connect(u, v, 0.9)

    basin = BasinInfo(
        basin_id="basin_0",
        nodes=a_nodes,
        size=len(a_nodes),
        internal_edges=memory.graph.subgraph(a_nodes).number_of_edges(),
        boundary_edges=3,
        internal_density=1.0,
        emergent_count=0,
        mean_stability=0.2,
        top_nodes_by_access=[(a_nodes[0], 10)],
        created_at=0.0,
    )
    return memory, basin, bridge_edges


def test_prune_basin_edges_reduces_internal_density_only() -> None:
    memory, basin, bridge_edges = _make_two_community_web()
    before_internal = memory.graph.subgraph(basin.nodes).number_of_edges()

    result = prune_basin_edges(memory, basin, weight_threshold=0.2, keep_top_k=2)

    after_internal = memory.graph.subgraph(basin.nodes).number_of_edges()
    assert result.edges_pruned > 0
    assert before_internal > after_internal
    assert result.density_before > result.density_after

    for u, v in bridge_edges:
        assert memory.graph.has_edge(u, v)
