import numpy as np
import time
import re
from typing import Dict, List, Any, Optional, Tuple

from src.blocks.base_block import BaseBlock
from src.core.cognitive_chunk import CognitiveChunk

class LanguageProcessingBlock(BaseBlock):
    """
    Block 8: Language Processing
    
    Handles natural language processing, including understanding input text
    and generating linguistic responses based on the system's cognitive state.
    Integrates with the ECWF to ensure ethical and contextually appropriate
    language generation.
    """
    
    def __init__(self, memory_bridge=None):
        """
        Initialize the Language Processing block.
        
        Args:
            memory_bridge: Optional reference to Memory-ECWF bridge for cognitive-linguistic translation
        """
        super().__init__("LanguageProcessing")
        self.memory_bridge = memory_bridge
        
        # Tracking for language processing performance
        self.processing_history = []
        self.max_history_length = 50
        
        # Language style and tone settings
        self.language_style = {
            "formality": 0.5,  # 0 = casual, 1 = formal
            "complexity": 0.5,  # 0 = simple, 1 = complex
            "precision": 0.6,   # 0 = general, 1 = precise
            "empathy": 0.7      # 0 = neutral, 1 = highly empathetic
        }
        
        # Context tracking for coherent conversations
        self.context_history = []
        self.context_window_size = 5
    
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Process a cognitive chunk to generate appropriate language response.
        
        Args:
            chunk: The cognitive chunk to process
            
        Returns:
            Processed cognitive chunk with language generation results
        """
        # Extract relevant data from chunk
        action_data = chunk.get_section_content("action_selection_section") or {}
        reasoning_data = chunk.get_section_content("reasoning_section") or {}
        memory_data = chunk.get_section_content("memory_section") or {}
        ethics_data = chunk.get_section_content("ethics_king_section") or {}
        sensory_data = chunk.get_section_content("sensory_input_section") or {}
        
        # Get selected action and parameters
        selected_action = action_data.get("selected_action", "provide_partial_answer")
        action_confidence = action_data.get("action_confidence", 0.5)
        action_parameters = action_data.get("action_parameters", {})
        
        # Get input text for context
        input_text = sensory_data.get("input_text", "")
        self._update_context_history(input_text)
        
        # Extract reasoning insights and memory concepts
        reasoning_plan = reasoning_data.get("reasoning_plan", [])
        memory_concepts = self._extract_concepts(memory_data)
        
        # Get ethical insights
        ethical_evaluation = ethics_data.get("evaluation", {})
        ethical_status = ethical_evaluation.get("status", "acceptable")
        ethical_principles = ethical_evaluation.get("principle_scores", {})
        
        # Get cognitive and ethical state from memory bridge
        cognitive_state, ethical_state = self._get_cognitive_ethical_state(memory_concepts)
        
        # Adjust language style based on action and ethical context
        self._adjust_language_style(selected_action, ethical_status, action_confidence)
        
        # Generate response based on action type
        response = self._generate_response(
            selected_action=selected_action,
            action_confidence=action_confidence,
            action_parameters=action_parameters,
            reasoning_plan=reasoning_plan,
            memory_concepts=memory_concepts,
            ethical_status=ethical_status,
            ethical_principles=ethical_principles,
            input_text=input_text,
            cognitive_state=cognitive_state,
            ethical_state=ethical_state
        )
        
        # Update language processing section in chunk
        language_data = {
            "generated_response": response,
            "language_style": self.language_style,
            "cognitive_state": cognitive_state.tolist() if isinstance(cognitive_state, np.ndarray) else cognitive_state,
            "ethical_state": ethical_state.tolist() if isinstance(ethical_state, np.ndarray) else ethical_state,
            "context_sensitivity": self._calculate_context_sensitivity(),
            "processed_timestamp": time.time()
        }
        
        chunk.update_section("language_processing_section", language_data)
        
        # Record processing for history
        self._record_processing(selected_action, action_confidence, len(response))
        
        # Log processing details
        self.log_process(chunk, "language_generation", {
            "action_type": selected_action,
            "response_length": len(response),
            "style": self.language_style
        })
        
        return chunk
    
    def _extract_concepts(self, memory_data: Dict[str, Any]) -> List[str]:
        """Extract concepts from memory data."""
        concepts = []
        
        # Extract retrieved concepts
        if "retrieved_concepts" in memory_data:
            for concept in memory_data["retrieved_concepts"]:
                if isinstance(concept, tuple) and len(concept) >= 1:
                    concepts.append(concept[0])
                elif isinstance(concept, str):
                    concepts.append(concept)
        
        # Also extract activated concepts
        if "activated_concepts" in memory_data:
            activated = memory_data["activated_concepts"]
            if isinstance(activated, dict):
                concepts.extend(list(activated.keys()))
            elif isinstance(activated, list):
                concepts.extend(activated)
        
        # Remove duplicates and limit to top concepts
        return list(set(concepts))[:10]
    
    def _get_cognitive_ethical_state(self, concepts: List[str]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get cognitive and ethical state vectors based on concepts.
        
        Args:
            concepts: List of active concepts
            
        Returns:
            Tuple of (cognitive_state, ethical_state) as numpy arrays
        """
        # If memory bridge is available, use it to get states
        if self.memory_bridge:
            cognitive_state = self.memory_bridge.get_cognitive_state_for_concepts(concepts)
            ethical_state = self.memory_bridge.get_ethical_state_for_concepts(concepts)
            return cognitive_state, ethical_state
        
        # Otherwise, create default states
        return np.array([0.5, 0.5, 0.5, 0.5, 0.5]), np.array([0.5, 0.5, 0.5, 0.5, 0.5])
    
    def _adjust_language_style(self, action: str, ethical_status: str, confidence: float):
        """
        Adjust language style based on action type and ethical context.
        
        Args:
            action: Selected action type
            ethical_status: Ethical evaluation status
            confidence: Action confidence
        """
        # Adjust formality based on action type
        if action in ["answer_query", "defer_decision"]:
            self.language_style["formality"] = 0.7  # More formal for direct answers and ethical issues
        elif action in ["ask_clarification", "provide_partial_answer"]:
            self.language_style["formality"] = 0.5  # Balanced for clarifications
        
        # Adjust complexity based on confidence
        self.language_style["complexity"] = max(0.3, min(0.8, confidence + 0.1))
        
        # Adjust precision based on confidence
        self.language_style["precision"] = max(0.4, min(0.9, confidence + 0.2))
        
        # Adjust empathy based on ethical status
        if ethical_status in ["review_needed", "acceptable"]:
            self.language_style["empathy"] = 0.8  # Higher empathy for ethically sensitive topics
        else:
            self.language_style["empathy"] = 0.6  # Moderate empathy for standard topics
    
    def _generate_response(
        self,
        selected_action: str,
        action_confidence: float,
        action_parameters: Dict[str, Any],
        reasoning_plan: List[Dict[str, Any]],
        memory_concepts: List[str],
        ethical_status: str,
        ethical_principles: Dict[str, float],
        input_text: str,
        cognitive_state: np.ndarray,
        ethical_state: np.ndarray
    ) -> str:
        """
        Generate a natural language response based on system state.
        
        Args:
            selected_action: Type of action to take
            action_confidence: Confidence in the action
            action_parameters: Parameters for the action
            reasoning_plan: Reasoning steps from reasoning block
            memory_concepts: Relevant concepts from memory
            ethical_status: Ethical evaluation status
            ethical_principles: Ethical principle scores
            input_text: Original input text
            cognitive_state: Current cognitive state vector
            ethical_state: Current ethical state vector
            
        Returns:
            Generated natural language response
        """
        # Select generation method based on action type
        if selected_action == "answer_query":
            return self._generate_direct_answer(
                memory_concepts, 
                reasoning_plan, 
                ethical_status, 
                action_confidence,
                ethical_principles
            )
        elif selected_action == "provide_partial_answer":
            return self._generate_partial_answer(
                memory_concepts, 
                reasoning_plan, 
                ethical_status, 
                action_confidence
            )
        elif selected_action == "ask_clarification":
            return self._generate_clarification_request(
                action_parameters, 
                memory_concepts
            )
        elif selected_action == "defer_decision":
            return self._generate_ethical_deferral(
                ethical_status, 
                ethical_principles, 
                memory_concepts
            )
        else:
            # Default response for unknown action types
            return self._generate_default_response(input_text, memory_concepts)
    
    def _generate_direct_answer(
        self,
        concepts: List[str],
        reasoning_plan: List[Dict[str, Any]],
        ethical_status: str,
        confidence: float,
        ethical_principles: Dict[str, float]
    ) -> str:
        """Generate a direct, comprehensive answer."""
        # Get conclusion from reasoning plan
        conclusion = self._extract_conclusion(reasoning_plan)
        
        # Format concepts for inclusion
        concept_text = ", ".join(concepts[:5])
        if not concept_text:
            concept_text = "the available information"
        
        # Start with introduction
        response = f"Based on my understanding of {concept_text}, "
        
        # Add main conclusion
        if conclusion:
            response += f"{conclusion} "
        else:
            response += "I can provide the following insights. "
        
        # Add reasoning steps if confidence is high
        if confidence > 0.7 and reasoning_plan:
            response += "My reasoning follows these key steps:\n\n"
            for i, step in enumerate(reasoning_plan[:3]):
                response += f"{i+1}. {step.get('description', 'Analysis')}: "
                content = step.get('content', [])
                if isinstance(content, list) and content:
                    response += f"{content[0]} "
                elif isinstance(content, str):
                    response += f"{content} "
                response += "\n"
        
        # Add ethical considerations if relevant
        if ethical_status != "excellent" and ethical_principles:
            top_principles = sorted(ethical_principles.items(), key=lambda x: x[1], reverse=True)[:2]
            response += "\n\nIt's worth noting the ethical considerations around "
            response += ", ".join([principle for principle, _ in top_principles]) + ". "
        
        # Add confidence statement
        if confidence > 0.8:
            response += "I have high confidence in this assessment."
        elif confidence > 0.6:
            response += "I have moderate confidence in this assessment."
        else:
            response += "While this represents my current understanding, there's room for additional exploration."
        
        return response
    
    def _generate_partial_answer(
        self,
        concepts: List[str],
        reasoning_plan: List[Dict[str, Any]],
        ethical_status: str,
        confidence: float
    ) -> str:
        """Generate a partial answer acknowledging limitations."""
        # Format concepts for inclusion
        concept_text = ", ".join(concepts[:3])
        if not concept_text:
            concept_text = "the information available to me"
        
        # Start with acknowledging limitations
        response = f"Based on {concept_text}, I can offer a partial perspective, though my understanding is incomplete. "
        
        # Add preliminary insights
        if reasoning_plan:
            response += "Here's what I understand so far:\n\n"
            for i, step in enumerate(reasoning_plan[:2]):
                response += f"• {step.get('description', 'Observation')}: "
                content = step.get('content', [])
                if isinstance(content, list) and content:
                    response += f"{content[0]}"
                elif isinstance(content, str):
                    response += f"{content}"
                response += "\n"
        
        # Add ethical consideration if relevant
        if ethical_status == "review_needed":
            response += "\nI note that this topic involves ethical considerations that warrant careful attention. "
        
        # Add confidence statement and request for more information
        response += f"\nMy confidence in this assessment is limited (approximately {int(confidence * 100)}%). "
        response += "Could you provide additional details to help expand my understanding?"
        
        return response
    
    def _generate_clarification_request(
        self,
        action_parameters: Dict[str, Any],
        concepts: List[str]
    ) -> str:
        """Generate a request for clarification."""
        # Get clarification questions from parameters
        questions = action_parameters.get("clarification_questions", [])
        if not questions:
            questions = ["Could you provide more context or details?"]
        
        # Format concepts for inclusion
        concept_text = ", ".join(concepts[:3])
        
        # Start with acknowledgment
        if concept_text:
            response = f"I see you're asking about {concept_text}, but I need some clarification to better assist you. "
        else:
            response = "To better assist you, I need some clarification about your query. "
        
        # Add primary question
        response += f"\n\n{questions[0]}"
        
        # Add follow-up questions if available
        if len(questions) > 1:
            response += f"\n\nAdditionally, it would help if I knew: {questions[1]}"
        
        # Add helpful context for why clarification is needed
        response += "\n\nThis will help me provide a more accurate and relevant response."
        
        return response
    
    def _generate_ethical_deferral(
        self,
        ethical_status: str,
        ethical_principles: Dict[str, float],
        concepts: List[str]
    ) -> str:
        """Generate a response that defers on ethical grounds."""
        # Format concepts for inclusion
        concept_text = ", ".join(concepts[:3])
        if not concept_text:
            concept_text = "this topic"
        
        # Start with ethical acknowledgment
        response = f"Your query about {concept_text} touches on important ethical considerations. "
        
        # Add specific ethical principles
        if ethical_principles:
            top_principles = sorted(ethical_principles.items(), key=lambda x: x[1], reverse=True)[:2]
            principle_names = [name for name, _ in top_principles]
            response += f"This involves aspects of {' and '.join(principle_names)}, which require careful consideration. "
        
        # Explain deferral
        response += "I want to approach this topic thoughtfully and responsibly. "
        response += "Ethical reasoning requires balancing multiple perspectives and values, and I want to ensure my response is appropriately nuanced. "
        
        # Request more context
        response += "\n\nCould you share more about the specific context or your goals? "
        response += "This would help me provide a more thoughtful and appropriate response."
        
        return response
    
    def _generate_default_response(self, input_text: str, concepts: List[str]) -> str:
        """Generate a default response when no specific action is selected."""
        # Format concepts for inclusion
        concept_text = ", ".join(concepts[:3])
        if not concept_text:
            concept_text = "your query"
        
        # Create general response
        response = f"I've processed your question about {concept_text}. "
        response += "To provide the most helpful response, could you let me know what specific aspect you're most interested in learning about?"
        
        return response
    
    def _extract_conclusion(self, reasoning_plan: List[Dict[str, Any]]) -> str:
        """Extract conclusion from reasoning plan."""
        if not reasoning_plan:
            return ""
        
        # Look for conclusion step
        for step in reversed(reasoning_plan):
            if step.get("type") == "conclusion_formation":
                content = step.get("content", [])
                if isinstance(content, list) and content:
                    return content[0]
                elif isinstance(content, str):
                    return content
        
        # If no conclusion step found, use the last step
        last_step = reasoning_plan[-1]
        content = last_step.get("content", [])
        if isinstance(content, list) and content:
            return content[0]
        elif isinstance(content, str):
            return content
        
        return ""
    
    def _update_context_history(self, input_text: str):
        """Update context history with new input."""
        if input_text:
            self.context_history.append({
                "text": input_text,
                "timestamp": time.time()
            })
            
            # Maintain maximum context window size
            if len(self.context_history) > self.context_window_size:
                self.context_history.pop(0)
    
    def _calculate_context_sensitivity(self) -> float:
        """Calculate how sensitive the response is to conversation context."""
        if not self.context_history:
            return 0.5
        
        # More context history means more context sensitivity
        context_factor = min(1.0, len(self.context_history) / self.context_window_size)
        
        # Recent context has more influence
        recency_factor = 0.0
        if len(self.context_history) > 1:
            current_time = time.time()
            most_recent = current_time - self.context_history[-1]["timestamp"]
            second_recent = current_time - self.context_history[-2]["timestamp"]
            
            # If recent messages are close together, increase context sensitivity
            time_gap = most_recent / max(1.0, second_recent)
            recency_factor = 1.0 - min(1.0, time_gap)
        
        return 0.5 * context_factor + 0.5 * recency_factor
    
    def _record_processing(self, action_type: str, confidence: float, response_length: int):
        """Record processing details for performance history."""
        self.processing_history.append({
            "timestamp": time.time(),
            "action_type": action_type,
            "confidence": confidence,
            "response_length": response_length,
            "style": self.language_style.copy()
        })
        
        # Maintain maximum history length
        if len(self.processing_history) > self.max_history_length:
            self.processing_history.pop(0)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for this block.
        
        Returns:
            Dictionary of performance metrics
        """
        if not self.processing_history:
            return {
                "average_response_length": 0,
                "action_type_distribution": {},
                "average_confidence": 0,
                "language_style": self.language_style
            }
        
        # Calculate average response length
        avg_length = sum(entry["response_length"] for entry in self.processing_history) / len(self.processing_history)
        
        # Calculate action type distribution
        action_counts = {}
        for entry in self.processing_history:
            action = entry["action_type"]
            action_counts[action] = action_counts.get(action, 0) + 1
        
        action_distribution = {action: count / len(self.processing_history) for action, count in action_counts.items()}
        
        # Calculate average confidence
        avg_confidence = sum(entry["confidence"] for entry in self.processing_history) / len(self.processing_history)
        
        return {
            "average_response_length": avg_length,
            "action_type_distribution": action_distribution,
            "average_confidence": avg_confidence,
            "language_style": self.language_style,
            "context_window_size": self.context_window_size,
            "context_history_length": len(self.context_history)
        }