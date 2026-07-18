"""ForefrontKing — executive function, attention, and cognitive load.

Supervises: InternalCommunication, ReasoningPlanning, ActionSelection.
Derives phase controls and applies coherence feedback from ethomorphic.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from verdant.pipeline.chunk import CognitiveChunk
from verdant.thermodynamics.phase import compute_phase


class ForefrontKing:
    """Allocates attention, manages cognitive load, adjusts decision threshold."""

    name: str = "ForefrontKing"

    def __init__(self, decision_threshold: float = 0.7) -> None:
        self.attention_focus: str = ""
        self.cognitive_load: float = 0.5
        self.cognitive_capacity: float = 1.0
        self.decision_threshold: float = decision_threshold
        self.working_memory: Dict[str, float] = {}
        self.emotional_state: Dict[str, float] = {"valence": 0.5, "arousal": 0.5}
        self.metrics: Dict[str, Any] = {"total_oversights": 0}

    def oversee(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Apply executive oversight."""
        comm = chunk.get_section_content("internal_communication_section") or {}
        reasoning = chunk.get_section_content("reasoning_section") or {}
        action = chunk.get_section_content("action_selection_section") or {}
        coherence = chunk.get_section_content("coherence_invariants_section") or {}
        pattern = chunk.get_section_content("pattern_recognition_section") or {}

        integrated = comm.get("integrated_context", {})
        concepts = integrated.get("primary_concepts", pattern.get("concepts", []))

        # Attention
        focus = self._allocate_attention(concepts, pattern, reasoning)

        # Cognitive load
        load_info = self._manage_load(concepts, reasoning)

        # Working memory
        wm_info = self._update_working_memory(concepts, focus)

        # Threshold
        threshold_info = self._adjust_threshold(self.cognitive_load, reasoning, action)

        # Phase controls
        process_metrics = chunk.get_section_content("processing_metrics_section") or {}
        t_g = float(process_metrics.get("glass_transition_temp", 0.5))
        ps = compute_phase(t_g)
        phase_state = ps.phase
        self.cognitive_capacity = ps.capacity_multiplier
        phase_threshold = ps.decision_threshold

        # Coherence feedback
        hci = float(coherence.get("housed_contradiction_index", 0.0))
        triangle_valid = coherence.get("triangle_valid_at_alpha1", True)
        coherence_adj = 0.0
        if hci > 0.5:
            coherence_adj = 0.05
        if not triangle_valid:
            phase_state = "coherence_strained"

        # Blend threshold
        self.decision_threshold = max(0.4, min(0.9,
            threshold_info["new_threshold"] * 0.6 + phase_threshold * 0.4 + coherence_adj
        ))

        # Refine action
        action_refinement = self._refine_action(chunk, action, self.decision_threshold)

        # Emotional state
        emotion = self._update_emotion(action, self.cognitive_load)

        self.metrics["total_oversights"] += 1

        chunk.update_section("forefront_king_section", {
            "attention_focus": focus,
            "cognitive_load": self.cognitive_load,
            "cognitive_capacity": self.cognitive_capacity,
            "decision_threshold": self.decision_threshold,
            "phase_state": phase_state,
            "working_memory": dict(sorted(
                self.working_memory.items(), key=lambda x: x[1], reverse=True,
            )[:7]),
            "emotional_state": self.emotional_state,
            "coherence_feedback": {
                "hci": hci,
                "triangle_valid": triangle_valid,
                "threshold_adjustment": coherence_adj,
            },
            "action_refinement": action_refinement,
            "timestamp": time.time(),
        })
        chunk.add_processing_step(self.name, "executive_oversight", {
            "focus": self.attention_focus,
            "load": self.cognitive_load,
            "threshold": self.decision_threshold,
        })
        return chunk

    def to_state_dict(self) -> Dict[str, Any]:
        """Serialise state."""
        return {
            "attention_focus": self.attention_focus,
            "cognitive_load": self.cognitive_load,
            "cognitive_capacity": self.cognitive_capacity,
            "decision_threshold": self.decision_threshold,
            "emotional_state": self.emotional_state,
            "metrics": self.metrics,
        }

    def from_state_dict(self, state: Dict[str, Any]) -> None:
        """Restore state."""
        self.attention_focus = state.get("attention_focus", "")
        self.cognitive_load = state.get("cognitive_load", 0.5)
        self.cognitive_capacity = state.get("cognitive_capacity", 1.0)
        self.decision_threshold = state.get("decision_threshold", 0.7)
        self.emotional_state = state.get("emotional_state", {"valence": 0.5, "arousal": 0.5})
        self.metrics.update(state.get("metrics", {}))

    # ------------------------------------------------------------------

    def _allocate_attention(
        self,
        concepts: List[str],
        pattern: Dict[str, Any],
        reasoning: Dict[str, Any],
    ) -> str:
        # Highest-salience concept
        if concepts:
            self.attention_focus = concepts[0]
        return self.attention_focus

    def _manage_load(self, concepts: List[str], reasoning: Dict[str, Any]) -> Dict[str, Any]:
        baseline = 0.5
        load_change = 0.0
        if len(concepts) > 5:
            load_change += 0.1
        inferences = reasoning.get("inferences", {})
        total_inf = sum(len(v) for v in inferences.values() if isinstance(v, list))
        if total_inf > 3:
            load_change += 0.08 * min(total_inf / 10, 1)
        self.cognitive_load = max(0.1, min(0.95, (1 - 0.2) * self.cognitive_load + 0.2 * baseline + load_change))
        return {"load": self.cognitive_load, "change": load_change}

    def _update_working_memory(self, concepts: List[str], focus: str) -> Dict[str, Any]:
        for c in list(self.working_memory):
            self.working_memory[c] *= 0.95
            if self.working_memory[c] < 0.05:
                del self.working_memory[c]
        for c in concepts[:7]:
            self.working_memory[c] = max(self.working_memory.get(c, 0), 0.5)
        if focus in self.working_memory:
            self.working_memory[focus] = min(1.0, self.working_memory[focus] + 0.2)
        # Keep top 7
        if len(self.working_memory) > 7:
            items = sorted(self.working_memory.items(), key=lambda x: x[1], reverse=True)
            self.working_memory = dict(items[:7])
        return {"count": len(self.working_memory)}

    def _adjust_threshold(
        self,
        load: float,
        reasoning: Dict[str, Any],
        action: Dict[str, Any],
    ) -> Dict[str, Any]:
        base = 0.7
        load_adj = 0.2 * (load - 0.5)
        conf = float(reasoning.get("confidence_score", 0.5))
        conf_adj = -0.1 * conf
        arousal = self.emotional_state.get("arousal", 0.5)
        emotion_adj = 0.1 if arousal > 0.7 else 0.0
        new = max(0.4, min(0.9, base + load_adj + conf_adj + emotion_adj))
        return {"new_threshold": new, "adjustments": {"load": load_adj, "conf": conf_adj, "emotion": emotion_adj}}

    def _refine_action(
        self,
        chunk: CognitiveChunk,
        action: Dict[str, Any],
        threshold: float,
    ) -> Dict[str, Any]:
        selected = action.get("selected_action", "")
        conf = float(action.get("action_confidence", 0.5))
        refinement: Dict[str, Any] = {"original": selected, "refined": selected}
        if conf < threshold and selected == "answer_query":
            refinement["refined"] = "provide_partial_answer"
            action["selected_action"] = "provide_partial_answer"
            chunk.update_section("action_selection_section", action)
        if self.cognitive_load > 0.8 and selected == "answer_query":
            refinement["refined"] = "provide_partial_answer"
            action["selected_action"] = "provide_partial_answer"
            chunk.update_section("action_selection_section", action)
        return refinement

    def _update_emotion(self, action: Dict[str, Any], load: float) -> Dict[str, Any]:
        selected = action.get("selected_action", "")
        valence_target = 0.5
        arousal_target = 0.5
        if selected == "defer_decision":
            arousal_target += 0.15
        if load > 0.7:
            arousal_target += 0.1
            valence_target -= 0.1
        self.emotional_state["valence"] = 0.8 * self.emotional_state["valence"] + 0.2 * valence_target
        self.emotional_state["arousal"] = 0.8 * self.emotional_state["arousal"] + 0.2 * arousal_target
        return dict(self.emotional_state)
