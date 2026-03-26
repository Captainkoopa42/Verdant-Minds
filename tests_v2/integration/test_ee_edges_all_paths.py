from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SPEC_DIR = Path(__file__).resolve().parents[2] / "cultivation" / "specs"


def _count_ee_edges(state_path: Path) -> int:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    edges = state.get("memory_web", {}).get("edges", [])
    return sum(
        1
        for edge in edges
        if isinstance(edge, dict)
        and str(edge.get("source", "")).startswith("Emergent_")
        and str(edge.get("target", "")).startswith("Emergent_")
    )


def _latest_run_dir(out_root: Path) -> Path:
    runs = sorted(out_root.glob("run_*"))
    assert runs, f"No run_* directories under {out_root}"
    return runs[-1]


def _run_cultivation(tmp_path: Path, *, enable_all_dynamics: bool) -> int:
    out_root = tmp_path / ("run_all" if enable_all_dynamics else "run_default")
    cmd = [
        sys.executable,
        "-m",
        "cultivation.cli",
        "run",
        "--cycles",
        "20",
        "--seeds",
        "0",
        "--provider",
        "local",
        "--density-regulation",
        "--outdir",
        str(out_root),
    ]
    if enable_all_dynamics:
        cmd.extend(["--enable-all-dynamics"])
    subprocess.run(cmd, check=True)
    state_path = _latest_run_dir(out_root) / "seed_0" / "state.json"
    assert state_path.exists()
    return _count_ee_edges(state_path)


def test_run_command_has_ee_edges_with_enable_all_dynamics(tmp_path: Path) -> None:
    ee_edges = _run_cultivation(tmp_path, enable_all_dynamics=True)
    assert ee_edges > 0


def test_run_command_has_ee_edges_without_enable_all_dynamics(tmp_path: Path) -> None:
    ee_edges = _run_cultivation(tmp_path, enable_all_dynamics=False)
    assert ee_edges > 0


def test_cultivate_command_has_ee_edges(tmp_path: Path) -> None:
    out_root = tmp_path / "cultivate"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "cultivation.cli",
            "cultivate",
            "--spec",
            str(SPEC_DIR / "quick_test.vcult"),
            "--provider",
            "local",
            "--seeds",
            "0-0",
            "--outdir",
            str(out_root),
        ],
        check=True,
    )
    state_path = _latest_run_dir(out_root) / "seed_0" / "state.json"
    assert state_path.exists()
    assert _count_ee_edges(state_path) > 0
