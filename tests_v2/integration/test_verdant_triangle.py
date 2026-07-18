from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig


def test_triangle_in_validation(tmp_path: Path) -> None:
    run_dir = CultivationRunner(
        RunnerConfig(
            cycles=30,
            provider="local",
            outdir=str(tmp_path / "outputs"),
            basin_routing=True,
            enable_pruning=True,
            enable_budding=True,
            enable_boundary_emergence=True,
        )
    ).run([0])

    validation_dir = tmp_path / "validation"
    subprocess.run(
        [
            sys.executable,
            "analysis/run_full_validation.py",
            "--run-dir",
            str(run_dir),
            "--seeds",
            "1",
            "--outdir",
            str(validation_dir),
            "--skip-slow",
        ],
        check=True,
    )

    report = json.loads((validation_dir / "validation_report.json").read_text(encoding="utf-8"))
    assert "task9_verdant_triangle" in report
    assert report["task9_verdant_triangle"]["status"] == "REPORTED"
    assert report["task9_verdant_triangle"]["note"] == (
        "Open conjecture - tested empirically, does not hold with current tau* definition"
    )
    assert "within_basin" in report["task9_verdant_triangle"]
    assert "cross_basin" in report["task9_verdant_triangle"]
