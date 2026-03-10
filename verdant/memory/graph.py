"""MemoryWeb — associative memory graph implementing the ethomorphic MemoryBackend.

Internally uses NetworkX for graph storage.  This is the **only** module
in verdant_v2/ that imports NetworkX.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np


class MemoryWeb:
    """Associative memory network satisfying ``ethomorphic.bridge.bridge.MemoryBackend``.

    Every node stores:
    * ``stability`` – float in ``[0, 1]``
    * ``access_count`` – int
    * ``last_accessed`` – float (unix timestamp)
    * ``metadata`` – dict
    * ``connections`` – list of ``(label, weight)``
    """

    def __init__(self, edge_policy: str = "default") -> None:
        self.graph: nx.Graph = nx.Graph()
        self.memory_store: Dict[str, Dict[str, Any]] = {}
        self.thought_clusters: Dict[str, List[str]] = {}
        self.activation_history: Dict[str, List[Tuple[float, float]]] = {}
        self.edge_policy = edge_policy
        self.metrics: Dict[str, Any] = {
            "total_concepts": 0,
            "total_connections": 0,
            "avg_stability": 0.0,
            "start_time": time.time(),
        }

    # ------------------------------------------------------------------
    # MemoryBackend protocol
    # ------------------------------------------------------------------

    def add_concept(self, label: str, stability: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add or update a concept node."""
        now = time.time()
        if label in self.memory_store:
            entry = self.memory_store[label]
            entry["access_count"] += 1
            entry["stability"] = min(1.0, entry["stability"] + 0.02)
            entry["last_accessed"] = now
            if metadata:
                entry["metadata"].update(metadata)
        else:
            self.memory_store[label] = {
                "stability": stability,
                "connections": [],
                "first_seen": now,
                "last_accessed": now,
                "access_count": 1,
                "metadata": metadata or {},
            }
            self.graph.add_node(label, stability=stability)
            self.metrics["total_concepts"] += 1

            # Auto-connect to top-3 stable existing nodes
            if len(self.memory_store) > 1:
                others = [
                    (k, v["stability"])
                    for k, v in self.memory_store.items()
                    if k != label
                ]
                others.sort(key=lambda x: x[1], reverse=True)
                for other_label, _ in others[:3]:
                    self.connect(label, other_label, 0.3)

        self.graph.nodes[label]["stability"] = self.memory_store[label]["stability"]
        self._update_avg_stability()

    # Alias used by v1-style callers
    add_thought = add_concept

    def get_concept(self, label: str) -> Optional[Dict[str, Any]]:
        """Return concept data or ``None``."""
        return self.memory_store.get(label)

    def connect(self, label1: str, label2: str, weight: float = 0.5) -> bool:
        """Create or strengthen an edge.  Returns ``True`` if newly created."""
        if label1 not in self.memory_store or label2 not in self.memory_store:
            return False

        s1 = self.memory_store[label1]["stability"]
        s2 = self.memory_store[label2]["stability"]
        effective_weight = min(1.0, weight * (s1 + s2) / 2)

        if self.edge_policy == "pconnect":
            delta_e = abs(self._get_ethical_charge(label1) - self._get_ethical_charge(label2))
            prob = (1 - 0.6 * delta_e) * np.exp(-1.0 * (1 - effective_weight))
            if np.random.random() > prob:
                return False

        new_edge = not self.graph.has_edge(label1, label2)
        if new_edge:
            self.graph.add_edge(label1, label2, weight=effective_weight)
            self.memory_store[label1]["connections"].append((label2, effective_weight))
            self.memory_store[label2]["connections"].append((label1, effective_weight))
            self.metrics["total_connections"] += 1
        else:
            old_w = self.graph[label1][label2]["weight"]
            blended = old_w * 0.7 + effective_weight * 0.3
            self.graph[label1][label2]["weight"] = blended

        return new_edge

    connect_thoughts = connect

    def get_neighbors(self, label: str) -> List[str]:
        """Return immediate neighbor labels."""
        if label not in self.graph:
            return []
        return list(self.graph.neighbors(label))

    def list_concepts(self) -> List[str]:
        """Return all concept labels."""
        return list(self.memory_store.keys())

    def reinforce(self, label: str, amount: float = 0.1) -> float:
        """Increase stability and return new value."""
        if label not in self.memory_store:
            return 0.0
        new = min(1.0, self.memory_store[label]["stability"] + amount)
        self.memory_store[label]["stability"] = new
        self.graph.nodes[label]["stability"] = new
        self._update_avg_stability()
        return new

    reinforce_memory = reinforce

    def decay(self, factor: float = 0.01) -> int:
        """Apply uniform decay; returns count of affected nodes."""
        count = 0
        for label, data in self.memory_store.items():
            old = data["stability"]
            data["stability"] = max(0.1, old - factor)
            self.graph.nodes[label]["stability"] = data["stability"]
            if data["stability"] < old:
                count += 1
        self._update_avg_stability()
        return count

    decay_memories = decay

    # ------------------------------------------------------------------
    # Extended methods
    # ------------------------------------------------------------------

    def retrieve_related(self, label: str, depth: int = 2, limit: int = 10) -> List[Tuple[str, float]]:
        """Retrieve related concepts via ego-graph radius."""
        if label not in self.graph:
            return []
        ego = nx.ego_graph(self.graph, label, radius=depth)
        results: List[Tuple[str, float]] = []
        for node in ego.nodes():
            if node == label:
                continue
            try:
                path_len = nx.shortest_path_length(self.graph, label, node)
            except nx.NetworkXNoPath:
                path_len = depth + 1
            stability = self.memory_store.get(node, {}).get("stability", 0.5)
            relevance = stability / (path_len + 1)
            results.append((node, relevance))
            # Update access tracking
            if node in self.memory_store:
                self.memory_store[node]["last_accessed"] = time.time()
                self.memory_store[node]["access_count"] += 1
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    retrieve_related_thoughts = retrieve_related

    def activate_concepts(
        self,
        seeds: List[str],
        strength: float = 0.7,
        spread_factor: float = 0.5,
        max_depth: int = 3,
        threshold: float = 0.1,
    ) -> Dict[str, float]:
        """Spreading activation from *seeds*."""
        activations: Dict[str, float] = {}
        queue: List[Tuple[str, float, int]] = [(s, strength, 0) for s in seeds if s in self.graph]

        while queue:
            concept, level, depth = queue.pop(0)
            if concept in activations and activations[concept] >= level:
                continue
            activations[concept] = level
            if depth >= max_depth:
                continue
            for neighbor in self.graph.neighbors(concept):
                w = self.graph[concept][neighbor].get("weight", 0.5)
                new_level = level * w * spread_factor
                if new_level >= threshold:
                    queue.append((neighbor, new_level, depth + 1))

        # Record history
        now = time.time()
        for concept, level in activations.items():
            self.activation_history.setdefault(concept, []).append((now, level))
            hist = self.activation_history[concept]
            if len(hist) > 100:
                self.activation_history[concept] = hist[-100:]

        return activations

    def cluster_thoughts(self, min_stability: float = 0.3) -> Dict[str, List[str]]:
        """Cluster concepts using connected components on stability-filtered subgraph."""
        nodes = [n for n, d in self.graph.nodes(data=True) if d.get("stability", 0) >= min_stability]
        if not nodes:
            self.thought_clusters = {}
            return {}
        sub = self.graph.subgraph(nodes)
        clusters: Dict[str, List[str]] = {}
        for i, comp in enumerate(nx.connected_components(sub)):
            clusters[f"cluster_{i}"] = sorted(comp)
        self.thought_clusters = clusters
        return clusters

    def get_emergent_nodes(self) -> List[str]:
        """Return labels of all emergent concepts."""
        return [l for l in self.memory_store if l.startswith("Emergent_")]

    def get_edge_classification(self) -> Dict[str, int]:
        """Classify edges as emergent↔emergent, emergent↔seeded, seeded↔seeded."""
        counts = {"emergent_emergent": 0, "emergent_seeded": 0, "seeded_seeded": 0}
        for u, v in self.graph.edges():
            u_em = u.startswith("Emergent_")
            v_em = v.startswith("Emergent_")
            if u_em and v_em:
                counts["emergent_emergent"] += 1
            elif u_em or v_em:
                counts["emergent_seeded"] += 1
            else:
                counts["seeded_seeded"] += 1
        return counts

    def to_chunks(self) -> Dict[str, Any]:
        """Produce chunked serialisation format."""
        nodes: Dict[str, Any] = {}
        for label, data in self.memory_store.items():
            nodes[label] = {
                "stability": data["stability"],
                "access_count": data["access_count"],
                "last_accessed": data["last_accessed"],
                "metadata": data["metadata"],
            }
        edges = [
            {"source": u, "target": v, "weight": d.get("weight", 0.5)}
            for u, v, d in self.graph.edges(data=True)
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "emergent_summary": {
                "emergent_count": len(self.get_emergent_nodes()),
                "edge_classification": self.get_edge_classification(),
            },
        }

    def to_state_dict(self) -> Dict[str, Any]:
        """Full serialisation."""
        return {
            "memory_store": {
                k: {
                    "stability": v["stability"],
                    "connections": v["connections"],
                    "first_seen": v["first_seen"],
                    "last_accessed": v["last_accessed"],
                    "access_count": v["access_count"],
                    "metadata": v["metadata"],
                }
                for k, v in self.memory_store.items()
            },
            "edges": [
                {"source": u, "target": v, "weight": d.get("weight", 0.5)}
                for u, v, d in self.graph.edges(data=True)
            ],
            "edge_policy": self.edge_policy,
            "metrics": self.metrics,
        }

    @classmethod
    def from_state_dict(cls, state: Dict[str, Any]) -> "MemoryWeb":
        """Restore from serialised state."""
        web = cls(edge_policy=state.get("edge_policy", "default"))
        for label, data in state.get("memory_store", {}).items():
            web.memory_store[label] = {
                "stability": data["stability"],
                "connections": data.get("connections", []),
                "first_seen": data.get("first_seen", 0),
                "last_accessed": data.get("last_accessed", 0),
                "access_count": data.get("access_count", 1),
                "metadata": data.get("metadata", {}),
            }
            web.graph.add_node(label, stability=data["stability"])
        for edge in state.get("edges", []):
            web.graph.add_edge(edge["source"], edge["target"], weight=edge["weight"])
        web.metrics = state.get("metrics", web.metrics)
        return web

    def get_metrics(self) -> Dict[str, Any]:
        """Return current metrics."""
        self._update_avg_stability()
        return dict(self.metrics)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_avg_stability(self) -> None:
        if self.memory_store:
            self.metrics["avg_stability"] = sum(
                d["stability"] for d in self.memory_store.values()
            ) / len(self.memory_store)
        else:
            self.metrics["avg_stability"] = 0.0

    @staticmethod
    def _get_ethical_charge(concept: str) -> float:
        """Map a concept name to an ethical charge in ``[-1, 1]``."""
        positive = {"benefit", "good", "justice", "fair", "trust", "care", "virtue", "integrity"}
        negative = {"harm", "wrong", "danger", "risk", "pain", "suffering", "injury"}
        lower = concept.lower()
        for kw in positive:
            if kw in lower:
                return 0.5
        for kw in negative:
            if kw in lower:
                return -0.5
        return 0.0
