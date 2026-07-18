"""Bridge subpackage – connects memory backends to the ECWF engine."""

from ethomorphic.bridge.bridge import EthomorphicBridge, MemoryBackend

__all__ = ["EthomorphicBridge", "MemoryBackend"]
