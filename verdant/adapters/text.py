from __future__ import annotations

from .base import Adapter, InputEvent


class TextAdapter(Adapter):
    def __init__(self, buffer=None):
        super().__init__()
        self.buffer = list(buffer or [])

    def add(self, text: str):
        self.buffer.append(text)

    def poll(self):
        events = [InputEvent("text", {"text": t}, source="text") for t in self.buffer]
        self.buffer.clear()
        return events
