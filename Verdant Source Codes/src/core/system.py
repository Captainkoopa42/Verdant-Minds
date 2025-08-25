import numpy as np
import time
from typing import Dict, List, Any, Optional, Tuple
import logging

from src.core.cognitive_chunk import CognitiveChunk
from src.memory.memory_web import MemoryWeb
from src.memory.ecwf_core import ECWFCore
from src.memory.memory_ecwf_bridge import MemoryECWFBridge
from src.blocks.sensory_input_block import SensoryInputBlock
from src.blocks.pattern_recognition_block import PatternRecognitionBlock
from src.blocks.internal_communication_block import InternalCommunicationBlock
from src.blocks.memory_storage_block import MemoryStorageBlock
from src.blocks.reasoning_planning_block import ReasoningPlanningBlock
from src.blocks.ethics_values_block import EthicsValuesBlock
from src.blocks.action_selection_block import ActionSelectionBlock
from src.blocks.language_processing_block import LanguageProcessingBlock
from src.blocks.continual_learning_block import ContinualLearningBlock
from src.kings.three_kings_layer import ThreeKingsLayer
from src.core.system_learning import SystemWideLearning
from src.integration.integration_tools import integrate_system_tools
from src.utils.logging_utils import setup_logger

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
            influence_factor=self.config.get("bridge_influence_factor", 0.3)
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
            "log_level": "INFO"
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
            "MemoryStorage": MemoryStorageBlock(self.memory_bridge),
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
        
        # Add processing time data to chunk
        chunk.update_section("processing_metrics_section", {
            "processing_times": processing_times,
            "total_processing_time": sum(processing_times.values()),
            "glass_transition_temp": self.metrics["glass_transition_temp"],
            "system_entropy": self.metrics["system_entropy"]
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
        
        # Calculate environmental entropy (E)
        # Based on input ambiguity and novelty
        input_ambiguity = sensory_data.get("ambiguity_score", 0.5)
        novelty_score = memory_data.get("novelty_score", 0.5)
        environmental_entropy = (input_ambiguity + novelty_score) / 2
        
        # Calculate system entropy (H_S)
        # Based on wave function entropy and reasoning uncertainty
        wave_data = memory_data.get("wave_properties", {})
        wave_entropy = wave_data.get("entropy", 0.5)
        self.metrics["system_entropy"] = wave_entropy
        
        # Calculate glass transition temperature
        # Uses a non-linear function with feedback from system entropy
        base_t_g = 0.4 + 0.3 * computational_complexity - 0.2 * environmental_entropy
        entropy_feedback = 0.1 * np.sin(wave_entropy * np.pi)
        
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
        
        # Core ethical principles
        principles = [
            ("Non-maleficence", 0.9, {"description": "Avoid causing harm"}),
            ("Beneficence", 0.9, {"description": "Act to benefit others"}),
            ("Autonomy", 0.9, {"description": "Respect individual choice"}),
            ("Justice", 0.9, {"description": "Ensure fairness"}),
            ("Transparency", 0.8, {"description": "Be open and explainable"})
        ]
        
        # Common ethical concepts
        ethical_concepts_list = [
            ("Privacy", 0.8, {"description": "Control over personal information"}),
            ("Fairness", 0.8, {"description": "Equitable treatment"}),
            ("Consent", 0.8, {"description": "Informed agreement"}),
            ("Responsibility", 0.8, {"description": "Accountability for actions"}),
            ("Safety", 0.9, {"description": "Protection from harm"}),
            ("Trust", 0.7, {"description": "Reliability of intentions and actions"}),
            ("Integrity", 0.8, {"description": "Adherence to moral principles"}),
            ("Equality", 0.8, {"description": "Equal treatment and opportunity"})
        ]
        
        # General concepts
        general_concepts = [
            ("Artificial Intelligence", 0.8, {"description": "Computer systems that perform tasks requiring human intelligence"}),
            ("Data", 0.7, {"description": "Information collected and processed"}),
            ("Decision Making", 0.8, {"description": "Process of selecting between options"}),
            ("Algorithm", 0.7, {"description": "Step-by-step procedure for calculations or problem-solving"})
        ]
        
        # Add additional ethical concepts if provided
        if ethical_concepts:
            for concept in ethical_concepts:
                if isinstance(concept, tuple) and len(concept) >= 2:
                    ethical_concepts_list.append(concept)
                else:
                    ethical_concepts_list.append((concept, 0.7, {"description": "User-provided ethical concept"}))
        
        # Add all concepts to memory
        all_concepts = principles + ethical_concepts_list + general_concepts
        for concept, stability, metadata in all_concepts:
            self.memory_web.add_thought(concept, stability, metadata)
        
        # Create connections between related concepts
        # Principles to related ethical concepts
        self.memory_web.connect_thoughts("Non-maleficence", "Safety", 0.9)
        self.memory_web.connect_thoughts("Beneficence", "Trust", 0.8)
        self.memory_web.connect_thoughts("Autonomy", "Privacy", 0.8)
        self.memory_web.connect_thoughts("Autonomy", "Consent", 0.9)
        self.memory_web.connect_thoughts("Justice", "Fairness", 0.9)
        self.memory_web.connect_thoughts("Justice", "Equality", 0.9)
        self.memory_web.connect_thoughts("Transparency", "Trust", 0.8)
        
        # Cross-connections
        self.memory_web.connect_thoughts("Privacy", "Data", 0.8)
        self.memory_web.connect_thoughts("Artificial Intelligence", "Algorithm", 0.9)
        self.memory_web.connect_thoughts("Artificial Intelligence", "Decision Making", 0.8)
        self.memory_web.connect_thoughts("Safety", "Responsibility", 0.7)
        
        # Initialize the crucial Memory-ECWF bridge with ethical concept list
        explicit_ethical_concepts = [c[0] for c in principles + ethical_concepts_list]
        mapping_count = self.memory_bridge.initialize_concept_mappings(explicit_ethical_concepts)
        
        self.logger.info(f"Knowledge initialization complete. Added {len(all_concepts)} concepts and created {mapping_count} dimension mappings")
        
        return {
            "concepts_added": len(all_concepts),
            "ethical_concepts": len(principles) + len(ethical_concepts_list),
            "general_concepts": len(general_concepts),
            "dimension_mappings": mapping_count
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
                influence_factor=system.config.get("bridge_influence_factor", 0.3)
            )
            
            # Restore metrics
            system.metrics = state['metrics']
            
            system.logger.info(f"System state loaded from {filepath}")
            return system
        except Exception as e:
            logging.error(f"Error loading system state: {e}")
            raise