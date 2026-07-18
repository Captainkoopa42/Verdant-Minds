"""Bridge between a MemoryBackend and the ECWFCore.

Enables bidirectional flow between symbolic knowledge representation and
quantum-inspired wave function processing.  The bridge uses a *protocol*
for memory access so that ``ethomorphic`` has **zero** dependency on any
concrete graph library (e.g. NetworkX).
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

import numpy as np

from ethomorphic.ecwf.core import ECWFCore


# ---------------------------------------------------------------------------
# Memory backend protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class MemoryBackend(Protocol):
    """Protocol that any memory store must implement to work with the bridge."""

    def add_concept(
        self, label: str, stability: float, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a concept node to the store."""
        ...

    def get_concept(self, label: str) -> Optional[Dict[str, Any]]:
        """Return concept data or ``None`` if missing."""
        ...

    def connect(self, label1: str, label2: str, weight: float) -> None:
        """Create or update a weighted edge between two concepts."""
        ...

    def get_neighbors(self, label: str) -> List[str]:
        """Return labels of all neighbours for *label*."""
        ...

    def list_concepts(self) -> List[str]:
        """Return a list of all concept labels in the store."""
        ...

    def reinforce(self, label: str, amount: float) -> None:
        """Increase the stability of *label* by *amount*."""
        ...

    def decay(self, factor: float) -> None:
        """Multiply all stabilities by *factor* (< 1 to decay)."""
        ...


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------

