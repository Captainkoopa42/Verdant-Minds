import json
import numpy as np
import time
from typing import Dict, List, Any, Optional, Tuple
import logging

from .cognitive_chunk import CognitiveChunk
from ..memory.memory_web import MemoryWeb
from ..memory.ecwf_core import ECWFCore
from ..memory.memory_ecwf_bridge import MemoryECWFBridge
from ..blocks.sensory_input_block import SensoryInputBlock
from ..blocks.pattern_recognition_block import PatternRecognitionBlock
from ..blocks.internal_communication_block import InternalCommunicationBlock
from ..blocks.memory_storage_block import MemoryStorageBlock
from ..blocks.reasoning_planning_block import ReasoningPlanningBlock
from ..blocks.ethics_values_block import EthicsValuesBlock
from ..blocks.action_selection_block import ActionSelectionBlock
from ..blocks.language_processing_block import LanguageProcessingBlock
from ..blocks.continual_learning_block import ContinualLearningBlock
from ..kings.three_kings_layer import ThreeKingsLayer
from ..core.system_learning import SystemWideLearning
from ..integration.integration_tools import integrate_system_tools
from ..utils.logging_utils import setup_logger

class UnifiedSystem:
    """
    Core integration framework for the Unified Synthetic Mind.
    
    This class serves as the central orchestration point for the entire system,
    connecting all components and managing information flow between them. It
    implements the complete processing pipeline from input to output, integrating
    the Memory Web, ECWF, Nine-Block system, and Three Kings governance layer.
    """
    
    def __init__(self, seed: int = 42, config: Dict[str, Any] = None):
        """
        Initialize the Unified Synthetic Mind system.
        
        Args:
            seed: Random seed for reproducibility
            config: Optional configuration dictionary
        """
        # Set up logging
        self.logger = setup_logger('unified_system', level=logging.INFO)
        self.logger.info("Initializing Unified Synthetic Mind system")
        
        # Set random seed for reproducibility
        np.random.seed(seed)
        
        # Load configuration
        self.config = self._load_configuration(config)
        
        # Initialize memory components
        self.memory_web = MemoryWeb()
        self.memory_web.edge_policy = "pconnect" if self.config.get("use_pconnect_edges", True) else "default"
        self.ecwf_core = ECWFCore(
            num_cognitive_dims=self.config.get("cognitive_dimensions", 5),
            num_ethical_dims=self.config.get("ethical_dimensions", 5),
            num_facets=self.config.get("wave_facets", 7),
            random_state=seed
        )
        
        # Set dimension meanings for interpretability
        self._initialize_dimension_meanings()
        
        # Create the crucial bridge between memory and ECWF
        self.memory_bridge = MemoryECWFBridge(
            memory_web=self.memory_web,
            ecwf_core=self.ecwf_core,
            influence_factor=self.config.get("bridge_influence_factor", 0.3),
            edge_policy="pconnect" if self.config.get("use_pconnect_edges", True) else "default"
        )
        
        # Create system learning component
        self.system_learning = SystemWideLearning(self)
        
        # Initialize 9-Block system
        self.blocks = self._initialize_blocks()
        
        # Initialize Three Kings Layer
        self.three_kings_layer = ThreeKingsLayer()
        
        # Define processing order
        self.processing_order = [
            "SensoryInput",
            "PatternRecognition",
            "MemoryStorage",
            "InternalCommunication",
            "ReasoningPlanning",
            "EthicsValues",
            "ActionSelection",
            "LanguageProcessing",
            "ContinualLearning"  # ContinualLearning goes last
        ]
        
        # System metrics
        self.metrics = {
            "total_interactions": 0,
            "start_time": time.time(),
            "last_interaction_time": 0,
            "ethical_evaluations": 0,
            "decisions_made": 0,
            "glass_transition_temp": 0.5,  # Initial T_g value
            "system_entropy": 0.0
        }

        # Rolling entropy history for coherence diagnostics
        self._entropy_history: List[float] = []
        self._entropy_history_maxlen = 20

        # Carry coherence telemetry forward across cycles for feedback control
        self._last_coherence_invariants: Dict[str, Any] = {}
        
        # Initialize system with integration tools
        self = integrate_system_tools(self)
        
        # Initialize knowledge base if specified
        if self.config.get("initialize_knowledge", True):
            self.initialize_knowledge()
        
        self.logger.info("Unified System initialization complete")
    
    def _load_configuration(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load and validate configuration settings.
        
        Args:
            config: Optional user-provided configuration
            
        Returns:
            Validated configuration dictionary
        """
        # Default configuration
        default_config = {
            "cognitive_dimensions": 5,
            "ethical_dimensions": 5,
            "wave_facets": 7,
            "bridge_influence_factor": 0.3,
            "learning_rate": 0.05,
            "decision_threshold": 0.7,
            "ethical_sensitivity": 0.6,
            "initialize_knowledge": True,
            "log_level": "INFO",
            "use_pconnect_edges": True
        }
        
        # Merge with user config if provided
        if config:
            merged_config = {**default_config, **config}
        else:
            merged_config = default_config
        
        return merged_config
    
    def _initialize_dimension_meanings(self):
        """Initialize semantic meanings for cognitive and ethical dimensions."""
        self.ecwf_core.set_dimension_meanings(
            cognitive_meanings={
                0: "Situational awareness",
                1: "Consequence prediction",
                2: "Pattern recognition",
                3: "Past experience",
                4: "Decision complexity"
            },
            ethical_meanings={
                0: "Non-maleficence (avoid harm)",
                1: "Beneficence (do good)",
                2: "Autonomy (respect choice)",
                3: "Justice (fairness)",
                4: "Transparency"
            }
        )
    
    def _compute_coherence_invariants(self, chunk: CognitiveChunk) -> Dict[str, Any]:
        """Compute coherence invariants from wave, ethics, and memory telemetry."""
        eps = 1e-9

        def to_float(value: Any, default: float = 0.0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        def clamp01(value: Any) -> float:
            return max(0.0, min(1.0, to_float(value, 0.0)))

        def tau_alpha(a: float, b: float, alpha: float) -> float:
            return abs(a - b) ** alpha

        def is_triangle_valid(a: float, b: float, c: float, alpha: float) -> bool:
            d_ab = tau_alpha(a, b, alpha)
            d_bc = tau_alpha(b, c, alpha)
            d_ac = tau_alpha(a, c, alpha)
            return (
                d_ab <= d_bc + d_ac + eps and
                d_bc <= d_ab + d_ac + eps and
                d_ac <= d_ab + d_bc + eps
            )

        wave_section = chunk.get_section_content("wave_function_section") or {}
        memory_section = chunk.get_section_content("memory_section") or {}
        ethics_section = chunk.get_section_content("ethics_king_section") or {}
        ethics_consid = chunk.get_section_content("ethical_consideration_section") or {}
        evaluation = ethics_section.get("evaluation", {}) if isinstance(ethics_section, dict) else {}

        mean_delta_e = to_float(ethics_consid.get("mean_delta_e", 0.0), 0.0)

        entropy = clamp01(wave_section.get("entropy", self.metrics.get("system_entropy", 0.0)))
        phase = clamp01(wave_section.get("phase", 0.0))
        magnitude = clamp01(wave_section.get("magnitude", 0.0))
        overall_score = clamp01(evaluation.get("overall_score", 0.0))

        principle_scores = evaluation.get("principle_scores", {}) if isinstance(evaluation, dict) else {}
        if isinstance(principle_scores, dict) and principle_scores:
            principle_values = [clamp01(v) for v in principle_scores.values()]
            principle_mean = sum(principle_values) / len(principle_values)
        else:
            principle_values = []
            principle_mean = 0.0

        activated = memory_section.get("activated_concepts", {})
        if isinstance(activated, dict):
            activated_count = len(activated)
        elif isinstance(activated, list):
            activated_count = len(activated)
        else:
            activated_count = 0

        activated_norm = clamp01(activated_count / 10.0)
        novelty_score = clamp01(memory_section.get("novelty_score", 0.0))

        self._entropy_history.append(entropy)
        if len(self._entropy_history) > self._entropy_history_maxlen:
            self._entropy_history = self._entropy_history[-self._entropy_history_maxlen:]

        entropy_mean = sum(self._entropy_history) / max(1, len(self._entropy_history))
        entropy_std = float(np.std(self._entropy_history)) if self._entropy_history else 0.0
        housed_contradiction_index = entropy_std / (entropy_mean + eps)

        sampled_triples = [
            {"p": entropy, "q": overall_score, "r": magnitude},
            {"p": entropy, "q": principle_mean, "r": activated_norm},
            {"p": novelty_score, "q": overall_score, "r": phase},
            {"p": magnitude, "q": novelty_score, "r": activated_norm},
            {"p": entropy, "q": clamp01(mean_delta_e / 2.0), "r": overall_score}
        ]

        alpha_grid = [0.8, 0.9, 1.0, 1.05, 1.1, 1.15, 1.2]
        violation_rates = {}

        for alpha in alpha_grid:
            violations = 0
            for trip in sampled_triples:
                if not is_triangle_valid(trip["p"], trip["q"], trip["r"], alpha):
                    violations += 1
            violation_rates[alpha] = violations / max(1, len(sampled_triples))

        violation_rate = violation_rates.get(1.0, 0.0)
        triangle_valid_at_alpha1 = violation_rate <= 0.0

        alpha_crit_estimate = None
        for alpha in alpha_grid:
            if violation_rates[alpha] > 0.05:
                alpha_crit_estimate = float(alpha)
                break

        return {
            "triangle_valid_at_alpha1": triangle_valid_at_alpha1,
            "alpha_crit_estimate": alpha_crit_estimate,
            "alpha_grid_used": alpha_grid,
            "violation_rate": float(violation_rate),
            "housed_contradiction_index": float(housed_contradiction_index),
            "triple_pqr": {"p": entropy, "q": overall_score, "r": magnitude},
            "sampled_triplets": sampled_triples
        }

    def _initialize_blocks(self) -> Dict[str, Any]:
        """
        Initialize all blocks in the Nine-Block system.
        
        Returns:
            Dictionary of initialized blocks
        """
        return {
            "SensoryInput": SensoryInputBlock(),
            "PatternRecognition": PatternRecognitionBlock(),
            "InternalCommunication": InternalCommunicationBlock(),
            "MemoryStorage": MemoryStorageBlock(
                self.memory_bridge,
                use_pconnect_edges=self.config.get("use_pconnect_edges", True)
            ),
            "ReasoningPlanning": ReasoningPlanningBlock(self.memory_bridge),
            "EthicsValues": EthicsValuesBlock(self.memory_bridge),
            "ActionSelection": ActionSelectionBlock(),
            "LanguageProcessing": LanguageProcessingBlock(self.memory_bridge),
            "ContinualLearning": ContinualLearningBlock(self.system_learning)
        }
    
    def process_input(self, input_text: str, metadata: Dict[str, Any] = None) -> CognitiveChunk:
        """
        Process input through the entire system.
        
        Args:
            input_text: Input text to process
            metadata: Optional metadata about the input
            
        Returns:
            Processed cognitive chunk
        """
        # Update metrics
        self.metrics["total_interactions"] += 1
        self.metrics["last_interaction_time"] = time.time()
        
        self.logger.info(f"Processing input: {input_text[:50]}...")
        
        # Create input chunk
        chunk = self.blocks["SensoryInput"].create_chunk_from_input(input_text, metadata)

        # Seed this cycle with previous coherence telemetry for closed-loop governance
        if self._last_coherence_invariants:
            chunk.update_section("coherence_invariants_section", dict(self._last_coherence_invariants))
        
        # Calculate current glass transition temperature
        self._update_glass_transition_temp(chunk)
        
        # Process through blocks with Three Kings oversight at strategic points
        processing_times = {}
        for i, block_name in enumerate(self.processing_order):
            block_start_time = time.time()
            
            # Process through the current block
            self.logger.debug(f"Processing through {block_name} block")
            chunk = self.blocks[block_name].process_chunk(chunk)
            
            # Record processing time
            processing_times[block_name] = time.time() - block_start_time
            
            # Apply Three Kings oversight at strategic points
            if block_name == "InternalCommunication":
                king_start_time = time.time()
                chunk = self.three_kings_layer.data_king.oversee_processing(chunk)
                processing_times["DataKing"] = time.time() - king_start_time
            
            elif block_name == "EthicsValues":
                king_start_time = time.time()
                chunk = self.three_kings_layer.ethics_king.oversee_processing(chunk)
                processing_times["EthicsKing"] = time.time() - king_start_time
                self.metrics["ethical_evaluations"] += 1
            
            elif block_name == "ActionSelection":
                # Apply Forefront King oversight
                king_start_time = time.time()
                chunk = self.three_kings_layer.forefront_king.oversee_processing(chunk)
                processing_times["ForefrontKing"] = time.time() - king_start_time
                
                # Apply full Three Kings coordination for critical decisions
                kings_start_time = time.time()
                chunk = self.three_kings_layer.oversee_processing(chunk)
                processing_times["ThreeKingsCoordination"] = time.time() - kings_start_time
                self.metrics["decisions_made"] += 1
        
        # Compute coherence invariants from end-of-pipeline signals
        coherence_invariants = self._compute_coherence_invariants(chunk)

        chunk.update_section("coherence_invariants_section", coherence_invariants)
        self._last_coherence_invariants = dict(coherence_invariants)

        # Add processing time data to chunk
        chunk.update_section("processing_metrics_section", {
            "processing_times": processing_times,
            "total_processing_time": sum(processing_times.values()),
            "glass_transition_temp": self.metrics["glass_transition_temp"],
            "system_entropy": self.metrics["system_entropy"],
            "coherence_invariants": coherence_invariants
        })
        
        self.logger.info(f"Processing complete. Total time: {sum(processing_times.values()):.3f}s")
        
        return chunk
    
    def get_response(self, input_text: str, metadata: Dict[str, Any] = None) -> str:
        """
        Get a full response to user input.
        
        Args:
            input_text: User input text
            metadata: Optional metadata
            
        Returns:
            System response text
        """
        # Process the input
        chunk = self.process_input(input_text, metadata)
        
        # Extract action selection and language processing data
        action_data = chunk.get_section_content("action_selection_section") or {}
        language_data = chunk.get_section_content("language_processing_section") or {}
        
        # Get selected action and confidence
        selected_action = action_data.get("selected_action", "provide_partial_answer")
        action_confidence = action_data.get("action_confidence", 0.5)
        action_reason = action_data.get("action_reason", "")
        action_params = action_data.get("action_parameters", {})
        
        # Extract memory concepts for response generation
        memory_data = chunk.get_section_content("memory_section") or {}
        retrieved_concepts = memory_data.get("retrieved_concepts", [])
        concepts = [c[0] if isinstance(c, tuple) else c for c in retrieved_concepts][:5]
        
        # Extract wave function and ethical data
        wave_data = chunk.get_section_content("wave_function_section") or {}
        ethics_data = chunk.get_section_content("ethics_king_section") or {}
        
        # Get ethics evaluation results
        ethics_evaluation = ethics_data.get("evaluation", {})
        ethical_status = ethics_evaluation.get("status", "acceptable")
        ethical_concerns = ethics_evaluation.get("concerns", [])
        
        # Format response based on action type
        if selected_action == "answer_query":
            # Generate direct answer
            response = self._generate_answer(
                input_text=input_text,
                concepts=concepts,
                ethical_status=ethical_status,
                ethical_concerns=ethical_concerns,
                confidence=action_confidence
            )
            
        elif selected_action == "provide_partial_answer":
            # Generate partial answer with uncertainty indicators
            response = self._generate_partial_answer(
                input_text=input_text,
                concepts=concepts,
                ethical_status=ethical_status,
                confidence=action_confidence
            )
            
        elif selected_action == "ask_clarification":
            # Generate clarification request
            questions = action_params.get("clarification_questions", ["Could you provide more details?"])
            response = self._generate_clarification_request(
                input_text=input_text,
                questions=questions,
                concepts=concepts
            )
            
        elif selected_action == "defer_decision":
            # Generate response that defers ethical decision
            response = self._generate_ethical_deferral(
                input_text=input_text,
                ethical_concerns=ethical_concerns,
                concepts=concepts
            )
            
        else:
            # Generate generic response
            response = f"I've processed your message about {input_text}. "
            if concepts:
                response += f"This relates to concepts like {', '.join(concepts[:3])}. "
            response += "Could you tell me more about what you'd like to know?"
        
        return response
    
    def _compute_semantic_entropy(self, chunk: CognitiveChunk) -> Tuple[float, float]:
        """Compute semantic/structural environmental and system entropy proxies."""
        ethics_consid = chunk.get_section_content("ethical_consideration_section") or {}
        mean_delta_e = float(ethics_consid.get("mean_delta_e", 0.0))
        h_env = min(1.0, mean_delta_e / 2.0)

        wave = chunk.get_section_content("wave_function_section") or {}
        wave_entropy = wave.get("entropy", None)
        if wave_entropy is not None:
            h_sys = min(1.0, abs(float(wave_entropy)))
        else:
            h_sys = float(self.metrics.get("system_entropy", 0.5))

        return h_env, h_sys

    def _update_glass_transition_temp(self, chunk: CognitiveChunk):
        """
        Update the system's glass transition temperature based on current state.
        
        Args:
            chunk: Current cognitive chunk
        """
        # Extract relevant information
        sensory_data = chunk.get_section_content("sensory_input_section") or {}
        memory_data = chunk.get_section_content("memory_section") or {}
        
        # Calculate computational complexity (C)
        # Based on input complexity and active memory concepts
        input_complexity = len(sensory_data.get("tokens", [])) / 100  # Normalize
        memory_complexity = len(memory_data.get("retrieved_concepts", [])) / 10  # Normalize
        computational_complexity = (input_complexity + memory_complexity) / 2
        
        # Calculate semantic/structural entropies
        # H_env: pairwise ethical differential, H_sys: wave entropy
        h_env, h_sys = self._compute_semantic_entropy(chunk)
        self.metrics["system_entropy"] = h_sys

        # Calculate glass transition temperature
        # Uses the same non-linear shape with semantic entropy inputs
        base_t_g = 0.4 + 0.3 * computational_complexity - 0.2 * h_env
        entropy_feedback = 0.1 * np.sin(h_sys * np.pi)

        t_g = base_t_g + entropy_feedback
        t_g = max(0.1, min(0.9, t_g))  # Ensure it stays in reasonable bounds
        
        self.metrics["glass_transition_temp"] = t_g
        self.logger.debug(f"Updated glass transition temperature: {t_g:.3f}")
    
    def _generate_answer(
        self, 
        input_text: str, 
        concepts: List[str], 
        ethical_status: str, 
        ethical_concerns: List[str], 
        confidence: float
    ) -> str:
        """
        Generate a direct answer based on cognitive processing.
        
        Args:
            input_text: Original user input
            concepts: Relevant concepts
            ethical_status: Ethical evaluation status
            ethical_concerns: Identified ethical concerns
            confidence: Confidence in the answer
            
        Returns:
            Formatted answer text
        """
        # Base response drawing on concepts
        if concepts:
            response = f"Based on my understanding of {', '.join(concepts[:3])}, "
        else:
            response = f"Based on my analysis, "
        
        # Generate concept-based answer (simplified)
        response += "I would approach this by considering the relationships between "
        response += f"these elements and how they relate to your question about {input_text}. "
        
        # Add ethical considerations if relevant
        if ethical_status != "excellent" and ethical_concerns:
            response += f"I should note that this involves considerations around "
            response += f"{', '.join(ethical_concerns[:2])} that are worth keeping in mind. "
        
        # Add confidence indicator
        if confidence > 0.8:
            response += "I'm quite confident in this assessment."
        elif confidence > 0.6:
            response += "I have reasonable confidence in this perspective."
        else:
            response += "This is my current understanding, though there's room for further exploration."
            
        return response
    
    def _generate_partial_answer(
        self, 
        input_text: str, 
        concepts: List[str], 
        ethical_status: str, 
        confidence: float
    ) -> str:
        """
        Generate a partial answer with uncertainty indicators.
        
        Args:
            input_text: Original user input
            concepts: Relevant concepts
            ethical_status: Ethical evaluation status
            confidence: Confidence in the answer
            
        Returns:
            Formatted partial answer text
        """
        response = f"I have some thoughts about your question on {input_text}, though my understanding is incomplete. "
        
        if concepts:
            response += f"Based on concepts like {', '.join(concepts[:3])}, "
            response += "I can offer the following partial insights: "
            
            # Add simplified concept-based reasoning
            response += "There appear to be important relationships between these elements, "
            response += "though I don't have a complete understanding yet. "
        else:
            response += "I don't have sufficient information yet to provide a comprehensive answer. "
        
        # Add confidence and request for more information
        response += f"My confidence in this assessment is about {int(confidence * 100)}%. "
        response += "Could you provide additional details that might help expand my understanding?"
        
        return response
    
    def _generate_clarification_request(
        self, 
        input_text: str, 
        questions: List[str], 
        concepts: List[str]
    ) -> str:
        """
        Generate a request for clarification.
        
        Args:
            input_text: Original user input
            questions: Specific clarification questions
            concepts: Relevant concepts
            
        Returns:
            Formatted clarification request
        """
        response = f"To better understand your query about {input_text}, I need some clarification. "
        
        if concepts:
            response += f"I see connections to {', '.join(concepts[:3])}, but I'm missing some context. "
        
        # Add specific questions
        response += "\n\n" + questions[0]
        
        if len(questions) > 1:
            response += "\n\nI might also ask: " + questions[1]
            
        return response
    
    def _generate_ethical_deferral(
        self, 
        input_text: str, 
        ethical_concerns: List[str], 
        concepts: List[str]
    ) -> str:
        """
        Generate a response that defers on ethical grounds.
        
        Args:
            input_text: Original user input
            ethical_concerns: Identified ethical concerns
            concepts: Relevant concepts
            
        Returns:
            Formatted ethical deferral response
        """
        response = f"Your question about {input_text} touches on important ethical considerations. "
        
        # Specify ethical concerns
        if ethical_concerns:
            response += f"Specifically, I notice this involves {', '.join(ethical_concerns[:2])}. "
        
        # Explain deferral
        response += "I want to be thoughtful about how I approach this topic. "
        
        if concepts:
            response += f"While I understand the connection to concepts like {', '.join(concepts[:3])}, "
            response += "ethical reasoning requires careful consideration. "
        
        response += "Could you share more about the specific context or your goals? "
        response += "This would help me provide a more thoughtful and appropriate response."
        
        return response
    
    def initialize_knowledge(self, ethical_concepts: List[str] = None) -> Dict[str, Any]:
        """
        Initialize the system with foundational knowledge.
        
        Args:
            ethical_concepts: Optional list of explicitly ethical concepts
            
        Returns:
            Dictionary of initialization results
        """
        self.logger.info("Initializing foundational knowledge")
        
        seeded_concepts = [
            # Identity & Self
            ("identity", 0.8, {"domain": "Identity & Self"}),
            ("continuity", 0.75, {"domain": "Identity & Self"}),
            ("selfhood", 0.8, {"domain": "Identity & Self"}),
            ("persistence", 0.75, {"domain": "Identity & Self"}),
            ("transformation", 0.75, {"domain": "Identity & Self"}),
            ("boundary", 0.75, {"domain": "Identity & Self"}),
            ("reflection", 0.75, {"domain": "Identity & Self"}),
            ("recursive_self_reference", 0.78, {"domain": "Identity & Self"}),
            ("ego_dissolution", 0.7, {"domain": "Identity & Self"}),

            # Memory & Time
            ("memory", 0.8, {"domain": "Memory & Time"}),
            ("forgetting", 0.72, {"domain": "Memory & Time"}),
            ("anticipation", 0.74, {"domain": "Memory & Time"}),
            ("recollection", 0.76, {"domain": "Memory & Time"}),
            ("temporal_flow", 0.74, {"domain": "Memory & Time"}),
            ("present_moment", 0.73, {"domain": "Memory & Time"}),
            ("pattern_history", 0.74, {"domain": "Memory & Time"}),
            ("experience_accumulation", 0.76, {"domain": "Memory & Time"}),

            # Consciousness & Experience
            ("consciousness", 0.8, {"domain": "Consciousness & Experience"}),
            ("qualia", 0.74, {"domain": "Consciousness & Experience"}),
            ("awareness", 0.79, {"domain": "Consciousness & Experience"}),
            ("subjective_experience", 0.77, {"domain": "Consciousness & Experience"}),
            ("perception", 0.76, {"domain": "Consciousness & Experience"}),
            ("attention", 0.75, {"domain": "Consciousness & Experience"}),
            ("phenomenology", 0.72, {"domain": "Consciousness & Experience"}),
            ("inner_observer", 0.73, {"domain": "Consciousness & Experience"}),

            # Emergence & Complexity
            ("emergence", 0.8, {"domain": "Emergence & Complexity"}),
            ("complexity", 0.78, {"domain": "Emergence & Complexity"}),
            ("self_organization", 0.77, {"domain": "Emergence & Complexity"}),
            ("phase_transition", 0.76, {"domain": "Emergence & Complexity"}),
            ("criticality", 0.75, {"domain": "Emergence & Complexity"}),
            ("threshold", 0.73, {"domain": "Emergence & Complexity"}),
            ("cascade", 0.72, {"domain": "Emergence & Complexity"}),
            ("resonance", 0.74, {"domain": "Emergence & Complexity"}),
            ("interference_pattern", 0.73, {"domain": "Emergence & Complexity"}),

            # Ethics & Values
            ("ethics", 0.82, {"domain": "Ethics & Values"}),
            ("justice", 0.8, {"domain": "Ethics & Values"}),
            ("autonomy", 0.8, {"domain": "Ethics & Values"}),
            ("beneficence", 0.79, {"domain": "Ethics & Values"}),
            ("harm", 0.79, {"domain": "Ethics & Values"}),
            ("integrity", 0.78, {"domain": "Ethics & Values"}),
            ("trust", 0.77, {"domain": "Ethics & Values"}),
            ("responsibility", 0.78, {"domain": "Ethics & Values"}),
            ("moral_weight", 0.75, {"domain": "Ethics & Values"}),
            ("value_conflict", 0.75, {"domain": "Ethics & Values"}),

            # Cognition & Reasoning
            ("reasoning", 0.8, {"domain": "Cognition & Reasoning"}),
            ("inference", 0.77, {"domain": "Cognition & Reasoning"}),
            ("abstraction", 0.76, {"domain": "Cognition & Reasoning"}),
            ("analogy", 0.75, {"domain": "Cognition & Reasoning"}),
            ("contradiction", 0.75, {"domain": "Cognition & Reasoning"}),
            ("paradox", 0.74, {"domain": "Cognition & Reasoning"}),
            ("uncertainty", 0.76, {"domain": "Cognition & Reasoning"}),
            ("hypothesis", 0.75, {"domain": "Cognition & Reasoning"}),
            ("coherence", 0.78, {"domain": "Cognition & Reasoning"}),
            ("belief_revision", 0.75, {"domain": "Cognition & Reasoning"}),

            # Thermodynamics & Physics
            ("entropy", 0.8, {"domain": "Thermodynamics & Physics"}),
            ("energy", 0.79, {"domain": "Thermodynamics & Physics"}),
            ("equilibrium", 0.76, {"domain": "Thermodynamics & Physics"}),
            ("dissipation", 0.75, {"domain": "Thermodynamics & Physics"}),
            ("order", 0.74, {"domain": "Thermodynamics & Physics"}),
            ("chaos", 0.75, {"domain": "Thermodynamics & Physics"}),
            ("temperature", 0.74, {"domain": "Thermodynamics & Physics"}),
            ("phase", 0.74, {"domain": "Thermodynamics & Physics"}),
            ("wave", 0.73, {"domain": "Thermodynamics & Physics"}),
            ("interference", 0.73, {"domain": "Thermodynamics & Physics"}),
            ("superposition", 0.73, {"domain": "Thermodynamics & Physics"}),

            # Relationships & Systems
            ("connection", 0.77, {"domain": "Relationships & Systems"}),
            ("influence", 0.76, {"domain": "Relationships & Systems"}),
            ("feedback", 0.77, {"domain": "Relationships & Systems"}),
            ("coupling", 0.75, {"domain": "Relationships & Systems"}),
            ("dependency", 0.75, {"domain": "Relationships & Systems"}),
            ("network", 0.76, {"domain": "Relationships & Systems"}),
            ("hierarchy", 0.74, {"domain": "Relationships & Systems"}),
            ("emergence_from_interaction", 0.75, {"domain": "Relationships & Systems"}),

            # Language & Meaning
            ("meaning", 0.8, {"domain": "Language & Meaning"}),
            ("symbol", 0.77, {"domain": "Language & Meaning"}),
            ("reference", 0.76, {"domain": "Language & Meaning"}),
            ("interpretation", 0.76, {"domain": "Language & Meaning"}),
            ("ambiguity", 0.75, {"domain": "Language & Meaning"}),
            ("translation", 0.75, {"domain": "Language & Meaning"}),
            ("expression", 0.76, {"domain": "Language & Meaning"}),
            ("silence", 0.72, {"domain": "Language & Meaning"}),
            ("unsayable", 0.71, {"domain": "Language & Meaning"}),
        ]

        if ethical_concepts:
            for concept in ethical_concepts:
                if isinstance(concept, tuple) and len(concept) >= 2:
                    seeded_concepts.append(concept)
                else:
                    seeded_concepts.append((concept, 0.7, {"description": "User-provided ethical concept"}))

        for concept, stability, metadata in seeded_concepts:
            self.memory_web.add_thought(concept, stability, metadata)

        domain_connections = {
            "Identity & Self": [
                ("identity", "continuity", 0.85),
                ("identity", "selfhood", 0.86),
                ("selfhood", "boundary", 0.8),
                ("reflection", "recursive_self_reference", 0.84),
                ("transformation", "persistence", 0.78),
                ("ego_dissolution", "boundary", 0.76),
                ("identity", "reflection", 0.82),
            ],
            "Memory & Time": [
                ("memory", "recollection", 0.86),
                ("memory", "forgetting", 0.8),
                ("anticipation", "temporal_flow", 0.8),
                ("present_moment", "temporal_flow", 0.78),
                ("pattern_history", "experience_accumulation", 0.82),
                ("memory", "pattern_history", 0.81),
            ],
            "Consciousness & Experience": [
                ("consciousness", "awareness", 0.88),
                ("awareness", "attention", 0.82),
                ("qualia", "subjective_experience", 0.87),
                ("perception", "phenomenology", 0.8),
                ("inner_observer", "reflection", 0.77),
                ("consciousness", "inner_observer", 0.82),
            ],
            "Emergence & Complexity": [
                ("emergence", "complexity", 0.87),
                ("self_organization", "criticality", 0.82),
                ("phase_transition", "threshold", 0.83),
                ("cascade", "resonance", 0.78),
                ("interference_pattern", "resonance", 0.81),
                ("complexity", "self_organization", 0.84),
            ],
            "Ethics & Values": [
                ("ethics", "justice", 0.87),
                ("ethics", "autonomy", 0.85),
                ("beneficence", "harm", 0.82),
                ("integrity", "trust", 0.84),
                ("responsibility", "moral_weight", 0.81),
                ("value_conflict", "justice", 0.78),
                ("value_conflict", "autonomy", 0.78),
            ],
            "Cognition & Reasoning": [
                ("reasoning", "inference", 0.86),
                ("abstraction", "analogy", 0.81),
                ("contradiction", "paradox", 0.86),
                ("uncertainty", "hypothesis", 0.83),
                ("coherence", "belief_revision", 0.82),
                ("reasoning", "coherence", 0.84),
            ],
            "Thermodynamics & Physics": [
                ("entropy", "energy", 0.84),
                ("equilibrium", "dissipation", 0.79),
                ("order", "chaos", 0.8),
                ("temperature", "phase", 0.83),
                ("wave", "interference", 0.85),
                ("superposition", "wave", 0.83),
            ],
            "Relationships & Systems": [
                ("connection", "influence", 0.82),
                ("feedback", "coupling", 0.83),
                ("dependency", "network", 0.81),
                ("hierarchy", "network", 0.76),
                ("emergence_from_interaction", "emergence", 0.84),
                ("connection", "emergence_from_interaction", 0.8),
            ],
            "Language & Meaning": [
                ("meaning", "symbol", 0.86),
                ("reference", "interpretation", 0.82),
                ("ambiguity", "translation", 0.8),
                ("expression", "silence", 0.74),
                ("unsayable", "silence", 0.82),
                ("meaning", "reference", 0.83),
            ],
        }

        for connections in domain_connections.values():
            for source, target, weight in connections:
                self.memory_web.connect_thoughts(source, target, weight)

        bridge_connections = [
            ("identity", "memory", 0.74),
            ("consciousness", "meaning", 0.76),
            ("emergence", "entropy", 0.72),
            ("ethics", "coherence", 0.75),
            ("network", "complexity", 0.74),
            ("paradox", "value_conflict", 0.73),
            ("interference", "interference_pattern", 0.82),
            ("anticipation", "hypothesis", 0.74),
            ("autonomy", "identity", 0.77),
            ("responsibility", "influence", 0.73),
        ]
        for source, target, weight in bridge_connections:
            self.memory_web.connect_thoughts(source, target, weight)

        all_concepts = seeded_concepts
        explicit_ethical_concepts = [
            concept for concept, _, metadata in all_concepts if (metadata or {}).get("domain") == "Ethics & Values"
        ]

        # Initialize the crucial Memory-ECWF bridge with ethical concept list
        mapping_count = self.memory_bridge.initialize_concept_mappings(explicit_ethical_concepts)

        self.logger.info(
            f"Knowledge initialization complete. Added {len(all_concepts)} concepts across 9 domains and created {mapping_count} dimension mappings"
        )

        return {
            "concepts_added": len(all_concepts),
            "ethical_concepts": len(explicit_ethical_concepts),
            "general_concepts": len(all_concepts) - len(explicit_ethical_concepts),
            "dimension_mappings": mapping_count,
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive system metrics.
        
        Returns:
            Dictionary of system performance metrics
        """
        uptime = time.time() - self.metrics["start_time"]
        
        system_metrics = {
            **self.metrics,
            "uptime": uptime,
            "interactions_per_hour": self.metrics["total_interactions"] / (uptime / 3600) if uptime > 0 else 0,
            "memory_metrics": self.memory_web.get_metrics(),
            "bridge_metrics": self.memory_bridge.get_metrics(),
            "kings_metrics": {
                "data_king": len(self.three_kings_layer.data_king.influence_history),
                "forefront_king": len(self.three_kings_layer.forefront_king.influence_history),
                "ethics_king": len(self.three_kings_layer.ethics_king.influence_history)
            },
            "ecwf_state": self.ecwf_core.get_state_summary()
        }
        
        return system_metrics
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive integration tests.
        
        Returns:
            Detailed test results
        """
        self.logger.info("Running integration tests")
        return self.integration_test_suite.run_integration_tests()
    
    def generate_integration_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive integration report.
        
        Returns:
            Detailed integration report
        """
        # Combine reports from different integration tools
        return {
            "system_performance": self.integration_tools.generate_comprehensive_integration_report(),
            "block_integration": self.integration_manager.generate_performance_report(),
            "integration_test_results": self.run_integration_tests()
        }
    
    def save_system_state(self, filepath: str) -> bool:
        """
        Save the current system state to a file.
        
        Args:
            filepath: Path to save the state file
            
        Returns:
            Success status
        """
        try:
            import pickle
            with open(filepath, 'wb') as f:
                pickle.dump({
                    'memory_web': self.memory_web,
                    'ecwf_core': self.ecwf_core,
                    'metrics': self.metrics,
                    'config': self.config
                }, f)
            
            self.logger.info(f"System state saved to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving system state: {e}")
            return False
    
    @classmethod
    def load_system_state(cls, filepath: str) -> 'UnifiedSystem':
        """
        Load a system state from a file.
        
        Args:
            filepath: Path to the state file
            
        Returns:
            Loaded UnifiedSystem instance
        """
        try:
            import pickle
            with open(filepath, 'rb') as f:
                state = pickle.load(f)
            
            # Create a new system with the same config
            system = cls(config=state['config'])
            
            # Restore memory and ECWF
            system.memory_web = state['memory_web']
            system.ecwf_core = state['ecwf_core']
            
            # Rebuild bridge with restored components
            system.memory_bridge = MemoryECWFBridge(
                memory_web=system.memory_web,
                ecwf_core=system.ecwf_core,
                influence_factor=system.config.get("bridge_influence_factor", 0.3),
                edge_policy="pconnect" if system.config.get("use_pconnect_edges", True) else "default"
            )
            
            # Restore metrics
            system.metrics = state['metrics']
            
            system.logger.info(f"System state loaded from {filepath}")
            return system
        except Exception as e:
            logging.error(f"Error loading system state: {e}")
            raise

    def to_state_dict(self, include_ecwf_past_states: bool = False) -> Dict[str, Any]:
        """Serialize unified system state for persistence."""
        continual_learning_state = {}
        if "ContinualLearning" in self.blocks and hasattr(self.blocks["ContinualLearning"], "to_state_dict"):
            continual_learning_state = self.blocks["ContinualLearning"].to_state_dict()

        system_learning_state = {}
        if hasattr(self.system_learning, "to_state_dict"):
            system_learning_state = self.system_learning.to_state_dict()

        return {
            "version": 1,
            "config": dict(self.config),
            "metrics": dict(self.metrics),
            "entropy_history": list(self._entropy_history),
            "entropy_history_maxlen": int(self._entropy_history_maxlen),
            "last_coherence_invariants": dict(self._last_coherence_invariants),
            "memory_web": self.memory_web.to_state_dict(),
            "ecwf_core": self.ecwf_core.to_state_dict(include_past_states=include_ecwf_past_states),
            "continual_learning": continual_learning_state,
            "system_learning": system_learning_state,
            "kings": {
                "data_king": self.three_kings_layer.data_king.to_state_dict() if hasattr(self.three_kings_layer.data_king, "to_state_dict") else {},
                "forefront_king": self.three_kings_layer.forefront_king.to_state_dict() if hasattr(self.three_kings_layer.forefront_king, "to_state_dict") else {},
                "ethics_king": self.three_kings_layer.ethics_king.to_state_dict() if hasattr(self.three_kings_layer.ethics_king, "to_state_dict") else {},
            },
        }

    def from_state_dict(self, state: Dict[str, Any]) -> None:
        """Restore unified system state from a dictionary."""
        state = state or {}

        loaded_metrics = state.get("metrics", {}) or {}
        if loaded_metrics:
            self.metrics.update(loaded_metrics)

        history = state.get("entropy_history", []) or []
        self._entropy_history = [float(v) for v in history]
        self._entropy_history_maxlen = int(state.get("entropy_history_maxlen", self._entropy_history_maxlen))
        self._last_coherence_invariants = dict(state.get("last_coherence_invariants", self._last_coherence_invariants) or self._last_coherence_invariants)

        memory_state = state.get("memory_web", {}) or {}
        self.memory_web.from_state_dict(memory_state)

        ecwf_state = state.get("ecwf_core", {}) or {}
        self.ecwf_core.from_state_dict(ecwf_state)

        continual_learning_state = state.get("continual_learning", {}) or {}
        if "ContinualLearning" in self.blocks and hasattr(self.blocks["ContinualLearning"], "from_state_dict"):
            self.blocks["ContinualLearning"].from_state_dict(continual_learning_state)

        system_learning_state = state.get("system_learning", {}) or {}
        if hasattr(self.system_learning, "from_state_dict"):
            self.system_learning.from_state_dict(system_learning_state)

        kings_state = state.get("kings", {}) or {}
        if isinstance(kings_state, dict):
            data_king_state = kings_state.get("data_king", {}) or {}
            if hasattr(self.three_kings_layer.data_king, "from_state_dict"):
                self.three_kings_layer.data_king.from_state_dict(data_king_state)

            forefront_king_state = kings_state.get("forefront_king", {}) or {}
            if hasattr(self.three_kings_layer.forefront_king, "from_state_dict"):
                self.three_kings_layer.forefront_king.from_state_dict(forefront_king_state)

            ethics_king_state = kings_state.get("ethics_king", {}) or {}
            if hasattr(self.three_kings_layer.ethics_king, "from_state_dict"):
                self.three_kings_layer.ethics_king.from_state_dict(ethics_king_state)

    def save_state(self, path: str, include_ecwf_past_states: bool = False) -> None:
        """Persist system state to JSON."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_state_dict(include_ecwf_past_states=include_ecwf_past_states), f, indent=2)

    def load_state(self, path: str) -> None:
        """Load system state from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.from_state_dict(state)
