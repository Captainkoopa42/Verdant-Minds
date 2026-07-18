#!/usr/bin/env python3
"""Count node/edge totals from a Verdant state file.

Uses ijson for true streaming when available. Falls back to stdlib json with
an explicit warning when ijson is not installed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


NODE_KEYS = ("nodes", "concepts")
EDGE_KEYS = ("edges", "relations", "links")


def _count_with_ijson(state_path: Path) -> tuple[int, int]:
    import ijson  # type: ignore

    nodes = 0
    edges = 0
    with state_path.open("rb") as handle:
        for key in NODE_KEYS:
            for _ in ijson.items(handle, f"{key}.item"):
                nodes += 1
            handle.seek(0)
        for key in EDGE_KEYS:
            for _ in ijson.items(handle, f"{key}.item"):
                edges += 1
            handle.seek(0)
    return nodes, edges


def _count_with_stdlib(state_path: Path) -> tuple[int, int]:
    payload: dict[str, Any] = json.loads(state_path.read_text(encoding="utf-8"))

    def _length(keys: tuple[str, ...]) -> int:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
        return 0

    return _length(NODE_KEYS), _length(EDGE_KEYS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Count nodes and edges in Verdant state JSON")
    parser.add_argument("--state", type=Path, required=True, help="Path to persisted state JSON")
    args = parser.parse_args()

    method = "ijson(streaming)"
    try:
        nodes, edges = _count_with_ijson(args.state)
    except ModuleNotFoundError:
        method = "stdlib(json.load fallback)"
        print("[warn] ijson not installed; falling back to full JSON load.")
        print("[hint] Install streaming parser via: pip install ijson")
        nodes, edges = _count_with_stdlib(args.state)

    print(json.dumps({"nodes": nodes, "edges": edges, "method": method}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
