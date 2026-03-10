"""ActionSelectionBlock — selects the best action among six types.

ForefrontKing + Three Kings Council oversight hooks in after this block.

Reads: ``internal_communication_section``, ``reasoning_section``,
       ``ethics_king_section``, ``memory_section``,
       ``pattern_recognition_section``, ``forefront_king_section``
Writes: ``action_selection_section``
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from verdant_v2.pipeline.chunk import CognitiveChunk


class ActionBlock:
    """Scores and selects from six action types."""

    name: str = "ActionSelection"

    def __init__(self, decision_threshold: float = 0.7) -> None:
        self.decision_threshold = decision_threshold

    def process(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Score actions and select the best one."""
        comm = chunk.get_section_content("internal_communication_section") or {}
        reasoning = chunk.get_section_content("reasoning_section") or {}
        ethics = chunk.get_section_content("ethics_king_section") or {}
        memory = chunk.get_section_content("memory_section") or {}
        pattern = chunk.get_section_content("pattern_recognition_section") or {}
        forefront = chunk.get_section_content("forefront_king_section") or {}

        concepts = pattern.get("concepts", [])
        avg_conf = float(reasoning.get("confidence_score", 0.5))
        ethical_eval = ethics.get("evaluation", {})
        ethical_status = ethical_eval.get("status", "good")
        ethical_concerns = ethical_eval.get("concerns", [])
        cognitive_load = float(forefront.get("cognitive_load", 0.5))
        threshold = float(forefront.get("decision_threshold", self.decision_threshold))
        activations = memory.get("activated_concepts", {})

        scores = self._compute_scores(
            avg_conf, concepts, ethical_status, ethical_concerns,
            cognitive_load, threshold, activations, reasoning,
        )

        selected = max(scores, key=scores.get)  # type: ignore[arg-type]
        params = self._generate_params(selected, concepts, ethical_concerns, reasoning)

        chunk.update_section("action_selection_section", {
            "selected_action": selected,
            "action_confidence": scores[selected],
            "action_reason": f"Scored highest ({scores[selected]:.2f}) among {len(scores)} options.",
            "action_parameters": params,
            "all_action_scores": scores,
            "processed_timestamp": time.time(),
        })
        chunk.add_processing_step(self.name, "action_selection", {
            "selected": selected,
            "confidence": scores[selected],
        })
        return chunk

    # ------------------------------------------------------------------

    @staticmethod
    def _compute_scores(
        avg_conf: float,
        concepts: List[str],
        ethical_status: str,
        ethical_concerns: list,
        cognitive_load: float,
        threshold: float,
        activations: Dict[str, float],
        reasoning: Dict[str, Any],
    ) -> Dict[str, float]:
        n_concepts = len(concepts)
        ethics_penalty = max(0.6, 1.0 - len(ethical_concerns) * 0.1)
        load_penalty = max(0.7, 1.0 - cognitive_load * 0.3)

        scores: Dict[str, float] = {}

        # answer_query
        if avg_conf > threshold and n_concepts >= 2:
            scores["answer_query"] = min(
                0.95, (avg_conf + 0.1 * min(n_concepts, 5) / 5) * ethics_penalty * load_penalty,
            )
        else:
            scores["answer_query"] = avg_conf * 0.6 * ethics_penalty

        # partial
        scores["provide_partial_answer"] = (
            avg_conf + 0.1 * min(n_concepts, 3) / 3 - cognitive_load * 0.1
        )

        # clarification
        info_gap = max(0.0, 1.0 - n_concepts / 5)
        inductive = len(reasoning.get("inferences", {}).get("inductive", []))
        scores["ask_clarification"] = (
            0.5 + (1 - avg_conf) * 0.3 + info_gap * 0.2 + min(inductive, 2) * 0.05
        )

        # log_memory
        novel = sum(1 for c in concepts if c not in activations)
        scores["log_memory"] = min(0.8, novel * 0.1)

        # defer_decision
        severity = sum(c.get("severity", 0.5) for c in ethical_concerns) if ethical_concerns else 0.0
        status_score = 0.3 if ethical_status == "review_needed" else 0.0
        scores["defer_decision"] = min(0.95, 0.3 + severity + status_score)

        # trigger_system_action
        cmd_kw = {"run", "execute", "start", "stop", "reset", "update"}
        cmd_matches = sum(1 for c in concepts if c.lower() in cmd_kw)
        scores["trigger_system_action"] = 0.3 + 0.1 * cmd_matches

        return scores

    @staticmethod
    def _generate_params(
        action: str,
        concepts: List[str],
        concerns: list,
        reasoning: Dict[str, Any],
    ) -> Dict[str, Any]:
        if action == "ask_clarification":
            questions = []
            if len(concepts) < 3:
                questions.append(f"Could you provide more context about '{concepts[0] if concepts else 'your query'}'?")
            else:
                questions.append("Could you clarify your main intent?")
            return {"clarification_questions": questions}
        if action == "defer_decision":
            return {
                "ethical_flags": [c.get("type", "") for c in concerns],
                "alternatives": ["Rephrase to address concerns", "Provide additional context"],
            }
        return {}
