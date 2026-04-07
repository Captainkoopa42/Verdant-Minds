"""Smoke test for Verdant output bus emission.

Usage:
    python scripts/test_output_bus.py
"""

from __future__ import annotations

from dataclasses import asdict

from verdant.adapters.base import InputEvent
from verdant.output import OutputAdapter, OutputEvent
from verdant.system import VerdantSystem


class PrintOutputAdapter(OutputAdapter):
    def __init__(self) -> None:
        self.events: list[OutputEvent] = []

    def emit(self, event: OutputEvent) -> None:
        self.events.append(event)
        print(f"[{event.type}] {event.source}: {event.payload}")


def main() -> None:
    system = VerdantSystem()
    printer = PrintOutputAdapter()
    system.register_output_adapter(printer)

    input_event = InputEvent(type="text", payload={"text": "Explain photosynthesis briefly."}, source="test")
    system.process_cycle([input_event])

    assert printer.events, "Expected output events to be emitted"
    assert any(event.type == "speech" for event in printer.events), "Expected at least one speech event"
    print(f"Emitted {len(printer.events)} events")
    print("First event:", asdict(printer.events[0]))


if __name__ == "__main__":
    main()
