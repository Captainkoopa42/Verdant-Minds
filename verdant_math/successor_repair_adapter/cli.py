"""Freeze or replay terminal-successor adapter bytes without running its cohort."""
from __future__ import annotations

import argparse
import json

from .adapter import (
    adapter_summary,
    freeze_successor_repair_adapter,
    load_successor_repair_adapter,
    save_successor_repair_adapter,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("freeze", "replay"):
        command = commands.add_parser(name)
        command.add_argument("protocol_path")
        command.add_argument("implementation_path")
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            envelope = freeze_successor_repair_adapter(args.protocol_path)
            save_successor_repair_adapter(args.protocol_path, args.implementation_path, envelope)
        else:
            envelope = load_successor_repair_adapter(args.protocol_path, args.implementation_path)
        print(json.dumps(adapter_summary(envelope), sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(json.dumps(dict(status="invalid", error=str(exc)), sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
