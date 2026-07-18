from __future__ import annotations

from .base import Adapter, InputEvent


class DummySensorAdapter(Adapter):
    """Simulated sensor adapter for daemon/runtime testing."""

    def __init__(self, sensor_name: str = "dummy_sensor") -> None:
        super().__init__()
        self.sensor_name = sensor_name
        self._tick = 0

    def emit(self, payload: dict) -> None:
        self.push(InputEvent(type="sensor", payload=payload, source=self.sensor_name))

    def poll(self) -> list[InputEvent]:
        events = list(self._buffer)
        self._buffer.clear()

        self._tick += 1
        events.append(
            InputEvent(
                type="sensor",
                payload={"tick": self._tick, "state": "ok"},
                source=self.sensor_name,
            )
        )
        return events
