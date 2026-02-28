import json
import subprocess
import sys
from pathlib import Path


def test_kernel_loop_demo_writes_trajectory_and_summary(tmp_path):
    repo_root = Path.cwd()
    script = repo_root / "scripts" / "kernel_loop.py"

    proc = subprocess.run(
        [sys.executable, str(script), "--demo"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "TRAJECTORY REPORT" in proc.stdout

    trajectory_path = tmp_path / "outputs" / "demo_trajectory.json"
    summary_path = tmp_path / "outputs" / "demo_summary.txt"

    assert trajectory_path.exists()
    assert summary_path.exists()

    payload = json.loads(trajectory_path.read_text(encoding="utf-8"))
    assert payload.get("mode") == "demo"
    assert len(payload.get("steps", [])) == 5

    report = payload.get("trajectory_report", {})
    assert len(report.get("tg_evolution", [])) == 5
    assert len(report.get("interference_evolution", [])) == 5
    assert len(report.get("housed_contradiction_evolution", [])) == 5
    assert len(report.get("memory_node_growth", [])) == 5

    summary_text = summary_path.read_text(encoding="utf-8")
    assert "Verdant demo summary" in summary_text
    assert "Interference signatures moved through" in summary_text
