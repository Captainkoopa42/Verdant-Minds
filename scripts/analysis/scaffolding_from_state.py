#!/usr/bin/env python3
"""Analyze emergent scaffolding structure from a Verdant state JSON file.

Method summary:
- Uses metadata.creation_time as primary ordering.
- Falls back to parsing the last 9+ digit timestamp token in the concept label.
- Treats MemoryWeb as an undirected weighted graph; constructs a top-k backbone per node.
- Counts only emergent↔emergent (EE) edges found in that backbone.
- Reports earlier-share: fraction of EE edges oriented newer -> older (excluding equal-time ties).
- Runs shuffle trials by permuting creation times across emergent nodes while keeping EE edges fixed.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import matplotlib.pyplot as plt
import networkx as nx


TS_RE = re.compile(r"(?:^|_)(\d{9,})(?:$|_)")  # 9+ digits: unix seconds-ish, avoids small numbers


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fallback_timestamp_from_label(label: str) -> float:
    """Fallback: extract the last 9+ digit token anywhere in the label."""
    hits = TS_RE.findall(str(label))
    if not hits:
        return float("nan")
    try:
        return float(int(hits[-1]))
    except Exception:
        return float("nan")


def _is_emergent(payload: Dict[str, Any]) -> bool:
    meta = (payload or {}).get("metadata", {}) or {}
    return str(meta.get("origin", "")).lower() == "wave_emergence"


def _creation_time(label: str, payload: Dict[str, Any]) -> float:
    """Primary: metadata.creation_time; fallback: label timestamp; else NaN."""
    meta = (payload or {}).get("metadata", {}) or {}
    ct = meta.get("creation_time", None)
    if ct is not None:
        return _safe_float(ct, default=float("nan"))
    return _fallback_timestamp_from_label(label)


def _iter_connections(raw_connections: Any) -> Iterable[Tuple[str, float]]:
    """
    Supports:
      - dict: {target: weight} or {target: {weight: ...}}
      - list/tuple items: "node" OR {"target":..., "weight":...} OR ["node", weight]
      - str: "node"
    """
    if isinstance(raw_connections, dict):
        for key, value in raw_connections.items():
            if isinstance(value, dict):
                w = value.get("weight", 1.0)
            else:
                w = value
            yield str(key), _safe_float(w, 1.0)
        return

    if isinstance(raw_connections, (list, tuple)):
        for item in raw_connections:
            if isinstance(item, str):
                yield item, 1.0
            elif isinstance(item, dict):
                target = item.get("target") or item.get("node") or item.get("concept") or item.get("label") or item.get("name")
                if not target:
                    continue
                yield str(target), _safe_float(item.get("weight", item.get("strength", 1.0)), 1.0)
            elif isinstance(item, (list, tuple)) and len(item) >= 1:
                target = item[0]
                w = item[1] if len(item) >= 2 else 1.0
                yield str(target), _safe_float(w, 1.0)
        return

    if isinstance(raw_connections, str):
        yield raw_connections, 1.0


def _build_weighted_undirected_graph(memory_store: Dict[str, Dict[str, Any]]) -> nx.Graph:
    """Build an undirected weighted graph from memory_store connections (max weight on duplicates)."""
    g = nx.Graph()
    for label in memory_store.keys():
        g.add_node(label)

    for source, payload in memory_store.items():
        for target, weight in _iter_connections((payload or {}).get("connections", [])):
            if not target or target == source:
                continue
            if target not in memory_store:
                # Some states may reference nodes not present in memory_store
                continue
            w = _safe_float(weight, 1.0)
            if g.has_edge(source, target):
                g[source][target]["weight"] = max(_safe_float(g[source][target].get("weight", 0.0)), w)
            else:
                g.add_edge(source, target, weight=w)
    return g


def _topk_backbone_undirected(g: nx.Graph, topk: int) -> nx.Graph:
    """Keep top-k weighted incident edges per node (union across nodes)."""
    h = nx.Graph()
    h.add_nodes_from(g.nodes(data=True))

    for u in g.nodes():
        nbrs = [(v, _safe_float(g[u][v].get("weight", 0.0))) for v in g.neighbors(u)]
        nbrs.sort(key=lambda x: x[1], reverse=True)
        for v, w in nbrs[:topk]:
            if h.has_edge(u, v):
                h[u][v]["weight"] = max(_safe_float(h[u][v].get("weight", 0.0)), w)
            else:
                h.add_edge(u, v, weight=w)

    # keep largest connected component for cleaner plots/metrics
    if h.number_of_edges() > 0:
        largest_cc = max(nx.connected_components(h), key=len)
        h = h.subgraph(list(largest_cc)).copy()
    return h


def analyze_scaffolding(state_path: Path, topk: int, trials: int) -> Dict[str, Any]:
    with state_path.open("r", encoding="utf-8") as fh:
        state = json.load(fh)

    memory_store: Dict[str, Dict[str, Any]] = (((state or {}).get("memory_web", {}) or {}).get("memory_store", {}) or {})
    if not isinstance(memory_store, dict):
        raise ValueError("state['memory_web']['memory_store'] must be a dict")

    # creation times: only meaningful for emergents; seeded nodes may not have ct
    emergents = {label for label, payload in memory_store.items() if isinstance(payload, dict) and _is_emergent(payload)}
    creation = {label: _creation_time(label, memory_store.get(label, {})) for label in emergents}

    # Graph + backbone
    full = _build_weighted_undirected_graph(memory_store)
    backbone = _topk_backbone_undirected(full, topk=topk)

    # Emergent-only edges in backbone
    ee_edges_used: List[Tuple[str, str]] = []
    for u, v in backbone.edges():
        if u in emergents and v in emergents:
            # require both endpoints to have a finite creation time
            tu = creation.get(u, float("nan"))
            tv = creation.get(v, float("nan"))
            if math.isfinite(tu) and math.isfinite(tv):
                ee_edges_used.append((u, v))

    earlier = later = equal = 0
    age_gaps: List[float] = []
    scaffold = nx.DiGraph()
    scaffold.add_nodes_from(sorted(emergents))

    for u, v in ee_edges_used:
        tu, tv = creation[u], creation[v]
        if tu < tv:
            earlier += 1
            newer, older, gap = v, u, tv - tu
        elif tu > tv:
            later += 1
            newer, older, gap = u, v, tu - tv
        else:
            equal += 1
            continue

        if math.isfinite(gap):
            age_gaps.append(gap)

        w = _safe_float(backbone[u][v].get("weight", 0.0))
        # orient newer -> older
        if scaffold.has_edge(newer, older):
            scaffold[newer][older]["weight"] = max(_safe_float(scaffold[newer][older].get("weight", 0.0)), w)
        else:
            scaffold.add_edge(newer, older, weight=w)

    denom = (earlier + later)
    observed_share = (earlier / denom) if denom > 0 else 0.0

    # Shuffle baseline: shuffle observed creation times across emergent nodes
    shuffle_vals: List[float] = []
    em_nodes = [n for n in emergents if math.isfinite(creation.get(n, float("nan")))]
    if denom > 0 and len(em_nodes) >= 10 and trials > 0:
        times = [creation[n] for n in em_nodes]
        for _ in range(trials):
            random.shuffle(times)
            fake = {n: t for n, t in zip(em_nodes, times)}
            e = l = 0
            for u, v in ee_edges_used:
                tu, tv = fake[u], fake[v]
                if tu < tv:
                    e += 1
                elif tu > tv:
                    l += 1
            share = e / (e + l) if (e + l) > 0 else 0.0
            shuffle_vals.append(share)

    shuffle_mean = mean(shuffle_vals) if shuffle_vals else 0.0
    shuffle_sd = pstdev(shuffle_vals) if len(shuffle_vals) > 1 else 0.0
    z_score = (observed_share - shuffle_mean) / shuffle_sd if shuffle_sd > 0 else 0.0

    return {
        "full_nodes": full.number_of_nodes(),
        "full_edges": full.number_of_edges(),
        "backbone_nodes": backbone.number_of_nodes(),
        "backbone_edges": backbone.number_of_edges(),
        "emergent_nodes": len(emergents),
        "ee_edges_used": len(ee_edges_used),
        "earlier": earlier,
        "later": later,
        "equal": equal,
        "earlier_share": float(observed_share),
        "shuffle_mean": float(shuffle_mean),
        "shuffle_sd": float(shuffle_sd),
        "z": float(z_score),
        "age_gaps": age_gaps,
        "scaffold_graph": scaffold,
    }


def _plot_scaffolding(scaffold: nx.DiGraph, output_path: Path) -> None:
    plt.figure(figsize=(12, 9))
    if scaffold.number_of_edges() == 0:
        plt.text(0.5, 0.5, "No emergent scaffold edges found", ha="center", va="center")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(output_path, dpi=180)
        plt.close()
        return

    pos = nx.spring_layout(scaffold, seed=42, k=0.8, iterations=200)

    # label only top-degree nodes for readability
    deg = dict(scaffold.degree())
    label_nodes = set(sorted(deg, key=deg.get, reverse=True)[:12])
    labels = {n: n.replace("Emergent_", "E:")[:28] for n in label_nodes}

    nx.draw_networkx_edges(scaffold, pos, arrows=True, arrowstyle="-|>", arrowsize=10, alpha=0.35, width=1.0)
    nx.draw_networkx_nodes(scaffold, pos, node_size=220, alpha=0.85)
    nx.draw_networkx_labels(scaffold, pos, labels=labels, font_size=8)

    plt.title("Emergent Scaffolding (newer → older)")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def _plot_age_gaps(age_gaps: Sequence[float], output_path: Path) -> None:
    plt.figure(figsize=(10, 4))
    if age_gaps:
        bins = min(30, max(8, int(len(age_gaps) ** 0.5) * 4))
        plt.hist(age_gaps, bins=bins, edgecolor="black")
    else:
        plt.text(0.5, 0.5, "No age gaps available", ha="center", va="center")
    plt.title("Emergent→Emergent link age gaps (newer → older)")
    plt.xlabel("Time gap (seconds)")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Emergent scaffolding metrics from a persisted Verdant state")
    parser.add_argument("--state", required=True, help="Path to Verdant JSON state")
    parser.add_argument("--topk", type=int, default=6, help="Top-k backbone edges per node")
    parser.add_argument("--trials", type=int, default=500, help="Shuffle trial count for earlier-share baseline")
    parser.add_argument("--outdir", default=None, help="Optional output directory for PNGs")
    args = parser.parse_args()

    state_path = Path(args.state).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve() if args.outdir else state_path.parent
    outdir.mkdir(parents=True, exist_ok=True)

    metrics = analyze_scaffolding(state_path=state_path, topk=args.topk, trials=args.trials)

    scaffolding_png = outdir / "emergent_scaffolding.png"
    age_gaps_png = outdir / "link_age_gaps.png"
    _plot_scaffolding(metrics["scaffold_graph"], scaffolding_png)
    _plot_age_gaps(metrics["age_gaps"], age_gaps_png)

    print(f"Full graph: nodes={metrics['full_nodes']} edges={metrics['full_edges']}")
    print(f"Backbone graph: nodes={metrics['backbone_nodes']} edges={metrics['backbone_edges']} (top-{args.topk}/node)")
    print(f"Emergent nodes: {metrics['emergent_nodes']} | EE edges used: {metrics['ee_edges_used']}")
    print(f"earlier={metrics['earlier']} later={metrics['later']} equal={metrics['equal']}")
    print(f"earlier-share (excluding equal): {metrics['earlier_share']:.4f}")
    print(f"shuffle mean±sd: {metrics['shuffle_mean']:.4f} ± {metrics['shuffle_sd']:.4f}")
    print(f"z-score: {metrics['z']:.4f}")
    print(f"saved: {scaffolding_png}")
    print(f"saved: {age_gaps_png}")


if __name__ == "__main__":
    main()
