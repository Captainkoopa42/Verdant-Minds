"""Unit tests for pressure-driven basin budding."""

from __future__ import annotations

import networkx as nx

from verdant.memory.basins import BasinInfo
from verdant.memory.basin_dynamics import maybe_bud_basin
from verdant.memory.basin_state import BasinState
from verdant.memory.graph import MemoryWeb


def test_budding_creates_new_basin_and_preserves_parent_connectivity() -> None:
    memory = MemoryWeb()
    nodes = [f"n{i}" for i in range(20)]
    for i, node in enumerate(nodes):
        access = 100 if i == 0 else 1
        memory.add_concept(node, stability=0.01, metadata={"access_count": access})
        memory.memory_store[node]["access_count"] = access
        memory.graph.nodes[node]["access_count"] = access

    core = nodes[:10]
    leaves = nodes[10:]
    for i, u in enumerate(core):
        for v in core[i + 1 :]:
            memory.connect(u, v, 0.95)
    for i, leaf in enumerate(leaves):
        memory.connect(leaf, core[i % len(core)], 0.6)

    basin = BasinInfo(
        basin_id="basin_0",
        nodes=nodes,
        size=20,
        internal_edges=memory.graph.subgraph(nodes).number_of_edges(),
        boundary_edges=0,
        internal_density=0.9,
        emergent_count=0,
        mean_stability=0.01,
        top_nodes_by_access=[("n0", 100)],
        created_at=0.0,
    )
    states = {"basin_0": BasinState(basin_id="basin_0", member_nodes=nodes, local_metrics={"created_cycle": 0})}

    result = maybe_bud_basin(
        memory,
        basin,
        states,
        cycle=30,
        next_basin_id=1,
        pressure_threshold=0.0001,
        split_fraction=0.2,
        min_size_for_split=12,
        min_age_for_split=20,
    )

    assert result is not None
    assert result.new_basin_id in states
    assert len(states["basin_0"].member_nodes) < 20

    for node in states[result.new_basin_id].member_nodes:
        meta = memory.get_concept(node)["metadata"]
        assert meta["basin_origin"] == "budded"
        assert meta["parent_basin"] == "basin_0"
        assert meta["bud_cycle"] == 30

    parent_sub = memory.graph.subgraph(states["basin_0"].member_nodes)
    assert nx.is_connected(parent_sub)
