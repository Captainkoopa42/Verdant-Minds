import argparse


def main():
    parser = argparse.ArgumentParser(description="Verdant Minds CLI")

    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="Run cultivation cycles")
    run.add_argument("--cycles", type=int, default=50)
    run.add_argument("--outdir", default="./output")

    sub.add_parser("daemon", help="Run persistent kernel loop")

    args = parser.parse_args()

    if args.command == "run":
        print(f"🚀 Running {args.cycles} cycles → {args.outdir}")
    elif args.command == "daemon":
        print("♾️ Starting Verdant daemon...")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
