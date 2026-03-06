"""Smoke test for Colab-style replication and analysis commands."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig


def test_colab_replication_and_analysis_smoke(tmp_path: Path) -> None:
    out_root = tmp_path / "outputs"
    config = RunnerConfig(
        cycles=5,
        provider="local",
        outdir=str(out_root),
        pressure_every=2,
        basin_routing=True,
    )

    run_dir = CultivationRunner(config).run([0, 1])

    for seed in (0, 1):
        seed_dir = run_dir / f"seed_{seed}"
        assert (seed_dir / "state.json").exists()
        assert (seed_dir / "cycles.jsonl").exists()
        assert (seed_dir / "summary.json").exists()

    state_path = run_dir / "seed_0" / "state.json"
    results_root = tmp_path / "results"

    subprocess.run(
        [
            sys.executable,
            "analysis/run_all.py",
            "--state",
            str(state_path),
            "--results-root",
            str(results_root),
            "--n-nulls",
            "10",
            "--k",
            "6",
        ],
        check=True,
    )

    result_dirs = sorted([p for p in results_root.iterdir() if p.is_dir()])
    assert result_dirs, "No analysis output directory created"
    latest = result_dirs[-1]

    assert (latest / "metrics.json").exists()
    figure_candidates = list(latest.glob("*.png")) + list(latest.glob("*.pdf"))
    assert figure_candidates, "Expected at least one analysis figure artifact"
