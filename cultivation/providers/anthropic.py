"""Optional Anthropic provider."""

from __future__ import annotations

import os


class AnthropicProvider:
    """Thin optional provider wrapper.

    Raises a clean runtime error if API credentials or SDK are unavailable.
    """

    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set; Anthropic provider unavailable.")
        try:
            import anthropic  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise RuntimeError("anthropic SDK is not installed; install it to use this provider.") from exc
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate(self, prompt: str, *, seed: int | None = None) -> str:
        msg = self._client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=180,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
