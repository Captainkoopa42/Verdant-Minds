#!/usr/bin/env python3
"""Verify the Verdant Triangle Inequality on the saved concept graph."""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable

import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis.tau_star import DEFAULT_WEIGHTS, TauStarComputer, parse_weight_string


SENSITIVITY_CONFIGS: list[tuple[str, dict[str, float]]] = [
    ("default", {"coactivation": 0.4, "dimension": 0.3, "ethical": 0.2, "stability": 0.1}),
    ("coactivation_only", {"coactivation": 1.0, "dimension": 0.0, "ethical": 0.0, "stability": 0.0}),
    ("dimension_only", {"coactivation": 0.0, "dimension": 1.0, "ethical": 0.0, "stability": 0.0}),
    ("equal", {"coactivation": 0.25, "dimension": 0.25, "ethical": 0.25, "stability": 0.25}),
    ("no_stability", {"coactivation": 0.45, "dimension": 0.35, "ethical": 0.2, "stability": 0.0}),
    ("coactivation_ethical", {"coactivation": 0.5, "dimension": 0.0, "ethical": 0.5, "stability": 0.0}),
]


def _build_graph(computer: TauStarComputer, emergent_only: bool = False) -> nx.Graph:
    graph = nx.Graph()
    emergent_names = {str(node["name"]) for node in computer.state.emergent_nodes}
    for node_name in computer.node_names:
        if emergent_only and node_name not in emergent_names:
            continue
        graph.add_node(node_name)
    for (a, b), weight in computer.edge_weights.items():
        if emergent_only and (a not in emergent_names or b not in emergent_names):
            continue
        graph.add_edge(a, b, weight=float(weight))
    return graph


def _triangle_stream(graph: nx.Graph) -> Iterable[tuple[str, str, str]]:
    nodes = sorted(graph.nodes())
    order = {node: idx for idx, node in enumerate(nodes)}
    adjacency = {node: {nbr for nbr in graph.neighbors(node) if order[nbr] > order[node]} for node in nodes}
    for u in nodes:
        for v in sorted(adjacency[u], key=order.get):
            common = adjacency[u] & adjacency[v]
            for w in sorted(common, key=order.get):
                yield (u, v, w)


def _sample_or_collect_triples(
    graph: nx.Graph,
    max_triples: int,
    rng: random.Random,
) -> tuple[list[tuple[str, str, str]], int, bool]:
    sample: list[tuple[str, str, str]] = []
    total = 0
    for triple in _triangle_stream(graph):
        total += 1
        if len(sample) < max_triples:
            sample.append(triple)
            continue
        replace_idx = rng.randint(1, total)
        if replace_idx <= max_triples:
            sample[replace_idx - 1] = triple
    return sample, total, total > max_triples


def _margin_histogram(values: list[float], bins: int = 20) -> dict[str, list[float] | list[int]]:
    if not values:
        return {"bins": [], "counts": []}
    counts, hist_bins = np.histogram(values, bins=bins)
    return {
        "bins": [float(value) for value in hist_bins.tolist()],
        "counts": [int(value) for value in counts.tolist()],
    }


def _classify_basin_relation(
    computer: TauStarComputer,
    triple: tuple[str, str, str],
) -> str:
    basin_sets = [computer.basin_membership.get(node, set()) for node in triple]
    if any(not basins for basins in basin_sets):
        return "unassigned"
    shared = set.intersection(*basin_sets)
    if shared:
        return "within_basin"
    return "cross_basin"


