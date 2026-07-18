"""Thermodynamically-governed attention buffering for Verdant."""

from __future__ import annotations

from typing import Any


class AttentionItem:
    """A single impression in the attention buffer."""

    def __init__(
        self,
        concepts: list[str],
        activation: float,
        source_text: str = "",
        novelty: float = 0.0,
        basin_id: str | None = None,
        cycle: int = 0,
    ) -> None:
        self.concepts = list(concepts)
        self.activation = float(activation)
        self.initial_activation = float(activation)
        self.source_text = source_text
        self.novelty = float(novelty)
        self.basin_id = basin_id
        self.cycle = int(cycle)
        self.age = 0
        self.resonance_count = 0

    def decay(self, rate: float = 0.02) -> None:
        """Decay activation over time. Old unattended items fade."""
        self.age += 1
        self.activation = max(0.0, self.activation - rate)

    def boost(self, amount: float = 0.1) -> None:
        """Boost activation from resonance or external signal."""
        self.resonance_count += 1
        self.activation = min(1.0, self.activation + amount)

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "concepts": self.concepts,
            "activation": round(self.activation, 4),
            "source_text": self.source_text[:100],
            "novelty": round(self.novelty, 4),
            "basin_id": self.basin_id,
            "cycle": self.cycle,
            "age": self.age,
            "resonance_count": self.resonance_count,
        }


class AttentionBuffer:
    """Thermodynamically-governed attention mechanism."""

    def __init__(self, config: dict[str, Any] | None = None, bypass: bool = False) -> None:
        self.items: list[AttentionItem] = []
        self.capacity = 10
        self.threshold = 0.15
        self.history: list[AttentionItem] = []
        self.bypass = bool(bypass)

        self.min_capacity = 3
        self.max_capacity = 30
        self.min_threshold = 0.05
        self.max_threshold = 0.50
        self.max_silent_cycles = 20
        self.silent_count = 0

        self.tg_center = 0.576
        self.capacity_scale = 20.0
        self.threshold_scale = 0.5

        if config:
            for key, value in config.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    def update_governance(self, t_g: float) -> None:
        """Adjust capacity and threshold based on current T_g."""
        delta = float(t_g) - self.tg_center
        raw_capacity = 10 + delta * self.capacity_scale
        self.capacity = int(max(self.min_capacity, min(self.max_capacity, raw_capacity)))

        raw_threshold = 0.15 - delta * self.threshold_scale
        self.threshold = max(self.min_threshold, min(self.max_threshold, raw_threshold))

    def add(self, item: AttentionItem) -> None:
        """Add an impression to the buffer."""
        self.items.append(item)
        for existing in self.items:
            existing.decay(rate=0.02)

        if len(self.items) > self.capacity:
            self.items.sort(key=lambda x: x.activation)
            self.items = self.items[-self.capacity:]

        self._check_resonance(item)

    def evaluate(self) -> list[AttentionItem]:
        """Evaluate buffer and return items crossing threshold."""
        if self.bypass:
            escalated = list(self.items)
            self.items = []
            if escalated:
                self.history.extend(escalated)
                self.history = self.history[-50:]
                self.silent_count = 0
            return escalated

        self.silent_count += 1
        escalated: list[AttentionItem] = []
        remaining: list[AttentionItem] = []

        for item in self.items:
            if item.activation >= self.threshold:
                escalated.append(item)
            else:
                remaining.append(item)

        if not escalated and self.silent_count >= self.max_silent_cycles and self.items:
            self.items.sort(key=lambda x: x.activation, reverse=True)
            escalated.append(self.items[0])
            remaining = self.items[1:]

        if escalated:
            self.silent_count = 0
            self.history.extend(escalated)
            self.history = self.history[-50:]

        self.items = remaining
        return escalated

    def _check_resonance(self, new_item: AttentionItem) -> None:
        """Boost overlapping buffered items."""
        for existing in self.items:
            if existing is new_item:
                continue
            overlap = set(new_item.concepts) & set(existing.concepts)
            if overlap:
                boost = len(overlap) * 0.1
                existing.boost(amount=boost)
                new_item.boost(amount=boost)

    def get_state(self) -> dict[str, Any]:
        """Return monitoring state."""
        return {
            "item_count": len(self.items),
            "capacity": self.capacity,
            "threshold": round(self.threshold, 4),
            "silent_cycles": self.silent_count,
            "top_activation": round(max((i.activation for i in self.items), default=0), 4),
            "mean_activation": round(
                sum(i.activation for i in self.items) / max(len(self.items), 1),
                4,
            ),
        }
