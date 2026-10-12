"""Explicit freeze/replay of an unanswered operand-order protocol."""
from __future__ import annotations

import argparse
import json

from .protocol import (freeze_operand_order_protocol, load_operand_order_protocol,
                       protocol_summary, save_operand_order_protocol)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("freeze", "replay"):
        command = commands.add_parser(name)
        command.add_argument("protocol_path")
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            envelope = freeze_operand_order_protocol()
            save_operand_order_protocol(args.protocol_path, envelope)
        else:
            envelope = load_operand_order_protocol(args.protocol_path)
        print(json.dumps(protocol_summary(envelope), sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(json.dumps(dict(status="invalid", error=str(exc)), sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
