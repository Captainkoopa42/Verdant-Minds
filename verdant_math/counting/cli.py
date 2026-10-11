"""Explicit successor/counting run, replay and private-memory query commands."""
from __future__ import annotations

import argparse
import json

from .pilot import (
    CountingRequest, _ROLES, count_forward, counting_summary, load_counting_pilot,
    restore_counting_arm, run_counting_pilot, save_counting_pilot,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "replay", "query"):
        command = commands.add_parser(name)
        command.add_argument("path")
        if name == "query":
            command.add_argument("--start", type=int, required=True)
            command.add_argument("--ticks", type=int, choices=range(5), required=True)
            command.add_argument("--role", choices=_ROLES, default="taught")
    args = parser.parse_args(argv)
    try:
        if args.command in ("replay", "query"):
            envelope = load_counting_pilot(args.path)
        else:
            envelope = run_counting_pilot()
            save_counting_pilot(args.path, envelope)
        if args.command == "query":
            request = CountingRequest(start=args.start, ticks=("tick",) * args.ticks)
            reply = count_forward(restore_counting_arm(envelope, args.role), request)
            result = dict(status="teacher_scaffold_counting_reply", role=args.role,
                request=request.model_dump(mode="json"), reply=reply.model_dump(mode="json"),
                instruction_discovery_observed=False, source_authenticated=False,
                generalized_arithmetic_claim_permitted=False, physical_evidence_admissible=False,
                canonical_commit_permitted=False)
        else:
            result = counting_summary(envelope)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(json.dumps(dict(status="invalid", error=str(exc)), sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
