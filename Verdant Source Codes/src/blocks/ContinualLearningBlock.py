import numpy as np
import time
import logging
from typing import Dict, List, Tuple, Optional, Any

from .base_block import BaseBlock
from ..core.cognitive_chunk import CognitiveChunk

logger = logging.getLogger(__name__)

class ContinualLearningBlock(BaseBlock):
    """
    Block 9: Continual Learning & Adaptation
    
    Adapts and refines the system over time by learning from interactions.
    Optimizes parameters across components and enhances cross-block integration.
    """
    
    def __init__(self, system_learning_component=None):
        """
        Initialize the Continual Learning block.
        
        Args:
            system_learning_component: Optional reference to system-wide learning component
        """
        super().__init__("ContinualLearning")
        self.system_learning = system_learning_component
        
        # Learning rates for different system aspects
        self.learning_rates = {
            "memory": 0.05,      # Memory stability and connection adjustment
            "reasoning": 0.03,   # Reasoning rule adjustment
            "ethics": 0.07,      # Ethical principle weighting
            "action": 0.04       # Decision threshold adjustment
        }
        
        # Adaptive memory for tracking concepts
        self.adaptive_memory = {}  # Stores learned patterns and refinements
        
        # Track reasoning performance over time
        self.inference_history = {}  # Tracks reasoning performance
        
        # Track ethical evaluations over time
        self.ethics_sensitivity = {}  # Tracks sensitivity to different ethical concerns
        
        # Track action selection effectiveness
        self.action_feedback = {}  # Tracks action success/failure rates
        
        # Performance metrics across learning cycles
        self.performance_history = {
            "memory_accuracy": [],
            "reasoning_quality": [],
            "ethical_alignment": [],
            "action_success": []
        }
        
        # Reinforcement tracking
        self.reinforcement_cycles = 0
        self.last_reinforcement_time = time.time()
    
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """
        Process a chunk through continual learning adaptation.
        
        Args:
            chunk: The cognitive chunk to process
            
        Returns:
            Updated cognitive chunk with learning adjustments
        """
        # Extract data from all relevant processing stages
        memory_data = chunk.get_section_content("memory_section") or {}
        reasoning_data = chunk.get_section_content("reasoning_section") or {}
        ethics_data = chunk.get_section_content("ethics_king_section") or {}
        action_data = chunk.get_section_content("action_selection_section") or {}
        wave_data = chunk.get_section_content("wave_function_section") or {}
        
        # Learn from memory patterns
        memory_updates = self._update_memory_patterns(memory_data)
        
        # Adapt reasoning rules
        reasoning_refinements = self._refine_reasoning(reasoning_data)
        
        # Improve ethical sensitivity
        ethics_improvements = self._refine_ethics_model(ethics_data)
        
        # Optimize action selection
        action_tuning = self._adjust_action_weights(action_data)
        
        # Apply cross-component learning
        cross_learning = self._optimize_cross_block_interactions(chunk)
        
        # Update learning rates based on performance trends
        self._adapt_learning_rates()
        
        # Update the chunk with learning information
        learning_data = {
            "memory_updates": memory_updates,
            "reasoning_refinements": reasoning_refinements,
            "ethics_improvements": ethics_improvements,
            "action_tuning": action_tuning,
            "cross_learning": cross_learning,
            "learning_rates": self.learning_rates.copy(),
            "reinforcement_cycles": self.reinforcement_cycles,
            "resonance_patterns": {},
            "emergent_concepts_created": 0,
            "processed_timestamp": time.time()
        }
        
        chunk.update_section("continual_learning_section", learning_data)
        
        # Log the learning process
        self.log_process(chunk, "learning_cycle", {
            "memory_updates": len(memory_updates),
            "reasoning_refinements": len(reasoning_refinements),
            "ethics_improvements": len(ethics_improvements),
            "action_tuning": len(action_tuning)
        })
        
        # Increment reinforcement cycle counter
        self.reinforcement_cycles += 1
        self.last_reinforcement_time = time.time()
        
        # If system learning component exists, apply feedback
        if self.system_learning:
            # Estimate quality metrics for feedback
            quality_estimates = self._estimate_processing_quality(chunk)
            
            # Apply system-wide learning
            self.system_learning.apply_feedback(quality_estimates, context={"chunk": chunk})

            # Wire bidirectional bridge hooks into the end of each learning cycle
            resonance_info = {}
            emergent_concepts_created = 0

            bridge = self._get_memory_bridge()
            if bridge is None:
                warning_message = "memory_bridge not available in system learning context; skipping bridge updates"
                logger.warning(warning_message)
                self.log_process(chunk, "warning", {"message": warning_message})
            else:
                try:
                    current_time = time.time()
                    cognitive_state, ethical_state = self._derive_bridge_states_from_wave(bridge, wave_data)
                    input_concepts = self._extract_bridge_input_concepts(memory_data)

                    bridge.bidirectional_update(
                        cognitive_state=cognitive_state,
                        ethical_state=ethical_state,
                        input_concepts=input_concepts,
                        t=current_time
                    )

                    wave_magnitude = self._safe_float(wave_data.get("magnitude", 0.0), 0.0)
                    if wave_magnitude > 0.6:
                        wave_output = bridge.ecwf_core.compute_ecwf(cognitive_state, ethical_state, current_time)
                        emergent_concepts = bridge.detect_and_create_emergent_concepts(wave_output, current_time)
                        emergent_concepts_created = len(emergent_concepts)

                    resonance_info = bridge.get_resonance_info() or {}
                except Exception as exc:
                    warning_message = f"bridge update failed in continual learning cycle: {exc}"
                    logger.warning(warning_message)
                    self.log_process(chunk, "warning", {"message": warning_message})

            updated_learning_data = chunk.get_section_content("continual_learning_section") or {}
            updated_learning_data["resonance_patterns"] = resonance_info
            updated_learning_data["emergent_concepts_created"] = emergent_concepts_created
            chunk.update_section("continual_learning_section", updated_learning_data)
        
        return chunk

    def _get_memory_bridge(self):
        """Safely resolve the memory bridge from system-learning context."""
        if not self.system_learning:
            return None

        if hasattr(self.system_learning, "unified_system"):
            unified_system = getattr(self.system_learning, "unified_system", None)
            if unified_system is not None and hasattr(unified_system, "memory_bridge"):
                return getattr(unified_system, "memory_bridge", None)

        if hasattr(self.system_learning, "system"):
            system_obj = getattr(self.system_learning, "system", None)
            if system_obj is not None and hasattr(system_obj, "memory_bridge"):
                return getattr(system_obj, "memory_bridge", None)

        return getattr(self.system_learning, "memory_bridge", None)

    def _derive_bridge_states_from_wave(self, bridge, wave_data: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        """Build bridge state tensors from wave-function section values."""
        magnitude = self._safe_float(wave_data.get("magnitude", 0.0), 0.0)
        phase = self._safe_float(wave_data.get("phase", 0.0), 0.0)
        entropy = self._safe_float(wave_data.get("entropy", 0.5), 0.5)

        cognitive_dims = max(1, int(getattr(bridge.ecwf_core, "num_cognitive_dims", 1)))
        ethical_dims = max(1, int(getattr(bridge.ecwf_core, "num_ethical_dims", 1)))

        cognitive_value = magnitude * np.cos(phase)
        ethical_value = np.clip(1.0 - entropy, 0.0, 1.0)

        cognitive_state = np.full((1, 1, cognitive_dims), cognitive_value, dtype=float)
        ethical_state = np.full((1, 1, ethical_dims), ethical_value, dtype=float)

        return cognitive_state, ethical_state

    def _extract_bridge_input_concepts(self, memory_data: Dict[str, Any]) -> List[str]:
        """Collect concepts to drive memory→ECWF updates."""
        concepts: List[str] = []

        retrieved = memory_data.get("retrieved_concepts", [])
        if isinstance(retrieved, list):
            for concept in retrieved:
                if concept is not None:
                    concepts.append(str(concept))

        activated = memory_data.get("activated_concepts", {})
        if isinstance(activated, dict):
            concepts.extend(str(key) for key in activated.keys())
        elif isinstance(activated, list):
            for concept in activated:
                if concept is not None:
                    concepts.append(str(concept))

        deduped = []
        seen = set()
        for concept in concepts:
            if concept not in seen:
                seen.add(concept)
                deduped.append(concept)

        return deduped

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Coerce values to float safely."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    
    def _update_memory_patterns(self, memory_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Learn from memory activation patterns to optimize future retrievals.
        
        Args:
            memory_data: Memory section data from chunk
            
        Returns:
            List of memory updates performed
        """
        updates = []
        
        # Extract concepts from memory data
        retrieved_concepts = memory_data.get("retrieved_concepts", [])
        activated_concepts = memory_data.get("activated_concepts", [])
        all_concepts = set()
        
        # Process retrieved concepts
        for item in retrieved_concepts:
            if isinstance(item, tuple) and len(item) >= 2:
                concept, relevance = item
                all_concepts.add(concept)
            elif isinstance(item, str):
                all_concepts.add(item)
        
        # Add activated concepts
        all_concepts.update(activated_concepts)
        
        # Process each concept for memory updates
        for concept in all_concepts:
            # Initialize adaptive memory entry if not exists
            if concept not in self.adaptive_memory:
                self.adaptive_memory[concept] = {
                    "stability": 0.5,
                    "retrieval_count": 0,
                    "connections": [],
                    "last_accessed": time.time()
                }
            
            # Update concept statistics
            self.adaptive_memory[concept]["retrieval_count"] += 1
            self.adaptive_memory[concept]["last_accessed"] = time.time()
            
            # Calculate stability adjustment
            current_stability = self.adaptive_memory[concept]["stability"]
            
            # Get activation from memory data if available
            activation = 0.5  # Default activation
            if concept in activated_concepts:
                if isinstance(activated_concepts, dict):
                    activation = activated_concepts[concept]
                else:
                    activation = 0.7  # Default activation when in list but not dict
            
            # Adjust stability based on activation and learning rate
            stability_delta = self.learning_rates["memory"] * activation
            new_stability = min(1.0, current_stability + stability_delta)
            self.adaptive_memory[concept]["stability"] = new_stability
            
            # Connect related concepts
            for other_concept in all_concepts:
                if other_concept != concept and other_concept not in [conn[0] for conn in self.adaptive_memory[concept]["connections"]]:
                    # New connection with initial weight
                    self.adaptive_memory[concept]["connections"].append((other_concept, 0.3))
                    
            # Record update
            updates.append({
                "concept": concept,
                "old_stability": current_stability,
                "new_stability": new_stability,
                "retrieval_count": self.adaptive_memory[concept]["retrieval_count"]
            })
        
        # Apply memory decay for unused concepts
        self._prune_memory()
        
        return updates
    
    def _prune_memory(self) -> int:
        """Prunes memory by decaying unused concepts."""
        current_time = time.time()
        threshold_time = current_time - (60 * 60 * 24 * 7)  # One week ago
        
        concepts_to_remove = []
        for concept, data in self.adaptive_memory.items():
            # Skip special records
            if isinstance(data, list):
                continue
                
            # Check if concept has low stability and hasn't been accessed recently
            if data["stability"] < 0.3 and data.get("last_accessed", 0) < threshold_time:
                concepts_to_remove.append(concept)
        
        # Remove weak concepts
        for concept in concepts_to_remove:
            del self.adaptive_memory[concept]
            
        return len(concepts_to_remove)
    
    def _refine_reasoning(self, reasoning_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Refine reasoning rules based on past inference performance.
        
        Args:
            reasoning_data: Reasoning section data from chunk
            
        Returns:
            List of reasoning refinements performed
        """
        refinements = []
        
        # Extract inference information
        inferences = reasoning_data.get("inferences", {})
        confidence_score = reasoning_data.get("confidence_score", 0.5)
        
        # Process each inference type
        for inference_type, inference_list in inferences.items():
            # Initialize inference type tracking if not exists
            if inference_type not in self.inference_history:
                self.inference_history[inference_type] = {
                    "count": 0,
                    "avg_confidence": 0.5,
                    "success_rate": 0.5,
                    "rules": {}
                }
            
            # Update inference type statistics
            self.inference_history[inference_type]["count"] += 1
            
            # Update average confidence using exponential moving average
            old_avg = self.inference_history[inference_type]["avg_confidence"]
            new_avg = old_avg * 0.9 + confidence_score * 0.1  # 90% old, 10% new
            self.inference_history[inference_type]["avg_confidence"] = new_avg
            
            # Process individual inferences
            for inference in inference_list:
                rule_key = self._get_rule_key(inference)
                
                # Initialize rule tracking if not exists
                if rule_key not in self.inference_history[inference_type]["rules"]:
                    self.inference_history[inference_type]["rules"][rule_key] = {
                        "count": 0,
                        "confidence": 0.5
                    }
                
                # Update rule statistics
                rule_data = self.inference_history[inference_type]["rules"][rule_key]
                rule_data["count"] += 1
                
                # Update rule confidence
                old_conf = rule_data["confidence"]
                new_conf = old_conf * 0.9 + confidence_score * 0.1
                rule_data["confidence"] = new_conf
                
                # Record refinement
                refinements.append({
                    "inference_type": inference_type,
                    "rule_key": rule_key,
                    "old_confidence": old_conf,
                    "new_confidence": new_conf,
                    "count": rule_data["count"]
                })
        
        return refinements
    
    def _get_rule_key(self, inference: Any) -> str:
        """
        Creates a simplified key from an inference string for tracking purposes.
        
        Args:
            inference: Inference to create a key for
            
        Returns:
            String key for tracking the inference rule
        """
        # Remove stop words and punctuation, lowercase, and take first 5 words
        if isinstance(inference, str):
            words = inference.lower().translate(str.maketrans('', '', '.,;:!?')).split()
            significant_words = [word for word in words if len(word) > 3][:5]
            return "_".join(significant_words) if significant_words else inference[:20]
        return str(inference)[:20]
    
    def _refine_ethics_model(self, ethics_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Learns from ethical considerations to improve system behavior.
        
        Args:
            ethics_data: Ethics section data from chunk
            
        Returns:
            List of ethical sensitivity adjustments
        """
        improvements = []
        
        # Extract ethical evaluation data
        evaluation = ethics_data.get("evaluation", {})
        ethical_concerns = evaluation.get("concerns", [])
        principle_scores = evaluation.get("principle_scores", {})
        overall_assessment = evaluation.get("status", "acceptable")
        
        # Process each ethical concern
        for concern in ethical_concerns:
            if concern not in self.ethics_sensitivity:
                self.ethics_sensitivity[concern] = {
                    "occurrence_count": 0,
                    "sensitivity_level": 0.5
                }
            
            # Update ethical concern statistics
            self.ethics_sensitivity[concern]["occurrence_count"] += 1
            
            # Adjust sensitivity based on overall assessment
            old_sensitivity = self.ethics_sensitivity[concern]["sensitivity_level"]
            new_sensitivity = old_sensitivity
            
            if overall_assessment == "review_needed":
                # Increase sensitivity for concerning situations
                new_sensitivity = min(1.0, old_sensitivity + self.learning_rates["ethics"])
            elif overall_assessment == "excellent":
                # Slightly decrease sensitivity if we're being too cautious
                new_sensitivity = max(0.3, old_sensitivity - self.learning_rates["ethics"] * 0.5)
            
            self.ethics_sensitivity[concern]["sensitivity_level"] = new_sensitivity
            
            # Record adjustment
            improvements.append({
                "concern": concern,
                "old_sensitivity": old_sensitivity,
                "new_sensitivity": new_sensitivity,
                "occurrence_count": self.ethics_sensitivity[concern]["occurrence_count"]
            })
        
        # Process principle scores if present
        for principle, score in principle_scores.items():
            # Record principle refinement
            improvements.append({
                "principle": principle,
                "score": score,
                "refinement_type": "principle_score_tracking"
            })
        
        return improvements
    
    def _adjust_action_weights(self, action_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Refines action selection by learning from past successes and failures.
        
        Args:
            action_data: Action selection data from chunk
            
        Returns:
            List of action weight adjustments
        """
        adjustments = []
        
        # Extract action information
        selected_action = action_data.get("selected_action", "")
        action_confidence = action_data.get("action_confidence", 0.5)
        all_action_scores = action_data.get("all_action_scores", {})
        
        if not selected_action:
            return adjustments
        
        # Initialize action tracking if needed
        if selected_action not in self.action_feedback:
            self.action_feedback[selected_action] = {
                "selection_count": 0,
                "confidence_history": [],
                "success_rate": 0.5
            }
        
        # Update action statistics
        self.action_feedback[selected_action]["selection_count"] += 1
        self.action_feedback[selected_action]["confidence_history"].append(action_confidence)
        
        # Calculate average confidence
        confidence_history = self.action_feedback[selected_action]["confidence_history"]
        avg_confidence = sum(confidence_history[-10:]) / min(10, len(confidence_history))
        
        # Record adjustment for selected action
        adjustments.append({
            "action": selected_action,
            "selection_count": self.action_feedback[selected_action]["selection_count"],
            "avg_confidence": avg_confidence
        })
        
        # Track non-selected actions
        for action, score in all_action_scores.items():
            if action != selected_action:
                if action not in self.action_feedback:
                    self.action_feedback[action] = {
                        "selection_count": 0,
                        "confidence_history": [],
                        "non_selection_scores": []
                    }
                
                # Track this non-selection instance
                if "non_selection_scores" not in self.action_feedback[action]:
                    self.action_feedback[action]["non_selection_scores"] = []
                    
                self.action_feedback[action]["non_selection_scores"].append(score)
                
                adjustments.append({
                    "action": action,
                    "non_selection_score": score,
                    "tracking_type": "alternative_action"
                })
        
        return adjustments
    
    def _optimize_cross_block_interactions(self, chunk: CognitiveChunk) -> Dict[str, Any]:
        """
        Uses reinforcement learning to optimize how blocks interact with each other.
        
        Args:
            chunk: Cognitive chunk being processed
            
        Returns:
            Dict with cross-block optimization information
        """
        # Extract internal communication data
        comm_data = chunk.get_section_content("internal_communication_section") or {}
        cross_block_insights = comm_data.get("cross_block_insights", [])
        
        # Track which block combinations produce useful insights
        block_pair_performance = {}
        learning_rate_adjustments = {}
        
        # Analyze cross-block insights
        for insight in cross_block_insights:
            source_blocks = insight.get("source_blocks", [])
            importance = insight.get("importance", 0.5)
            
            # Track performance for block pairs
            if len(source_blocks) >= 2:
                # Create a stable key from source blocks
                block_pair = "_".join(sorted(source_blocks))
                
                if block_pair not in block_pair_performance:
                    block_pair_performance[block_pair] = {
                        "count": 0,
                        "avg_importance": 0.5
                    }
                
                # Update statistics
                block_pair_performance[block_pair]["count"] += 1
                
                # Update average importance
                old_avg = block_pair_performance[block_pair]["avg_importance"]
                new_avg = old_avg * 0.8 + importance * 0.2
                block_pair_performance[block_pair]["avg_importance"] = new_avg
            
            # Adjust learning rates for related areas
            for block in source_blocks:
                # Map blocks to learning rate domains
                domain = self._map_block_to_learning_domain(block)
                
                if domain in self.learning_rates:
                    # High importance insights lead to increased learning rates
                    if importance > 0.7:
                        old_rate = self.learning_rates[domain]
                        new_rate = min(0.15, old_rate * 1.05)  # 5% increase, max 0.15
                        self.learning_rates[domain] = new_rate
                        
                        learning_rate_adjustments[domain] = {
                            "old_rate": old_rate,
                            "new_rate": new_rate,
                            "reason": f"High importance insight from {block}"
                        }
        
        return {
            "block_pair_insights": len(block_pair_performance),
            "learning_rate_adjustments": learning_rate_adjustments
        }
    
    def _map_block_to_learning_domain(self, block_name: str) -> str:
        """Maps block names to learning rate domains."""
        # Mapping from blocks to learning domains
        domain_mapping = {
            "MemoryStorage": "memory",
            "SensoryInput": "memory",
            "PatternRecognition": "memory",
            "ReasoningPlanning": "reasoning",
            "InternalCommunication": "reasoning",
            "EthicsValues": "ethics",
            "ActionSelection": "action",
            "LanguageProcessing": "reasoning"
        }
        
        return domain_mapping.get(block_name, "memory")
    
    def _adapt_learning_rates(self):
        """Automatically adapt learning rates based on performance trends."""
        # Calculate time since last reinforcement
        current_time = time.time()
        time_since_last = current_time - self.last_reinforcement_time
        
        # If it's been a while since last reinforcement, normalize learning rates
        if time_since_last > 3600:  # 1 hour
            # Baseline values for learning rates
            baseline_values = {
                "memory": 0.05,
                "reasoning": 0.03,
                "ethics": 0.07,
                "action": 0.04
            }
            
            # Gradually return to baseline values
            for domain in self.learning_rates:
                current_rate = self.learning_rates[domain]
                baseline = baseline_values.get(domain, 0.05)
                
                # Move 10% toward baseline
                self.learning_rates[domain] = current_rate * 0.9 + baseline * 0.1
    
    def _estimate_processing_quality(self, chunk: CognitiveChunk) -> Dict[str, float]:
        """
        Estimate the quality of processing for system feedback.
        
        Args:
            chunk: The processed cognitive chunk
            
        Returns:
            Dictionary of quality estimates
        """
        # Extract relevant data
        ethics_data = chunk.get_section_content("ethics_king_section") or {}
        evaluation = ethics_data.get("evaluation", {})
        overall_score = evaluation.get("overall_score", 0.5)
        
        # Get reasoning confidence
        reasoning_data = chunk.get_section_content("reasoning_section") or {}
        reasoning_confidence = reasoning_data.get("confidence_score", 0.5)
        
        # Get action confidence
        action_data = chunk.get_section_content("action_selection_section") or {}
        action_confidence = action_data.get("action_confidence", 0.5)
        
        # Combine scores for overall response quality estimate
        response_quality = (overall_score + action_confidence + reasoning_confidence) / 3
        
        return {
            "response_quality": response_quality,
            "ethical_alignment": overall_score,
            "reasoning_quality": reasoning_confidence,
            "action_quality": action_confidence
        }


    def to_state_dict(self) -> Dict[str, Any]:
        """Serialize continual-learning state for persistence."""
        return {
            "version": 1,
            "adaptive_memory": dict(self.adaptive_memory),
            "learning_rates": dict(self.learning_rates),
            "reinforcement_cycles": int(self.reinforcement_cycles),
        }

    def from_state_dict(self, state: Dict[str, Any]) -> None:
        """Restore continual-learning state with safe defaults."""
        state = state or {}
        self.adaptive_memory = dict(state.get("adaptive_memory", self.adaptive_memory) or self.adaptive_memory)

        loaded_rates = state.get("learning_rates", {}) or {}
        if isinstance(loaded_rates, dict) and loaded_rates:
            for key, value in loaded_rates.items():
                if key in self.learning_rates:
                    try:
                        self.learning_rates[key] = float(value)
                    except (TypeError, ValueError):
                        pass

        self.reinforcement_cycles = int(state.get("reinforcement_cycles", self.reinforcement_cycles))
