"""Assess robustness of basin/community detection under stochastic perturbations."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import networkx as nx
import numpy as np
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

try:
    from analysis.extract_scaffolding_metrics import load_graph
except ImportError:
    from extract_scaffolding_metrics import load_graph


def build_backbone_graph(state_path: Path, k: int = 6) -> nx.Graph:
    """Build undirected top-k backbone from state graph edges."""
    nodes, edges = load_graph(str(state_path))
    graph = nx.Graph()
    for nid in nodes.keys():
        graph.add_node(str(nid))

    by_source: dict[str, list[dict[str, float | str]]] = defaultdict(list)
    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        weight = float(edge.get("weight", 1.0))
        by_source[source].append({"source": source, "target": target, "weight": weight})

    for source, source_edges in by_source.items():
        for edge in sorted(source_edges, key=lambda x: float(x["weight"]), reverse=True)[: max(1, k)]:
            target = str(edge["target"])
            weight = float(edge["weight"])
            if graph.has_edge(source, target):
                graph[source][target]["weight"] = max(float(graph[source][target].get("weight", 0.0)), weight)
            else:
                graph.add_edge(source, target, weight=weight)

    return graph


def run_detection(graph: nx.Graph, seed: int | None = None, algorithm: str = "louvain") -> list[set[str]]:
    """Run community detection and return partition as list of node sets."""
    algo = algorithm.lower()
    if algo == "greedy":
        return [set(c) for c in nx.algorithms.community.greedy_modularity_communities(graph, weight="weight")]
    if algo == "louvain":
        return [set(c) for c in nx.algorithms.community.louvain_communities(graph, weight="weight", seed=seed)]
    raise ValueError(f"Unsupported algorithm: {algorithm}")


def partition_to_labels(partition: list[set[str]], all_nodes: list[str]) -> list[int]:
    """Convert partition to labels aligned to all_nodes order."""
    labels: dict[str, int] = {}
    for idx, community in enumerate(partition):
        for node in community:
            labels[str(node)] = idx
    return [labels.get(str(node), -1) for node in all_nodes]


def _summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "values": []}
    arr = np.array(values, dtype=float)
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=0)),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "values": [float(v) for v in values],
    }


def compute_node_stability(partitions: list[list[set[str]]], all_nodes: list[str]) -> dict[str, float]:
    """Compute per-node stability based on most-common exact community membership set."""
    if not partitions:
        return {node: 0.0 for node in all_nodes}

    per_node: dict[str, list[tuple[str, ...]]] = {node: [] for node in all_nodes}
    for partition in partitions:
        membership: dict[str, tuple[str, ...]] = {}
        for comm in partition:
            signature = tuple(sorted(str(node) for node in comm))
            for node in comm:
                membership[str(node)] = signature
        for node in all_nodes:
            per_node[node].append(membership.get(node, ("__missing__",)))

    stability: dict[str, float] = {}
    n_runs = len(partitions)
    for node, assignments in per_node.items():
        counts: dict[tuple[str, ...], int] = defaultdict(int)
        for assignment in assignments:
            counts[assignment] += 1
        stability[node] = max(counts.values()) / n_runs if counts else 0.0
    return stability


def compute_robustness(state_path: Path, n_runs: int = 10, algorithm: str = "louvain", k: int = 6) -> dict[str, Any]:
    """Run repeated community detection and compute pairwise stability metrics."""
    graph = build_backbone_graph(state_path, k=k)
    all_nodes = sorted(str(n) for n in graph.nodes())

    partitions: list[list[set[str]]] = []
    labels_per_run: list[list[int]] = []
    basin_counts: list[int] = []
    for run_idx in range(n_runs):
        seed = run_idx
        partition = run_detection(graph, seed=seed, algorithm=algorithm)
        partitions.append(partition)
        labels_per_run.append(partition_to_labels(partition, all_nodes))
        basin_counts.append(len(partition))

    pairwise_ari: list[float] = []
    pairwise_nmi: list[float] = []
    for i, j in combinations(range(n_runs), 2):
        pairwise_ari.append(float(adjusted_rand_score(labels_per_run[i], labels_per_run[j])))
        pairwise_nmi.append(float(normalized_mutual_info_score(labels_per_run[i], labels_per_run[j])))

    node_stability = compute_node_stability(partitions, all_nodes)
    node_scores = np.array(list(node_stability.values()), dtype=float) if node_stability else np.array([], dtype=float)
    emergent_scores = np.array([node_stability[n] for n in all_nodes if str(n).startswith("Emergent_")], dtype=float)
    seeded_scores = np.array([node_stability[n] for n in all_nodes if not str(n).startswith("Emergent_")], dtype=float)

    ari_mean = float(mean(pairwise_ari)) if pairwise_ari else 1.0
    if ari_mean > 0.8:
        interpretation = "stable"
    elif ari_mean >= 0.5:
        interpretation = "moderate"
    else:
        interpretation = "unstable"

    return {
        "state_path": str(state_path),
        "algorithm": algorithm,
        "n_runs": n_runs,
        "n_nodes": int(graph.number_of_nodes()),
        "n_edges": int(graph.number_of_edges()),
        "pairwise_ari": _summary(pairwise_ari),
        "pairwise_nmi": _summary(pairwise_nmi),
        "basin_count_per_run": basin_counts,
        "basin_count_mean": float(mean(basin_counts)) if basin_counts else 0.0,
        "basin_count_std": float(pstdev(basin_counts)) if len(basin_counts) > 1 else 0.0,
        "node_stability": {
            "mean": float(node_scores.mean()) if node_scores.size else 0.0,
            "std": float(node_scores.std(ddof=0)) if node_scores.size else 0.0,
            "min": float(node_scores.min()) if node_scores.size else 0.0,
            "fraction_above_0.8": float((node_scores >= 0.8).mean()) if node_scores.size else 0.0,
            "fraction_above_0.9": float((node_scores >= 0.9).mean()) if node_scores.size else 0.0,
            "emergent_node_stability_mean": float(emergent_scores.mean()) if emergent_scores.size else 0.0,
            "seeded_node_stability_mean": float(seeded_scores.mean()) if seeded_scores.size else 0.0,
            "per_node": {node: float(score) for node, score in node_stability.items()},
        },
        "run_labels": {str(idx): labels for idx, labels in enumerate(labels_per_run)},
        "all_nodes": all_nodes,
        "interpretation": interpretation,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Basin detection robustness check")
    parser.add_argument("--state", required=True)
    parser.add_argument("--n-runs", type=int, default=10)
    parser.add_argument("--algorithm", choices=["louvain", "greedy"], default="louvain")
    parser.add_argument("--k", type=int, default=6)
    parser.add_argument("--outfile", required=True)
    args = parser.parse_args()

    result = compute_robustness(Path(args.state), n_runs=args.n_runs, algorithm=args.algorithm, k=args.k)
    out = Path(args.outfile)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
