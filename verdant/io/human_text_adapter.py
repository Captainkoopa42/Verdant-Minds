from __future__ import annotations

from datetime import datetime, timezone

from verdant.adapters.base import Adapter, InputEvent


class HumanTextInputAdapter(Adapter):
    """Queue human text turns as InputEvents for VerdantSystem.collect_inputs()."""

    def __init__(self, person_id: str, session_id: str) -> None:
        super().__init__()
        self.person_id = str(person_id)
        self.session_id = str(session_id)

    def send(self, text: str) -> None:
        ts_utc = datetime.now(timezone.utc).isoformat()
        self.push(
            InputEvent(
                type="text",
                payload={
                    "text": str(text),
                    "person_id": self.person_id,
                    "session_id": self.session_id,
                    "ts_utc": ts_utc,
                },
                source="human",
            )
        )

    def poll(self) -> list[InputEvent]:
        events = list(self._buffer)
        self._buffer.clear()
        return events