def verify_verdant_triangle(
    state_path: str | Path,
    *,
    weights: dict[str, float] | None = None,
    include_disconnected: bool = False,
    emergent_only: bool = False,
    max_triples: int = 1_000_000,
    random_seed: int = 0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compute τ* and evaluate the Verdant Triangle Inequality."""
    computer = TauStarComputer(
        state_path=state_path,
        weights=weights or DEFAULT_WEIGHTS,
        include_disconnected=include_disconnected,
    )
    graph = _build_graph(computer, emergent_only=emergent_only)
    sampled_triples, total_triangles_found, sampled = _sample_or_collect_triples(
        graph, max_triples=max(1, int(max_triples)), rng=random.Random(random_seed)
    )

    upper_violations = 0
    lower_violations = 0
    valid_triples = 0
    invalid_triples: list[dict[str, Any]] = []
    all_margins: list[float] = []
    valid_margins: list[float] = []
    basin_stats: dict[str, dict[str, int]] = {
        "within_basin": {"valid": 0, "invalid": 0},
        "cross_basin": {"valid": 0, "invalid": 0},
        "unassigned": {"valid": 0, "invalid": 0},
    }
    eps = 1e-9

    for p, q, r in sampled_triples:
        tau_pq = computer.compute_tau_star(p, q)
        tau_qr = computer.compute_tau_star(q, r)
        tau_pr = computer.compute_tau_star(p, r)
        if tau_pq is None or tau_qr is None or tau_pr is None:
            continue

        upper_margin = max(tau_pq, tau_qr) - tau_pr
        lower_margin = tau_pr - abs(tau_pq - tau_qr)
        margin = min(upper_margin, lower_margin)
        upper_violated = upper_margin < -eps
        lower_violated = lower_margin < -eps
        violation_magnitude = max(0.0, -upper_margin, -lower_margin)
        record = {
            "p": p,
            "q": q,
            "r": r,
            "tau_pq": float(tau_pq),
            "tau_qr": float(tau_qr),
            "tau_pr": float(tau_pr),
            "upper_violated": bool(upper_violated),
            "lower_violated": bool(lower_violated),
            "violation_magnitude": float(violation_magnitude),
            "margin_to_violation": float(margin),
        }

        all_margins.append(float(margin))
        if upper_violated:
            upper_violations += 1
        if lower_violated:
            lower_violations += 1
        if upper_violated or lower_violated:
            invalid_triples.append(record)
            basin_stats[_classify_basin_relation(computer, (p, q, r))]["invalid"] += 1
        else:
            valid_triples += 1
            valid_margins.append(float(margin))
            basin_stats[_classify_basin_relation(computer, (p, q, r))]["valid"] += 1

    total_triples_checked = valid_triples + len(invalid_triples)
    invalid_triples.sort(key=lambda item: item["violation_magnitude"], reverse=True)
    validity_fraction = (
        float(valid_triples / total_triples_checked)
        if total_triples_checked
        else 0.0
    )

    tau_star_stats = computer.get_tau_star_stats()

    def _basin_summary(name: str) -> dict[str, float | int | None]:
        stats = basin_stats[name]
        total = stats["valid"] + stats["invalid"]
        return {
            "valid_triples": int(stats["valid"]),
            "invalid_triples": int(stats["invalid"]),
            "total_triples": int(total),
            "validity_fraction": float(stats["valid"] / total) if total else None,
        }

    report = {
        "state": str(Path(state_path)),
        "total_triangles_found": int(total_triangles_found),
        "total_triples_checked": int(total_triples_checked),
        "sampled": bool(sampled),
        "sample_size": int(len(sampled_triples)),
        "valid_triples": int(valid_triples),
        "invalid_triples": int(len(invalid_triples)),
        "validity_fraction": float(validity_fraction),
        "upper_bound_violations": int(upper_violations),
        "lower_bound_violations": int(lower_violations),
        "max_violation_magnitude": float(max((item["violation_magnitude"] for item in invalid_triples), default=0.0)),
        "mean_margin_to_violation": float(statistics.mean(all_margins)) if all_margins else 0.0,
        "tau_star_stats": {
            "min": float(tau_star_stats["min"]),
            "max": float(tau_star_stats["max"]),
            "mean": float(tau_star_stats["mean"]),
            "std": float(tau_star_stats["std"]),
        },
        "sample_invalid_triples": invalid_triples[:10],
        "components_used": computer.components_available,
        "weights": dict(computer.weights),
        "include_disconnected": bool(include_disconnected),
        "emergent_only": bool(emergent_only),
        "within_basin": _basin_summary("within_basin"),
        "cross_basin": _basin_summary("cross_basin"),
        "unassigned_basin": _basin_summary("unassigned"),
    }

    figures = {
        "tau_star_distribution": computer.get_tau_star_distribution(),
        "tau_star_vs_edge_weight": computer.get_tau_star_vs_edge_weight(),
        "triangle_margin_distribution": {
            "count": len(valid_margins),
            "histogram": _margin_histogram(valid_margins),
        },
        "tau_star_by_basin": computer.get_tau_star_by_basin(),
    }
    return report, figures


def run_sensitivity(
    state_path: str | Path,
    *,
    include_disconnected: bool = False,
    emergent_only: bool = False,
    max_triples: int = 1_000_000,
) -> dict[str, Any]:
    configurations: list[dict[str, Any]] = []
    for name, weights in SENSITIVITY_CONFIGS:
        report, _ = verify_verdant_triangle(
            state_path,
            weights=weights,
            include_disconnected=include_disconnected,
            emergent_only=emergent_only,
            max_triples=max_triples,
        )
        configurations.append(
            {
                "name": name,
                "weights": dict(weights),
                "validity_fraction": float(report["validity_fraction"]),
                "total_triples": int(report["total_triples_checked"]),
                "violations": int(report["invalid_triples"]),
            }
        )
    return {
        "configurations": configurations,
        "robust_across_configs": bool(all(item["validity_fraction"] > 0.95 for item in configurations)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="Path to state.json")
    parser.add_argument("--outdir", default="tau_star_results")
    parser.add_argument("--weights", default="0.4,0.3,0.2,0.1")
    parser.add_argument("--sensitivity", action="store_true")
    parser.add_argument("--figures", action="store_true")
    parser.add_argument("--max-triples", type=int, default=1_000_000)
    parser.add_argument("--include-disconnected", action="store_true")
    parser.add_argument("--emergent-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    weights = parse_weight_string(args.weights)

    report, figures = verify_verdant_triangle(
        args.state,
        weights=weights,
        include_disconnected=args.include_disconnected,
        emergent_only=args.emergent_only,
        max_triples=args.max_triples,
    )
    (outdir / "verdant_triangle_verification.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    if args.sensitivity:
        sensitivity = run_sensitivity(
            args.state,
            include_disconnected=args.include_disconnected,
            emergent_only=args.emergent_only,
            max_triples=args.max_triples,
        )
        (outdir / "tau_star_sensitivity.json").write_text(
            json.dumps(sensitivity, indent=2),
            encoding="utf-8",
        )

    if args.figures:
        (outdir / "tau_star_distribution.json").write_text(
            json.dumps(figures["tau_star_distribution"], indent=2),
            encoding="utf-8",
        )
        (outdir / "tau_star_vs_edge_weight.json").write_text(
            json.dumps(figures["tau_star_vs_edge_weight"], indent=2),
            encoding="utf-8",
        )
        (outdir / "triangle_margin_distribution.json").write_text(
            json.dumps(figures["triangle_margin_distribution"], indent=2),
            encoding="utf-8",
        )
        (outdir / "tau_star_by_basin.json").write_text(
            json.dumps(figures["tau_star_by_basin"], indent=2),
            encoding="utf-8",
        )

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
