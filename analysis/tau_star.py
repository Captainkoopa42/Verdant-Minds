"""Post-hoc τ* (tau-star) tension coefficient computation for saved Verdant states."""

from __future__ import annotations

import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis.state_adapter import VerdantState
from verdant.memory.graph import MemoryWeb


DEFAULT_WEIGHTS: dict[str, float] = {
    "coactivation": 0.4,
    "dimension": 0.3,
    "ethical": 0.2,
    "stability": 0.1,
}


@dataclass(frozen=True)
class TauComponents:
    """Resolved τ* components for a single pair."""

    coactivation: float | None
    dimension: float | None
    ethical: float | None
    stability: float | None

    def as_dict(self) -> dict[str, float | None]:
        return {
            "coactivation": self.coactivation,
            "dimension": self.dimension,
            "ethical": self.ethical,
            "stability": self.stability,
        }


def canonical_pair(concept_a: str, concept_b: str) -> tuple[str, str]:
    """Return a stable undirected pair key."""
    a = str(concept_a)
    b = str(concept_b)
    return (a, b) if a <= b else (b, a)


def parse_weight_string(text: str) -> dict[str, float]:
    """Parse ``w1,w2,w3,w4`` into the named τ* weight mapping."""
    parts = [part.strip() for part in str(text).split(",")]
    if len(parts) != 4:
        raise ValueError("weights must be four comma-separated values: w1,w2,w3,w4")
    try:
        w1, w2, w3, w4 = (float(part) for part in parts)
    except ValueError as exc:
        raise ValueError("weights must be numeric") from exc
    return {
        "coactivation": w1,
        "dimension": w2,
        "ethical": w3,
        "stability": w4,
    }


