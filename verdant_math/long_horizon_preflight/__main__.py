"""Native 1,000-cycle feasibility pilot for long-horizon retention.

This is a diagnostic precursor, NOT the proposed 12,000-cycle curriculum:
it studies persistence and direct fact recall only. Its training is explicit
human testimony; the responder never performs arithmetic or self-repair.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from cognitive_chunk_v2 import ExperienceInput, PipelineOrchestrator
from verdant_claims import ClaimLearningPipeline
from verdant_kernel import (
    ClaimPolarity, ClaimSourceClass, EvidenceKind, ExperienceCommand,
    VerdantKernel, checkpoint_bytes,
)
from verdant_kernel.checkpoint import load_checkpoint_bytes
from verdant_kernel.models import canonical_json_bytes
from verdant_math.teaching_pilot import AdditionProblem, recall_addition_fact

VERSION = "native_long_horizon_preflight_v0.1"
ROLES = ("progressive", "rehearsal", "activity_control", "delayed")
SEEDS = (79066, 79067, 79068)
TRAIN = ((5, 0), (5, 1), (5, 2), (6, 0), (6, 1),
         (6, 2), (7, 0), (7, 1))
REVERSED = ((0, 5), (1, 5), (2, 5), (0, 6), (1, 6),
            (2, 6), (0, 7), (1, 7))
NOVEL = ((8, 0), (8, 1), (9, 0), (9, 1))
PROBLEMS = tuple(("trained", p) for p in TRAIN) + tuple(
    ("reversed", p) for p in REVERSED) + tuple(("novel", p) for p in NOVEL)
PROBES = (0, 250, 500, 750, 1000)
_SLOTS = (25, 75, 125, 175, 225, 275, 325, 375)
_LATE_SLOTS = (625, 675, 725, 775, 825, 875, 925, 975)


class PreflightError(RuntimeError):
    """A persistence, identity, or evidence boundary failed."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(payload: dict) -> bytes:
    return canonical_json_bytes(payload)


