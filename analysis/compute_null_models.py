#!/usr/bin/env python3
import argparse
import json
import os
import random
import statistics
from copy import deepcopy

from extract_scaffolding_metrics import load_graph


EMERGENT_PREFIX = "Emergent_"


def orientation_shares(nmap, edges):
    em = {k: v for k, v in nmap.items() if v.get("is_emergent") or str(k).startswith(EMERGENT_PREFIX)}
    older_to_newer = 0
    newer_to_older = 0
    comparable = 0
    for e in edges:
        s, t = e["source"], e["target"]
        if s in em and t in em:
            ts_s, ts_t = em[s]["timestamp"], em[t]["timestamp"]
            if ts_s is None or ts_t is None or ts_s == ts_t:
                continue
            comparable += 1
            if e.get("undirected"):
                older_to_newer += 1
            else:
                older_to_newer += 1 if ts_s < ts_t else 0
                newer_to_older += 1 if ts_s > ts_t else 0
    if not comparable:
        return None, None
    return older_to_newer / comparable, newer_to_older / comparable


def orientation_share(nmap, edges, orientation):
    older_to_newer, newer_to_older = orientation_shares(nmap, edges)
    if orientation == "older_to_newer":
        return older_to_newer
    return newer_to_older


def shuffle_null(nmap, edges, n, orientation):
    em_ids = [k for k, v in nmap.items() if v.get("is_emergent") or str(k).startswith(EMERGENT_PREFIX)]
    ts = [nmap[k]["timestamp"] for k in em_ids]
    obs = orientation_share(nmap, edges, orientation)
    sims = []
    for _ in range(n):
        random.shuffle(ts)
        tmp = deepcopy(nmap)
        for i, k in enumerate(em_ids):
            tmp[k]["timestamp"] = ts[i]
        s = orientation_share(tmp, edges, orientation)
        if s is not None:
            sims.append(s)
    mu = statistics.mean(sims) if sims else None
    sd = statistics.pstdev(sims) if len(sims) > 1 else 0.0
    z = ((obs - mu) / sd) if (obs is not None and mu is not None and sd and sd > 0) else None
    return {"observed": obs, "mean": mu, "std": sd, "z": z, "n": len(sims)}


def degree_preserving_null(edges, nswap=1000):
    e = [(x["source"], x["target"], x["weight"], bool(x.get("undirected", False))) for x in edges]
    if len(e) < 2:
        return edges
    for _ in range(nswap):
        i, j = random.sample(range(len(e)), 2)
        a, b, wa, ua = e[i]
        c, d, wc, uc = e[j]
        if ua or uc:
            continue
        if len({a, b, c, d}) < 4:
            continue
        e[i] = (a, d, wa, ua)
        e[j] = (c, b, wc, uc)
    return [{"source": s, "target": t, "weight": w, "undirected": u} for s, t, w, u in e]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument(
        "--orientation",
        choices=["older_to_newer", "newer_to_older"],
        default="older_to_newer",
        help="Orientation override for 'observed' and null share calculations; scaffolding defaults to older->newer.",
    )
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    nmap, edges = load_graph(args.state)

    shuffle = shuffle_null(nmap, edges, args.n, args.orientation)

    observed_older_to_newer_share, observed_newer_to_older_share = orientation_shares(nmap, edges)
    scaffolding_share = observed_older_to_newer_share
    obs = orientation_share(nmap, edges, args.orientation)
    sims = []
    for _ in range(args.n):
        rewired = degree_preserving_null(edges, nswap=min(5000, len(edges) * 2))
        s = orientation_share(nmap, rewired, args.orientation)
        if s is not None:
            sims.append(s)
    mu = statistics.mean(sims) if sims else None
    sd = statistics.pstdev(sims) if len(sims) > 1 else 0.0
    z = ((obs - mu) / sd) if (obs is not None and mu is not None and sd and sd > 0) else None

    out = {
        "edge_orientation_mode": args.orientation,
        "observed_older_to_newer_share": observed_older_to_newer_share,
        "observed_newer_to_older_share": observed_newer_to_older_share,
        "scaffolding_share": scaffolding_share,
        "observed": scaffolding_share,
        "shuffle_null": shuffle,
        "degree_preserving_null": {"observed": obs, "mean": mu, "std": sd, "z": z, "n": len(sims)},
    }
    with open(os.path.join(args.outdir, "null_models.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
