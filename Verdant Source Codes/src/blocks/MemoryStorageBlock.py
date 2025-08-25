import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from collections import OrderedDict

from src.core.cognitive_chunk import CognitiveChunk


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
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        """
        Initialize the memory storage block.
        
        Args:
            max_size: Maximum number of items to store before eviction
            default_ttl: Default time-to-live in seconds for items (None means no expiration)
        """
        self._store: OrderedDict = OrderedDict()
        self._expiry: Dict[str, float] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
            "inserts": 0,
            "updates": 0,
        }

    # [FIXED]
    def process_chunk(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Stub processing method for compatibility."""
        print(f"MemoryStorageBlock processing chunk {chunk.chunk_id}")
        return chunk
    
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
            # Proactively clean up expired entries so size and stats remain
            # accurate even if this method is the only one being called. This
            # ensures stale items are removed before we attempt to fetch the
            # requested key.
            self._cleanup_expired()

            # Check if the key exists after cleanup
            if key not in self._store:
                self._stats["misses"] += 1
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
            # Ensure expired items are removed so metrics reflect the current
            # state of the cache. Without this cleanup, stale entries could
            # cause the reported size to be inaccurate.
            self._cleanup_expired()

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