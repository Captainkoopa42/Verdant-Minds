#!/usr/bin/env python3
import argparse
import csv
import json
import os

try:
    from analysis.state_adapter import VerdantState
except ImportError:
    from state_adapter import VerdantState


def _higher_order_emergent_count(emergent_nodes):
    count = 0
    for nid in emergent_nodes:
        name = str(nid)
        nested = name.count("Emergent_") >= 2
        separators = sum(name.count(sep) for sep in ("__", ":", "|", "->", "/", "+"))
        if nested or separators >= 2:
            count += 1
    return count


def load_graph(path):
    state = VerdantState.load(path)
    nmap = {
        node["name"]: {
            "id": node["name"],
            "timestamp": node.get("creation_time"),
            "raw": node.get("raw", {}),
            "is_emergent": bool(node.get("is_emergent")),
            "access_count": int(node.get("access_count", 0) or 0),
            "connection_count": int(node.get("connection_count", 0) or 0),
            "stability": float(node.get("stability", 0.0) or 0.0),
            "metadata": node.get("metadata", {}),
        }
        for node in state.nodes
    }
    edges = []
    for edge in state.edges:
        normalized = dict(edge)
        if state.format_version == "v3":
            normalized["undirected"] = True
        edges.append(normalized)
    return nmap, edges


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

    vs = VerdantState.load(args.state)
    nmap, edges = load_graph(args.state)
    basins = vs.basins if isinstance(vs.basins, list) else []
    emergent = {node["name"]: node for node in vs.emergent_nodes}
    em_edges = []
    older_to_newer = 0
    newer_to_older = 0
    comparable = 0
    for edge in vs.emergent_edges:
        source = edge["source"]
        target = edge["target"]
        ts_s = emergent[source].get("creation_time")
        ts_t = emergent[target].get("creation_time")
        is_older_to_newer = None
        is_newer_to_older = None
        if ts_s is not None and ts_t is not None and ts_s != ts_t:
            comparable += 1
            if vs.format_version == "v3":
                is_older_to_newer = True
                is_newer_to_older = False
                older_to_newer += 1
            else:
                is_older_to_newer = ts_s < ts_t
                is_newer_to_older = ts_s > ts_t
                older_to_newer += 1 if is_older_to_newer else 0
                newer_to_older += 1 if is_newer_to_older else 0
        em_edges.append(
            {
                **edge,
                "src_ts": ts_s,
                "dst_ts": ts_t,
                "is_older_to_newer": is_older_to_newer,
                "is_newer_to_older": is_newer_to_older,
            }
        )

    older_to_newer_share = (older_to_newer / comparable) if comparable else None
    newer_to_older_share = (newer_to_older / comparable) if comparable else (0.0 if vs.format_version == "v3" and comparable == 0 else None)
    scaffolding_share = older_to_newer_share
    earlier_share = scaffolding_share
    metrics = {
        "state": args.state,
        "nodes": vs.node_count,
        "edges": vs.edge_count,
        "emergent_nodes": vs.emergent_count,
        "emergent_edges": len(vs.emergent_edges),
        "comparable_emergent_edges": comparable,
        "older_to_newer_share": older_to_newer_share,
        "newer_to_older_share": newer_to_older_share,
        "scaffolding_share": scaffolding_share,
        "earlier_share": earlier_share,
        "edge_orientation_mode": args.orientation,
        "basin_count": len(basins),
        "higher_order_emergent_count": _higher_order_emergent_count(emergent.keys()),
    }

    with open(os.path.join(args.outdir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    with open(os.path.join(args.outdir, "basins.json"), "w", encoding="utf-8") as f:
        json.dump({"basins": basins}, f, indent=2)

    with open(os.path.join(args.outdir, "emergent_edges.csv"), "w", newline="", encoding="utf-8") as f:
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
