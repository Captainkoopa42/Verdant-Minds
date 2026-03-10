"""InternalCommunicationBlock — inter-block aggregation and conflict detection.

Reads: ``sensory_input_section``, ``pattern_recognition_section``, ``memory_section``
Writes: ``internal_communication_section``
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from verdant_v2.pipeline.chunk import CognitiveChunk


class CommunicationBlock:
    """Routes information between blocks, detects cross-block insights."""

    name: str = "InternalCommunication"

    def __init__(self) -> None:
        self.working_memory: Dict[str, float] = {}
        self.working_memory_capacity: int = 10
        self.decay_rate: float = 0.05

    def process(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Aggregate cross-block information and create integrated context."""
        sensory = chunk.get_section_content("sensory_input_section") or {}
        pattern = chunk.get_section_content("pattern_recognition_section") or {}
        memory = chunk.get_section_content("memory_section") or {}

        # Analyse information from multiple sources
        concepts = pattern.get("concepts", [])
        keywords = pattern.get("keywords", [])
        sentiment = pattern.get("sentiment", {})
        activations = memory.get("activated_concepts", {})
        tensions = pattern.get("tension_coefficients", {})

        # Determine priorities
        priorities = self._determine_priorities(pattern, memory, sensory)

        # Update working memory
        self._update_working_memory(concepts, activations)

        # Cross-block insights
        insights = self._detect_insights(chunk)

        # Integrated context
        integrated = {
            "primary_concepts": concepts[:7],
            "concept_activations": {c: activations.get(c, 0.0) for c in concepts[:7]},
            "sentiment_summary": sentiment,
            "tension_summary": tensions,
            "key_relationships": pattern.get("entities", []),
            "confidence_scores": {
                "pattern": pattern.get("question_confidence", 0.5),
                "memory": min(1.0, len(activations) / 5) if activations else 0.3,
            },
        }

        chunk.update_section("internal_communication_section", {
            "information_analysis": {
                "primary_concepts": concepts,
                "confidence_scores": integrated["confidence_scores"],
            },
            "information_priorities": priorities,
            "integrated_context": integrated,
            "cross_block_insights": insights,
            "working_memory_state": {
                "active_concepts": dict(sorted(
                    self.working_memory.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:self.working_memory_capacity]),
                "capacity": self.working_memory_capacity,
                "utilization": min(1.0, len(self.working_memory) / self.working_memory_capacity),
            },
            "processed_timestamp": time.time(),
        })
        chunk.add_processing_step(self.name, "communication_routing", {
            "insight_count": len(insights),
        })
        return chunk

    # ------------------------------------------------------------------

    def _determine_priorities(
        self,
        pattern: Dict[str, Any],
        memory: Dict[str, Any],
        sensory: Dict[str, Any],
    ) -> Dict[str, float]:
        priorities: Dict[str, float] = {
            "memory": 0.5,
            "reasoning": 0.5,
            "ethics": 0.5,
            "action": 0.5,
            "language": 0.5,
        }
        confidence = pattern.get("question_confidence", 0.5)
        if confidence > 0.7:
            priorities["reasoning"] += 0.15
            priorities["action"] += 0.1
        elif confidence < 0.4:
            priorities["memory"] += 0.15
            priorities["ethics"] += 0.1

        sentiment = pattern.get("sentiment", {})
        if sentiment.get("net_sentiment", 0) < -0.3:
            priorities["ethics"] += 0.15

        qtype = pattern.get("question_type", "statement")
        if qtype != "statement":
            priorities["reasoning"] += 0.1
            priorities["memory"] += 0.1
        return priorities

    def _update_working_memory(
        self,
        concepts: List[str],
        activations: Dict[str, float],
    ) -> None:
        # Decay existing entries
        for c in list(self.working_memory):
            self.working_memory[c] -= self.decay_rate
            if self.working_memory[c] <= 0:
                del self.working_memory[c]
        # Add / boost
        for c in concepts:
            salience = activations.get(c, 0.5)
            self.working_memory[c] = max(self.working_memory.get(c, 0.0), salience)
        # Evict if over capacity
        if len(self.working_memory) > self.working_memory_capacity:
            sorted_items = sorted(self.working_memory.items(), key=lambda x: x[1], reverse=True)
            self.working_memory = dict(sorted_items[:self.working_memory_capacity])

    def _detect_insights(self, chunk: CognitiveChunk) -> List[Dict[str, Any]]:
        insights: List[Dict[str, Any]] = []
        ethics = chunk.get_section_content("ethics_king_section") or {}
        action = chunk.get_section_content("action_selection_section") or {}
        reasoning = chunk.get_section_content("reasoning_section") or {}
        memory = chunk.get_section_content("memory_section") or {}

        # Ethics–memory resonance
        if ethics.get("evaluation", {}).get("status") in ("review_needed", "acceptable"):
            if memory.get("activated_concepts"):
                insights.append({
                    "type": "ethics_memory_resonance",
                    "importance": 0.8,
                    "source_blocks": ["EthicsValues", "MemoryStorage"],
                })

        # Confidence mismatch
        pattern_conf = (chunk.get_section_content("pattern_recognition_section") or {}).get(
            "question_confidence", 0.5
        )
        reasoning_conf = reasoning.get("confidence_score", 0.5)
        if abs(pattern_conf - reasoning_conf) > 0.3:
            insights.append({
                "type": "confidence_uncertainty_mismatch",
                "importance": 0.6,
                "source_blocks": ["PatternRecognition", "ReasoningPlanning"],
            })

        # Ethics–action alignment
        eval_status = ethics.get("evaluation", {}).get("status", "")
        selected = action.get("selected_action", "")
        if eval_status == "review_needed" and selected not in ("defer_decision", ""):
            insights.append({
                "type": "ethics_action_misalignment",
                "importance": 0.9,
                "source_blocks": ["EthicsValues", "ActionSelection"],
            })

        return insights
