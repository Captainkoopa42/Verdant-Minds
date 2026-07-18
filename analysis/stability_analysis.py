"""Compute true growth/contraction stability metrics from cycle telemetry."""

from __future__ import annotations

import sys
from pathlib import Path as _PathBootstrap

sys.path.insert(0, str(_PathBootstrap(__file__).resolve().parents[1]))

import argparse
from pathlib import Path
from typing import Any

import numpy as np

from analysis.telemetry_analysis_common import (
    EPSILON,
    iter_seed_cycles,
    linear_slope,
    mean_std_by_position,
    resolve_run_dir,
    to_float,
    to_int,
    write_json,
)


def estimate_total_edges(rows: list[dict[str, Any]]) -> list[float]:
    """Estimate per-cycle total edge count from the best available telemetry."""
    estimates: list[float] = []
    for row in rows:
        telemetry = row.get("telemetry", {})
        if not isinstance(telemetry, dict):
            telemetry = {}
        total_edges = to_float(row.get("total_edges"))
        if total_edges is None:
            total_edges = to_float(telemetry.get("total_edges"))
        if total_edges is None:
            edge_count = to_float(row.get("edge_count"))
            if edge_count is None:
                edge_count = to_float(telemetry.get("edge_count"))
            total_edges = edge_count
        if total_edges is None:
            memory_size = to_float(row.get("memory_size"), 0.0) or 0.0
            edge_ratio = to_float(row.get("global_edge_ratio_before"), 0.0) or 0.0
            total_edges = memory_size * edge_ratio
        estimates.append(float(total_edges or 0.0))
    return estimates


