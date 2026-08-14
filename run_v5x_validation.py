from __future__ import annotations

import argparse
from pathlib import Path

from verdant_benchmarks.v5x_validation import V5XValidationHarness


def main() -> int:
    parser = argparse.ArgumentParser(description="Verdant V5-X pre-merge validation harness")
    parser.add_argument("--seed", type=int, default=1901)
    parser.add_argument("--state-dim", type=int, default=16)
    parser.add_argument("--noise-concepts", type=int, default=0)
    parser.add_argument("--experiment", choices=("all", "m19", "thermodynamics", "lesions"), default="all")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-ref", default="V5-X", help="branch/commit label recorded in the validation package")
    parser.add_argument("--headless", action="store_true", help="accepted for batch-runner compatibility; this CLI is always headless")
    args = parser.parse_args()

    harness = V5XValidationHarness(seed=args.seed, state_dim=args.state_dim, noise_concepts=args.noise_concepts, source_ref=args.source_ref)
    payload = harness.run(experiment=args.experiment)
    path, sha_path = harness.write_package(payload, args.output)
    print(f"V5-X validation package: {path}")
    print(f"SHA-256 manifest: {sha_path}")
    print(f"validation_qualifies={payload['validation_qualifies']}")
    return 0 if payload["validation_qualifies"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
