#!/usr/bin/env python3
"""Canonical Verdant Minds V4 runner.

The former Colab runner carried runtime monkey patches for checkpoint path
propagation, shard thaw recovery/LRU sizing, graph cache synchronization, council
persistence, and mitosis defaults. Those behaviors now live in importable
``verdant`` modules; this script is intentionally a thin operational entry point.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from verdant.system import VerdantSystem

MITOSIS_CAPS = {
    "force": {"max_nodes_per_shard": 128, "max_edges_per_shard": 4000},
    "watch": {"max_nodes_per_shard": 450, "max_edges_per_shard": 16000},
    "safe": {"max_nodes_per_shard": 10000, "max_edges_per_shard": 250000},
}

def configure_mitosis(system: VerdantSystem, mode: str = "watch", lru_cache_size: int = 8) -> None:
    defaults = system.memory_web.manifest.setdefault("defaults", {})
    defaults.update(MITOSIS_CAPS[mode])
    defaults.setdefault("thaw_penalty", 0.35)
    defaults.setdefault("thaw_threshold", 0.12)
    defaults.setdefault("noise_floor", 0.01)
    defaults["lru_cache_size"] = lru_cache_size

def build_parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(description="Run Verdant Minds V4")
    p.add_argument("--checkpoint", default="verdant_latest.json")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--input", default="trust care justice")
    p.add_argument("--mitosis-mode", choices=sorted(MITOSIS_CAPS), default="watch")
    p.add_argument("--dry-run", action="store_true", help="load/configure/report without saving")
    return p

def main(argv: list[str] | None = None) -> int:
    args=build_parser().parse_args(argv)
    system=VerdantSystem(); checkpoint=Path(args.checkpoint)
    if args.resume and checkpoint.exists(): system.load_state(str(checkpoint))
    configure_mitosis(system,args.mitosis_mode)
    system.process_input(args.input)
    metrics=system.get_metrics()
    print(json.dumps({"checkpoint":str(checkpoint),"metrics":metrics}, indent=2))
    if not args.dry_run: system.save_state(str(checkpoint))
    return 0
if __name__ == "__main__": raise SystemExit(main())
