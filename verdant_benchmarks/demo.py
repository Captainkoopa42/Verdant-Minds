from __future__ import annotations

import json
from pathlib import Path

from .ethomorphism import BenchmarkConfig, EthomorphismBenchmarkHarness


def run_demo(output_dir: str | Path = "artifacts") -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    harness = EthomorphismBenchmarkHarness(BenchmarkConfig())
    summary = harness.run()
    payload = summary.to_dict()
    (output / "milestone_19_benchmark_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return payload


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, sort_keys=True))
