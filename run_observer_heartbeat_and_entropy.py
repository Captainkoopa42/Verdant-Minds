"""Observer-only heartbeat profile and Tg-input trace.

This script measures. It has no behavioral authority and changes no source
file, policy, or checkpoint. It builds a disposable kernel, feeds it a seeded
synthetic curriculum through the ordinary ``VerdantDevelopmentPipeline``, and
reports two things:

``profile``
    Wall time per developmental cycle as the organism grows, with inclusive
    time spent in named kernel/pipeline operations and the size of the state
    being carried.

``entropy``
    The four Tg inputs (h_sys, c_input, c_memory, h_env) and Tg itself for
    every cycle, plus a comparison statistic for h_sys against the value a
    field of independent random phasors would produce.

``regimes``
    Alternating blocks of *focused* experience (one domain repeated) and
    *scattered* experience (a random domain every cycle). Reports whether
    h_sys separates the two, next to one observer-only candidate statistic:
    the effective number of concepts ringing in the present field. The
    candidate is telemetry for comparison. It is not Tg, not a proposed
    replacement formula, and has no behavioral authority.

Timing wrappers are installed on classes only for the lifetime of this
process. Wall-clock values are descriptive, not reproducible measurements.
The synthetic curriculum is not a cognition benchmark.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from cognitive_chunk_v2.translators import TextTranslator
from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import EvidenceKind, ExperienceCommand, RelationProposal, VerdantKernel
from verdant_plasticity import VerdantPlasticityPipeline
from verdant_structures import VerdantStructurePipeline
from verdant_thermodynamics import VerdantThermodynamicObserver
from verdant_workspace import VerdantWorkspacePipeline

SCHEMA = "verdant.observer.heartbeat_and_entropy.v0"


def synthetic_curriculum(
    *, seed: int, domains: int, members: int, repeats: int
) -> list[ExperienceCommand]:
    """Seeded, shuffled primitive-edge curriculum with real text features."""
    translator = TextTranslator()
    rng = random.Random(seed)
    rows: list[tuple[int, int, int]] = []
    for repeat in range(repeats):
        for domain in range(domains):
            for edge in range(members - 1):
                rows.append((repeat, domain, edge))
    rng.shuffle(rows)
    commands: list[ExperienceCommand] = []
    for index, (repeat, domain, edge) in enumerate(rows):
        left = f"d{domain:03d}_c{edge}"
        right = f"d{domain:03d}_c{edge + 1}"
        sentence = f"{left} linked {right}"
        event_key = f"observer:{index:06d}:{left}:{right}:r{repeat}"
        features = translator.translate(sentence.encode("utf-8")).features
        commands.append(
            ExperienceCommand(
                event_key=event_key,
                source_ref="observer:synthetic-curriculum",
                modality="text",
                payload_sha256=hashlib.sha256(
                    (event_key + sentence).encode("utf-8")
                ).hexdigest(),
                feature_vector=tuple(float(value) for value in features),
                concept_labels=(left, right),
                relation_proposals=(
                    RelationProposal(
                        source_label=left,
                        target_label=right,
                        relation_type="linked",
                        directed=False,
                        weight=0.8,
                        confidence=1.0,
                    ),
                ),
                confidence=1.0,
                semantic_evidence_kind=EvidenceKind.TESTIMONY,
                semantic_evidence_details={"observer_synthetic_edge": True},
                metadata={
                    "sentence": sentence,
                    "context_id": f"d{domain:03d}:context:{repeat % 2}",
                },
            )
        )
    return commands


class _Timers:
    def __init__(self) -> None:
        self.seconds: dict[str, float] = defaultdict(float)
        self.calls: dict[str, int] = defaultdict(int)
        self._restore: list[tuple[type, str, object]] = []

    def wrap(self, owner: type, name: str, label: str) -> None:
        original = getattr(owner, name)

        @functools.wraps(original)
        def timed(*args, **kwargs):
            started = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                self.seconds[label] += time.perf_counter() - started
                self.calls[label] += 1

        self._restore.append((owner, name, owner.__dict__[name]))
        setattr(owner, name, timed)

    def restore(self) -> None:
        for owner, name, original in reversed(self._restore):
            setattr(owner, name, original)
        self._restore.clear()

    def take(self) -> tuple[dict[str, float], dict[str, int]]:
        seconds, calls = dict(self.seconds), dict(self.calls)
        self.seconds.clear()
        self.calls.clear()
        return seconds, calls


def _state_sizes(kernel: VerdantKernel) -> dict[str, int]:
    state = kernel.state
    return {
        "concepts": len(state.concepts),
        "evidence": len(state.evidence),
        "relations": len(state.relations),
        "field_history_frames": len(state.field.history),
        "transitions": len(state.transitions),
        "resonance_events": len(state.resonance_events),
        "workspace_cycle_events": len(state.workspace_cycle_events),
        "plasticity_events": len(state.plasticity_events),
        "plasticity_associations": len(state.plasticity_associations),
        "structure_candidates": len(state.structure_candidates),
    }


def run_profile(args: argparse.Namespace) -> dict:
    commands = synthetic_curriculum(
        seed=args.seed, domains=args.domains, members=args.members, repeats=args.repeats
    )[: args.cycles]
    kernel = VerdantKernel(seed=args.seed, state_dim=args.state_dim, run_label="observer-profile")
    pipeline = VerdantDevelopmentPipeline()
    timers = _Timers()
    # Inclusive timings. Nested operations overlap by design: for example
    # _validate_state runs inside apply_experience and every commit.
    timers.wrap(VerdantKernel, "snapshot", "kernel.snapshot (deep copy)")
    timers.wrap(VerdantKernel, "_validate_state", "kernel._validate_state")
    timers.wrap(VerdantKernel, "fingerprint", "kernel.fingerprint")
    timers.wrap(VerdantKernel, "semantic_fingerprint", "kernel.semantic_fingerprint")
    timers.wrap(VerdantKernel, "field_fingerprint", "kernel.field_fingerprint")
    timers.wrap(VerdantKernel, "apply_experience", "stage.apply_experience")
    timers.wrap(VerdantKernel, "inspect_resonance", "stage.inspect_resonance")
    timers.wrap(VerdantKernel, "commit_resonance", "stage.commit_resonance")
    timers.wrap(VerdantWorkspacePipeline, "run_cycle", "stage.workspace")
    timers.wrap(VerdantPlasticityPipeline, "run_cycle", "stage.plasticity")
    timers.wrap(VerdantStructurePipeline, "run_cycle", "stage.structures")
    windows: list[dict] = []
    try:
        window_seconds = 0.0
        window_start = 0
        for index, command in enumerate(commands, start=1):
            started = time.perf_counter()
            pipeline.advance(kernel, command)
            window_seconds += time.perf_counter() - started
            if index % args.window == 0 or index == len(commands):
                count = index - window_start
                seconds, calls = timers.take()
                windows.append(
                    {
                        "cycles": f"{window_start + 1}-{index}",
                        "mean_ms_per_heartbeat": 1000.0 * window_seconds / count,
                        "inclusive_ms_per_heartbeat": {
                            key: 1000.0 * value / count for key, value in sorted(seconds.items())
                        },
                        "calls_per_heartbeat": {
                            key: value / count for key, value in sorted(calls.items())
                        },
                        "state": _state_sizes(kernel),
                        "state_json_bytes": len(kernel.state.model_dump_json()),
                    }
                )
                window_seconds = 0.0
                window_start = index
    finally:
        timers.restore()
    return {
        "schema": SCHEMA,
        "mode": "profile",
        "config": vars(args) | {"func": None},
        "heartbeats": len(commands),
        "final_fingerprint": kernel.state.fingerprint(),
        "windows": windows,
        "wall_clock_is_descriptive_only": True,
    }


def run_entropy(args: argparse.Namespace) -> dict:
    commands = synthetic_curriculum(
        seed=args.seed, domains=args.domains, members=args.members, repeats=args.repeats
    )[: args.cycles]
    kernel = VerdantKernel(seed=args.seed, state_dim=args.state_dim, run_label="observer-entropy")
    pipeline = VerdantDevelopmentPipeline()
    observer = VerdantThermodynamicObserver()
    previous = None
    rows: list[dict] = []
    for command in commands:
        result = pipeline.advance(kernel, command)
        before = kernel.fingerprint()
        state = observer.inspect(
            kernel,
            command,
            candidate_scope_count=len(result.candidate_scope_ids),
            workspace_report=result.workspace.report if result.workspace else None,
            previous=previous,
        )
        if kernel.fingerprint() != before:
            raise RuntimeError("Thermodynamic observation mutated canonical state.")
        previous = state
        rows.append(
            {
                "cycle": state.cycle,
                "h_sys": state.h_sys,
                "c_input": state.c_input,
                "c_memory": state.c_memory,
                "h_env": state.h_env,
                "entropy_feedback": state.entropy_feedback,
                "t_g": state.t_g,
                "phase": state.phase.value,
            }
        )

    def summary(name: str) -> dict:
        values = [row[name] for row in rows]
        return {
            "min": min(values),
            "max": max(values),
            "mean": statistics.fmean(values),
            "stdev": statistics.pstdev(values),
            "range": max(values) - min(values),
        }

    dim = args.state_dim
    # If the D per-dimension powers behaved like independent exponential
    # variables (a sum of random phasors), the expected Shannon entropy is
    # about log(D) - (1 - Euler gamma). This is a reference value only.
    random_phasor_reference = (
        (math.log(dim) - (1.0 - 0.5772156649015329)) / math.log(dim) if dim > 1 else 0.0
    )
    phases: dict[str, int] = defaultdict(int)
    for row in rows:
        phases[row["phase"]] += 1
    return {
        "schema": SCHEMA,
        "mode": "entropy",
        "config": vars(args) | {"func": None},
        "heartbeats": len(rows),
        "summary": {name: summary(name) for name in ("h_sys", "c_input", "c_memory", "h_env", "entropy_feedback", "t_g")},
        "h_sys_random_phasor_reference": random_phasor_reference,
        "phase_counts": dict(sorted(phases.items())),
        "rows": rows,
        "behavioral_authority": False,
    }


def effective_present_concepts(kernel: VerdantKernel) -> float:
    """Participation count of concept addresses in the normalized field.

    Each address's squared alignment with the field has an expected chance
    value of 1/state_dim for an unrelated random address; that floor is
    subtracted before taking (sum p)^2 / sum p^2. Pure inspection.
    """
    field = np.asarray(kernel.state.field.real) + 1j * np.asarray(kernel.state.field.imag)
    norm = float(np.linalg.norm(field))
    if norm <= 1e-15 or not kernel.state.field_addresses:
        return 0.0
    field = field / norm
    floor = 1.0 / kernel.state.field.state_dim
    powers = np.asarray(
        [
            abs(np.vdot(np.asarray(item.real) + 1j * np.asarray(item.imag), field)) ** 2
            for _key, item in sorted(kernel.state.field_addresses.items())
        ]
    )
    signal = np.clip(powers - floor, 0.0, None)
    denominator = float(np.sum(signal**2))
    return float(np.sum(signal) ** 2 / denominator) if denominator > 0.0 else 0.0


def run_regimes(args: argparse.Namespace) -> dict:
    from verdant_thermodynamics.metrics import field_entropy

    pool = synthetic_curriculum(
        seed=args.seed, domains=args.domains, members=args.members, repeats=max(args.repeats, 40)
    )
    by_domain: dict[str, list[ExperienceCommand]] = defaultdict(list)
    for command in pool:
        by_domain[command.concept_labels[0].split("_")[0]].append(command)
    domains = sorted(by_domain)
    rng = random.Random(args.seed + 1)
    kernel = VerdantKernel(seed=args.seed, state_dim=args.state_dim, run_label="observer-regimes")
    pipeline = VerdantDevelopmentPipeline()
    rows: list[dict] = []
    blocks = max(2, args.cycles // args.window)
    for block in range(blocks):
        regime = "focused" if block % 2 == 0 else "scattered"
        for position in range(args.window):
            domain = domains[block % len(domains)] if regime == "focused" else rng.choice(domains)
            if not by_domain[domain]:
                continue
            pipeline.advance(kernel, by_domain[domain].pop())
            before = kernel.fingerprint()
            row = {
                "cycle": kernel.state.cycle,
                "regime": regime,
                "position_in_block": position,
                "h_sys": field_entropy(kernel).h_sys,
                "effective_present_concepts": effective_present_concepts(kernel),
                "concepts": len(kernel.state.concepts),
            }
            if kernel.fingerprint() != before:
                raise RuntimeError("Regime observation mutated canonical state.")
            rows.append(row)

    def stats(regime: str, name: str) -> dict:
        # The first quarter of each block is excluded as carry-over from the
        # previous regime (field retention spans several experiences).
        values = [
            row[name] for row in rows
            if row["regime"] == regime and row["position_in_block"] >= args.window // 4
        ]
        return {"n": len(values), "mean": statistics.fmean(values), "stdev": statistics.pstdev(values)}

    summary = {
        name: {regime: stats(regime, name) for regime in ("focused", "scattered")}
        for name in ("h_sys", "effective_present_concepts")
    }
    for name, item in summary.items():
        pooled = math.sqrt((item["focused"]["stdev"] ** 2 + item["scattered"]["stdev"] ** 2) / 2.0)
        item["separation_in_pooled_stdevs"] = (
            abs(item["focused"]["mean"] - item["scattered"]["mean"]) / pooled if pooled > 0 else 0.0
        )
    return {
        "schema": SCHEMA,
        "mode": "regimes",
        "config": vars(args) | {"func": None},
        "heartbeats": len(rows),
        "summary": summary,
        "rows": rows,
        "behavioral_authority": False,
        "candidate_statistic_is_not_tg": True,
    }


def _print_regimes(report: dict) -> None:
    print(f"heartbeats: {report['heartbeats']}")
    for name, item in report["summary"].items():
        print(
            f"  {name:<27} focused {item['focused']['mean']:.4f}+-{item['focused']['stdev']:.4f}  "
            f"scattered {item['scattered']['mean']:.4f}+-{item['scattered']['stdev']:.4f}  "
            f"separation {item['separation_in_pooled_stdevs']:.2f} pooled stdevs"
        )


def _print_profile(report: dict) -> None:
    print(f"heartbeats: {report['heartbeats']}   final fingerprint (reference): {report['final_fingerprint']}")
    labels = sorted({k for w in report["windows"] for k in w["inclusive_ms_per_heartbeat"]})
    for window in report["windows"]:
        state = window["state"]
        print(
            f"\ncycles {window['cycles']}: {window['mean_ms_per_heartbeat']:.1f} ms/heartbeat | "
            f"state {window['state_json_bytes'] / 1e6:.2f} MB | concepts {state['concepts']} | "
            f"field frames {state['field_history_frames']} | transitions {state['transitions']}"
        )
        for label in labels:
            ms = window["inclusive_ms_per_heartbeat"].get(label, 0.0)
            calls = window["calls_per_heartbeat"].get(label, 0.0)
            print(f"    {label:<34} {ms:8.1f} ms  ({calls:.1f} calls)")


def _print_entropy(report: dict) -> None:
    print(f"heartbeats: {report['heartbeats']}   phases: {report['phase_counts']}")
    print(f"h_sys reference for independent random phasors: {report['h_sys_random_phasor_reference']:.4f}")
    for name, item in report["summary"].items():
        print(
            f"  {name:<17} mean {item['mean']:.4f}  stdev {item['stdev']:.4f}  "
            f"min {item['min']:.4f}  max {item['max']:.4f}  range {item['range']:.4f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("mode", choices=("profile", "entropy", "regimes"))
    parser.add_argument("--seed", type=int, default=2301)
    parser.add_argument("--state-dim", type=int, default=128)
    parser.add_argument("--domains", type=int, default=30)
    parser.add_argument("--members", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=6)
    parser.add_argument("--cycles", type=int, default=600)
    parser.add_argument("--window", type=int, default=100)
    parser.add_argument("--out", type=Path, default=None, help="Exclusive-create JSON report path.")
    parser.add_argument(
        "--accelerate",
        action="store_true",
        help="Opt in to the byte-exact fingerprint accelerator for this process.",
    )
    args = parser.parse_args()
    if args.accelerate:
        from sidecar_acceleration import install_fingerprint_cache

        install_fingerprint_cache()
    runner = {"profile": run_profile, "entropy": run_entropy, "regimes": run_regimes}[args.mode]
    printer = {"profile": _print_profile, "entropy": _print_entropy, "regimes": _print_regimes}[args.mode]
    report = runner(args)
    report["config"] = {k: (str(v) if isinstance(v, Path) else v) for k, v in report["config"].items() if k != "func"}
    printer(report)
    if args.out is not None:
        with open(args.out, "x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
