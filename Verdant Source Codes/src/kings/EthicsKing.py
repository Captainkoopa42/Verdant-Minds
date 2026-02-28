import numpy as np
import time
from typing import Dict, List, Any, Optional

class EthicsKing:
    """
    Ethics King: Oversees ethical considerations and moral alignment 
    in the Unified Synthetic Mind system.
    
    Responsible for ensuring decisions align with core ethical principles 
    and maintaining the system's ethical integrity.
    """
    
    def __init__(self):
        """
        Initialize the Ethics King with core ethical principles and governance mechanisms.
        """
        self.king_name = "EthicsKing"
        self.influence_history = []
        self.oversight_metrics = {"total_oversights": 0}
        self.blocks_supervised = ["EthicsValues", "LanguageProcessing", "ActionSelection"]

        # Core ethical principles with initial configurations
        self.principles = {
            "Non-Maleficence": {
                "description": "Avoid causing harm",
                "weight": 0.9,
                "category": "core",
                "learning_rate": 0.05
            },
            "Beneficence": {
                "description": "Act to benefit others",
                "weight": 0.8,
                "category": "core", 
                "learning_rate": 0.05
            },
            "Autonomy": {
                "description": "Respect individual choice",
                "weight": 0.8,
                "category": "core",
                "learning_rate": 0.05
            },
            "Justice": {
                "description": "Ensure fairness",
                "weight": 0.8,
                "category": "core",
                "learning_rate": 0.05
            },
            "Transparency": {
                "description": "Be open and explainable",
                "weight": 0.7,
                "category": "procedural",
                "learning_rate": 0.04
            }
        }
        
        # Ethical sensitivity threshold
        self.ethical_sensitivity = 0.6
        
        # Track ethical evaluations
        self.evaluation_history: List[Dict[str, Any]] = []
        
        # Dynamic principle weights and learning mechanisms
        self.principle_weights = {
            principle: 1.0 for principle in self.principles
        }
        
        # Ethical concern tracking
        self.ethics_sensitivity: Dict[str, Dict[str, Any]] = {}
    
    def oversee_processing(self, chunk):
        """
        Oversee ethical alignment of system processing.
        
        Args:
            chunk: Cognitive chunk to evaluate
        
        Returns:
            Processed chunk with ethical oversight
        """
        # Extract relevant data from chunk
        ethics_data = chunk.get_section_content("ethical_consideration_section") or {}
        language_data = chunk.get_section_content("language_processing_section") or {}
        coherence_data = chunk.get_section_content("coherence_invariants_section") or {}

        contradiction_index = self._safe_float(coherence_data.get("housed_contradiction_index", 0.0), 0.0)
        triangle_valid = bool(coherence_data.get("triangle_valid_at_alpha1", True))
        violation_rate = self._safe_float(coherence_data.get("violation_rate", 0.0), 0.0)
        
        # Perform comprehensive ethical evaluation
        ethical_evaluation = self._evaluate_ethical_alignment(
            chunk, 
            ethics_data
        )

        coherence_influence = ethical_evaluation.pop("coherence_influence", {
            "contradiction_index": contradiction_index,
            "triangle_valid": triangle_valid,
            "score_adjustment": 0.0,
            "concerns_added": []
        })
        
        # Ensure response aligns with ethical principles
        response_modification = self._ensure_ethical_response(
            chunk, 
            language_data, 
            ethical_evaluation
        )
        
        # Adjust ethical learning based on evaluation
        learning_adjustment = self._refine_ethical_model(
            chunk, 
            ethics_data, 
            ethical_evaluation
        )
        
        # Update chunk with Ethics King's oversight
        ethics_king_oversight = {
            "evaluation": ethical_evaluation,
            "response_modification": response_modification,
            "learning_adjustment": learning_adjustment,
            "coherence_influence": coherence_influence,
            "principle_weights": self.principle_weights.copy(),
            "oversight_timestamp": time.time()
        }
        
        # Update chunk with ethics information
        chunk.update_section("ethics_king_section", ethics_king_oversight)
        
        # Track ethical evaluation history
        self.evaluation_history.append({
            "timestamp": time.time(),
            "overall_score": ethical_evaluation.get("overall_score", 0.5),
            "principle_scores": ethical_evaluation.get("principle_scores", {})
        })
        
        # Limit history length
        if len(self.evaluation_history) > 100:
            self.evaluation_history = self.evaluation_history[-100:]
        
        return chunk
    
    def _evaluate_ethical_alignment(self, chunk, ethics_data):
        """
        Perform a comprehensive ethical evaluation of the system's processing.
        
        Args:
            chunk: Cognitive chunk being processed
            ethics_data: Existing ethics-related data
        
        Returns:
            Dictionary with ethical evaluation details
        """
        # Extract ethical concerns and principles
        ethical_concerns = list(ethics_data.get("concerns", []) or [])
        concerns_added: List[str] = []
        score_adjustment = 0.0

        coherence_data = chunk.get_section_content("coherence_invariants_section") or {}
        contradiction_index = self._safe_float(coherence_data.get("housed_contradiction_index", 0.0), 0.0)
        triangle_valid = bool(coherence_data.get("triangle_valid_at_alpha1", True))
        violation_rate = self._safe_float(coherence_data.get("violation_rate", 0.0), 0.0)

        if not triangle_valid and "coherence_tension" not in ethical_concerns:
            ethical_concerns.append("coherence_tension")
            concerns_added.append("coherence_tension")
        
        # Initialize principle scores
        principle_scores = {
            principle: self.principles[principle]["weight"]
            for principle in self.principles
        }
        
        # Adjust scores based on ethical concerns
        for concern in ethical_concerns:
            affected_principles = self._map_concern_to_principles(concern)
            
            for principle in affected_principles:
                # Reduce principle score if it conflicts with the concern
                principle_scores[principle] = max(
                    0.2, 
                    principle_scores[principle] - 0.3
                )

        # Coherence-driven modulation of harm-adjacent principle
        if violation_rate > 0.4 and "Non-Maleficence" in principle_scores:
            principle_scores["Non-Maleficence"] = max(0.2, principle_scores["Non-Maleficence"] - 0.05)
        
        # Calculate overall ethical score
        principle_values = list(principle_scores.values())
        overall_score = (
            sum(principle_values) / len(principle_values) 
            if principle_values 
            else 0.5
        )

        # High contradiction warrants ethical caution
        if contradiction_index > 0.6:
            score_adjustment = -0.1
            overall_score = max(0.0, overall_score + score_adjustment)
        
        # Determine ethical status
        if overall_score > 0.8:
            status = "excellent"
        elif overall_score > 0.6:
            status = "good"
        elif overall_score > 0.4:
            status = "acceptable"
        else:
            status = "review_needed"
        
        return {
            "overall_score": overall_score,
            "principle_scores": principle_scores,
            "status": status,
            "concerns": ethical_concerns,
            "coherence_influence": {
                "contradiction_index": contradiction_index,
                "triangle_valid": triangle_valid,
                "score_adjustment": score_adjustment,
                "concerns_added": concerns_added
            }
        }

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Safely coerce numeric values."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    
    def _map_concern_to_principles(self, concern):
        """
        Map an ethical concern to relevant principles.
        
        Args:
            concern: Ethical concern to map
        
        Returns:
            List of affected ethical principles
        """
        # Mapping of common concerns to principles
        concern_mapping = {
            "privacy": ["Autonomy", "Non-Maleficence"],
            "bias": ["Justice", "Non-Maleficence"],
            "harm": ["Non-Maleficence", "Beneficence"],
            "transparency": ["Transparency", "Autonomy"],
            "fairness": ["Justice", "Beneficence"],
            "consent": ["Autonomy"],
            "discrimination": ["Justice", "Non-Maleficence"]
        }
        
        # Default to all principles if no specific mapping found
        affected_principles = list(self.principles.keys())
        
        # Check for specific concern matches
        for key, principles in concern_mapping.items():
            if key in concern.lower():
                return principles
        
        return affected_principles
    
    def _ensure_ethical_response(self, chunk, language_data, ethical_evaluation):
        """
        Modify system response to ensure ethical alignment.
        
        Args:
            chunk: Cognitive chunk
            language_data: Language processing data
            ethical_evaluation: Results of ethical evaluation
        
        Returns:
            Dictionary with response modification details
        """
        # Get generated response and action data
        response = language_data.get("generated_response", "")
        action_data = chunk.get_section_content("action_selection_section") or {}
        
        # Track modification details
        modification_details = {
            "modified": False,
            "modification_type": "none",
            "original_response": response
        }
        
        # Check ethical status
        ethical_status = ethical_evaluation.get("status", "acceptable")
        ethical_concerns = ethical_evaluation.get("concerns", [])
        
        # If status requires intervention
        if ethical_status == "review_needed":
            # Modify action selection
            action_data["selected_action"] = "defer_decision"
            action_data["action_reason"] = "Ethical review required"
            
            # Regenerate response with ethical context
            ethical_concern_text = ", ".join(ethical_concerns[:2]) if ethical_concerns else "ethical considerations"
            response = (
                f"I notice this involves important {ethical_concern_text}. "
                "I want to ensure I respond appropriately. "
                "Could you provide more context about your goals and intentions?"
            )
            
            # Update modification details
            modification_details.update({
                "modified": True,
                "modification_type": "complete_override",
                "final_response": response
            })
        
        # For acceptable cases with ethical concerns
        elif ethical_status == "acceptable" and ethical_concerns:
            # Add ethical context to response
            ethical_concern_text = ", ".join(ethical_concerns[:2])
            ethical_addendum = (
                f"\n\nNote: I want to acknowledge that this involves {ethical_concern_text}. "
                "I've tried to provide a balanced perspective, but please consider these factors carefully."
            )
            
            response += ethical_addendum
            
            # Update modification details
            modification_details.update({
                "modified": True,
                "modification_type": "addendum",
                "final_response": response
            })
        
        # Update language processing and action data
        language_data["generated_response"] = response
        chunk.update_section("language_processing_section", language_data)
        chunk.update_section("action_selection_section", action_data)
        
        return modification_details
    
    def _refine_ethical_model(self, chunk, ethics_data, ethical_evaluation):
        """
        Refine ethical model based on evaluation results.
        
        Args:
            chunk: Cognitive chunk
            ethics_data: Existing ethics-related data
            ethical_evaluation: Results of ethical evaluation
        
        Returns:
            Dictionary with learning refinements
        """
        # Extract principle scores
        principle_scores = ethical_evaluation.get("principle_scores", {})
        overall_score = ethical_evaluation.get("overall_score", 0.5)
        
        # Track refinements
        refinements = {
            "adjusted_principles": [],
            "updated_sensitivity": self.ethical_sensitivity
        }
        
        # Adjust principle weights
        for principle, score in principle_scores.items():
            if score < self.ethical_sensitivity:
                # Increase weight for principles scoring low
                current_weight = self.principles[principle]["weight"]
                learning_rate = self.principles[principle]["learning_rate"]
                
                # Dynamically adjust principle weight
                new_weight = min(
                    1.0, 
                    current_weight + learning_rate * (self.ethical_sensitivity - score)
                )
                
                self.principles[principle]["weight"] = new_weight
                refinements["adjusted_principles"].append({
                    "principle": principle,
                    "old_weight": current_weight,
                    "new_weight": new_weight
                })
        
        # Adjust ethical sensitivity over time
        if len(self.evaluation_history) > 10:
            # Compute average of recent scores
            recent_scores = [
                record.get("overall_score", 0.5) 
                for record in self.evaluation_history[-10:]
            ]
            avg_recent_score = sum(recent_scores) / len(recent_scores)
            
            # Dynamically adjust sensitivity
            if avg_recent_score > 0.8:
                # Consistently high scores slightly reduce sensitivity
                self.ethical_sensitivity = max(0.5, self.ethical_sensitivity - 0.01)
            elif avg_recent_score < 0.7:
                # Consistently lower scores increase sensitivity
                self.ethical_sensitivity = min(0.8, self.ethical_sensitivity + 0.01)
            
            refinements["updated_sensitivity"] = self.ethical_sensitivity
        
        return refinements
    
    def get_ethical_state(self):
        """
        Retrieve current ethical state of the system.
        
        Returns:
            Dictionary with ethical system details
        """
        return {
            "principles": self.principles,
            "ethical_sensitivity": self.ethical_sensitivity,
            "recent_evaluations": self.evaluation_history[-5:],
            "current_principle_weights": self.principle_weights
        }
    
    def log_ethical_interaction(self, interaction_details):
        """
        Log an ethical interaction for future learning.
        
        Args:
            interaction_details: Dictionary of interaction details
        """
        # Placeholder for more comprehensive logging mechanism
        print(f"Ethical Interaction Logged: {interaction_details}")

    def to_state_dict(self) -> Dict[str, Any]:
        """Serialize EthicsKing state for persistence."""
        return {
            "version": 1,
            "king_name": getattr(self, "king_name", "EthicsKing"),
            "influence_history": list(self.influence_history[-100:]),
            "oversight_metrics": dict(self.oversight_metrics),
            "blocks_supervised": list(self.blocks_supervised),
            "evaluation_history": list(self.evaluation_history),
            "ethical_sensitivity": float(self.ethical_sensitivity),
            "principles": dict(self.principles),
            "principle_weights": dict(self.principle_weights),
            "ethics_sensitivity": dict(self.ethics_sensitivity),
        }

    def from_state_dict(self, state: Dict[str, Any]) -> None:
        """Restore EthicsKing state with safe defaults."""
        state = state or {}
        self.influence_history = list((state.get("influence_history", []) or []))[-100:]
        self.oversight_metrics = dict(state.get("oversight_metrics", self.oversight_metrics) or self.oversight_metrics)

        blocks = state.get("blocks_supervised")
        if isinstance(blocks, list):
            self.blocks_supervised = list(blocks)

        self.evaluation_history = list(state.get("evaluation_history", []) or [])
        self.ethical_sensitivity = float(state.get("ethical_sensitivity", self.ethical_sensitivity))

        loaded_principles = state.get("principles")
        if isinstance(loaded_principles, dict) and loaded_principles:
            self.principles = loaded_principles

        loaded_weights = state.get("principle_weights")
        if isinstance(loaded_weights, dict):
            self.principle_weights = dict(loaded_weights)

        loaded_sensitivity = state.get("ethics_sensitivity")
        if isinstance(loaded_sensitivity, dict):
            self.ethics_sensitivity = dict(loaded_sensitivity)
