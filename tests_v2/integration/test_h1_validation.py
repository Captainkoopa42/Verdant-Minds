from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig


def test_h1_in_full_validation(tmp_path: Path) -> None:
    run_dir = CultivationRunner(
        RunnerConfig(
            cycles=20,
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
    assert "task8_h1_coherence" in report
    assert report["task8_h1_coherence"]["status"] in {"PASS", "PARTIAL", "FAIL"}
