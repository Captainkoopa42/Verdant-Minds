#!/usr/bin/env python3
"""Create comprehensive phase-diagram figures from sweep results."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _load_sweeps(sweep_dir: Path) -> list[dict[str, Any]]:
    payloads = []
    for path in sorted(sweep_dir.glob("sweep_*/sweep_results.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not payload.get("skipped", False):
            payloads.append(payload)
    return payloads


def _subplots_grid(count: int) -> tuple[int, int]:
    cols = max(1, math.ceil(math.sqrt(count)))
    rows = max(1, math.ceil(count / cols))
    return rows, cols


def _parameter_shift(sweep: dict[str, Any], metric: str) -> float:
    values = [row.get(metric) for row in sweep["results"] if row.get(metric) is not None]
    return float(max(values) - min(values)) if values else 0.0


def _plot_metric_panels(
    plt: Any,
    sweeps: list[dict[str, Any]],
    *,
    metric_mean: str,
    metric_std: str,
    ylabel: str,
    reference_line: float,
    reference_label: str,
    filename: str,
    outdir: Path,
) -> Path:
    rows, cols = _subplots_grid(len(sweeps))
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 4.8 * rows), squeeze=False)
    for ax in axes.flat[len(sweeps):]:
        ax.axis("off")
    for idx, sweep in enumerate(sweeps):
        ax = axes.flat[idx]
        xs = [row["value"] for row in sweep["results"]]
        ys = [row.get(metric_mean) for row in sweep["results"]]
        es = [row.get(metric_std) or 0.0 for row in sweep["results"]]
        ax.errorbar(xs, ys, yerr=es, fmt="o-", capsize=4)
        ax.axhline(reference_line, linestyle="--", color="#ff7676", alpha=0.8, label=reference_label)
        ax.set_title(f"{ylabel} vs {sweep['parameter']}")
        ax.set_xlabel(sweep["parameter"])
        ax.set_ylabel(ylabel)
        ax.legend(loc="best")
    fig.tight_layout()
    output_path = outdir / filename
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate phase-diagram sweep figures")
    parser.add_argument("--sweep-dir", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as exc:
        raise SystemExit(f"matplotlib and numpy are required: {exc}")

    plt.style.use("dark_background")
    sweeps = _load_sweeps(Path(args.sweep_dir))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if not sweeps:
        raise SystemExit("No sweep_results.json files found")

    outputs: list[Path] = []
    outputs.append(
        _plot_metric_panels(
            plt,
            sweeps,
            metric_mean="onset_cycle_mean",
            metric_std="onset_cycle_std",
            ylabel="onset_cycle",
            reference_line=9.0,
            reference_label="cycle 9 reference",
            filename="phase_onset_cycle_panels.png",
            outdir=outdir,
        )
    )
    outputs.append(
        _plot_metric_panels(
            plt,
            sweeps,
            metric_mean="onset_t_g_mean",
            metric_std="onset_t_g_std",
            ylabel="onset_T_g",
            reference_line=0.572,
            reference_label="T_g = 0.572 reference",
            filename="phase_onset_tg_panels.png",
            outdir=outdir,
        )
    )

    ranked = sorted(
        (
            {
                "parameter": sweep["parameter"],
                "cycle_shift": _parameter_shift(sweep, "onset_cycle_mean"),
                "tg_shift": _parameter_shift(sweep, "onset_t_g_mean"),
                "results": sweep["results"],
            }
            for sweep in sweeps
        ),
        key=lambda row: (-row["cycle_shift"], row["parameter"]),
    )

    fig3, ax3 = plt.subplots(figsize=(9, 5.5))
    ax3.bar([row["parameter"] for row in ranked], [row["cycle_shift"] for row in ranked], color="#5cc8ff")
    ax3.set_ylabel("max(onset_cycle) - min(onset_cycle)")
    ax3.set_title("Onset sensitivity ranking")
    ax3.tick_params(axis="x", rotation=35)
    fig3.tight_layout()
    outputs.append(outdir / "phase_onset_sensitivity.png")
    fig3.savefig(outputs[-1], dpi=220, bbox_inches="tight")

    significant = [row for row in ranked if row["cycle_shift"] > 0.25]
    if len(significant) >= 2:
        first, second = significant[:2]
        x_vals = [entry["value"] for entry in first["results"]]
        y_vals = [entry["value"] for entry in second["results"]]
        x_means = np.array([entry["onset_cycle_mean"] or np.nan for entry in first["results"]], dtype=float)
        y_means = np.array([entry["onset_cycle_mean"] or np.nan for entry in second["results"]], dtype=float)
        surface = (y_means[:, None] + x_means[None, :]) / 2.0
        fig4, ax4 = plt.subplots(figsize=(7, 5.5))
        im = ax4.imshow(surface, aspect="auto", origin="lower", cmap="magma")
        ax4.set_xticks(range(len(x_vals)))
        ax4.set_xticklabels(x_vals)
        ax4.set_yticks(range(len(y_vals)))
        ax4.set_yticklabels(y_vals)
        ax4.set_xlabel(first["parameter"])
        ax4.set_ylabel(second["parameter"])
        ax4.set_title("Projected 2D onset surface")
        cbar = fig4.colorbar(im, ax=ax4)
        cbar.set_label("projected onset_cycle")
        fig4.tight_layout()
        outputs.append(outdir / "phase_onset_surface_projection.png")
        fig4.savefig(outputs[-1], dpi=220, bbox_inches="tight")

    varying_tg = [row for row in ranked if row["tg_shift"] > 0.002]
    if varying_tg:
        fig5, ax5 = plt.subplots(figsize=(9, 5.5))
        for row in varying_tg:
            xs = [entry["value"] for entry in row["results"]]
            ys = [entry["onset_t_g_mean"] for entry in row["results"]]
            ax5.plot(xs, ys, marker="o", label=row["parameter"])
        ax5.axhline(0.572, linestyle="--", color="#ff7676", alpha=0.8, label="T_g = 0.572")
        ax5.set_xlabel("swept parameter value")
        ax5.set_ylabel("critical onset T_g")
        ax5.set_title("F_c = 0 surface projection")
        ax5.legend(loc="best")
        fig5.tight_layout()
        outputs.append(outdir / "phase_fc0_surface_projection.png")
        fig5.savefig(outputs[-1], dpi=220, bbox_inches="tight")

    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
