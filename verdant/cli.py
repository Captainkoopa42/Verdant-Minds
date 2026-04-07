from __future__ import annotations

import argparse

from verdant.adapters import DummySensorAdapter
from verdant.daemon import VerdantDaemon
from verdant.system import VerdantSystem


def main() -> None:
    parser = argparse.ArgumentParser(description="Verdant Minds CLI")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="Run finite cultivation cycles")
    run.add_argument("--cycles", type=int, default=50)
    run.add_argument("--checkpoint", default=None)

    daemon = sub.add_parser("daemon", help="Run persistent kernel loop")
    daemon.add_argument("--interval", type=float, default=0.5)
    daemon.add_argument("--checkpoint-dir", default=None)
    daemon.add_argument("--log-level", default="INFO")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    system = VerdantSystem()
    system.register_adapter(DummySensorAdapter())

    if args.command == "run":
        for _ in range(max(0, args.cycles)):
            system.run_cycle()
        if args.checkpoint:
            system.save_state(args.checkpoint)
        return

    if args.command == "daemon":
        VerdantDaemon(
            system,
            interval=max(0.0, args.interval),
            checkpoint_dir=args.checkpoint_dir,
            log_level=args.log_level,
        ).run()


if __name__ == "__main__":
    main()
