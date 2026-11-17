"""Observer: one folding rule at every depth, tested against the archive's acceptance gates.

Runs the whole experimental stack (recurrence, bond clock, rehearsal, surprise, wave) with
`sidecar_fold`, and the same stack without folding, on one generated curriculum:

  families   13 three-word families, each taught 5 times
  scenes     groups of three families taught TOGETHER: three groups 5 times each;
             one group only twice (must not fold); one group 5 times in a single context
             (must not fold)
  world      the three well-taught groups all together, 5 times

Gates checked (letters follow the archive): A one code path reaches several depths;
B same run twice gives the same fingerprint; C a new scene recruits its fold and a
near-miss scene does not; D/F ablating a lower fold stops every fold above it being
recognised and restoring it brings them back; H how much the mind holds per lesson.
"""
from __future__ import annotations

import argparse, collections, hashlib, json, random, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "curriculum_packs")]
from generate_controls_pack_v0 import RELATIONS, TEMPLATES, Tokens, text_features  # noqa: E402
from verdant_compilation import VerdantCompilationPipeline  # noqa: E402
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel  # noqa: E402
from verdant_kernel.models import RelationProposal  # noqa: E402

DIM = 128


def build_curriculum(seed: int):
    rng = random.Random(seed); tokens = Tokens(rng); fams = []
    for i in range(16):
        m = [tokens.new() for _ in range(3)]
        fams.append({"id": f"f{i:02d}", "members": m, "edges": [(m[0], rng.choice(RELATIONS), m[1]), (m[1], rng.choice(RELATIONS), m[2])]})
    groups = {"g1": fams[0:3], "g2": fams[3:6], "g3": fams[6:9], "twice": fams[9:12], "one_context": fams[12:15]}
    near_miss = [fams[0], fams[1], fams[15]]
    counter = [0]

    def lesson(parts, exposure, tag, contexts=3):
        counter[0] += 1
        edges = [e for f in parts for e in f["edges"]]
        clauses = " and ".join(f"the {a} {r} the {b}" for a, r, b in (edges if exposure % 2 == 0 else edges[::-1]))
        text = TEMPLATES[exposure % len(TEMPLATES)].format(clauses=clauses)
        return ExperienceCommand(event_key=f"fold-{seed}-{counter[0]:04d}", source_ref=f"recursive-fold::{tag}", modality="text",
                                 feature_vector=text_features(text, DIM), payload_sha256=hashlib.sha256(text.encode()).hexdigest(),
                                 concept_proposals=[ConceptProposal(label=m) for f in parts for m in f["members"]],
                                 relation_proposals=[RelationProposal(source_label=a, target_label=b, relation_type=r) for a, r, b in edges],
                                 metadata={"context_id": f"{tag}_c{exposure % contexts}"})
    plan = []
    for f in fams:
        plan += [("family", lesson([f], e, f["id"])) for e in range(5)]
    for name in ("g1", "g2", "g3"):
        plan += [("scene", lesson(groups[name], e, name)) for e in range(5)]
    plan += [("scene", lesson(groups["twice"], e, "twice")) for e in range(2)]
    plan += [("scene", lesson(groups["one_context"], e, "one_context", contexts=1)) for e in range(5)]
    world = groups["g1"] + groups["g2"] + groups["g3"]
    plan += [("world", lesson(world, e, "world")) for e in range(5)]
    probes = {"new_scene_g1": lesson(groups["g1"], 7, "probe_g1"), "near_miss": lesson(near_miss, 7, "probe_near"),
              "new_world": lesson(world, 7, "probe_world")}
    return fams, groups, plan, probes


def make_stack(folding: bool):
    from sidecar_bond_clock import BondClockPlasticityPipeline
    from sidecar_recurrence import ExperienceRecurrenceStructurePipeline
    from sidecar_rehearsal import RehearsalConfig, RehearsingDevelopmentPipeline
    from sidecar_surprise import SurpriseDevelopmentPipeline, surprise_plasticity
    structures = ExperienceRecurrenceStructurePipeline(); plasticity = surprise_plasticity(BondClockPlasticityPipeline)
    if folding:
        from sidecar_fold import FoldingDevelopmentPipeline, folding_plasticity
        inner = FoldingDevelopmentPipeline(structures=structures, plasticity=folding_plasticity(plasticity)())
    else:
        inner = SurpriseDevelopmentPipeline(structures=structures, plasticity=plasticity())
    return RehearsingDevelopmentPipeline(inner, RehearsalConfig(min_real_exposures=1)), inner, structures


