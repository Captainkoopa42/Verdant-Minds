"""Optional Groq provider."""

from __future__ import annotations

import os


class GroqProvider:
    """Thin optional provider wrapper for Groq chat completions."""

    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set; Groq provider unavailable.")
        try:
            from groq import Groq  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise RuntimeError("groq SDK is not installed; install it to use this provider.") from exc
        self._client = Groq(api_key=api_key)

    def generate(self, prompt: str, *, seed: int | None = None) -> str:
        resp = self._client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""
