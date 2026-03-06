"""Deterministic curriculum for contradiction pressure/release cycles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CurriculumStep:
    """Prompt template metadata for a cycle."""

    phase: str
    prompt: str
    topic: str


class CurriculumStrategy:
    """Topic wheel + contradiction pressure/release schedule."""

    TOPIC_WHEEL = [
        "identity",
        "memory",
        "ethics",
        "emergence",
        "time",
        "coherence",
        "entropy",
        "agency",
        "collective intelligence",
    ]

    def __init__(self, *, pressure_every: int = 5) -> None:
        self.pressure_every = max(1, pressure_every)

    def step(self, cycle_index: int, *, seed: int) -> CurriculumStep:
        """Build deterministic phase/topic prompt for a cycle."""
        topic = self.TOPIC_WHEEL[(cycle_index + seed) % len(self.TOPIC_WHEEL)]
        is_pressure = (cycle_index + 1) % self.pressure_every == 0
        if is_pressure:
            prompt = (
                f"Contradiction pressure on {topic}: hold two competing claims as simultaneously relevant, "
                f"then reconcile with explicit trade-offs and unresolved residue."
            )
            phase = "pressure"
        else:
            prompt = (
                f"Reflective release on {topic}: summarize stable insights, identify uncertainty, "
                f"and connect to prior memory without forced contradiction."
            )
            phase = "release"
        return CurriculumStep(phase=phase, prompt=prompt, topic=topic)
