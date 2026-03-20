#!/usr/bin/env python3
"""Analyze H¹ coherence telemetry over developmental time."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis.telemetry_analysis_common import (
    iter_seed_cycles,
    linear_slope,
    resolve_run_dir,
    safe_corr,
    to_float,
    to_int,
    write_json,
)


def _trend_label(values: list[float]) -> str:
    slope = linear_slope(values)
    if slope > 1e-3:
        return "increasing"
    if slope < -1e-3:
        return "decreasing"
    return "stable"


def _finite_or_none(value: float) -> float | None:
    return float(value) if math.isfinite(value) else None


def _is_stable(values: list[float]) -> bool:
    if len(values) < 2:
        return True
    return pstdev(values) <= 0.05


def _row_bool(row: dict[str, Any], key: str) -> bool | None:
    value = row.get(key)
    if value is None:
        return None
    return bool(value)


def _collect_seed_summary(seed: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    cycles = [to_int(row.get("cycle_index")) for row in rows]
    h1_valid = [_row_bool(row, "h1_triangle_valid") for row in rows]
    h1_numeric = [1.0 if flag else 0.0 for flag in h1_valid if flag is not None]
    hci = [to_float(row.get("housed_contradiction_index"), 0.0) or 0.0 for row in rows]
    violation = [to_float(row.get("violation_rate"), 0.0) or 0.0 for row in rows]
    alpha = [to_float(row.get("alpha_critical_estimate")) for row in rows]
    alpha_present = [value for value in alpha if value is not None]
    alpha_filled = [value if value is not None else 0.0 for value in alpha]
    basin_count = [to_float(row.get("basin_count"), 0.0) or 0.0 for row in rows]
    bud_events = [1.0 if to_int(row.get("bud_events_count"), 0) > 0 else 0.0 for row in rows]
    boundary_events = [1.0 if to_int(row.get("boundary_emergents_created"), 0) > 0 else 0.0 for row in rows]
    emergence_events: list[float] = []
    prev_emergent = None
    for row in rows:
        emergent = to_int(row.get("emergent_count"), 0)
        emergence_events.append(1.0 if prev_emergent is not None and emergent > prev_emergent else 0.0)
        prev_emergent = emergent
    t_g = [to_float(row.get("t_g"), 0.0) or 0.0 for row in rows]

    onset_row = next((row for row in rows if to_int(row.get("cycle_index"), -1) == 9), rows[min(9, len(rows) - 1)])
    valid_known = [flag for flag in h1_valid if flag is not None]

    return {
        "seed": seed,
        "total_cycles": len(rows),
        "cycle_indices": cycles,
        "h1_triangle_valid_series": [1 if flag else 0 for flag in h1_valid if flag is not None],
        "h1_valid_fraction": float(sum(1 for flag in valid_known if flag) / len(valid_known)) if valid_known else 0.0,
        "h1_valid_count": int(sum(1 for flag in valid_known if flag)),
        "h1_valid_at_onset": bool(onset_row.get("h1_triangle_valid")) if onset_row.get("h1_triangle_valid") is not None else False,
        "h1_valid_at_end": bool(rows[-1].get("h1_triangle_valid")) if rows[-1].get("h1_triangle_valid") is not None else False,
        "hci_mean": float(mean(hci)) if hci else 0.0,
        "hci_std": float(pstdev(hci)) if len(hci) > 1 else 0.0,
        "hci_min": float(min(hci)) if hci else 0.0,
        "hci_max": float(max(hci)) if hci else 0.0,
        "hci_trend": _trend_label(hci),
        "violation_rate_mean": float(mean(violation)) if violation else 0.0,
        "violation_rate_max": float(max(violation)) if violation else 0.0,
        "alpha_critical_mean": float(mean(alpha_present)) if alpha_present else 0.0,
        "alpha_critical_stable": _is_stable(alpha_present),
        "h1_budding_correlation": _finite_or_none(float(safe_corr(violation, bud_events))) if violation else None,
        "h1_emergence_correlation": _finite_or_none(float(safe_corr(violation, emergence_events))) if violation else None,
        "h1_basin_count_correlation": _finite_or_none(float(safe_corr(h1_numeric, basin_count))) if h1_numeric and len(h1_numeric) == len(basin_count) else None,
        "violation_boundary_correlation": _finite_or_none(float(safe_corr(violation, boundary_events))) if violation else None,
        "alpha_tg_correlation": _finite_or_none(float(safe_corr(alpha_filled, t_g))) if alpha_filled else None,
        "series": {
            "hci": hci,
            "violation_rate": violation,
            "alpha_critical_estimate": alpha,
            "t_g": t_g,
            "basin_count": basin_count,
            "bud_events": bud_events,
            "boundary_events": boundary_events,
            "emergence_events": emergence_events,
        },
    }


def _aggregate_seed_summaries(per_seed: list[dict[str, Any]]) -> dict[str, Any]:
    if not per_seed:
        return {
            "total_cycles": 0,
            "h1_valid_fraction": 0.0,
            "h1_valid_at_onset": False,
            "h1_valid_at_end": False,
            "hci_mean": 0.0,
            "hci_trend": "stable",
            "violation_rate_mean": 0.0,
            "violation_rate_max": 0.0,
            "alpha_critical_mean": 0.0,
            "alpha_critical_stable": True,
            "h1_budding_correlation": 0.0,
            "h1_emergence_correlation": 0.0,
        }

    def _avg(key: str) -> float:
        vals = [float(item.get(key, 0.0)) for item in per_seed if item.get(key) is not None]
        return float(mean(vals)) if vals else 0.0

    hci_trends = [item.get("hci_trend", "stable") for item in per_seed]
    trend = max(set(hci_trends), key=hci_trends.count)
    return {
        "total_cycles": int(sum(int(item.get("total_cycles", 0)) for item in per_seed)),
        "h1_valid_fraction": _avg("h1_valid_fraction"),
        "h1_valid_at_onset": bool(all(item.get("h1_valid_at_onset", False) for item in per_seed)),
        "h1_valid_at_end": bool(all(item.get("h1_valid_at_end", False) for item in per_seed)),
        "hci_mean": _avg("hci_mean"),
        "hci_trend": trend,
        "violation_rate_mean": _avg("violation_rate_mean"),
        "violation_rate_max": max(float(item.get("violation_rate_max", 0.0)) for item in per_seed),
        "alpha_critical_mean": _avg("alpha_critical_mean"),
        "alpha_critical_stable": bool(all(item.get("alpha_critical_stable", False) for item in per_seed)),
        "h1_budding_correlation": _avg("h1_budding_correlation"),
        "h1_emergence_correlation": _avg("h1_emergence_correlation"),
        "per_seed": per_seed,
    }


def _make_figures(outdir: Path, per_seed: list[dict[str, Any]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - environment dependent
        raise SystemExit(f"matplotlib required for --figures: {exc}") from exc

    if not per_seed:
        return

    plt.style.use("dark_background")
    figures_dir = outdir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    seed0 = per_seed[0]
    x = seed0["cycle_indices"]
    series = seed0["series"]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    h1_plot = [1 if bool(val) else 0 for val in seed0["h1_triangle_valid_series"]]
    ax.step(x[: len(h1_plot)], h1_plot, where="post")
    ax.set_title("H¹ triangle validity over time (seed 0)")
    ax.set_xlabel("Cycle")
    ax.set_ylabel("Valid @ α=1.0")
    ax.set_ylim(-0.05, 1.05)
    fig.tight_layout()
    fig.savefig(figures_dir / "h1_triangle_valid_seed0.png", dpi=180)
    plt.close(fig)

    for key, title, filename in [
        ("hci", "Housed contradiction index", "hci_seed0.png"),
        ("violation_rate", "Violation rate", "violation_rate_seed0.png"),
        ("alpha_critical_estimate", "Alpha critical estimate", "alpha_critical_seed0.png"),
    ]:
        fig, ax = plt.subplots(figsize=(10, 4.5))
        y = [0.0 if value is None else float(value) for value in series[key]]
        ax.plot(x, y)
        ax.set_title(f"{title} over time (seed 0)")
        ax.set_xlabel("Cycle")
        ax.set_ylabel(title)
        fig.tight_layout()
        fig.savefig(figures_dir / filename, dpi=180)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--figures", action="store_true")
    args = parser.parse_args()

    run_dir = resolve_run_dir(args.run_dir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    per_seed: list[dict[str, Any]] = []
    for seed, _cycles_path, rows in iter_seed_cycles(run_dir, args.seeds):
        summary = _collect_seed_summary(seed, rows)
        per_seed.append(summary)
        write_json(outdir / f"h1_coherence_seed_{seed}.json", summary)

    payload = _aggregate_seed_summaries(per_seed)
    write_json(outdir / "h1_coherence_analysis.json", payload)

    if args.figures:
        _make_figures(outdir, per_seed)


if __name__ == "__main__":
    main()
