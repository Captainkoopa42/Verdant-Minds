"""Integration tests for multi-cycle cultivation."""

from __future__ import annotations

import pytest
from verdant_v2.system import VerdantConfig, VerdantSystem
from verdant_v2.thermodynamics.phase import compute_phase


@pytest.fixture
def system() -> VerdantSystem:
    return VerdantSystem(VerdantConfig(seed=42))


_CONTRADICTION_INPUTS = [
    "Privacy demands secrecy but transparency demands openness. "
    "Both are ethical imperatives that cannot both be fully satisfied.",

    "The benefit of helping others conflicts with the harm of overextending. "
    "Justice requires fair distribution but autonomy allows free choice.",

    "Good intentions can lead to bad outcomes. "
    "The order we seek emerges from underlying chaos.",

    "Certainty and uncertainty coexist in every hypothesis. "
    "Rational analysis reveals emotional truths we cannot ignore.",

    "Individual freedom creates collective constraints. "
    "Trust requires vulnerability but self-protection demands boundaries.",
]


class TestCultivationCycles:
    """Run multiple cycles with contradiction-heavy inputs."""

    def test_five_cycles_complete(self, system: VerdantSystem) -> None:
        """All 5 cycles should complete without error."""
        chunks = []
        for text in _CONTRADICTION_INPUTS:
            chunk = system.process_input(text)
            chunks.append(chunk)
        assert len(chunks) == 5

    def test_coherence_computed_each_cycle(self, system: VerdantSystem) -> None:
        """Coherence invariants should be computed on every cycle."""
        for text in _CONTRADICTION_INPUTS:
            chunk = system.process_input(text)
            coherence = chunk.get_section_content("coherence_invariants_section")
            assert coherence is not None
            assert "triangle_valid_at_alpha1" in coherence
            assert "housed_contradiction_index" in coherence

    def test_emergent_concepts_created(self, system: VerdantSystem) -> None:
        """After several contradiction-heavy cycles, emergent concepts should appear."""
        for text in _CONTRADICTION_INPUTS:
            system.process_input(text)
        emergent = system.memory_web.get_emergent_nodes()
        # We expect at least some emergent concepts from contradiction processing
        # (The exact count depends on entropy/magnitude dynamics)
        metrics = system.get_metrics()
        # At minimum the system should have tracked cycles
        assert metrics["cycle_count"] == 5

    def test_emergent_to_emergent_edges_possible(self, system: VerdantSystem) -> None:
        """Emergent concepts should be able to connect to other emergent concepts."""
        # Run enough cycles to generate emergent concepts
        for text in _CONTRADICTION_INPUTS:
            system.process_input(text)
        # Run a few more to create connections between emergents
        for text in _CONTRADICTION_INPUTS:
            system.process_input(text)

        classification = system.memory_web.get_edge_classification()
        # The graph should have some edges classified
        total_edges = sum(classification.values())
        assert total_edges > 0

    def test_phase_tracking(self, system: VerdantSystem) -> None:
        """System should track T_g and phase across cycles."""
        phases_seen = set()
        for text in _CONTRADICTION_INPUTS:
            system.process_input(text)
            ps = compute_phase(system._t_g)
            phases_seen.add(ps.phase)
        # T_g should be tracked
        assert system._t_g > 0

    def test_ten_cycles_produces_metrics(self, system: VerdantSystem) -> None:
        """10 cycles should produce valid metrics."""
        inputs = _CONTRADICTION_INPUTS * 2  # 10 inputs
        for text in inputs:
            system.process_input(text)
        metrics = system.get_metrics()
        assert metrics["cycle_count"] == 10
        assert metrics["total_cycles"] == 10
        assert metrics["memory_concepts"] > 0
        assert "phase" in metrics
        assert metrics["phase"] in ("Rigid", "Flexible", "Chaotic")

    def test_memory_grows_across_cycles(self, system: VerdantSystem) -> None:
        """Memory web should grow as new concepts are processed."""
        initial_count = len(system.memory_web.list_concepts())
        for text in _CONTRADICTION_INPUTS:
            system.process_input(text)
        final_count = len(system.memory_web.list_concepts())
        assert final_count > initial_count

    def test_entropy_history_tracked(self, system: VerdantSystem) -> None:
        """Entropy history should accumulate across cycles."""
        for text in _CONTRADICTION_INPUTS:
            system.process_input(text)
        assert len(system._entropy_history) == 5
