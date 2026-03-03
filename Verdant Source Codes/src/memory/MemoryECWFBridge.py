import itertools
import numpy as np
import time
import warnings
from typing import Dict, List, Tuple, Optional, Any, Set

# Try to import sentence-transformers; fall back gracefully
try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False

# Try to import sklearn PCA; fall back gracefully
try:
    from sklearn.decomposition import PCA
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

class MemoryECWFBridge:
    """
    Bridge between MemoryWeb and ECWFCore for the Unified Synthetic Mind.

    Enables bidirectional flow between symbolic knowledge representation (MemoryWeb)
    and quantum-inspired wave function (ECWF) processing. This connection is crucial
    for integrating associative memory with mathematical reasoning under uncertainty.

    Concept-dimension mapping uses semantic embeddings (sentence-transformers) projected
    via PCA to the ECWF dimension space, ensuring that semantically related concepts
    map to nearby regions in the wave function. Falls back to random mapping when
    sentence-transformers or scikit-learn are unavailable.
    """

    def __init__(self, memory_web, ecwf_core, influence_factor=0.3, edge_policy: str = "default"):
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
        self.edge_policy = edge_policy

        # Map concepts to dimensions for translation between systems
        self.concept_dimension_mapping = {}

        # Track activation history and resonance patterns
        self.activation_history = {}
        self.resonance_patterns = {}

        # Semantic embedding state
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self._pca_model = None
        self._semantic_available = False
        self._encoder = None

        # Transfer metrics
        self.metrics = {
            "memory_to_ecwf_transfers": 0,
            "ecwf_to_memory_transfers": 0,
            "concepts_activated": 0,
            "wave_modulations": 0,
            "emergent_connections": 0,
            "last_update": time.time()
        }

    # =========================================================================
    # Semantic Embedding Infrastructure
    # =========================================================================

    def _build_semantic_mapping(
        self, concepts: List[str]
    ) -> Dict[str, List[Tuple[str, int, float]]]:
        """
        Build semantically meaningful concept-dimension mappings using
        sentence-transformer embeddings projected via PCA.

        Args:
            concepts: List of concept name strings

        Returns:
            Mapping dictionary for all concepts that were projected. Empty
            dict indicates semantic mapping is unavailable and callers should
            use fallback logic.
        """
        if not concepts:
            return {}

        if not (_HAS_SENTENCE_TRANSFORMERS and _HAS_SKLEARN):
            if not _HAS_SENTENCE_TRANSFORMERS:
                warnings.warn(
                    "sentence-transformers not available; falling back to random "
                    "concept-dimension mapping. Install with: "
                    "pip install sentence-transformers",
                    stacklevel=2
                )
            if not _HAS_SKLEARN:
                warnings.warn(
                    "scikit-learn not available for PCA; falling back to random "
                    "concept-dimension mapping. Install with: "
                    "pip install scikit-learn",
                    stacklevel=2
                )
            self._semantic_available = False
            return {}

        try:
            # Load the encoder (cached across calls)
            if self._encoder is None:
                self._encoder = SentenceTransformer("all-MiniLM-L6-v2")

            # Encode all concept names
            embeddings = self._encoder.encode(concepts, show_progress_bar=False)
            embeddings = np.array(embeddings, dtype=np.float64)

            # Cache raw embeddings
            for i, concept in enumerate(concepts):
                self._embedding_cache[concept] = embeddings[i]

            # Target dimensionality = cognitive + ethical dims
            cog_dims = self.ecwf_core.num_cognitive_dims
            eth_dims = self.ecwf_core.num_ethical_dims
            total_dims = cog_dims + eth_dims

            # PCA projection
            n_components = min(total_dims, len(concepts), embeddings.shape[1])
            self._pca_model = PCA(n_components=n_components)
            projected = self._pca_model.fit_transform(embeddings)

            # Pad if we have fewer components than total_dims
            if projected.shape[1] < total_dims:
                pad_width = total_dims - projected.shape[1]
                projected = np.hstack([
                    projected,
                    np.zeros((projected.shape[0], pad_width))
                ])

            # Build mappings from the projected vectors
            semantic_mapping: Dict[str, List[Tuple[str, int, float]]] = {}
            for i, concept in enumerate(concepts):
                vec = projected[i]
                cog_weights = vec[:cog_dims]
                eth_weights = vec[cog_dims:cog_dims + eth_dims]

                dimensions = self._weights_to_mappings(cog_weights, eth_weights)
                semantic_mapping[concept] = dimensions

            self._semantic_available = True
            return semantic_mapping

        except Exception as e:
            warnings.warn(
                f"Semantic embedding mapping failed ({e}); "
                f"falling back to random mapping.",
                stacklevel=2
            )
            self._semantic_available = False
            return {}

    def _weights_to_mappings(
        self, cog_weights: np.ndarray, eth_weights: np.ndarray
    ) -> List[Tuple[str, int, float]]:
        """
        Convert raw PCA weight vectors into the (type, dim_idx, weight) mapping
        format used by the rest of the bridge.

        Normalizes absolute values to the [0.1, 1.0] range.
        """
        dimensions = []

        for dim_idx, w in enumerate(cog_weights):
            dimensions.append(("cognitive", int(dim_idx), float(w)))

        for dim_idx, w in enumerate(eth_weights):
            dimensions.append(("ethical", int(dim_idx), float(w)))

        # Normalize weights to [0.1, 1.0] by absolute value
        abs_weights = [abs(d[2]) for d in dimensions]
        max_w = max(abs_weights) if abs_weights else 1.0
        min_w = min(abs_weights) if abs_weights else 0.0

        if max_w - min_w > 1e-10:
            dimensions = [
                (dtype, idx, 0.1 + 0.9 * (abs(w) - min_w) / (max_w - min_w))
                for dtype, idx, w in dimensions
            ]
        else:
            # All weights equal – assign uniform mid-range weight
            dimensions = [
                (dtype, idx, 0.5)
                for dtype, idx, w in dimensions
            ]

        return dimensions

    def _project_single_embedding(self, concept: str, embedding: np.ndarray) -> List[Tuple[str, int, float]]:
        """
        Project a single concept embedding through the stored PCA model
        to produce dimension mappings.

        Args:
            concept: Concept name
            embedding: Raw embedding vector

        Returns:
            List of (type, dim_idx, weight) tuples
        """
        cog_dims = self.ecwf_core.num_cognitive_dims
        eth_dims = self.ecwf_core.num_ethical_dims
        total_dims = cog_dims + eth_dims

        projected = self._pca_model.transform(embedding.reshape(1, -1))[0]

        # Pad if needed
        if len(projected) < total_dims:
            projected = np.concatenate([
                projected,
                np.zeros(total_dims - len(projected))
            ])

        cog_weights = projected[:cog_dims]
        eth_weights = projected[cog_dims:cog_dims + eth_dims]

        return self._weights_to_mappings(cog_weights, eth_weights)

    def get_semantic_similarity(self, concept_a: str, concept_b: str) -> float:
        """
        Compute cosine similarity between two concepts using cached embeddings.

        Args:
            concept_a: First concept name
            concept_b: Second concept name

        Returns:
            Cosine similarity in [-1, 1], or 0.0 if embeddings unavailable
        """
        emb_a = self._embedding_cache.get(concept_a)
        emb_b = self._embedding_cache.get(concept_b)

        if self._encoder is None and _HAS_SENTENCE_TRANSFORMERS:
            try:
                self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self._encoder = None

        if emb_a is None and self._encoder is not None:
            try:
                emb_a = np.array(
                    self._encoder.encode([concept_a], show_progress_bar=False)[0],
                    dtype=np.float64
                )
                self._embedding_cache[concept_a] = emb_a
            except Exception:
                emb_a = None

        if emb_b is None and self._encoder is not None:
            try:
                emb_b = np.array(
                    self._encoder.encode([concept_b], show_progress_bar=False)[0],
                    dtype=np.float64
                )
                self._embedding_cache[concept_b] = emb_b
            except Exception:
                emb_b = None

        if emb_a is None or emb_b is None:
            return 0.0

        norm_a = np.linalg.norm(emb_a)
        norm_b = np.linalg.norm(emb_b)

        if norm_a < 1e-10 or norm_b < 1e-10:
            return 0.0

        return float(np.dot(emb_a, emb_b) / (norm_a * norm_b))

    # =========================================================================
    # Core Mapping Initialization
    # =========================================================================

    def initialize_concept_mappings(self, ethical_concepts=None):
        """
        Initialize mappings between memory concepts and ECWF dimensions.

        Uses semantic embeddings (sentence-transformers + PCA) when available,
        falling back to random assignment otherwise.

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

        # Attempt semantic mapping first
        semantic_mapping = self._build_semantic_mapping(concepts)
        if semantic_mapping:
            self.concept_dimension_mapping.update(semantic_mapping)
            # Semantic mapping succeeded — initialize activation history
            for concept in concepts:
                self.activation_history[concept] = []
            return len(self.concept_dimension_mapping)

        # Fallback: random mapping (original behavior)
        for concept in concepts:
            # Determine if concept is primarily ethical or cognitive
            is_ethical = (
                ethical_concepts and concept.lower() in ethical_concept_set
            ) or self._is_ethical_concept(concept)

            dimensions = []
            if is_ethical:
                primary_dim = np.random.randint(0, eth_dims)
                dimensions.append(("ethical", primary_dim, 0.8 + np.random.random() * 0.2))

                for _ in range(min(2, eth_dims - 1)):
                    sec_dim = np.random.randint(0, eth_dims)
                    while sec_dim == primary_dim:
                        sec_dim = np.random.randint(0, eth_dims)
                    dimensions.append(("ethical", sec_dim, 0.3 + np.random.random() * 0.3))

                cog_dim = np.random.randint(0, cog_dims)
                dimensions.append(("cognitive", cog_dim, 0.2 + np.random.random() * 0.2))
            else:
                primary_dim = np.random.randint(0, cog_dims)
                dimensions.append(("cognitive", primary_dim, 0.8 + np.random.random() * 0.2))

                for _ in range(min(2, cog_dims - 1)):
                    sec_dim = np.random.randint(0, cog_dims)
                    while sec_dim == primary_dim:
                        sec_dim = np.random.randint(0, cog_dims)
                    dimensions.append(("cognitive", sec_dim, 0.3 + np.random.random() * 0.3))

                eth_dim = np.random.randint(0, eth_dims)
                dimensions.append(("ethical", eth_dim, 0.1 + np.random.random() * 0.2))

            self.concept_dimension_mapping[concept] = dimensions
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
                    effective_policy = getattr(self.memory_web, "edge_policy", self.edge_policy)
                    new_connection = self.memory_web.connect_thoughts(
                        concept1,
                        concept2,
                        initial_weight=connection_strength,
                        edge_policy=effective_policy
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
        Assign dimension mappings for a new concept added after initialization.

        If semantic embedding infrastructure is available, encodes the concept
        and projects through the stored PCA model. Otherwise falls back to
        random assignment.

        Args:
            concept: Concept string
            is_ethical: Whether the concept is primarily ethical (used only in fallback)

        Returns:
            List of dimension mappings
        """
        # Rebuild semantic mapping to include this concept when possible.
        all_concepts = list(self.memory_web.memory_store.keys())
        if concept not in all_concepts:
            all_concepts.append(concept)
        semantic_mapping = self._build_semantic_mapping(all_concepts)
        if semantic_mapping and concept in semantic_mapping:
            self.concept_dimension_mapping.update(semantic_mapping)
            return semantic_mapping[concept]

        # Try semantic projection through an existing PCA model if available.
        if self._semantic_available and self._encoder is not None and self._pca_model is not None:
            try:
                embedding = self._encoder.encode([concept], show_progress_bar=False)
                embedding = np.array(embedding[0], dtype=np.float64)
                self._embedding_cache[concept] = embedding
                dimensions = self._project_single_embedding(concept, embedding)
                self.concept_dimension_mapping[concept] = dimensions
                return dimensions
            except Exception:
                pass  # Fall through to random

        # Fallback: random assignment
        cog_dims = self.ecwf_core.num_cognitive_dims
        eth_dims = self.ecwf_core.num_ethical_dims

        dimensions = []
        if is_ethical:
            primary_dim = np.random.randint(0, eth_dims)
            dimensions.append(("ethical", primary_dim, 0.8 + np.random.random() * 0.2))

            sec_dim = np.random.randint(0, eth_dims)
            while sec_dim == primary_dim and eth_dims > 1:
                sec_dim = np.random.randint(0, eth_dims)
            dimensions.append(("ethical", sec_dim, 0.3 + np.random.random() * 0.3))

            cog_dim = np.random.randint(0, cog_dims)
            dimensions.append(("cognitive", cog_dim, 0.2 + np.random.random() * 0.2))
        else:
            primary_dim = np.random.randint(0, cog_dims)
            dimensions.append(("cognitive", primary_dim, 0.8 + np.random.random() * 0.2))

            sec_dim = np.random.randint(0, cog_dims)
            while sec_dim == primary_dim and cog_dims > 1:
                sec_dim = np.random.randint(0, cog_dims)
            dimensions.append(("cognitive", sec_dim, 0.3 + np.random.random() * 0.3))

            eth_dim = np.random.randint(0, eth_dims)
            dimensions.append(("ethical", eth_dim, 0.1 + np.random.random() * 0.2))

        self.concept_dimension_mapping[concept] = dimensions

        return dimensions

    def _assign_emergent_concept_mappings(
        self, new_concept: str, parent_concepts: List[str]
    ) -> List[Tuple[str, int, float]]:
        """
        Assign dimension mappings for an emergent concept by averaging
        its parent concept embeddings and projecting through PCA.

        Falls back to random mapping if semantic infrastructure is unavailable.

        Args:
            new_concept: Name of the new emergent concept
            parent_concepts: List of parent concept names that were combined

        Returns:
            List of (type, dim_idx, weight) tuples
        """
        if self._semantic_available and self._pca_model is not None:
            # Collect parent embeddings that exist in the cache
            parent_embeddings = [
                self._embedding_cache[c]
                for c in parent_concepts
                if c in self._embedding_cache
            ]

            if parent_embeddings:
                # Average parent embeddings to create the emergent concept embedding
                avg_embedding = np.mean(parent_embeddings, axis=0)
                self._embedding_cache[new_concept] = avg_embedding
                dimensions = self._project_single_embedding(new_concept, avg_embedding)
                self.concept_dimension_mapping[new_concept] = dimensions
                return dimensions

        # Fallback: use random assignment
        is_ethical = self._is_ethical_concept(new_concept)
        return self._assign_concept_mappings(new_concept, is_ethical)

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

    def detect_and_create_emergent_concepts(self, wave_output, t, threshold=0.15):
        """
        Detect and create emergent concepts based on wave patterns that don't
        map to existing concepts.

        When semantic embeddings are available, prefers combinations of concepts
        with LOW semantic similarity that still co-activate — surprising
        combinations are more interesting than obvious ones.

        Args:
            wave_output: Output from ECWF computation
            t: Current time parameter
            threshold: Confidence threshold for creating new concepts

        Returns:
            List of newly created concepts
        """
        # Compute sensitivities over all dimensions
        cognitive_dims = self.ecwf_core.num_cognitive_dims
        ethical_dims = self.ecwf_core.num_ethical_dims
        cog_state = np.ones((1, 1, cognitive_dims)) * 0.5
        eth_state = np.ones((1, 1, ethical_dims)) * 0.5
        cog_sens, eth_sens = self.ecwf_core.compute_sensitivities(
            cog_state, eth_state, t
        )

        # Compute Shannon entropy over sensitivity distribution
        sens_vector = np.abs(np.concatenate([
            cog_sens.flatten(), eth_sens.flatten()
        ]))
        sens_norm = sens_vector / (sens_vector.sum() + 1e-10)
        entropy = float(-np.sum(sens_norm * np.log(sens_norm + 1e-10)))

        # Magnitude from mean sensitivity
        magnitude_scalar = float(sens_vector.mean())

        # Keep wave_output for phase
        phase = np.angle(wave_output)

        # Only attempt to create emergent concepts if entropy is in the optimal range
        # Too low: not enough complexity for emergence
        # Too high: too chaotic for meaningful patterns
        if entropy < 0.3 or entropy > 3.0:
            return []

        # Identify dimension clusters with high activity
        cognitive_sens, ethical_sens = cog_sens, eth_sens

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

        # Get top matched concepts by activation strength in MemoryWeb
        try:
            def _safe_stability(node):
                raw = node.get('stability', 0.5)
                if isinstance(raw, dict):
                    raw = raw.get('value', raw.get('score', 0.5))
                try:
                    return float(raw)
                except (TypeError, ValueError):
                    return 0.5

            scored_concepts = []
            for concept in matched_concepts:
                try:
                    node = self.memory_web.graph.nodes.get(concept, {})
                    strength = _safe_stability(node)
                    scored_concepts.append((concept, strength))
                except Exception:
                    scored_concepts.append((concept, 0.5))

            # When semantic embeddings are available, prefer combinations of
            # concepts with LOW semantic similarity — surprising co-activations
            # produce more interesting emergent concepts than obvious ones.
            if self._semantic_available and len(scored_concepts) > 3:
                # Score each concept by a blend of stability and "surprise" potential
                # (inverse average similarity to other matched concepts)
                surprise_scored = []
                concept_names = [c for c, _ in scored_concepts]
                for concept, strength in scored_concepts:
                    similarities = [
                        self.get_semantic_similarity(concept, other)
                        for other in concept_names
                        if other != concept
                    ]
                    avg_sim = np.mean(similarities) if similarities else 0.0
                    # Surprise = inverse similarity; blend with stability
                    surprise = 1.0 - avg_sim
                    blended_score = 0.5 * strength + 0.5 * surprise
                    surprise_scored.append((concept, blended_score))
                surprise_scored.sort(key=lambda x: x[1], reverse=True)
                top_concepts = [c for c, _ in surprise_scored[:3]]
            else:
                # Fallback: sort by strength, take top 3
                scored_concepts.sort(key=lambda x: x[1], reverse=True)
                top_concepts = [c for c, _ in scored_concepts[:3]]

            # Name using the two semantically most distant co-activated concepts.
            naming_pair = top_concepts[:2]
            if self._semantic_available and len(top_concepts) >= 2:
                pair_similarities = []
                for concept_a, concept_b in itertools.combinations(top_concepts, 2):
                    pair_similarities.append(
                        (
                            self.get_semantic_similarity(concept_a, concept_b),
                            concept_a,
                            concept_b
                        )
                    )
                if pair_similarities:
                    pair_similarities.sort(key=lambda x: x[0])
                    _, c1, c2 = pair_similarities[0]
                    naming_pair = [c1, c2]
        except Exception:
            top_concepts = list(matched_concepts)[:3]
            naming_pair = top_concepts[:2]

        # Create a combination key from top concepts
        combo_key = "_x_".join(sorted(top_concepts))

        # Only create emergent concept if this combination is new
        if combo_key not in self.resonance_patterns and magnitude_scalar > threshold:
            self.resonance_patterns[combo_key] = {
                "concepts": top_concepts,
                "created_at": time.time(),
                "magnitude": magnitude_scalar
            }

            # Name the emergent concept after the combination
            concept_base = f"Emergent_{'_'.join(naming_pair)}"
            timestamp = int(time.time())
            new_concept = f"{concept_base}_{timestamp}"

            # Create mappings for the new concept using semantic averaging when available
            if self._semantic_available and self._pca_model is not None:
                dimensions = self._assign_emergent_concept_mappings(new_concept, top_concepts)
            else:
                dimensions = []
                for dim in cog_strongest:
                    dimensions.append(("cognitive", int(dim), 0.8 + np.random.random() * 0.2))
                for dim in eth_strongest:
                    dimensions.append(("ethical", int(dim), 0.7 + np.random.random() * 0.3))
                self.concept_dimension_mapping[new_concept] = dimensions

            # Add concept to memory
            self.memory_web.add_thought(
                new_concept,
                stability=0.5,  # Moderate initial stability
                metadata={
                    "origin": "wave_emergence",
                    "creation_time": time.time(),
                    "entropy": float(entropy),
                    "magnitude": float(magnitude_scalar)
                }
            )

            # Connect to related concepts if any
            for concept in matched_concepts:
                effective_policy = getattr(self.memory_web, "edge_policy", self.edge_policy)
                self.memory_web.connect_thoughts(new_concept, concept, 0.6, edge_policy=effective_policy)

            return [new_concept]

        return []

    def get_resonance_info(self):
        """
        Get information about the resonance patterns between memory and ECWF.

        Returns:
            Dictionary with resonance information
        """
        # Sort patterns by creation timestamp when available, with a safe fallback
        try:
            sorted_patterns = sorted(
                self.resonance_patterns.items(),
                key=lambda x: x[1].get("created_at", 0) if isinstance(x[1], dict) else 0,
                reverse=True
            )
        except (TypeError, AttributeError):
            sorted_patterns = list(self.resonance_patterns.items())

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
            "total_transfers": self.metrics["memory_to_ecwf_transfers"] + self.metrics["ecwf_to_memory_transfers"],
            "semantic_mapping_active": self._semantic_available
        }

        # Combine with basic metrics
        metrics = dict(self.metrics)
        metrics.update(advanced_metrics)

        return metrics
