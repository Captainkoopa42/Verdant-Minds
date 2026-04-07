from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig
from verdant.system import VerdantConfig, VerdantSystem


def test_coherence_metrics_accessible() -> None:
    system = VerdantSystem(VerdantConfig(seed=17, initialize_knowledge=True))

    for idx in range(5):
        system.process_input(f"Reflect on coherence and emergence at cycle {idx}.")

    metrics = system.get_coherence_metrics()
    assert set(metrics) == {
        "h1_triangle_valid",
        "housed_contradiction_index",
        "violation_rate",
        "alpha_critical_estimate",
    }
    assert isinstance(metrics["h1_triangle_valid"], bool)
    assert isinstance(metrics["housed_contradiction_index"], float)
    assert isinstance(metrics["violation_rate"], float)
    assert metrics["alpha_critical_estimate"] is None or isinstance(metrics["alpha_critical_estimate"], float)


def test_coherence_in_telemetry(tmp_path: Path) -> None:
    run_dir = CultivationRunner(RunnerConfig(cycles=10, provider="local", outdir=str(tmp_path))).run([0])
    rows = [
        json.loads(line)
        for line in (run_dir / "seed_0" / "cycles.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert rows
    assert "h1_triangle_valid" in rows[0]
    assert "housed_contradiction_index" in rows[0]
    assert "violation_rate" in rows[0]
    assert "alpha_critical_estimate" in rows[0]


def test_h1_analysis_script(tmp_path: Path) -> None:
    run_dir = CultivationRunner(RunnerConfig(cycles=20, provider="local", outdir=str(tmp_path / "outputs"))).run([0])
    outdir = tmp_path / "analysis"
    subprocess.run(
        [
            sys.executable,
            "analysis/h1_coherence_analysis.py",
            "--run-dir",
            str(run_dir),
            "--seeds",
            "1",
            "--outdir",
            str(outdir),
        ],
        check=True,
    )

    result_path = outdir / "h1_coherence_analysis.json"
    assert result_path.exists()
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert isinstance(payload["h1_valid_fraction"], float)
    assert 0.0 <= payload["h1_valid_fraction"] <= 1.0
