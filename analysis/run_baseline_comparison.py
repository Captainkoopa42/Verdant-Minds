#!/usr/bin/env python3
"""Run multi-seed baseline generation and scaffolding comparison analysis."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=80)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--outdir", type=Path, default=Path("outputs_baseline_comparison"))
    return parser.parse_args()


def _mean(values: list[float]) -> float:
    return float(statistics.mean(values)) if values else 0.0


def _std(values: list[float]) -> float:
    return float(statistics.pstdev(values)) if len(values) > 1 else 0.0


def main() -> None:
    args = parse_args()
    outdir: Path = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    earlier_values: list[float] = []
    z_values: list[float] = []
    emergent_counts: list[float] = []

    for seed in range(args.seeds):
        seed_dir = outdir / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)

        _run([
            sys.executable,
            "analysis/baseline_random_graph.py",
            "--cycles", str(args.cycles),
            "--seed", str(seed),
            "--outdir", str(seed_dir),
        ])
        state_path = seed_dir / "state.json"

        _run([
            sys.executable,
            "analysis/extract_scaffolding_metrics.py",
            "--state", str(state_path),
            "--outdir", str(seed_dir),
            "--orientation", "older_to_newer",
        ])

        _run([
            sys.executable,
            "analysis/compute_null_models.py",
            "--state", str(state_path),
            "--outdir", str(seed_dir),
            "--n", "200",
            "--orientation", "older_to_newer",
        ])

        metrics = _read_json(seed_dir / "metrics.json")
        null_models = _read_json(seed_dir / "null_models.json")

        earlier = metrics.get("earlier_share")
        if earlier is not None:
            earlier_values.append(float(earlier))
        emergent_counts.append(float(metrics.get("emergent_nodes", 0)))

        z_score = (null_models.get("shuffle_null") or {}).get("z")
        if z_score is not None:
            z_values.append(float(z_score))

    summary = {
        "baseline": {
            "earlier_share_mean": _mean(earlier_values),
            "earlier_share_std": _std(earlier_values),
            "earlier_share_values": earlier_values,
            "shuffle_z_mean": _mean(z_values),
            "shuffle_z_std": _std(z_values),
            "shuffle_z_values": z_values,
            "emergent_count_mean": _mean(emergent_counts),
            "emergent_count_std": _std(emergent_counts),
        },
        "note": "Compare against Verdant results: earlier_share=1.000, z=12.73",
    }

    summary_path = outdir / "comparison_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(summary_path)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
