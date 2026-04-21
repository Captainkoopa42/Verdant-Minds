"""Verdant-Memory public package.

Production-oriented persistent memory substrate API for LLM agents.
"""

from verdant_memory.api.memory import Memory
from verdant_memory.schema import MemorySnapshot, ObserveResult, RetrieveResult, UpdateResult

__all__ = [
    "Memory",
    "MemorySnapshot",
    "ObserveResult",
    "RetrieveResult",
    "UpdateResult",
]
