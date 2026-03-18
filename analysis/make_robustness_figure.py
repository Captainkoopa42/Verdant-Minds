"""Create figures for basin detection robustness outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate robustness figures")
    parser.add_argument("--robustness", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    robust_path = Path(args.robustness)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    data = json.loads(robust_path.read_text(encoding="utf-8"))
    all_nodes = list(data.get("all_nodes", []))
    run_labels_raw = data.get("run_labels", {})
    run_keys = sorted(run_labels_raw.keys(), key=lambda x: int(x))
    labels_matrix = np.array([run_labels_raw[k] for k in run_keys], dtype=int).T if run_keys else np.empty((0, 0), dtype=int)

    per_node_stability = data.get("node_stability", {}).get("per_node", {})
    sorted_nodes = sorted(all_nodes, key=lambda n: per_node_stability.get(n, 0.0), reverse=True)
    node_to_row = {node: idx for idx, node in enumerate(all_nodes)}
    reorder_idx = [node_to_row[n] for n in sorted_nodes if n in node_to_row]
    if reorder_idx and labels_matrix.size:
        labels_matrix = labels_matrix[reorder_idx, :]

    plt.style.use("dark_background")

    fig1, ax1 = plt.subplots(figsize=(12, 8))
    if labels_matrix.size:
        im = ax1.imshow(labels_matrix, aspect="auto", interpolation="nearest", cmap="tab20")
        fig1.colorbar(im, ax=ax1, fraction=0.03, pad=0.02, label="Community Label")
    ax1.set_title("Node Community Assignments Across Detection Runs")
    ax1.set_xlabel("Detection Run")
    ax1.set_ylabel("Nodes (sorted by stability)")
    ax1.set_xticks(np.arange(len(run_keys)))
    ax1.set_xticklabels([str(int(k) + 1) for k in run_keys])
    fig1.tight_layout()
    fig1_path = outdir / "node_stability_heatmap.png"
    fig1.savefig(fig1_path, dpi=180)
    plt.close(fig1)

    ari_values = data.get("pairwise_ari", {}).get("values", [])
    nmi_values = data.get("pairwise_nmi", {}).get("values", [])
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    if ari_values:
        ax2.hist(ari_values, bins=12, alpha=0.7, label="ARI", color="#4cc9f0")
    if nmi_values:
        ax2.hist(nmi_values, bins=12, alpha=0.5, label="NMI", color="#f72585")
    ax2.axvline(0.8, linestyle="--", linewidth=1.2, color="white", label="0.8 stability threshold")
    ax2.set_xlabel("Pairwise Similarity")
    ax2.set_ylabel("Frequency")
    ax2.set_title("Pairwise ARI/NMI Distribution")
    ax2.legend()
    fig2.tight_layout()
    fig2_path = outdir / "ari_nmi_histogram.png"
    fig2.savefig(fig2_path, dpi=180)
    plt.close(fig2)

    emergent_scores = [float(per_node_stability.get(n, 0.0)) for n in all_nodes if str(n).startswith("Emergent_")]
    seeded_scores = [float(per_node_stability.get(n, 0.0)) for n in all_nodes if not str(n).startswith("Emergent_")]
    fig3, ax3 = plt.subplots(figsize=(8, 6))
    series = [emergent_scores if emergent_scores else [0.0], seeded_scores if seeded_scores else [0.0]]
    vp = ax3.violinplot(series, showmeans=True, widths=0.8)
    for body, color in zip(vp["bodies"], ["#f72585", "#4cc9f0"]):
        body.set_facecolor(color)
        body.set_alpha(0.7)
    ax3.set_xticks([1, 2])
    ax3.set_xticklabels(["Emergent", "Seeded"])
    ax3.set_ylabel("Node Stability")
    ax3.set_ylim(0, 1.05)
    ax3.set_title("Node Stability by Node Type")
    fig3.tight_layout()
    fig3_path = outdir / "stability_by_node_type.png"
    fig3.savefig(fig3_path, dpi=180)
    plt.close(fig3)

    print(f"wrote {fig1_path}")
    print(f"wrote {fig2_path}")
    print(f"wrote {fig3_path}")


if __name__ == "__main__":
    main()
