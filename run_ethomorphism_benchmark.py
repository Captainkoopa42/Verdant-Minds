from __future__ import annotations

import argparse
import json
from pathlib import Path

from verdant_benchmarks.ethomorphism import BenchmarkConfig
from verdant_benchmarks.ethomorphism_oracle_free import EthomorphismBenchmarkHarness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the oracle-free Verdant Milestone 19 Ethomorphism benchmark.")
    parser.add_argument("--output", default="artifacts/milestone_19_benchmark_summary.json")
    parser.add_argument("--seed", type=int, default=1901)
    parser.add_argument("--state-dim", type=int, default=16)
    parser.add_argument("--noise-concepts", type=int, default=16)
    args = parser.parse_args()

    config = BenchmarkConfig(seed=args.seed, state_dim=args.state_dim, noise_concepts=args.noise_concepts)
    summary = EthomorphismBenchmarkHarness(config).run()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(summary.to_json(), encoding="utf-8")
    print(summary.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
