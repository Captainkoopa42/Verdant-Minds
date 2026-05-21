from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from verdant.io.human_text_adapter import HumanTextInputAdapter
from verdant.io.conversational_output_adapter import ConversationalOutputAdapter
from verdant.io.query_interface import QueryInterface
from verdant.system import VerdantSystem


class InteractionService:
    def __init__(
        self,
        system: VerdantSystem,
        input_adapter: HumanTextInputAdapter,
        output_adapter: ConversationalOutputAdapter,
        query_interface: QueryInterface,
        base_dir: str = "interactions",
        continuity_window: int = 5,
    ) -> None:
        self.system = system
        self.input_adapter = input_adapter
        self.output_adapter = output_adapter
        self.query_interface = query_interface
        self.base_dir = Path(base_dir)
        self.continuity_window = max(1, int(continuity_window))

    def _events_path(self, person_id: str) -> Path:
        path = self.base_dir / person_id
        path.mkdir(parents=True, exist_ok=True)
        return path / "events.jsonl"

    def _read_recent(self, person_id: str) -> list[dict[str, Any]]:
        path = self._events_path(person_id)
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines[-self.continuity_window :]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def turn(self, person_id: str, text: str) -> str:
        continuity = self._read_recent(person_id)
        self.input_adapter.send(text)
        chunks = self.system.run_cycle()
        response = self.output_adapter.get_last_response()
        query_snapshot = self.query_interface.summarize_chunk(text=text, chunk=chunks[-1] if chunks else self.system._null_chunk(text=text))

        event = {
            "event_id": f"evt_{datetime.now(timezone.utc).timestamp()}",
            "person_id": person_id,
            "session_id": self.input_adapter.session_id,
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "input_text": text,
            "response_text": response,
            "continuity_context": continuity,
            "top_activated_nodes": query_snapshot.get("top_activated_nodes", []),
            "dominant_basins": query_snapshot.get("dominant_basins", []),
            "coherence": query_snapshot.get("coherence", {}),
            "t_g": query_snapshot.get("t_g", 0.5),
            "chunks_processed": len(chunks),
            "schema_version": "interaction-v0",
        }
        path = self._events_path(person_id)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, default=str) + "\n")
        return response
