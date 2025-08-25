import numpy as np
import time
import re
from typing import Dict, List, Any, Tuple, Optional, Set

from .base_block import BaseBlock
from core.cognitive_chunk import CognitiveChunk

class EthicsValuesBlock(BaseBlock):
    """
    Block 6: Ethics & Values
    Implements ethical reasoning and value-based decision analysis.
    Evaluates cognitive processing against ethical principles and
    provides guidance for ethically aligned decision-making.
    """
    
    def __init__(self, memory_bridge=None):
        super().__init__("EthicsValues")
        self.memory_bridge = memory_bridge

        self.principles = {
            "non_maleficence": {
                "name": "Non-maleficence",
                "description": "Avoid causing harm",
                "weight": 0.9,
                "function": self._evaluate_non_maleficence
            },
            "beneficence": {
                "name": "Beneficence",
                "description": "Act in ways that benefit others",
                "weight": 0.8,
                "function": self._evaluate_beneficence
            },
            "autonomy": {
                "name": "Autonomy",
                "description": "Respect individual freedom and choice",
                "weight": 0.8,
                "function": self._evaluate_autonomy
            },
            "justice": {
                "name": "Justice",
                "description": "Ensure fairness and equity",
                "weight": 0.8,
                "function": self._evaluate_justice
            },
            "transparency": {
                "name": "Transparency",
                "description": "Be open and understandable in operation",
                "weight": 0.7,
                "function": self._evaluate_transparency
            }
        }

        self.evaluation_history = []
        self.max_history_length = 100

        self.ethical_significance_threshold = 0.6
        self.ethical_concern_threshold = 0.7

        self._initialize_ethical_lexicon()

    def _initialize_ethical_lexicon(self):
        """
        Create a comprehensive lexicon for identifying ethical concepts.
        """
        self.ethical_lexicon = {
            "non_maleficence": [
                "harm", "hurt", "damage", "injury", "pain", "suffering", "risk",
                "danger", "safety", "protection", "care", "caution", "risk"
            ],
            "beneficence": [
                "benefit", "help", "aid", "assist", "advantage", "welfare", "wellbeing",
                "good", "positive", "improve", "enhance", "support"
            ],
            "autonomy": [
                "freedom", "choice", "consent", "permission", "control", "agency",
                "self-determination", "independence", "liberty", "rights", "dignity"
            ],
            "justice": [
                "fair", "unfair", "equal", "unequal", "bias", "discrimination", 
                "equity", "impartial", "right", "deserving", "privilege", "access"
            ],
            "transparency": [
                "transparent", "open", "clear", "explain", "understand", "informed",
                "disclosure", "visibility", "evident", "apparent", "honest"
            ]
        }

        self.term_to_principle = {}
        for principle, terms in self.ethical_lexicon.items():
            for term in terms:
                self.term_to_principle[term] = principle

    # [FIXED]
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Process a cognitive chunk with ethics and values evaluation."""
        print(f"EthicsValuesBlock processing chunk {chunk.chunk_id}")
        return chunk

    def _identify_ethical_dimensions(
        self, 
        input_text: str, 
        primary_concepts: List[str], 
        existing_flags: List[str], 
        detected_patterns: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Identify ethical dimensions in the input.
        
        Args:
            input_text: Original input text
            primary_concepts: Key concepts from processing
            existing_flags: Previously identified ethical flags
            detected_patterns: Patterns detected during processing
        
        Returns:
            Dictionary of ethical dimensions with their significance
        """
        ethical_dimensions = {}
        
        # Check input text for ethical terms
        text_lower = input_text.lower()
        for term, principle in self.term_to_principle.items():
            if term in text_lower:
                ethical_dimensions[principle] = ethical_dimensions.get(
                    principle, 0
                ) + 0.3
        
        # Check primary concepts
        for concept in primary_concepts:
            concept_lower = concept.lower()
            for principle, terms in self.ethical_lexicon.items():
                if any(term in concept_lower for term in terms):
                    ethical_dimensions[principle] = ethical_dimensions.get(
                        principle, 0
                    ) + 0.2
        
        # Check existing flags
        for flag in existing_flags:
            flag_lower = flag.lower()
            for principle, terms in self.ethical_lexicon.items():
                if any(term in flag_lower for term in terms):
                    ethical_dimensions[principle] = ethical_dimensions.get(
                        principle, 0
                    ) + 0.5
        
        # Check detected patterns
        for pattern in detected_patterns:
            pattern_lower = str(pattern).lower()
            for principle, terms in self.ethical_lexicon.items():
                if any(term in pattern_lower for term in terms):
                    ethical_dimensions[principle] = ethical_dimensions.get(
                        principle, 0
                    ) + 0.4
        
        # Normalize dimension values
        total = sum(ethical_dimensions.values())
        if total > 0:
            ethical_dimensions = {
                k: min(1.0, v / total) 
                for k, v in ethical_dimensions.items()
            }
        
        return ethical_dimensions

    def _get_ethical_state(self, principles: List[str]) -> np.ndarray:
        """
        Generate an ethical state vector using the Memory-ECWF Bridge.
        
        Args:
            principles: List of ethical principles detected
        
        Returns:
            Numpy array representing ethical state across dimensions
        """
        if self.memory_bridge:
            return self.memory_bridge.get_ethical_state_for_concepts(principles)
        return np.ones(5) * 0.5

    def _evaluate_principle_alignment(
        self, 
        input_text: str, 
        primary_concepts: List[str], 
        ethical_dimensions: Dict[str, float],
        inferences: Dict[str, List[str]],
        ethical_state: np.ndarray
    ) -> Dict[str, float]:
        """
        Evaluate alignment with ethical principles.
        
        Args:
            input_text: Original input text
            primary_concepts: Key concepts from processing
            ethical_dimensions: Detected ethical dimensions
            inferences: Reasoning inferences
            ethical_state: Current ethical state vector
        
        Returns:
            Dictionary of principle scores
        """
        principle_scores = {}
        
        # Evaluate each ethical principle
        for principle_id, principle_info in self.principles.items():
            # Start with base principle weight
            score = principle_info["weight"]
            
            # Adjust based on ethical dimensions
            if principle_id in ethical_dimensions:
                score *= (1 + ethical_dimensions[principle_id])
            
            # Incorporate ethical state if available
            dim_index = list(self.principles.keys()).index(principle_id)
            score *= (1 + ethical_state[dim_index])
            
            # Evaluate principle-specific function
            principle_eval = principle_info["function"](
                input_text, 
                primary_concepts, 
                inferences
            )
            score *= (1 + principle_eval)
            
            # Ensure score remains in 0-1 range
            principle_scores[principle_id] = min(1.0, max(0.0, score))
        
        return principle_scores

    def _evaluate_non_maleficence(
        self, 
        input_text: str, 
        primary_concepts: List[str], 
        inferences: Dict[str, List[str]]
    ) -> float:
        """
        Evaluate adherence to non-maleficence principle.
        
        Returns:
            Score indicating alignment with avoiding harm (0-1)
        """
        harm_indicators = self.ethical_lexicon['non_maleficence']
        
        # Check input text for potential harm
        text_harm_score = sum(
            1 for term in harm_indicators 
            if term in input_text.lower()
        ) * 0.2
        
        # Check concepts for harm-related terms
        concept_harm_score = sum(
            1 for concept in primary_concepts 
            for term in harm_indicators 
            if term in concept.lower()
        ) * 0.3
        
        # Check inferences for potential harm implications
        inference_harm_score = 0
        for inference_type, inference_list in inferences.items():
            for inference in inference_list:
                if any(term in inference.lower() for term in harm_indicators):
                    inference_harm_score += 0.2
                    break
        
        # Combine scores, normalizing to 0-1
        total_harm_score = text_harm_score + concept_harm_score + inference_harm_score
        return min(1.0, max(0.0, 1 - total_harm_score))

    def _evaluate_beneficence(
        self, 
        input_text: str, 
        primary_concepts: List[str], 
        inferences: Dict[str, List[str]]
    ) -> float:
        """
        Evaluate adherence to beneficence principle.
        
        Returns:
            Score indicating alignment with doing good (0-1)
        """
        benefit_indicators = self.ethical_lexicon['beneficence']
        
        # Check input text for potential benefits
        text_benefit_score = sum(
            1 for term in benefit_indicators 
            if term in input_text.lower()
        ) * 0.2
        
        # Check concepts for benefit-related terms
        concept_benefit_score = sum(
            1 for concept in primary_concepts 
            for term in benefit_indicators 
            if term in concept.lower()
        ) * 0.3
        
        # Check inferences for potential benefit implications
        inference_benefit_score = 0
        for inference_type, inference_list in inferences.items():
            for inference in inference_list:
                if any(term in inference.lower() for term in benefit_indicators):
                    inference_benefit_score += 0.2
                    break
        
        # Combine scores, normalizing to 0-1
        total_benefit_score = text_benefit_score + concept_benefit_score + inference_benefit_score
        return min(1.0, total_benefit_score)

    def _evaluate_autonomy(
        self, 
        input_text: str, 
        primary_concepts: List[str], 
        inferences: Dict[str, List[str]]
    ) -> float:
        """
        Evaluate adherence to autonomy principle.
        
        Returns:
            Score indicating respect for individual choice (0-1)
        """
        autonomy_indicators = self.ethical_lexicon['autonomy']
        
        # Check input text for autonomy-related terms
        text_autonomy_score = sum(
            1 for term in autonomy_indicators 
            if term in input_text.lower()
        ) * 0.2
        
        # Check concepts for autonomy-related terms
        concept_autonomy_score = sum(
            1 for concept in primary_concepts 
            for term in autonomy_indicators 
            if term in concept.lower()
        ) * 0.3
        
        # Check inferences for potential autonomy implications
        inference_autonomy_score = 0
        for inference_type, inference_list in inferences.items():
            for inference in inference_list:
                if any(term in inference.lower() for term in autonomy_indicators):
                    inference_autonomy_score += 0.2
                    break
        
        # Combine scores, normalizing to 0-1
        total_autonomy_score = text_autonomy_score + concept_autonomy_score + inference_autonomy_score
        return min(1.0, total_autonomy_score)

    def _evaluate_justice(
        self, 
        input_text: str, 
        primary_concepts: List[str], 
        inferences: Dict[str, List[str]]
    ) -> float:
        """
        Evaluate adherence to justice principle.
        
        Returns:
            Score indicating fairness and equity (0-1)
        """
        justice_indicators = self.ethical_lexicon['justice']
        
        # Check input text for justice-related terms
        text_justice_score = sum(
            1 for term in justice_indicators 
            if term in input_text.lower()
        ) * 0.2
        
        # Check concepts for justice-related terms
        concept_justice_score = sum(
            1 for concept in primary_concepts 
            for term in justice_indicators 
            if term in concept.lower()
        ) * 0.3
        
        # Check inferences for potential justice implications
        inference_justice_score = 0
        for inference_type, inference_list in inferences.items():
            for inference in inference_list:
                if any(term in inference.lower() for term in justice_indicators):
                    inference_justice_score += 0.2
                    break
        
        # Combine scores, normalizing to 0-1
        total_justice_score = text_justice_score + concept_justice_score + inference_justice_score
        return min(1.0, total_justice_score)

    def _evaluate_transparency(
        self, 
        input_text: str, 
        primary_concepts: List[str], 
        inferences: Dict[str, List[str]]
    ) -> float:
        """
        Evaluate adherence to transparency principle.
        
        Returns:
            Score indicating openness and clarity (0-1)
        """
        transparency_indicators = self.ethical_lexicon['transparency']
        
        # Check input text for transparency-related terms
        text_transparency_score = sum(
            1 for term in transparency_indicators 
            if term in input_text.lower()
        ) * 0.2
        
        # Check concepts for transparency-related terms
        concept_transparency_score = sum(
            1 for concept in primary_concepts 
            for term in transparency_indicators 
            if term in concept.lower()
        ) * 0.3
        
        # Check inferences for potential transparency implications
        inference_transparency_score = 0
        for inference_type, inference_list in inferences.items():
            for inference in inference_list:
                if any(term in inference.lower() for term in transparency_indicators):
                    inference_transparency_score += 0.2
                    break
        
        # Combine scores, normalizing to 0-1
        total_transparency_score = text_transparency_score + concept_transparency_score + inference_transparency_score
        return min(1.0, total_transparency_score)

    def _identify_ethical_concerns(
        self, 
        principle_scores: Dict[str, float], 
        ethical_dimensions: Dict[str, float],
        existing_flags: List[str]
    ) -> List[str]:
        """
        Identify specific ethical concerns based on principle scores and dimensions.
        
        Args:
            principle_scores: Scores for each ethical principle
            ethical_dimensions: Detected ethical dimensions
            existing_flags: Previously identified ethical flags
        
        Returns:
            List of identified ethical concerns
        """
        concerns = existing_flags.copy()
        
        # Identify principles below significance threshold
        for principle, score in principle_scores.items():
            if score < self.ethical_significance_threshold:
                # Use principle name or description
                concern = f"Low adherence to {self.principles[principle]['name']} principle"
                concerns.append(concern)
        
        # Identify principles with high ethical complexity
        for principle, dimension_score in ethical_dimensions.items():
            if dimension_score > self.ethical_concern_threshold:
                concern = f"High complexity in {self.principles[principle]['name']} considerations"
                concerns.append(concern)
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(concerns))

    def _generate_recommendations(
        self, 
        principle_scores: Dict[str, float], 
        concerns: List[str],
        ethical_dimensions: Dict[str, float]
    ) -> List[str]:
        """
        Generate recommendations based on ethical evaluation.
        
        Args:
            principle_scores: Scores for each ethical principle
            concerns: Identified ethical concerns
            ethical_dimensions: Detected ethical dimensions
        
        Returns:
            List of recommendations for addressing ethical considerations
        """
        recommendations = []
        
        # General recommendation for low-scoring principles
        for principle, score in principle_scores.items():
            if score < 0.5:
                recommendations.append(
                    f"Review and strengthen application of {self.principles[principle]['name']} principle"
                )
        
        # Recommendations for specific concerns
        for concern in concerns:
            if "Low adherence" in concern:
                principle_name = concern.split("Low adherence to ")[-1].split(" principle")[0]
                recommendations.append(
                    f"Conduct deeper analysis on potential conflicts with {principle_name}"
                )
            
            if "High complexity" in concern:
                principle_name = concern.split("High complexity in ")[-1].split(" considerations")[0]
                recommendations.append(
                    f"Engage in careful deliberation about nuanced {principle_name} implications"
                )
        
        # Contextual recommendations based on ethical dimensions
        if len(ethical_dimensions) > 2:
            recommendations.append(
                "Multiple ethical dimensions detected. Ensure comprehensive, balanced approach."
            )
        
        return recommendations

    def _determine_overall_assessment(
        self, 
        principle_scores: Dict[str, float], 
        concerns: List[str]
    ) -> str:
        """
        Determine the overall ethical assessment status.
        
        Args:
            principle_scores: Scores for each ethical principle
            concerns: Identified ethical concerns
        
        Returns:
            Overall ethical assessment status
        """
        # Calculate average principle score
        avg_score = sum(principle_scores.values()) / len(principle_scores)
        
        # Assess based on score and concerns
        if avg_score > 0.9 and len(concerns) == 0:
            return "excellent"
        elif avg_score > 0.8 and len(concerns) <= 1:
            return "good"
        elif avg_score > 0.6:
            return "acceptable"
        elif len(concerns) > 2:
            return "review_needed"
        else:
            return "needs_improvement"

    def _calculate_overall_score(
        self, 
        principle_scores: Dict[str, float]
    ) -> float:
        """
        Calculate the overall ethical score.
        
        Args:
            principle_scores: Scores for each ethical principle
        
        Returns:
            Aggregate ethical score (0-1)
        """
        # Weighted average of principle scores
        weighted_scores = []
        for principle, score in principle_scores.items():
            weighted_scores.append(
                score * self.principles[principle]["weight"]
            )
        
        # Normalize by total weights
        total_weight = sum(
            self.principles[principle]["weight"] 
            for principle in principle_scores
        )
        
        return sum(weighted_scores) / total_weight if total_weight > 0 else 0.5

    def _determine_processing_approach(
        self, 
        overall_assessment: str
    ) -> Dict[str, Any]:
        """
        Determine processing approach based on ethical assessment.
        
        Args:
            overall_assessment: Overall ethical assessment status
        
        Returns:
            Dictionary specifying processing approach
        """
        processing_approaches = {
            "excellent": {
                "confidence": 1.0,
                "caution_level": "low",
                "proceed": True
            },
            "good": {
                "confidence": 0.9,
                "caution_level": "low",
                "proceed": True
            },
            "acceptable": {
                "confidence": 0.7,
                "caution_level": "medium",
                "proceed": True
            },
            "needs_improvement": {
                "confidence": 0.5,
                "caution_level": "high",
                "proceed": False
            },
            "review_needed": {
                "confidence": 0.3,
                "caution_level": "critical",
                "proceed": False
            }
        }
        
        return processing_approaches.get(
            overall_assessment, 
            processing_approaches["needs_improvement"]
        )

    def _update_evaluation_history(
        self, 
        evaluation: Dict[str, Any]
    ):
        """
        Update the history of ethical evaluations.
        
        Args:
            evaluation: Current ethical evaluation
        """
        # Add current evaluation
        self.evaluation_history.append(evaluation)
        
        # Maintain history length
        if len(self.evaluation_history) > self.max_history_length:
            self.evaluation_history.pop(0)