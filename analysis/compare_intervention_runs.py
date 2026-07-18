#!/usr/bin/env python3
"""Compare baseline, ablation, and scramble intervention runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

try:
    from analysis.state_adapter import VerdantState
except ImportError:
    from state_adapter import VerdantState


def _load_seed_dirs(run_dir: Path) -> list[Path]:
    return sorted([p for p in run_dir.iterdir() if p.is_dir() and p.name.startswith("seed_")])


def _higher_order_count_from_state(state_path: Path) -> int:
    vs = VerdantState.load(state_path)
    count = 0
    for node in vs.emergent_nodes:
        name = str(node["name"])
        nested = name.count("Emergent_") >= 2
        separators = sum(name.count(sep) for sep in ("__", ":", "|", "->", "/", "+"))
        if nested or separators >= 2:
            count += 1
    return count


def _metrics_from_seed(seed_dir: Path) -> dict:
    summary = json.loads((seed_dir / "summary.json").read_text(encoding="utf-8"))
    state_path = seed_dir / "state.json"
    vs = VerdantState.load(state_path)

    comparable = 0
    older_to_newer = 0
    for edge in vs.emergent_edges:
        left = vs.get_node(edge["source"])
        right = vs.get_node(edge["target"])
        if left is None or right is None:
            continue
        tu = left.get("creation_time")
        tv = right.get("creation_time")
        if tu is None or tv is None or tu == tv:
            continue
        comparable += 1
        if vs.format_version == "v3":
            older_to_newer += 1
        else:
            older_to_newer += 1 if tu < tv else 0

    scaffolding_share = (older_to_newer / comparable) if comparable else 0.0

    return {
        "emergent_nodes": float(summary.get("emergent_count", 0)),
        "post_intervention_new_emergents": float(summary.get("post_intervention_new_emergents", 0)),
        "basin_count": float(summary.get("post_intervention_basin_count", summary.get("pre_intervention_basin_count", 0))),
        "scaffolding_share": float(scaffolding_share),
        "comparable_emergent_edges": float(comparable),
        "higher_order_emergent_count": float(_higher_order_count_from_state(state_path)),
    }


def _aggregate(run_dir: Path) -> dict:
    rows = [_metrics_from_seed(seed_dir) for seed_dir in _load_seed_dirs(run_dir)]
    if not rows:
        return {k: 0.0 for k in (
            "mean_emergent_nodes",
            "mean_post_intervention_new_emergents",
            "mean_basin_count",
            "mean_scaffolding_share",
            "mean_comparable_emergent_edges",
            "mean_higher_order_emergent_count",
        )}

    def m(key: str) -> float:
        return sum(r[key] for r in rows) / len(rows)

    return {
        "mean_emergent_nodes": m("emergent_nodes"),
        "mean_post_intervention_new_emergents": m("post_intervention_new_emergents"),
        "mean_basin_count": m("basin_count"),
        "mean_scaffolding_share": m("scaffolding_share"),
        "mean_comparable_emergent_edges": m("comparable_emergent_edges"),
        "mean_higher_order_emergent_count": m("higher_order_emergent_count"),
    }


def _delta(base: dict, other: dict) -> dict:
    return {k: float(other.get(k, 0.0) - base.get(k, 0.0)) for k in base.keys()}


def _bar(path: Path, title: str, baseline: float, ablation: float, scramble: float) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.bar(["baseline", "ablation", "scramble"], [baseline, ablation, scramble], color=["#457B9D", "#E63946", "#2A9D8F"])
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--ablation", required=True)
    ap.add_argument("--scramble", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    base = _aggregate(Path(args.baseline))
    abl = _aggregate(Path(args.ablation))
    scr = _aggregate(Path(args.scramble))

    summary = {
        "baseline": base,
        "ablation": abl,
        "scramble": scr,
        "delta_baseline_to_ablation": _delta(base, abl),
        "delta_baseline_to_scramble": _delta(base, scr),
    }
    (outdir / "comparison_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    _bar(
        outdir / "fig_post_intervention_emergents.png",
        "Post-intervention emergent nodes",
        base["mean_emergent_nodes"],
        abl["mean_emergent_nodes"],
        scr["mean_emergent_nodes"],
    )
    _bar(
        outdir / "fig_post_intervention_basin_counts.png",
        "Post-intervention basin count",
        base["mean_basin_count"],
        abl["mean_basin_count"],
        scr["mean_basin_count"],
    )
    _bar(
        outdir / "fig_post_intervention_scaffolding.png",
        "Scaffolding share",
        base["mean_scaffolding_share"],
        abl["mean_scaffolding_share"],
        scr["mean_scaffolding_share"],
    )


if __name__ == "__main__":
    main()
