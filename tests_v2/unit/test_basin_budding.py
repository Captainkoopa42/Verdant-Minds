"""Unit tests for basin budding gates and execution alignment."""

from __future__ import annotations

from verdant_v2.memory.basins import BasinInfo
from verdant_v2.memory.basin_dynamics import find_ejection_candidates, maybe_bud_basin
from verdant_v2.memory.basin_state import BasinState
from verdant_v2.memory.graph import MemoryWeb


def _make_basin(memory: MemoryWeb, nodes: list[str], *, density: float = 0.8) -> BasinInfo:
    return BasinInfo(
        basin_id="basin_0",
        nodes=nodes,
        size=len(nodes),
        internal_edges=memory.graph.subgraph(nodes).number_of_edges(),
        boundary_edges=0,
        internal_density=density,
        emergent_count=0,
        mean_stability=0.01,
        top_nodes_by_access=[(nodes[0], 100)],
        created_at=0.0,
    )


def test_maybe_bud_basin_returns_result_when_thresholds_and_ejection_pass() -> None:
    memory = MemoryWeb()
    nodes = [f"n{i}" for i in range(12)]
    for i, node in enumerate(nodes):
        access = 300 if i == 0 else 1
        memory.add_concept(node, stability=0.01, metadata={})
        memory.memory_store[node]["access_count"] = access
        memory.graph.nodes[node]["access_count"] = access
    for i, u in enumerate(nodes):
        for v in nodes[i + 1 :]:
            memory.connect(u, v, 0.9)

    basin = _make_basin(memory, nodes, density=1.0)
    states = {"basin_0": BasinState(basin_id="basin_0", member_nodes=nodes, local_metrics={"created_cycle": 0})}

    assert find_ejection_candidates(memory, basin, split_fraction=0.2)
    result = maybe_bud_basin(
        memory,
        basin,
        states,
        cycle=20,
        next_basin_id=1,
        pressure_threshold=0.001,
        split_fraction=0.2,
        min_size_for_split=8,
        min_age_for_split=10,
    )
    assert result is not None
    assert result.new_basin_id in states


def test_maybe_bud_basin_returns_none_when_parent_would_disconnect() -> None:
    memory = MemoryWeb()
    bridge_left = "a_bridge_left"
    bridge_right = "a_bridge_right"
    clique_a = ["c0", "c1", "c2", "c3"]
    clique_b = ["d0", "d1", "d2", "d3"]
    nodes = [bridge_left, bridge_right] + clique_a + clique_b
    for i, node in enumerate(nodes):
        access = 250 if i == 0 else 1
        memory.add_concept(node, stability=0.01, metadata={})
        memory.memory_store[node]["access_count"] = access
        memory.graph.nodes[node]["access_count"] = access
    memory.graph.clear_edges()

    for i, u in enumerate(clique_a):
        for v in clique_a[i + 1 :]:
            memory.graph.add_edge(u, v, weight=0.9)
    for i, u in enumerate(clique_b):
        for v in clique_b[i + 1 :]:
            memory.graph.add_edge(u, v, weight=0.9)
    memory.graph.add_edge(bridge_left, clique_a[0], weight=0.8)
    memory.graph.add_edge(bridge_left, bridge_right, weight=0.8)
    memory.graph.add_edge(bridge_right, clique_b[0], weight=0.8)

    basin = _make_basin(memory, nodes)
    states = {"basin_0": BasinState(basin_id="basin_0", member_nodes=nodes, local_metrics={"created_cycle": 0})}

    assert find_ejection_candidates(memory, basin, split_fraction=0.1) == []
    result = maybe_bud_basin(
        memory,
        basin,
        states,
        cycle=25,
        next_basin_id=1,
        pressure_threshold=0.001,
        split_fraction=0.1,
        min_size_for_split=8,
        min_age_for_split=10,
    )
    assert result is None


def test_diagnostic_candidate_check_matches_budding_outcome() -> None:
    memory = MemoryWeb()
    nodes = [f"x{i}" for i in range(10)]
    for i, node in enumerate(nodes):
        access = 220 if i == 0 else 1
        memory.add_concept(node, stability=0.01, metadata={})
        memory.memory_store[node]["access_count"] = access
        memory.graph.nodes[node]["access_count"] = access
    for i, u in enumerate(nodes):
        for v in nodes[i + 1 :]:
            memory.connect(u, v, 0.85)

    basin = _make_basin(memory, nodes, density=1.0)
    states = {"basin_0": BasinState(basin_id="basin_0", member_nodes=nodes, local_metrics={"created_cycle": 0})}

    ejection = find_ejection_candidates(memory, basin, split_fraction=0.2)
    result = maybe_bud_basin(
        memory,
        basin,
        states,
        cycle=20,
        next_basin_id=1,
        pressure_threshold=0.001,
        split_fraction=0.2,
        min_size_for_split=8,
        min_age_for_split=10,
    )
    assert bool(ejection) is (result is not None)
