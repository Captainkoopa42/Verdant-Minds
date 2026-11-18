"""Observer: tension and the unknown steering attention (readiness item 8). Fast synthetic senses.

Phase 1: 6 familiar things, each seen and heard 4 times under its own name.
Phase 2 (short-term memory of one experience on, as in run_observer_binding.py), interleaved:
  new        2 new things, each heard (named) right after a familiar thing is seen, 4 times
  familiar   2 familiar things, each heard (named) right after another familiar thing is seen, 4 times
  conflict   a sound told to be familiar thing X, but it is the sound of familiar thing Y, 3 times
  correct    familiar sounds told correctly (false-alarm control), 8 times
Arms: stock attention (novelty 0.35, contradiction 0 for everything) vs measured (sidecar_ring.install_attention).
Measured: the novelty / contradiction signals and the workspace score of each kind of moment; the
bond formed between the seen thing and the heard thing (new pairs vs familiar pairs, same exposures);
false alarms (correctly told familiar sounds with contradiction > 0.2); the tension record.
"""
from __future__ import annotations

import argparse, hashlib, json, random, sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "workbench" / "backend"), str(REPO / "curriculum_packs")]


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=61); ap.add_argument("--steer", action="store_true")
    ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    from sidecar_bond_clock import install_changes_only; install_changes_only()
    import sidecar_ring as ring
    ring.install_ring(adapt=True)
    if a.steer:
        ring.install_attention()
    import run_observer_long_life as R
    R.PIPELINE_CONFIG.update(ring.CARRY_ONE_EXPERIENCE)
    from generate_controls_pack_v0 import Tokens
    from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel

    rng = random.Random(a.seed); nrng = np.random.default_rng(a.seed); tokens = Tokens(rng)
    fam = [{"name": tokens.new(), "look": nrng.normal(size=24), "sound": nrng.normal(size=16)} for _ in range(6)]
    new = [{"name": tokens.new(), "sound": nrng.normal(size=16)} for _ in range(2)]
    n = [0]; kinds = {}

    def cmd(mod, base, names, kind, ctx):
        n[0] += 1; f = list(base + 0.15 * nrng.normal(size=base.size)); key = f"a{n[0]:04d}"; kinds[key] = kind
        return ExperienceCommand(event_key=key, source_ref="attention", modality=mod, feature_vector=f,
                                 payload_sha256=hashlib.sha256(repr(f).encode()).hexdigest(),
                                 concept_proposals=[ConceptProposal(label=x) for x in names], metadata={"context_id": ctx})
    phase1 = []
    for t in fam:
        for e in range(4):
            phase1 += [[cmd("visual", t["look"], [t["name"]], "learning", f"l{t['name']}{e}")], [cmd("audio", t["sound"], [t["name"]], "learning", f"h{t['name']}{e}")]]
    rng.shuffle(phase1)
    pairs_new = [(fam[0], new[0]), (fam[1], new[1])]; pairs_fam = [(fam[2], fam[3]), (fam[4], fam[5])]
    phase2 = []
    for e in range(4):
        for (p, q), kind in [(x, "new") for x in pairs_new] + [(x, "familiar") for x in pairs_fam]:
            ctx = f"m{p['name']}{e}"
            phase2.append([cmd("visual", p["look"], [p["name"]], "seen_first", ctx), cmd("audio", q["sound"], [q["name"]], kind, ctx)])
    for e in range(3):
        phase2.append([cmd("audio", fam[4]["sound"], [fam[2]["name"]], "conflict", f"c{e}")])     # told fam2, sounds like fam4
    for e in range(8):
        t = fam[e % 6]; phase2.append([cmd("audio", t["sound"], [t["name"]], "correct", f"k{e}")])
    rng.shuffle(phase2)
    kernel = VerdantKernel(seed=a.seed, state_dim=128, run_label=f"attention-{a.steer}")
    ring.carry_one_experience(kernel); pipe, _ = R.build_pipeline("reunion")
    for b in phase1 + phase2:
        for c in b:
            pipe.advance(kernel, c)
    rows = []
    for w in kernel.state.workspace_cycle_events:
        for x in w.report.assessments:
            if x.candidate.source_kind.value == "current_evidence" and x.carried_from_item_id is None:
                key = x.candidate.label.split(": ", 1)[1]
                if key in kinds:
                    rows.append({"kind": kinds[key], "novelty": x.candidate.signals.novelty,
                                 "contradiction": x.candidate.signals.contradiction_pressure, "score": x.effective_score})
    by = {}
    for r in rows:
        by.setdefault(r["kind"], []).append(r)
    label = {c: x.label for c, x in kernel.state.concepts.items()}; ids = {v: k for k, v in label.items()}
    def bond(x, y):
        return max((b.strength for b in kernel.state.plasticity_associations.values() if set(b.concept_ids) == {ids[x], ids[y]}), default=0.0)
    summary = {"steer": a.steer,
               "signals": {k: {"novelty": round(float(np.mean([r["novelty"] for r in v])), 3), "contradiction": round(float(np.mean([r["contradiction"] for r in v])), 3),
                               "workspace_score": round(float(np.mean([r["score"] for r in v])), 3), "moments": len(v)} for k, v in sorted(by.items())},
               "bonds_new_pairs": [round(bond(p["name"], q["name"]), 3) for p, q in pairs_new],
               "bonds_familiar_pairs": [round(bond(p["name"], q["name"]), 3) for p, q in pairs_fam],
               "false_alarms": f'{sum(r["contradiction"] > 0.2 for r in by.get("correct", []))}/{len(by.get("correct", []))}',
               "conflicts_flagged": f'{sum(r["contradiction"] > 0.2 for r in by.get("conflict", []))}/{len(by.get("conflict", []))}',
               "tension": {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in ring.read_tension(kernel).items()
                           if k in (fam[2]["name"], fam[0]["name"], fam[5]["name"])},
               "who": {"told_but_conflicting": fam[2]["name"], "control_familiar": fam[0]["name"]}}
    a.out.write_text(json.dumps({"schema": "verdant.observer.attention.v0", "summary": summary}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
