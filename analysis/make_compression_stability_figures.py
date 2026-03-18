"""Generate combined compression/stability figures from analysis outputs."""

from __future__ import annotations

import sys
from pathlib import Path as _PathBootstrap

sys.path.insert(0, str(_PathBootstrap(__file__).resolve().parents[1]))

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from analysis.compression_analysis import extract_branching_series, select_compression_proxy
from analysis.telemetry_analysis_common import iter_seed_cycles, resolve_run_dir


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_overlay_seed(run_dir: Path, seeds: int) -> tuple[int | None, list[dict]]:
    best_seed = None
    best_rows: list[dict] = []
    best_buds = -1
    for seed, _cycles_path, rows in iter_seed_cycles(run_dir, seeds):
        bud_total = int(sum(extract_branching_series(rows)))
        if bud_total > best_buds:
            best_seed = seed
            best_rows = rows
            best_buds = bud_total
    return best_seed, best_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Create combined compression/stability figures")
    parser.add_argument("--compression", required=True)
    parser.add_argument("--stability", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    compression = _load_json(Path(args.compression))
    stability = _load_json(Path(args.stability))
    run_dir = resolve_run_dir(args.run_dir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    seeds = max(int(compression.get("seeds_analyzed", 0)), int(stability.get("seeds_analyzed", 0)))

    plt.style.use("dark_background")

    lags = np.arange(len(compression["compression_vs_branching"]["lag_correlations_mean"]))
    mean_corr = np.asarray(compression["compression_vs_branching"]["lag_correlations_mean"], dtype=float)
    std_corr = np.asarray(compression["compression_vs_branching"]["lag_correlations_std"], dtype=float)
    fig1, ax1 = plt.subplots(figsize=(9, 5))
    ax1.plot(lags, mean_corr, color="#61dafb", linewidth=2)
    ax1.fill_between(lags, mean_corr - std_corr, mean_corr + std_corr, color="#61dafb", alpha=0.25)
    ax1.axhline(0.0, color="white", linestyle="--", linewidth=1, alpha=0.7)
    best_lag = int(compression["compression_vs_branching"]["best_lag"])
    best_corr = float(compression["compression_vs_branching"]["best_correlation"])
    ax1.scatter([best_lag], [best_corr], color="#ff6b6b", zorder=5)
    ax1.annotate(f"best lag={best_lag}\nr={best_corr:.3f}", (best_lag, best_corr), xytext=(8, 8), textcoords="offset points")
    ax1.set_xlabel("Lag (cycles)")
    ax1.set_ylabel("Correlation coefficient")
    ax1.set_title("Compression → Branching Lag Correlation (Improved Proxy)")
    fig1.tight_layout()
    fig1.savefig(outdir / "compression_branching_lag_correlation.png", dpi=180)
    plt.close(fig1)

    edge_positions = stability["edge_stability"].get("cycle_positions", [])
    edge_mean = stability["edge_stability"].get("mean_trajectory", [])
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    for item in stability.get("per_seed", []):
        cycles = item.get("cycle_positions", [])
        trajectory = item.get("edge_trajectory", [])
        if cycles and trajectory:
            ax2.plot(cycles, trajectory, color="#888888", alpha=0.25, linewidth=1)
    if edge_positions and edge_mean:
        ax2.plot(edge_positions, edge_mean, color="#7bd389", linewidth=2.5)
    ax2.axhline(1.0, color="white", linestyle="--", linewidth=1, alpha=0.7)
    ax2.set_xlabel("Cycle")
    ax2.set_ylabel("Edge stability ratio")
    ax2.set_title("Edge Growth/Contraction Ratio Over 300 Cycles")
    fig2.tight_layout()
    fig2.savefig(outdir / "edge_stability_trajectory.png", dpi=180)
    plt.close(fig2)

    node_positions = stability["node_stability"].get("cycle_positions", [])
    node_mean = stability["node_stability"].get("mean_trajectory", [])
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    for item in stability.get("per_seed", []):
        cycles = item.get("cycle_positions", [])
        trajectory = item.get("node_trajectory", [])
        if cycles and trajectory:
            ax3.plot(cycles, trajectory, color="#888888", alpha=0.25, linewidth=1)
    if node_positions and node_mean:
        ax3.plot(node_positions, node_mean, color="#f4d35e", linewidth=2.5)
    ax3.axhline(1.0, color="white", linestyle="--", linewidth=1, alpha=0.7)
    ax3.set_xlabel("Cycle")
    ax3.set_ylabel("Node stability ratio")
    ax3.set_title("Emergent Birth Rate Over 300 Cycles")
    fig3.tight_layout()
    fig3.savefig(outdir / "node_stability_trajectory.png", dpi=180)
    plt.close(fig3)

    overlay_seed, overlay_rows = _pick_overlay_seed(run_dir, seeds)
    overlay_proxy_type, overlay_proxy = select_compression_proxy(overlay_rows) if overlay_rows else ("unavailable", [])
    overlay_buds = extract_branching_series(overlay_rows) if overlay_rows else []
    fig4, ax4 = plt.subplots(figsize=(11, 5))
    cycles = list(range(len(overlay_proxy)))
    if overlay_proxy:
        ax4.plot(cycles, overlay_proxy, color="#c792ea", linewidth=2)
    for idx, bud in enumerate(overlay_buds):
        if bud > 0:
            ax4.axvline(idx, color="#ff6b6b", alpha=0.4, linewidth=1)
    ax4.set_xlabel("Cycle")
    ax4.set_ylabel(f"Compression proxy ({overlay_proxy_type})")
    title_seed = overlay_seed if overlay_seed is not None else 0
    ax4.set_title(f"Compression Time Series with Bud Events Overlay (seed {title_seed})")
    fig4.tight_layout()
    fig4.savefig(outdir / "compression_time_series_with_buds.png", dpi=180)
    plt.close(fig4)


if __name__ == "__main__":
    main()
