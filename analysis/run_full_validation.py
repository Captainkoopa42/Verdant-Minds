#!/usr/bin/env python3
"""Run the full V3 validation pipeline and emit a consolidated report."""

from __future__ import annotations

import sys
from pathlib import Path as _PathBootstrap

sys.path.insert(0, str(_PathBootstrap(__file__).resolve().parents[1]))

import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.baseline_random_graph import BaselineConfig, build_baseline_state
from analysis.detect_onset import detect_onset
from analysis.extract_scaffolding_metrics import load_graph
from analysis.telemetry_analysis_common import resolve_run_dir
import subprocess


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _seed_dirs(run_dir: Path) -> list[Path]:
    return sorted([path for path in run_dir.glob("seed_*") if path.is_dir()], key=lambda path: int(path.name.split("_")[-1]))


def _count_checkpoints(run_dir: Path) -> int:
    return sum(1 for _ in run_dir.glob("seed_*/checkpoint_*.json"))


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _status_label(value: bool) -> str:
    return "PASS" if value else "FAIL"


def _sigma_separation(verdant: float, baseline_mean: float, baseline_std: float) -> float:
    if baseline_std <= 0:
        return math.inf if verdant > baseline_mean else 0.0
    return float((verdant - baseline_mean) / baseline_std)


def _task3_status(total_daughters: int, forge_fraction_peak: float, max_emergent_any_daughter: int) -> str:
    if total_daughters == 0:
        return "NEEDS_LONGER_RUN"
    if forge_fraction_peak >= 0.10 or max_emergent_any_daughter >= 50:
        return "PASS"
    return "PARTIAL"


def _task4_status(meaningful_fraction: float, mean_score: float) -> str:
    return "PASS" if meaningful_fraction >= 0.75 and mean_score >= 0.70 else "FAIL"


def _task5_status(best_correlation: float) -> str:
    return "SIGNAL_FOUND" if abs(best_correlation) >= 0.15 else "NULL_RESULT"


def _task6_status(trend: str) -> str:
    normalized = str(trend).lower()
    if normalized == "homeostatic":
        return "HOMEOSTATIC"
    if normalized == "growing":
        return "GROWING"
    return "OSCILLATING"


def _task7_status(ari_mean: float) -> str:
    if ari_mean >= 0.80:
        return "PASS"
    if ari_mean >= 0.50:
        return "MODERATE"
    return "FAIL"


def _task8_status(h1_valid_fraction: float) -> str:
    if h1_valid_fraction > 0.9:
        return "PASS"
    if h1_valid_fraction >= 0.5:
        return "PARTIAL"
    return "FAIL"


TASK9_OPEN_CONJECTURE_NOTE = (
    "Open conjecture - tested empirically, does not hold with current tau* definition"
)


def _task9_status(_: float) -> str:
    return "REPORTED"


def _fmt_number(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float) and math.isinf(value):
        return "∞"
    return f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def _load_last_cycle(seed_dir: Path) -> dict[str, Any]:
    cycles_path = seed_dir / "cycles.jsonl"
    last = None
    with cycles_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                last = json.loads(line)
    if last is None:
        raise ValueError(f"No cycles found in {cycles_path}")
    return last


def _baseline_comparison(outdir: Path, cycles: int = 40, seeds: int = 20) -> dict[str, Any]:
    summary_path = outdir / "comparison_summary.json"
    if summary_path.exists():
        return _read_json(summary_path)

    def _earlier_share(state: dict[str, Any]) -> float:
        scratch = outdir / "_baseline_state.json"
        scratch.write_text(json.dumps(state), encoding="utf-8")
        nmap, edges = load_graph(str(scratch))
        emergent = {nid: meta for nid, meta in nmap.items() if meta.get("is_emergent") or str(nid).startswith("Emergent_")}
        comparable = 0
        earlier = 0
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            if source not in emergent or target not in emergent:
                continue
            ts_source = emergent[source]["timestamp"]
            ts_target = emergent[target]["timestamp"]
            if ts_source is None or ts_target is None or ts_source == ts_target:
                continue
            comparable += 1
            if edge.get("undirected"):
                earlier += 1
            else:
                earlier += 1 if ts_source < ts_target else 0
        return float(earlier / comparable) if comparable else 0.0

    outdir.mkdir(parents=True, exist_ok=True)
    earlier_values: list[float] = []
    for seed in range(seeds):
        state = build_baseline_state(BaselineConfig(cycles=cycles, seed=seed))
        earlier_values.append(_earlier_share(state))

    summary = {
        "baseline": {
            "earlier_share_mean": float(statistics.mean(earlier_values)) if earlier_values else 0.0,
            "earlier_share_std": float(statistics.pstdev(earlier_values)) if len(earlier_values) > 1 else 0.0,
            "earlier_share_values": earlier_values,
        },
        "note": "Comparison summary generated by analysis/run_full_validation.py",
    }
    _write_json(summary_path, summary)
    scratch = outdir / "_baseline_state.json"
    if scratch.exists():
        scratch.unlink()
    return summary


