"""MemoryWeb — associative memory graph implementing the ethomorphic MemoryBackend.

Internally uses NetworkX for graph storage.  This is the **only** module
in verdant/ that imports NetworkX.
"""

from __future__ import annotations

import time
from copy import deepcopy
from pathlib import Path
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
                "ethics_salience_peak": 0.0,
                "ethics_salience_floor": 0.0,
                "ethics_salience_last_cycle": 0,
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
                others.sort(key=lambda x: (-float(x[1]), str(x[0])))
                for other_label, _ in others[:3]:
                    self.connect(label, other_label, 0.3)

        self.memory_store[label].setdefault("ethics_salience_peak", 0.0)
        self.memory_store[label].setdefault("ethics_salience_floor", 0.0)
        self.memory_store[label].setdefault("ethics_salience_last_cycle", 0)
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

    def remove_connection(self, label1: str, label2: str) -> bool:
        """Remove an edge from both the NetworkX graph and the connections cache.

        Callers that only invoke ``graph.remove_edge`` leave
        ``memory_store[*]['connections']`` stale (phantom neighbors).
        """
        a, b = str(label1), str(label2)
        removed = False
        if self.graph.has_edge(a, b):
            self.graph.remove_edge(a, b)
            removed = True
            self.metrics["total_connections"] = max(
                0, int(self.metrics.get("total_connections", 0)) - 1,
            )
        for node, other in ((a, b), (b, a)):
            if node in self.memory_store:
                self.memory_store[node]["connections"] = [
                    x for x in self.memory_store[node].get("connections", [])
                    if str(x[0]) != other
                ]
        return removed

    def get_neighbors(self, label: str) -> List[str]:
        """Return immediate neighbor labels."""
        if label not in self.graph:
            return []
        return sorted(str(neighbor) for neighbor in self.graph.neighbors(label))

    def list_concepts(self) -> List[str]:
        """Return all concept labels."""
        return sorted(str(label) for label in self.memory_store.keys())

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
        for label, data in sorted(self.memory_store.items(), key=lambda item: str(item[0])):
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
        for node in sorted(ego.nodes(), key=str):
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
            for neighbor in sorted(self.graph.neighbors(concept), key=str):
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
        for u, v in sorted(self.graph.edges(), key=lambda edge: (str(edge[0]), str(edge[1]))):
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
        for label, data in sorted(self.memory_store.items(), key=lambda item: str(item[0])):
            nodes[label] = {
                "stability": data["stability"],
                "access_count": data["access_count"],
                "last_accessed": data["last_accessed"],
                "metadata": data["metadata"],
            }
        edges = [
            {"source": u, "target": v, "weight": d.get("weight", 0.5)}
            for u, v, d in sorted(self.graph.edges(data=True), key=lambda edge: (str(edge[0]), str(edge[1])))
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
                    "ethics_salience_peak": v.get("ethics_salience_peak", 0.0),
                    "ethics_salience_floor": v.get("ethics_salience_floor", 0.0),
                    "ethics_salience_last_cycle": v.get("ethics_salience_last_cycle", 0),
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
                "connections": [tuple(conn) for conn in data.get("connections", [])],
                "first_seen": data.get("first_seen", 0),
                "last_accessed": data.get("last_accessed", 0),
                "access_count": data.get("access_count", 1),
                "metadata": data.get("metadata", {}),
                "ethics_salience_peak": data.get("ethics_salience_peak", 0.0),
                "ethics_salience_floor": data.get("ethics_salience_floor", 0.0),
                "ethics_salience_last_cycle": data.get("ethics_salience_last_cycle", 0),
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

    def prune_connections(self, max_per_node: int = 50) -> None:
        """Prune concept connection lists to top-K by stored weight."""
        for node_id in self.list_concepts():
            data = self.get_concept(node_id)
            if not isinstance(data, dict):
                continue
            connections = data.get("connections", [])
            if not isinstance(connections, list):
                continue
            if len(connections) > max_per_node:
                connections.sort(
                    key=lambda conn: (
                        float(conn[1]) if isinstance(conn, (list, tuple)) and len(conn) > 1 else 0.0
                    ),
                    reverse=True,
                )
                data["connections"] = connections[:max_per_node]

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


class ShardedMemoryWeb:
    """Facade exposing a shard-aware MemoryBackend over one active canvas.

    Phase 2 deliberately keeps a single monolithic active shard so the rest of
    Verdant can depend on the facade contract before physical shard mitosis is
    introduced. The underlying canvas remains a normal ``MemoryWeb``.
    """

    DEFAULT_SHARD_ID = "basin_monolith_000000"

    def __init__(
        self,
        active_canvas: Optional[MemoryWeb] = None,
        *,
        active_shard_id: str = DEFAULT_SHARD_ID,
        manifest: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.active_canvas = active_canvas or MemoryWeb()
        self.active_shard_id = str(active_shard_id)
        self.manifest = deepcopy(manifest) if manifest is not None else self._default_manifest()
        self._dirty = False
        self._warm_cache: Dict[str, MemoryWeb] = {}

    @classmethod
    def monolith(cls, active_canvas: Optional[MemoryWeb] = None) -> "ShardedMemoryWeb":
        """Create a facade backed by a single active monolith shard."""
        return cls(active_canvas=active_canvas, active_shard_id=cls.DEFAULT_SHARD_ID)

    @property
    def graph(self) -> nx.Graph:
        return self.active_canvas.graph

    @property
    def memory_store(self) -> Dict[str, Dict[str, Any]]:
        return self.active_canvas.memory_store

    @property
    def thought_clusters(self) -> Dict[str, List[str]]:
        return self.active_canvas.thought_clusters

    @property
    def activation_history(self) -> Dict[str, List[Tuple[float, float]]]:
        return self.active_canvas.activation_history

    @property
    def edge_policy(self) -> str:
        return self.active_canvas.edge_policy

    @edge_policy.setter
    def edge_policy(self, value: str) -> None:
        self.active_canvas.edge_policy = value

    @property
    def metrics(self) -> Dict[str, Any]:
        return self.active_canvas.metrics

    def add_concept(self, label: str, stability: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.active_canvas.add_concept(label, stability=stability, metadata=metadata)
        self._dirty = True
        self._refresh_active_manifest()

    add_thought = add_concept

    def get_concept(self, label: str) -> Optional[Dict[str, Any]]:
        return self.active_canvas.get_concept(label)

    def connect(self, label1: str, label2: str, weight: float = 0.5) -> bool:
        created = self.active_canvas.connect(label1, label2, weight=weight)
        if created:
            self._dirty = True
            self._refresh_active_manifest()
        return created

    connect_thoughts = connect

    def get_neighbors(self, label: str) -> List[str]:
        return self.active_canvas.get_neighbors(label)

    def list_concepts(self) -> List[str]:
        return self.active_canvas.list_concepts()

    def list_active_concepts(self) -> List[str]:
        """Return labels resident in the active canvas."""
        return self.active_canvas.list_concepts()

    def reinforce(self, label: str, amount: float = 0.1) -> float:
        return self.active_canvas.reinforce(label, amount=amount)

    reinforce_memory = reinforce

    def remove_connection(self, label1: str, label2: str) -> bool:
        """Delegate dual-write edge removal to the active canvas."""
        return self.active_canvas.remove_connection(label1, label2)

    def decay(self, factor: float = 0.01) -> int:
        return self.active_canvas.decay(factor=factor)

    decay_memories = decay

    def retrieve_related(self, label: str, depth: int = 2, limit: int = 10) -> List[Tuple[str, float]]:
        return self.active_canvas.retrieve_related(label, depth=depth, limit=limit)

    retrieve_related_thoughts = retrieve_related

    def activate_concepts(
        self,
        seeds: List[str],
        strength: float = 0.7,
        spread_factor: float = 0.5,
        max_depth: int = 3,
        threshold: float = 0.1,
    ) -> Dict[str, float]:
        return self.active_canvas.activate_concepts(
            seeds,
            strength=strength,
            spread_factor=spread_factor,
            max_depth=max_depth,
            threshold=threshold,
        )

    def cluster_thoughts(self, min_stability: float = 0.3) -> Dict[str, List[str]]:
        return self.active_canvas.cluster_thoughts(min_stability=min_stability)

    def get_emergent_nodes(self) -> List[str]:
        return self.active_canvas.get_emergent_nodes()

    def get_edge_classification(self) -> Dict[str, int]:
        return self.active_canvas.get_edge_classification()

    def to_chunks(self) -> Dict[str, Any]:
        return self.active_canvas.to_chunks()

    def to_state_dict(self) -> Dict[str, Any]:
        state = self._active_canvas_state_without_ghosts()
        state["sharded_facade"] = {
            "active_shard_id": self.active_shard_id,
            "manifest": deepcopy(self.manifest),
        }
        return state

    @classmethod
    def from_state_dict(cls, state: Dict[str, Any]) -> "ShardedMemoryWeb":
        facade_state = state.get("sharded_facade", {}) if isinstance(state, dict) else {}
        canvas_state = state.get("active_canvas", state) if isinstance(state, dict) else state
        canvas = MemoryWeb.from_state_dict(canvas_state)
        return cls(
            active_canvas=canvas,
            active_shard_id=str(facade_state.get("active_shard_id", cls.DEFAULT_SHARD_ID)),
            manifest=facade_state.get("manifest"),
        )

    def get_metrics(self) -> Dict[str, Any]:
        return self.active_canvas.get_metrics()

    def prune_connections(self, max_per_node: int = 50) -> None:
        self.active_canvas.prune_connections(max_per_node=max_per_node)

    def mark_dirty(self) -> None:
        self._dirty = True
        self._refresh_active_manifest(dirty=True)

    def flush_shards(self, memory_root: str | Path, *, generation: str | None = None) -> Dict[str, Any]:
        """Persist active shard state and trigger mitosis when caps are exceeded.

        This is the Phase 6 router hook: callers provide a memory root containing
        ``manifest.json`` and ``shards/``. If the dirty active shard exceeds the
        manifest caps, it is physically split and the first daughter becomes the
        active canvas.
        """
        from verdant.memory.mitosis import split_and_persist
        from verdant.memory.persistence import save_state

        root = Path(memory_root)
        shards_dir = root / "shards"
        shards_dir.mkdir(parents=True, exist_ok=True)
        self._refresh_active_manifest(dirty=True)

        result = split_and_persist(
            memory_web=self.active_canvas,
            manifest=self.manifest,
            parent_shard_id=self.active_shard_id,
            memory_root=root,
            generation=generation,
        )
        if result is not None:
            self.active_canvas = MemoryWeb.from_state_dict(result.active_state)
            self.active_shard_id = result.active_shard_id
            self.manifest = result.manifest
            self._dirty = False
            self._warm_cache = {self.active_shard_id: self.active_canvas}
            self._load_mandatory_bridge_ghosts(root)
            return {
                "mitosis_performed": True,
                "parent_shard_id": result.parent_shard_id,
                "daughter_shard_ids": [daughter.shard_id for daughter in result.daughters],
                "weak_bridge_edges": len(result.weak_bridge_edges),
                "memory_root": str(root),
            }

        self._strip_ghosts()
        self._populate_active_concept_index()
        active_meta = self.manifest.setdefault("shards", {}).setdefault(self.active_shard_id, {})
        active_meta.setdefault("path", f"shards/{self.active_shard_id}.json")
        shard_path = root / str(active_meta["path"])
        save_state(
            shard_path,
            {
                "version": 1,
                "schema": "verdant.memory_shard.v1",
                "shard_id": self.active_shard_id,
                "anchors": active_meta.get("anchor_labels", []),
                "generation": generation,
                "memory_web": self.active_canvas.to_state_dict(),
            },
            generation=generation,
            temp_failpoint="active_shard_temp_written",
            commit_failpoint="active_shard_committed",
        )
        active_meta["dirty"] = False
        self._dirty = False
        self.manifest["updated_at"] = time.time()
        if generation is not None:
            self.manifest.setdefault("transactions", {})["committed_generation"] = generation
            self.manifest["manifest_generation"] = generation
        save_state(
            root / "manifest.json",
            self.manifest,
            generation=generation,
            temp_failpoint="manifest_temp_written",
            commit_failpoint="manifest_committed",
        )
        return {
            "mitosis_performed": False,
            "active_shard_id": self.active_shard_id,
            "memory_root": str(root),
        }


    def thaw(self, shard_id: str, memory_root: str | Path) -> None:
        """Load *shard_id* as the active canvas and materialize mandatory ghosts."""
        shard_id = str(shard_id)
        root = Path(memory_root)
        if shard_id == self.active_shard_id:
            return
        if self._dirty:
            self.flush_shards(root)

        if shard_id in self._warm_cache:
            canvas = self._warm_cache.pop(shard_id)
        else:
            meta = (self.manifest.get("shards", {}) or {}).get(shard_id, {})
            path_value = (
                meta.get("path", f"shards/{shard_id}.json")
                if isinstance(meta, dict)
                else f"shards/{shard_id}.json"
            )
            target_path = root / str(path_value)
            if not target_path.exists() and not str(path_value).startswith("shards/"):
                target_path = root / "shards" / str(path_value)
            # Self-heal: missing shard files should not crash interactive
            # inspection / eval restore — mark split and stay on active canvas.
            if not target_path.exists():
                if isinstance(meta, dict):
                    meta["state"] = "split"
                ci = self.manifest.get("concept_index", {})
                if isinstance(ci, dict):
                    for label in list(ci.keys()):
                        homes = ci[label] if isinstance(ci[label], list) else [ci[label]]
                        homes = [h for h in homes if h != shard_id]
                        if homes:
                            ci[label] = homes
                        else:
                            del ci[label]
                return
            from verdant.memory.persistence import load_state

            document = load_state(target_path)
            canvas = MemoryWeb.from_state_dict(document.get("memory_web", document))
        self._strip_ghosts(canvas)
        self.active_canvas = canvas
        self.active_shard_id = shard_id
        self._warm_cache[shard_id] = self.active_canvas
        # Honour manifest LRU (was hardcoded > 2)
        lru_size = int(
            (self.manifest.get("defaults", {}) or {}).get("lru_cache_size", 2) or 2
        )
        lru_size = max(1, lru_size)
        while len(self._warm_cache) > lru_size:
            self._warm_cache.pop(next(iter(self._warm_cache)))
        self._refresh_active_manifest(dirty=False)
        self._load_mandatory_bridge_ghosts(root)

    def _active_canvas_state_without_ghosts(self) -> Dict[str, Any]:
        state = self.active_canvas.to_state_dict()
        store = state.get("memory_store", {})
        ghost_labels = {
            label for label, data in store.items()
            if (data.get("metadata") or {}).get("ghost")
        }
        if not ghost_labels:
            return state
        state["memory_store"] = {
            label: data for label, data in store.items()
            if label not in ghost_labels
        }
        state["edges"] = [
            edge for edge in state.get("edges", [])
            if edge.get("source") not in ghost_labels and edge.get("target") not in ghost_labels
        ]
        metrics = dict(state.get("metrics", {}) or {})
        metrics["total_concepts"] = len(state["memory_store"])
        metrics["total_connections"] = len(state["edges"])
        state["metrics"] = metrics
        return state

    def _populate_active_concept_index(self) -> None:
        concept_index = self.manifest.setdefault("concept_index", {})
        for label, data in self.memory_store.items():
            if (data.get("metadata") or {}).get("ghost"):
                continue
            concept_index[str(label)] = [self.active_shard_id]

    def _strip_ghosts(self, canvas: Optional[MemoryWeb] = None) -> None:
        canvas = canvas or self.active_canvas
        ghost_labels = [
            label for label, data in canvas.memory_store.items()
            if (data.get("metadata") or {}).get("ghost")
        ]
        for label in ghost_labels:
            canvas.memory_store.pop(label, None)
            canvas.activation_history.pop(label, None)
            if canvas.graph.has_node(label):
                canvas.graph.remove_node(label)
        canvas.metrics["total_concepts"] = len(canvas.memory_store)
        canvas.metrics["total_connections"] = canvas.graph.number_of_edges()
        canvas._update_avg_stability()

    def _load_mandatory_bridge_ghosts(self, root: Path) -> None:
        from verdant.memory.persistence import load_state
        from verdant.memory.router import MemoryRouter

        router = MemoryRouter(self.manifest)
        for edge in router.get_mandatory_bridges_for_shard(self.active_shard_id):
            if edge.get("source_shard") == self.active_shard_id:
                home_label = str(edge.get("source"))
                ghost_label = str(edge.get("target"))
                ghost_shard = str(edge.get("target_shard"))
            else:
                home_label = str(edge.get("target"))
                ghost_label = str(edge.get("source"))
                ghost_shard = str(edge.get("source_shard"))
            if ghost_label in self.active_canvas.memory_store:
                continue
            meta = (self.manifest.get("shards", {}) or {}).get(ghost_shard, {})
            if not isinstance(meta, dict) or meta.get("state") == "split":
                continue
            path_value = meta.get("path", f"shards/{ghost_shard}.json")
            shard_path = root / str(path_value)
            if not shard_path.exists():
                continue
            document = load_state(shard_path)
            other_state = document.get("memory_web", document)
            other_store = other_state.get("memory_store", {}) if isinstance(other_state, dict) else {}
            node_data = dict(other_store.get(ghost_label, {}) or {})
            if not node_data:
                continue
            node_data.setdefault("connections", [])
            metadata = dict(node_data.get("metadata", {}) or {})
            metadata.update({"ghost": True, "home_shard": ghost_shard})
            node_data["metadata"] = metadata
            node_data["activation"] = float(edge.get("weight", 0.5)) * float(edge.get("thaw_penalty", self.manifest.get("defaults", {}).get("thaw_penalty", 0.35)))
            node_data.setdefault("ethics_salience_peak", 0.0)
            node_data.setdefault("ethics_salience_floor", 0.0)
            node_data.setdefault("ethics_salience_last_cycle", 0)
            self.active_canvas.memory_store[ghost_label] = node_data
            self.active_canvas.graph.add_node(ghost_label, stability=float(node_data.get("stability", 0.5)))
            if self.active_canvas.graph.has_node(home_label):
                self.active_canvas.graph.add_edge(home_label, ghost_label, weight=float(edge.get("weight", 0.5)))

    def _default_manifest(self) -> Dict[str, Any]:
        now = time.time()
        return {
            "version": 1,
            "schema": "verdant.routing_registry.v1",
            "created_at": now,
            "updated_at": now,
            "active_shards": [self.active_shard_id],
            "defaults": {
                "max_nodes_per_shard": 512,
                "max_edges_per_shard": 20_000,
                "thaw_penalty": 0.35,
                "thaw_threshold": 0.12,
                "noise_floor": 0.01,
                "salience_decay_rate": 0.92,
                "ethics_anchor_threshold": 0.35,
                "salience_high_water_floor": 0.20,
            },
            "shards": {
                self.active_shard_id: {
                    "shard_id": self.active_shard_id,
                    "path": f"shards/{self.active_shard_id}.json",
                    "state": "active",
                    "node_count": self.graph.number_of_nodes(),
                    "edge_count": self.graph.number_of_edges(),
                    "dirty": False,
                    "anchor_labels": [],
                    "centroid": {
                        "space": "verdant.anchor_hash.v1",
                        "dimensions": 0,
                        "values": [],
                    },
                }
            },
            "concept_index": {},
            "weak_bridge_edges": [],
        }

    def _refresh_active_manifest(self, *, dirty: bool = True) -> None:
        shard = self.manifest.setdefault("shards", {}).setdefault(self.active_shard_id, {})
        shard.update({
            "shard_id": self.active_shard_id,
            "state": "active",
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "dirty": bool(dirty),
            "updated_at": time.time(),
        })
        self.manifest["active_shards"] = [self.active_shard_id]
        self.manifest["updated_at"] = shard["updated_at"]
