import csv
import json
import subprocess
import sys


def test_v2_older_to_newer_scaffolding_orientation_reporting(tmp_path):
    state = {
        "memory_web": {
            "memory_store": {
                "Emergent_A": {"metadata": {"creation_time": 0}},
                "Emergent_B": {"metadata": {"creation_time": 10}},
                "Emergent_C": {"metadata": {"creation_time": 20}},
            },
            "edges": [
                ["Emergent_A", "Emergent_B", 1.0],
                ["Emergent_B", "Emergent_C", 1.0],
            ],
        }
    }

    state_path = tmp_path / "state.json"
    outdir = tmp_path / "out"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "analysis/extract_scaffolding_metrics.py",
            "--state",
            str(state_path),
            "--outdir",
            str(outdir),
        ],
        check=True,
    )

    metrics = json.loads((outdir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["older_to_newer_share"] == 1.0
    assert metrics["newer_to_older_share"] == 0.0
    assert metrics["scaffolding_share"] == 1.0
    assert metrics["earlier_share"] == 1.0

    with open(outdir / "emergent_edges.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert all(row["is_older_to_newer"] == "True" for row in rows)
    assert all(row["is_newer_to_older"] == "False" for row in rows)


def test_null_models_reports_explicit_observed_orientation_shares(tmp_path):
    state = {
        "memory_web": {
            "memory_store": {
                "Emergent_A": {"metadata": {"creation_time": 0}},
                "Emergent_B": {"metadata": {"creation_time": 10}},
                "Emergent_C": {"metadata": {"creation_time": 20}},
            },
            "edges": [
                ["Emergent_A", "Emergent_B", 1.0],
                ["Emergent_B", "Emergent_C", 1.0],
            ],
        }
    }

    state_path = tmp_path / "state.json"
    outdir = tmp_path / "out"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "analysis/compute_null_models.py",
            "--state",
            str(state_path),
            "--outdir",
            str(outdir),
            "--n",
            "8",
        ],
        check=True,
    )

    nulls = json.loads((outdir / "null_models.json").read_text(encoding="utf-8"))
    assert nulls["observed_older_to_newer_share"] == 1.0
    assert nulls["observed_newer_to_older_share"] == 0.0
    assert nulls["scaffolding_share"] == 1.0
    assert nulls["observed"] == 1.0
