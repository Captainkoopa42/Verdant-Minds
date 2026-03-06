"""Optional Mistral provider."""

from __future__ import annotations

import os


class MistralProvider:
    """Thin optional provider wrapper for Mistral API."""

    def __init__(self) -> None:
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise RuntimeError("MISTRAL_API_KEY is not set; Mistral provider unavailable.")
        try:
            from mistralai import Mistral  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise RuntimeError("mistralai SDK is not installed; install it to use this provider.") from exc
        self._client = Mistral(api_key=api_key)

    def generate(self, prompt: str, *, seed: int | None = None) -> str:
        resp = self._client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""
