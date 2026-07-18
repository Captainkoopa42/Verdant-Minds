"""Integration test verifying budding actually fires under permissive thresholds."""

from __future__ import annotations

import json
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig


def test_budding_fires_and_registers_daughter_basin(tmp_path: Path) -> None:
    cfg = RunnerConfig(
        cycles=50,
        provider="local",
        outdir=str(tmp_path),
        basin_routing=True,
        enable_budding=True,
        enable_pruning=False,
        enable_boundary_emergence=False,
        basin_bud_interval=4,
        basin_pressure_threshold=0.0001,
        basin_split_fraction=0.2,
        basin_min_size_for_split=5,
        basin_min_age_for_split=2,
        density_regulation_enabled=False,
        basin_use_registry=True,
    )
    run_dir = CultivationRunner(cfg).run([0])
    rows = [
        json.loads(line)
        for line in (run_dir / "seed_0" / "cycles.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    bud_rows = [row for row in rows if int(row.get("bud_events_count", 0)) > 0]
    assert bud_rows, "expected at least one bud event in a permissive 50-cycle run"

    daughter_ids = {
        str(row.get("bud_new_basin_id"))
        for row in bud_rows
        if row.get("bud_new_basin_id") is not None
    }
    assert daughter_ids

    budded_events = []
    for row in rows:
        for event in row.get("basin_registry_events") or []:
            if event.get("event_type") == "budded":
                budded_events.append(event)
    assert budded_events, "expected at least one basin_registry budded lifecycle event"
    event_basin_ids = {str(event.get("basin_id")) for event in budded_events}
    assert any(daughter_id in event_basin_ids for daughter_id in daughter_ids)
