"""Generate daughter basin growth and forge outcome figures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def _load_seed_files(analysis_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for p in sorted(analysis_dir.glob("daughter_analysis_seed_*.json")):
        rows.append(json.loads(p.read_text(encoding="utf-8")))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Create daughter basin analysis figures")
    parser.add_argument("--analysis-dir", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    analysis_dir = Path(args.analysis_dir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    seed_results = _load_seed_files(analysis_dir)
    daughters = [d for seed in seed_results for d in seed.get("daughters", [])]

    plt.style.use("dark_background")

    fig1, ax1 = plt.subplots(figsize=(10, 6))
    parent_to_color: dict[str, tuple] = {}
    cmap = plt.cm.get_cmap("tab20")
    color_idx = 0
    for d in daughters:
        parent = str(d.get("parent_id"))
        if parent not in parent_to_color:
            parent_to_color[parent] = cmap(color_idx % 20)
            color_idx += 1
        y = d.get("growth_trajectory", [])
        x = list(range(len(y)))
        ax1.plot(x, y, color=parent_to_color[parent], alpha=0.8, linewidth=1.5)
    ax1.axhline(10, linestyle="--", linewidth=1.0)
    ax1.set_xlabel("Cycles Since Birth")
    ax1.set_ylabel("Emergent Count")
    ax1.set_title("Daughter Basin Emergent Accumulation After Budding")
    fig1.tight_layout()
    fig1.savefig(outdir / "daughter_growth_trajectories.png", dpi=160)
    plt.close(fig1)

    fig2, ax2 = plt.subplots(figsize=(8, 5))
    if seed_results:
        labels = [f"seed_{int(s.get('seed', 0))}" for s in seed_results]
        vals = [float((s.get("summary") or {}).get("forge_fraction", 0.0)) for s in seed_results]
        ax2.bar(labels, vals)
        ax2.set_ylim(0, 1)
    ax2.set_ylabel("Forge Fraction")
    ax2.set_title("Daughter Forge Fraction by Seed")
    fig2.tight_layout()
    fig2.savefig(outdir / "daughter_forge_fraction.png", dpi=160)
    plt.close(fig2)

    fig3, ax3 = plt.subplots(figsize=(10, 6))
    parents = [int(d.get("parent_emergent_count_at_birth", 0)) for d in daughters]
    finals = [int(d.get("final_emergent_count", 0)) for d in daughters]
    idx = list(range(len(daughters)))
    w = 0.4
    ax3.bar([i - w / 2 for i in idx], parents, width=w, label="Parent @ Bud")
    ax3.bar([i + w / 2 for i in idx], finals, width=w, label="Daughter Final")
    ax3.set_xlabel("Daughter Basin Index")
    ax3.set_ylabel("Emergent Count")
    ax3.set_title("Parent vs Daughter Emergent Counts")
    ax3.legend()
    fig3.tight_layout()
    fig3.savefig(outdir / "parent_vs_daughter_counts.png", dpi=160)
    plt.close(fig3)


if __name__ == "__main__":
    main()
