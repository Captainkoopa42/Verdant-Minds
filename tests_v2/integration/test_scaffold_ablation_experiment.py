"""Integration test for scaffold-ablation experiment flow."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig


def test_scaffold_ablation_flow_and_comparison(tmp_path: Path) -> None:
    base = CultivationRunner(
        RunnerConfig(cycles=8, provider="local", outdir=str(tmp_path / "baseline"), basin_routing=True)
    ).run([0])

    ablation = CultivationRunner(
        RunnerConfig(
            cycles=8,
            provider="local",
            outdir=str(tmp_path / "ablation"),
            basin_routing=True,
            intervention_mode="ablate_oldest_nodes",
            intervention_cycle=4,
            ablation_fraction=0.2,
            intervention_target="global",
        )
    ).run([0])

    scramble = CultivationRunner(
        RunnerConfig(
            cycles=8,
            provider="local",
            outdir=str(tmp_path / "scramble"),
            basin_routing=True,
            intervention_mode="scramble_ee_edges",
            intervention_cycle=4,
            intervention_target="global",
            intervention_seed=33,
        )
    ).run([0])

    for run_dir in (base, ablation, scramble):
        seed_dir = run_dir / "seed_0"
        assert (seed_dir / "state.json").exists()
        assert (seed_dir / "cycles.jsonl").exists()
        assert (seed_dir / "summary.json").exists()

    ab_lines = (ablation / "seed_0" / "cycles.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ab_cycle4 = json.loads(ab_lines[4])
    assert ab_cycle4["intervention_applied"] is True
    assert ab_cycle4["intervention_mode"] == "ablate_oldest_nodes"

    outdir = tmp_path / "cmp"
    subprocess.run(
        [
            sys.executable,
            "analysis/compare_intervention_runs.py",
            "--baseline",
            str(base),
            "--ablation",
            str(ablation),
            "--scramble",
            str(scramble),
            "--outdir",
            str(outdir),
        ],
        check=True,
    )

    assert (outdir / "comparison_summary.json").exists()
    assert (outdir / "fig_post_intervention_emergents.png").exists()
    assert (outdir / "fig_post_intervention_basin_counts.png").exists()
    assert (outdir / "fig_post_intervention_scaffolding.png").exists()
