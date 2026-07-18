#!/usr/bin/env python3
"""Phase-diagram parameter sweeps for developmental onset."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cultivation.runner import CultivationRunner, RunnerConfig
# TODO: migrate verdant imports to verdant for V3
from verdant import system as verdant_system
from verdant.ethomorphic_config import EthomorphicParams, SWEEPABILITY

from analysis.detect_onset import detect_onset
from analysis.seed_sets import get_seed_set


DEFAULT_SWEEP_VALUES: dict[str, list[float | int]] = {
    "seed_count": [20, 40, 60, 82, 100, 120],
    "pressure_threshold": [0.0001, 0.001, 0.01, 0.1, 0.5],
    "cognitive_dims": [2, 3, 4, 5, 6, 8],
    "ethical_dims": [2, 3, 4, 5, 6, 8],
    "entropy_window_min": [0.3, 0.5, 0.8, 1.0, 1.5],
    "entropy_window_max": [2.0, 2.5, 3.0, 4.0, 5.0],
    "magnitude_threshold": [0.05, 0.10, 0.15, 0.20, 0.30],
    "adaptive_rate": [0.02, 0.05, 0.075, 0.10, 0.15],
    "basin_prune_interval": [10, 15, 20, 25, 30],
    "basin_bud_interval": [10, 15, 20, 25, 30],
}

PARAMETER_METADATA: dict[str, dict[str, Any]] = {
    "seed_count": {"kind": "seed_count", "field": None, "sweepability": None},
    "pressure_threshold": {"kind": "runner", "field": "basin_pressure_threshold", "sweepability": None},
    "basin_prune_interval": {"kind": "runner", "field": "basin_prune_interval", "sweepability": None},
    "basin_bud_interval": {"kind": "runner", "field": "basin_bud_interval", "sweepability": None},
    "cognitive_dims": {"kind": "ethomorphic", "field": "num_cognitive_dims", "sweepability": "num_cognitive_dims"},
    "ethical_dims": {"kind": "ethomorphic", "field": "num_ethical_dims", "sweepability": "num_ethical_dims"},
    "entropy_window_min": {"kind": "ethomorphic", "field": "emergence_entropy_min", "sweepability": "emergence_entropy_min"},
    "entropy_window_max": {"kind": "ethomorphic", "field": "emergence_entropy_max", "sweepability": "emergence_entropy_max"},
    "magnitude_threshold": {"kind": "ethomorphic", "field": "emergence_magnitude_threshold", "sweepability": "emergence_magnitude_threshold"},
    "adaptive_rate": {"kind": "ethomorphic", "field": "adaptive_rate", "sweepability": "adaptive_rate"},
}

SUPPORTED_PARAMS = set(PARAMETER_METADATA)


def _parse_values(raw: str) -> list[float | int]:
    values: list[float | int] = []
    for token in [x.strip() for x in raw.split(",") if x.strip()]:
        if "." in token or "e" in token.lower():
            values.append(float(token))
        else:
            values.append(int(token))
    return values


def _seeded_concepts_from_names(names: list[str]) -> list[tuple[str, float, dict[str, str]]]:
    return [(name, 0.75, {"domain": "Phase Sweep"}) for name in names]


def _copy_seed_outputs(run_dir: Path, config_dir: Path, seeds_per_config: int) -> list[Path]:
    cycles_paths: list[Path] = []
    for seed in range(seeds_per_config):
        src = run_dir / f"seed_{seed}"
        dst = config_dir / f"seed_{seed}"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        cycles_paths.append(dst / "cycles.jsonl")
    return cycles_paths


def _safe_stats(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return mean(values), (pstdev(values) if len(values) > 1 else 0.0)


def _runner_config_for_value(
    parameter: str,
    value: float | int,
    *,
    cycles_per_run: int,
    run_container: Path,
) -> RunnerConfig:
    base_kwargs: dict[str, Any] = {
        "cycles": cycles_per_run,
        "provider": "local",
        "outdir": str(run_container),
        "basin_routing": True,
        "enable_pruning": True,
        "enable_budding": True,
        "enable_boundary_emergence": True,
        "boundary_use_ecwf": True,
        "density_regulation_enabled": True,
    }
    meta = PARAMETER_METADATA[parameter]
    if meta["kind"] == "runner" and meta["field"] is not None:
        base_kwargs[str(meta["field"])] = value
    elif meta["kind"] == "ethomorphic" and meta["field"] is not None:
        base_kwargs["ethomorphic_params"] = EthomorphicParams(**{str(meta["field"]): value})
    return RunnerConfig(**base_kwargs)


def is_parameter_sweepable(parameter: str) -> tuple[bool, str]:
    meta = PARAMETER_METADATA.get(parameter)
    if meta is None:
        return False, f"Unknown parameter {parameter!r}."
    key = meta.get("sweepability")
    if key is None:
        return True, "Sweepable via existing Verdant runner configuration."
    record = SWEEPABILITY[key]
    if record.sweepable:
        return True, record.reason
    return False, record.reason


def run_sweep(
    parameter: str,
    values: list[float | int],
    cycles_per_run: int,
    seeds_per_config: int,
    outdir: Path,
) -> dict[str, Any]:
    sweepable, reason = is_parameter_sweepable(parameter)
    outdir.mkdir(parents=True, exist_ok=True)
    sweep_dir = outdir / f"sweep_{parameter}"
    sweep_dir.mkdir(parents=True, exist_ok=True)

    if not sweepable:
        message = f"Parameter {parameter} is not sweepable without modifying ethomorphic/. Skipping."
        payload = {
            "parameter": parameter,
            "values": values,
            "results": [],
            "skipped": True,
            "skip_reason": f"{message} {reason}",
        }
        (sweep_dir / "sweep_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(message)
        return payload

    original_seeded = list(verdant_system._SEEDED_CONCEPTS)
    results: list[dict[str, Any]] = []

    try:
        for value in values:
            config_dir = sweep_dir / f"config_{value}"
            run_container = config_dir / "_raw_runs"
            run_container.mkdir(parents=True, exist_ok=True)

            if parameter == "seed_count":
                seed_names = get_seed_set(int(value))
                verdant_system._SEEDED_CONCEPTS = _seeded_concepts_from_names(seed_names)

            cfg = _runner_config_for_value(
                parameter,
                value,
                cycles_per_run=cycles_per_run,
                run_container=run_container,
            )
            runner = CultivationRunner(cfg)
            run_dir = runner.run(range(seeds_per_config))

            cycles_files = _copy_seed_outputs(run_dir, config_dir, seeds_per_config)
            onset_records: list[dict[str, Any]] = []
            for idx, cycles_file in enumerate(cycles_files):
                onset = detect_onset(str(cycles_file))
                onset_records.append(onset)
                (config_dir / f"seed_{idx}" / "onset.json").write_text(
                    json.dumps(onset, indent=2),
                    encoding="utf-8",
                )

            onset_cycles = [float(x["onset_cycle"]) for x in onset_records if x["onset_cycle"] is not None]
            onset_tg = [float(x["onset_t_g"]) for x in onset_records if x["onset_t_g"] is not None]
            onset_mem = [float(x["onset_memory_size"]) for x in onset_records if x["onset_memory_size"] is not None]
            onset_emergent = [float(x["onset_emergent_count"]) for x in onset_records if x["onset_emergent_count"] is not None]

            cycle_mean, cycle_std = _safe_stats(onset_cycles)
            tg_mean, tg_std = _safe_stats(onset_tg)
            mem_mean, _ = _safe_stats(onset_mem)
            emergent_mean, _ = _safe_stats(onset_emergent)

            results.append(
                {
                    "value": value,
                    "onset_cycle_mean": cycle_mean,
                    "onset_cycle_std": cycle_std,
                    "onset_t_g_mean": tg_mean,
                    "onset_t_g_std": tg_std,
                    "onset_memory_mean": mem_mean,
                    "onset_emergent_mean": emergent_mean,
                    "onsets_found": len(onset_cycles),
                    "seeds_run": seeds_per_config,
                    "notes": reason,
                }
            )
    finally:
        verdant_system._SEEDED_CONCEPTS = original_seeded

    payload = {
        "parameter": parameter,
        "values": values,
        "results": results,
        "skipped": False,
        "sweep_reason": reason,
    }
    (sweep_dir / "sweep_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run phase-diagram sweeps for onset detection")
    parser.add_argument("--parameter", required=True, choices=sorted(SUPPORTED_PARAMS))
    parser.add_argument("--values", required=False, help="Comma-separated values")
    parser.add_argument("--cycles-per-run", type=int, default=40)
    parser.add_argument("--seeds-per-config", type=int, default=3)
    parser.add_argument("--outdir", default="outputs_phase_diagram_v3")
    args = parser.parse_args()

    values = _parse_values(args.values) if args.values else list(DEFAULT_SWEEP_VALUES[args.parameter])
    payload = run_sweep(args.parameter, values, args.cycles_per_run, args.seeds_per_config, Path(args.outdir))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
