"""MemoryBlock — interfaces with MemoryWeb and the ethomorphic bridge.

Reads: ``pattern_recognition_section``
Writes: ``memory_section``, ``wave_function_section``
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np

from ethomorphic.bridge.bridge import EthomorphicBridge
from ethomorphic.bridge.emergence import detect_and_create_emergent_concepts
from verdant_v2.memory.activation import spread_activation
from verdant_v2.memory.graph import MemoryWeb
from verdant_v2.pipeline.chunk import CognitiveChunk
from verdant_v2.thermodynamics.phase import PhaseState, compute_phase


class MemoryBlock:
    """Retrieves, activates, and updates memory; runs bridge bidirectional update."""

    name: str = "MemoryStorage"

    def __init__(
        self,
        memory_web: MemoryWeb,
        bridge: EthomorphicBridge,
    ) -> None:
        self.memory_web = memory_web
        self.bridge = bridge

    def process(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Run memory retrieval, bridge update, and phase-dependent maintenance."""
        pattern = chunk.get_section_content("pattern_recognition_section") or {}
        concepts: List[str] = pattern.get("concepts", [])
        keywords: List[str] = pattern.get("keywords", [])
        all_concepts = list(dict.fromkeys(concepts + keywords))

        # Spreading activation
        activations = spread_activation(self.memory_web, all_concepts)

        # Retrieve related
        related: Dict[str, float] = {}
        for c in all_concepts[:5]:
            for label, rel in self.memory_web.retrieve_related(c, depth=2, limit=5):
                if label not in related or related[label] < rel:
                    related[label] = rel

        # Ensure concepts exist in memory
        for c in all_concepts:
            if self.memory_web.get_concept(c) is None:
                self.memory_web.add_concept(c, stability=0.5)

        # Bridge bidirectional update
        ecwf = self.bridge.ecwf
        cog_state = np.ones((1, 1, ecwf.num_cognitive_dims)) * 0.5
        eth_state = np.ones((1, 1, ecwf.num_ethical_dims)) * 0.5
        t = time.time() % 1000
        bridge_result = self.bridge.bidirectional_update(cog_state, eth_state, all_concepts, t)

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
        for c in all_concepts:
            if c in activations and activations[c] > 0.3:
                self.memory_web.reinforce(c, ps.reinforcement_amount)
                reinforced.append(c)

        # Emergent concept detection
        wave_output = ecwf.compute_ecwf(cog_state, eth_state, t)
        emergent = detect_and_create_emergent_concepts(self.bridge, wave_output, t)

        # Novelty score
        known = set(self.memory_web.list_concepts())
        novel_count = sum(1 for c in all_concepts if c not in known)
        novelty = min(1.0, novel_count / max(len(all_concepts), 1))

        chunk.update_section("memory_section", {
            "retrieved_concepts": related,
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
