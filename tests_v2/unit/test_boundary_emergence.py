"""Unit tests for cross-basin boundary emergents."""

from __future__ import annotations

from ethomorphic.bridge.bridge import EthomorphicBridge
from ethomorphic.ecwf.core import ECWFCore

from verdant_v2.memory.basins import BasinInfo
from verdant_v2.memory.basin_dynamics import maybe_create_boundary_emergents
from verdant_v2.memory.graph import MemoryWeb


def test_boundary_emergence_and_cooldown() -> None:
    memory = MemoryWeb()
    ecwf = ECWFCore(num_cognitive_dims=5, num_ethical_dims=5, random_state=42)
    bridge = EthomorphicBridge(ecwf=ecwf, memory=memory)

    a_nodes = ["a0", "a1", "a2", "a3"]
    b_nodes = ["b0", "b1", "b2", "b3"]
    for n in a_nodes + b_nodes:
        memory.add_concept(n, stability=0.4, metadata={})

    for i, u in enumerate(a_nodes):
        for v in a_nodes[i + 1 :]:
            memory.connect(u, v, 0.8)
    for i, u in enumerate(b_nodes):
        for v in b_nodes[i + 1 :]:
            memory.connect(u, v, 0.8)
    memory.connect("a0", "b0", 0.9)
    memory.connect("a1", "b1", 0.9)

    active = {
        n: 0.0 for n in a_nodes + b_nodes
    }
    active.update({"a0": 0.9, "a1": 0.8, "a2": 0.6, "b0": 0.9, "b1": 0.8, "b2": 0.6})

    basins = [
        BasinInfo("basin_0", a_nodes, 4, 6, 2, 1.0, 0, 0.2, [], 0.0),
        BasinInfo("basin_1", b_nodes, 4, 6, 2, 1.0, 0, 0.2, [], 0.0),
    ]
    cooldowns: dict[frozenset[str], int] = {}

    first = maybe_create_boundary_emergents(
        memory,
        bridge,
        basins,
        active,
        cycle=10,
        threshold=0.1,
        cooldown_cycles=10,
        last_boundary_cycles=cooldowns,
    )
    assert first.created_count == 1

    created = [n for n in memory.list_concepts() if n.startswith("Emergent_boundary")]
    assert created
    meta = memory.get_concept(created[0])["metadata"]
    assert meta["boundary"] is True

    neighbors = set(memory.graph.neighbors(created[0]))
    assert any(n in neighbors for n in a_nodes)
    assert any(n in neighbors for n in b_nodes)

    second = maybe_create_boundary_emergents(
        memory,
        bridge,
        basins,
        active,
        cycle=15,
        threshold=0.1,
        cooldown_cycles=10,
        last_boundary_cycles=cooldowns,
    )
    assert second.created_count == 0
