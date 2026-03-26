"""Query execution engine for Verdant MemoryWeb state."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import networkx as nx

from verdant.memory.basins import BasinInfo, detect_basins
from verdant.query.parser import ParsedQuery, QueryParser


@dataclass(frozen=True)
class RelatedConcept:
    """A ranked concept related to a query seed."""

    concept: str
    strength: float
    path: str | None = None


class QueryEngine:
    """Execute natural-language queries against a loaded ``VerdantSystem``.

    The engine is state-driven and does not mutate the system. It performs:
    - parser-guided seed extraction,
    - spreading activation over the MemoryWeb,
    - basin-context lookup,
    - ranked related-concept selection.
    """

    def __init__(self, parser: QueryParser | None = None) -> None:
        self._parser = parser or QueryParser()

    def query(
        self,
        system: Any,
        question: str,
        *,
        top_k: int = 8,
        max_depth: int = 3,
        spread_factor: float = 0.65,
        threshold: float = 0.02,
    ) -> dict[str, Any]:
        """Answer a query from an already loaded Verdant system instance."""
        memory_web = system.memory_web
        concepts = memory_web.list_concepts()
        parsed = self._parser.parse(question, concepts)

        if not parsed.seed_concepts:
            return {
                "query": question,
                "primary_concept": None,
                "stability": 0.0,
                "basin": None,
                "basin_summary": None,
                "related": [],
                "coherence": self._coherence_summary(system),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "notice": "No matching concepts found in memory graph.",
            }

        activation = self._spread_activation(
            memory_web=memory_web,
            seeds=parsed.seed_concepts,
            max_depth=max_depth,
            spread_factor=spread_factor,
            threshold=threshold,
        )

        ranked = self._rank_concepts(memory_web=memory_web, activation=activation, parsed=parsed)
        primary = parsed.primary_concept
        primary_data = memory_web.get_concept(primary) if primary else None

        basins = self._resolve_basins(system)
        primary_basin = self._find_basin_for_concept(primary, basins)

        related: list[dict[str, Any]] = []
        for item in ranked[:top_k]:
            if item.concept == primary:
                continue
            payload: dict[str, Any] = {
                "concept": item.concept,
                "strength": round(item.strength, 6),
            }
            if item.path:
                payload["path"] = item.path
            related.append(payload)

        return {
            "query": question,
            "primary_concept": primary,
            "stability": round(float((primary_data or {}).get("stability", 0.0)), 6),
            "basin": primary_basin.basin_id if primary_basin else None,
            "basin_summary": self._basin_summary(primary_basin),
            "related": related,
            "coherence": self._coherence_summary(system),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "meta": {
                "seeds": parsed.seed_concepts,
                "seed_count": len(parsed.seed_concepts),
                "activation_nodes": len(activation),
            },
        }

    def _spread_activation(
        self,
        *,
        memory_web: Any,
        seeds: list[str],
        max_depth: int,
        spread_factor: float,
        threshold: float,
    ) -> dict[str, float]:
        """Compute spreading activation over graph edges with stability-aware damping."""
        graph = memory_web.graph
        activation: dict[str, float] = {}
        queue = deque((seed, 1.0, 0) for seed in seeds if seed in graph)

        while queue:
            node, level, depth = queue.popleft()
            if level < threshold:
                continue
            if activation.get(node, 0.0) >= level:
                continue

            activation[node] = level
            if depth >= max_depth:
                continue

            for neighbor in graph.neighbors(node):
                edge_w = float(graph[node][neighbor].get("weight", 0.5))
                n_stability = float((memory_web.get_concept(neighbor) or {}).get("stability", 0.5))
                propagated = level * edge_w * n_stability * spread_factor
                if propagated >= threshold:
                    queue.append((neighbor, propagated, depth + 1))

        return activation

    def _rank_concepts(self, *, memory_web: Any, activation: dict[str, float], parsed: ParsedQuery) -> list[RelatedConcept]:
        """Rank concepts using stability × access_count × activation."""
        graph = memory_web.graph
        primary = parsed.primary_concept
        ranked: list[RelatedConcept] = []

        for concept, act in activation.items():
            data = memory_web.get_concept(concept) or {}
            stability = float(data.get("stability", 0.0))
            access_count = max(1, int(data.get("access_count", 1)))
            score = stability * access_count * act
            path_str = self._format_path(graph, primary, concept) if primary else None
            ranked.append(RelatedConcept(concept=concept, strength=score, path=path_str))

        ranked.sort(key=lambda item: item.strength, reverse=True)
        return ranked

    @staticmethod
    def _format_path(graph: nx.Graph, source: str | None, target: str) -> str | None:
        if source is None or source == target or source not in graph or target not in graph:
            return None
        try:
            path = nx.shortest_path(graph, source=source, target=target)
        except nx.NetworkXNoPath:
            return None
        return " → ".join(path)

    @staticmethod
    def _resolve_basins(system: Any) -> list[BasinInfo]:
        basins = getattr(system, "_last_basins", None)
        if isinstance(basins, list) and basins:
            return basins
        scan_k = int(getattr(getattr(system, "config", object()), "basin_scan_k", 6))
        min_size = int(getattr(getattr(system, "config", object()), "basin_min_size", 5))
        return detect_basins(system.memory_web, k=scan_k, min_size=min_size)

    @staticmethod
    def _find_basin_for_concept(concept: str | None, basins: list[BasinInfo]) -> BasinInfo | None:
        if not concept:
            return None
        for basin in basins:
            if concept in basin.nodes:
                return basin
        return None

    @staticmethod
    def _basin_summary(basin: BasinInfo | None) -> dict[str, Any] | None:
        if basin is None:
            return None
        return {
            "size": basin.size,
            "emergent_count": basin.emergent_count,
            "mean_stability": round(float(basin.mean_stability), 6),
        }

    @staticmethod
    def _coherence_summary(system: Any) -> dict[str, Any]:
        metrics = getattr(system, "_last_coherence_metrics", {}) or {}
        return {
            "h1_valid": bool(metrics.get("h1_triangle_valid")) if metrics.get("h1_triangle_valid") is not None else None,
            "hci": metrics.get("housed_contradiction_index"),
        }
