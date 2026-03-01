"""Groq provider adapter using the official Groq Python SDK."""

from __future__ import annotations

import os
from typing import Optional

from groq import Groq


class GroqRateLimitError(RuntimeError):
    """Raised when Groq responds with HTTP 429 (tokens/day or rate limits)."""

    def __init__(self, message: str, retry_after_seconds: Optional[float] = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def _extract_status_code(exc: Exception) -> Optional[int]:
    for attr in ("status_code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    for attr in ("status_code", "status"):
        value = getattr(response, attr, None)
        if isinstance(value, int):
            return value
    return None


def _extract_error_detail(exc: Exception) -> str:
    body = getattr(exc, "body", None)
    if body:
        return str(body)
    return str(exc)


def groq_next_input(
    prompt: str,
    *,
    model: str | None = None,
    max_tokens: int = 256,
    temperature: float = 0.7,
) -> str:
    """Generate a Verdant next-input suggestion from Groq."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY environment variable")

    resolved_model = model or os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    client = Groq(api_key=api_key)

    try:
        completion = client.chat.completions.create(
            model=resolved_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as exc:  # noqa: BLE001
        status_code = _extract_status_code(exc)
        detail = _extract_error_detail(exc)
        if status_code == 429:
            raise GroqRateLimitError(f"Groq API rate limited (429): {detail}") from exc
        raise RuntimeError(f"Groq API error: {detail}") from exc

    choices = getattr(completion, "choices", None) or []
    message = getattr(choices[0], "message", None) if choices else None
    content = getattr(message, "content", None)
    text = str(content or "").strip()
    if not text:
        raise RuntimeError("Groq API returned empty content")
    return text
