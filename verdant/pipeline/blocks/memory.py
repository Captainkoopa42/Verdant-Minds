"""MemoryBlock — interfaces with MemoryWeb and the ethomorphic bridge.

Reads: ``pattern_recognition_section``
Writes: ``memory_section``, ``wave_function_section``
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import numpy as np

from ethomorphic.bridge.bridge import EthomorphicBridge
from verdant.ethomorphic_config import detect_and_create_emergent_concepts_with_params
from verdant.memory.activation import spread_activation
from verdant.memory.graph import MemoryWeb
from verdant.pipeline.chunk import CognitiveChunk
from verdant.thermodynamics.phase import PhaseState, compute_phase


class MemoryBlock:
    """Retrieves, activates, and updates memory; runs bridge bidirectional update."""

    name: str = "MemoryStorage"

    def __init__(
        self,
        memory_web: MemoryWeb,
        bridge: EthomorphicBridge,
        *,
        concept_min_length: int = 3,
        filter_numeric_concepts: bool = True,
        seeded_concepts: Optional[set[str]] = None,
    ) -> None:
        self.memory_web = memory_web
        self.bridge = bridge
        self.concept_min_length = max(1, int(concept_min_length))
        self.filter_numeric_concepts = bool(filter_numeric_concepts)
        self.seeded_concepts = set(seeded_concepts or set())

    _CONCEPT_STOPWORDS = {
        "and", "the", "for", "with", "from", "that", "this", "into",
        "about", "under", "while", "through", "across", "between",
        "their", "there", "these", "those", "have", "has", "had",
        "been", "being", "will", "would", "could", "should", "may",
        "might", "must", "onto", "than", "then", "also", "such",
    }
    _BASIN_ID_RE = re.compile(r"^basin_\d+$")
    _NUMERIC_RE = re.compile(r"^\d+$")
    _HEX_ID_RE = re.compile(r"^[a-f0-9]{6,}$")

    def _should_seed_concept(self, concept: str) -> bool:
        """Return True when a concept should be added as a new memory node."""
        if concept in self.seeded_concepts:
            return True

        normalized = concept.strip().lower()
        if not normalized:
            return False
        if len(normalized) < self.concept_min_length:
            return False
        if normalized in self._CONCEPT_STOPWORDS:
            return False
        if not self.filter_numeric_concepts:
            return True
        if self._NUMERIC_RE.fullmatch(normalized):
            return False
        if self._BASIN_ID_RE.fullmatch(normalized):
            return False
        if self._HEX_ID_RE.fullmatch(normalized):
            return False
        return True

    def process(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Run memory retrieval, bridge update, and phase-dependent maintenance."""
        pattern = chunk.get_section_content("pattern_recognition_section") or {}
        concepts: List[str] = pattern.get("concepts", [])
        keywords: List[str] = pattern.get("keywords", [])
        all_concepts = list(dict.fromkeys(concepts + keywords))

        routing = chunk.get_section_content("routing_section") or {}
        priority = routing.get("priority_seeds", []) if isinstance(routing, dict) else []
        prioritized = [c for c in priority if isinstance(c, str)] + all_concepts
        seed_concepts = list(dict.fromkeys(prioritized))

        # Spreading activation
        activations = spread_activation(self.memory_web, seed_concepts)

        # Retrieve related
        related: Dict[str, float] = {}
        for c in seed_concepts[:5]:
            for label, rel in self.memory_web.retrieve_related(c, depth=2, limit=5):
                if label not in related or related[label] < rel:
                    related[label] = rel

        # Ensure concepts exist in memory
        for c in seed_concepts:
            if self.memory_web.get_concept(c) is None:
                if not self._should_seed_concept(c):
                    continue
                self.memory_web.add_concept(c, stability=0.5)

        # Bridge bidirectional update
        ecwf = self.bridge.ecwf
        cog_state = np.ones((1, 1, ecwf.num_cognitive_dims)) * 0.5
        eth_state = np.ones((1, 1, ecwf.num_ethical_dims)) * 0.5
        pm = chunk.get_section_content("processing_metrics_section") or {}
        t = float(pm.get("cycle", 0)) + 1.0
        bridge_result = self.bridge.bidirectional_update(cog_state, eth_state, seed_concepts, t)

        # Extract wave properties
        mem_update = bridge_result.get("memory_update", {})
        magnitude = 0.0
        phase_val = 0.0
        entropy = 0.0
        wave_mag = mem_update.get("wave_magnitude", [])
        wave_phase = mem_update.get("wave_phase", [])
        if wave_mag:
            magnitude = float(wave_mag[0]) if isinstance(wave_mag, list) else float(wave_mag)
        if wave_phase:
            phase_val = float(wave_phase[0]) if isinstance(wave_phase, list) else float(wave_phase)
        entropy = float(mem_update.get("entropy", 0.0))

        # Phase-dependent decay / reinforcement
        metrics = chunk.get_section_content("processing_metrics_section") or {}
        t_g = float(metrics.get("glass_transition_temp", 0.5))
        ps = compute_phase(t_g)

        self.memory_web.decay(ps.decay_factor)
        reinforced: List[str] = []
        for c in seed_concepts:
            if c in activations and activations[c] > 0.3:
                self.memory_web.reinforce(c, ps.reinforcement_amount)
                reinforced.append(c)

        # Emergent concept detection
        wave_output = ecwf.compute_ecwf(cog_state, eth_state, t)
        emergent = detect_and_create_emergent_concepts_with_params(self.bridge, wave_output, t)

        # Novelty score
        known = set(self.memory_web.list_concepts())
        novel_count = sum(1 for c in seed_concepts if c not in known)
        novelty = min(1.0, novel_count / max(len(seed_concepts), 1))

        chunk.update_section("memory_section", {
            "retrieved_concepts": related,
            "routing_priority_count": len(priority),
            "activated_concepts": activations,
            "activation_levels": activations,
            "novelty_score": novelty,
            "emergent_concepts": emergent,
            "phase_memory_management": {
                "phase": ps.phase,
                "decay_factor": ps.decay_factor,
                "reinforcement": ps.reinforcement_amount,
                "concepts_reinforced": reinforced,
            },
        })
        chunk.update_section("wave_function_section", {
            "magnitude": magnitude,
            "phase": phase_val,
            "entropy": entropy,
        })
        chunk.add_processing_step(self.name, "memory_integration", {
            "activated": len(activations),
            "emergent_created": len(emergent),
        })
        return chunk
