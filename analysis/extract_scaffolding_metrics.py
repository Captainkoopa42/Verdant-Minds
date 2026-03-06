#!/usr/bin/env python3
import argparse
import csv
import json
import os
from datetime import datetime


def parse_ts(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt).timestamp()
        except Exception:
            pass
    try:
        return float(s)
    except Exception:
        return None




def first_present(*values):
    for v in values:
        if v is not None:
            return v
    return None

def _load_snapshot_graph(data):
    mw = data.get("memory_web") or {}
    store = mw.get("memory_store") or {}
    edge_list = mw.get("edges") or []

    nmap = {}
    for nid, payload in store.items():
        md = payload.get("metadata") if isinstance(payload, dict) else {}
        md = md if isinstance(md, dict) else {}
        ts = parse_ts(first_present(md.get("created_at"), md.get("creation_time"), payload.get("first_seen")))
        nmap[str(nid)] = {"id": str(nid), "timestamp": ts, "raw": payload}

    norm_edges = []
    for e in edge_list:
        if isinstance(e, (list, tuple)) and len(e) >= 3:
            s, t, w = e[0], e[1], e[2]
            norm_edges.append({"source": str(s), "target": str(t), "weight": float(w)})
        elif isinstance(e, dict):
            s = e.get("source") or e.get("src") or e.get("from")
            t = e.get("target") or e.get("dst") or e.get("to")
            if s is None or t is None:
                continue
            norm_edges.append({"source": str(s), "target": str(t), "weight": float(e.get("weight", e.get("w", 1.0)))})
    return nmap, norm_edges


def load_graph(path):
    data = json.load(open(path))

    if isinstance(data, dict) and "memory_web" in data:
        return _load_snapshot_graph(data)

    nodes = data.get("nodes") or data.get("concepts") or []
    edges = data.get("edges") or data.get("relations") or data.get("links") or []
    nmap = {}
    for n in nodes:
        nid = n.get("id") or n.get("name") or n.get("key")
        if nid is None:
            continue
        ts = parse_ts(first_present(n.get("timestamp"), n.get("created_at"), n.get("time")))
        nmap[str(nid)] = {"id": str(nid), "timestamp": ts, "raw": n}
    norm_edges = []
    for e in edges:
        s = e.get("source") or e.get("src") or e.get("from")
        t = e.get("target") or e.get("dst") or e.get("to")
        if s is None or t is None:
            continue
        w = float(e.get("weight", e.get("w", 1.0)))
        norm_edges.append({"source": str(s), "target": str(t), "weight": w})
    return nmap, norm_edges


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument(
        "--orientation",
        choices=["older_to_newer", "newer_to_older"],
        default="older_to_newer",
        help="Orientation mode used to populate backward-compatible earlier_share.",
    )
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    nmap, edges = load_graph(args.state)
    raw_state = json.load(open(args.state))
    basins = []
    if isinstance(raw_state, dict):
        extra = raw_state.get("extra", {})
        if isinstance(extra, dict):
            raw_basins = extra.get("last_basins", [])
            if isinstance(raw_basins, list):
                basins = [b for b in raw_basins if isinstance(b, dict)]
    emergent = {nid: n for nid, n in nmap.items() if nid.startswith("Emergent_")}
    em_edges = []
    older_to_newer = 0
    newer_to_older = 0
    comparable = 0
    for e in edges:
        if e["source"] in emergent and e["target"] in emergent:
            ts_s = emergent[e["source"]]["timestamp"]
            ts_t = emergent[e["target"]]["timestamp"]
            is_older_to_newer = None
            is_newer_to_older = None
            if ts_s is not None and ts_t is not None:
                comparable += 1
                is_older_to_newer = ts_s < ts_t
                is_newer_to_older = ts_s > ts_t
                older_to_newer += 1 if is_older_to_newer else 0
                newer_to_older += 1 if is_newer_to_older else 0
            em_edges.append(
                {
                    **e,
                    "src_ts": ts_s,
                    "dst_ts": ts_t,
                    "is_older_to_newer": is_older_to_newer,
                    "is_newer_to_older": is_newer_to_older,
                }
            )

    older_to_newer_share = (older_to_newer / comparable) if comparable else None
    newer_to_older_share = (newer_to_older / comparable) if comparable else None
    # In V2, emergent->emergent edges are interpreted as scaffolding (older->newer).
    # Keep backward-compatible fields, but make reporting explicit and unambiguous.
    scaffolding_share = older_to_newer_share
    earlier_share = scaffolding_share
    metrics = {
        "state": args.state,
        "nodes": len(nmap),
        "edges": len(edges),
        "emergent_nodes": len(emergent),
        "emergent_edges": len(em_edges),
        "comparable_emergent_edges": comparable,
        "older_to_newer_share": older_to_newer_share,
        "newer_to_older_share": newer_to_older_share,
        "scaffolding_share": scaffolding_share,
        "earlier_share": earlier_share,
        "edge_orientation_mode": args.orientation,
        "basin_count": len(basins),
    }

    with open(os.path.join(args.outdir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    with open(os.path.join(args.outdir, "basins.json"), "w") as f:
        json.dump({"basins": basins}, f, indent=2)

    with open(os.path.join(args.outdir, "emergent_edges.csv"), "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "source",
                "target",
                "weight",
                "src_ts",
                "dst_ts",
                "is_older_to_newer",
                "is_newer_to_older",
            ],
        )
        w.writeheader()
        w.writerows(em_edges)

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