def compute_growth_contraction(rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    """Extract per-cycle node/edge growth and contraction signals."""
    emergent_births: list[float] = []
    removed_nodes: list[float] = []
    boundary_emergents_created: list[float] = []
    pruned_edges: list[float] = []
    density_removed: list[float] = []
    memory_growth: list[float] = []
    edges_created: list[float] = []

    total_edges = estimate_total_edges(rows)
    prev_emergent = None
    prev_memory = None
    prev_edges = None

    for index, row in enumerate(rows):
        emergent_count = to_int(row.get("emergent_count"))
        memory_size = to_int(row.get("memory_size"))
        pruned = float(to_int(row.get("pruned_edges_count")))
        density = float(to_int(row.get("density_regulation_edges_removed")))
        removed = float(to_int(row.get("removed_nodes_count")))
        boundary_created = float(to_int(row.get("boundary_emergents_created")))

        emergent_births.append(float(max(0, emergent_count - prev_emergent)) if prev_emergent is not None else 0.0)
        memory_growth.append(float(max(0, memory_size - prev_memory)) if prev_memory is not None else 0.0)
        removed_nodes.append(removed)
        boundary_emergents_created.append(boundary_created)
        pruned_edges.append(pruned)
        density_removed.append(density)

        current_edges = total_edges[index]
        if prev_edges is None:
            edges_created.append(0.0)
        else:
            estimated_created = (current_edges - prev_edges) + pruned + density
            edges_created.append(float(max(0.0, estimated_created)))
        prev_emergent = emergent_count
        prev_memory = memory_size
        prev_edges = current_edges

    return {
        "emergent_births": emergent_births,
        "memory_growth": memory_growth,
        "boundary_emergents_created": boundary_emergents_created,
        "removed_nodes_count": removed_nodes,
        "pruned_edges_count": pruned_edges,
        "density_regulation_edges_removed": density_removed,
        "edges_created": edges_created,
        "total_edges_estimate": total_edges,
    }


def rolling_stability_ratio(
    growth: list[float],
    contraction: list[float],
    window: int,
    *,
    epsilon: float = EPSILON,
) -> tuple[list[int], list[float]]:
    """Compute rolling growth/contraction ratios over a fixed window."""
    if window <= 0:
        raise ValueError("window must be positive")
    if len(growth) != len(contraction):
        raise ValueError("growth and contraction series must align")
    if len(growth) < window:
        return [], []

    cycle_positions: list[int] = []
    ratios: list[float] = []
    for end in range(window - 1, len(growth)):
        start = end - window + 1
        growth_rate = float(sum(growth[start : end + 1]) / window)
        contraction_rate = float(sum(contraction[start : end + 1]) / window)
        ratios.append(float(growth_rate / (contraction_rate + epsilon)))
        cycle_positions.append(end)
    return cycle_positions, ratios


def classify_trend(values: list[float]) -> tuple[str, float]:
    """Classify the long-term shape of a stability trajectory."""
    if len(values) < 2:
        return "homeostatic", 0.0

    slope = linear_slope(values)
    start_dist = abs(values[0] - 1.0)
    end_dist = abs(values[-1] - 1.0)
    diffs = np.diff(np.asarray(values, dtype=float))
    sign_changes = int(np.sum(np.sign(diffs[1:]) != np.sign(diffs[:-1]))) if len(diffs) > 1 else 0
    oscillatory = sign_changes >= max(2, len(diffs) // 3) and float(np.std(values)) > 0.1

    if end_dist <= 0.15 and end_dist <= start_dist:
        return "homeostatic", slope
    if oscillatory:
        return "oscillating", slope
    if slope > 0.01 or values[-1] > values[0] + 0.2:
        return "growing", slope
    if slope < -0.01 or values[-1] < values[0] - 0.2:
        return "declining", slope
    if end_dist <= 0.2:
        return "homeostatic", slope
    return "oscillating", slope


def summarize_trajectories(trajectories: list[list[float]]) -> tuple[list[float], float, float, str, float]:
    """Aggregate stability trajectories across seeds."""
    if not trajectories:
        return [], float("nan"), float("nan"), "oscillating", 0.0

    mean_trajectory, _std_trajectory = mean_std_by_position(trajectories)
    final_values = [traj[-1] for traj in trajectories if traj]
    trend, slope = classify_trend(mean_trajectory)
    return (
        mean_trajectory,
        float(np.mean(final_values)) if final_values else float("nan"),
        float(np.std(final_values)) if final_values else float("nan"),
        trend,
        slope,
    )


def analyze_run(run_dir: Path, seeds: int, window: int) -> dict[str, Any]:
    per_seed: list[dict[str, Any]] = []
    node_trajectories: list[list[float]] = []
    edge_trajectories: list[list[float]] = []
    common_cycle_positions: list[int] | None = None

    for seed, _cycles_path, rows in iter_seed_cycles(run_dir, seeds):
        signals = compute_growth_contraction(rows)
        node_cycles, node_ratio = rolling_stability_ratio(
            signals["emergent_births"],
            signals["removed_nodes_count"],
            window,
        )
        edge_cycles, edge_ratio = rolling_stability_ratio(
            signals["edges_created"],
            [
                p + d
                for p, d in zip(
                    signals["pruned_edges_count"],
                    signals["density_regulation_edges_removed"],
                )
            ],
            window,
        )
        node_trend, _node_slope = classify_trend(node_ratio)
        edge_trend, _edge_slope = classify_trend(edge_ratio)

        if node_ratio and edge_ratio:
            common_cycle_positions = common_cycle_positions or edge_cycles
            node_trajectories.append(node_ratio)
            edge_trajectories.append(edge_ratio)

        per_seed.append(
            {
                "seed": seed,
                "node_final_ratio": float(node_ratio[-1]) if node_ratio else float("nan"),
                "edge_final_ratio": float(edge_ratio[-1]) if edge_ratio else float("nan"),
                "node_trend": node_trend,
                "edge_trend": edge_trend,
                "cycle_positions": edge_cycles,
                "node_trajectory": node_ratio,
                "edge_trajectory": edge_ratio,
            }
        )

    node_summary = summarize_trajectories(node_trajectories)
    edge_summary = summarize_trajectories(edge_trajectories)
    overall = (
        f"Across {len(per_seed)} seeds, node dynamics are {node_summary[3]} "
        f"(final mean ratio {node_summary[1]:.3f}) and edge dynamics are {edge_summary[3]} "
        f"(final mean ratio {edge_summary[1]:.3f})."
    )

    return {
        "seeds_analyzed": len(per_seed),
        "window_size": window,
        "node_stability": {
            "cycle_positions": common_cycle_positions or [],
            "mean_trajectory": node_summary[0],
            "final_ratio_mean": node_summary[1],
            "final_ratio_std": node_summary[2],
            "trend": node_summary[3],
            "trend_slope": node_summary[4],
        },
        "edge_stability": {
            "cycle_positions": common_cycle_positions or [],
            "mean_trajectory": edge_summary[0],
            "final_ratio_mean": edge_summary[1],
            "final_ratio_std": edge_summary[2],
            "trend": edge_summary[3],
            "trend_slope": edge_summary[4],
        },
        "overall_characterization": overall,
        "per_seed": per_seed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze growth/contraction stability from cycle telemetry")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--window", type=int, default=20)
    parser.add_argument("--outfile", required=True)
    args = parser.parse_args()

    run_dir = resolve_run_dir(args.run_dir)
    result = analyze_run(run_dir=run_dir, seeds=args.seeds, window=args.window)
    write_json(Path(args.outfile), result)


if __name__ == "__main__":
    main()
