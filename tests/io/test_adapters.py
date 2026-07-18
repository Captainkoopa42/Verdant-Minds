from __future__ import annotations

import json
from pathlib import Path

from verdant.io.human_text_adapter import HumanTextInputAdapter
from verdant.io.conversational_output_adapter import ConversationalOutputAdapter
from verdant.io.query_interface import QueryInterface
from verdant.io.interaction_service import InteractionService
from verdant.output.bus import OutputBus
from verdant.output.events import OutputEvent
from verdant.system import VerdantSystem


def test_human_text_adapter_send_poll_fields() -> None:
    adapter = HumanTextInputAdapter(person_id="p1", session_id="s1")
    adapter.send("hello verdant")
    events = adapter.poll()
    assert len(events) == 1
    event = events[0]
    assert event.type == "text"
    assert event.source == "human"
    assert event.payload["text"] == "hello verdant"
    assert event.payload["person_id"] == "p1"
    assert event.payload["session_id"] == "s1"
    assert "ts_utc" in event.payload


def test_conversational_output_adapter_receives_speech() -> None:
    bus = OutputBus()
    adapter = ConversationalOutputAdapter()
    bus.register(adapter)
    bus.emit_all([OutputEvent(type="speech", payload="hi there", source="language_processing")])
    assert adapter.get_last_response() == "hi there"


def test_query_interface_query_returns_activations() -> None:
    system = VerdantSystem()
    qi = QueryInterface(system)
    result = qi.query("trust and care in relationships")
    assert "top_activated_nodes" in result
    assert isinstance(result["top_activated_nodes"], list)


def test_interaction_service_turn_persists(tmp_path: Path) -> None:
    system = VerdantSystem()
    in_adapter = HumanTextInputAdapter(person_id="p1", session_id="s1")
    out_adapter = ConversationalOutputAdapter()
    qi = QueryInterface(system)
    system.register_adapter(in_adapter)
    system.register_output_adapter(out_adapter)
    svc = InteractionService(system, in_adapter, out_adapter, qi, base_dir=str(tmp_path))

    svc.turn("p1", "first turn about trust")
    path = tmp_path / "p1" / "events.jsonl"
    assert path.exists()
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 1


def test_two_turns_second_includes_prior_context(tmp_path: Path) -> None:
    system = VerdantSystem()
    in_adapter = HumanTextInputAdapter(person_id="p1", session_id="s1")
    out_adapter = ConversationalOutputAdapter()
    qi = QueryInterface(system)
    system.register_adapter(in_adapter)
    system.register_output_adapter(out_adapter)
    svc = InteractionService(system, in_adapter, out_adapter, qi, base_dir=str(tmp_path), continuity_window=5)

    svc.turn("p1", "I feel uncertain")
    svc.turn("p1", "Can you remember what I said?")

    path = tmp_path / "p1" / "events.jsonl"
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 2
    second = rows[1]
    assert isinstance(second.get("continuity_context"), list)
    assert len(second["continuity_context"]) >= 1


def test_inspect_basin_fallback_detects_when_cache_empty() -> None:
    system = VerdantSystem()
    qi = QueryInterface(system)
    qi.query("trust care justice integrity")
    # Simulate no cached basins and ensure method still works deterministically.
    system._last_basins = []
    out = qi.inspect_basin("nonexistent")
    assert "source" in out
    assert out["source"] in {"cached", "detected"}
