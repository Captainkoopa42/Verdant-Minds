#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import subprocess
import sys


def run(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description="Run full Verdant scaffolding analysis pipeline.")
    ap.add_argument("--state", required=True, help="Path to persisted state JSON")
    ap.add_argument("--results-root", default="results", help="Root output directory")
    ap.add_argument("--n-nulls", type=int, default=1000, help="Null-model simulation count")
    ap.add_argument("--k", type=int, default=6, help="Top-K for backbone extraction")
    ap.add_argument(
        "--orientation",
        choices=["older_to_newer", "newer_to_older"],
        default="older_to_newer",
        help="Orientation mode override for null model calculations (metrics always include both shares).",
    )
    args = ap.parse_args()

    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    outdir = os.path.join(args.results_root, stamp)
    os.makedirs(outdir, exist_ok=True)

    py = sys.executable
    state_path = os.path.abspath(args.state)
    print(f"Using state: {state_path}")

    run([py, "analysis/extract_scaffolding_metrics.py", "--state", state_path, "--outdir", outdir, "--orientation", args.orientation])
    metrics_path = os.path.join(outdir, "metrics.json")
    with open(metrics_path) as f:
        metrics = json.load(f)
    print(
        "Extracted orientation shares: "
        f"older_to_newer_share={metrics.get('older_to_newer_share')} "
        f"newer_to_older_share={metrics.get('newer_to_older_share')}"
    )
    run([py, "analysis/compute_null_models.py", "--state", state_path, "--outdir", outdir, "--n", str(args.n_nulls), "--orientation", args.orientation])
    run([py, "analysis/fit_two_timescale_mixture.py", "--state", state_path, "--outdir", outdir])
    run([py, "analysis/export_backbone_graph.py", "--state", state_path, "--outdir", outdir, "--k", str(args.k)])
    run([
        py,
        "analysis/make_figures.py",
        "--state",
        state_path,
        "--metrics",
        os.path.join(outdir, "metrics.json"),
        "--nulls",
        os.path.join(outdir, "null_models.json"),
        "--mixture",
        os.path.join(outdir, "two_timescale_mixture.json"),
        "--outdir",
        outdir,
        "--basins",
        os.path.join(outdir, "basins.json"),
    ])

    created = sorted(os.listdir(outdir))
    print(f"\nAll outputs written to: {os.path.abspath(outdir)}")
    print("Created files:")
    for name in created:
        print(f" - {name}")


if __name__ == "__main__":
    main()
