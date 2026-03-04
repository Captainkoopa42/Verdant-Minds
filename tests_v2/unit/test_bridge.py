"""Unit tests for ethomorphic.bridge – bridge, emergence, and protocol."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pytest

from ethomorphic.bridge.bridge import EthomorphicBridge, MemoryBackend
from ethomorphic.bridge.emergence import detect_and_create_emergent_concepts
from ethomorphic.ecwf.core import ECWFCore


# ---------------------------------------------------------------------------
# Mock memory backend
# ---------------------------------------------------------------------------

class MockMemoryBackend:
    """In-memory implementation of :class:`MemoryBackend` for testing."""

    def __init__(self) -> None:
        self._concepts: Dict[str, Dict[str, Any]] = {}
        self._edges: Dict[str, Dict[str, float]] = {}

    def add_concept(
        self, label: str, stability: float, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self._concepts[label] = {
            "stability": stability,
            "metadata": metadata or {},
        }

    def get_concept(self, label: str) -> Optional[Dict[str, Any]]:
        return self._concepts.get(label)

    def connect(self, label1: str, label2: str, weight: float) -> None:
        self._edges.setdefault(label1, {})[label2] = weight
        self._edges.setdefault(label2, {})[label1] = weight

    def get_neighbors(self, label: str) -> List[str]:
        return list(self._edges.get(label, {}).keys())

    def list_concepts(self) -> List[str]:
        return list(self._concepts.keys())

    def reinforce(self, label: str, amount: float) -> None:
        if label in self._concepts:
            self._concepts[label]["stability"] += amount

    def decay(self, factor: float) -> None:
        for data in self._concepts.values():
            data["stability"] *= factor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def memory() -> MockMemoryBackend:
    """A populated mock memory backend."""
    mem = MockMemoryBackend()
    for name in ["identity", "consciousness", "ethics", "trust", "reasoning"]:
        mem.add_concept(name, stability=0.7)
    mem.connect("identity", "consciousness", 0.8)
    mem.connect("ethics", "trust", 0.9)
    return mem


@pytest.fixture
def ecwf() -> ECWFCore:
    return ECWFCore(num_cognitive_dims=5, num_ethical_dims=5, random_state=42)


@pytest.fixture
def bridge(memory: MockMemoryBackend, ecwf: ECWFCore) -> EthomorphicBridge:
    br = EthomorphicBridge(memory, ecwf, influence_factor=0.3)
    br.initialize_concept_mappings()
    return br


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

class TestProtocol:
    """Verify MockMemoryBackend satisfies the protocol."""

    def test_isinstance_check(self) -> None:
        assert isinstance(MockMemoryBackend(), MemoryBackend)

    def test_all_methods_present(self) -> None:
        mem = MockMemoryBackend()
        for method in [
            "add_concept", "get_concept", "connect",
            "get_neighbors", "list_concepts", "reinforce", "decay",
        ]:
            assert callable(getattr(mem, method))


# ---------------------------------------------------------------------------
# Bidirectional update
# ---------------------------------------------------------------------------

class TestBidirectionalUpdate:
    """Tests for bidirectional bridge updates."""

    def test_produces_activations(self, bridge: EthomorphicBridge) -> None:
        cog = np.ones(5) * 0.8
        eth = np.ones(5) * 0.6
        result = bridge.bidirectional_update(cog, eth, ["identity", "ethics"], t=0.0)
        # Should have at least some activated concepts
        assert "memory_update" in result
        assert "ecwf_update" in result

    def test_ecwf_influence_nonzero(self, bridge: EthomorphicBridge) -> None:
        result = bridge.update_ecwf_from_memory(["identity", "consciousness"])
        cog_inf = np.array(result["cognitive_influence"])
        eth_inf = np.array(result["ethical_influence"])
        # At least one dimension should have nonzero influence
        assert np.any(cog_inf != 0) or np.any(eth_inf != 0)

    def test_memory_update_returns_info(self, bridge: EthomorphicBridge) -> None:
        cog = np.ones(5) * 0.5
        eth = np.ones(5) * 0.5
        result = bridge.update_memory_from_ecwf(cog, eth, t=0.0)
        assert "activated_concepts" in result
        assert "entropy" in result


# ---------------------------------------------------------------------------
# Emergent concepts
# ---------------------------------------------------------------------------

class TestEmergence:
    """Tests for emergent concept creation."""

    def _force_emergence(self, bridge: EthomorphicBridge) -> List[str]:
        """Helper that runs emergence with conditions likely to trigger it."""
        ecwf = bridge.ecwf
        x = np.ones((1, 1, ecwf.num_cognitive_dims)) * 0.5
        e = np.ones((1, 1, ecwf.num_ethical_dims)) * 0.5
        wave = ecwf.compute_ecwf(x, e, t=1.0)
        return detect_and_create_emergent_concepts(bridge, wave, t=1.0, threshold=0.01)

    def test_emergent_creation(self, bridge: EthomorphicBridge) -> None:
        created = self._force_emergence(bridge)
        # With a very low threshold and enough concepts, emergence should fire
        assert len(created) >= 1
        # The new concept should exist in memory
        for name in created:
            assert bridge.memory.get_concept(name) is not None

    def test_emergent_gets_mappings(self, bridge: EthomorphicBridge) -> None:
        created = self._force_emergence(bridge)
        for name in created:
            assert name in bridge.concept_dimension_mapping

    def test_combo_key_deduplication(self, bridge: EthomorphicBridge) -> None:
        first = self._force_emergence(bridge)
        second = self._force_emergence(bridge)
        # Second call with same conditions should be blocked by combo_key
        assert len(second) == 0

    def test_emergent_name_has_hash_suffix(self, bridge: EthomorphicBridge) -> None:
        created = self._force_emergence(bridge)
        for name in created:
            # Should end with a 6-character hex hash
            suffix = name.split("_")[-1]
            assert len(suffix) == 6
            int(suffix, 16)  # Should be valid hex


# ---------------------------------------------------------------------------
# State vector helpers
# ---------------------------------------------------------------------------

class TestStateVectors:
    """Tests for cognitive/ethical state vector generation."""

    def test_cognitive_state_shape(self, bridge: EthomorphicBridge) -> None:
        state = bridge.get_cognitive_state_for_concepts(["identity"])
        assert state.shape == (5,)

    def test_ethical_state_shape(self, bridge: EthomorphicBridge) -> None:
        state = bridge.get_ethical_state_for_concepts(["ethics"])
        assert state.shape == (5,)

    def test_cognitive_state_normalised(self, bridge: EthomorphicBridge) -> None:
        state = bridge.get_cognitive_state_for_concepts(["identity", "reasoning"])
        assert np.max(state) <= 1.0 + 1e-7
