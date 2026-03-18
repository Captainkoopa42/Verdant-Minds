from __future__ import annotations

import json
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig
from analysis.daughter_basin_analysis import analyze_cycles


def test_emergent_count_by_basin_in_telemetry(tmp_path: Path) -> None:
    runner = CultivationRunner(
        RunnerConfig(
            cycles=15,
            provider="local",
            outdir=str(tmp_path),
            basin_routing=True,
            enable_pruning=True,
            enable_budding=True,
            enable_boundary_emergence=True,
        )
    )
    run_dir = runner.run([0])
    cycles_path = run_dir / "seed_0" / "cycles.jsonl"
    rows = [json.loads(line) for line in cycles_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    for row in rows:
        assert "emergent_count_by_basin" in row
        assert isinstance(row["emergent_count_by_basin"], dict)
        assert all(isinstance(k, str) for k in row["emergent_count_by_basin"].keys())
        assert all(isinstance(v, int) for v in row["emergent_count_by_basin"].values())


def test_daughter_analysis_mock(tmp_path: Path) -> None:
    cycles_path = tmp_path / "cycles.jsonl"
    rows = []
    for cycle in range(31):
        rec = {
            "cycle_index": cycle,
            "seed": 7,
            "bud_events_count": 0,
            "bud_parent_basin_id": None,
            "bud_new_basin_id": None,
            "emergent_count_by_basin": {"basin_0": 20},
        }
        if cycle >= 10:
            daughter_count = min(15, cycle - 10)
            rec["emergent_count_by_basin"]["basin_3"] = daughter_count
        if cycle == 10:
            rec["bud_events_count"] = 1
            rec["bud_parent_basin_id"] = "basin_0"
            rec["bud_new_basin_id"] = "basin_3"
        rows.append(rec)
    cycles_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    out = analyze_cycles(cycles_path)
    assert out["summary"]["total_daughters"] == 1
    daughter = out["daughters"][0]
    assert daughter["daughter_id"] == "basin_3"
    assert daughter["became_forge_peak"] is True
    assert daughter["became_forge_final"] is True
    assert len(daughter["growth_trajectory"]) == 21
