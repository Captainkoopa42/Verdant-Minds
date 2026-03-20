"""Deterministic topic variation for repeated local-provider cultivation topics."""

from __future__ import annotations

PERSPECTIVE_MODIFIERS = [
    "focusing on how this tension manifests in emergency situations",
    "considering historical perspectives",
    "examining edge cases and exceptions",
    "from the perspective of vulnerable populations",
    "in the context of systemic constraints",
    "through the lens of competing obligations",
    "considering unintended consequences",
    "examining what changes at scale",
]


def vary_topic_for_pass(topic: str, pass_index: int) -> str:
    """Return a deterministic variation for the Nth use of a topic in a phase."""
    if pass_index <= 1:
        return topic
    modifier = PERSPECTIVE_MODIFIERS[(pass_index - 2) % len(PERSPECTIVE_MODIFIERS)]
    return f"{topic}, {modifier}"
