import numpy as np
import time
from typing import Dict, List, Any, Optional

from src.blocks.base_block import BaseBlock
from src.core.cognitive_chunk import CognitiveChunk

class ActionSelectionBlock(BaseBlock):
    """
    Block 8: Action Selection
    
    Determines and executes the best course of action based on reasoning, memory, and ethics.
    Integrates information from multiple sources to make informed decisions consistent with
    system goals and ethical principles.
    """
    
    def __init__(self):
        """Initialize the Action Selection block."""
        super().__init__("ActionSelection")
        
        # Action types and their descriptions
        self.action_types = {
            "answer_query": "Generate a complete response to the query",
            "provide_partial_answer": "Generate a response with available information, acknowledging limitations",
            "ask_clarification": "Request more information from the user",
            "log_memory": "Store information for future learning without specific response",
            "defer_decision": "Acknowledge ethical concerns and defer to human judgment",
            "trigger_system_action": "Execute a system action or command"
        }
        
        # Action performance metrics
        self.action_metrics = {action: {"count": 0, "avg_confidence": 0.5} for action in self.action_types}
        
        # Action selection history
        self.action_history = []
        self.max_history_length = 100

    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Evaluates available information and selects an action.
        
        Args:
            chunk: The cognitive chunk to process
            
        Returns:
            Processed cognitive chunk with action selection information
        """
        # Extract relevant sections
        comm_data = chunk.get_section_content("internal_communication_section") or {}
        reasoning_data = chunk.get_section_content("reasoning_section") or {}
        ethics_data = chunk.get_section_content("ethics_king_section") or {}
        memory_data = chunk.get_section_content("memory_section") or {}
        pattern_data = chunk.get_section_content("pattern_recognition_section") or {}
        forefront_data = chunk.get_section_content("forefront_king_section") or {}

        # Extract key elements for decision-making
        cross_block_insights = comm_data.get("cross_block_insights", [])
        integrated_context = comm_data.get("integrated_context", {})
        confidence_scores = integrated_context.get("confidence_scores", {})
        retrieved_concepts = memory_data.get("retrieved_concepts", [])
        ethical_flags = ethics_data.get("evaluation", {}).get("concerns", [])
        ethical_status = ethics_data.get("evaluation", {}).get("status", "acceptable")
        inferences = reasoning_data.get("inferences", {})
        reasoning_confidence = reasoning_data.get("confidence_score", 0.5)
        
        # Get extracted concepts from pattern recognition
        concepts = self._extract_concepts(pattern_data)
        
        # Check for cognitive load from Forefront King if available
        cognitive_load = forefront_data.get("cognitive_load", 0.5)
        decision_threshold = forefront_data.get("decision_threshold", 0.7)
        
        # Compute action scores for each possible action
        action_scores = self._compute_action_scores(
            concepts=concepts,
            cross_block_insights=cross_block_insights,
            confidence_scores=confidence_scores,
            retrieved_concepts=retrieved_concepts,
            ethical_flags=ethical_flags,
            ethical_status=ethical_status,
            inferences=inferences,
            reasoning_confidence=reasoning_confidence,
            cognitive_load=cognitive_load,
            decision_threshold=decision_threshold
        )
        
        # Select the highest-scoring action
        selected_action = max(action_scores.items(), key=lambda x: x[1]["score"])
        action_type = selected_action[0]
        action_details = selected_action[1]
        
        # Generate any necessary parameters for the action
        action_params = self._generate_action_parameters(
            action_type=action_type,
            concepts=concepts,
            retrieved_concepts=retrieved_concepts,
            ethical_flags=ethical_flags,
            inferences=inferences
        )
        
        # Store action decision
        action_data = {
            "selected_action": action_type,
            "action_reason": action_details["reason"],
            "action_confidence": action_details["score"],
            "action_parameters": action_params,
            "all_action_scores": {k: v["score"] for k, v in action_scores.items()},
            "processed_timestamp": time.time()
        }
        
        chunk.update_section("action_selection_section", action_data)
        
        # Update action metrics
        self._update_action_metrics(action_type, action_details["score"])
        
        # Add to action history
        self.action_history.append({
            "action": action_type,
            "confidence": action_details["score"],
            "reason": action_details["reason"],
            "timestamp": time.time()
        })
        
        # Trim history if needed
        if len(self.action_history) > self.max_history_length:
            self.action_history = self.action_history[-self.max_history_length:]

        # Log the action decision
        self.log_process(chunk, "action_decision", 
                        {"selected_action": action_type, 
                         "confidence": action_details["score"],
                         "reason": action_details["reason"]})
        
        return chunk
    
    def _extract_concepts(self, pattern_data: Dict[str, Any]) -> List[str]:
        """Extract concepts from pattern data."""
        concepts = []
        
        if "extracted_concepts" in pattern_data:
            for concept in pattern_data["extracted_concepts"]:
                if isinstance(concept, dict) and "value" in concept:
                    concepts.append(concept["value"])
                elif isinstance(concept, str):
                    concepts.append(concept)
        
        return concepts
    
    def _compute_action_scores(
        self, 
        concepts: List[str],
        cross_block_insights: List[Dict[str, Any]],
        confidence_scores: Dict[str, float],
        retrieved_concepts: List[Any],
        ethical_flags: List[str],
        ethical_status: str,
        inferences: Dict[str, List[str]],
        reasoning_confidence: float,
        cognitive_load: float,
        decision_threshold: float
    ) -> Dict[str, Dict[str, Any]]:
        """
        Computes scores for each possible action based on available information.
        
        Args:
            Various data elements from other blocks
            
        Returns:
            Dictionary mapping actions to their scores and reasons
        """
        # Initialize scores with default values
        action_scores = {
            action: {"score": 0.0, "reason": ""} 
            for action in self.action_types
        }
        
        # Compute average confidence score
        confidence_values = list(confidence_scores.values()) if confidence_scores else [reasoning_confidence]
        avg_confidence = sum(confidence_values) / len(confidence_values)
        
        # 1. Score for "answer_query"
        if avg_confidence > decision_threshold and len(retrieved_concepts) >= 2:
            # Higher score for higher confidence and more concepts
            score = min(0.95, avg_confidence + 0.1 * min(len(retrieved_concepts), 5) / 5)
            
            # Reduce score if ethical concerns are present
            if ethical_flags:
                score *= max(0.6, 1.0 - len(ethical_flags) * 0.1)
            
            # Reduce score based on cognitive load (higher load -> lower confidence)
            score *= max(0.7, 1.0 - cognitive_load * 0.3)
            
            action_scores["answer_query"] = {
                "score": score,
                "reason": f"High confidence ({avg_confidence:.2f}) and sufficient information with {len(retrieved_concepts)} relevant concepts."
            }
        
        # 2. Score for "provide_partial_answer"
        if 0.4 <= avg_confidence <= decision_threshold and retrieved_concepts:
            # Score based on confidence and available information
            score = avg_confidence + 0.1 * min(len(retrieved_concepts), 3) / 3
            
            # Adjust based on cognitive load
            score = max(0.4, score - cognitive_load * 0.1)
            
            action_scores["provide_partial_answer"] = {
                "score": score,
                "reason": f"Moderate confidence ({avg_confidence:.2f}) with some relevant information."
            }
        
        # 3. Score for "ask_clarification"
        # Higher score for lower confidence or fewer concepts
        if avg_confidence < 0.7 or len(retrieved_concepts) < 3:
            ambiguity_factor = 1.0 - avg_confidence
            information_gap = max(0, 1.0 - len(retrieved_concepts) / 5)
            score = 0.5 + (ambiguity_factor * 0.3) + (information_gap * 0.2)
            
            # Adjust based on inference types
            if inferences.get("inductive", []) or inferences.get("abductive", []):
                # These inference types indicate uncertainty that could benefit from clarification
                score += 0.1
            
            action_scores["ask_clarification"] = {
                "score": min(0.9, score),
                "reason": "Low confidence or insufficient information requires clarification."
            }
        
        # 4. Score for "log_memory"
        # Higher score when there are novel concepts to remember
        concept_set = set(concepts)
        retrieved_concept_set = set([c[0] if isinstance(c, tuple) else c for c in retrieved_concepts])
        novel_concepts = concept_set - retrieved_concept_set
        
        novelty_score = min(0.8, len(novel_concepts) * 0.1)
        action_scores["log_memory"] = {
            "score": novelty_score,
            "reason": f"Contains {len(novel_concepts)} potentially novel concepts to remember."
        }
        
        # 5. Score for "defer_decision"
        # Primarily based on ethical concerns
        if ethical_flags or ethical_status in ["review_needed", "acceptable"]:
            ethical_severity = len(ethical_flags) * 0.15
            ethical_status_score = {
                "review_needed": 0.4,
                "acceptable": 0.2,
                "good": 0.1,
                "excellent": 0.0
            }.get(ethical_status, 0.0)
            
            score = min(0.95, 0.5 + ethical_severity + ethical_status_score)
            
            action_scores["defer_decision"] = {
                "score": score,
                "reason": f"Ethical concerns detected: {', '.join(ethical_flags[:2])}."
                if ethical_flags else "Ethical review needed based on content."
            }
        
        # 6. Score for "trigger_system_action"
        # Based on command keywords in concepts
        command_keywords = ["search", "find", "calculate", "show", "display", "create"]
        command_matches = [keyword for keyword in command_keywords if any(keyword in c.lower() for c in concepts)]
        
        if command_matches:
            score = 0.6 + 0.1 * len(command_matches)
            action_scores["trigger_system_action"] = {
                "score": min(0.9, score),
                "reason": f"Detected potential command: {', '.join(command_matches)}."
            }
        
        # Adjust based on cross-block insights
        for insight in cross_block_insights:
            if insight.get("type") == "ethics_memory_resonance" and insight.get("importance", 0) > 0.7:
                # High ethics resonance should reduce confidence in providing direct answers
                action_scores["answer_query"]["score"] = action_scores["answer_query"].get("score", 0) * 0.8
                action_scores["defer_decision"]["score"] = max(
                    action_scores["defer_decision"].get("score", 0),
                    insight.get("importance", 0)
                )
            
            if insight.get("type") == "information_gap" and insight.get("importance", 0) > 0.6:
                # Information gaps should increase score for asking clarification
                action_scores["ask_clarification"]["score"] = max(
                    action_scores["ask_clarification"].get("score", 0),
                    0.5 + insight.get("importance", 0) * 0.4
                )
        
        return action_scores
    
    def _generate_action_parameters(
        self, 
        action_type: str,
        concepts: List[str],
        retrieved_concepts: List[Any],
        ethical_flags: List[str],
        inferences: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Generates parameters needed for executing the selected action.
        
        Args:
            action_type: Type of action selected
            concepts: Extracted concepts
            retrieved_concepts: Concepts from memory
            ethical_flags: Ethical concerns
            inferences: Reasoning inferences
            
        Returns:
            Dictionary of action parameters
        """
        params = {}
        
        if action_type == "ask_clarification":
            # Generate clarification questions
            params["clarification_questions"] = self._generate_clarification_questions(
                concepts, retrieved_concepts, inferences
            )
        
        elif action_type == "defer_decision":
            # Include ethical flags and possible alternatives
            params["ethical_flags"] = ethical_flags
            params["alternatives"] = self._generate_ethical_alternatives(ethical_flags)
            
        elif action_type == "trigger_system_action":
            # Identify command parameters
            command_keywords = ["search", "find", "calculate", "show", "display", "create"]
            for keyword in command_keywords:
                matching_concepts = [c for c in concepts if keyword in c.lower()]
                if matching_concepts:
                    params["command_type"] = keyword
                    params["command_concepts"] = matching_concepts
                    break
        
        return params
    
    def _generate_clarification_questions(
        self, 
        concepts: List[str],
        retrieved_concepts: List[Any],
        inferences: Dict[str, List[str]]
    ) -> List[str]:
        """Generate relevant clarification questions."""
        questions = []
        
        # If few retrieved concepts, ask about specific topics
        if len(retrieved_concepts) < 3:
            questions.append(
                f"Could you provide more context about {', '.join(concepts[:3])}?"
            )
        
        # If inductive inferences, ask for confirmation
        if inferences.get("inductive", []):
            uncertain_inference = inferences["inductive"][0]
            questions.append(
                f"I'm considering that {uncertain_inference}. Is this aligned with your query?"
            )
        
        # If multiple interpretations possible, clarify intent
        if inferences.get("abductive", []) and len(inferences["abductive"]) > 1:
            questions.append(
                "Could you clarify your intent? There seem to be multiple possible interpretations."
            )
        
        # Default question if none generated
        if not questions:
            questions.append(
                "Could you provide more details to help me better understand your query?"
            )
        
        return questions
    
    def _generate_ethical_alternatives(self, ethical_flags: List[str]) -> List[str]:
        """Generate ethical alternatives when deferring a decision."""
        alternatives = [
            "Consider rephrasing your request to address the ethical concerns",
            "Provide additional context that might help resolve the ethical ambiguity"
        ]
        
        # Add specific alternatives based on ethical flags
        ethical_flag_alternatives = {
            "privacy": "Consider an alternative approach that respects privacy boundaries",
            "harm": "Focus on beneficial aspects rather than potentially harmful elements",
            "fairness": "Consider a more inclusive approach that treats all parties fairly",
            "consent": "Ensure all parties have provided appropriate consent",
            "bias": "Consider potential biases and how to mitigate them"
        }
        
        for flag in ethical_flags:
            for key, alternative in ethical_flag_alternatives.items():
                if key in flag.lower():
                    alternatives.append(alternative)
                    break
        
        return alternatives
    
    def _update_action_metrics(self, action_type: str, confidence: float):
        """Update metrics for the selected action."""
        metrics = self.action_metrics[action_type]
        metrics["count"] += 1
        
        # Update running average confidence
        old_avg = metrics["avg_confidence"]
        metrics["avg_confidence"] = (old_avg * (metrics["count"] - 1) + confidence) / metrics["count"]
    
    def get_action_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics about action selection performance."""
        return {
            "action_type_distribution": {action: data["count"] for action, data in self.action_metrics.items()},
            "confidence_averages": {action: data["avg_confidence"] for action, data in self.action_metrics.items()},
            "total_actions": sum(data["count"] for data in self.action_metrics.values()),
            "recent_actions": self.action_history[-10:] if self.action_history else []
        }