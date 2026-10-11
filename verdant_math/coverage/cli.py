"""Explicit freeze, run and replay commands for the coverage challenge."""
from __future__ import annotations

import argparse
import json

from .challenge import (coverage_summary, freeze_coverage_plan, load_coverage_challenge,
                        run_coverage_challenge, save_coverage_challenge, save_coverage_plan)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("freeze", "run", "replay"):
        command = commands.add_parser(name)
        command.add_argument("plan_path")
        if name != "freeze":
            command.add_argument("result_path")
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            plan = freeze_coverage_plan()
            digest = save_coverage_plan(args.plan_path, plan)
            result = dict(status="frozen_coverage_plan", plan_sha256=plan.plan_sha256,
                          plan_file_sha256=digest, enrolled_per_role=32, execution_performed=False)
        else:
            if args.command == "run":
                envelope = run_coverage_challenge(args.plan_path)
                save_coverage_challenge(args.plan_path, args.result_path, envelope)
            else:
                envelope = load_coverage_challenge(args.plan_path, args.result_path)
            result = coverage_summary(envelope)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(json.dumps(dict(status="invalid", error=str(exc)), sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
