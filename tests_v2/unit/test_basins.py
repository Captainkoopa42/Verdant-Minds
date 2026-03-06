"""Unit tests for basin detection."""

from __future__ import annotations

from verdant_v2.memory.basins import detect_basins
from verdant_v2.memory.graph import MemoryWeb


def test_detect_basins_two_clusters_bridge() -> None:
    web = MemoryWeb()

    cluster_a = ["a1", "a2", "a3", "Emergent_a4", "a5"]
    cluster_b = ["b1", "b2", "b3", "b4", "Emergent_b5"]

    for node in cluster_a + cluster_b:
        web.add_concept(node, stability=0.6)

    # Dense cluster A
    for i, src in enumerate(cluster_a):
        for dst in cluster_a[i + 1 :]:
            web.connect(src, dst, 0.95)

    # Dense cluster B
    for i, src in enumerate(cluster_b):
        for dst in cluster_b[i + 1 :]:
            web.connect(src, dst, 0.95)

    # sparse bridge
    web.connect("a1", "b1", 0.05)

    basins = detect_basins(web, k=3, min_size=3)
    assert len(basins) >= 2

    # Ensure emergent counting and density/boundary are populated
    for basin in basins:
        assert basin.internal_density >= 0.0
        assert basin.boundary_edges >= 0

    emergent_total = sum(b.emergent_count for b in basins)
    assert emergent_total >= 2

    largest = basins[0]
    assert largest.internal_edges > 0
