import os
import sys
import pytest

# Ensure required third-party dependencies are available
pytest.importorskip("networkx")
pytest.importorskip("numpy")

# Add source code path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Verdant Source Codes', 'src'))

from memory.memory_web import MemoryWeb

def test_add_thought_avoids_self_connection():
    """Adding a new thought should not create a self-referential connection."""
    memory = MemoryWeb()
    memory.add_thought('A', stability=0.9)
    memory.add_thought('B', stability=0.8)

    connections = [conn for conn, _ in memory.memory_store['B']['connections']]
    assert 'B' not in connections
    assert not memory.graph.has_edge('B', 'B')