def run(seed: int, folding: bool):
    from sidecar_fold import promote_and_reify
    fams, groups, plan, probes = build_curriculum(seed)
    kernel = VerdantKernel(seed=seed, state_dim=DIM, run_label="recursive-fold"); pipe, inner, structures = make_stack(folding)
    for step, (_kind, command) in enumerate(plan, start=1):
        pipe.advance(kernel, command)
        if step % 5 == 0 or step == len(plan):
            for cid, cand in sorted(kernel.state.structure_candidates.items()):
                if cand.status.value == "eligible":
                    if folding:
                        promote_and_reify(kernel, structures, cid)
                    else:
                        structures.promote(kernel, cid)
    return kernel, inner, fams, groups, plan, probes


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=2301); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--no-wave", action="store_true"); a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    if not a.no_wave:
        from sidecar_wave import install_wave; install_wave()
    from sidecar_fold import chunk, depth_of, fold_table, unfold
    kernel, inner, fams, groups, plan, probes = run(a.seed, True)
    state = kernel.state; label = {cid: c.label for cid, c in state.concepts.items()}; ids = {v: k for k, v in label.items()}
    leaves = lambda sid: frozenset(label[c] for c in unfold(kernel, state.structures[sid].member_concept_ids))
    intended = {frozenset(f["members"]): f"family {f['id']}" for f in fams}
    for name in ("g1", "g2", "g3"):
        intended[frozenset(m for f in groups[name] for m in f["members"])] = f"scene {name}"
    intended[frozenset(m for n in ("g1", "g2", "g3") for f in groups[n] for m in f["members"])] = "world"
    forbidden = {frozenset(m for f in groups[n] for m in f["members"]): n for n in ("twice", "one_context")}
    rows = []; by_depth = collections.Counter()
    for sid in sorted(state.structures):
        d = depth_of(kernel, sid); by_depth[d] += 1; lv = leaves(sid)
        rows.append({"depth": d, "operands": len(state.structures[sid].member_concept_ids), "stands_for_concepts": len(lv),
                     "is": intended.get(lv, forbidden.get(lv, "UNINTENDED"))})
    kinds = collections.Counter(type(e).__name__ for e in state.structure_promotion_events)
    report = {"schema": "verdant.observer.recursive_fold.v0", "seed": a.seed, "lessons": len(plan), "wave": not a.no_wave,
              "A_structures_by_depth": dict(sorted(by_depth.items())), "A_promotion_record_types": dict(kinds),
              "A_found": collections.Counter(r["is"].split()[0] for r in rows),
              "unintended_or_forbidden_folds": [r for r in rows if r["is"] in ("UNINTENDED", "twice", "one_context")]}

    def routed(command):
        got, used = chunk(kernel, [ids[p.label] for p in command.concept_proposals])
        return sorted(label[c] for c in got), used
    scene_g1 = next(sid for sid in state.structures if intended.get(leaves(sid)) == "scene g1") if any(intended.get(leaves(s)) == "scene g1" for s in state.structures) else None
    handle_of = {sid: h for h, (sid, _m) in fold_table(kernel, available_only=False).items()}
    report["C_new_scene_routes_to"] = routed(probes["new_scene_g1"]); report["C_near_miss_routes_to"] = routed(probes["near_miss"])
    report["C_new_scene_recruits_scene_fold"] = bool(scene_g1 and routed(probes["new_scene_g1"])[0] == [label[handle_of[scene_g1]]])
    report["C_near_miss_recruits_scene_fold"] = bool(scene_g1 and label[handle_of[scene_g1]] in routed(probes["near_miss"])[0])
    report["H_concepts_named_vs_held_in_mind"] = {"new scene": [len(probes["new_scene_g1"].concept_proposals), len(routed(probes["new_scene_g1"])[0])],
                                                  "new world": [len(probes["new_world"].concept_proposals), len(routed(probes["new_world"])[0])]}
    log = collections.defaultdict(list)
    for (key, before, after, used), (kind, _c) in zip(inner.fold_log, plan):
        log[kind].append((before, after))
    report["H_mean_bound_per_lesson_before_and_after_routing"] = {k: [round(sum(b for b, _ in v) / len(v), 1), round(sum(x for _, x in v) / len(v), 1)] for k, v in log.items()}

    # D/F: remove one lowest fold and watch everything above it
    fam0 = next(sid for sid in state.structures if leaves(sid) == frozenset(fams[0]["members"]))
    before = fingerprint = None
    recall = VerdantCompilationPipeline(); cue = ids[fams[0]["members"][0]]
    def snapshot():
        from_cue = unfold(kernel, recall.inspect(kernel, list(chunk(kernel, [ids[m] for m in fams[0]["members"]])[0])).reconstructed_concept_ids, available_only=True)
        return {"scene_routes_to": len(routed(probes["new_scene_g1"])[0]), "world_routes_to": len(routed(probes["new_world"])[0]),
                "seeing_one_family_recalls_concepts": len(from_cue)}
    report["DF_with_all_folds"] = snapshot()
    recall.ablate(kernel, fam0, "recursive fold gate D"); report["DF_lowest_fold_removed"] = snapshot()
    recall.restore(kernel, fam0, "recursive fold gate D"); report["DF_restored"] = snapshot()

    again, *_ = run(a.seed, True)
    kernel_fp_first = run(a.seed, True)[0].fingerprint()
    report["B_same_run_twice_same_fingerprint"] = again.fingerprint() == kernel_fp_first
    base, base_inner, *_ = run(a.seed, False); b = base.state; bl = {cid: c.label for cid, c in b.concepts.items()}
    base_sets = [frozenset(bl[m] for m in s.member_concept_ids) for s in b.structures.values()]
    report["baseline_same_stack_without_folding"] = {"structures": len(base_sets), "largest": max(map(len, base_sets), default=0),
        "families": sum(1 for s in base_sets if intended.get(s, "").startswith("family")), "scenes": sum(1 for s in base_sets if intended.get(s, "").startswith("scene")),
        "world": sum(1 for s in base_sets if intended.get(s) == "world"), "other": sum(1 for s in base_sets if s not in intended)}
    report["A_found"] = dict(report["A_found"])
    a.out.write_text(json.dumps(report, indent=1), encoding="utf-8"); print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
