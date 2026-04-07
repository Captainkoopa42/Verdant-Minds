"""Unit tests for verdant.memory.graph.MemoryWeb."""

from __future__ import annotations

import pytest
from verdant.memory.graph import MemoryWeb


class TestMemoryBackendProtocol:
    """Verify MemoryWeb satisfies MemoryBackend protocol."""

    def test_has_add_concept(self) -> None:
        web = MemoryWeb()
        assert callable(web.add_concept)

    def test_has_get_concept(self) -> None:
        web = MemoryWeb()
        assert callable(web.get_concept)

    def test_has_connect(self) -> None:
        web = MemoryWeb()
        assert callable(web.connect)

    def test_has_get_neighbors(self) -> None:
        web = MemoryWeb()
        assert callable(web.get_neighbors)

    def test_has_list_concepts(self) -> None:
        web = MemoryWeb()
        assert callable(web.list_concepts)

    def test_has_reinforce(self) -> None:
        web = MemoryWeb()
        assert callable(web.reinforce)

    def test_has_decay(self) -> None:
        web = MemoryWeb()
        assert callable(web.decay)


class TestAddRetrieveConnect:
    """Test core CRUD operations."""

    def test_add_and_get(self) -> None:
        web = MemoryWeb()
        web.add_concept("foo", 0.7, {"domain": "test"})
        data = web.get_concept("foo")
        assert data is not None
        assert data["stability"] == pytest.approx(0.7)
        assert data["metadata"]["domain"] == "test"

    def test_get_missing_returns_none(self) -> None:
        web = MemoryWeb()
        assert web.get_concept("missing") is None

    def test_connect_and_neighbors(self) -> None:
        web = MemoryWeb()
        web.add_concept("a", 0.5)
        web.add_concept("b", 0.5)
        # "b" auto-connects to "a" on add, so explicit connect strengthens
        web.connect("a", "b", 0.8)
        assert "b" in web.get_neighbors("a")
        assert "a" in web.get_neighbors("b")

    def test_list_concepts(self) -> None:
        web = MemoryWeb()
        web.add_concept("x")
        web.add_concept("y")
        assert set(web.list_concepts()) == {"x", "y"}

    def test_reinforce_increases_stability(self) -> None:
        web = MemoryWeb()
        web.add_concept("c", 0.5)
        new = web.reinforce("c", 0.2)
        assert new == pytest.approx(0.7)

    def test_decay_decreases_stability(self) -> None:
        web = MemoryWeb()
        web.add_concept("c", 0.5)
        web.decay(0.1)
        assert web.get_concept("c")["stability"] == pytest.approx(0.4)

    def test_activate_concepts(self) -> None:
        web = MemoryWeb()
        web.add_concept("root", 0.8)
        web.add_concept("child", 0.6)
        web.connect("root", "child", 0.7)
        activations = web.activate_concepts(["root"])
        assert "root" in activations
        assert activations["root"] > 0


class TestEmergentNodes:
    """Test emergent node filtering."""

    def test_get_emergent_nodes_empty(self) -> None:
        web = MemoryWeb()
        web.add_concept("normal", 0.5)
        assert web.get_emergent_nodes() == []

    def test_get_emergent_nodes_filters(self) -> None:
        web = MemoryWeb()
        web.add_concept("seeded", 0.5)
        web.add_concept("Emergent_test_abc123", 0.5)
        web.add_concept("Emergent_other_def456", 0.5)
        result = web.get_emergent_nodes()
        assert len(result) == 2
        assert all(r.startswith("Emergent_") for r in result)


class TestEdgeClassification:
    """Test edge classification counts."""

    def test_all_seeded(self) -> None:
        web = MemoryWeb()
        web.add_concept("a", 0.5)
        web.add_concept("b", 0.5)
        web.connect("a", "b", 0.5)
        cls = web.get_edge_classification()
        assert cls["seeded_seeded"] >= 1
        assert cls["emergent_emergent"] == 0

    def test_mixed_edges(self) -> None:
        web = MemoryWeb()
        web.add_concept("seeded", 0.5)
        web.add_concept("Emergent_x", 0.5)
        web.connect("seeded", "Emergent_x", 0.5)
        cls = web.get_edge_classification()
        assert cls["emergent_seeded"] >= 1

    def test_emergent_to_emergent(self) -> None:
        web = MemoryWeb()
        web.add_concept("Emergent_a", 0.5)
        web.add_concept("Emergent_b", 0.5)
        web.connect("Emergent_a", "Emergent_b", 0.5)
        cls = web.get_edge_classification()
        assert cls["emergent_emergent"] >= 1


class TestChunkedSerialization:
    """Test to_chunks / to_state_dict / from_state_dict roundtrips."""

    def test_to_chunks_format(self) -> None:
        web = MemoryWeb()
        web.add_concept("x", 0.6, {"foo": "bar"})
        chunks = web.to_chunks()
        assert "nodes" in chunks
        assert "edges" in chunks
        assert "emergent_summary" in chunks
        assert "x" in chunks["nodes"]

    def test_state_dict_roundtrip(self) -> None:
        web = MemoryWeb()
        web.add_concept("alpha", 0.7, {"domain": "test"})
        web.add_concept("beta", 0.6)
        web.connect("alpha", "beta", 0.8)

        state = web.to_state_dict()
        restored = MemoryWeb.from_state_dict(state)

        assert set(restored.list_concepts()) == {"alpha", "beta"}
        assert restored.get_concept("alpha")["stability"] == pytest.approx(0.7)
        assert "beta" in restored.get_neighbors("alpha")
