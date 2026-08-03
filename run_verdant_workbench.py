from __future__ import annotations

import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "workbench" / "backend"
for path in (ROOT, BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verdant Workbench 1.0.1 / V5 local laboratory")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Keep loopback unless you understand the security implications.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("VERDANT_WORKBENCH_PORT", "8765")))
    parser.add_argument("--home", default=os.environ.get("VERDANT_WORKBENCH_HOME", ".verdant-workbench"), help="Workbench project/artifact directory")
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--check", action="store_true", help="Run startup/integrity diagnostics and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.environ["VERDANT_WORKBENCH_HOME"] = str(Path(args.home).resolve())

    # Local runtime safety policy: historical Living Explorer reconstruction is
    # forensic work and must never monopolize the organism worker while the
    # developmental queue is actively cultivating.
    from verdant_workbench.runtime_stability import install_runtime_stability_patches
    install_runtime_stability_patches()

    if args.check:
        from verdant_workbench.run_service import DurableRunService
        service = DurableRunService(os.environ["VERDANT_WORKBENCH_HOME"])
        try:
            scan = service.integrity_scan()
            print("Verdant Workbench 1.0.1 / V5 diagnostic")
            print(f"home: {service.root}")
            print(f"recovered stale runs: {service.recovered_stale_runs}")
            print(f"providers: {len(service.list_providers())}")
            print(f"plugins: {len(service.list_plugins())}")
            from verdant_workbench.release_identity import source_build_identity
            build = source_build_identity()
            print(f"release: {build['release_id']}")
            print(f"engine source: {build['engine_source_sha256']}")
            print(f"workbench source: {build['workbench_source_sha256']}")
            print(f"dependency lock: {build['dependency_lock_sha256']}")
            print(f"artifacts: {scan['artifact_count']} verified={scan['all_ok']}")
            return 0 if scan["all_ok"] else 2
        finally:
            service.close()

    import uvicorn
    url = f"http://{args.host}:{args.port}/"
    print(f"Verdant Workbench 1.0.1 / V5: {url}")
    print(f"Workbench home: {os.environ['VERDANT_WORKBENCH_HOME']}")
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        print("WARNING: Workbench has no production authentication layer; non-loopback binding is not recommended.")
    if args.open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    uvicorn.run("verdant_workbench.app:app", host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
