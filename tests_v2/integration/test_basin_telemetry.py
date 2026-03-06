"""Integration tests for basin telemetry in system + cultivation outputs."""

from __future__ import annotations

import json
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig
from verdant_v2.system import VerdantConfig, VerdantSystem


def test_system_emits_basins_section() -> None:
    system = VerdantSystem(VerdantConfig(seed=7, basin_scan_interval=10))
    saw_scan = False
    for i in range(12):
        chunk = system.process_input(f"Cycle {i}: memory, ethics, emergence, time.")
        basins_section = chunk.get_section_content("basins_section")
        assert basins_section is not None
        assert "basins" in basins_section
        if basins_section.get("scanned_this_cycle"):
            saw_scan = True
    assert saw_scan


def test_cultivation_cycles_include_basin_telemetry(tmp_path: Path) -> None:
    config = RunnerConfig(cycles=12, provider="local", outdir=str(tmp_path / "out"), pressure_every=4)
    run_dir = CultivationRunner(config).run([0])
    cycles_path = run_dir / "seed_0" / "cycles.jsonl"
    lines = cycles_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 12

    sample = json.loads(lines[-1])
    assert "basin_count" in sample
    assert "largest_basin_size" in sample
    assert "self_cluster_basin_id" in sample
    assert "emergent_basins" in sample
    assert "basin_proposals_count" in sample
    assert "basin_conflict_detected" in sample
    assert "final_action_source" in sample
    assert "top_proposal_scores" in sample
