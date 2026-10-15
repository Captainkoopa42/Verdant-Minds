"""Run or replay the exact frozen zero-new-lesson retention evaluation."""
from __future__ import annotations

import argparse
import json

from .evaluation import (
    capture_successor_retention_responses,
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
        command.add_argument("history_response_path")
        command.add_argument("history_evaluation_path")
        command.add_argument("response_path")
        command.add_argument("result_path")
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            batch = capture_successor_retention_responses(
                args.protocol_path,
                args.history_response_path,
                args.history_evaluation_path,
            )
            save_response_batch(
                args.protocol_path,
                args.history_response_path,
                args.history_evaluation_path,
                args.response_path,
                batch,
            )
            result = evaluate_response_batch(
                args.protocol_path,
                args.history_response_path,
                args.history_evaluation_path,
                args.response_path,
            )
            save_evaluation(
                args.protocol_path,
                args.history_response_path,
                args.history_evaluation_path,
                args.response_path,
                args.result_path,
                result,
            )
        else:
            batch = load_response_batch(
                args.protocol_path,
                args.history_response_path,
                args.history_evaluation_path,
                args.response_path,
            )
            result = load_evaluation(
                args.protocol_path,
                args.history_response_path,
                args.history_evaluation_path,
                args.response_path,
                args.result_path,
            )
        print(json.dumps(evaluation_summary(batch, result), sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
