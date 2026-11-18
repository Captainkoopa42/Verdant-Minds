"""Observer: one continuous life, the same lessons for up to four organisms, measured as they age.

    python run_observer_long_life.py --lessons 2500 --arm all

That one command generates the life if it is not there yet, then runs each arm in turn.
Every arm is resumable: stop it at any time and run the same command again.

Arms (each adds one opt-in sidecar to the one before; no engine file is edited)
    stock        the engine as it is
    recurrence   + occurrences counted from the experience itself     (sidecar_recurrence)
    bond_clock   + decay on the bond's own clock                      (sidecar_bond_clock)
    full         + rehearsal beats                                    (sidecar_rehearsal)

Every arm promotes the same way: every 20 lessons, up to 4 candidates the engine itself
marks eligible go through the ordinary Council promotion, in candidate-id order. The
expectations file is opened only by the read-only scorer at checkpoints; it is never given
to a pipeline, and the scorer is checked not to change the fingerprint.

At each checkpoint, for families whose last lesson has already happened:
    kept      share of single-concept cues that recall exactly the family (the engine's own recall)
    promoted  share promoted to a P structure
    alive     share with at least one living bond
and, for the whole organism: wrong promotions (a P that is not one of the families that
meet every stated gate), cost per beat, and the fingerprint.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "workbench" / "backend"), str(REPO / "curriculum_packs")]

ARMS = ("stock", "recurrence", "bond_clock", "full")
EXTRA_ARMS = ("surprise", "surprise_wave", "reunion", "whole")
# surprise: full + measured surprise | reunion: + the two memories consulted together | whole: + wave + generic folding
SCHEMA = "verdant.observer.long_life.v0"


PIPELINE_CONFIG: dict = {}          # optional DevelopmentalCycleConfig overrides (e.g. current_evidence_persistence)


def build_pipeline(arm: str):
    from verdant_development import VerdantDevelopmentPipeline
    from verdant_structures import VerdantStructurePipeline
    stages = {}; structures = VerdantStructurePipeline()
    if PIPELINE_CONFIG:
        from verdant_development.pipeline import DevelopmentalCycleConfig
        stages["config"] = DevelopmentalCycleConfig(**PIPELINE_CONFIG)
    extra = arm in EXTRA_ARMS; name = arm
    if arm in ("surprise_wave", "whole"):
        from sidecar_wave import install_wave
        install_wave()
    if extra:
        arm = "full"
    if arm in ("recurrence", "bond_clock", "full"):
        from sidecar_recurrence import ExperienceRecurrenceStructurePipeline
        structures = ExperienceRecurrenceStructurePipeline(); stages["structures"] = structures
    if arm in ("bond_clock", "full"):
        from sidecar_bond_clock import BondClockPlasticityPipeline
        stages["plasticity"] = BondClockPlasticityPipeline()
    if extra:
        from sidecar_bond_clock import BondClockPlasticityPipeline
        from sidecar_surprise import SurpriseDevelopmentPipeline, surprise_plasticity
        plasticity = surprise_plasticity(BondClockPlasticityPipeline, reunion=name in ("reunion", "whole"))
        if name == "whole":
            from sidecar_fold import FoldingDevelopmentPipeline, folding_plasticity
            stages["plasticity"] = folding_plasticity(plasticity)()
            pipeline = FoldingDevelopmentPipeline(**stages)
        else:
            stages["plasticity"] = plasticity()
            pipeline = SurpriseDevelopmentPipeline(**stages)
    else:
        pipeline = VerdantDevelopmentPipeline(**stages)
    if arm == "full":
        from sidecar_rehearsal import RehearsalConfig, RehearsingDevelopmentPipeline
        pipeline = RehearsingDevelopmentPipeline(pipeline, RehearsalConfig(min_real_exposures=1))
    return pipeline, structures


def load_commands(pack_path: Path):
    from verdant_kernel import ExperienceCommand
    from verdant_workbench.curriculum import CurriculumCompiler, CurriculumCompileRequest, curriculum_pack_bundle_source
    text = pack_path.read_text(encoding="utf-8")
    pack, _bundle, _selected, _probes, source = curriculum_pack_bundle_source(text, ())
    compiled = CurriculumCompiler().compile(CurriculumCompileRequest(project_id="observer", title=pack.title,
                                            source_format="teaching_bundle_json", source_text=source, state_dim=pack.state_dim))
    return pack.state_dim, [ExperienceCommand.model_validate(c) for c in compiled.compiled_commands], hashlib.sha256(text.encode("utf-8")).hexdigest()


def promote_eligible(kernel, structures, limit: int, reify: bool = False) -> tuple[int, list[str]]:
    done, refused = 0, []
    for candidate_id, candidate in sorted(kernel.state.structure_candidates.items()):
        if done >= limit:
            break
        if candidate.status.value != "eligible":
            continue
        try:
            if reify:
                from sidecar_fold import promote_and_reify
                promote_and_reify(kernel, structures, candidate_id)
            else:
                structures.promote(kernel, candidate_id)
            done += 1
        except Exception as exc:                       # reported, never hidden
            refused.append(f"{type(exc).__name__}: {str(exc)[:80]}")
    return done, refused


def checkpoint_score(kernel, expectations: dict, lesson: int) -> dict:
    from verdant_compilation import VerdantCompilationPipeline
    state = kernel.state; recall = VerdantCompilationPipeline()
    label_of = {cid: c.label for cid, c in state.concepts.items()}; id_of = {v: k for k, v in label_of.items()}
    candidates = {frozenset(label_of[m] for m in c.member_concept_ids): c for c in state.structure_candidates.values()}
    from sidecar_fold import unfold   # a fold of folds is scored by everything it stands for
    promoted = [frozenset(label_of[m] for m in unfold(kernel, s.member_concept_ids)) for s in state.structures.values()]
    should_pass = {frozenset(f["members"]) for f in expectations["families"]
                   if f["expectation"].get("exact_candidate_promotion_eligible") is True}
    groups: dict[str, collections.Counter] = collections.OrderedDict()
    for family in expectations["families"]:
        if family["last_lesson"] > lesson:
            continue
        members = frozenset(family["members"]); row = groups.setdefault(family["group"], collections.Counter())
        row["families"] += 1
        cand = candidates.get(members)
        row["candidate"] += cand is not None
        row["eligible_or_promoted"] += cand is not None and cand.status.value in ("eligible", "promoted")
        row["promoted"] += members in promoted
        ids = {id_of[m] for m in members if m in id_of}
        row["alive"] += any(set(a.concept_ids) <= ids for a in state.plasticity_associations.values())
        for cue in sorted(members):
            row["cues"] += 1
            if cue in id_of:
                got = {label_of[c] for c in recall.inspect(kernel, [id_of[cue]]).reconstructed_concept_ids}
                row["kept"] += got == members
    distractors = frozenset(expectations["distractor_concepts"])
    return {"groups": {g: dict(v) for g, v in groups.items()},
            "wrong_promotions": [sorted(p) for p in promoted if p not in should_pass],
            "distractor_only_promotions": sum(1 for p in promoted if p <= distractors),
            "structures": len(state.structures), "candidates": len(state.structure_candidates),
            "concepts": len(state.concepts), "bonds": len(state.plasticity_associations), "evidence": len(state.evidence)}


READER = {"on": False}
SENSES = {"on": False}


def run_arm(arm: str, pack_path: Path, expect_path: Path, out_dir: Path, *, seed: int, checkpoint_every: int,
            promote_every: int, max_promotions: int, stop_after: int | None) -> None:
    from verdant_kernel import VerdantKernel
    from verdant_kernel.models import KernelState
    state_dim, commands, pack_sha = load_commands(pack_path)
    if READER["on"]:                                   # sidecar_reader: the reading organ also hands in each word's own look
        from sidecar_reader import attach, install_reader
        install_reader(); texts = {it["item_id"]: it["source_text"] for sec in json.loads(pack_path.read_text())["sections"] for it in sec["items"]}
        commands = [attach(c, texts[c.metadata["item_id"]]) if c.modality == "text" and c.metadata.get("item_id") in texts else c for c in commands]
    stem = pack_path.stem; log_path = out_dir / f"{stem}__{arm}.jsonl"; state_path = out_dir / f"{stem}__{arm}.state.json"
    done_path = out_dir / f"{stem}__{arm}.done.json"
    if done_path.exists():
        print(f"[{arm}] already finished ({done_path.name})"); return
    pipeline, structures = build_pipeline(arm)
    if state_path.exists():
        kernel = VerdantKernel.from_state(KernelState.model_validate_json(state_path.read_text(encoding="utf-8")))
        print(f"[{arm}] resuming at lesson {len(kernel.state.processed_event_keys)}", flush=True)
    else:
        kernel = VerdantKernel(seed=seed, state_dim=state_dim, run_label=f"long-life-{arm}")
        if SENSES["on"]:
            from sidecar_ring import carry_one_experience
            carry_one_experience(kernel)
        log_path.write_text("", encoding="utf-8")
    start = len(kernel.state.processed_event_keys); total = len(commands) if stop_after is None else min(len(commands), stop_after)
    window = time.perf_counter(); began = window; promoted_window = 0; refusals: list[str] = []
    for lesson in range(start + 1, total + 1):
        pipeline.advance(kernel, commands[lesson - 1])
        if lesson % promote_every == 0:
            count, refused = promote_eligible(kernel, structures, max_promotions, reify=arm == "whole"); promoted_window += count; refusals += refused
        if lesson % checkpoint_every == 0 or lesson == total:
            now = time.perf_counter(); beats = (lesson - 1) % checkpoint_every + 1 if lesson == total and lesson % checkpoint_every else checkpoint_every
            fingerprint = kernel.fingerprint()
            expectations = json.loads(expect_path.read_text(encoding="utf-8"))
            if expectations.get("pack_sha256") != pack_sha:
                raise SystemExit("Expectations file was generated for a different pack.")
            score = checkpoint_score(kernel, expectations, lesson)
            if kernel.fingerprint() != fingerprint:
                raise RuntimeError("Scoring changed canonical state.")
            row = {"schema": SCHEMA, "arm": arm, "lesson": lesson, "cycle": kernel.state.cycle,
                   "ms_per_beat": round(1000 * (now - window) / max(1, min(beats, lesson - start)), 1),
                   "promoted_in_window": promoted_window, "promotion_refusals": refusals[-3:], "fingerprint": fingerprint, **score}
            inner = getattr(pipeline, "inner", pipeline)
            if hasattr(inner, "surprise_log"):
                row["surprise"] = inner.surprise_log[-checkpoint_every:]
            if hasattr(pipeline, "reports"):
                row["rehearsal_beats_committed"] = sum(r.committed for r in pipeline.reports)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row) + "\n")
            state_path.write_text(kernel.state.model_dump_json(), encoding="utf-8")
            passing = [g for g in ("massed", "spaced_short", "spaced_long", "returning") if g in score["groups"]]
            kept = sum(score["groups"][g].get("kept", 0) for g in passing); cues = sum(score["groups"][g]["cues"] for g in passing)
            prom = sum(score["groups"][g].get("promoted", 0) for g in passing); fams = sum(score["groups"][g]["families"] for g in passing)
            print(f"[{arm}] lesson {lesson:5d} cycle {kernel.state.cycle:6d}  {row['ms_per_beat']:7.0f} ms/beat  "
                  f"kept {kept}/{cues}  promoted {prom}/{fams}  wrong {len(score['wrong_promotions'])}  "
                  f"structures {score['structures']}  elapsed {(now - began) / 60:5.1f} min", flush=True)
            window = time.perf_counter(); promoted_window = 0
    if total == len(commands):
        done_path.write_text(json.dumps({"arm": arm, "lessons": total, "final_fingerprint": kernel.fingerprint(),
                                         "pack_sha256": pack_sha, "seed": seed}, indent=1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--lessons", type=int, default=2500, help="Length of the life to generate (ignored if --pack is given).")
    parser.add_argument("--life-seed", type=int, default=9001); parser.add_argument("--seed", type=int, default=2301, help="Kernel seed.")
    parser.add_argument("--pack", type=Path, default=None); parser.add_argument("--arm", default="all", choices=ARMS + EXTRA_ARMS + ("all",))
    parser.add_argument("--out-dir", type=Path, default=REPO / "long_life_runs")
    parser.add_argument("--checkpoint-every", type=int, default=100); parser.add_argument("--promote-every", type=int, default=20)
    parser.add_argument("--max-promotions", type=int, default=4)
    parser.add_argument("--stop-after", type=int, default=None, help="Stop each arm at this lesson (it stays resumable).")
    parser.add_argument("--no-accelerate", action="store_true", help="Run without the byte-exact long-life accelerators.")
    parser.add_argument("--reader", action="store_true", help="sidecar_reader: words seen separately (field unchanged).")
    parser.add_argument("--senses", action="store_true", help="sidecar_ring stack: per-sense views, ringing, adaptation, carry one experience, reminding, measured attention.")
    parser.add_argument("--senses-without", default="", help="comma list of parts to leave out of --senses: moment, remind, attention")
    parser.add_argument("--senses-with", default="", help="extra parts: carry (carry everything one experience; measured harmful)")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.pack is None:
        from generate_long_life_pack_v0 import write
        stem = f"verdant_long_life_curriculum_{args.lessons}_seed{args.life_seed}"
        args.pack = args.out_dir / f"{stem}.vcpack"
        if not args.pack.exists():
            write(args.lessons, args.life_seed, args.out_dir); print(f"generated {args.pack.name}")
    expect_path = args.pack.with_name(args.pack.stem + ".expectations.json")
    READER["on"] = args.reader
    if args.senses:
        import sidecar_ring as ring
        leave = set(filter(None, args.senses_without.split(",")))
        ring.install_ring(adapt=True)
        if "remind" not in leave:
            ring.install_inferred_association()
        if "attention" not in leave:
            ring.install_attention()
        if "carry" in args.senses_with.split(","):           # the old carry, kept only to reproduce its measured harm
            PIPELINE_CONFIG.update(ring.CARRY_ONE_EXPERIENCE); SENSES["on"] = True
        if "moment" not in leave:
            ring.install_moment_carry()
    if not args.no_accelerate:
        from sidecar_acceleration import install_long_life_acceleration
        install_long_life_acceleration()
    for arm in (ARMS if args.arm == "all" else (args.arm,)):
        run_arm(arm, args.pack, expect_path, args.out_dir, seed=args.seed, checkpoint_every=args.checkpoint_every,
                promote_every=args.promote_every, max_promotions=args.max_promotions, stop_after=args.stop_after)


if __name__ == "__main__":
    main()
