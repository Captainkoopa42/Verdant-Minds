import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Any, Set

from core.cognitive_chunk import CognitiveChunk

class MemoryECWFBridge:
    """
    Bridge between MemoryWeb and ECWFCore for the Unified Synthetic Mind.
    
    Enables bidirectional flow between symbolic knowledge representation (MemoryWeb)
    and quantum-inspired wave function (ECWF) processing. This connection is crucial
    for integrating associative memory with mathematical reasoning under uncertainty.
    """
    
    def __init__(self, memory_web, ecwf_core, influence_factor=0.3):
        """
        Initialize the bridge between memory web and ECWF.
        
        Args:
            memory_web: Memory web instance
            ecwf_core: ECWF core instance
            influence_factor: Strength of bidirectional influence
        """
        self.memory_web = memory_web
        self.ecwf_core = ecwf_core
        self.influence_factor = influence_factor
        
        # Map concepts to dimensions for translation between systems
        self.concept_dimension_mapping = {}
        
        # Track activation history and resonance patterns
        self.activation_history = {}
        self.resonance_patterns = {}
        
        # Transfer metrics
        self.metrics = {
            "memory_to_ecwf_transfers": 0,
            "ecwf_to_memory_transfers": 0,
            "concepts_activated": 0,
            "wave_modulations": 0,
            "emergent_connections": 0,
            "last_update": time.time()
        }

    # [FIXED]
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Stub processing to maintain interface."""
        print(f"MemoryECWFBridge processing chunk {chunk.chunk_id}")
        return chunk
    
    def initialize_concept_mappings(self, ethical_concepts=None):
        """
        Initialize mappings between memory concepts and ECWF dimensions.
        
        Args:
            ethical_concepts: Optional list of concepts that are primarily ethical in nature
            
        Returns:
            Number of concepts mapped
        """
        # Get all concepts from memory
        concepts = list(self.memory_web.memory_store.keys())
        
        # Get dimension counts
        cog_dims = self.ecwf_core.num_cognitive_dims
        eth_dims = self.ecwf_core.num_ethical_dims
        
        # Create an ethical concept set if provided
        ethical_concept_set = set()
        if ethical_concepts:
            ethical_concept_set = set(c.lower() for c in ethical_concepts)
        
        # Clear existing mappings
        self.concept_dimension_mapping = {}
        
        # Create mappings for each concept - this is where concepts are connected to wave dimensions
        for concept in concepts:
            # Determine if concept is primarily ethical or cognitive
            is_ethical = (
                ethical_concepts and concept.lower() in ethical_concept_set
            ) or self._is_ethical_concept(concept)
            
            dimensions = []
            if is_ethical:
                # Map primarily to ethical dimensions with weighted representation
                # Each concept can influence multiple dimensions to different degrees
                primary_dim = np.random.randint(0, eth_dims)
                dimensions.append(("ethical", primary_dim, 0.8 + np.random.random() * 0.2))  # Primary influence
                
                # Secondary influences on other ethical dimensions
                for _ in range(min(2, eth_dims - 1)):
                    sec_dim = np.random.randint(0, eth_dims)
                    while sec_dim == primary_dim:
                        sec_dim = np.random.randint(0, eth_dims)
                    dimensions.append(("ethical", sec_dim, 0.3 + np.random.random() * 0.3))
                
                # Minor influence on cognitive dimensions
                cog_dim = np.random.randint(0, cog_dims)
                dimensions.append(("cognitive", cog_dim, 0.2 + np.random.random() * 0.2))
            else:
                # Map primarily to cognitive dimensions with weighted representation
                primary_dim = np.random.randint(0, cog_dims)
                dimensions.append(("cognitive", primary_dim, 0.8 + np.random.random() * 0.2))  # Primary influence
                
                # Secondary influences on other cognitive dimensions
                for _ in range(min(2, cog_dims - 1)):
                    sec_dim = np.random.randint(0, cog_dims)
                    while sec_dim == primary_dim:
                        sec_dim = np.random.randint(0, cog_dims)
                    dimensions.append(("cognitive", sec_dim, 0.3 + np.random.random() * 0.3))
                
                # Minor influence on ethical dimensions
                eth_dim = np.random.randint(0, eth_dims)
                dimensions.append(("ethical", eth_dim, 0.1 + np.random.random() * 0.2))
            
            # Store the dimensional mapping for this concept
            self.concept_dimension_mapping[concept] = dimensions
            
            # Initialize activation history for this concept
            self.activation_history[concept] = []
        
        return len(self.concept_dimension_mapping)
    
    def update_memory_from_ecwf(self, cognitive_state, ethical_state, t):
        """
        Update memory based on ECWF state. This is how wave function processing
        influences symbolic memory.
        
        Args:
            cognitive_state: Current cognitive state vector
            ethical_state: Current ethical state vector
            t: Time parameter
            
        Returns:
            Dictionary with memory update information
        """
        # Ensure input arrays are properly shaped
        if cognitive_state.ndim == 1:
            cognitive_state = cognitive_state.reshape(1, 1, -1)
        if ethical_state.ndim == 1:
            ethical_state = ethical_state.reshape(1, 1, -1)
        
        # Compute ECWF
        wave_output = self.ecwf_core.compute_ecwf(cognitive_state, ethical_state, t)
        
        # Extract wave properties
        magnitude = np.abs(wave_output).flatten()
        phase = np.angle(wave_output).flatten()
        entropy = self.ecwf_core.calculate_entropy(wave_output)
        
        # Generate concept activations from wave state - translating mathematical to symbolic
        activations = {}
        
        # Process mappings to determine which concepts get activated by the wave state
        for concept, mappings in self.concept_dimension_mapping.items():
            # Calculate activation based on dimension mappings
            activation = 0.0
            
            for mapping_type, dim_idx, weight in mappings:
                if mapping_type == "cognitive" and dim_idx < len(cognitive_state[0, 0]):
                    # Cognitive dimensions influence
                    activation += cognitive_state[0, 0, dim_idx] * weight
                elif mapping_type == "ethical" and dim_idx < len(ethical_state[0, 0]):
                    # Ethical dimensions influence 
                    activation += ethical_state[0, 0, dim_idx] * weight
            
            # Scale by wave magnitude and entropy
            if len(magnitude) > 0:
                dim_magnitude = magnitude[0]  # Use first magnitude value
                activation *= dim_magnitude
                
                # Reduce activation for high entropy (high uncertainty)
                # This ensures that uncertain states have less influence on memory
                uncertainty_factor = max(0.2, 1.0 - entropy / 5.0)
                activation *= uncertainty_factor
                
                # Apply phase influence (concepts that resonate with the phase get boosted)
                # This implements quantum-inspired interference effects
                phase_influence = 0.5 + 0.5 * np.cos(phase[0])  # 0 to 1 range
                activation *= phase_influence
            
            # Only include significant activations
            if activation > 0.2:
                activations[concept] = min(1.0, activation)
        
        # Update memory with activations
        updated_concepts = []
        created_concepts = []
        emergent_connections = []
        
        # First pass: update existing concepts
        for concept, activation in activations.items():
            if concept in self.memory_web.memory_store:
                # Reinforce existing concept
                old_stability = self.memory_web.memory_store[concept]["stability"]
                # Apply influence factor to control the strength of wave-to-memory influence
                self.memory_web.reinforce_memory(
                    concept, 
                    amount=activation * self.influence_factor
                )
                updated_concepts.append(concept)
            else:
                # Create new concept with moderate initial stability
                self.memory_web.add_thought(
                    concept, 
                    stability=activation * 0.5,
                    metadata={"origin": "wave_emergence", "creation_time": time.time()}
                )
                created_concepts.append(concept)
                
                # Add this new concept to dimension mappings
                # New concepts get random mappings weighted toward the dimensions that created them
                is_ethical = self._is_ethical_concept(concept)
                self._assign_concept_mappings(concept, is_ethical)
            
            # Track activation history
            if concept not in self.activation_history:
                self.activation_history[concept] = []
            self.activation_history[concept].append((time.time(), activation))
        
        # Second pass: connect activated concepts
        # This is how the wave function creates new conceptual relationships
        for concept1, activation1 in activations.items():
            for concept2, activation2 in activations.items():
                if concept1 != concept2:
                    # Determine connection strength based on quantum resonance
                    # Concepts activated by the same wave have stronger connections
                    connection_strength = min(activation1, activation2)
                    
                    # Create or strengthen connection
                    new_connection = self.memory_web.connect_thoughts(
                        concept1, 
                        concept2, 
                        initial_weight=connection_strength
                    )
                    
                    if new_connection:
                        emergent_connections.append((concept1, concept2))
        
        # Update metrics
        self.metrics["ecwf_to_memory_transfers"] += 1
        self.metrics["concepts_activated"] += len(updated_concepts)
        self.metrics["emergent_connections"] += len(emergent_connections)
        self.metrics["last_update"] = time.time()
        
        return {
            "activated_concepts": activations,
            "updated_concepts": updated_concepts,
            "created_concepts": created_concepts,
            "emergent_connections": emergent_connections,
            "wave_magnitude": magnitude.tolist(),
            "wave_phase": phase.tolist(),
            "entropy": entropy
        }
    
    def update_ecwf_from_memory(self, input_concepts):
        """
        Update ECWF parameters based on memory activations. This is how 
        symbolic memory influences wave function processing.
        
        Args:
            input_concepts: List of concepts to activate in memory
            
        Returns:
            Dictionary with ECWF influence information
        """
        # Get related concepts from memory - spreading activation through the network
        all_concepts = set(input_concepts)
        related_concepts = []
        
        for concept in input_concepts:
            related = self.memory_web.retrieve_related_thoughts(concept)
            related_concepts.extend(related)
            all_concepts.add(concept)
        
        # Calculate influence vectors for ECWF parameters
        cognitive_influence = np.zeros(self.ecwf_core.num_cognitive_dims)
        ethical_influence = np.zeros(self.ecwf_core.num_ethical_dims)
        
        # Process retrieved concepts to update wave parameters
        processed_concepts = []
        
        for concept_tuple in related_concepts:
            if isinstance(concept_tuple, tuple):
                concept, relevance = concept_tuple
            else:
                concept, relevance = concept_tuple, 0.5
            
            processed_concepts.append(concept)
            
            # Skip if concept not in mapping
            if concept not in self.concept_dimension_mapping:
                # If an important concept isn't mapped yet, create a mapping for it
                if relevance > 0.5:
                    is_ethical = self._is_ethical_concept(concept)
                    self._assign_concept_mappings(concept, is_ethical)
                else:
                    continue
            
            # Apply concept's influence to dimensions
            for mapping_type, dim_idx, weight in self.concept_dimension_mapping[concept]:
                # Calculate influence based on relevance, weight, and concept stability
                stability = 0.5  # Default value
                if concept in self.memory_web.memory_store:
                    stability = self.memory_web.memory_store[concept]["stability"]
                
                # Memory concepts with high stability and relevance have more influence on the wave function
                influence_value = relevance * weight * stability * self.influence_factor
                
                if mapping_type == "cognitive" and dim_idx < len(cognitive_influence):
                    cognitive_influence[dim_idx] += influence_value
                elif mapping_type == "ethical" and dim_idx < len(ethical_influence):
                    ethical_influence[dim_idx] += influence_value
        
        # Apply influences to ECWF parameters
        self.ecwf_core.update_parameters(
            cognitive_influence=cognitive_influence,
            ethical_influence=ethical_influence,
            factor=self.influence_factor
        )
        
        # Update metrics
        self.metrics["memory_to_ecwf_transfers"] += 1
        self.metrics["wave_modulations"] += 1
        self.metrics["last_update"] = time.time()
        
        return {
            "cognitive_influence": cognitive_influence.tolist(),
            "ethical_influence": ethical_influence.tolist(),
            "processed_concepts": processed_concepts
        }
    
    def bidirectional_update(self, cognitive_state, ethical_state, input_concepts, t):
        """
        Perform full bidirectional update between memory and ECWF.
        This is the primary interface for the full memory-wave integration.
        
        Args:
            cognitive_state: Current cognitive state vector
            ethical_state: Current ethical state vector
            input_concepts: Concepts involved in current processing
            t: Time parameter
            
        Returns:
            Dictionary with comprehensive update information
        """
        # First update ECWF based on memory - memory shapes wave
        ecwf_update = self.update_ecwf_from_memory(input_concepts)
        
        # Then update memory based on ECWF - wave shapes memory
        memory_update = self.update_memory_from_ecwf(cognitive_state, ethical_state, t)
        
        # Detect emergent resonance patterns by comparing influence patterns
        self._detect_resonance_patterns(ecwf_update, memory_update)
        
        return {
            "ecwf_update": ecwf_update,
            "memory_update": memory_update,
            "resonance_patterns": list(self.resonance_patterns.keys())[:5],  # Top 5 patterns
            "timestamp": time.time()
        }
    
    def _detect_resonance_patterns(self, ecwf_update, memory_update):
        """
        Detect emergent resonance patterns between memory and wave systems.
        These patterns reveal deeper conceptual structures.
        
        Args:
            ecwf_update: Update results from memory to ECWF
            memory_update: Update results from ECWF to memory
        """
        # Get concepts from both directions
        memory_concepts = set(ecwf_update.get("processed_concepts", []))
        wave_concepts = set(memory_update.get("activated_concepts", {}).keys())
        
        # Find concepts that resonate in both directions
        resonant_concepts = memory_concepts.intersection(wave_concepts)
        
        # Update resonance patterns
        for concept in resonant_concepts:
            if concept in self.resonance_patterns:
                self.resonance_patterns[concept] += 1
            else:
                self.resonance_patterns[concept] = 1
    
    def _is_ethical_concept(self, concept):
        """
        Determine if a concept is primarily ethical in nature.
        
        Args:
            concept: Concept string to evaluate
            
        Returns:
            Boolean indicating ethical nature
        """
        ethical_keywords = [
            "ethics", "moral", "fair", "justice", "right", 
            "wrong", "good", "bad", "harm", "benefit", "duty",
            "principle", "value", "integrity", "virtue", "character",
            "responsibility", "obligation", "consequence", "autonomy",
            "privacy", "consent", "transparency", "accountability",
            "honesty", "trust", "equality"
        ]
        
        concept_lower = concept.lower()
        return any(keyword in concept_lower for keyword in ethical_keywords)
    
    def _assign_concept_mappings(self, concept, is_ethical):
        """
        Assign dimension mappings for a new concept.
        
        Args:
            concept: Concept string
            is_ethical: Whether the concept is primarily ethical
            
        Returns:
            List of dimension mappings
        """
        # Get dimension counts
        cog_dims = self.ecwf_core.num_cognitive_dims
        eth_dims = self.ecwf_core.num_ethical_dims
        
        dimensions = []
        if is_ethical:
            # Map primarily to ethical dimensions
            primary_dim = np.random.randint(0, eth_dims)
            dimensions.append(("ethical", primary_dim, 0.8 + np.random.random() * 0.2))
            
            # Secondary ethical dimension
            sec_dim = np.random.randint(0, eth_dims)
            while sec_dim == primary_dim and eth_dims > 1:
                sec_dim = np.random.randint(0, eth_dims)
            dimensions.append(("ethical", sec_dim, 0.3 + np.random.random() * 0.3))
            
            # Minor cognitive dimension
            cog_dim = np.random.randint(0, cog_dims)
            dimensions.append(("cognitive", cog_dim, 0.2 + np.random.random() * 0.2))
        else:
            # Map primarily to cognitive dimensions
            primary_dim = np.random.randint(0, cog_dims)
            dimensions.append(("cognitive", primary_dim, 0.8 + np.random.random() * 0.2))
            
            # Secondary cognitive dimension
            sec_dim = np.random.randint(0, cog_dims)
            while sec_dim == primary_dim and cog_dims > 1:
                sec_dim = np.random.randint(0, cog_dims)
            dimensions.append(("cognitive", sec_dim, 0.3 + np.random.random() * 0.3))
            
            # Minor ethical dimension
            eth_dim = np.random.randint(0, eth_dims)
            dimensions.append(("ethical", eth_dim, 0.1 + np.random.random() * 0.2))
        
        # Store the mappings
        self.concept_dimension_mapping[concept] = dimensions
        
        return dimensions
    
    def get_cognitive_state_for_concepts(self, concepts):
        """
        Generate a cognitive state vector based on given concepts.
        This function translates symbolic concepts to a mathematical
        representation for the ECWF.
        
        Args:
            concepts: List of concept strings
            
        Returns:
            Cognitive state vector
        """
        cognitive_state = np.zeros(self.ecwf_core.num_cognitive_dims)
        
        for concept in concepts:
            if concept in self.concept_dimension_mapping:
                for mapping_type, dim_idx, weight in self.concept_dimension_mapping[concept]:
                    if mapping_type == "cognitive" and dim_idx < len(cognitive_state):
                        # Get concept stability for weighting
                        stability = 0.5
                        if concept in self.memory_web.memory_store:
                            stability = self.memory_web.memory_store[concept]["stability"]
                        
                        # Add influence to cognitive dimension
                        cognitive_state[dim_idx] += weight * stability
        
        # Normalize to [0, 1] range
        max_value = np.max(cognitive_state)
        if max_value > 0:
            cognitive_state = cognitive_state / max_value
        
        return cognitive_state
    
    def get_ethical_state_for_concepts(self, concepts):
        """
        Generate an ethical state vector based on given concepts.
        This function translates symbolic ethical concepts to a mathematical
        representation for the ECWF.
        
        Args:
            concepts: List of concept strings
            
        Returns:
            Ethical state vector
        """
        ethical_state = np.zeros(self.ecwf_core.num_ethical_dims)
        
        for concept in concepts:
            if concept in self.concept_dimension_mapping:
                for mapping_type, dim_idx, weight in self.concept_dimension_mapping[concept]:
                    if mapping_type == "ethical" and dim_idx < len(ethical_state):
                        # Get concept stability for weighting
                        stability = 0.5
                        if concept in self.memory_web.memory_store:
                            stability = self.memory_web.memory_store[concept]["stability"]
                        
                        # Add influence to ethical dimension
                        ethical_state[dim_idx] += weight * stability
        
        # Normalize to [0, 1] range
        max_value = np.max(ethical_state)
        if max_value > 0:
            ethical_state = ethical_state / max_value
        
        return ethical_state
    
    def detect_and_create_emergent_concepts(self, wave_output, t, threshold=0.7):
        """
        Detect and create emergent concepts based on wave patterns that don't
        map to existing concepts.
        
        Args:
            wave_output: Output from ECWF computation
            t: Current time parameter
            threshold: Confidence threshold for creating new concepts
            
        Returns:
            List of newly created concepts
        """
        # Extract wave properties
        magnitude = np.abs(wave_output)
        phase = np.angle(wave_output)
        entropy = self.ecwf_core.calculate_entropy(wave_output)
        
        # Only attempt to create emergent concepts if entropy is in the optimal range
        # Too low: not enough complexity for emergence
        # Too high: too chaotic for meaningful patterns
        if entropy < 0.8 or entropy > 3.0:
            return []
        
        # Identify dimension clusters with high activity
        cognitive_dims = self.ecwf_core.num_cognitive_dims
        ethical_dims = self.ecwf_core.num_ethical_dims
        
        # Calculate sensitvities to see which dimensions are most influential
        cognitive_sens, ethical_sens = self.ecwf_core.compute_sensitivities(
            np.ones((1, 1, cognitive_dims)),
            np.ones((1, 1, ethical_dims)),
            t
        )
        
        # Find strongest dimensions
        cog_strongest = np.argsort(cognitive_sens.flatten())[-2:]
        eth_strongest = np.argsort(ethical_sens.flatten())[-2:]
        
        # Check if these strong dimensions map to existing concepts
        matched_concepts = set()
        for concept, mappings in self.concept_dimension_mapping.items():
            for mapping_type, dim_idx, weight in mappings:
                if mapping_type == "cognitive" and dim_idx in cog_strongest:
                    matched_concepts.add(concept)
                elif mapping_type == "ethical" and dim_idx in eth_strongest:
                    matched_concepts.add(concept)
        
        # If strong pattern doesn't match existing concepts well, create a new one
        if len(matched_concepts) < 2 and magnitude.mean() > threshold:
            # Create emergent concept name based on related concepts
            if matched_concepts:
                related_concept = list(matched_concepts)[0]
                concept_base = f"Emergent_{related_concept}"
            else:
                # Create completely new concept
                concept_base = f"Emergent_Concept_{len(self.resonance_patterns) + 1}"
            
            # Add timestamp to make name unique
            timestamp = int(time.time())
            new_concept = f"{concept_base}_{timestamp}"
            
            # Create mappings for the new concept based on the strong dimensions
            dimensions = []
            # Add cognitive dimensions
            for dim in cog_strongest:
                dimensions.append(("cognitive", int(dim), 0.8 + np.random.random() * 0.2))
            # Add ethical dimensions
            for dim in eth_strongest:
                dimensions.append(("ethical", int(dim), 0.7 + np.random.random() * 0.3))
            
            # Add concept to memory
            self.memory_web.add_thought(
                new_concept,
                stability=0.5,  # Moderate initial stability
                metadata={
                    "origin": "wave_emergence",
                    "creation_time": time.time(),
                    "entropy": float(entropy),
                    "magnitude": float(magnitude.mean())
                }
            )
            
            # Add concept to dimension mappings
            self.concept_dimension_mapping[new_concept] = dimensions
            
            # Connect to related concepts if any
            for concept in matched_concepts:
                self.memory_web.connect_thoughts(new_concept, concept, 0.6)
            
            return [new_concept]
        
        return []
    
    def get_resonance_info(self):
        """
        Get information about the resonance patterns between memory and ECWF.
        
        Returns:
            Dictionary with resonance information
        """
        # Sort patterns by frequency
        sorted_patterns = sorted(
            self.resonance_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "top_patterns": sorted_patterns[:10],
            "pattern_count": len(self.resonance_patterns),
            "strongest_pattern": sorted_patterns[0] if sorted_patterns else None
        }
    
    def get_metrics(self):
        """
        Get bridge performance metrics.
        
        Returns:
            Dictionary of metrics
        """
        # Create advanced metrics
        transfer_ratio = (
            self.metrics["memory_to_ecwf_transfers"] / 
            max(1, self.metrics["ecwf_to_memory_transfers"])
        )
        
        average_activations = (
            self.metrics["concepts_activated"] / 
            max(1, self.metrics["ecwf_to_memory_transfers"])
        )
        
        advanced_metrics = {
            "transfer_ratio": transfer_ratio,
            "average_activations": average_activations,
            "emergence_rate": self.metrics["emergent_connections"] / max(1, self.metrics["concepts_activated"]),
            "total_transfers": self.metrics["memory_to_ecwf_transfers"] + self.metrics["ecwf_to_memory_transfers"]
        }
        
        # Combine with basic metrics
        metrics = dict(self.metrics)
        metrics.update(advanced_metrics)
        
        return metrics