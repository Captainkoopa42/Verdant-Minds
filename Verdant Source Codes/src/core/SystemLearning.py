import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Any, Set

from src.core.cognitive_chunk import CognitiveChunk

class SystemWideLearning:
    """
    System-wide learning mechanisms for the Unified Synthetic Mind.
    
    This component implements continuous learning capabilities that span across
    all other system components, enabling holistic adaptation and improvement
    based on experience and feedback.
    """
    
    def __init__(self, unified_system):
        """
        Initialize the system-wide learning component.
        
        Args:
            unified_system: Reference to the main Unified Synthetic Mind system
        """
        self.system = unified_system
        
        # Learning rates for different aspects of the system
        self.learning_rates = {
            "memory": 0.05,      # Memory stability and connection adjustment
            "ethical": 0.07,     # Ethical parameter adaptation
            "cognitive": 0.03,   # Cognitive processing refinement
            "action": 0.04       # Decision-making optimization
        }
        
        # Track learning events and performance trends
        self.learning_history = []
        self.performance_trends = {
            "memory_accuracy": [],
            "ethical_alignment": [],
            "reasoning_quality": [],
            "decision_confidence": []
        }
        
        # Learning state
        self.total_learning_cycles = 0
        self.last_learning_time = time.time()

        # Glass transition temperature parameters
        self.t_glass = 0.5  # Initial glass transition temperature
        self.phase_state = "balanced"  # Current cognitive phase state

    # [FIXED]
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Stub processing method for learning component."""
        print(f"SystemWideLearning processing chunk {chunk.chunk_id}")
        return chunk
    
    def apply_feedback(self, feedback: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Apply external feedback to improve system-wide performance.
        
        Args:
            feedback: Dictionary with feedback information
                {
                    "response_quality": float 0-1,
                    "ethical_alignment": float 0-1,
                    "reasoning_quality": float 0-1,
                    "specific_feedback": str
                }
            context: Optional context information including processing details
            
        Returns:
            Dict with learning results
        """
        # Extract learning signals from feedback
        learning_signals = self._extract_learning_signals(feedback, context)
        
        # Apply learning to different system components
        memory_adjustments = self._adjust_memory(learning_signals)
        wave_adjustments = self._adjust_wave_parameters(learning_signals)
        kings_adjustments = self._adjust_kings_parameters(learning_signals)
        block_adjustments = self._adjust_block_parameters(learning_signals)
        
        # Update glass transition temperature based on feedback
        self._update_glass_transition(feedback)
        
        # Record learning event
        learning_event = {
            "timestamp": time.time(),
            "feedback": feedback,
            "learning_signals": learning_signals,
            "adjustments": {
                "memory": memory_adjustments,
                "wave": wave_adjustments,
                "kings": kings_adjustments,
                "blocks": block_adjustments
            },
            "learning_rates": self.learning_rates.copy(),
            "t_glass": self.t_glass,
            "phase_state": self.phase_state
        }
        
        self.learning_history.append(learning_event)
        self.total_learning_cycles += 1
        self.last_learning_time = time.time()
        
        # Limit history size to prevent memory issues
        if len(self.learning_history) > 1000:
            self.learning_history = self.learning_history[-1000:]
        
        # Update performance trends
        self._update_performance_trends(feedback)
        
        return learning_event
    
    def _extract_learning_signals(self, feedback: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract specific learning signals from feedback.
        
        Args:
            feedback: Feedback dictionary
            context: Optional context information
            
        Returns:
            Dictionary of learning signals for different system components
        """
        signals = {
            "memory_reinforcement": [],    # Concepts to strengthen
            "memory_correction": [],       # Concepts to weaken
            "ethical_adjustment": 0.0,     # Ethical parameter adjustment (-1 to 1)
            "reasoning_adjustment": 0.0,   # Reasoning parameter adjustment (-1 to 1)
            "action_adjustment": 0.0       # Action selection adjustment (-1 to 1)
        }
        
        # Get quality signals from feedback
        response_quality = feedback.get("response_quality", 0.5)
        ethical_alignment = feedback.get("ethical_alignment", 0.5)
        reasoning_quality = feedback.get("reasoning_quality", 0.5)
        specific_feedback = feedback.get("specific_feedback", "")
        
        # Convert to adjustment signals (-1 to 1 scale)
        signals["ethical_adjustment"] = (ethical_alignment - 0.5) * 2
        signals["reasoning_adjustment"] = (reasoning_quality - 0.5) * 2
        signals["action_adjustment"] = (response_quality - 0.5) * 2
        
        # Extract concepts for memory adjustments if context available
        if context and "activated_concepts" in context:
            activated_concepts = context["activated_concepts"]
            
            # Reinforce concepts mentioned in positive feedback
            if response_quality > 0.6:
                for concept in activated_concepts:
                    if concept.lower() in specific_feedback.lower():
                        signals["memory_reinforcement"].append(concept)
            
            # Correct concepts mentioned in negative feedback
            if response_quality < 0.4:
                for concept in activated_concepts:
                    if concept.lower() in specific_feedback.lower():
                        signals["memory_correction"].append(concept)
        
        return signals
    
    def _adjust_memory(self, learning_signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adjust memory components based on learning signals.
        
        Args:
            learning_signals: Dictionary of learning signals
            
        Returns:
            Dictionary describing memory adjustments
        """
        adjustments = {
            "reinforced_concepts": [],
            "corrected_concepts": [],
            "new_connections": []
        }
        
        # Skip if no memory web available
        if not hasattr(self.system, "memory_web"):
            return adjustments
        
        memory_web = self.system.memory_web
        
        # Reinforce positively mentioned concepts
        for concept in learning_signals["memory_reinforcement"]:
            if concept in memory_web.memory_store:
                old_stability = memory_web.memory_store[concept]["stability"]
                new_stability = min(1.0, old_stability + self.learning_rates["memory"])
                memory_web.memory_store[concept]["stability"] = new_stability
                
                adjustments["reinforced_concepts"].append({
                    "concept": concept,
                    "old_stability": old_stability,
                    "new_stability": new_stability
                })
        
        # Reduce stability of negatively mentioned concepts
        for concept in learning_signals["memory_correction"]:
            if concept in memory_web.memory_store:
                old_stability = memory_web.memory_store[concept]["stability"]
                new_stability = max(0.1, old_stability - self.learning_rates["memory"])
                memory_web.memory_store[concept]["stability"] = new_stability
                
                adjustments["corrected_concepts"].append({
                    "concept": concept,
                    "old_stability": old_stability,
                    "new_stability": new_stability
                })
        
        # Create or strengthen connections between reinforced concepts
        reinforced = learning_signals["memory_reinforcement"]
        if len(reinforced) >= 2:
            for i in range(len(reinforced)):
                for j in range(i+1, len(reinforced)):
                    if reinforced[i] in memory_web.memory_store and reinforced[j] in memory_web.memory_store:
                        new_connection = memory_web.connect_thoughts(
                            reinforced[i], 
                            reinforced[j], 
                            initial_weight=self.learning_rates["memory"] * 10
                        )
                        
                        if new_connection:
                            adjustments["new_connections"].append({
                                "source": reinforced[i],
                                "target": reinforced[j]
                            })
        
        return adjustments
    
    def _adjust_wave_parameters(self, learning_signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adjust ECWF wave function parameters based on learning signals.
        
        Args:
            learning_signals: Dictionary of learning signals
            
        Returns:
            Dictionary describing wave parameter adjustments
        """
        adjustments = {
            "parameter_updates": [],
            "dimension_impacts": {}
        }
        
        # Skip if no ECWF core available
        if not hasattr(self.system, "ecwf_core"):
            return adjustments
        
        ecwf_core = self.system.ecwf_core

        # Extract adjustment signals
        ethical_adjustment = learning_signals["ethical_adjustment"]
        reasoning_adjustment = learning_signals["reasoning_adjustment"]

        # [FIXED] Safely initialize gradients
        chunk = learning_signals.get("chunk")
        ethical_gradient = None
        if isinstance(chunk, CognitiveChunk):
            ethical_gradient = chunk.get_section_content("ethics", {}).get("gradient", None)
        cognitive_gradient = None
        
        # Scale adjustments by learning rates
        ethical_factor = ethical_adjustment * self.learning_rates["ethical"]
        reasoning_factor = reasoning_adjustment * self.learning_rates["cognitive"]
        
        # Apply small adjustments to prevent instability
        if abs(ethical_factor) > 0.001:
            # Create gradient vectors for ethical dimensions
            ethical_gradient = np.random.normal(
                loc=ethical_factor,
                scale=abs(ethical_factor) * 0.2,
                size=ecwf_core.num_ethical_dims
            )
            
            # Apply gradient to ethical wave numbers
            for i in range(ecwf_core.num_facets):
                old_values = ecwf_core.m[i].copy()
                ecwf_core.m[i] += ethical_gradient * 0.01
                
                adjustments["parameter_updates"].append({
                    "type": "ethical_wave_numbers",
                    "facet": i,
                    "average_change": np.mean(np.abs(ecwf_core.m[i] - old_values))
                })
        
        if abs(reasoning_factor) > 0.001:
            # Create gradient vectors for cognitive dimensions
            cognitive_gradient = np.random.normal(
                loc=reasoning_factor,
                scale=abs(reasoning_factor) * 0.2,
                size=ecwf_core.num_cognitive_dims
            )
            
            # Apply gradient to cognitive wave numbers
            for i in range(ecwf_core.num_facets):
                old_values = ecwf_core.k[i].copy()
                ecwf_core.k[i] += cognitive_gradient * 0.01
                
                adjustments["parameter_updates"].append({
                    "type": "cognitive_wave_numbers",
                    "facet": i,
                    "average_change": np.mean(np.abs(ecwf_core.k[i] - old_values))
                })
        
        # Track which dimensions were most affected
        if hasattr(ecwf_core, "dimension_meanings"):
            if cognitive_gradient is not None:
                for i, impact in enumerate(np.abs(cognitive_gradient)):
                    dim_name = f"C{i+1}"
                    if dim_name in ecwf_core.dimension_meanings:
                        dim_meaning = ecwf_core.dimension_meanings[dim_name]
                        adjustments["dimension_impacts"][dim_meaning] = float(impact)

            if ethical_gradient is not None:
                for i, impact in enumerate(np.abs(ethical_gradient)):
                    dim_name = f"E{i+1}"
                    if dim_name in ecwf_core.dimension_meanings:
                        dim_meaning = ecwf_core.dimension_meanings[dim_name]
                        adjustments["dimension_impacts"][dim_meaning] = float(impact)
        
        return adjustments
    
    def _adjust_kings_parameters(self, learning_signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adjust Three Kings governance parameters based on learning signals.
        
        Args:
            learning_signals: Dictionary of learning signals
            
        Returns:
            Dictionary describing king parameter adjustments
        """
        adjustments = {
            "ethics_king": {},
            "forefront_king": {},
            "data_king": {}
        }
        
        # Skip if no kings available
        if not hasattr(self.system, "three_kings_layer"):
            return adjustments
        
        kings_layer = self.system.three_kings_layer
        
        # Extract adjustment signals
        ethical_adjustment = learning_signals["ethical_adjustment"]
        reasoning_adjustment = learning_signals["reasoning_adjustment"]
        action_adjustment = learning_signals["action_adjustment"]
        
        # Adjust Ethics King parameters
        if hasattr(kings_layer, "ethics_king") and abs(ethical_adjustment) > 0.001:
            ethics_king = kings_layer.ethics_king
            
            # Adjust ethical sensitivity threshold
            if hasattr(ethics_king, "ethical_sensitivity"):
                old_sensitivity = ethics_king.ethical_sensitivity
                new_sensitivity = max(0.4, min(0.9, old_sensitivity + ethical_adjustment * 0.01))
                ethics_king.ethical_sensitivity = new_sensitivity
                
                adjustments["ethics_king"]["sensitivity"] = {
                    "old": old_sensitivity,
                    "new": new_sensitivity
                }
            
            # Adjust principle weights if available
            if hasattr(ethics_king, "principle_weights"):
                # Selectively adjust weights based on feedback direction
                principle_adjustments = {}
                
                for principle, weight in ethics_king.principle_weights.items():
                    # Higher ethical adjustment -> strengthen all principles
                    # Lower ethical adjustment -> normalize principle weights
                    if ethical_adjustment > 0:
                        new_weight = min(1.5, weight * (1 + ethical_adjustment * 0.05))
                    else:
                        new_weight = weight * 0.95 + 1.0 * 0.05  # Move toward 1.0
                    
                    ethics_king.principle_weights[principle] = new_weight
                    principle_adjustments[principle] = {"old": weight, "new": new_weight}
                
                adjustments["ethics_king"]["principle_weights"] = principle_adjustments
        
        # Adjust Forefront King parameters
        if hasattr(kings_layer, "forefront_king") and abs(reasoning_adjustment) > 0.001:
            forefront_king = kings_layer.forefront_king
            
            # Adjust decision threshold
            if hasattr(forefront_king, "decision_threshold"):
                old_threshold = forefront_king.decision_threshold
                
                # Better reasoning -> can be more decisive (lower threshold)
                # Worse reasoning -> be more cautious (higher threshold)
                new_threshold = max(0.4, min(0.9, old_threshold - reasoning_adjustment * 0.02))
                forefront_king.decision_threshold = new_threshold
                
                adjustments["forefront_king"]["threshold"] = {
                    "old": old_threshold,
                    "new": new_threshold
                }
        
        # Adjust Data King parameters
        if hasattr(kings_layer, "data_king") and abs(action_adjustment) > 0.001:
            data_king = kings_layer.data_king
            
            # Adjust information quality threshold
            if hasattr(data_king, "information_quality_threshold"):
                old_threshold = data_king.information_quality_threshold
                
                # Better actions -> can be more permissive with information
                # Worse actions -> be more strict with information quality
                new_threshold = max(0.3, min(0.8, old_threshold - action_adjustment * 0.01))
                data_king.information_quality_threshold = new_threshold
                
                adjustments["data_king"]["quality_threshold"] = {
                    "old": old_threshold,
                    "new": new_threshold
                }
        
        return adjustments
    
    def _adjust_block_parameters(self, learning_signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adjust processing block parameters based on learning signals.
        
        Args:
            learning_signals: Dictionary of learning signals
            
        Returns:
            Dictionary describing block parameter adjustments
        """
        adjustments = {
            "learning_rates": {},
            "blocks": {}
        }
        
        # Extract adjustment signals
        action_adjustment = learning_signals["action_adjustment"]
        
        # Adjust system-wide learning rates
        for domain, rate in self.learning_rates.items():
            # Positive feedback -> slightly increase learning rates
            # Negative feedback -> slightly decrease learning rates
            if action_adjustment > 0:
                new_rate = min(0.15, rate * (1 + 0.05 * action_adjustment))
            else:
                new_rate = max(0.01, rate * (1 + 0.05 * action_adjustment))
            
            adjustments["learning_rates"][domain] = {
                "old": rate,
                "new": new_rate
            }
            
            self.learning_rates[domain] = new_rate
        
        # Adjust individual block parameters if continual learning block exists
        if hasattr(self.system, "blocks") and "ContinualLearning" in self.system.blocks:
            cl_block = self.system.blocks["ContinualLearning"]
            
            # If the block has learning rates, update them
            if hasattr(cl_block, "learning_rates"):
                old_rates = cl_block.learning_rates.copy()
                
                # Positive feedback -> slightly increase learning rates
                # Negative feedback -> slightly decrease learning rates
                if action_adjustment > 0:
                    for key in cl_block.learning_rates:
                        cl_block.learning_rates[key] = min(
                            0.15, 
                            cl_block.learning_rates[key] * (1 + 0.05 * action_adjustment)
                        )
                else:
                    for key in cl_block.learning_rates:
                        cl_block.learning_rates[key] = max(
                            0.01, 
                            cl_block.learning_rates[key] * (1 + 0.05 * action_adjustment)
                        )
                
                adjustments["blocks"]["ContinualLearning"] = {
                    "learning_rates": {
                        "old": old_rates,
                        "new": cl_block.learning_rates.copy()
                    }
                }
        
        return adjustments
    
    def _update_glass_transition(self, feedback: Dict[str, Any]):
        """
        Update the system's glass transition temperature (T_g) based on feedback.
        
        Args:
            feedback: Feedback dictionary
        """
        # Extract relevant metrics
        response_quality = feedback.get("response_quality", 0.5)
        reasoning_quality = feedback.get("reasoning_quality", 0.5)
        
        # Calculate adjustment factor
        # Higher quality -> push toward more fluid state (lower T_g)
        # Lower quality -> push toward more rigid state (higher T_g)
        quality_factor = (response_quality + reasoning_quality) / 2
        adjustment = (quality_factor - 0.5) * 0.05  # Small adjustment
        
        # Apply adjustment with smoothing
        self.t_glass = self.t_glass * 0.9 - adjustment * 0.1
        
        # Ensure T_g stays in valid range
        self.t_glass = max(0.1, min(0.9, self.t_glass))
        
        # Update phase state descriptor
        if self.t_glass < 0.4:
            self.phase_state = "fluid"     # Low T_g = more emergent cognition
        elif self.t_glass > 0.6:
            self.phase_state = "rigid"     # High T_g = more structured cognition
        else:
            self.phase_state = "balanced"  # Balanced state
    
    def _update_performance_trends(self, feedback: Dict[str, Any]):
        """
        Update performance trend tracking.
        
        Args:
            feedback: Feedback dictionary
        """
        # Extract metrics
        memory_accuracy = feedback.get("memory_accuracy", feedback.get("response_quality", 0.5))
        ethical_alignment = feedback.get("ethical_alignment", 0.5)
        reasoning_quality = feedback.get("reasoning_quality", 0.5)
        decision_confidence = feedback.get("decision_confidence", feedback.get("response_quality", 0.5))
        
        # Add to trends
        self.performance_trends["memory_accuracy"].append(memory_accuracy)
        self.performance_trends["ethical_alignment"].append(ethical_alignment)
        self.performance_trends["reasoning_quality"].append(reasoning_quality)
        self.performance_trends["decision_confidence"].append(decision_confidence)
        
        # Limit trend history
        max_history = 100
        for key in self.performance_trends:
            if len(self.performance_trends[key]) > max_history:
                self.performance_trends[key] = self.performance_trends[key][-max_history:]
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the learning process.
        
        Returns:
            Dictionary with learning statistics
        """
        # Calculate trend metrics
        trends = {}
        for key, values in self.performance_trends.items():
            if values:
                trends[key] = {
                    "current": values[-1],
                    "average": sum(values) / len(values),
                    "trend": self._calculate_trend(values[-min(10, len(values)):])
                }
            else:
                trends[key] = {
                    "current": 0.5,
                    "average": 0.5,
                    "trend": 0.0
                }
        
        # Calculate learning cycles per hour
        current_time = time.time()
        hours_running = max(0.001, (current_time - self.learning_history[0]["timestamp"] if self.learning_history else current_time) / 3600)
        learning_rate = self.total_learning_cycles / hours_running
        
        return {
            "total_learning_cycles": self.total_learning_cycles,
            "learning_cycles_per_hour": learning_rate,
            "last_learning_time": self.last_learning_time,
            "current_learning_rates": self.learning_rates,
            "glass_transition_temperature": self.t_glass,
            "cognitive_phase_state": self.phase_state,
            "performance_trends": trends
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calculate the trend direction and magnitude from a list of values.
        
        Args:
            values: List of recent values
            
        Returns:
            Trend value (-1 to 1 scale, negative=declining, positive=improving)
        """
        if len(values) < 2:
            return 0.0
            
        # Simple linear regression
        x = np.array(range(len(values)))
        y = np.array(values)
        
        # Calculate slope
        n = len(values)
        m = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x * x) - np.sum(x) ** 2)
        
        # Normalize to -1 to 1 range
        return max(-1.0, min(1.0, m * n * 5))  # Scale factor to make trends more visible