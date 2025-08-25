import os
import sys
import time

# Add source code path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Verdant Source Codes', 'src'))

from blocks.MemoryStorageBlock import MemoryStorageBlock


def test_get_stats_excludes_expired_items():
    """Expired items should not be counted in statistics."""
    storage = MemoryStorageBlock(default_ttl=0.1)
    storage.set("temp", "value")

    time.sleep(0.2)  # Allow the item to expire
    stats = storage.get_stats()

    assert stats["size"] == 0
    assert stats["expirations"] == 1
