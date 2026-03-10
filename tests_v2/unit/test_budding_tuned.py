"""Unit tests for tuned budding thresholds and pressure diagnostics."""

from __future__ import annotations

from verdant_v2.memory.basins import BasinInfo
from verdant_v2.memory.basin_dynamics import compute_basin_pressure, maybe_bud_basin
from verdant_v2.memory.basin_state import BasinState
from verdant_v2.memory.graph import MemoryWeb


def test_budding_fires_with_tuned_thresholds_and_breakdown() -> None:
    memory = MemoryWeb()
    nodes = [f"n{i}" for i in range(12)]
    for i, node in enumerate(nodes):
        access = 400 if i == 0 else 1
        memory.add_concept(node, stability=0.01, metadata={})
        memory.memory_store[node]["access_count"] = access
        memory.graph.nodes[node]["access_count"] = access

    for i, u in enumerate(nodes):
        for v in nodes[i + 1 :]:
            memory.connect(u, v, 0.95)

    basin = BasinInfo(
        basin_id="basin_0",
        nodes=nodes,
        size=len(nodes),
        internal_edges=memory.graph.subgraph(nodes).number_of_edges(),
        boundary_edges=0,
        internal_density=1.0,
        emergent_count=0,
        mean_stability=0.01,
        top_nodes_by_access=[("n0", 400)],
        created_at=0.0,
    )
    states = {"basin_0": BasinState(basin_id="basin_0", member_nodes=nodes, local_metrics={"created_cycle": 0})}

    breakdown = compute_basin_pressure(memory, basin)
    assert breakdown.raw_pressure > 0.01
    assert breakdown.internal_density == 1.0
    assert breakdown.stability_factor > 0.9
    assert breakdown.inverse_entropy > 0.0

    result = maybe_bud_basin(
        memory,
        basin,
        states,
        cycle=12,
        next_basin_id=1,
        pressure_threshold=0.01,
        split_fraction=0.2,
        min_size_for_split=8,
        min_age_for_split=10,
    )
    assert result is not None
