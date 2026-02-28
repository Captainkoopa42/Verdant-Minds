"""Groq provider adapter with rate-limit handling and safe local fallback."""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from typing import Callable, Optional


class GroqRateLimitError(RuntimeError):
    """Raised when Groq responds with HTTP 429 (tokens/day or rate limits)."""

    def __init__(self, message: str, retry_after_seconds: Optional[float] = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def _extract_retry_after(exc: urllib.error.HTTPError) -> Optional[float]:
    retry_after = exc.headers.get("Retry-After") if exc.headers else None
    if retry_after is None:
        return None
    try:
        return float(retry_after)
    except (TypeError, ValueError):
        return None


def groq_next_input(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    telemetry_payload: str,
    temperature: float,
    max_tokens: int,
    retries: int = 3,
    fallback_fn: Optional[Callable[[str], str]] = None,
) -> str:
    """Generate next input from Groq with retries, jittered backoff, and optional fallback."""
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Cultivation telemetry (JSON):\n"
                    f"{telemetry_payload}\n\n"
                    "Produce only the next input text for Verdant."
                ),
            },
        ],
    }
    data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        },
        method="POST",
    )

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
            choices = payload.get("choices") or []
            content = ((choices[0] or {}).get("message") or {}).get("content") if choices else None
            text = str(content or "").strip()
            if not text:
                raise RuntimeError(f"Groq API returned empty content: {payload}")
            return text
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
            if exc.code == 429:
                retry_after = _extract_retry_after(exc)
                wait_for = retry_after if retry_after is not None else (2**attempt) + random.uniform(0.0, 0.75)
                if attempt < retries - 1:
                    print(
                        "warning provider=groq event=rate_limited "
                        f"attempt={attempt + 1}/{retries} retry_after={wait_for:.2f}s"
                    )
                    time.sleep(max(0.0, wait_for))
                    continue
                print(
                    "warning provider=groq event=rate_limited "
                    f"retry_after={retry_after if retry_after is not None else 'unknown'}s fallback=local"
                )
                if fallback_fn is not None:
                    return fallback_fn("groq_rate_limited")
                raise GroqRateLimitError(f"Groq API HTTP 429: {detail}", retry_after_seconds=retry_after) from exc
            raise RuntimeError(f"Groq API HTTP error: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            if attempt < retries - 1:
                wait_for = (2**attempt) + random.uniform(0.0, 0.75)
                print(
                    "warning provider=groq event=network_error "
                    f"attempt={attempt + 1}/{retries} retry_after={wait_for:.2f}s"
                )
                time.sleep(max(0.0, wait_for))
                continue
            if fallback_fn is not None:
                return fallback_fn("groq_network_error")
            raise RuntimeError(f"Groq API network error: {exc.reason}") from exc

    if fallback_fn is not None:
        return fallback_fn("groq_unknown_error")
    raise RuntimeError("Groq API request failed after retries")
