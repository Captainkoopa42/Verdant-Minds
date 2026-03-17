"""Analyze daughter basin emergent growth trajectories from per-cycle telemetry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any


def _load_cycles(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def analyze_cycles(cycles_jsonl: Path) -> dict[str, Any]:
    rows = _load_cycles(cycles_jsonl)
    if not rows:
        return {
            "seed": None,
            "total_bud_events": 0,
            "daughters": [],
            "summary": {
                "total_daughters": 0,
                "daughters_became_forge": 0,
                "forge_fraction": 0.0,
                "mean_final_emergent_count": 0.0,
                "mean_time_to_ignition": None,
                "max_emergent_any_daughter": 0,
            },
        }

    seed = rows[0].get("seed")
    daughters: list[dict[str, Any]] = []
    total_bud_events = 0

    for row in rows:
        buds = int(row.get("bud_events_count", 0) or 0)
        daughter_id = row.get("bud_new_basin_id")
        if buds <= 0 or not isinstance(daughter_id, str):
            continue
        total_bud_events += buds
        birth_cycle = int(row.get("cycle_index", 0))
        parent_id = row.get("bud_parent_basin_id")
        parent_counts = row.get("emergent_count_by_basin", {})
        if not isinstance(parent_counts, dict):
            parent_counts = {}
        parent_count_at_birth = int(parent_counts.get(parent_id, 0)) if isinstance(parent_id, str) else 0

        post_rows = [r for r in rows if int(r.get("cycle_index", 0)) >= birth_cycle]
        trajectory: list[int] = []
        parent_post: list[int] = []
        for prow in post_rows:
            per_basin = prow.get("emergent_count_by_basin", {})
            if not isinstance(per_basin, dict):
                per_basin = {}
            trajectory.append(int(per_basin.get(daughter_id, 0) or 0))
            if isinstance(parent_id, str):
                parent_post.append(int(per_basin.get(parent_id, 0) or 0))

        if not trajectory:
            continue
        initial = trajectory[0]
        final = trajectory[-1]
        max_count = max(trajectory)
        final_cycle = int(rows[-1].get("cycle_index", 0))
        denom = max(1, final_cycle - birth_cycle)
        growth_rate = float((final - initial) / denom)
        ignition_index = next((i for i, val in enumerate(trajectory) if val > 5), None)
        ignition_cycle = (birth_cycle + ignition_index) if ignition_index is not None else None
        time_to_ignition = (ignition_cycle - birth_cycle) if ignition_cycle is not None else None
        parent_decreased_after_bud = bool(parent_post and min(parent_post) < parent_count_at_birth)

        daughters.append(
            {
                "daughter_id": daughter_id,
                "parent_id": parent_id,
                "birth_cycle": birth_cycle,
                "final_cycle": final_cycle,
                "lifetime_cycles": final_cycle - birth_cycle,
                "initial_emergent_count": initial,
                "final_emergent_count": final,
                "max_emergent_count": max_count,
                "growth_rate": growth_rate,
                "became_forge": final >= 10,
                "ignition_cycle": ignition_cycle,
                "time_to_ignition": time_to_ignition,
                "growth_trajectory": trajectory,
                "parent_emergent_count_at_birth": parent_count_at_birth,
                "parent_decreased_after_bud": parent_decreased_after_bud,
            }
        )

    forge_count = sum(1 for d in daughters if d["became_forge"])
    ignition_times = [int(d["time_to_ignition"]) for d in daughters if d["time_to_ignition"] is not None]
    finals = [int(d["final_emergent_count"]) for d in daughters]
    max_any = max((int(d["max_emergent_count"]) for d in daughters), default=0)

    return {
        "seed": seed,
        "total_bud_events": total_bud_events,
        "daughters": daughters,
        "summary": {
            "total_daughters": len(daughters),
            "daughters_became_forge": forge_count,
            "forge_fraction": float(forge_count / len(daughters)) if daughters else 0.0,
            "mean_final_emergent_count": float(mean(finals)) if finals else 0.0,
            "mean_time_to_ignition": float(mean(ignition_times)) if ignition_times else None,
            "max_emergent_any_daughter": max_any,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze daughter basin growth from cycles.jsonl")
    parser.add_argument("--cycles-jsonl", required=True)
    parser.add_argument("--outfile", required=True)
    args = parser.parse_args()

    result = analyze_cycles(Path(args.cycles_jsonl))
    out = Path(args.outfile)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
