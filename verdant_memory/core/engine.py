"""Internal engine wrapper used by the public Verdant-Memory API."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from verdant.query import QueryEngine
from verdant.system import VerdantConfig, VerdantSystem

from verdant_memory.schema import ConceptRecord, EdgeRecord, MemoryGraphState, MemorySnapshot


class MemoryEngine:
    """Wraps the existing VerdantSystem as an internal implementation detail."""

    def __init__(self, config: VerdantConfig | None = None) -> None:
        self.system = VerdantSystem(config=config or VerdantConfig())
        self.query = QueryEngine()

    def observe(self, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        chunk = self.system.process_input(text, metadata=metadata or {})
        action = chunk.get_section_content("action_selection_section") or {}
        language = chunk.get_section_content("language_processing_section") or {}
        return {
            "selected_action": str(action.get("selected_action", "")),
            "generated_response": str(language.get("generated_response", "")),
            "memory_size": int(self.system.memory_web.graph.number_of_nodes()),
            "cycle": int(self.system.get_metrics().get("total_cycles", 0)),
        }

    def retrieve(self, query: str, *, top_k: int = 8) -> dict[str, Any]:
        result = self.query.query(self.system, query, top_k=top_k)
        primary = result.get("primary_concept")
        context: dict[str, Any] = {}
        if isinstance(primary, str) and primary:
            context = self.system.memory_web.get_concept(primary) or {}
        return {
            "query": str(result.get("query", query)),
            "primary_concept": primary,
            "related": list(result.get("related", [])),
            "memory_context": context,
        }

    def apply_delta(self, delta: dict[str, Any]) -> dict[str, int]:
        added_concepts = 0
        added_edges = 0
        reinforced = 0

        for concept in delta.get("concepts", []):
            if not isinstance(concept, dict):
                continue
            label = str(concept.get("label", "")).strip()
            if not label:
                continue
            if self.system.memory_web.get_concept(label) is None:
                added_concepts += 1
            self.system.memory_web.add_concept(
                label,
                stability=float(concept.get("stability", 0.5)),
                metadata=dict(concept.get("metadata", {}) or {}),
            )

        for edge in delta.get("edges", []):
            if not isinstance(edge, dict):
                continue
            src = str(edge.get("source", "")).strip()
            dst = str(edge.get("target", "")).strip()
            if not src or not dst:
                continue
            if self.system.memory_web.get_concept(src) is None:
                self.system.memory_web.add_concept(src, stability=0.5)
                added_concepts += 1
            if self.system.memory_web.get_concept(dst) is None:
                self.system.memory_web.add_concept(dst, stability=0.5)
                added_concepts += 1
            created = self.system.memory_web.connect(src, dst, float(edge.get("weight", 0.5)))
            if created:
                added_edges += 1

        for item in delta.get("reinforce", []):
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip()
            if not label:
                continue
            if self.system.memory_web.get_concept(label) is None:
                continue
            self.system.memory_web.reinforce(label, float(item.get("amount", 0.1)))
            reinforced += 1

        return {
            "concepts_added": added_concepts,
            "edges_added": added_edges,
            "concepts_reinforced": reinforced,
        }

    def snapshot(self) -> MemorySnapshot:
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tmp:
            path = tmp.name
        try:
            self.system.save_state(path)
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        finally:
            if os.path.exists(path):
                os.remove(path)

        memory = payload.get("memory_web", {}) if isinstance(payload, dict) else {}
        store = memory.get("memory_store", {}) if isinstance(memory, dict) else {}
        edges = memory.get("edges", []) if isinstance(memory, dict) else []

        concepts = [
            ConceptRecord(
                label=str(label),
                stability=float(node.get("stability", 0.0)),
                access_count=int(node.get("access_count", 0)),
                last_accessed=float(node.get("last_accessed", 0.0)),
                metadata=dict(node.get("metadata", {}) or {}),
            )
            for label, node in store.items()
            if isinstance(node, dict)
        ]
        graph_edges = [
            EdgeRecord(
                source=str(edge.get("source", "")),
                target=str(edge.get("target", "")),
                weight=float(edge.get("weight", 0.5)),
            )
            for edge in edges
            if isinstance(edge, dict)
        ]

        graph = MemoryGraphState(
            concepts=concepts,
            edges=graph_edges,
            metadata={"concept_count": len(concepts), "edge_count": len(graph_edges)},
        )
        return MemorySnapshot(graph=graph, internal_state=payload)

    def load(self, snapshot: MemorySnapshot) -> None:
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tmp:
            path = tmp.name
            tmp.write(json.dumps(snapshot.internal_state))
            tmp.flush()
        try:
            self.system.load_state(path)
        finally:
            if os.path.exists(path):
                os.remove(path)
