#!/usr/bin/env python3
"""Create phase-diagram figures from sweep results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_sweeps(sweep_dir: Path) -> list[dict]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(sweep_dir.glob("sweep_*/sweep_results.json"))]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate phase-diagram sweep figures")
    parser.add_argument("--sweep-dir", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        raise SystemExit(f"matplotlib is required: {exc}")

    plt.style.use("dark_background")
    sweeps = _load_sweeps(Path(args.sweep_dir))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if not sweeps:
        raise SystemExit("No sweep_results.json files found")

    # Figure 1: onset cycle vs parameter
    fig1, axes1 = plt.subplots(1, len(sweeps), figsize=(6 * len(sweeps), 5), squeeze=False)
    for i, sweep in enumerate(sweeps):
        ax = axes1[0][i]
        xs = [r["value"] for r in sweep["results"]]
        ys = [r["onset_cycle_mean"] for r in sweep["results"]]
        es = [r["onset_cycle_std"] for r in sweep["results"]]
        ax.errorbar(xs, ys, yerr=es, fmt="o-", capsize=4)
        ax.axhline(9, linestyle="--", color="#ff7676", alpha=0.8)
        ax.set_title(f"onset_cycle vs {sweep['parameter']}")
        ax.set_xlabel(sweep["parameter"])
        ax.set_ylabel("onset_cycle")
    fig1.tight_layout()
    fig1.savefig(outdir / "phase_onset_cycle.png", dpi=220, bbox_inches="tight")

    # Figure 2: onset T_g vs parameter
    fig2, axes2 = plt.subplots(1, len(sweeps), figsize=(6 * len(sweeps), 5), squeeze=False)
    for i, sweep in enumerate(sweeps):
        ax = axes2[0][i]
        xs = [r["value"] for r in sweep["results"]]
        ys = [r["onset_t_g_mean"] for r in sweep["results"]]
        es = [r["onset_t_g_std"] for r in sweep["results"]]
        ax.errorbar(xs, ys, yerr=es, fmt="o-", capsize=4)
        ax.axhline(0.566, linestyle="--", color="#ff7676", alpha=0.8)
        ax.set_title(f"onset_t_g vs {sweep['parameter']}")
        ax.set_xlabel(sweep["parameter"])
        ax.set_ylabel("onset_t_g")
    fig2.tight_layout()
    fig2.savefig(outdir / "phase_onset_tg.png", dpi=220, bbox_inches="tight")

    # Figure 3: onset state scatter
    fig3, ax3 = plt.subplots(figsize=(7, 5.5))
    for sweep in sweeps:
        xs = [r["onset_memory_mean"] for r in sweep["results"] if r["onset_memory_mean"] is not None]
        ys = [r["onset_t_g_mean"] for r in sweep["results"] if r["onset_t_g_mean"] is not None]
        cs = [r["value"] for r in sweep["results"] if r["onset_t_g_mean"] is not None and r["onset_memory_mean"] is not None]
        scatter = ax3.scatter(xs, ys, c=cs, cmap="viridis", s=80, alpha=0.9, label=sweep["parameter"])
        cbar = fig3.colorbar(scatter, ax=ax3)
        cbar.set_label(sweep["parameter"])
    ax3.set_xlabel("onset_memory_size")
    ax3.set_ylabel("onset_t_g")
    ax3.axhline(0.566, linestyle="--", color="#ff7676", alpha=0.8)
    ax3.set_title("Onset state clustering")
    fig3.tight_layout()
    fig3.savefig(outdir / "phase_onset_state_scatter.png", dpi=220, bbox_inches="tight")

    print(outdir / "phase_onset_cycle.png")
    print(outdir / "phase_onset_tg.png")
    print(outdir / "phase_onset_state_scatter.png")


if __name__ == "__main__":
    main()
