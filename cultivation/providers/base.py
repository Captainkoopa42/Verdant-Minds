"""Provider protocol for cultivation text generation."""

from __future__ import annotations

from typing import Protocol


class Provider(Protocol):
    """Protocol for text generation backends used by cultivation."""

    def generate(self, prompt: str, *, seed: int | None = None) -> str:
        """Generate a text completion for *prompt*."""
        ...
