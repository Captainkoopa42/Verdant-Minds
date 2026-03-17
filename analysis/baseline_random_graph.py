#!/usr/bin/env python3
"""Build a timestamped random-growth baseline graph in Verdant state format."""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


SEEDED_CONCEPTS: list[str] = [
    "identity", "continuity", "selfhood", "persistence", "transformation", "boundary", "reflection",
    "recursive_self_reference", "ego_dissolution", "memory", "forgetting", "anticipation", "recollection",
    "temporal_flow", "present_moment", "pattern_history", "experience_accumulation", "consciousness", "qualia",
    "awareness", "subjective_experience", "perception", "attention", "phenomenology", "inner_observer",
    "emergence", "complexity", "self_organization", "phase_transition", "criticality", "threshold", "cascade",
    "resonance", "interference_pattern", "ethics", "justice", "autonomy", "beneficence", "harm", "integrity",
    "trust", "responsibility", "moral_weight", "value_conflict", "reasoning", "inference", "abstraction",
    "analogy", "contradiction", "paradox", "uncertainty", "hypothesis", "coherence", "belief_revision",
    "entropy", "energy", "equilibrium", "dissipation", "order", "chaos", "temperature", "phase", "wave",
    "interference", "superposition", "connection", "influence", "feedback", "coupling", "dependency", "network",
    "hierarchy", "emergence_from_interaction", "meaning", "symbol", "reference", "interpretation", "ambiguity",
    "translation", "expression", "silence", "unsayable",
]

WORD_BANK: list[str] = [
    "lumen", "thread", "echo", "fractal", "ripple", "axiom", "vessel", "glyph", "prism", "orbit",
    "signal", "weave", "pulse", "arc", "delta", "field", "node", "chorus", "matrix", "spark",
]


@dataclass
class BaselineConfig:
    """Runtime configuration for baseline graph generation."""

    cycles: int = 80
    seed: int = 0
    emergent_rate: float = 1.0
    connections_per_emergent: int = 5
    extra_edges_per_cycle: int = 3


def _rand_weight(rng: random.Random) -> float:
    return round(rng.uniform(0.3, 1.0), 6)


def _new_label(rng: random.Random) -> str:
    return f"Emergent_{rng.choice(WORD_BANK)}_{rng.choice(WORD_BANK)}_{rng.getrandbits(24):06x}"


def build_baseline_state(config: BaselineConfig) -> dict[str, Any]:
    """Build a random timestamped growth graph in Verdant-compatible state schema."""

    py_rng = random.Random(config.seed)
    np_rng = np.random.default_rng(config.seed)

    memory_store: dict[str, dict[str, Any]] = {}
    edges: list[list[Any]] = []

    for index, concept in enumerate(SEEDED_CONCEPTS):
        created_at = float(index)
        memory_store[concept] = {
            "stability": round(py_rng.uniform(0.7, 0.9), 6),
            "connections": [],
            "access_count": py_rng.randint(1, 10),
            "created_at": created_at,
            "first_seen": created_at,
            "metadata": {"created_at": created_at},
        }

    for cycle in range(config.cycles):
        n_new = min(2, int(np_rng.poisson(config.emergent_rate)))
        base_ts = cycle * 10.0
        offsets = sorted(py_rng.uniform(0.0, 9.999) for _ in range(n_new))

        for offset in offsets:
            node = _new_label(py_rng)
            while node in memory_store:
                node = _new_label(py_rng)
            created_at = base_ts + offset
            memory_store[node] = {
                "stability": round(py_rng.uniform(0.4, 0.85), 6),
                "connections": [],
                "access_count": 0,
                "created_at": created_at,
                "first_seen": created_at,
                "metadata": {"created_at": created_at},
            }

            existing = [name for name in memory_store if name != node]
            k = min(max(1, config.connections_per_emergent), len(existing))
            for target in py_rng.sample(existing, k=k):
                weight = _rand_weight(py_rng)
                memory_store[node]["connections"].append([target, weight])
                edges.append([node, target, weight])

        nodes = list(memory_store)
        if len(nodes) >= 2:
            for _ in range(config.extra_edges_per_cycle):
                src, dst = py_rng.sample(nodes, k=2)
                weight = _rand_weight(py_rng)
                memory_store[src]["connections"].append([dst, weight])
                edges.append([src, dst, weight])

    return {
        "memory_web": {
            "memory_store": memory_store,
            "edges": edges,
        },
        "extra": {"last_basins": []},
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line args."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=80)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--emergent-rate", type=float, default=1.0)
    parser.add_argument("--connections-per-emergent", type=int, default=5)
    parser.add_argument("--extra-edges-per-cycle", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint."""

    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    config = BaselineConfig(
        cycles=args.cycles,
        seed=args.seed,
        emergent_rate=args.emergent_rate,
        connections_per_emergent=args.connections_per_emergent,
        extra_edges_per_cycle=args.extra_edges_per_cycle,
    )
    state = build_baseline_state(config)
    output_path = args.outdir / "state.json"
    output_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
