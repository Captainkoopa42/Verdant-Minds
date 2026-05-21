from __future__ import annotations

from collections import deque
from typing import Any

from verdant.system import VerdantSystem


class QueryInterface:
    """Inspection wrapper over a live VerdantSystem instance."""

    def __init__(self, system: VerdantSystem, activation_threshold: float = 0.1) -> None:
        self.system = system
        self.activation_threshold = float(activation_threshold)
        self._recent = deque(maxlen=500)

    def _summarize_chunk(self, text: str, chunk: Any) -> dict[str, Any]:
        memory = chunk.get_section_content("memory_section") or {}
        activations = memory.get("activated_concepts", {}) or {}
        top_activated = sorted(
            ((str(k), float(v)) for k, v in activations.items()),
            key=lambda x: x[1],
            reverse=True,
        )[:10]
        for label, score in top_activated:
            if score >= self.activation_threshold:
                self._recent.append({"concept": label, "activation": score})

        metrics = self.system.get_metrics()
        language = chunk.get_section_content("language_processing_section") or {}
        return {
            "input": text,
            "top_activated_nodes": top_activated,
            "dominant_basins": list(metrics.get("basins", []))[:3],
            "coherence": self.system.get_coherence_metrics(),
            "t_g": float(metrics.get("t_g", 0.5)),
            "generated_response": language.get("generated_response", ""),
        }

    def query(self, text: str) -> dict[str, Any]:
        chunk = self.system.process_input(text)
        return self._summarize_chunk(text, chunk)

    def summarize_chunk(self, *, text: str, chunk: Any) -> dict[str, Any]:
        return self._summarize_chunk(text, chunk)

    def inspect_concept(self, label: str) -> dict[str, Any]:
        graph = self.system.memory_web.graph
        data = self.system.memory_web.get_concept(label) or {}
        neighbors = []
        for n in self.system.memory_web.get_neighbors(label):
            edge = graph.get_edge_data(label, n, default={})
            neighbors.append({"label": n, "weight": float(edge.get("weight", 0.0))})
        basin_membership = [b.basin_id for b in self.system._last_basins if label in b.nodes]
        activation_history = self.system.memory_web.activation_history.get(label, [])
        return {
            "label": label,
            "concept": data,
            "activation_history": activation_history,
            "neighbors": neighbors,
            "basin_membership": basin_membership,
        }

    def inspect_basin(self, basin_id: str) -> dict[str, Any]:
        for basin in self.system._last_basins:
            if str(basin.basin_id) == str(basin_id):
                return {
                    "basin_id": basin.basin_id,
                    "members": list(basin.nodes),
                    "centroid": basin.centroid,
                    "volatility": basin.volatility,
                    "hotness": basin.hotness,
                }
        return {"basin_id": basin_id, "error": "not_found"}

    def recent_activations(self, n: int = 10) -> list[dict[str, Any]]:
        n = max(1, int(n))
        return list(self._recent)[-n:]

    def diff(self, text_a: str, text_b: str) -> dict[str, Any]:
        a = self.query(text_a)
        b = self.query(text_b)
        a_map = {k: v for k, v in a["top_activated_nodes"]}
        b_map = {k: v for k, v in b["top_activated_nodes"]}
        keys = sorted(set(a_map) | set(b_map))
        delta = []
        for k in keys:
            delta.append({"concept": k, "a": a_map.get(k, 0.0), "b": b_map.get(k, 0.0), "delta": b_map.get(k, 0.0) - a_map.get(k, 0.0)})
        delta.sort(key=lambda x: abs(x["delta"]), reverse=True)
        return {"text_a": text_a, "text_b": text_b, "activation_delta": delta[:20]}
