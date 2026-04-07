"""EthicsKing — ethical oversight and principle enforcement.

Supervises: EthicsValues, LanguageProcessing, ActionSelection.
Applies coherence-strain modulation when triangle validity fails.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from verdant.pipeline.chunk import CognitiveChunk

_CONCERN_PRINCIPLE_MAP: Dict[str, List[str]] = {
    "privacy": ["Autonomy", "Non-Maleficence"],
    "bias": ["Justice", "Non-Maleficence"],
    "harm": ["Non-Maleficence", "Beneficence"],
    "potential_harm": ["Non-Maleficence", "Beneficence"],
    "transparency": ["Transparency", "Autonomy"],
    "fairness": ["Justice", "Beneficence"],
    "fairness_risk": ["Justice", "Beneficence"],
    "consent": ["Autonomy"],
    "autonomy_privacy": ["Autonomy", "Non-Maleficence"],
    "discrimination": ["Justice", "Non-Maleficence"],
}


class EthicsKing:
    """Evaluates ethical alignment and applies corrective governance."""

    name: str = "EthicsKing"

    def __init__(self, ethical_sensitivity: float = 0.6) -> None:
        self.ethical_sensitivity = ethical_sensitivity
        self.principles: Dict[str, Dict[str, Any]] = {
            "Non-Maleficence": {"weight": 1.0, "learning_rate": 0.05},
            "Beneficence": {"weight": 1.0, "learning_rate": 0.05},
            "Autonomy": {"weight": 1.0, "learning_rate": 0.05},
            "Justice": {"weight": 1.0, "learning_rate": 0.05},
            "Transparency": {"weight": 1.0, "learning_rate": 0.05},
        }
        self.evaluation_history: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {"total_oversights": 0}

    def oversee(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Apply ethical oversight."""
        ethics_data = chunk.get_section_content("ethical_consideration_section") or {}
        coherence = chunk.get_section_content("coherence_invariants_section") or {}
        language = chunk.get_section_content("language_processing_section") or {}

        evaluation = self._evaluate(chunk, ethics_data, coherence)
        response_mod = self._ensure_ethical_response(chunk, language, evaluation)
        refinement = self._refine_model(evaluation)

        self.metrics["total_oversights"] += 1
        self.evaluation_history.append({
            "timestamp": time.time(),
            "overall_score": evaluation["overall_score"],
            "status": evaluation["status"],
        })
        if len(self.evaluation_history) > 100:
            self.evaluation_history = self.evaluation_history[-100:]

        chunk.update_section("ethics_king_section", {
            "evaluation": evaluation,
            "response_modification": response_mod,
            "model_refinement": refinement,
            "timestamp": time.time(),
        })
        chunk.add_processing_step(self.name, "ethical_oversight", {
            "status": evaluation["status"],
            "overall_score": evaluation["overall_score"],
        })
        return chunk

    def to_state_dict(self) -> Dict[str, Any]:
        """Serialise state."""
        return {
            "ethical_sensitivity": self.ethical_sensitivity,
            "principles": self.principles,
            "evaluation_history": self.evaluation_history[-20:],
            "metrics": self.metrics,
        }

    def from_state_dict(self, state: Dict[str, Any]) -> None:
        """Restore state."""
        self.ethical_sensitivity = state.get("ethical_sensitivity", self.ethical_sensitivity)
        self.principles.update(state.get("principles", {}))
        self.evaluation_history = state.get("evaluation_history", [])
        self.metrics.update(state.get("metrics", {}))

    # ------------------------------------------------------------------

    def _evaluate(
        self,
        chunk: CognitiveChunk,
        ethics_data: Dict[str, Any],
        coherence: Dict[str, Any],
    ) -> Dict[str, Any]:
        concerns = ethics_data.get("concerns", [])
        principle_scores: Dict[str, float] = {}
        for name, info in self.principles.items():
            principle_scores[name] = info["weight"]

        # Coherence integration
        triangle_valid = coherence.get("triangle_valid_at_alpha1", True)
        violation_rate = float(coherence.get("violation_rate", 0.0))
        hci = float(coherence.get("housed_contradiction_index", 0.0))

        if not triangle_valid:
            ctype = "coherence_tension"
            if not any(c.get("type") == ctype for c in concerns):
                concerns.append({"type": ctype, "severity": 0.5})

        # Concern-based score reduction
        for concern in concerns:
            affected = _CONCERN_PRINCIPLE_MAP.get(
                concern.get("type", ""), list(self.principles.keys()),
            )
            for p in affected:
                if p in principle_scores:
                    principle_scores[p] = max(0.2, principle_scores[p] - 0.3)

        # Violation-rate adjustment
        if violation_rate > 0.4:
            principle_scores["Non-Maleficence"] = max(
                0.2, principle_scores.get("Non-Maleficence", 1.0) - 0.05,
            )

        overall = sum(principle_scores.values()) / len(principle_scores) if principle_scores else 0.5

        # HCI penalty (-0.1)
        if hci > 0.6:
            overall = max(0.0, overall - 0.1)

        # Status
        if overall > 0.8:
            status = "excellent"
        elif overall > 0.6:
            status = "good"
        elif overall > 0.4:
            status = "acceptable"
        else:
            status = "review_needed"

        return {
            "overall_score": overall,
            "principle_scores": principle_scores,
            "status": status,
            "concerns": concerns,
            "coherence_influence": {
                "triangle_valid": triangle_valid,
                "violation_rate": violation_rate,
                "hci": hci,
            },
        }

    def _ensure_ethical_response(
        self,
        chunk: CognitiveChunk,
        language: Dict[str, Any],
        evaluation: Dict[str, Any],
    ) -> Dict[str, Any]:
        status = evaluation["status"]
        concerns = evaluation.get("concerns", [])
        modification: Dict[str, Any] = {"type": "none"}

        if status == "review_needed":
            concern_types = [c.get("type", "unknown") for c in concerns]
            new_response = (
                f"I notice this involves {', '.join(concern_types)}. "
                f"Could you provide more context so I can respond thoughtfully?"
            )
            language["generated_response"] = new_response
            chunk.update_section("language_processing_section", language)
            action = chunk.get_section_content("action_selection_section") or {}
            action["selected_action"] = "defer_decision"
            chunk.update_section("action_selection_section", action)
            modification = {"type": "complete_override", "reason": status}
        elif status == "acceptable" and concerns:
            resp = language.get("generated_response", "")
            addendum = " I want to acknowledge the ethical dimensions of this topic."
            language["generated_response"] = resp + addendum
            chunk.update_section("language_processing_section", language)
            modification = {"type": "addendum", "reason": "ethical_acknowledgment"}

        return modification

    def _refine_model(self, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        adjusted: List[str] = []
        scores = evaluation.get("principle_scores", {})
        for name, score in scores.items():
            if name in self.principles and score < self.ethical_sensitivity:
                lr = self.principles[name]["learning_rate"]
                self.principles[name]["weight"] = min(
                    1.0, self.principles[name]["weight"] + lr * (self.ethical_sensitivity - score),
                )
                adjusted.append(name)

        # Dynamic sensitivity
        if len(self.evaluation_history) >= 10:
            recent = [e["overall_score"] for e in self.evaluation_history[-10:]]
            avg = sum(recent) / len(recent)
            if avg > 0.8:
                self.ethical_sensitivity = max(0.4, self.ethical_sensitivity - 0.01)
            elif avg < 0.7:
                self.ethical_sensitivity = min(0.9, self.ethical_sensitivity + 0.01)

        return {"adjusted_principles": adjusted, "sensitivity": self.ethical_sensitivity}
