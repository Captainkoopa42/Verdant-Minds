"""Internal compatibility namespace.

This package intentionally points to legacy Verdant-Minds internals.
External consumers should use `verdant_memory.Memory` instead.
"""

from verdant import system as verdant_system

__all__ = ["verdant_system"]
