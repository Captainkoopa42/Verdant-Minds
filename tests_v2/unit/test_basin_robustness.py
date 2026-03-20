from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from analysis.basin_detection_robustness import compute_node_stability, partition_to_labels, run_detection
from analysis.daughter_basin_analysis import analyze_cycles


def test_robustness_deterministic_graph() -> None:
    graph = nx.Graph()
    left = [f"l{i}" for i in range(8)]
    right = [f"r{i}" for i in range(8)]
    for nodes in (left, right):
        for i, u in enumerate(nodes):
            for v in nodes[i + 1 :]:
                graph.add_edge(u, v, weight=1.0)
    graph.add_edge("l0", "r0", weight=0.01)

    all_nodes = sorted(graph.nodes())
    labels = [partition_to_labels(run_detection(graph, seed=i, algorithm="louvain"), all_nodes) for i in range(5)]

    from sklearn.metrics import adjusted_rand_score

    scores = [adjusted_rand_score(labels[0], labels[i]) for i in range(1, 5)]
    assert min(scores) > 0.9


def test_robustness_ambiguous_graph() -> None:
    graph = nx.erdos_renyi_graph(30, 0.22, seed=11)
    for u, v in graph.edges():
        graph[u][v]["weight"] = 1.0

    all_nodes = sorted(graph.nodes())
    labels = [partition_to_labels(run_detection(graph, seed=i, algorithm="louvain"), all_nodes) for i in range(5)]

    from sklearn.metrics import adjusted_rand_score

    scores = [adjusted_rand_score(labels[0], labels[i]) for i in range(1, 5)]
    assert any(score < 0.9 for score in scores)


def test_node_stability_computation() -> None:
    all_nodes = ["a", "b", "c", "d"]
    partitions = [
        [{"a", "b"}, {"c", "d"}],
        [{"a", "b"}, {"c", "d"}],
        [{"a", "c"}, {"b", "d"}],
    ]
    stability = compute_node_stability(partitions, all_nodes)
    assert stability["a"] < 1.0
    assert stability["d"] < 1.0

    always_partitions = [[{"a", "b"}, {"c", "d"}] for _ in range(3)]
    always_stability = compute_node_stability(always_partitions, all_nodes)
    assert always_stability["a"] == 1.0
    assert always_stability["c"] == 1.0


def test_revised_daughter_metric(tmp_path: Path) -> None:
    cycles = []
    for cycle in range(12):
        rec = {
            "cycle_index": cycle,
            "seed": 0,
            "bud_events_count": 0,
            "bud_parent_basin_id": None,
            "bud_new_basin_id": None,
            "emergent_count_by_basin": {"basin_0": 12, "basin_1": 0},
        }
        if cycle == 2:
            rec["bud_events_count"] = 1
            rec["bud_parent_basin_id"] = "basin_0"
            rec["bud_new_basin_id"] = "basin_1"
        if cycle == 4:
            rec["emergent_count_by_basin"]["basin_1"] = 30
        elif cycle > 4:
            rec["emergent_count_by_basin"]["basin_1"] = 1
        cycles.append(rec)

    path = tmp_path / "cycles.jsonl"
    path.write_text("\n".join(json.dumps(c) for c in cycles) + "\n", encoding="utf-8")
    result = analyze_cycles(path)
    daughter = result["daughters"][0]

    assert daughter["max_emergent_count"] == 30
    assert daughter["final_emergent_count"] == 1
    assert daughter["became_forge_peak"] is True
    assert daughter["became_forge_final"] is False
    assert daughter["peak_to_final_ratio"] > 10
