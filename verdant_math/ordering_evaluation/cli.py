"""Run or replay the exact frozen operand-order evaluation."""
from __future__ import annotations

import argparse
import json

from .evaluation import (
    capture_operand_order_responses,
    evaluate_response_batch,
    evaluation_summary,
    load_evaluation,
    load_response_batch,
    save_evaluation,
    save_response_batch,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "replay"):
        command = commands.add_parser(name)
        command.add_argument("protocol_path")
        command.add_argument("implementation_path")
        command.add_argument("response_path")
        command.add_argument("result_path")
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            batch = capture_operand_order_responses(args.protocol_path, args.implementation_path)
            save_response_batch(args.protocol_path, args.implementation_path,
                args.response_path, batch)
            evaluation = evaluate_response_batch(args.protocol_path,
                args.implementation_path, args.response_path)
            save_evaluation(args.protocol_path, args.implementation_path,
                args.response_path, args.result_path, evaluation)
        else:
            batch = load_response_batch(args.protocol_path, args.implementation_path,
                args.response_path)
            evaluation = load_evaluation(args.protocol_path, args.implementation_path,
                args.response_path, args.result_path)
        print(json.dumps(evaluation_summary(batch, evaluation), sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(json.dumps(dict(status="invalid", error=str(exc)), sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
