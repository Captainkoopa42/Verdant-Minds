"""Run basin detection robustness across multiple seeds and aggregate results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

try:
    from analysis.basin_detection_robustness import compute_robustness
except ImportError:
    from basin_detection_robustness import compute_robustness


def _resolve_run_dir(spec: str) -> Path:
    p = Path(spec)
    if "*" not in spec:
        return p
    matches = sorted(Path().glob(spec))
    if not matches:
        raise FileNotFoundError(f"No run directory matches: {spec}")
    return matches[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run robustness checks for multiple seeds")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--n-runs", type=int, default=10)
    parser.add_argument("--algorithm", choices=["louvain", "greedy"], default="louvain")
    parser.add_argument("--k", type=int, default=6)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    run_dir = _resolve_run_dir(args.run_dir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    per_seed: list[dict[str, Any]] = []
    for seed in range(args.seeds):
        state_path = run_dir / f"seed_{seed}" / "state.json"
        if not state_path.exists():
            continue
        seed_outdir = outdir / f"seed_{seed}"
        seed_outdir.mkdir(parents=True, exist_ok=True)
        result = compute_robustness(state_path, n_runs=args.n_runs, algorithm=args.algorithm, k=args.k)
        (seed_outdir / "basin_robustness.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        per_seed.append(
            {
                "seed": seed,
                "state_path": str(state_path),
                "ari_mean": float(result.get("pairwise_ari", {}).get("mean", 0.0)),
                "nmi_mean": float(result.get("pairwise_nmi", {}).get("mean", 0.0)),
                "node_stability_mean": float(result.get("node_stability", {}).get("mean", 0.0)),
                "emergent_stability_mean": float(
                    result.get("node_stability", {}).get("emergent_node_stability_mean", 0.0)
                ),
                "interpretation": result.get("interpretation", "unstable"),
            }
        )

    overall_ari_mean = float(mean([p["ari_mean"] for p in per_seed])) if per_seed else 0.0
    overall_nmi_mean = float(mean([p["nmi_mean"] for p in per_seed])) if per_seed else 0.0
    overall_node_stability_mean = float(mean([p["node_stability_mean"] for p in per_seed])) if per_seed else 0.0
    overall_emergent_stability_mean = float(mean([p["emergent_stability_mean"] for p in per_seed])) if per_seed else 0.0

    if overall_ari_mean > 0.8:
        interpretation = "stable"
    elif overall_ari_mean >= 0.5:
        interpretation = "moderate"
    else:
        interpretation = "unstable"

    aggregate = {
        "seeds_analyzed": len(per_seed),
        "overall_ari_mean": overall_ari_mean,
        "overall_nmi_mean": overall_nmi_mean,
        "overall_node_stability_mean": overall_node_stability_mean,
        "overall_emergent_stability_mean": overall_emergent_stability_mean,
        "interpretation": interpretation,
        "per_seed": per_seed,
    }
    out = outdir / "aggregate_robustness.json"
    out.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    print(json.dumps(aggregate, indent=2))


if __name__ == "__main__":
    main()
