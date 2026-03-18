"""Generate semantic coherence figures from aggregate semantic evaluation output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def make_figures(results_path: Path, outdir: Path) -> list[Path]:
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    outdir.mkdir(parents=True, exist_ok=True)
    plt.style.use("dark_background")

    written: list[Path] = []

    fractions = [
        float(payload.get("overall_meaningful_fraction", 0.0)),
        float(payload.get("overall_partial_fraction", 0.0)),
        float(payload.get("overall_not_meaningful_fraction", 0.0)),
    ]
    labels = ["Meaningful", "Partial", "Not meaningful"]
    colors = ["#4cc9f0", "#f9c74f", "#f72585"]

    fig1, ax1 = plt.subplots(figsize=(8, 6))
    ax1.bar(["Semantic Coherence"], [fractions[0]], color=colors[0], label=labels[0])
    ax1.bar(["Semantic Coherence"], [fractions[1]], bottom=[fractions[0]], color=colors[1], label=labels[1])
    ax1.bar(
        ["Semantic Coherence"],
        [fractions[2]],
        bottom=[fractions[0] + fractions[1]],
        color=colors[2],
        label=labels[2],
    )
    ax1.set_ylim(0, 1)
    ax1.set_ylabel("Fraction of Emergent Concepts")
    ax1.set_title("Semantic Coherence of Emergent Concepts")
    ax1.legend(loc="upper right")
    ax1.text(
        0,
        min(0.98, fractions[0] + fractions[1] + fractions[2] + 0.02),
        f"Meaningful: {fractions[0]:.1%}\nPartial: {fractions[1]:.1%}\nNot meaningful: {fractions[2]:.1%}",
        ha="center",
        va="top",
        fontsize=11,
    )
    fig1.tight_layout()
    path1 = outdir / "semantic_score_distribution.png"
    fig1.savefig(path1, dpi=180)
    plt.close(fig1)
    written.append(path1)

    basin_payload = payload.get("by_basin_overall", {}) if isinstance(payload, dict) else {}
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    if basin_payload:
        basin_ids = list(sorted(basin_payload))
        means = [float(basin_payload[basin_id]["mean_score"]) for basin_id in basin_ids]
        counts = [int(basin_payload[basin_id]["total_count"]) for basin_id in basin_ids]
        bars = ax2.bar(basin_ids, means, color="#4361ee")
        for bar, count in zip(bars, counts):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02, f"n={count}", ha="center", va="bottom", fontsize=10)
    ax2.set_ylim(0, 1.05)
    ax2.set_ylabel("Mean Semantic Score")
    ax2.set_title("Semantic Score by Basin")
    fig2.tight_layout()
    path2 = outdir / "semantic_score_by_basin.png"
    fig2.savefig(path2, dpi=180)
    plt.close(fig2)
    written.append(path2)

    concepts = payload.get("all_concepts", []) if isinstance(payload, dict) else []
    fig3, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
    if concepts:
        access = [int(concept.get("access_count", 0) or 0) for concept in concepts]
        connections = [int(concept.get("connection_count", 0) or 0) for concept in concepts]
        scores = [float(concept.get("score", 0.0) or 0.0) for concept in concepts]
        axes[0].scatter(access, scores, alpha=0.7, color="#4cc9f0", edgecolors="none")
        axes[1].scatter(connections, scores, alpha=0.7, color="#f72585", edgecolors="none")
    axes[0].set_xlabel("Access Count")
    axes[1].set_xlabel("Connection Count")
    axes[0].set_ylabel("Semantic Score")
    axes[0].set_title("Semantic Score vs Access Count")
    axes[1].set_title("Semantic Score vs Connection Count")
    for axis in axes:
        axis.set_ylim(0, 1.05)
        axis.grid(alpha=0.2)
    fig3.tight_layout()
    path3 = outdir / "semantic_score_vs_structure.png"
    fig3.savefig(path3, dpi=180)
    plt.close(fig3)
    written.append(path3)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Create semantic coherence figures")
    parser.add_argument("--results", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    written = make_figures(Path(args.results), Path(args.outdir))
    for path in written:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
