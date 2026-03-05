"""Utilities for running Verdant-Minds in Google Colab with Drive persistence."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

REPO_URL = "https://github.com/Captainkoopa42/Verdant-Minds.git"
REPO_DIR = Path("/content/Verdant-Minds")
DRIVE_ROOT = Path("/content/drive/MyDrive/Verdant")
STATE_FILE = "verdant_persistent_state.json"
BASELINE_FILE = "verdant_v1_baseline_verified_16emergents.json"

EXTRA_DEPS = [
    "networkx",
    "python-louvain",
    "PyYAML",
    "psutil",
    "sentence-transformers",
    "scikit-learn",
    "groq",
    "mistralai",
    "matplotlib",
]


def _banner(text: str) -> None:
    print(f"\n{'=' * 80}\n{text}\n{'=' * 80}")


def _stream_command(cmd: List[str], cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None) -> None:
    print(f"$ {' '.join(shlex.quote(c) for c in cmd)}")
    process = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line.rstrip())
    rc = process.wait()
    if rc != 0:
        raise RuntimeError(f"Command failed with exit code {rc}: {' '.join(cmd)}")


def ensure_repo(repo_url: str = REPO_URL, repo_dir: Path = REPO_DIR) -> Path:
    """Clone repo if missing, otherwise pull latest changes."""
    _banner("Clone or update repo")
    repo_dir = Path(repo_dir)
    if repo_dir.exists() and (repo_dir / ".git").exists():
        print(f"Repo already exists at {repo_dir}; pulling latest changes.")
        _stream_command(["git", "pull", "--ff-only"], cwd=repo_dir)
    elif repo_dir.exists():
        raise RuntimeError(f"{repo_dir} exists but is not a git repository.")
    else:
        _stream_command(["git", "clone", repo_url, str(repo_dir)])
    return repo_dir


def install_deps(repo_dir: Path = REPO_DIR) -> None:
    """Install project and Colab helper dependencies."""
    _banner("Install dependencies")
    repo_dir = Path(repo_dir)
    req = repo_dir / "requirements.txt"
    if req.exists():
        _stream_command([sys.executable, "-m", "pip", "install", "-r", str(req)])
    _stream_command([sys.executable, "-m", "pip", "install", *EXTRA_DEPS])


def mount_drive_and_prepare(drive_root: str = str(DRIVE_ROOT)) -> Dict[str, str]:
    """Mount Google Drive (in Colab) and create persistent folders."""
    _banner("Mount Drive + configure paths")
    drive_root_path = Path(drive_root)

    if "google.colab" in sys.modules:
        from google.colab import drive  # type: ignore

        drive.mount("/content/drive", force_remount=False)
    else:
        print("Not running in Colab. Skipping drive.mount().")

    drive_root_path.mkdir(parents=True, exist_ok=True)
    outputs_root = drive_root_path / "outputs"
    outputs_root.mkdir(parents=True, exist_ok=True)

    paths = {
        "drive_root": str(drive_root_path),
        "state_path": str(drive_root_path / STATE_FILE),
        "baseline_path": str(drive_root_path / BASELINE_FILE),
        "outputs_root": str(outputs_root),
    }

    print("Configured paths:")
    for k, v in paths.items():
        print(f"  - {k}: {v}")

    baseline = Path(paths["baseline_path"])
    if not baseline.exists():
        print(f"Warning: baseline file not found at {baseline}")

    return paths


def run_cultivator_loop(
    repo_dir: str,
    state_path: str,
    n_runs: int,
    cycles: int,
    seed_topic: str,
    perturb_interval: int,
    env_overrides: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Run the LLM cultivator repeatedly with resume/fresh logic and Drive output folders."""
    repo_path = Path(repo_dir)
    state = Path(state_path)
    outputs: List[str] = []

    for run_idx in range(1, n_runs + 1):
        _banner(f"Cultivator run {run_idx}/{n_runs}")
        run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_out = Path(state_path).parent / "outputs" / run_stamp
        run_out.mkdir(parents=True, exist_ok=True)
        outputs.append(str(run_out))

        cmd = [
            sys.executable,
            str(repo_path / "scripts" / "verdant_llm_cultivator.py"),
            "--cycles",
            str(cycles),
            "--seed-topic",
            seed_topic,
            "--perturbation-interval",
            str(perturb_interval),
            "--save-state",
            str(state),
            "--output-dir",
            str(run_out),
        ]

        if state.exists():
            print(f"Resuming from existing state: {state}")
            cmd.extend(["--load-state", str(state)])
        else:
            print("No prior state found. Starting fresh with initialization.")
            cmd.extend(["--initialize-knowledge", "--fresh"])

        env = os.environ.copy()
        if env_overrides:
            env.update({k: str(v) for k, v in env_overrides.items() if v is not None})

        print(f"Run outputs will be written to: {run_out}")
        print(f"Persistent state path: {state}")
        _stream_command(cmd, cwd=repo_path, env=env)
        time.sleep(1)

    return outputs


def _iter_emergent(memory_store: Dict[str, dict]) -> Iterable[tuple[str, dict]]:
    for label, payload in memory_store.items():
        metadata = (payload or {}).get("metadata", {}) or {}
        if str(metadata.get("origin", "")).lower() == "wave_emergence":
            yield label, payload


def quick_summary(state_path: str) -> None:
    """Print simple post-run checks and summaries from state JSON."""
    _banner("Quick sanity checks + summary")
    import json

    state_file = Path(state_path)
    if not state_file.exists():
        print(f"State file not found: {state_file}")
        return

    with state_file.open("r", encoding="utf-8") as fh:
        state = json.load(fh)

    memory_store = (((state or {}).get("memory_web", {}) or {}).get("memory_store", {}) or {})
    print(f"State file: {state_file}")
    print(f"Total memory concepts: {len(memory_store)}")

    top_access = sorted(
        memory_store.items(),
        key=lambda kv: float((kv[1] or {}).get("access_count", 0) or 0),
        reverse=True,
    )[:10]

    print("\nTop access_count concepts:")
    for idx, (label, payload) in enumerate(top_access, start=1):
        print(f"{idx:2d}. {label} -> access_count={(payload or {}).get('access_count', 0)}")

    emergents = []
    for label, payload in _iter_emergent(memory_store):
        metadata = (payload or {}).get("metadata", {}) or {}
        creation = metadata.get("creation_time", float("inf"))
        emergents.append((label, creation))

    emergents.sort(key=lambda item: item[1])
    print("\nWave emergent concepts (creation_time order):")
    if not emergents:
        print("  (none found)")
    else:
        for idx, (label, creation) in enumerate(emergents, start=1):
            print(f"{idx:2d}. {label} @ {creation}")


if __name__ == "__main__":
    _banner("colab_bootstrap module")
    print("Import this module from notebooks/colab_startup_kit.ipynb")
