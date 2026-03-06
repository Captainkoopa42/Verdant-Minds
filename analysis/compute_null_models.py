#!/usr/bin/env python3
import argparse, json, os, random, statistics
from copy import deepcopy
from extract_scaffolding_metrics import load_graph


def orientation_share(nmap, edges, orientation):
    em = {k: v for k, v in nmap.items() if k.startswith("Emergent_")}
    vals = []
    for e in edges:
        s, t = e["source"], e["target"]
        if s in em and t in em:
            ts_s, ts_t = em[s]["timestamp"], em[t]["timestamp"]
            if ts_s is not None and ts_t is not None:
                if orientation == "older_to_newer":
                    vals.append(1.0 if ts_s < ts_t else 0.0)
                else:
                    vals.append(1.0 if ts_s > ts_t else 0.0)
    return (sum(vals) / len(vals)) if vals else None


def shuffle_null(nmap, edges, n, orientation):
    em_ids = [k for k in nmap if k.startswith("Emergent_")]
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
    z = ((obs - mu) / sd) if (obs is not None and sd and sd > 0) else None
    return {"observed": obs, "mean": mu, "std": sd, "z": z, "n": len(sims)}


def degree_preserving_null(edges, nswap=1000):
    e = [(x["source"], x["target"], x["weight"]) for x in edges]
    if len(e) < 2:
        return edges
    for _ in range(nswap):
        i, j = random.sample(range(len(e)), 2)
        a, b, wa = e[i]
        c, d, wc = e[j]
        if len({a, b, c, d}) < 4:
            continue
        e[i] = (a, d, wa)
        e[j] = (c, b, wc)
    return [{"source": s, "target": t, "weight": w} for s, t, w in e]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument(
        "--orientation",
        choices=["older_to_newer", "newer_to_older"],
        default="older_to_newer",
        help="Orientation mode for observed/null share calculations.",
    )
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    nmap, edges = load_graph(args.state)

    shuffle = shuffle_null(nmap, edges, args.n, args.orientation)

    obs = orientation_share(nmap, edges, args.orientation)
    sims = []
    for _ in range(args.n):
        rewired = degree_preserving_null(edges, nswap=min(5000, len(edges) * 2))
        s = orientation_share(nmap, rewired, args.orientation)
        if s is not None:
            sims.append(s)
    mu = statistics.mean(sims) if sims else None
    sd = statistics.pstdev(sims) if len(sims) > 1 else 0.0
    z = ((obs - mu) / sd) if (obs is not None and sd and sd > 0) else None

    out = {
        "edge_orientation_mode": args.orientation,
        "shuffle_null": shuffle,
        "degree_preserving_null": {"observed": obs, "mean": mu, "std": sd, "z": z, "n": len(sims)},
    }
    with open(os.path.join(args.outdir, "null_models.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
