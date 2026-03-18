"""Compute improved compression-vs-branching correlations from cycle telemetry."""

from __future__ import annotations

import sys
from pathlib import Path as _PathBootstrap

sys.path.insert(0, str(_PathBootstrap(__file__).resolve().parents[1]))

import argparse
from pathlib import Path
from typing import Any

import numpy as np

from analysis.telemetry_analysis_common import (
    iter_seed_cycles,
    lagged_correlations,
    mean_std_by_position,
    resolve_run_dir,
    to_float,
    to_int,
    write_json,
)


def select_compression_proxy(rows: list[dict[str, Any]]) -> tuple[str, list[float]]:
    """Choose the best available per-cycle compression proxy."""
    basin_density = [to_float(row.get("basin_density_before")) for row in rows]
    if any(value is not None for value in basin_density):
        from analysis.telemetry_analysis_common import interpolate_series

        return "basin_density_before", interpolate_series(basin_density)

    edge_keys = ("total_edges", "edge_count_estimate", "edge_count")
    edge_series: list[float | None] = []
    for row in rows:
        edge_count = None
        telemetry = row.get("telemetry", {})
        if not isinstance(telemetry, dict):
            telemetry = {}
        for key in edge_keys:
            edge_count = to_float(row.get(key))
            if edge_count is None:
                edge_count = to_float(telemetry.get(key))
            if edge_count is not None:
                break
        memory_size = to_float(row.get("memory_size"), 0.0) or 0.0
        if edge_count is None or edge_count <= 0:
            edge_series.append(None)
            continue
        edge_series.append(float((memory_size ** 2) / (2.0 * edge_count)))
    if any(value is not None for value in edge_series):
        from analysis.telemetry_analysis_common import interpolate_series

        return "memory_sq_over_2_edges", interpolate_series(edge_series)

    global_density = [to_float(row.get("global_edge_ratio_before"), 0.0) or 0.0 for row in rows]
    return "global_edge_ratio_before", global_density


def extract_branching_series(rows: list[dict[str, Any]]) -> list[float]:
    return [1.0 if to_int(row.get("bud_events_count")) > 0 else 0.0 for row in rows]


def extract_emergence_birth_series(rows: list[dict[str, Any]]) -> list[float]:
    births: list[float] = []
    previous = None
    for row in rows:
        current = to_int(row.get("emergent_count"))
        births.append(float(max(0, current - previous)) if previous is not None else 0.0)
        previous = current
    return births


def analyze_run(run_dir: Path, seeds: int, max_lag: int) -> dict[str, Any]:
    per_seed_branching: list[dict[str, Any]] = []
    per_seed_emergence: list[dict[str, Any]] = []
    branching_corrs: list[list[float]] = []
    emergence_corrs: list[list[float]] = []
    proxy_types: list[str] = []

    for seed, _cycles_path, rows in iter_seed_cycles(run_dir, seeds):
        proxy_type, compression = select_compression_proxy(rows)
        proxy_types.append(proxy_type)
        branching = extract_branching_series(rows)
        emergence = extract_emergence_birth_series(rows)
        branching_lags = lagged_correlations(compression, branching, max_lag)
        emergence_lags = lagged_correlations(compression, emergence, max_lag)
        branching_corrs.append(branching_lags)
        emergence_corrs.append(emergence_lags)
        per_seed_branching.append(
            {
                "seed": seed,
                "lag_correlations": [float(v) if not np.isnan(v) else None for v in branching_lags],
            }
        )
        per_seed_emergence.append(
            {
                "seed": seed,
                "lag_correlations": [float(v) if not np.isnan(v) else None for v in emergence_lags],
            }
        )

    mean_branching, std_branching = mean_std_by_position(branching_corrs)
    mean_emergence, std_emergence = mean_std_by_position(emergence_corrs)
    best_branch_lag = int(np.nanargmax(mean_branching)) if mean_branching else 0
    best_emergence_lag = int(np.nanargmax(mean_emergence)) if mean_emergence else 0
    proxy_type = max(set(proxy_types), key=proxy_types.count) if proxy_types else "unavailable"

    if mean_branching:
        best_branch_corr = float(mean_branching[best_branch_lag])
    else:
        best_branch_corr = float("nan")
    if mean_emergence:
        best_emergence_corr = float(mean_emergence[best_emergence_lag])
    else:
        best_emergence_corr = float("nan")

    interpretation = (
        f"Using {proxy_type} as the compression proxy across {len(per_seed_branching)} seeds, "
        f"the strongest mean compression→branching correlation occurs at lag {best_branch_lag} "
        f"with r={best_branch_corr:.3f}; the strongest compression→emergence correlation occurs "
        f"at lag {best_emergence_lag} with r={best_emergence_corr:.3f}."
    )

    return {
        "proxy_type": proxy_type,
        "seeds_analyzed": len(per_seed_branching),
        "compression_vs_branching": {
            "lag_correlations_mean": mean_branching,
            "lag_correlations_std": std_branching,
            "best_lag": best_branch_lag,
            "best_correlation": best_branch_corr,
            "per_seed": per_seed_branching,
        },
        "compression_vs_emergence": {
            "lag_correlations_mean": mean_emergence,
            "lag_correlations_std": std_emergence,
            "best_lag": best_emergence_lag,
            "best_correlation": best_emergence_corr,
            "per_seed": per_seed_emergence,
        },
        "interpretation": interpretation,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze compression-vs-branching lag correlations")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--max-lag", type=int, default=10)
    parser.add_argument("--outfile", required=True)
    args = parser.parse_args()

    run_dir = resolve_run_dir(args.run_dir)
    result = analyze_run(run_dir=run_dir, seeds=args.seeds, max_lag=args.max_lag)
    write_json(Path(args.outfile), result)


if __name__ == "__main__":
    main()
