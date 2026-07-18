"""Deterministic local provider for offline, reproducible cultivation."""

from __future__ import annotations

import hashlib
import random


class LocalProvider:
    """Seeded deterministic provider with contradiction-aware templating."""

    _TEMPLATES = [
        "Observed pattern: {topic}. Reflective synthesis: {motif}.",
        "Working hypothesis on {topic}: {motif} under bounded uncertainty.",
        "Memory-linked note on {topic}: {motif}; update coherence carefully.",
        "Constraint-focused framing of {topic}: {motif}; preserve traceability.",
    ]
    _MOTIFS = [
        "identity is stable yet transformable",
        "order emerges through managed contradiction",
        "ethical tension can improve representational clarity",
        "time-asymmetry appears in concept integration",
        "coherence increases when novelty is bounded",
    ]

    def generate(self, prompt: str, *, seed: int | None = None) -> str:
        """Return deterministic pseudo-generated text from prompt and seed."""
        topic = self._extract_topic(prompt)
        if self._looks_like_full_sentence(topic):
            return topic

        token = f"{seed}|{prompt}".encode("utf-8")
        digest = hashlib.sha256(token).hexdigest()
        local_seed = int(digest[:16], 16)
        rng = random.Random(local_seed)
        template = rng.choice(self._TEMPLATES)
        motif = rng.choice(self._MOTIFS)
        contradiction = ""
        if rng.random() < 0.35:
            contradiction = (
                " Contradiction marker: preserve autonomy while enforcing strict collective symmetry."
            )
        return template.format(topic=topic, motif=motif) + contradiction

    @staticmethod
    def _extract_topic(prompt: str) -> str:
        cleaned = " ".join(prompt.replace("\n", " ").split()).strip()
        if not cleaned:
            return "general cognition"

        # Preserve the caller's natural-language content so those concepts reach the pipeline.
        if len(cleaned) <= 140:
            return cleaned
        return cleaned[:140].rsplit(" ", 1)[0].strip() or cleaned[:140]

    @staticmethod
    def _looks_like_full_sentence(topic: str) -> bool:
        return bool(topic) and " " in topic and topic[-1] in ".!?"