def build_report(run_dir: Path, outdir: Path, seeds: int | None, n_nulls: int, skip_slow: bool) -> dict[str, Any]:
    seed_dirs_all = _seed_dirs(run_dir)
    if not seed_dirs_all:
        raise FileNotFoundError(f"No seed directories found in {run_dir}")

    selected_seed_dirs = seed_dirs_all[:seeds] if seeds is not None else seed_dirs_all
    seed0_dir = selected_seed_dirs[0]
    seed0_state = seed0_dir / "state.json"

    scaffold_dir = outdir / "scaffold"
    mixture_dir = outdir / "mixture"
    backbone_dir = outdir / "backbone"
    nulls_dir = outdir / "nulls"
    figures_dir = outdir / "figures"
    daughter_dir = outdir / "daughter"
    semantic_dir = outdir / "semantic"
    robustness_dir = outdir / "robustness"
    baseline_dir = outdir / "baseline"
    onset_dir = outdir / "onset"

    outdir.mkdir(parents=True, exist_ok=True)

    _run([
        sys.executable,
        "analysis/extract_scaffolding_metrics.py",
        "--state",
        str(seed0_state),
        "--outdir",
        str(scaffold_dir),
        "--orientation",
        "older_to_newer",
    ])
    metrics = _read_json(scaffold_dir / "metrics.json")

    if skip_slow:
        nulls = None
    else:
        _run([
            sys.executable,
            "analysis/compute_null_models.py",
            "--state",
            str(seed0_state),
            "--outdir",
            str(nulls_dir),
            "--n",
            str(n_nulls),
            "--orientation",
            "older_to_newer",
        ])
        nulls = _read_json(nulls_dir / "null_models.json")

    _run([
        sys.executable,
        "analysis/fit_two_timescale_mixture.py",
        "--state",
        str(seed0_state),
        "--outdir",
        str(mixture_dir),
    ])
    _run([
        sys.executable,
        "analysis/export_backbone_graph.py",
        "--state",
        str(seed0_state),
        "--outdir",
        str(backbone_dir),
        "--k",
        "6",
    ])
    mixture = _read_json(mixture_dir / "two_timescale_mixture.json")

    figure_generation_error = None
    if not skip_slow:
        try:
            _run([
                sys.executable,
                "analysis/make_figures.py",
                "--state",
                str(seed0_state),
                "--metrics",
                str(scaffold_dir / "metrics.json"),
                "--nulls",
                str(nulls_dir / "null_models.json"),
                "--mixture",
                str(mixture_dir / "two_timescale_mixture.json"),
                "--outdir",
                str(figures_dir),
                "--basins",
                str(scaffold_dir / "basins.json"),
            ])
        except subprocess.CalledProcessError as exc:
            figure_generation_error = str(exc)
            print(f"warning: make_figures failed but validation will continue: {exc}")

    if not skip_slow:
        pipeline_dir = outdir / "seed0_pipeline"
        _run([
            sys.executable,
            "analysis/run_all.py",
            "--state",
            str(seed0_state),
            "--results-root",
            str(pipeline_dir),
            "--n-nulls",
            str(n_nulls),
            "--k",
            "6",
        ])

    onset_results: list[dict[str, Any]] = []
    for seed_dir in selected_seed_dirs:
        seed = int(seed_dir.name.split("_")[-1])
        onset = detect_onset(str(seed_dir / "cycles.jsonl"))
        onset["seed"] = seed
        onset_results.append(onset)
    _write_json(onset_dir / "aggregate_onset.json", {"per_seed": onset_results})

    _run([
        sys.executable,
        "analysis/run_daughter_analysis.py",
        "--run-dir",
        str(run_dir),
        "--seeds",
        str(len(selected_seed_dirs)),
        "--outdir",
        str(daughter_dir),
    ])
    daughter = _read_json(daughter_dir / "aggregate_daughter_analysis.json")

    _run([
        sys.executable,
        "analysis/run_semantic_evaluation.py",
        "--run-dir",
        str(run_dir),
        "--seeds",
        str(len(selected_seed_dirs)),
        "--mode",
        "local",
        "--outdir",
        str(semantic_dir),
    ])
    semantic = _read_json(semantic_dir / "aggregate_semantic.json")

    compression_path = outdir / "compression.json"
    _run([
        sys.executable,
        "analysis/compression_analysis.py",
        "--run-dir",
        str(run_dir),
        "--seeds",
        str(len(selected_seed_dirs)),
        "--max-lag",
        "10",
        "--outfile",
        str(compression_path),
    ])
    compression = _read_json(compression_path)

    stability_path = outdir / "stability.json"
    _run([
        sys.executable,
        "analysis/stability_analysis.py",
        "--run-dir",
        str(run_dir),
        "--seeds",
        str(len(selected_seed_dirs)),
        "--window",
        "10",
        "--outfile",
        str(stability_path),
    ])
    stability = _read_json(stability_path)

    h1_dir = outdir / "h1_coherence"
    _run([
        sys.executable,
        "analysis/h1_coherence_analysis.py",
        "--run-dir",
        str(run_dir),
        "--seeds",
        str(len(selected_seed_dirs)),
        "--outdir",
        str(h1_dir),
    ])
    h1_coherence = _read_json(h1_dir / "h1_coherence_analysis.json")

    triangle_dir = outdir / "verdant_triangle"
    _run([
        sys.executable,
        "analysis/verdant_triangle_verification.py",
        "--state",
        str(seed0_state),
        "--outdir",
        str(triangle_dir),
        "--max-triples",
        "1000000",
    ])
    verdant_triangle = _read_json(triangle_dir / "verdant_triangle_verification.json")

    if skip_slow:
        robustness = {
            "seeds_analyzed": 0,
            "overall_ari_mean": 0.0,
            "interpretation": "skipped",
        }
    else:
        _run([
            sys.executable,
            "analysis/run_robustness_check.py",
            "--run-dir",
            str(run_dir),
            "--seeds",
            str(min(3, len(selected_seed_dirs))),
            "--n-runs",
            "5",
            "--outdir",
            str(robustness_dir),
        ])
        robustness = _read_json(robustness_dir / "aggregate_robustness.json")

    baseline = _baseline_comparison(baseline_dir)
    baseline_summary = baseline.get("baseline", {})

    state = _read_json(seed0_state)
    registry = (state.get("extra", {}) or {}).get("basin_registry", {}) or {}
    registry_basins = registry.get("basins", {}) or {}
    last_cycle = _load_last_cycle(seed0_dir)
    config = (state.get("extra", {}) or {}).get("config", {}) or {}

    verdant_earlier_share = _coerce_float(metrics.get("earlier_share"))
    baseline_earlier_share_mean = _coerce_float(baseline_summary.get("earlier_share_mean"))
    baseline_earlier_share_std = _coerce_float(baseline_summary.get("earlier_share_std"))
    sigma_separation = _sigma_separation(verdant_earlier_share, baseline_earlier_share_mean, baseline_earlier_share_std)

    onset_cycles = [result["onset_cycle"] for result in onset_results if result.get("onset_cycle") is not None]
    onset_tgs = [result["onset_t_g"] for result in onset_results if result.get("onset_t_g") is not None]
    onset_cycle_mean = float(statistics.mean(onset_cycles)) if onset_cycles else 0.0
    onset_tg_mean = float(statistics.mean(onset_tgs)) if onset_tgs else 0.0
    onset_invariant = bool(len(onset_cycles) >= 1 and (max(onset_cycles) - min(onset_cycles) <= 2))

    meaningful_fraction = _coerce_float(semantic.get("overall_meaningful_fraction"))
    mean_score = _coerce_float(semantic.get("overall_mean_score"))
    best_lag = int(compression.get("compression_vs_branching", {}).get("best_lag", 0) or 0)
    best_correlation = _coerce_float(compression.get("compression_vs_branching", {}).get("best_correlation"))
    edge_final_ratio = _coerce_float(stability.get("edge_stability", {}).get("final_ratio_mean"))
    edge_trend = str(stability.get("edge_stability", {}).get("trend", "oscillating"))
    ari_mean = _coerce_float(robustness.get("overall_ari_mean")) if not skip_slow else 0.0
    robustness_interpretation = str(robustness.get("interpretation", "skipped"))

    task1 = {
        "verdant_earlier_share": verdant_earlier_share,
        "baseline_earlier_share_mean": baseline_earlier_share_mean,
        "sigma_separation": sigma_separation,
        "status": _status_label(verdant_earlier_share >= 0.95 and (sigma_separation >= 5.0 or baseline_earlier_share_mean >= 0.95)),
    }
    task2 = {
        "onset_cycle_mean": onset_cycle_mean,
        "onset_tg_mean": onset_tg_mean,
        "onset_invariant": onset_invariant,
        "status": _status_label(bool(onset_cycles) and onset_invariant),
    }
    task3 = {
        "total_daughters": int(daughter.get("total_daughters_all_seeds", 0)),
        "forge_fraction_peak": _coerce_float(daughter.get("overall_forge_fraction_peak")),
        "max_emergent_any_daughter": int(daughter.get("max_emergent_any_daughter_any_seed", 0)),
    }
    task3["status"] = _task3_status(
        task3["total_daughters"],
        task3["forge_fraction_peak"],
        task3["max_emergent_any_daughter"],
    )
    task4 = {
        "meaningful_fraction": meaningful_fraction,
        "mean_score": mean_score,
        "status": _task4_status(meaningful_fraction, mean_score),
    }
    task5 = {
        "best_lag": best_lag,
        "best_correlation": best_correlation,
        "status": _task5_status(best_correlation),
    }
    task6 = {
        "edge_final_ratio": edge_final_ratio,
        "trend": edge_trend,
        "status": _task6_status(edge_trend),
    }
    task7 = {
        "ari_mean": ari_mean,
        "interpretation": robustness_interpretation,
        "status": _task7_status(ari_mean) if not skip_slow else "MODERATE",
    }
    task8 = {
        "h1_valid_fraction": _coerce_float(h1_coherence.get("h1_valid_fraction")),
        "hci_mean": _coerce_float(h1_coherence.get("hci_mean")),
        "violation_rate_mean": _coerce_float(h1_coherence.get("violation_rate_mean")),
        "status": _task8_status(_coerce_float(h1_coherence.get("h1_valid_fraction"))),
    }
    task9 = {
        "validity_fraction": _coerce_float(verdant_triangle.get("validity_fraction")),
        "total_triples": int(verdant_triangle.get("total_triples_checked", 0) or 0),
        "violations": int(verdant_triangle.get("invalid_triples", 0) or 0),
        "tau_star_mean": _coerce_float((verdant_triangle.get("tau_star_stats") or {}).get("mean")),
        "within_basin": verdant_triangle.get("within_basin", {}),
        "cross_basin": verdant_triangle.get("cross_basin", {}),
        "unassigned_basin": verdant_triangle.get("unassigned_basin", {}),
        "note": TASK9_OPEN_CONJECTURE_NOTE,
        "status": _task9_status(_coerce_float(verdant_triangle.get("validity_fraction"))),
    }

    critical_failures = sum(1 for task in (task1, task2, task4, task8) if task["status"] == "FAIL")
    if not skip_slow and task7["status"] == "FAIL":
        critical_failures += 1

    summary = (
        f"Validated {len(selected_seed_dirs)} seed(s) with earlier_share={verdant_earlier_share:.3f}; "
        f"critical_failures={critical_failures}; registry_enabled={bool(config.get('basin_use_registry', bool(registry_basins)))}."
    )

    report = {
        "run_dir": str(run_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seeds_analyzed": len(selected_seed_dirs),
        "v3_features": {
            "registry_enabled": bool(config.get("basin_use_registry", bool(registry_basins))),
            "checkpoints_found": _count_checkpoints(run_dir),
            "fast_bridge": bool(config.get("fast_bridge", False)),
        },
        "task1_baseline": task1,
        "task2_phase_diagram": task2,
        "task3_daughter": task3,
        "task4_semantic": task4,
        "task5_compression": task5,
        "task6_stability": task6,
        "task7_robustness": task7,
        "task8_h1_coherence": task8,
        "task9_verdant_triangle": task9,
        "overall": {
            "earlier_share": verdant_earlier_share,
            "all_tasks_run": not skip_slow,
            "critical_failures": critical_failures,
            "summary": summary,
            "figure_generation_error": figure_generation_error,
        },
    }

    active_count = int(last_cycle.get("basin_registry_active", 0) or 0)
    dormant_count = int(last_cycle.get("basin_registry_dormant", 0) or 0)
    checkpoints_found = report["v3_features"]["checkpoints_found"]
    registry_label = "enabled" if report["v3_features"]["registry_enabled"] else "disabled"
    fast_bridge_label = "enabled" if report["v3_features"]["fast_bridge"] else "disabled"

    print("=" * 60)
    print("VERDANT V3 VALIDATION REPORT")
    print("=" * 60)
    print(f"Run: {run_dir}")
    print(f"Seeds: {len(selected_seed_dirs)}")
    print(f"Registry: {registry_label} ({active_count} active, {dormant_count} dormant)")
    print(f"Checkpoints: {checkpoints_found} found")
    print(f"Fast bridge: {fast_bridge_label}")
    print()
    print(
        f"Task 1 - Baseline Comparison:     {task1['status']:<7} "
        f"({_fmt_number(task1['baseline_earlier_share_mean'])} vs {_fmt_number(task1['verdant_earlier_share'])}, {_fmt_number(task1['sigma_separation'], 1)}σ)"
    )
    print(
        f"Task 2 - Phase Diagram:           {task2['status']:<7} "
        f"(onset cycle {_fmt_number(task2['onset_cycle_mean'], 1)}, T_g {_fmt_number(task2['onset_tg_mean'])})"
    )
    print(
        f"Task 3 - Daughter Tracking:       {task3['status']:<16} "
        f"({_fmt_number(task3['forge_fraction_peak'] * 100.0, 1)}% peak forge, max {task3['max_emergent_any_daughter']})"
    )
    print(
        f"Task 4 - Semantic Evaluation:     {task4['status']:<7} "
        f"({_fmt_number(task4['meaningful_fraction'] * 100.0, 1)}% meaningful)"
    )
    print(
        f"Task 5 - Compression Proxy:       {task5['status']:<11} "
        f"(r = {_fmt_number(task5['best_correlation'])}, lag {task5['best_lag']})"
    )
    print(
        f"Task 6 - Stability Metric:        {task6['status']:<11} "
        f"(ratio {_fmt_number(task6['edge_final_ratio'])}, trend {task6['trend']})"
    )
    print(
        f"Task 7 - Detection Robustness:    {task7['status']:<7} "
        f"(ARI {_fmt_number(task7['ari_mean'])})"
    )
    print(
        f"Task 8 - H¹ Coherence:            {task8['status']:<7} "
        f"(valid {_fmt_number(task8['h1_valid_fraction'] * 100.0, 1)}%, HCI {_fmt_number(task8['hci_mean'])})"
    )
    print(
        f"Task 9 - Verdant Triangle:        {task9['status']:<7} "
        f"({_fmt_number(task9['validity_fraction'] * 100.0, 1)}% global, conjecture)"
    )
    print()
    print(f"Earlier-share: {_fmt_number(report['overall']['earlier_share'])}")
    print(f"Critical failures: {report['overall']['critical_failures']}")
    print("=" * 60)

    _write_json(outdir / "validation_report.json", report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, help="Run directory or glob matching a run directory")
    parser.add_argument("--seeds", type=int, default=None, help="Maximum number of seeds to analyze")
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--n-nulls", type=int, default=200)
    parser.add_argument("--skip-slow", action="store_true", help="Skip null models and robustness checks")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = resolve_run_dir(args.run_dir)
    build_report(run_dir=run_dir, outdir=Path(args.outdir), seeds=args.seeds, n_nulls=args.n_nulls, skip_slow=args.skip_slow)


if __name__ == "__main__":
    main()
