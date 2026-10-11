"""Explicit addition teaching pilot; run writes a separate immutable result."""
from __future__ import annotations

import argparse
import json

from .teaching_pilot import (
    AdditionProblem, _ROLES, recall_addition_fact, restore_math_teaching_arm,
    load_math_teaching_pilot, math_teaching_summary,
    run_math_teaching_pilot, save_math_teaching_pilot,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "replay", "query"):
        command = commands.add_parser(name)
        command.add_argument("path")
        if name == "query":
            command.add_argument("--left", type=int, required=True)
            command.add_argument("--right", type=int, required=True)
            command.add_argument("--role", choices=_ROLES, default="taught")
    args = parser.parse_args(argv)
    try:
        if args.command in ("replay", "query"):
            envelope = load_math_teaching_pilot(args.path)
        else:
            envelope = run_math_teaching_pilot()
            save_math_teaching_pilot(args.path, envelope)
        if args.command == "query":
            problem = AdditionProblem(left=args.left, right=args.right)
            kernel = restore_math_teaching_arm(envelope, args.role)
            reply = recall_addition_fact(kernel, problem)
            result = dict(status="math_fact_reply", role=args.role,
                problem=problem.model_dump(mode="json"), reply=reply.model_dump(mode="json"),
                source_authenticated=False, generalized_arithmetic_claim_permitted=False,
                physical_evidence_admissible=False, canonical_commit_permitted=False)
        else:
            result = math_teaching_summary(envelope)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(json.dumps(dict(status="invalid", error=str(exc)), sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
