from __future__ import annotations

import argparse
import json

from verdant_benchmarks.q_evaluation import (
    QEvaluationConfig,
    QEvaluationHarness,
    write_evaluation_bundle,
)


def _integers(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the controlled Verdant Q evaluation campaign.")
    parser.add_argument("--output-dir", default="artifacts/q_evaluation")
    parser.add_argument("--seeds", default="1701,1901,2903,3907,4909,5903")
    parser.add_argument("--baseline-seeds", default="1901,2903")
    args = parser.parse_args()
    config = QEvaluationConfig(
        seeds=_integers(args.seeds),
        baseline_seeds=_integers(args.baseline_seeds),
    )
    result = QEvaluationHarness(config).run()
    write_evaluation_bundle(args.output_dir, result)
    print(json.dumps(result["aggregate"], indent=2, sort_keys=True))
    print(f"Scientific SHA-256: {result['scientific_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

