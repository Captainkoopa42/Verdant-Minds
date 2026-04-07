__version__ = "0.4.0"
__all__ = ["system", "cultivation", "ethomorphic", "adapters", "VerdantSystem"]


def __getattr__(name: str):
    if name == "VerdantSystem":
        from .system import VerdantSystem

        return VerdantSystem
    raise AttributeError(name)
