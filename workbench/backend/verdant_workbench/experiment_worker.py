from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict

from verdant_benchmarks import ArmName, BenchmarkConfig, EthomorphismBenchmarkHarness


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("arm", "full"), required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--arm")
    args = parser.parse_args()
    config = BenchmarkConfig(**json.loads(args.config))
    harness = EthomorphismBenchmarkHarness(config)
    if args.mode == "full":
        summary = harness.run().to_dict()
        print(json.dumps({"worker_pid": os.getpid(), "summary": summary}, sort_keys=True))
        return 0
    if not args.arm:
        parser.error("--arm is required for arm mode")
    arm = ArmName(args.arm)
    runtime = harness.train_arm(arm)
    payload = {
        "worker_pid": os.getpid(),
        "arm": arm.value,
        "arm_metrics": asdict(harness.evaluate_arm(runtime)),
    }
    if arm == ArmName.D_FULL:
        payload["causal_controls"] = asdict(harness.causal_controls(runtime))
        payload["refolding"] = asdict(harness.refolding_control())
        payload["health"] = asdict(harness.long_run_health(arm))
    elif arm == ArmName.C_PLASTIC:
        payload["health"] = asdict(harness.long_run_health(arm))
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