class EthomorphicBridge:
    """Bidirectional bridge between a :class:`MemoryBackend` and an :class:`ECWFCore`.

    Translates symbolic memory activations into wave-function parameter
    updates and vice-versa, producing concept activations from wave state.
    """

    def __init__(
        self,
        memory: MemoryBackend,
        ecwf: ECWFCore,
        *,
        influence_factor: float = 0.3,
    ) -> None:
        """Initialise the bridge.

        Args:
            memory: Any object implementing :class:`MemoryBackend`.
            ecwf: The ECWF engine to bridge with.
            influence_factor: Strength of bidirectional influence.
        """
        self.memory = memory
        self.ecwf = ecwf
        self.influence_factor = influence_factor

        self.concept_dimension_mapping: Dict[str, List[Tuple[str, int, float]]] = {}
        self.activation_history: Dict[str, List[Tuple[float, float]]] = {}
        self.resonance_patterns: Dict[str, Any] = {}
        self._emergent_combo_keys: set[str] = set()

        self.metrics: Dict[str, Any] = {
            "memory_to_ecwf_transfers": 0,
            "ecwf_to_memory_transfers": 0,
            "concepts_activated": 0,
            "wave_modulations": 0,
            "emergent_connections": 0,
            "last_update": time.time(),
        }

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _is_ethical_concept(self, concept: str) -> bool:
        """Return ``True`` if *concept* appears ethical in nature."""
        ethical_keywords = [
            "ethics", "moral", "fair", "justice", "right",
            "wrong", "good", "bad", "harm", "benefit", "duty",
            "principle", "value", "integrity", "virtue", "character",
            "responsibility", "obligation", "consequence", "autonomy",
            "privacy", "consent", "transparency", "accountability",
            "honesty", "trust", "equality",
        ]
        concept_lower = concept.lower()
        return any(kw in concept_lower for kw in ethical_keywords)

    def assign_concept_mappings(self, concept: str, is_ethical: Optional[bool] = None) -> List[Tuple[str, int, float]]:
        """Assign random dimension mappings for a single concept.

        Args:
            concept: Concept label.
            is_ethical: Override ethical classification.  When ``None`` the
                bridge guesses from the label.

        Returns:
            The list of ``(type, dim_idx, weight)`` tuples assigned.
        """
        if is_ethical is None:
            is_ethical = self._is_ethical_concept(concept)

        cog_dims = self.ecwf.num_cognitive_dims
        eth_dims = self.ecwf.num_ethical_dims
        base_seed = int(getattr(self.ecwf, "random_state", 0) or 0)
        digest = hashlib.sha256(f"{concept}|{base_seed}".encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "big") % (2**32))

        dimensions: List[Tuple[str, int, float]] = []

        if is_ethical:
            primary = int(rng.integers(0, eth_dims))
            dimensions.append(("ethical", primary, 0.8 + rng.random() * 0.2))
            for _ in range(min(2, eth_dims - 1)):
                sec = int(rng.integers(0, eth_dims))
                while sec == primary:
                    sec = int(rng.integers(0, eth_dims))
                dimensions.append(("ethical", sec, 0.3 + rng.random() * 0.3))
            dimensions.append(("cognitive", int(rng.integers(0, cog_dims)), 0.2 + rng.random() * 0.2))
        else:
            primary = int(rng.integers(0, cog_dims))
            dimensions.append(("cognitive", primary, 0.8 + rng.random() * 0.2))
            for _ in range(min(2, cog_dims - 1)):
                sec = int(rng.integers(0, cog_dims))
                while sec == primary:
                    sec = int(rng.integers(0, cog_dims))
                dimensions.append(("cognitive", sec, 0.3 + rng.random() * 0.3))
            dimensions.append(("ethical", int(rng.integers(0, eth_dims)), 0.1 + rng.random() * 0.2))

        self.concept_dimension_mapping[concept] = dimensions
        self.activation_history.setdefault(concept, [])
        return dimensions

    def initialize_concept_mappings(self) -> int:
        """Initialise mappings for all concepts currently in memory.

        Returns:
            Number of concepts mapped.
        """
        self.concept_dimension_mapping.clear()
        concepts = self.memory.list_concepts()
        for concept in sorted(concepts, key=str):
            self.assign_concept_mappings(concept)
        return len(self.concept_dimension_mapping)

    # ------------------------------------------------------------------
    # Bidirectional updates
    # ------------------------------------------------------------------

    def update_memory_from_ecwf(
        self,
        cognitive_state: np.ndarray,
        ethical_state: np.ndarray,
        t: float,
    ) -> Dict[str, Any]:
        """Update memory based on ECWF state.

        Args:
            cognitive_state: Current cognitive state vector.
            ethical_state: Current ethical state vector.
            t: Time parameter.

        Returns:
            Dictionary with activation and update information.
        """
        if cognitive_state.ndim == 1:
            cognitive_state = cognitive_state.reshape(1, 1, -1)
        if ethical_state.ndim == 1:
            ethical_state = ethical_state.reshape(1, 1, -1)

        wave_output = self.ecwf.compute_ecwf(cognitive_state, ethical_state, t)

        magnitude = np.abs(wave_output).flatten()
        phase = np.angle(wave_output).flatten()
        entropy = self.ecwf.calculate_entropy(wave_output)

        activations: Dict[str, float] = {}

        active_concepts = (
            self.memory.list_active_concepts()
            if hasattr(self.memory, "list_active_concepts")
            else self.memory.list_concepts()
        )
        for concept in sorted(active_concepts, key=str):
            mappings = self.concept_dimension_mapping.get(concept)
            if mappings is None:
                continue
            activation = 0.0
            for mtype, dim_idx, weight in mappings:
                if mtype == "cognitive" and dim_idx < cognitive_state.shape[-1]:
                    activation += cognitive_state[0, 0, dim_idx] * weight
                elif mtype == "ethical" and dim_idx < ethical_state.shape[-1]:
                    activation += ethical_state[0, 0, dim_idx] * weight

            if len(magnitude) > 0:
                activation *= magnitude[0]
                uncertainty_factor = max(0.2, 1.0 - entropy / 5.0)
                activation *= uncertainty_factor
                phase_influence = 0.5 + 0.5 * np.cos(phase[0])
                activation *= phase_influence

            if activation > 0.2:
                activations[concept] = min(1.0, activation)

        updated_concepts: List[str] = []
        created_concepts: List[str] = []

        for concept, activation in activations.items():
            existing = self.memory.get_concept(concept)
            if existing is not None:
                self.memory.reinforce(concept, activation * self.influence_factor)
                updated_concepts.append(concept)
            else:
                self.memory.add_concept(
                    concept,
                    stability=activation * 0.5,
                    metadata={"creation_time": time.time()},
                )
                created_concepts.append(concept)
                self.assign_concept_mappings(concept)

            self.activation_history.setdefault(concept, [])
            self.activation_history[concept].append((time.time(), activation))

        # Connect co-activated concepts
        concepts_list = sorted(activations.keys(), key=str)
        for i, c1 in enumerate(concepts_list):
            for c2 in concepts_list[i + 1:]:
                strength = min(activations[c1], activations[c2])
                self.memory.connect(c1, c2, strength)

        self.metrics["ecwf_to_memory_transfers"] += 1
        self.metrics["concepts_activated"] += len(updated_concepts)
        self.metrics["last_update"] = time.time()

        return {
            "activated_concepts": activations,
            "updated_concepts": updated_concepts,
            "created_concepts": created_concepts,
            "wave_magnitude": magnitude.tolist(),
            "wave_phase": phase.tolist(),
            "entropy": entropy,
        }

    def update_ecwf_from_memory(self, input_concepts: List[str]) -> Dict[str, Any]:
        """Update ECWF parameters based on memory activations.

        Args:
            input_concepts: Concepts to activate.

        Returns:
            Dictionary with influence information.
        """
        cognitive_influence = np.zeros(self.ecwf.num_cognitive_dims)
        ethical_influence = np.zeros(self.ecwf.num_ethical_dims)

        processed: List[str] = []

        for concept in sorted(input_concepts, key=str):
            neighbors = sorted(self.memory.get_neighbors(concept), key=str)
            related = [(concept, 1.0)] + [(n, 0.5) for n in neighbors]

            for rel_concept, relevance in related:
                if rel_concept not in self.concept_dimension_mapping:
                    if relevance > 0.5:
                        self.assign_concept_mappings(rel_concept)
                    else:
                        continue

                processed.append(rel_concept)
                data = self.memory.get_concept(rel_concept)
                stability = data.get("stability", 0.5) if data else 0.5

                for mtype, dim_idx, weight in self.concept_dimension_mapping[rel_concept]:
                    value = relevance * weight * stability * self.influence_factor
                    if mtype == "cognitive" and dim_idx < len(cognitive_influence):
                        cognitive_influence[dim_idx] += value
                    elif mtype == "ethical" and dim_idx < len(ethical_influence):
                        ethical_influence[dim_idx] += value

        self.ecwf.update_parameters(
            cognitive_influence=cognitive_influence,
            ethical_influence=ethical_influence,
            factor=self.influence_factor,
        )

        self.metrics["memory_to_ecwf_transfers"] += 1
        self.metrics["wave_modulations"] += 1
        self.metrics["last_update"] = time.time()

        return {
            "cognitive_influence": cognitive_influence.tolist(),
            "ethical_influence": ethical_influence.tolist(),
            "processed_concepts": processed,
        }

    def bidirectional_update(
        self,
        cognitive_state: np.ndarray,
        ethical_state: np.ndarray,
        input_concepts: List[str],
        t: float,
    ) -> Dict[str, Any]:
        """Perform full bidirectional update between memory and ECWF.

        Args:
            cognitive_state: Current cognitive state vector.
            ethical_state: Current ethical state vector.
            input_concepts: Concepts involved in current processing.
            t: Time parameter.

        Returns:
            Combined update information.
        """
        ecwf_update = self.update_ecwf_from_memory(input_concepts)
        memory_update = self.update_memory_from_ecwf(cognitive_state, ethical_state, t)

        # Detect resonance
        memory_concepts = set(ecwf_update.get("processed_concepts", []))
        wave_concepts = set(memory_update.get("activated_concepts", {}).keys())
        for concept in sorted(memory_concepts & wave_concepts, key=str):
            self.resonance_patterns[concept] = self.resonance_patterns.get(concept, 0) + 1

        return {
            "ecwf_update": ecwf_update,
            "memory_update": memory_update,
            "resonance_patterns": sorted(self.resonance_patterns.keys())[:5],
            "timestamp": time.time(),
        }

    # ------------------------------------------------------------------
    # State vector helpers
    # ------------------------------------------------------------------

    def get_cognitive_state_for_concepts(self, concepts: List[str]) -> np.ndarray:
        """Generate a cognitive state vector for a list of concepts.

        Args:
            concepts: Concept labels.

        Returns:
            Normalised cognitive state vector.
        """
        state = np.zeros(self.ecwf.num_cognitive_dims)
        for concept in concepts:
            if concept not in self.concept_dimension_mapping:
                continue
            data = self.memory.get_concept(concept)
            stability = data.get("stability", 0.5) if data else 0.5
            for mtype, dim_idx, weight in self.concept_dimension_mapping[concept]:
                if mtype == "cognitive" and dim_idx < len(state):
                    state[dim_idx] += weight * stability
        mx = np.max(state)
        if mx > 0:
            state /= mx
        return state

    def get_ethical_state_for_concepts(self, concepts: List[str]) -> np.ndarray:
        """Generate an ethical state vector for a list of concepts.

        Args:
            concepts: Concept labels.

        Returns:
            Normalised ethical state vector.
        """
        state = np.zeros(self.ecwf.num_ethical_dims)
        for concept in concepts:
            if concept not in self.concept_dimension_mapping:
                continue
            data = self.memory.get_concept(concept)
            stability = data.get("stability", 0.5) if data else 0.5
            for mtype, dim_idx, weight in self.concept_dimension_mapping[concept]:
                if mtype == "ethical" and dim_idx < len(state):
                    state[dim_idx] += weight * stability
        mx = np.max(state)
        if mx > 0:
            state /= mx
        return state

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def to_state_dict(self) -> Dict[str, Any]:
        """Serialize bridge state for persistence."""
        return {
            "influence_factor": self.influence_factor,
            "concept_dimension_mapping": {
                concept: [list(mapping) for mapping in mappings]
                for concept, mappings in self.concept_dimension_mapping.items()
            },
            "activation_history": {
                concept: [list(entry) for entry in history]
                for concept, history in self.activation_history.items()
            },
            "resonance_patterns": dict(self.resonance_patterns),
            "metrics": dict(self.metrics),
            "emergent_combo_keys": sorted(self._emergent_combo_keys),
        }

    def from_state_dict(self, state: Dict[str, Any]) -> None:
        """Restore bridge state from a serialized dict."""
        self.influence_factor = float(state.get("influence_factor", self.influence_factor))

        mapping_state = state.get("concept_dimension_mapping", {}) or {}
        self.concept_dimension_mapping = {
            concept: [
                (str(mtype), int(dim_idx), float(weight))
                for mtype, dim_idx, weight in mappings
            ]
            for concept, mappings in mapping_state.items()
        }

        history_state = state.get("activation_history", {}) or {}
        self.activation_history = {
            concept: [(float(ts), float(val)) for ts, val in history]
            for concept, history in history_state.items()
        }

        self.resonance_patterns = dict(state.get("resonance_patterns", {}) or {})
        self.metrics = dict(state.get("metrics", self.metrics) or self.metrics)
        combo_keys = state.get("emergent_combo_keys", []) or []
        self._emergent_combo_keys = {str(key) for key in combo_keys}
