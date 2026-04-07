"""Unit tests for memory intervention helpers."""

from __future__ import annotations

from verdant.memory.graph import MemoryWeb
from verdant.memory.interventions import (
    ablate_oldest_emergent_nodes,
    get_emergent_nodes_sorted_by_age,
    scramble_emergent_edges,
)


def _build_web() -> MemoryWeb:
    web = MemoryWeb()
    web.add_concept("seed", 0.8)
    for idx in range(5):
        label = f"Emergent_{idx}"
        web.add_concept(label, 0.6, {"created_at": float(100 + idx)})
    web.connect("Emergent_0", "Emergent_1", 0.4)
    web.connect("Emergent_1", "Emergent_2", 0.5)
    web.connect("Emergent_2", "Emergent_3", 0.6)
    web.connect("Emergent_3", "Emergent_4", 0.7)
    return web


def test_get_emergent_nodes_sorted_by_age_oldest_first() -> None:
    web = _build_web()
    ordered = get_emergent_nodes_sorted_by_age(web)
    assert ordered[:3] == ["Emergent_0", "Emergent_1", "Emergent_2"]


def test_ablate_oldest_removes_expected_nodes() -> None:
    web = _build_web()
    stats = ablate_oldest_emergent_nodes(web, fraction=0.4)
    assert stats["removed_count"] == 2
    assert stats["removed_nodes"] == ["Emergent_0", "Emergent_1"]
    assert "Emergent_0" not in web.memory_store
    assert "Emergent_1" not in web.memory_store


def test_scramble_preserves_ee_edge_count_and_no_self_loops() -> None:
    web = _build_web()
    before = web.get_edge_classification()["emergent_emergent"]
    stats = scramble_emergent_edges(web, rng_seed=123)
    after = web.get_edge_classification()["emergent_emergent"]

    assert stats["scrambled_edge_count"] == stats["original_edge_count"]
    assert before == after
    for u, v in web.graph.edges():
        assert u != v


def test_scramble_is_deterministic_with_fixed_seed() -> None:
    web1 = _build_web()
    web2 = _build_web()

    scramble_emergent_edges(web1, rng_seed=777)
    scramble_emergent_edges(web2, rng_seed=777)

    ee1 = sorted(tuple(sorted((u, v))) for u, v in web1.graph.edges() if u.startswith("Emergent_") and v.startswith("Emergent_"))
    ee2 = sorted(tuple(sorted((u, v))) for u, v in web2.graph.edges() if u.startswith("Emergent_") and v.startswith("Emergent_"))
    assert ee1 == ee2
