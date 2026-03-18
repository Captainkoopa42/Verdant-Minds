"""Shared helpers for post-hoc telemetry analyses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np


EPSILON = 1e-6


def resolve_run_dir(spec: str) -> Path:
    """Resolve a concrete run directory from a path or glob-like spec."""
    path = Path(spec)
    if "*" not in spec:
        return path
    matches = sorted(Path().glob(spec))
    if not matches:
        raise FileNotFoundError(f"No run directory matches: {spec}")
    return matches[-1]


def load_cycles(path: Path) -> list[dict[str, Any]]:
    """Load JSONL cycle telemetry rows."""
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def iter_seed_cycles(run_dir: Path, seeds: int) -> Iterable[tuple[int, Path, list[dict[str, Any]]]]:
    """Yield `(seed, path, rows)` for seed directories with cycles telemetry."""
    for seed in range(seeds):
        cycles_path = run_dir / f"seed_{seed}" / "cycles.jsonl"
        if not cycles_path.exists():
            continue
        rows = load_cycles(cycles_path)
        if rows:
            yield seed, cycles_path, rows


def to_int(value: Any, default: int = 0) -> int:
    """Best-effort integer conversion for telemetry values."""
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def to_float(value: Any, default: float | None = None) -> float | None:
    """Best-effort float conversion for telemetry values."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_corr(x: list[float], y: list[float]) -> float:
    """Return Pearson correlation or NaN when undefined."""
    if len(x) != len(y) or len(x) < 2:
        return float("nan")
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if np.allclose(x_arr, x_arr[0]) or np.allclose(y_arr, y_arr[0]):
        return float("nan")
    return float(np.corrcoef(x_arr, y_arr)[0, 1])


def lagged_correlations(source: list[float], target: list[float], max_lag: int) -> list[float]:
    """Correlate `source[t]` with `target[t + lag]` for lags 0..max_lag."""
    corrs: list[float] = []
    for lag in range(max_lag + 1):
        if lag == 0:
            xs = source
            ys = target
        else:
            xs = source[:-lag]
            ys = target[lag:]
        corrs.append(safe_corr(xs, ys))
    return corrs


def interpolate_series(values: list[float | None]) -> list[float]:
    """Fill missing values by linear interpolation with edge extension."""
    if not values:
        return []
    xs = np.arange(len(values), dtype=float)
    known_idx = np.array([i for i, val in enumerate(values) if val is not None], dtype=float)
    if known_idx.size == 0:
        return [0.0 for _ in values]
    known_vals = np.array([float(values[int(i)]) for i in known_idx], dtype=float)
    interpolated = np.interp(xs, known_idx, known_vals)
    return [float(v) for v in interpolated]


def mean_std_by_position(series: list[list[float]]) -> tuple[list[float], list[float]]:
    """Compute position-wise mean/std over same-length numeric series."""
    if not series:
        return [], []
    arr = np.asarray(series, dtype=float)
    return np.nanmean(arr, axis=0).tolist(), np.nanstd(arr, axis=0).tolist()


def linear_slope(values: list[float]) -> float:
    """Fit a simple linear slope across equally spaced samples."""
    if len(values) < 2:
        return 0.0
    y = np.asarray(values, dtype=float)
    x = np.arange(len(values), dtype=float)
    return float(np.polyfit(x, y, 1)[0])


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON payload with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
