"""Integration test for basin micro-pipeline proposals and arbitration."""

from __future__ import annotations

import json
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig


def _read_last_cycle(cycles_path: Path) -> dict:
    lines = cycles_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    return json.loads(lines[-1])


def test_basin_micro_pipeline_proposals_and_determinism(tmp_path: Path) -> None:
    config = RunnerConfig(
        cycles=15,
        provider="local",
        outdir=str(tmp_path / "out"),
        pressure_every=4,
        basin_routing=True,
    )

    run1 = CultivationRunner(config).run([0])
    seed_dir1 = run1 / "seed_0"
    assert (seed_dir1 / "cycles.jsonl").exists()

    last1 = _read_last_cycle(seed_dir1 / "cycles.jsonl")
    assert last1.get("basin_proposals_count", 0) >= 1
    assert "final_action_source" in last1
    assert "basin_conflict_detected" in last1

    run2 = CultivationRunner(config).run([0])
    last2 = _read_last_cycle(run2 / "seed_0" / "cycles.jsonl")

    assert last1.get("final_action_source") == last2.get("final_action_source")
    assert bool(last1.get("basin_conflict_detected")) == bool(last2.get("basin_conflict_detected"))
