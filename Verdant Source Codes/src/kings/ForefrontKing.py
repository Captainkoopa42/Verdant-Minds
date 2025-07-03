import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Any, Set

from ..core.cognitive_chunk import CognitiveChunk
from .BaseKing import BaseKing


class ForefrontKing(BaseKing):
    """
    The Forefront King manages executive function, attention allocation, and decision-making.
    
    This component serves as the executive controller, overseeing cognitive load,
    working memory, attention focus, and decision thresholds. It ensures the system
    allocates resources effectively and maintains goal-directed behavior.
    """
    
    def __init__(self):
        """Initialize the Forefront King."""
        super().__init__("ForefrontKing")
        
        # Attention parameters
        self.attention_focus = None
        self.attention_history = []
        self.max_attention_history = 50
        
        # Cognitive load tracking
        self.cognitive_load = 0.5  # 0.0 to 1.0 scale
        self.cognitive_capacity = 1.0
        self.load_history = []
        
        # Working memory
        self.working_memory = {}  # Concepts with activation levels
        self.working_memory_capacity = 7  # Miller's magical number
        
        # Decision parameters
        self.decision_threshold = 0.7  # Threshold for action selection
        self.threshold_history = []
        
        # Emotional state tracking
        self.emotional_state = {"valence": 0.5, "arousal": 0.5}  # Neutral starting point
        
        # Goal management
        self.goals = []  # List of active goals with priorities
        self.goal_history = []
        
        # Oversight metrics
        self.influence_history = []
        self.oversight_metrics = {}
        self.blocks_supervised = ["InternalCommunication", "ReasoningPlanning", "ActionSelection"]
    
    def oversee_processing(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Oversees executive processing, managing attention and decision-making.
        
        Args:
            chunk: The cognitive chunk to process
            
        Returns:
            Processed cognitive chunk with executive oversight
        """
        # Extract relevant data from supervised blocks
        comm_data = chunk.get_section_content("internal_communication_section") or {}
        reasoning_data = chunk.get_section_content("reasoning_section") or {}
        action_data = chunk.get_section_content("action_selection_section") or {}
        
        # Get integrated context
        integrated_context = comm_data.get("integrated_context", {})
        
        # Focus attention on the most relevant concepts
        focus_result = self._allocate_attention(integrated_context, chunk)
        
        # Update cognitive load based on processing complexity
        load_result = self._manage_cognitive_load(chunk, integrated_context)
        
        # Update working memory with current concepts
        memory_result = self._update_working_memory(chunk, focus_result["focus"])
        
        # Adjust decision threshold based on cognitive load and context
        threshold_result = self._adjust_decision_threshold(load_result["cognitive_load"], integrated_context)
        
        # Refine action selection if needed
        action_result = self._refine_action_selection(chunk, action_data, threshold_result["decision_threshold"])
        
        # Update emotional state based on contents and processing
        emotion_result = self._update_emotional_state(chunk, action_result["selected_action"])
        
        # Update goal structures if needed
        goal_result = self._update_goals(chunk, action_result["selected_action"])
        
        # Update chunk with Forefront King's oversight information
        forefront_king_oversight = {
            "attention_focus": focus_result["focus"],
            "cognitive_load": load_result["cognitive_load"],
            "working_memory": memory_result["active_concepts"],
            "decision_threshold": threshold_result["decision_threshold"],
            "executive_assessment": action_result["assessment"],
            "emotional_state": emotion_result,
            "active_goals": goal_result["active_goals"],
            "oversight_timestamp": time.time()
        }
        
        # Create or update a dedicated section for the Forefront King
        chunk.update_section("forefront_king_section", forefront_king_oversight)
        
        # Log the influence
        self.log_influence(chunk, "executive_oversight", 
                          {"focus": focus_result["focus"], 
                           "cognitive_load": load_result["cognitive_load"],
                           "threshold": threshold_result["decision_threshold"],
                           "action_modified": action_result["action_modified"]})
        
        # Update the king's internal state
        self.attention_focus = focus_result["focus"]
        self.cognitive_load = load_result["cognitive_load"]
        self.decision_threshold = threshold_result["decision_threshold"]
        self.emotional_state = emotion_result
        
        # Store attention history
        self.attention_history.append({
            "timestamp": time.time(),
            "focus": focus_result["focus"],
            "cognitive_load": load_result["cognitive_load"]
        })
        
        # Maintain maximum history length
        if len(self.attention_history) > self.max_attention_history:
            self.attention_history.pop(0)
        
        return chunk
    
    def _allocate_attention(self, integrated_context: Dict[str, Any], chunk: CognitiveChunk) -> Dict[str, Any]:
        """
        Allocate attention to the most relevant concepts or patterns based on multi-headed attention.
        
        Args:
            integrated_context: Integrated context information
            chunk: Current cognitive chunk
            
        Returns:
            Dictionary with focus information
        """
        primary_concepts = integrated_context.get("primary_concepts", [])
        
        # Default focus
        focus = "general"
        focus_reason = "no specific concepts to focus on"
        
        if primary_concepts:
            # Get pattern data for salience information
            pattern_data = chunk.get_section_content("pattern_recognition_section") or {}
            concepts = pattern_data.get("extracted_concepts", [])
            
            # Create a map of concept values to their salience
            concept_salience = {}
            for concept in concepts:
                if isinstance(concept, dict) and "value" in concept:
                    concept_salience[concept["value"]] = concept.get("salience", 0.5)
                    
            # Find the primary concept with highest salience
            if concept_salience:
                top_concept = None
                top_salience = 0
                
                for concept in primary_concepts:
                    if concept in concept_salience and concept_salience[concept] > top_salience:
                        top_concept = concept
                        top_salience = concept_salience[concept]
                
                if top_concept:
                    focus = top_concept
                    focus_reason = f"highest salience ({top_salience:.2f}) among primary concepts"
            else:
                # If no salience information, assess based on goal relevance
                focus = self._assess_goal_relevance(primary_concepts)
                focus_reason = "most relevant to current goals"
                
        # Implement multi-headed attention - combine different attention mechanisms
        novelty_focus = self._novelty_based_attention(chunk)
        uncertainty_focus = self._uncertainty_based_attention(chunk)
        
        # Combine attention mechanisms with appropriate weights
        # In a real system, these weights would be dynamically adjusted
        combined_focus = None
        if novelty_focus["novelty_score"] > 0.8:
            combined_focus = novelty_focus["focus"]
            focus_reason = "high novelty detected"
        elif uncertainty_focus["uncertainty_score"] > 0.7:
            combined_focus = uncertainty_focus["focus"]
            focus_reason = "high uncertainty area"
        
        # Use combined focus if available and different from default
        if combined_focus and combined_focus != "general":
            focus = combined_focus
            
        return {
            "focus": focus,
            "reason": focus_reason,
            "novelty_score": novelty_focus.get("novelty_score", 0),
            "uncertainty_score": uncertainty_focus.get("uncertainty_score", 0)
        }
    
    def _novelty_based_attention(self, chunk: CognitiveChunk) -> Dict[str, Any]:
        """Allocate attention based on novelty detection."""
        # Get memory data to assess novelty
        memory_data = chunk.get_section_content("memory_section") or {}
        pattern_data = chunk.get_section_content("pattern_recognition_section") or {}
        
        # Extract concepts
        memory_concepts = memory_data.get("retrieved_concepts", [])
        current_concepts = []
        for concept in pattern_data.get("extracted_concepts", []):
            if isinstance(concept, dict) and "value" in concept:
                current_concepts.append(concept["value"])
        
        # Convert memory concepts to simple list if tuples
        memory_concept_names = []
        for item in memory_concepts:
            if isinstance(item, tuple):
                memory_concept_names.append(item[0])
            else:
                memory_concept_names.append(item)
                
        # Find novel concepts (in current but not in memory)
        novel_concepts = [c for c in current_concepts if c not in memory_concept_names]
        
        # Calculate novelty score
        novelty_score = len(novel_concepts) / max(1, len(current_concepts))
        
        # Return focus on most novel concept if available
        if novel_concepts:
            return {
                "focus": novel_concepts[0],
                "novelty_score": novelty_score,
                "novel_concepts": novel_concepts
            }
        
        return {
            "focus": "general",
            "novelty_score": novelty_score,
            "novel_concepts": []
        }
    
    def _uncertainty_based_attention(self, chunk: CognitiveChunk) -> Dict[str, Any]:
        """Allocate attention based on uncertainty assessment."""
        # Get reasoning data to assess uncertainty
        reasoning_data = chunk.get_section_content("reasoning_section") or {}
        
        # Look for inconsistencies and uncertainty adjustments
        inconsistencies = reasoning_data.get("inconsistencies", [])
        uncertainty_adjustments = reasoning_data.get("uncertainty_adjustments", [])
        
        # Calculate uncertainty score
        uncertainty_score = (len(inconsistencies) * 0.2 + len(uncertainty_adjustments) * 0.1)
        uncertainty_score = min(1.0, uncertainty_score)  # Cap at 1.0
        
        # Find focus area with highest uncertainty
        focus = "general"
        if inconsistencies:
            # Extract concepts from first inconsistency
            inconsistent_concepts = self._extract_concepts_from_text(
                inconsistencies[0].get("inference1", "")
            )
            if inconsistent_concepts:
                focus = inconsistent_concepts[0]
                
        return {
            "focus": focus,
            "uncertainty_score": uncertainty_score,
            "inconsistencies": len(inconsistencies),
            "uncertainty_adjustments": len(uncertainty_adjustments)
        }
    
    def _extract_concepts_from_text(self, text: str) -> List[str]:
        """Extract potential concepts from text."""
        # Simple implementation - in a real system this would be more sophisticated
        words = text.split()
        # Look for capitalized words as potential concepts
        concepts = [word for word in words if word and word[0].isupper()]
        return concepts
        
    def _assess_goal_relevance(self, concepts: List[str]) -> str:
        """Assess which concept is most relevant to current goals."""
        # If no active goals, return first concept
        if not self.goals or not concepts:
            return concepts[0] if concepts else "general"
            
        # Simple implementation - match concepts to goal keywords
        # In a real system, this would use semantic similarity
        for goal in sorted(self.goals, key=lambda g: g.get("priority", 0), reverse=True):
            goal_desc = goal.get("description", "").lower()
            for concept in concepts:
                if concept.lower() in goal_desc:
                    return concept
                    
        # Default to first concept if no matches
        return concepts[0]
    
    def _manage_cognitive_load(self, chunk: CognitiveChunk, integrated_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update cognitive load based on processing complexity.
        
        Args:
            chunk: Current cognitive chunk
            integrated_context: Integrated context information
            
        Returns:
            Updated cognitive load information
        """
        # Start with current load for inertia
        new_load = self.cognitive_load
        
        # Factors that increase cognitive load
        load_factors = []
        
        # 1. Number of concepts to process
        concept_count = len(integrated_context.get("primary_concepts", []))
        if concept_count > 5:
            load_factors.append(0.1)  # Moderate increase for many concepts
        
        # 2. Ethical complexity
        ethical_flags = integrated_context.get("ethical_flags", [])
        if ethical_flags:
            load_factors.append(0.15 * len(ethical_flags))  # Significant increase for ethical issues
        
        # 3. Reasoning complexity
        reasoning_data = chunk.get_section_content("reasoning_section") or {}
        inference_count = sum(len(infs) for infs in reasoning_data.get("inferences", {}).values())
        if inference_count > 3:
            load_factors.append(0.08 * min(inference_count / 10, 1))  # Scale with inference count
        
        # 4. Ambiguity (lack of confidence)
        confidence_scores = integrated_context.get("confidence_scores", {})
        if confidence_scores:
            avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
            load_factors.append(0.2 * (1 - avg_confidence))  # Higher load for low confidence
        
        # 5. Process history length
        process_steps = len(chunk.processing_log)
        if process_steps > 5:  # Complex processing chain
            load_factors.append(0.05 * min(process_steps / 20, 1))  # Scale with process complexity
            
        # Apply load factors
        load_change = sum(load_factors)
        
        # Apply decay toward baseline (0.5) for natural recovery
        baseline = 0.5
        decay_rate = 0.2
        new_load = (1 - decay_rate) * new_load + decay_rate * baseline + load_change
        
        # Ensure load stays in valid range
        new_load = max(0.1, min(0.95, new_load))
        
        # Update load history
        self.load_history.append({
            "timestamp": time.time(),
            "load": new_load,
            "factors": load_factors
        })
        
        # Trim history if needed
        if len(self.load_history) > self.max_attention_history:
            self.load_history.pop(0)
        
        return {
            "cognitive_load": new_load,
            "load_factors": load_factors,
            "load_change": load_change,
            "capacity_percentage": new_load / self.cognitive_capacity
        }
    
    def _update_working_memory(self, chunk: CognitiveChunk, focus: str) -> Dict[str, Any]:
        """
        Update working memory with current concepts, focusing on the most relevant.
        
        Args:
            chunk: Current cognitive chunk
            focus: Current attention focus
            
        Returns:
            Updated working memory information
        """
        # Get memory and pattern data
        memory_data = chunk.get_section_content("memory_section") or {}
        pattern_data = chunk.get_section_content("pattern_recognition_section") or {}
        
        # Extract concepts
        memory_concepts = memory_data.get("retrieved_concepts", [])
        current_concepts = []
        for concept in pattern_data.get("extracted_concepts", []):
            if isinstance(concept, dict) and "value" in concept:
                current_concepts.append((concept["value"], concept.get("salience", 0.5)))
            elif isinstance(concept, str):
                current_concepts.append((concept, 0.5))
        
        # Convert memory concepts to consistent format
        formatted_memory = []
        for item in memory_concepts:
            if isinstance(item, tuple) and len(item) >= 2:
                formatted_memory.append((item[0], item[1]))
            elif isinstance(item, str):
                formatted_memory.append((item, 0.5))
        
        # Combine all concepts
        all_concepts = {}
        for concept, salience in formatted_memory + current_concepts:
            if concept in all_concepts:
                # Take the maximum salience if concept appears multiple times
                all_concepts[concept] = max(all_concepts[concept], salience)
            else:
                all_concepts[concept] = salience
        
        # Prioritize focused concept
        if focus != "general" and focus in all_concepts:
            all_concepts[focus] += 0.2  # Boost salience of focused concept
            
        # Prioritize concepts based on salience and recency
        prioritized_concepts = sorted(
            all_concepts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Keep only top concepts within working memory capacity
        active_concepts = prioritized_concepts[:self.working_memory_capacity]
        
        # Update working memory
        self.working_memory = dict(active_concepts)
        
        return {
            "active_concepts": dict(active_concepts),
            "capacity": self.working_memory_capacity,
            "utilization": len(active_concepts) / self.working_memory_capacity,
            "focus_boost": focus if focus != "general" else None
        }
    
    def _adjust_decision_threshold(self, cognitive_load: float, integrated_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adjusts decision threshold based on cognitive load and context.
        
        Args:
            cognitive_load: Current cognitive load
            integrated_context: Integrated context information
            
        Returns:
            Updated decision threshold information
        """
        # Base threshold
        base_threshold = 0.7
        
        # Adjust threshold based on cognitive load
        # Higher load -> higher threshold (more conservative)
        load_adjustment = 0.2 * (cognitive_load - 0.5)  # -0.1 to +0.1 range
        
        # Adjust threshold based on ethical flags
        ethical_flags = integrated_context.get("ethical_flags", [])
        ethics_adjustment = 0.05 * len(ethical_flags)  # Higher threshold for ethical concerns
        
        # Adjust threshold based on confidence
        confidence_scores = integrated_context.get("confidence_scores", {})
        confidence_adjustment = 0
        if confidence_scores:
            avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
            confidence_adjustment = -0.1 * avg_confidence  # Lower threshold for high confidence
        
        # Adjust threshold based on emotional state
        emotional_adjustment = 0
        if self.emotional_state["arousal"] > 0.7:  # High arousal (stress/excitement)
            emotional_adjustment = 0.1  # More cautious under high arousal
        elif self.emotional_state["valence"] < 0.3:  # Negative valence
            emotional_adjustment = 0.05  # More cautious under negative emotions
        
        # Combine adjustments
        new_threshold = base_threshold + load_adjustment + ethics_adjustment + confidence_adjustment + emotional_adjustment
        
        # Ensure threshold stays in valid range
        new_threshold = max(0.4, min(0.9, new_threshold))
        
        # Update threshold history
        self.threshold_history.append({
            "timestamp": time.time(),
            "threshold": new_threshold,
            "load_adjustment": load_adjustment,
            "ethics_adjustment": ethics_adjustment,
            "confidence_adjustment": confidence_adjustment,
            "emotional_adjustment": emotional_adjustment
        })
        
        # Trim history if needed
        if len(self.threshold_history) > self.max_attention_history:
            self.threshold_history.pop(0)
        
        return {
            "decision_threshold": new_threshold,
            "adjustments": {
                "load": load_adjustment,
                "ethics": ethics_adjustment,
                "confidence": confidence_adjustment,
                "emotional": emotional_adjustment
            }
        }
    
    def _refine_action_selection(self, chunk: CognitiveChunk, action_data: Dict[str, Any], decision_threshold: float) -> Dict[str, Any]:
        """
        Refines the action selection based on executive oversight.
        
        Args:
            chunk: Current cognitive chunk
            action_data: Action selection data
            decision_threshold: Current decision threshold
            
        Returns:
            Refined action selection information
        """
        # Get selected action and confidence
        selected_action = action_data.get("selected_action", "provide_partial_answer")
        action_confidence = action_data.get("action_confidence", 0.5)
        all_action_scores = action_data.get("all_action_scores", {})
        
        # Default assessment
        assessment = "action approved"
        action_modified = False
        
        # Check if action meets threshold
        if action_confidence < decision_threshold:
            # Action confidence is too low
            # Find more conservative action with higher confidence
            if selected_action == "answer_query" and "provide_partial_answer" in all_action_scores:
                selected_action = "provide_partial_answer"
                action_confidence = all_action_scores["provide_partial_answer"]
                assessment = "downgraded to partial answer due to low confidence"
                action_modified = True
                
            elif selected_action in ["answer_query", "provide_partial_answer"] and "ask_clarification" in all_action_scores:
                selected_action = "ask_clarification"
                action_confidence = all_action_scores["ask_clarification"]
                assessment = "switched to clarification due to insufficient confidence"
                action_modified = True
        
        # Check for ethical concerns that might have been missed
        ethics_section = chunk.get_section_content("ethical_consideration_section") or {}
        ethical_flags = ethics_section.get("concerns", [])
        if ethical_flags and selected_action not in ["defer_decision", "ask_clarification"]:
            selected_action = "defer_decision"
            action_confidence = 0.8  # High confidence in deferring for ethical reasons
            assessment = "deferred for ethical review due to detected concerns"
            action_modified = True
        
        # Check cognitive load threshold for complex actions
        if self.cognitive_load > 0.8 and selected_action in ["answer_query"]:
            selected_action = "provide_partial_answer"
            action_confidence = 0.7
            assessment = "downgraded to simpler action due to high cognitive load"
            action_modified = True
        
        # If action was modified, update the action section
        if action_modified:
            # Update action selection section
            action_data["selected_action"] = selected_action
            action_data["action_confidence"] = action_confidence
            action_data["forefront_override"] = True
            action_data["override_reason"] = assessment
            
            chunk.update_section("action_selection_section", action_data)
            
        return {
            "selected_action": selected_action,
            "action_confidence": action_confidence,
            "assessment": assessment,
            "action_modified": action_modified,
            "threshold_applied": decision_threshold
        }
    
    def _update_emotional_state(self, chunk: CognitiveChunk, selected_action: str) -> Dict[str, Any]:
        """
        Updates the emotional state based on content and processing.
        
        Args:
            chunk: Current cognitive chunk
            selected_action: Selected action
            
        Returns:
            Updated emotional state
        """
        # Get sensory data for sentiment analysis
        sensory_data = chunk.get_section_content("sensory_input_section") or {}
        sentiment = sensory_data.get("sentiment", {})
        
        # Current emotional state
        current_valence = self.emotional_state.get("valence", 0.5)
        current_arousal = self.emotional_state.get("arousal", 0.5)
        
        # Update valence (positive/negative dimension)
        valence_target = 0.5  # Neutral default
        if sentiment:
            # Use sentiment if available
            valence_target = 0.5 + (sentiment.get("positive_score", 0) - sentiment.get("negative_score", 0))
        
        # Update arousal (intensity dimension)
        arousal_target = 0.5  # Neutral default
        
        # Increase arousal for ethical concerns or important actions
        if selected_action in ["defer_decision", "trigger_system_action"]:
            arousal_target = 0.7
        
        # Increase arousal for high cognitive load
        arousal_target += (self.cognitive_load - 0.5) * 0.2
        
        # Apply smooth transition (inertia)
        inertia_factor = 0.8  # 80% old, 20% new
        new_valence = inertia_factor * current_valence + (1 - inertia_factor) * valence_target
        new_arousal = inertia_factor * current_arousal + (1 - inertia_factor) * arousal_target
        
        # Ensure values stay in valid range
        new_valence = max(0.1, min(0.9, new_valence))
        new_arousal = max(0.1, min(0.9, new_arousal))
        
        # Map to emotional state labels
        emotional_labels = self._map_to_emotion_labels(new_valence, new_arousal)
        
        return {
            "valence": new_valence,
            "arousal": new_arousal,
            "emotional_state": emotional_labels
        }
    
    def _map_to_emotion_labels(self, valence: float, arousal: float) -> List[str]:
        """
        Maps valence and arousal dimensions to emotional state labels.
        
        Args:
            valence: Emotional valence (negative to positive)
            arousal: Emotional arousal (calm to excited)
            
        Returns:
            List of emotional state labels
        """
        # High arousal, positive valence
        if arousal > 0.6 and valence > 0.6:
            return ["excited", "engaged", "enthusiastic"]
        
        # High arousal, negative valence  
        elif arousal > 0.6 and valence < 0.4:
            return ["stressed", "concerned", "alert"]
            
        # Low arousal, positive valence
        elif arousal < 0.4 and valence > 0.6:
            return ["content", "calm", "satisfied"]
            
        # Low arousal, negative valence
        elif arousal < 0.4 and valence < 0.4:
            return ["discouraged", "reserved", "cautious"]
            
        # Balanced states
        elif 0.4 <= valence <= 0.6 and 0.4 <= arousal <= 0.6:
            return ["neutral", "balanced", "attentive"]
            
        # High arousal, neutral valence
        elif arousal > 0.6 and 0.4 <= valence <= 0.6:
            return ["alert", "focused", "attentive"]
            
        # Low arousal, neutral valence
        elif arousal < 0.4 and 0.4 <= valence <= 0.6:
            return ["relaxed", "contemplative", "reserved"]
            
        # Neutral arousal, positive valence
        elif 0.4 <= arousal <= 0.6 and valence > 0.6:
            return ["positive", "optimistic", "open"]
            
        # Neutral arousal, negative valence
        elif 0.4 <= arousal <= 0.6 and valence < 0.4:
            return ["cautious", "skeptical", "concerned"]
            
        # Default
        else:
            return ["neutral", "balanced"]
    
    def _update_goals(self, chunk: CognitiveChunk, selected_action: str) -> Dict[str, Any]:
        """
        Updates goal structures based on current processing.
        
        Args:
            chunk: Current cognitive chunk
            selected_action: Selected action
            
        Returns:
            Updated goal information
        """
        # Extract action parameters and reasoning
        action_data = chunk.get_section_content("action_selection_section") or {}
        action_params = action_data.get("action_parameters", {})
        reasoning_data = chunk.get_section_content("reasoning_section") or {}
        
        # Check if we need to create a new goal
        created_goal = None
        if selected_action == "ask_clarification":
            # Create information gathering goal
            clarification_questions = action_params.get("clarification_questions", [])
            if clarification_questions:
                created_goal = {
                    "id": f"goal_{time.time()}",
                    "type": "information_gathering",
                    "description": f"Gather information: {clarification_questions[0]}",
                    "priority": 0.8,
                    "created_at": time.time(),
                    "status": "active"
                }
                self.goals.append(created_goal)
        
        # Check if any goals should be completed
        completed_goals = []
        for goal in self.goals:
            if goal["status"] != "active":
                continue
                
            if goal["type"] == "information_gathering" and selected_action == "answer_query":
                # Mark information gathering goal as complete
                goal["status"] = "completed"
                goal["completed_at"] = time.time()
                completed_goals.append(goal)
        
        # Remove completed goals from active list
        self.goals = [g for g in self.goals if g["status"] == "active"]
        
        # Record goal history
        if created_goal or completed_goals:
            self.goal_history.append({
                "timestamp": time.time(),
                "created_goal": created_goal,
                "completed_goals": completed_goals
            })
            
        # Return active goals with prioritization
        active_goals = sorted(self.goals, key=lambda g: g.get("priority", 0), reverse=True)
        
        return {
            "active_goals": active_goals,
            "created_goal": created_goal,
            "completed_goals": completed_goals,
            "goal_count": len(active_goals)
        }
    
    def log_influence(self, chunk: CognitiveChunk, influence_type: str, details: Dict[str, Any]):
        """
        Logs the king's influence on processing.
        
        Args:
            chunk: The chunk being processed
            influence_type: Type of influence applied
            details: Influence details
        """
        influence_record = {
            "king": "ForefrontKing",
            "influence_type": influence_type,
            "timestamp": time.time(),
            "details": details
        }
        
        # Add to chunk's processing log
        chunk.add_processing_step("ForefrontKing", influence_type, details)
        
        # Add to king's influence history
        self.influence_history.append(influence_record)
        
        # Keep history at a reasonable size
        if len(self.influence_history) > 1000:
            self.influence_history = self.influence_history[-1000:]
            
        return influence_record
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Gets comprehensive performance metrics for the Forefront King.
        
        Returns:
            Dictionary of performance metrics
        """
        # Analyze attention history
        attention_focus_counts = {}
        for entry in self.attention_history:
            focus = entry.get('focus', 'general')
            attention_focus_counts[focus] = attention_focus_counts.get(focus, 0) + 1
        
        # Most common attention focus
        most_common_focus = max(attention_focus_counts.items(), key=lambda x: x[1], default=('general', 0))[0]
        
        # Analyze cognitive load history
        if self.load_history:
            avg_cognitive_load = sum(entry['load'] for entry in self.load_history) / len(self.load_history)
            load_range = max(entry['load'] for entry in self.load_history) - min(entry['load'] for entry in self.load_history)
        else:
            avg_cognitive_load = self.cognitive_load
            load_range = 0
        
        # Analyze decision threshold history
        if self.threshold_history:
            avg_decision_threshold = sum(entry['threshold'] for entry in self.threshold_history) / len(self.threshold_history)
            threshold_range = max(entry['threshold'] for entry in self.threshold_history) - min(entry['threshold'] for entry in self.threshold_history)
        else:
            avg_decision_threshold = self.decision_threshold
            threshold_range = 0
        
        # Analyze goal management
        goal_metrics = {
            "total_goals_created": len(self.goal_history),
            "active_goals": len(self.goals),
            "goal_completion_rate": sum(1 for history in self.goal_history if history.get('completed_goals')) / max(1, len(self.goal_history))
        }
        
        # Analyze emotional state evolution
        emotional_state_metrics = {
            "valence_history": {
                "current": self.emotional_state['valence'],
                "max": max(history.get('valence', 0.5) for history in self.attention_history),
                "min": min(history.get('valence', 0.5) for history in self.attention_history)
            },
            "arousal_history": {
                "current": self.emotional_state['arousal'],
                "max": max(history.get('arousal', 0.5) for history in self.attention_history),
                "min": min(history.get('arousal', 0.5) for history in self.attention_history)
            }
        }
        
        # Compilation of performance metrics
        performance_metrics = {
            "oversight_metrics": {
                "total_influences": len(self.influence_history),
                "blocks_supervised": self.blocks_supervised
            },
            "attention_metrics": {
                "focus_history": attention_focus_counts,
                "most_common_focus": most_common_focus,
                "total_attention_entries": len(self.attention_history)
            },
            "cognitive_load_metrics": {
                "current_load": self.cognitive_load,
                "average_load": avg_cognitive_load,
                "load_range": load_range,
                "load_capacity": self.cognitive_capacity,
                "total_load_entries": len(self.load_history)
            },
            "decision_threshold_metrics": {
                "current_threshold": self.decision_threshold,
                "average_threshold": avg_decision_threshold,
                "threshold_range": threshold_range,
                "total_threshold_entries": len(self.threshold_history)
            },
            "goal_management_metrics": goal_metrics,
            "emotional_state_metrics": emotional_state_metrics,
            "working_memory_metrics": {
                "current_concepts": list(self.working_memory.keys()),
                "current_capacity": len(self.working_memory),
                "max_capacity": self.working_memory_capacity,
                "utilization_rate": len(self.working_memory) / self.working_memory_capacity
            }
        }
        
        return performance_metrics