def _atomic_new(path: Path, data: bytes) -> None:
    """Never overwrite a committed cohort artifact, including on replay."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.with_suffix(path.suffix + ".part").exists():
        raise PreflightError(f"Experiment output already exists: {path}")
    tmp = path.with_suffix(path.suffix + ".part")
    with open(tmp, "xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
    if os.name == "posix":
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def lesson_for(role: str, cycle: int):
    """Human-supplied native claim, never inferred from a held-out answer."""
    if role == "progressive" and cycle in _SLOTS:
        return TRAIN[_SLOTS.index(cycle)]
    if role == "rehearsal" and cycle in _SLOTS:
        return TRAIN[0]
    if role == "delayed" and cycle in _LATE_SLOTS:
        return TRAIN[_LATE_SLOTS.index(cycle)]
    return None


def _teach(kernel: VerdantKernel, *, key: str, pair: tuple[int, int]) -> str:
    a, b = pair
    result = ClaimLearningPipeline().record_claim(
        kernel,
        event_key=key,
        native_description=f"Teacher says {a} plus {b} equals {a + b}.",
        subject_label=f"math:sum:left:{a}:right:{b}",
        predicate="math_sum_equals",
        object_label=f"math:integer:{a + b}",
        polarity=ClaimPolarity.AFFIRMED,
        source_class=ClaimSourceClass.HUMAN_TESTIMONY,
        source_ref="declared-long-horizon-preflight-teacher://v0.1",
        rationale="Teacher-supplied fact for private retention feasibility only.",
    ).kernel_result
    if not result.transition_id or not result.claim_ids:
        raise PreflightError("Native teaching did not produce a traceable claim transition.")
    return result.transition_id


def _unrelated_experience(kernel: VerdantKernel, *, key: str, cycle: int) -> str:
    """A real native experience transition, NOT an assertion of learning."""
    source = "long-horizon-preflight-unrelated://v0.1"
    words = f"Unrelated orientation practice event number {cycle}: no mathematics claim or answer supplied."
    chunk, store = PipelineOrchestrator().process(
        ExperienceInput.from_text(words, source_id=source, source_name=f"{key}.txt"))
    payload, translation = chunk.payloads[0], chunk.translations[0]
    result = kernel.apply_experience(ExperienceCommand(
        event_key=key,
        source_ref=source,
        modality="text",
        payload_sha256=payload.source_sha256,
        feature_vector=tuple(float(x) for x in store.get_array(
            translation.feature_ref).reshape(-1)),
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"source_class": "human_testimony", "answer_supplied": False},
        metadata={"event_type": "unrelated_interference", "epistemic_status": "no_math_answer"},
    ))
    if not result.transition_id or result.claim_ids:
        raise PreflightError("Interference must be native but must not install mathematical claims.")
    return result.transition_id


def _probe(kernel: VerdantKernel, *, cycle: int) -> dict:
    before = kernel.fingerprint()
    entries = []
    for split, (a, b) in PROBLEMS:
        reply = recall_addition_fact(kernel, AdditionProblem(left=a, right=b))
        entries.append({
            "split": split, "left": a, "right": b,
            "reply": reply.model_dump(mode="json"),
        })
    if kernel.fingerprint() != before:
        raise PreflightError("A read-only retention probe modified native state.")
    return {"cycle": cycle, "fingerprint": before, "responses": entries}


def _checkpoint(kernel: VerdantKernel, path: Path) -> VerdantKernel:
    raw = checkpoint_bytes(kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint_bytes(raw))
    if (restored.fingerprint() != kernel.fingerprint()
            or checkpoint_bytes(restored.snapshot()) != raw):
        raise PreflightError("Native checkpoint was not exactly reloadable.")
    _atomic_new(path, raw)
    return restored


def execute(output_dir: str | Path, *, cycles: int = 1000,
            seeds: tuple[int, ...] = SEEDS) -> Path:
    """Write immutable ungraded responses after executing every private arm."""
    if not isinstance(cycles, int) or isinstance(cycles, bool) or not 0 <= cycles <= 1000:
        raise ValueError("Preflight supports only 0..1000 native cycles; 12000 is NOT implemented.")
    if (not seeds or len(set(seeds)) != len(seeds)
            or any(isinstance(s, bool) or not isinstance(s, int) or s < 0 for s in seeds)):
        raise ValueError("Seeds must be distinct nonnegative integers.")
    root = Path(output_dir)
    if root.exists():
        raise PreflightError("Output directory already exists; refusing overwrite/resume.")
    root.mkdir(parents=True)
    ordered_probes = tuple(c for c in PROBES if c <= cycles)
    if cycles not in ordered_probes:
        ordered_probes += (cycles,)
    results = []
    for seed in seeds:
        pristine = VerdantKernel(seed=seed, state_dim=16,
                                run_label=f"long-horizon-preflight-seed-{seed}")
        source_fingerprint = pristine.fingerprint()
        snapshot = pristine.snapshot()
        for role in ROLES:
            kernel = VerdantKernel.from_state(snapshot)
            first_fingerprint = kernel.fingerprint()
            if first_fingerprint != source_fingerprint:
                raise PreflightError("Private role did not start from identical native seed.")
            kernel = _checkpoint(kernel, root / f"seed-{seed}" / role / "cycle-00000.vdk")
            observations = [_probe(kernel, cycle=0)]
            teaching = []
            transitions = []
            for cycle in range(1, cycles + 1):
                key = f"lh-v01:seed:{seed}:role:{role}:cycle:{cycle}"
                before_cycle = kernel.state.cycle
                pair = lesson_for(role, cycle)
                transition = (_teach(kernel, key=key, pair=pair) if pair is not None
                              else _unrelated_experience(kernel, key=key, cycle=cycle))
                if kernel.state.cycle != before_cycle + 1:
                    raise PreflightError("Every charged event must produce exactly one native cycle.")
                transitions.append(transition)
                if pair is not None:
                    teaching.append({"cycle": cycle, "pair": list(pair),
                                     "transition_id": transition})
                if cycle in ordered_probes:
                    kernel = _checkpoint(kernel,
                        root / f"seed-{seed}" / role / f"cycle-{cycle:05d}.vdk")
                    observations.append(_probe(kernel, cycle=cycle))
            if kernel.fingerprint() != kernel.snapshot().fingerprint():
                raise PreflightError("Checkpoint and live kernel disagree.")
            if pristine.fingerprint() != source_fingerprint:
                raise PreflightError("The initial kernel was mutated.")
            results.append({
                "seed": seed, "role": role, "initial_fingerprint": source_fingerprint,
                "final_fingerprint": kernel.fingerprint(), "native_cycles": cycles,
                "teaching": teaching, "transition_ids_sha256": digest(_json({"ids": transitions})),
                "probes": observations,
            })
    payload = {
        "version": VERSION, "purpose": "native_persistence_and_direct_recall_feasibility",
        "cycles_per_arm": cycles, "seeds": list(seeds),
        "roles": list(ROLES), "probe_cycles": list(ordered_probes),
        "training_pairs": [list(p) for p in TRAIN],
        "test_pairs": [{"split": split, "pair": list(p)} for split, p in PROBLEMS],
        "no_autonomous_learning_claim": True, "canonical_commit_permitted": False,
        "grading_performed": False, "arms": results,
    }
    path = root / "responses.json"
    _atomic_new(path, _json(payload))
    return path


def grade(response_path: str | Path, grade_path: str | Path) -> Path:
    """Offline grade: source response bytes must already be durable."""
    source = Path(response_path)
    raw = source.read_bytes()
    data = json.loads(raw)
    if (data.get("version") != VERSION or data.get("grading_performed") is not False
            or _json(data) != raw):
        raise PreflightError("Response file is not the canonical ungraded preflight batch.")
    seen = set()
    grading = []
    for arm in data["arms"]:
        identity = (arm["seed"], arm["role"])
        if identity in seen:
            raise PreflightError("Duplicate private arm.")
        seen.add(identity)
        probes = []
        for p in arm["probes"]:
            records = []
            if len(p["responses"]) != len(PROBLEMS):
                raise PreflightError("Missing probe case.")
            for item, (split, pair) in zip(p["responses"], PROBLEMS):
                if (item["split"], item["left"], item["right"]) != (split, *pair):
                    raise PreflightError("Changed response case order.")
                reply = item["reply"]
                answer = reply["answer"]
                verdict = ("abstained" if answer is None else
                           "correct" if answer == sum(pair) else "incorrect")
                records.append(verdict)
            probes.append({"cycle": p["cycle"], "correct": records.count("correct"),
                           "incorrect": records.count("incorrect"),
                           "abstained": records.count("abstained"), "total": len(records)})
        grading.append({"seed": identity[0], "role": identity[1], "probes": probes})
    if seen != {(s, role) for s in data["seeds"] for role in ROLES}:
        raise PreflightError("Missing expected arms.")
    output = {
        "version": VERSION, "response_sha256": digest(raw),
        "counts_include_all_probes": True, "grading": grading,
        "interpretation": "only direct factual retention, not long-range general learning",
    }
    destination = Path(grade_path)
    _atomic_new(destination, _json(output))
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    run = commands.add_parser("pilot", help="Run private native feasibility pilot")
    run.add_argument("output_dir")
    run.add_argument("--cycles", type=int, default=1000)
    score = commands.add_parser("grade", help="Grade already-durable response batch")
    score.add_argument("response_path")
    score.add_argument("grade_path")
    args = parser.parse_args(argv)
    result = (execute(args.output_dir, cycles=args.cycles) if args.action == "pilot"
              else grade(args.response_path, args.grade_path))
    print(result)


if __name__ == "__main__":
    main()
