"""Run daughter basin analysis across all seeds in a run directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daughter_basin_analysis import analyze_cycles


def _resolve_run_dir(spec: str) -> Path:
    p = Path(spec)
    if "*" not in spec:
        return p
    matches = sorted(Path().glob(spec))
    if not matches:
        raise FileNotFoundError(f"No run directory matches: {spec}")
    return matches[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate daughter basin analyses across seeds")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    run_dir = _resolve_run_dir(args.run_dir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    per_seed: list[dict[str, Any]] = []
    all_daughters: list[dict[str, Any]] = []

    for seed in range(args.seeds):
        cycles_path = run_dir / f"seed_{seed}" / "cycles.jsonl"
        if not cycles_path.exists():
            continue
        result = analyze_cycles(cycles_path)
        (outdir / f"daughter_analysis_seed_{seed}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        per_seed.append(
            {
                "seed": seed,
                **result["summary"],
                "total_bud_events": int(result.get("total_bud_events", 0)),
            }
        )
        all_daughters.extend(result.get("daughters", []))

    became_forge_final = sum(1 for d in all_daughters if bool(d.get("became_forge_final", False)))
    became_forge_peak = sum(1 for d in all_daughters if bool(d.get("became_forge_peak", False)))
    final_counts = [int(d.get("final_emergent_count", 0)) for d in all_daughters]
    peak_counts = [int(d.get("max_emergent_count", 0)) for d in all_daughters]
    max_any = max((int(d.get("max_emergent_count", 0)) for d in all_daughters), default=0)

    aggregate = {
        "seeds_analyzed": len(per_seed),
        "total_daughters_all_seeds": len(all_daughters),
        "total_became_forge_final_all_seeds": became_forge_final,
        "total_became_forge_peak_all_seeds": became_forge_peak,
        "overall_forge_fraction_final": float(became_forge_final / len(all_daughters)) if all_daughters else 0.0,
        "overall_forge_fraction_peak": float(became_forge_peak / len(all_daughters)) if all_daughters else 0.0,
        "mean_final_emergent_across_daughters": float(mean(final_counts)) if final_counts else 0.0,
        "mean_peak_emergent_across_daughters": float(mean(peak_counts)) if peak_counts else 0.0,
        "max_emergent_any_daughter_any_seed": max_any,
        "per_seed_summaries": per_seed,
    }
    (outdir / "aggregate_daughter_analysis.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
