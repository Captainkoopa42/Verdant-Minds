#!/usr/bin/env python3
import argparse, csv, os
from collections import defaultdict
from extract_scaffolding_metrics import load_graph


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--k", type=int, default=6)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    _, edges = load_graph(args.state)
    by_src = defaultdict(list)
    for e in edges:
        by_src[e["source"]].append(e)
    bb = []
    for src, arr in by_src.items():
        bb.extend(sorted(arr, key=lambda x: x["weight"], reverse=True)[: args.k])

    out = os.path.join(args.outdir, "backbone_edges.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["source", "target", "weight"])
        w.writeheader()
        w.writerows(bb)
    print(f"wrote {len(bb)} edges to {out}")


if __name__ == "__main__":
    main()