class TauStarComputer:
    """Compute τ* tension coefficients for concept pairs from a saved state."""

    def __init__(
        self,
        state_path: str | Path,
        weights: dict[str, float] | None = None,
        include_disconnected: bool = False,
    ) -> None:
        self.state_path = Path(state_path)
        self.state = VerdantState.load(self.state_path)
        self.include_disconnected = bool(include_disconnected)
        self.weights = self._normalize_weight_dict(weights or DEFAULT_WEIGHTS)
        self._raw_state = self.state.raw

        self.node_names = sorted(str(node["name"]) for node in self.state.nodes)
        self.node_map = {str(node["name"]): node for node in self.state.nodes}
        self.edge_weights = self._build_edge_map()
        self.dimension_vectors = self._build_dimension_vectors()
        self.basin_membership = self._build_basin_membership()
        self._tau_cache: dict[tuple[str, str], float | None] = {}
        self._component_cache: dict[tuple[str, str], TauComponents] = {}

    @staticmethod
    def _normalize_weight_dict(weights: dict[str, float]) -> dict[str, float]:
        normalized = {name: float(weights.get(name, 0.0)) for name in DEFAULT_WEIGHTS}
        if all(value == 0.0 for value in normalized.values()):
            raise ValueError("at least one τ* weight must be non-zero")
        return normalized

    def _build_edge_map(self) -> dict[tuple[str, str], float]:
        edge_map: dict[tuple[str, str], float] = {}
        for edge in self.state.edges:
            source = str(edge["source"])
            target = str(edge["target"])
            if source == target:
                continue
            edge_map[canonical_pair(source, target)] = float(edge.get("weight", 0.0))
        return edge_map

    def _extract_dim_counts(self) -> tuple[int, int]:
        ecwf = self._raw_state.get("ecwf")
        meta = ecwf.get("metadata", ecwf) if isinstance(ecwf, dict) else {}
        cog = meta.get("num_cognitive_dims") if isinstance(meta, dict) else None
        eth = meta.get("num_ethical_dims") if isinstance(meta, dict) else None
        max_cog = 0
        max_eth = 0
        bridge = self._raw_state.get("bridge") if isinstance(self._raw_state.get("bridge"), dict) else {}
        mapping_state = bridge.get("concept_dimension_mapping") if isinstance(bridge, dict) else {}
        if isinstance(mapping_state, dict):
            for mappings in mapping_state.values():
                if not isinstance(mappings, list):
                    continue
                for item in mappings:
                    if not isinstance(item, (list, tuple)) or len(item) < 3:
                        continue
                    mtype, idx, _weight = item[:3]
                    try:
                        dim_idx = int(idx)
                    except (TypeError, ValueError):
                        continue
                    if str(mtype) == "cognitive":
                        max_cog = max(max_cog, dim_idx + 1)
                    elif str(mtype) == "ethical":
                        max_eth = max(max_eth, dim_idx + 1)
        return int(cog or max_cog), int(eth or max_eth)

    def _build_dimension_vectors(self) -> dict[str, np.ndarray]:
        bridge = self._raw_state.get("bridge") if isinstance(self._raw_state.get("bridge"), dict) else {}
        mapping_state = bridge.get("concept_dimension_mapping") if isinstance(bridge, dict) else {}
        if not isinstance(mapping_state, dict) or not mapping_state:
            return {}

        cog_dims, eth_dims = self._extract_dim_counts()
        total_dims = cog_dims + eth_dims
        if total_dims <= 0:
            return {}

        vectors: dict[str, np.ndarray] = {}
        for concept, mappings in mapping_state.items():
            if not isinstance(mappings, list):
                continue
            vector = np.zeros(total_dims, dtype=float)
            for item in mappings:
                if not isinstance(item, (list, tuple)) or len(item) < 3:
                    continue
                mtype, idx, weight = item[:3]
                try:
                    dim_idx = int(idx)
                    dim_weight = float(weight)
                except (TypeError, ValueError):
                    continue
                if str(mtype) == "cognitive" and 0 <= dim_idx < cog_dims:
                    vector[dim_idx] += dim_weight
                elif str(mtype) == "ethical" and 0 <= dim_idx < eth_dims:
                    vector[cog_dims + dim_idx] += dim_weight
            if np.linalg.norm(vector) > 0:
                vectors[str(concept)] = vector
        return vectors

    def _build_basin_membership(self) -> dict[str, set[str]]:
        membership: dict[str, set[str]] = {}
        registry = self.state.basin_registry.get("basins", {}) if isinstance(self.state.basin_registry, dict) else {}
        if isinstance(registry, dict) and registry:
            for basin_id, payload in registry.items():
                nodes = payload.get("nodes", []) if isinstance(payload, dict) else []
                for node in nodes:
                    membership.setdefault(str(node), set()).add(str(basin_id))
            return membership

        basins = self.state.basins
        if isinstance(basins, list):
            for idx, basin in enumerate(basins):
                if not isinstance(basin, dict):
                    continue
                basin_id = str(basin.get("basin_id", f"basin_{idx}"))
                for node in basin.get("nodes", []) or []:
                    membership.setdefault(str(node), set()).add(basin_id)
        elif isinstance(basins, dict):
            for basin_id, payload in basins.items():
                if not isinstance(payload, dict):
                    continue
                for node in payload.get("nodes", []) or []:
                    membership.setdefault(str(node), set()).add(str(basin_id))
        return membership

    @property
    def components_available(self) -> list[str]:
        available = ["coactivation"]
        if self.dimension_vectors:
            available.append("dimension")
        available.append("ethical")
        available.append("stability")
        return available

    def get_edge_weight(self, concept_a: str, concept_b: str) -> float | None:
        return self.edge_weights.get(canonical_pair(concept_a, concept_b))

    def get_node_stability(self, concept: str) -> float | None:
        node = self.node_map.get(str(concept))
        if node is None:
            return None
        try:
            return float(node.get("stability", 0.0))
        except (TypeError, ValueError):
            return None

    def get_ethical_charge(self, concept: str) -> float:
        return float(MemoryWeb._get_ethical_charge(str(concept)))

    def get_dimension_vector(self, concept: str) -> np.ndarray | None:
        return self.dimension_vectors.get(str(concept))

    def compute_components(self, concept_a: str, concept_b: str) -> TauComponents:
        key = canonical_pair(concept_a, concept_b)
        cached = self._component_cache.get(key)
        if cached is not None:
            return cached

        edge_weight = self.get_edge_weight(*key)
        if edge_weight is None and not self.include_disconnected:
            components = TauComponents(None, None, None, None)
            self._component_cache[key] = components
            return components

        tau_coact = 1.0 - float(edge_weight) if edge_weight is not None else 1.0

        tau_dim: float | None = None
        vector_a = self.get_dimension_vector(key[0])
        vector_b = self.get_dimension_vector(key[1])
        if vector_a is not None and vector_b is not None:
            norm_a = float(np.linalg.norm(vector_a))
            norm_b = float(np.linalg.norm(vector_b))
            if norm_a > 1e-12 and norm_b > 1e-12:
                cosine = float(np.dot(vector_a, vector_b) / (norm_a * norm_b))
                tau_dim = max(0.0, min(1.0, 1.0 - max(-1.0, min(1.0, cosine))))

        charge_a = self.get_ethical_charge(key[0])
        charge_b = self.get_ethical_charge(key[1])
        tau_eth = max(0.0, min(1.0, abs(charge_a - charge_b) / 2.0))

        stability_a = self.get_node_stability(key[0])
        stability_b = self.get_node_stability(key[1])
        tau_stab = None
        if stability_a is not None and stability_b is not None:
            tau_stab = max(0.0, min(1.0, abs(stability_a - stability_b)))

        components = TauComponents(
            coactivation=max(0.0, min(1.0, tau_coact)),
            dimension=tau_dim,
            ethical=tau_eth,
            stability=tau_stab,
        )
        self._component_cache[key] = components
        return components

    def compute_tau_star(self, concept_a: str, concept_b: str) -> float | None:
        """Compute τ*(a, b), or ``None`` for disconnected pairs when excluded."""
        key = canonical_pair(concept_a, concept_b)
        if key[0] == key[1]:
            return 0.0
        if key in self._tau_cache:
            return self._tau_cache[key]

        components = self.compute_components(*key)
        if components.coactivation is None and not self.include_disconnected:
            self._tau_cache[key] = None
            return None

        total_weight = 0.0
        total_value = 0.0
        for name, raw_weight in self.weights.items():
            component_value = components.as_dict().get(name)
            if component_value is None or raw_weight <= 0.0:
                continue
            total_weight += raw_weight
            total_value += raw_weight * float(component_value)

        if total_weight <= 0.0:
            self._tau_cache[key] = None
            return None

        tau_star = max(0.0, min(1.0, total_value / total_weight))
        self._tau_cache[key] = tau_star
        return tau_star

    def iter_candidate_pairs(self) -> list[tuple[str, str]]:
        if self.include_disconnected:
            names = self.node_names
            return [
                (names[i], names[j])
                for i in range(len(names))
                for j in range(i + 1, len(names))
            ]
        return sorted(self.edge_weights)

    def compute_all_pairs(self) -> dict[tuple[str, str], float]:
        """Compute τ* for all candidate pairs."""
        results: dict[tuple[str, str], float] = {}
        for pair in self.iter_candidate_pairs():
            value = self.compute_tau_star(*pair)
            if value is not None:
                results[pair] = value
        return results

    def get_tau_star_stats(self, bins: int = 20) -> dict[str, Any]:
        """Summarize τ* values across all computed pairs."""
        values = list(self.compute_all_pairs().values())
        if not values:
            return {
                "count": 0,
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "std": 0.0,
                "histogram": {"bins": [], "counts": []},
            }

        hist_counts, hist_bins = np.histogram(values, bins=bins, range=(0.0, 1.0))
        return {
            "count": len(values),
            "min": float(min(values)),
            "max": float(max(values)),
            "mean": float(statistics.mean(values)),
            "std": float(statistics.pstdev(values)) if len(values) > 1 else 0.0,
            "histogram": {
                "bins": [float(edge) for edge in hist_bins.tolist()],
                "counts": [int(count) for count in hist_counts.tolist()],
            },
        }

    def get_tau_star_distribution(self, bins: int = 20) -> dict[str, Any]:
        stats = self.get_tau_star_stats(bins=bins)
        return {
            "state": str(self.state_path),
            "count": int(stats["count"]),
            "bins": stats["histogram"]["bins"],
            "counts": stats["histogram"]["counts"],
            "summary": {
                "min": float(stats["min"]),
                "max": float(stats["max"]),
                "mean": float(stats["mean"]),
                "std": float(stats["std"]),
            },
        }

    def get_tau_star_vs_edge_weight(self) -> list[dict[str, float]]:
        scatter: list[dict[str, float]] = []
        for pair, edge_weight in sorted(self.edge_weights.items()):
            tau = self.compute_tau_star(*pair)
            if tau is None:
                continue
            scatter.append(
                {
                    "concept_a": pair[0],
                    "concept_b": pair[1],
                    "edge_weight": float(edge_weight),
                    "tau_star": float(tau),
                }
            )
        return scatter

    def get_tau_star_by_basin(self) -> dict[str, Any]:
        within: list[float] = []
        between: list[float] = []
        unassigned: list[float] = []
        for pair, tau in self.compute_all_pairs().items():
            basins_a = self.basin_membership.get(pair[0], set())
            basins_b = self.basin_membership.get(pair[1], set())
            if basins_a and basins_b:
                if basins_a & basins_b:
                    within.append(tau)
                else:
                    between.append(tau)
            else:
                unassigned.append(tau)

        def _summary(values: list[float]) -> dict[str, float | int | None]:
            if not values:
                return {"count": 0, "mean": None, "std": None}
            return {
                "count": len(values),
                "mean": float(statistics.mean(values)),
                "std": float(statistics.pstdev(values)) if len(values) > 1 else 0.0,
            }

        return {
            "within_basin": _summary(within),
            "between_basin": _summary(between),
            "unassigned": _summary(unassigned),
        }

    def export_pairs(self) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for pair, tau in self.compute_all_pairs().items():
            payload.append(
                {
                    "concept_a": pair[0],
                    "concept_b": pair[1],
                    "tau_star": float(tau),
                    "edge_weight": self.get_edge_weight(*pair),
                    "components": self.compute_components(*pair).as_dict(),
                }
            )
        return payload


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--weights", default="0.4,0.3,0.2,0.1")
    parser.add_argument("--include-disconnected", action="store_true")
    parser.add_argument("--out", default=None, help="Optional JSON file to write pairwise τ* data.")
    args = parser.parse_args()

    computer = TauStarComputer(
        args.state,
        weights=parse_weight_string(args.weights),
        include_disconnected=args.include_disconnected,
    )
    payload = {
        "state": str(computer.state_path),
        "weights": computer.weights,
        "components_used": computer.components_available,
        "tau_star_stats": computer.get_tau_star_stats(),
        "pairs": computer.export_pairs(),
    }
    text = json.dumps(payload, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
