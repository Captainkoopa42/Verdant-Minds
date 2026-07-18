#!/usr/bin/env python3
"""Generate baseline-vs-Verdant temporal scaffolding comparison figure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--verdant-earlier-share", type=float, default=1.0)
    parser.add_argument("--verdant-z", type=float, default=12.73)
    parser.add_argument("--outdir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    baseline = summary.get("baseline", {})
    earlier_values = baseline.get("earlier_share_values", [])
    z_values = baseline.get("shuffle_z_values", [])

    plt.style.use("dark_background")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), dpi=200)
    fig.patch.set_facecolor("#0a0a0a")

    for ax in axes:
        ax.set_facecolor("#0a0a0a")
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("white")

    axes[0].hist(earlier_values, bins=10, color="#ff6b35", edgecolor="white", alpha=0.9)
    axes[0].axvline(args.verdant_earlier_share, color="#2ecc71", linewidth=2.5, label=f"Verdant={args.verdant_earlier_share:.3f}")
    axes[0].set_xlim(0.0, 1.0)
    axes[0].set_xlabel("earlier_share", color="white")
    axes[0].set_ylabel("count", color="white")
    axes[0].set_title("Temporal Scaffolding: Verdant vs Random Baseline", color="white")
    axes[0].legend(facecolor="#111111", edgecolor="white")

    axes[1].hist(z_values, bins=10, color="#ff3b30", edgecolor="white", alpha=0.9)
    axes[1].axvline(args.verdant_z, color="#2ecc71", linewidth=2.5, label=f"Verdant z={args.verdant_z:.2f}")
    axes[1].set_xlabel("z-score", color="white")
    axes[1].set_ylabel("count", color="white")
    axes[1].set_title("Shuffle Null Z-Scores", color="white")
    axes[1].legend(facecolor="#111111", edgecolor="white")

    fig.tight_layout()

    png_path = args.outdir / "fig_baseline_vs_verdant.png"
    pdf_path = args.outdir / "fig_baseline_vs_verdant.pdf"
    fig.savefig(png_path, facecolor=fig.get_facecolor())
    fig.savefig(pdf_path, facecolor=fig.get_facecolor())
    print(png_path)
    print(pdf_path)


if __name__ == "__main__":
    main()
