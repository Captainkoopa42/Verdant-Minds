"""Tests for Verdant-side ethomorphic parameterization."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import fields
import time

import numpy as np

from verdant.ethomorphic_config import EthomorphicParams, SWEEPABILITY, params_report_rows
from verdant.system import VerdantConfig, VerdantSystem


@contextmanager
def deterministic_runtime(seed: int):
    """Stabilize time/default_rng for deterministic system comparisons."""

    real_time = time.time
    real_default_rng = np.random.default_rng
    tick = [0]
    rng_tick = [0]

    def fake_time() -> float:
        tick[0] += 1
        return float(seed) * 10_000.0 + tick[0] * 0.01

    def fake_default_rng(seed_arg: int | None = None):
        if seed_arg is not None:
            return real_default_rng(seed_arg)
        rng_tick[0] += 1
        return real_default_rng(seed * 10_000 + rng_tick[0])

    time.time = fake_time
    np.random.default_rng = fake_default_rng
    try:
        yield
    finally:
        time.time = real_time
        np.random.default_rng = real_default_rng


def _run_signature(config: VerdantConfig, *, cycles: int) -> list[dict[str, float | int]]:
    records: list[dict[str, float | int]] = []
    with deterministic_runtime(int(config.seed or 0)):
        system = VerdantSystem(config)
        for cycle in range(cycles):
            chunk = system.process_input(f"Cycle {cycle}: ethics identity emergence bridge")
            wave = chunk.get_section_content("wave_function_section") or {}
            metrics = system.get_metrics()
            records.append(
                {
                    "t_g": round(float(metrics["t_g"]), 6),
                    "memory_concepts": int(metrics["memory_concepts"]),
                    "emergent_nodes": int(metrics["emergent_nodes"]),
                    "entropy": round(float(wave.get("entropy", 0.0)), 6),
                }
            )
    return records


def test_default_params_match_current() -> None:
    baseline = _run_signature(VerdantConfig(seed=17), cycles=5)
    configured = _run_signature(
        VerdantConfig(seed=17, ethomorphic_params=EthomorphicParams()),
        cycles=5,
    )

    assert configured == baseline


def test_custom_dims() -> None:
    params = EthomorphicParams(num_cognitive_dims=3, num_ethical_dims=3)
    with deterministic_runtime(23):
        system = VerdantSystem(VerdantConfig(seed=23, ethomorphic_params=params))
        for cycle in range(5):
            system.process_input(f"Cycle {cycle}: custom dims")

    assert system.ecwf.num_cognitive_dims == 3
    assert system.ecwf.num_ethical_dims == 3
    assert system.bridge.ecwf.num_cognitive_dims == 3
    assert system.bridge.ecwf.num_ethical_dims == 3


def test_custom_entropy_window() -> None:
    params = EthomorphicParams(emergence_entropy_min=1.0, emergence_entropy_max=2.0)
    with deterministic_runtime(29):
        system = VerdantSystem(VerdantConfig(seed=29, ethomorphic_params=params))
        for cycle in range(10):
            chunk = system.process_input(f"Cycle {cycle}: narrower entropy window")

    memory_section = chunk.get_section_content("memory_section") or {}
    assert isinstance(memory_section.get("emergent_concepts", []), list)
    assert system.ethomorphic_params.emergence_entropy_min == 1.0
    assert system.ethomorphic_params.emergence_entropy_max == 2.0


def test_unsweepable_params_documented() -> None:
    report = params_report_rows()
    report_names = {row["name"] for row in report}

    for field in fields(EthomorphicParams):
        assert field.name in SWEEPABILITY
        assert field.name in report_names
        record = SWEEPABILITY[field.name]
        assert bool(record.reason)
        assert record.sweepable or record.mode == "locked"
