#!/usr/bin/env python3
import argparse
import json
import math
import os
from collections import defaultdict

from extract_scaffolding_metrics import load_graph


def _load_json(path):
    with open(path) as f:
        return json.load(f)


def _gini(values):
    xs = sorted(float(max(v, 0.0)) for v in values)
    n = len(xs)
    if n == 0:
        return None
    s = sum(xs)
    if s == 0:
        return 0.0
    cum = 0.0
    for i, x in enumerate(xs, 1):
        cum += i * x
    return (2 * cum) / (n * s) - (n + 1) / n


def _save_multi(fig, basepath):
    fig.savefig(basepath + ".png", dpi=220, bbox_inches="tight")
    try:
        fig.savefig(basepath + ".pdf", bbox_inches="tight")
    except Exception as e:
        print(f"warning: pdf export failed for {basepath}: {e}")


def _build_access_counts(nmap, edges):
    access = defaultdict(float)
    for nid, meta in nmap.items():
        raw = meta.get("raw", {})
        v = raw.get("access_count", raw.get("access", None))
        if isinstance(v, (int, float)):
            access[nid] += float(v)
    # fallback to weighted indegree if access_count absent
    if not any(v > 0 for v in access.values()):
        for e in edges:
            access[e["target"]] += float(e.get("weight", 1.0))
    return access


def _extract_log_dts(nmap, edges):
    ts = {k: v.get("timestamp") for k, v in nmap.items()}
    vals = []
    for e in edges:
        a = ts.get(e["source"])
        b = ts.get(e["target"])
        if a is None or b is None:
            continue
        dt = abs(a - b)
        if dt > 0:
            vals.append(math.log(dt))
    return vals


