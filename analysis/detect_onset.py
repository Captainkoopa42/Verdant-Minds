#!/usr/bin/env python3
"""Detect developmental onset from cultivation cycle telemetry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def detect_onset(cycles_jsonl_path: str) -> dict:
    """Detect developmental onset from telemetry.

    Onset is first cycle where ``basin_count > 0``.
    """
    path = Path(cycles_jsonl_path)
    onset = None
    total_cycles = 0

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            total_cycles += 1
            rec = json.loads(line)
            basin_count = int(rec.get("basin_count", 0) or 0)
            if onset is None and basin_count > 0:
                onset = rec

    if onset is None:
        return {
            "onset_cycle": None,
            "onset_t_g": None,
            "onset_memory_size": None,
            "onset_emergent_count": None,
            "onset_entropy": None,
            "onset_hci": None,
            "pre_onset_cycles": total_cycles,
            "total_cycles": total_cycles,
        }

    cycle = onset.get("cycle_index", onset.get("cycle"))
    return {
        "onset_cycle": int(cycle) if cycle is not None else None,
        "onset_t_g": float(onset.get("t_g")) if onset.get("t_g") is not None else None,
        "onset_memory_size": int(onset.get("memory_size")) if onset.get("memory_size") is not None else None,
        "onset_emergent_count": int(onset.get("emergent_count")) if onset.get("emergent_count") is not None else None,
        "onset_entropy": float(onset.get("entropy")) if onset.get("entropy") is not None else None,
        "onset_hci": float(onset.get("hci")) if onset.get("hci") is not None else None,
        "pre_onset_cycles": int(cycle) if cycle is not None else 0,
        "total_cycles": total_cycles,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect developmental onset from cycles.jsonl")
    parser.add_argument("--cycles-jsonl", required=True)
    parser.add_argument("--outfile", required=True)
    args = parser.parse_args()

    result = detect_onset(args.cycles_jsonl)
    outpath = Path(args.outfile)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
