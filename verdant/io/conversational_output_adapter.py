from __future__ import annotations

from collections import deque

from verdant.output.base import OutputAdapter
from verdant.output.events import OutputEvent


class ConversationalOutputAdapter(OutputAdapter):
    """Captures speech outputs emitted on the OutputBus."""

    def __init__(self, history_size: int = 20) -> None:
        self._last_response: str = ""
        self._history_size = max(1, int(history_size))
        self._history_by_session: dict[str, deque[str]] = {}

    def emit(self, event: OutputEvent) -> None:
        if event.type != "speech":
            return
        text = str(event.payload)
        self._last_response = text

        session_id = "default"
        if isinstance(event.payload, dict):
            session_id = str(event.payload.get("session_id", "default"))
            text = str(event.payload.get("text", ""))
            self._last_response = text

        if session_id not in self._history_by_session:
            self._history_by_session[session_id] = deque(maxlen=self._history_size)
        self._history_by_session[session_id].append(text)

    def get_last_response(self) -> str:
        return self._last_response

    def get_history(self, session_id: str = "default") -> list[str]:
        return list(self._history_by_session.get(session_id, deque()))