def main():
    ap = argparse.ArgumentParser(description="Generate camera-ready figures from Verdant analysis outputs.")
    ap.add_argument("--state", required=True, help="Path to persisted state JSON")
    ap.add_argument("--metrics", required=True, help="metrics.json from extract_scaffolding_metrics.py")
    ap.add_argument("--nulls", required=True, help="null_models.json from compute_null_models.py")
    ap.add_argument("--mixture", required=True, help="two_timescale_mixture.json from fit_two_timescale_mixture.py")
    ap.add_argument("--outdir", required=True, help="Output figure directory")
    ap.add_argument("--basins", required=False, help="Optional basins.json from extract script")
    args = ap.parse_args()

    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as e:
        raise SystemExit(f"matplotlib/numpy required for figure generation: {e}")

    os.makedirs(args.outdir, exist_ok=True)

    nmap, edges = load_graph(args.state)
    metrics = _load_json(args.metrics)
    nulls = _load_json(args.nulls)
    mixture = _load_json(args.mixture)
    basins_payload = _load_json(args.basins) if args.basins and os.path.exists(args.basins) else {"basins": []}

    # 1) emergent-only directed scaffold: newer->older
    em = {k: v for k, v in nmap.items() if k.startswith("Emergent_")}
    oriented = []
    for e in edges:
        s, t = e["source"], e["target"]
        if s in em and t in em:
            ts_s = em[s].get("timestamp")
            ts_t = em[t].get("timestamp")
            if ts_s is None or ts_t is None:
                continue
            if ts_s > ts_t:
                oriented.append((s, t))

    # map ids to time-rank for deterministic layout
    ranked = sorted([(nid, em[nid].get("timestamp") or 0.0) for nid in em], key=lambda x: x[1])
    posx = {nid: i for i, (nid, _) in enumerate(ranked)}

    fig, ax = plt.subplots(figsize=(11, 6))
    y_positions = {nid: (i % 9) for i, (nid, _) in enumerate(ranked)}
    for s, t in oriented:
        ax.annotate(
            "",
            xy=(posx[t], y_positions[t]),
            xytext=(posx[s], y_positions[s]),
            arrowprops=dict(arrowstyle="->", lw=0.7, alpha=0.25, color="#2A6FBB"),
        )
    ax.scatter([posx[n] for n, _ in ranked], [y_positions[n] for n, _ in ranked], s=14, c="#003049")
    ax.set_title(f"Emergent scaffold (newer→older only), edges={len(oriented)}")
    ax.set_xlabel("Emergent node temporal rank (older → newer)")
    ax.set_ylabel("Layout lane")
    _save_multi(fig, os.path.join(args.outdir, "fig_scaffold_directed"))
    plt.close(fig)

    # 2) null distributions (approximate from summary moments)
    sn = nulls.get("shuffle_null", {})
    dn = nulls.get("degree_preserving_null", {})

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for ax, title, dct in [
        (axes[0], "Shuffle null", sn),
        (axes[1], "Degree-preserving null", dn),
    ]:
        mu = dct.get("mean") if dct.get("mean") is not None else dct.get("mu")
        sd = dct.get("std") if dct.get("std") is not None else dct.get("sigma")
        obs = dct.get("observed")
        n = int(dct.get("n", 0) or 0)
        if mu is not None and sd is not None and sd > 0 and n > 3:
            sim = np.random.default_rng(0).normal(mu, sd, n)
            ax.hist(sim, bins=min(40, max(10, n // 15)), color="#7FB3D5", alpha=0.9, density=True)
        if obs is not None:
            ax.axvline(obs, color="#C1121F", lw=2, label=f"observed={obs:.3f}")
        zval = dct.get("z")
        mu_label = f"{mu:.3f}" if isinstance(mu, (int, float)) else "n/a"
        sd_label = f"{sd:.3f}" if isinstance(sd, (int, float)) else "n/a"
        z_label = f"{zval:.3f}" if isinstance(zval, (int, float)) else "n/a"
        label = f"μ={mu_label} σ={sd_label} z={z_label}"
        ax.set_title(title)
        ax.set_xlabel("earlier_share")
        ax.text(0.02, 0.96, label, transform=ax.transAxes, va="top", fontsize=9)
        ax.legend(loc="upper left", fontsize=8)
    axes[0].set_ylabel("density")
    fig.suptitle("Null-model earlier-share distributions")
    _save_multi(fig, os.path.join(args.outdir, "fig_null_distributions"))
    plt.close(fig)

    # 3) age-gap mixture: histogram + 1c / 2c overlays + BIC annotation
    log_dts = _extract_log_dts(nmap, edges)
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    if log_dts:
        ax.hist(log_dts, bins=50, density=True, alpha=0.45, color="#669BBC", label="log(Δt) empirical")

    one = mixture.get("one_component", {})
    two = mixture.get("two_component", {})
    xs = np.linspace(min(log_dts), max(log_dts), 400) if log_dts else np.linspace(0, 1, 200)

    def normpdf(x, mu, sig):
        sig = max(float(sig), 1e-9)
        return np.exp(-0.5 * ((x - mu) / sig) ** 2) / (sig * np.sqrt(2 * np.pi))

    if one:
        y1 = normpdf(xs, one.get("mu", 0), one.get("sigma", 1))
        ax.plot(xs, y1, color="#780000", lw=2, label="1-component fit")
    if two:
        w = float(two.get("weight1", 0.5))
        y2 = w * normpdf(xs, two.get("mu1", 0), two.get("sigma1", 1)) + (1 - w) * normpdf(xs, two.get("mu2", 1), two.get("sigma2", 1))
        ax.plot(xs, y2, color="#2D6A4F", lw=2, label="2-component fit")

    dbic = mixture.get("delta_bic_two_minus_one")
    ax.set_title("Age-gap mixture fit on log(Δt)")
    ax.set_xlabel("log(Δt seconds)")
    ax.set_ylabel("density")
    ax.text(0.02, 0.96, f"ΔBIC(2-1)={dbic:.2f}" if isinstance(dbic, (int, float)) else "ΔBIC unavailable", transform=ax.transAxes, va="top")
    ax.legend()
    _save_multi(fig, os.path.join(args.outdir, "fig_age_gap_mixture"))
    plt.close(fig)

    # 4) access concentration: Lorenz + rank-frequency
    access = _build_access_counts(nmap, edges)
    vals = sorted(access.values())
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))

    if vals:
        cs = np.cumsum(vals)
        total = cs[-1] if cs[-1] > 0 else 1.0
        p = np.arange(1, len(vals) + 1) / len(vals)
        lorenz = cs / total
        axes[0].plot([0, 1], [0, 1], "k--", lw=1, alpha=0.6)
        axes[0].plot(np.insert(p, 0, 0), np.insert(lorenz, 0, 0), color="#1D3557", lw=2)
        g = _gini(vals)
        axes[0].set_title(f"Lorenz curve (Gini={g:.3f})" if g is not None else "Lorenz curve")
        axes[0].set_xlabel("Cumulative share of nodes")
        axes[0].set_ylabel("Cumulative share of access")

        desc = sorted(vals, reverse=True)
        ranks = np.arange(1, len(desc) + 1)
        axes[1].loglog(ranks, np.array(desc) + 1e-9, color="#E63946")
        top10 = sum(desc[:10]) / sum(desc) if sum(desc) > 0 else 0.0
        axes[1].set_title(f"Rank-frequency (Top10 share={top10:.3f})")
        axes[1].set_xlabel("Rank")
        axes[1].set_ylabel("Access count")

    fig.suptitle("Access concentration diagnostics")
    _save_multi(fig, os.path.join(args.outdir, "fig_access_concentration"))
    plt.close(fig)


    # 5) basin size distribution
    basins = basins_payload.get("basins", []) if isinstance(basins_payload, dict) else []
    basin_sizes = [int(b.get("size", 0)) for b in basins if isinstance(b, dict)]
    if basin_sizes:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ranks = np.arange(1, len(sorted(basin_sizes, reverse=True)) + 1)
        ax.plot(ranks, sorted(basin_sizes, reverse=True), marker="o", color="#457B9D")
        ax.set_xlabel("Basin rank")
        ax.set_ylabel("Basin size")
        ax.set_title("Basin size distribution")
        _save_multi(fig, os.path.join(args.outdir, "fig_basin_size_distribution"))
        plt.close(fig)

    # 6) basin density vs emergent count
    xs = [float(b.get("internal_density", 0.0)) for b in basins if isinstance(b, dict)]
    ys = [int(b.get("emergent_count", 0)) for b in basins if isinstance(b, dict)]
    if xs and ys:
        fig, ax = plt.subplots(figsize=(6.8, 4.8))
        ax.scatter(xs, ys, color="#2A9D8F", alpha=0.85)
        for b in basins:
            if not isinstance(b, dict):
                continue
            ax.annotate(str(b.get("basin_id", "")), (float(b.get("internal_density", 0.0)), int(b.get("emergent_count", 0))), fontsize=7, alpha=0.7)
        ax.set_xlabel("Internal density")
        ax.set_ylabel("Emergent count")
        ax.set_title("Basin density vs emergent concepts")
        _save_multi(fig, os.path.join(args.outdir, "fig_basin_density_vs_emergent"))
        plt.close(fig)

    print("generated figures:")
    for f in [
        "fig_scaffold_directed",
        "fig_null_distributions",
        "fig_age_gap_mixture",
        "fig_access_concentration",
        "fig_basin_size_distribution",
        "fig_basin_density_vs_emergent",
    ]:
        print("-", os.path.join(args.outdir, f + ".png"))


if __name__ == "__main__":
    main()
