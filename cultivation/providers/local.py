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
        token = f"{seed}|{prompt}".encode("utf-8")
        digest = hashlib.sha256(token).hexdigest()
        local_seed = int(digest[:16], 16)
        rng = random.Random(local_seed)

        topic = self._extract_topic(prompt)
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
        lowered = prompt.lower()
        for key in ["identity", "memory", "ethics", "emergence", "time", "coherence", "entropy"]:
            if key in lowered:
                return key
        return "general cognition"
