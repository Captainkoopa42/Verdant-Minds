"""ContinualLearningBlock — parameter adaptation and bridge hooks.

Reads: ``memory_section``, ``reasoning_section``, ``ethics_king_section``,
       ``action_selection_section``, ``wave_function_section``
Writes: ``continual_learning_section``
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np

from ethomorphic.bridge.bridge import EthomorphicBridge
from verdant.ethomorphic_config import detect_and_create_emergent_concepts_with_params
from verdant.pipeline.chunk import CognitiveChunk


class LearningBlock:
    """Adapts system parameters and triggers emergent concept detection."""

    name: str = "ContinualLearning"

    def __init__(self, bridge: Optional[EthomorphicBridge] = None) -> None:
        self.bridge = bridge
        self.learning_rates: Dict[str, float] = {
            "memory": 0.05,
            "reasoning": 0.03,
            "ethics": 0.07,
            "action": 0.04,
        }
        self.reinforcement_cycles: int = 0

    def process(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Adapt parameters from processing results."""
        memory = chunk.get_section_content("memory_section") or {}
        reasoning = chunk.get_section_content("reasoning_section") or {}
        ethics = chunk.get_section_content("ethics_king_section") or {}
        action = chunk.get_section_content("action_selection_section") or {}
        wave = chunk.get_section_content("wave_function_section") or {}

        memory_updates = self._update_memory_patterns(memory)
        reasoning_refine = self._refine_reasoning(reasoning)
        ethics_improve = self._refine_ethics(ethics)
        action_tune = self._tune_actions(action)
        self._adapt_rates()
        self.reinforcement_cycles += 1

        # Bridge integration
        emergent_created = 0
        if self.bridge is not None:
            magnitude = float(wave.get("magnitude", 0.0))
            if magnitude > 0.15:
                ecwf = self.bridge.ecwf
                cog = np.ones((1, 1, ecwf.num_cognitive_dims)) * 0.5
                eth = np.ones((1, 1, ecwf.num_ethical_dims)) * 0.5
                t = time.time() % 1000
                wo = ecwf.compute_ecwf(cog, eth, t)
                created = detect_and_create_emergent_concepts_with_params(self.bridge, wo, t)
                emergent_created = len(created)

        chunk.update_section("continual_learning_section", {
            "memory_updates": memory_updates,
            "reasoning_refinements": reasoning_refine,
            "ethics_improvements": ethics_improve,
            "action_tuning": action_tune,
            "learning_rates": dict(self.learning_rates),
            "reinforcement_cycles": self.reinforcement_cycles,
            "emergent_concepts_created": emergent_created,
            "processed_timestamp": time.time(),
        })
        chunk.add_processing_step(self.name, "continual_learning", {
            "cycle": self.reinforcement_cycles,
            "emergent_created": emergent_created,
        })
        return chunk

    # ------------------------------------------------------------------

    def _update_memory_patterns(self, memory: Dict[str, Any]) -> List[Dict[str, Any]]:
        updates: List[Dict[str, Any]] = []
        activations = memory.get("activated_concepts", {})
        lr = self.learning_rates["memory"]
        for concept, level in list(activations.items())[:10]:
            delta = lr * level
            updates.append({"concept": concept, "stability_delta": delta})
        return updates

    def _refine_reasoning(self, reasoning: Dict[str, Any]) -> List[Dict[str, Any]]:
        refinements: List[Dict[str, Any]] = []
        inferences = reasoning.get("inferences", {})
        for rtype, items in inferences.items():
            if items:
                avg_conf = sum(i.get("confidence", 0.5) for i in items) / len(items)
                refinements.append({"type": rtype, "avg_confidence": avg_conf, "count": len(items)})
        return refinements

    def _refine_ethics(self, ethics: Dict[str, Any]) -> List[Dict[str, Any]]:
        improvements: List[Dict[str, Any]] = []
        evaluation = ethics.get("evaluation", {})
        status = evaluation.get("status", "good")
        lr = self.learning_rates["ethics"]
        if status == "review_needed":
            improvements.append({"adjustment": "increase_sensitivity", "delta": lr})
        elif status == "excellent":
            improvements.append({"adjustment": "decrease_sensitivity", "delta": -lr * 0.5})
        return improvements

    def _tune_actions(self, action: Dict[str, Any]) -> List[Dict[str, Any]]:
        tuning: List[Dict[str, Any]] = []
        selected = action.get("selected_action", "")
        conf = action.get("action_confidence", 0.5)
        if selected:
            tuning.append({"action": selected, "confidence": conf})
        return tuning

    def _adapt_rates(self) -> None:
        baselines = {"memory": 0.05, "reasoning": 0.03, "ethics": 0.07, "action": 0.04}
        for key in self.learning_rates:
            self.learning_rates[key] = self.learning_rates[key] * 0.9 + baselines[key] * 0.1
