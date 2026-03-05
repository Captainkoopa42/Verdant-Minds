import threading
import time
import math
from typing import Any, Dict, List, Optional, Tuple, Union
from collections import OrderedDict


class MemoryStorageBlock:
    """
    A thread-safe in-memory storage block implementation with expiration and size limits.
    
    This class provides an interface for storing data in memory with features like:
    - Key-value storage with optional TTL (time-to-live)
    - LRU (Least Recently Used) eviction strategy
    - Size-based eviction
    - Thread-safety through locking
    - Statistics and monitoring
    """
    
    def __init__(self, max_size: Union[int, Any] = 1000, default_ttl: Optional[int] = None, memory_bridge: Any = None, use_pconnect_edges: bool = False):
        """
        Initialize the memory storage block.
        
        Args:
            max_size: Maximum number of items to store before eviction
            default_ttl: Default time-to-live in seconds for items (None means no expiration)
        """
        self._store: OrderedDict = OrderedDict()
        self._expiry: Dict[str, float] = {}
        self.memory_bridge = None

        # Support pipeline initialization where memory_bridge may be passed
        # as the first argument (UnifiedSystem uses MemoryStorageBlock(self.memory_bridge)).
        if isinstance(max_size, int):
            self._max_size = max_size
            self.memory_bridge = memory_bridge
        else:
            self._max_size = 1000
            self.memory_bridge = max_size

        self._default_ttl = default_ttl

        self.use_pconnect_edges = bool(use_pconnect_edges)
        if getattr(self, "memory_bridge", None) is not None and hasattr(self.memory_bridge, "edge_policy"):
            self.memory_bridge.edge_policy = "pconnect" if self.use_pconnect_edges else "default"
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
            "inserts": 0,
            "updates": 0,
        }

    def set_memory_bridge(self, bridge: Any) -> None:
        """Attach or update the Memory-ECWF bridge reference."""
        self.memory_bridge = bridge
        if self.memory_bridge is not None and hasattr(self.memory_bridge, "edge_policy"):
            self.memory_bridge.edge_policy = "pconnect" if self.use_pconnect_edges else "default"
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store a value in the memory block.
        
        Args:
            key: The unique identifier for the stored value
            value: The data to store
            ttl: Time-to-live in seconds (None uses the default_ttl, negative means never expire)
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self._lock:
            is_update = key in self._store
            
            # Set the expiration time if applicable
            if ttl is None:
                ttl = self._default_ttl
                
            if ttl is not None and ttl >= 0:
                self._expiry[key] = time.time() + ttl
            elif key in self._expiry:
                del self._expiry[key]  # Remove expiration if ttl is negative
                
            # Add or update the item
            self._store[key] = value
            
            # If this is an update, move the key to the end (most recently used)
            if is_update:
                self._store.move_to_end(key)
                self._stats["updates"] += 1
            else:
                self._stats["inserts"] += 1
                
            # Check if we need to evict items
            self._evict_if_needed()
            
            return True
    
    def get(self, key: str, default: Any = None) -> Tuple[Any, bool]:
        """
        Retrieve a value from the memory block.
        
        Args:
            key: The unique identifier for the stored value
            default: Value to return if key is not found
            
        Returns:
            Tuple[Any, bool]: (value, found_flag)
        """
        with self._lock:
            # Check if the key exists
            if key not in self._store:
                self._stats["misses"] += 1
                return default, False
                
            # Check if the key has expired
            if self._is_expired(key):
                self.delete(key)
                self._stats["misses"] += 1
                self._stats["expirations"] += 1
                return default, False
                
            # Move the accessed key to the end (most recently used)
            self._store.move_to_end(key)
            self._stats["hits"] += 1
            
            return self._store[key], True
    
    def delete(self, key: str) -> bool:
        """
        Remove a value from the memory block.
        
        Args:
            key: The unique identifier to remove
            
        Returns:
            bool: True if the key was found and deleted, False otherwise
        """
        with self._lock:
            if key in self._store:
                del self._store[key]
                if key in self._expiry:
                    del self._expiry[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all items from the memory block."""
        with self._lock:
            self._store.clear()
            self._expiry.clear()
    
    def keys(self) -> List[str]:
        """
        Get all valid keys in the storage block.
        
        Returns:
            List[str]: List of all non-expired keys
        """
        with self._lock:
            self._cleanup_expired()
            return list(self._store.keys())
    
    def size(self) -> int:
        """
        Get the current number of items in the storage block.
        
        Returns:
            int: Number of items currently stored
        """
        with self._lock:
            self._cleanup_expired()
            return len(self._store)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get usage statistics.
        
        Returns:
            Dict[str, int]: Dictionary containing usage statistics
        """
        with self._lock:
            stats = self._stats.copy()
            stats["size"] = len(self._store)
            return stats
    
    def set_max_size(self, max_size: int) -> None:
        """
        Update the maximum size and evict items if needed.
        
        Args:
            max_size: New maximum size
        """
        with self._lock:
            self._max_size = max_size
            self._evict_if_needed()
    
    def _is_expired(self, key: str) -> bool:
        """Check if a key has expired."""
        if key in self._expiry and time.time() > self._expiry[key]:
            return True
        return False
    
    def _cleanup_expired(self) -> int:
        """
        Remove all expired items from the store.
        
        Returns:
            int: Number of items removed
        """
        now = time.time()
        expired_keys = [k for k, exp in self._expiry.items() if exp <= now]
        
        for key in expired_keys:
            if key in self._store:
                del self._store[key]
            del self._expiry[key]
            self._stats["expirations"] += 1
            
        return len(expired_keys)
    
    def _evict_if_needed(self) -> int:
        """
        Evict items if the store exceeds the maximum size.
        
        Returns:
            int: Number of items evicted
        """
        # First clean up any expired items
        self._cleanup_expired()
        
        # Then evict based on LRU if still needed
        eviction_count = 0
        while len(self._store) > self._max_size:
            # Remove the first item (least recently used)
            oldest_key, _ = self._store.popitem(last=False)
            if oldest_key in self._expiry:
                del self._expiry[oldest_key]
            eviction_count += 1
            self._stats["evictions"] += 1
            
        return eviction_count

    def process_chunk(self, chunk):
        """
        Process a cognitive chunk for memory/wave pipeline compatibility.

        Always writes memory_section and wave_function_section with
        safe defaults when upstream sections are missing.
        """
        pattern_data = chunk.get_section_content("pattern_recognition_section") or {}

        raw_concepts = []

        for concept in pattern_data.get("concepts", []) or []:
            if isinstance(concept, dict):
                value = concept.get("value")
                if value:
                    raw_concepts.append(str(value))
            elif concept is not None:
                raw_concepts.append(str(concept))

        for concept in pattern_data.get("extracted_concepts", []) or []:
            if isinstance(concept, dict):
                value = concept.get("value")
                if value:
                    raw_concepts.append(str(value))
            elif concept is not None:
                raw_concepts.append(str(concept))

        for keyword in pattern_data.get("keywords", []) or []:
            if keyword is not None:
                raw_concepts.append(str(keyword))

        concepts = list(dict.fromkeys(raw_concepts))

        retrieved_concepts = []
        activation_levels: Dict[str, float] = {}

        for concept in concepts:
            stored, found = self.get(concept, default=None)
            if found:
                retrieved_concepts.append(concept)
                if isinstance(stored, dict):
                    activation_levels[concept] = float(stored.get("activation", 0.7))
                else:
                    activation_levels[concept] = 0.7
            else:
                retrieved_concepts.append(concept)
                activation_levels[concept] = 0.5
                self.set(concept, {"activation": 0.5})

        activated_concepts = dict(activation_levels)

        wave_properties: Dict[str, Any] = {
            "magnitude": [0.0],
            "phase": [0.0],
            "entropy": 0.5
        }

        if getattr(self, "memory_bridge", None) is not None and concepts:
            try:
                bridge_result = self.memory_bridge.update_ecwf_from_memory(concepts)
                if isinstance(bridge_result, dict):
                    cognitive_influence_raw = bridge_result.get("cognitive_influence", [])
                    cognitive_influence_values = []
                    for value in cognitive_influence_raw:
                        try:
                            numeric_value = float(value)
                        except (TypeError, ValueError):
                            continue
                        if math.isfinite(numeric_value):
                            cognitive_influence_values.append(numeric_value)

                    if cognitive_influence_values:
                        wave_properties["magnitude"] = [
                            float(sum(cognitive_influence_values) / len(cognitive_influence_values))
                        ]

                        n_values = len(cognitive_influence_values)
                        abs_values = [abs(v) for v in cognitive_influence_values]
                        total_abs = sum(abs_values)
                        if n_values > 1 and total_abs > 0.0:
                            probabilities = [v / total_abs for v in abs_values if v > 0.0]
                            entropy = -sum(p * math.log2(p) for p in probabilities)
                            wave_properties["entropy"] = float(entropy / math.log2(n_values))
                        elif n_values == 1:
                            wave_properties["entropy"] = 0.0

                    wave_properties["bridge_update"] = {
                        "processed_concepts": bridge_result.get("processed_concepts", []),
                        "cognitive_influence": cognitive_influence_values,
                        "ethical_influence": bridge_result.get("ethical_influence", [])
                    }
            except Exception:
                pass

        # Thermodynamic phase-aware memory management from current T_g
        processing_metrics = chunk.get_section_content("processing_metrics_section") or {}
        raw_tg = processing_metrics.get("glass_transition_temp", 0.5)
        try:
            t_g = float(raw_tg)
        except (TypeError, ValueError):
            t_g = 0.5

        if t_g < 0.4:
            phase = "Rigid"
            decay_factor = 0.005
            reinforcement_amount = 0.05
        elif t_g <= 0.6:
            phase = "Flexible"
            decay_factor = 0.01
            reinforcement_amount = 0.1
        else:
            phase = "Chaotic"
            decay_factor = 0.02
            reinforcement_amount = 0.15

        concepts_reinforced = 0
        memory_web = getattr(getattr(self, "memory_bridge", None), "memory_web", None)
        if memory_web is not None:
            try:
                memory_web.decay_memories(decay_factor=decay_factor)
            except Exception:
                pass

            for concept in activated_concepts.keys():
                try:
                    reinforced_value = memory_web.reinforce_memory(concept, amount=reinforcement_amount)
                    if reinforced_value > 0.0:
                        concepts_reinforced += 1
                except Exception:
                    continue

        memory_section = {
            "retrieved_concepts": retrieved_concepts,
            "activated_concepts": activated_concepts,
            "activation_levels": activation_levels,
            "wave_properties": wave_properties,
            "phase_memory_management": {
                "phase": phase,
                "decay_factor_applied": decay_factor,
                "reinforcement_applied": reinforcement_amount,
                "concepts_reinforced": concepts_reinforced
            },
            "novelty_score": 0.0
        }

        wave_function_section = {
            "magnitude": (wave_properties.get("magnitude") or [None])[0],
            "phase": (wave_properties.get("phase") or [None])[0],
            "entropy": wave_properties.get("entropy")
        }

        chunk.update_section("memory_section", memory_section)
        chunk.update_section("wave_function_section", wave_function_section)

        return chunk


# Example usage
if __name__ == "__main__":
    # Create a memory storage block with max 5 items and default TTL of 10 seconds
    storage = MemoryStorageBlock(max_size=5, default_ttl=10)
    
    # Add some items
    storage.set("key1", "value1")
    storage.set("key2", "value2")
    storage.set("key3", "value3", ttl=20)  # Custom TTL
    storage.set("key4", "value4", ttl=-1)  # Never expires
    
    # Retrieve items
    value, found = storage.get("key1")
    print(f"key1: {value}, found: {found}")
    
    # Get statistics
    print(f"Stats: {storage.get_stats()}")
    
    # Check keys
    print(f"Current keys: {storage.keys()}")
    
    # Add more items to trigger eviction
    storage.set("key5", "value5")
    storage.set("key6", "value6")  # This will evict the oldest item
    
    # Check keys after eviction
    print(f"Keys after eviction: {storage.keys()}")
    
    # Wait for expiration
    print("Waiting for some items to expire...")
    time.sleep(11)  # Wait for items with default TTL to expire
    
    # Check keys after expiration
    print(f"Keys after expiration: {storage.keys()}")
    
    # Final stats
    print(f"Final stats: {storage.get_stats()}")
