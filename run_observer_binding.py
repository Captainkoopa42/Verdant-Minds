"""Observer: binding across senses, with its negative control (readiness item 7). Fast synthetic senses.

Groups (each thing has a fixed look, 24 numbers, and/or a fixed sound, 16 numbers, plus noise):
  named_both     6 things, each seen and heard under its own name (bound by the name)
  together       P_i seen (named P_i) and Q_i heard (named Q_i) at the same moment, 6 times (2 pairs)
  never_together R_i seen and S_i heard, always far apart in time, 6 times each (2 pairs)
  only_named     2 things only ever named in text, never seen or heard
Measured, with ringing + adaptation, on throwaway copies:
  1 bonds between P_i and Q_i vs between R_i and S_i (things never met together should not bind)
  2 an unnamed sound of Q_i arrives: does the real workspace bring P_i to mind (association recall)?
    the same for S_i -> R_i (should not)
  3 an unnamed sound of a named_both thing: does its own look come back (its sight view lines up with
    a fresh sight of it) better than another thing's look?
  4 how_known for each group (naming as its own evidence)
"""
from __future__ import annotations

import argparse, hashlib, json, random, sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "workbench" / "backend"), str(REPO / "curriculum_packs")]


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=51); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--carry", action="store_true", help="short-term memory of one experience (sidecar_ring.CARRY_ONE_EXPERIENCE)")
    ap.add_argument("--remind", action="store_true", help="what is recognised can remind (sidecar_ring.install_inferred_association)")
    ap.add_argument("--moment", action="store_true", help="binding by moment (sidecar_ring.install_moment_carry) instead of --carry")
    a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    from sidecar_bond_clock import install_changes_only; install_changes_only()
    from sidecar_ring import install_ring, how_known; install_ring(adapt=True)
    from generate_controls_pack_v0 import Tokens, text_features
    import run_observer_long_life as R
    from run_observer_long_life import build_pipeline, promote_eligible
    from sidecar_ring import CARRY_ONE_EXPERIENCE, carry_one_experience
    if a.carry:
        R.PIPELINE_CONFIG.update(CARRY_ONE_EXPERIENCE)
    if a.remind:
        from sidecar_ring import install_inferred_association; install_inferred_association()
    if a.moment:
        from sidecar_ring import install_moment_carry; install_moment_carry()
    from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel
    from verdant_kernel.models import KernelState

    rng = random.Random(a.seed); nrng = np.random.default_rng(a.seed); tokens = Tokens(rng)
    look = lambda: nrng.normal(size=24); sound = lambda: nrng.normal(size=16)
    both = [{"name": tokens.new(), "look": look(), "sound": sound()} for _ in range(6)]
    together = [({"name": tokens.new(), "look": look()}, {"name": tokens.new(), "sound": sound()}) for _ in range(2)]
    apart = [({"name": tokens.new(), "look": look()}, {"name": tokens.new(), "sound": sound()}) for _ in range(2)]
    only_named = [tokens.new() for _ in range(2)]
    n = [0]

    def cmd(mod, base, names, context):
        n[0] += 1; f = list(base + 0.15 * nrng.normal(size=base.size)) if mod != "text" else base
        return ExperienceCommand(event_key=f"b{n[0]:04d}", source_ref="binding", modality=mod, feature_vector=f,
                                 payload_sha256=hashlib.sha256(repr(f).encode()).hexdigest(),
                                 concept_proposals=[ConceptProposal(label=x) for x in names], metadata={"context_id": context})
    blocks = []
    for t in both:
        for e in range(4):
            blocks.append([cmd("visual", t["look"], [t["name"]], f"b-{t['name']}-{e}")]); blocks.append([cmd("audio", t["sound"], [t["name"]], f"h-{t['name']}-{e}")])
            if e < 2:
                blocks.append([cmd("text", text_features(f"look, the {t['name']}", 128), [t["name"]], "names")])
    for p, q in together:
        for e in range(6):
            ctx = f"moment-{p['name']}-{e}"; blocks.append([cmd("visual", p["look"], [p["name"]], ctx), cmd("audio", q["sound"], [q["name"]], ctx)])
    for r, s_ in apart:
        for e in range(6):
            blocks.append([cmd("visual", r["look"], [r["name"]], f"r-{r['name']}-{e}")]); blocks.append([cmd("audio", s_["sound"], [s_["name"]], f"s-{s_['name']}-{e}")])
    for w in only_named:
        for e in range(3):
            blocks.append([cmd("text", text_features(f"look, the {w}", 128), [w], "names")])
    rng.shuffle(blocks)
    # keep never-together pairs apart: no R_i block within 5 blocks of an S_i block
    for _ in range(200):
        bad = False
        for r, s_ in apart:
            pos_r = [i for i, b in enumerate(blocks) if b[0].concept_proposals[0].label == r["name"]]
            pos_s = [i for i, b in enumerate(blocks) if b[0].concept_proposals[0].label == s_["name"]]
            if any(abs(i - j) <= 5 for i in pos_r for j in pos_s):
                bad = True; break
        if not bad:
            break
        rng.shuffle(blocks)
    kernel = VerdantKernel(seed=a.seed, state_dim=128, run_label="binding"); pipe, structures = build_pipeline("reunion"); k = 0
    if a.carry:
        carry_one_experience(kernel)
    for b in blocks:
        for c in b:
            pipe.advance(kernel, c); k += 1
            if k % 20 == 0:
                promote_eligible(kernel, structures, 4)
    label = {c: x.label for c, x in kernel.state.concepts.items()}; ids = {v: c for c, v in label.items()}
    def bond(x, y):
        return max((b.strength for b in kernel.state.plasticity_associations.values() if set(b.concept_ids) == {ids[x], ids[y]}), default=0.0)
    state_json = kernel.state.model_dump_json()

    def brought_to_mind(sound_base, name=None):
        fork = VerdantKernel.from_state(KernelState.model_validate_json(state_json)); p2, _ = build_pipeline("reunion")
        c = cmd("audio", sound_base, [name] if name else [], "test"); p2.advance(fork, c)
        w = fork.state.workspace_cycle_events[-1].report; flab = {cc: x.label for cc, x in fork.state.concepts.items()}
        offered = {flab[m] for a_ in w.assessments if a_.candidate.source_kind.value in ("local_association", "earned_structure")
                   and a_.disposition.value == "admit" for m in a_.candidate.binding_refs if m in flab}
        return offered
    rows = {"together": [], "never_together": []}
    for group, pairs in (("together", together), ("never_together", apart)):
        for p, q in pairs:
            rows[group].append({"seen": p["name"], "heard": q["name"], "bond": round(bond(p["name"], q["name"]), 3),
                                "sound_brings_the_other_to_mind": p["name"] in brought_to_mind(q["sound"], q["name"]),
                                "unnamed_sound_brings_the_other_to_mind": p["name"] in brought_to_mind(q["sound"])})
    views = {t["name"]: kernel.state.concepts[ids[t["name"]]].attributes.get("view::visual") for t in both}
    look_back = []
    from sidecar_ring import recognise
    for t in both:
        S = kernel._project_effect(kernel._validated_feature_array(t["sound"] + 0.15 * nrng.normal(size=16)), "audio")
        shares, _u = recognise(kernel, S, "audio"); heard_as = label[shares[0][0]] if shares else None
        fresh = kernel._project_effect(kernel._validated_feature_array(t["look"] + 0.15 * nrng.normal(size=24)), "visual")
        v = views.get(heard_as); vec = np.asarray(v["real"]) + 1j * np.asarray(v["imag"]) if v else None
        own = float(abs(np.vdot(vec / np.linalg.norm(vec), fresh))) if vec is not None else None
        others = [float(abs(np.vdot((np.asarray(views[o]["real"]) + 1j * np.asarray(views[o]["imag"])) / np.linalg.norm(np.asarray(views[o]["real"]) + 1j * np.asarray(views[o]["imag"])), fresh)))
                  for o in views if o != t["name"]]
        look_back.append({"thing": t["name"], "heard_as": heard_as, "its_look_lines_up": own, "best_other_look": max(others)})
    summary = {"carry": a.carry, "remind": a.remind, "moment": a.moment,
        "1_bonds": {g: [r["bond"] for r in rows[g]] for g in rows},
        "2_sound_brings_the_other_to_mind": {g: f'{sum(r["sound_brings_the_other_to_mind"] for r in rows[g])}/{len(rows[g])}' for g in rows},
        "2_unnamed_sound_brings_the_other_to_mind": {g: f'{sum(r["unnamed_sound_brings_the_other_to_mind"] for r in rows[g])}/{len(rows[g])}' for g in rows},
        "3_sound_brings_back_its_own_look": f'{sum(x["heard_as"] == x["thing"] and x["its_look_lines_up"] > x["best_other_look"] for x in look_back)}/{len(look_back)}',
        "3_alignment": {"own": round(float(np.mean([x["its_look_lines_up"] for x in look_back])), 3), "best_other": round(float(np.mean([x["best_other_look"] for x in look_back])), 3)},
        "4_how_known": {"named_both": how_known(kernel, both[0]["name"]), "seen_only": how_known(kernel, together[0][0]["name"]),
                        "heard_only": how_known(kernel, together[0][1]["name"]), "only_named": how_known(kernel, only_named[0])}}
    a.out.write_text(json.dumps({"schema": "verdant.observer.binding.v0", "summary": summary, "rows": rows, "look_back": look_back}, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
