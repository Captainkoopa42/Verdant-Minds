"""DataKing — information quality guardian.

Supervises: SensoryInput, PatternRecognition, MemoryStorage.
Evaluates quality, novelty, and relevance of information flowing
through the pipeline.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from verdant_v2.pipeline.chunk import CognitiveChunk


class DataKing:
    """Scores information quality and applies data governance policies."""

    name: str = "DataKing"

    def __init__(self, quality_threshold: float = 0.6, novelty_threshold: float = 0.3) -> None:
        self.quality_threshold = quality_threshold
        self.novelty_threshold = novelty_threshold
        self.metrics: Dict[str, Any] = {
            "total_oversights": 0,
            "quality_improvements": 0,
            "novelty_detections": 0,
            "avg_information_quality": 0.5,
        }

    def oversee(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Evaluate and improve information quality."""
        sensory = chunk.get_section_content("sensory_input_section") or {}
        pattern = chunk.get_section_content("pattern_recognition_section") or {}
        memory = chunk.get_section_content("memory_section") or {}

        quality = self._evaluate_quality(sensory, pattern)
        novelty = self._evaluate_novelty(pattern, memory)
        relevance = self._evaluate_relevance(pattern, memory)

        actions = self._apply_governance(chunk, quality, novelty, relevance)
        self._update_metrics(quality, novelty)
        self.metrics["total_oversights"] += 1

        chunk.update_section("data_king_section", {
            "quality_score": quality,
            "novelty_score": novelty,
            "relevance_score": relevance,
            "governance_actions": actions,
            "assessment_confidence": (quality + relevance) / 2,
            "timestamp": time.time(),
        })
        chunk.add_processing_step(self.name, "data_oversight", {
            "quality": quality,
            "novelty": novelty,
        })
        return chunk

    def to_state_dict(self) -> Dict[str, Any]:
        """Serialise state."""
        return {
            "quality_threshold": self.quality_threshold,
            "novelty_threshold": self.novelty_threshold,
            "metrics": self.metrics,
        }

    def from_state_dict(self, state: Dict[str, Any]) -> None:
        """Restore state."""
        self.quality_threshold = state.get("quality_threshold", self.quality_threshold)
        self.novelty_threshold = state.get("novelty_threshold", self.novelty_threshold)
        self.metrics.update(state.get("metrics", {}))

    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_quality(sensory: Dict[str, Any], pattern: Dict[str, Any]) -> float:
        base = 0.5
        tokens = sensory.get("token_count", 0)
        if tokens > 50:
            base += 0.1
        elif tokens < 10:
            base -= 0.1
        concepts = pattern.get("concept_count", 0)
        base += min(0.2, concepts * 0.03)
        conf = pattern.get("question_confidence", 0.5)
        base += 0.1 * conf
        return max(0.1, min(1.0, base))

    @staticmethod
    def _evaluate_novelty(pattern: Dict[str, Any], memory: Dict[str, Any]) -> float:
        concepts = set(pattern.get("concepts", []))
        activated = set(memory.get("activated_concepts", {}).keys())
        if not concepts:
            return 0.5
        known = concepts & activated
        return max(0.1, min(1.0, 1.0 - len(known) / len(concepts) if concepts else 0.5))

    @staticmethod
    def _evaluate_relevance(pattern: Dict[str, Any], memory: Dict[str, Any]) -> float:
        activated = memory.get("activated_concepts", {})
        if not activated:
            return 0.5
        avg = sum(activated.values()) / len(activated)
        return max(0.1, min(1.0, 0.4 + avg * 0.5))

    def _apply_governance(
        self,
        chunk: CognitiveChunk,
        quality: float,
        novelty: float,
        relevance: float,
    ) -> List[Dict[str, Any]]:
        actions: List[Dict[str, Any]] = []
        if quality < self.quality_threshold:
            actions.append({"type": "enhance_quality", "current": quality, "threshold": self.quality_threshold})
        if novelty > self.novelty_threshold:
            actions.append({"type": "prioritize_novel", "novelty": novelty})
        # Tag metadata
        mem = chunk.get_section_content("memory_section") or {}
        mem["data_quality"] = {"quality": quality, "novelty": novelty, "relevance": relevance}
        chunk.update_section("memory_section", mem)
        return actions

    def _update_metrics(self, quality: float, novelty: float) -> None:
        self.metrics["avg_information_quality"] = (
            0.9 * self.metrics["avg_information_quality"] + 0.1 * quality
        )
        if quality < self.quality_threshold:
            self.metrics["quality_improvements"] += 1
        if novelty > self.novelty_threshold:
            self.metrics["novelty_detections"] += 1
