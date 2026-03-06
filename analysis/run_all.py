#!/usr/bin/env python3
import argparse
import datetime as dt
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
    args = ap.parse_args()

    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    outdir = os.path.join(args.results_root, stamp)
    os.makedirs(outdir, exist_ok=True)

    py = sys.executable
    run([py, "analysis/extract_scaffolding_metrics.py", "--state", args.state, "--outdir", outdir])
    run([py, "analysis/compute_null_models.py", "--state", args.state, "--outdir", outdir, "--n", str(args.n_nulls)])
    run([py, "analysis/fit_two_timescale_mixture.py", "--state", args.state, "--outdir", outdir])
    run([py, "analysis/export_backbone_graph.py", "--state", args.state, "--outdir", outdir, "--k", str(args.k)])
    run([
        py,
        "analysis/make_figures.py",
        "--state",
        args.state,
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

    print(f"\nAll outputs written to: {outdir}")


if __name__ == "__main__":
    main()
