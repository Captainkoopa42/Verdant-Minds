"""Observer: can the organism keep recognising a thing whose look changes late in life?

12 things are each met 12 times with a stable look (a random appearance vector plus noise).
Then 4 of them change their look completely and are met 6 more times with the new look.
Probes are FEATURES ONLY, read through the organism's own read-only resonance:
  new look of a changed thing     is it named first?
  old look of a changed thing     is it still named first? (the old memory must not be lost)
  look of an unchanged thing      control
Compared: stock lifelong profiles vs ``sidecar_profiles`` (lifelong + recent).
"""
from __future__ import annotations

import argparse, hashlib, json, sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO)]
from verdant_development import VerdantDevelopmentPipeline  # noqa: E402
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel  # noqa: E402

DIM = 64


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=2301); ap.add_argument("--recent", action="store_true")
    ap.add_argument("--noise", type=float, default=0.35); ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    if a.recent:
        from sidecar_profiles import install_profiles; install_profiles()
    r = np.random.default_rng(a.seed); things = [f"thing{i:02d}" for i in range(12)]; changed = things[:4]
    old = {t: r.standard_normal(DIM) for t in things}; new = {t: r.standard_normal(DIM) for t in changed}
    see = lambda look: [float(v) for v in (look + a.noise * r.standard_normal(DIM)) / np.linalg.norm(look)]
    kernel = VerdantKernel(seed=a.seed, state_dim=DIM, run_label="changing-look"); pipe = VerdantDevelopmentPipeline(); n = [0]

    def meet(thing, look):
        n[0] += 1; f = see(look)
        pipe.advance(kernel, ExperienceCommand(event_key=f"look-{n[0]}", source_ref="changing-look", modality="visual", feature_vector=f,
                     payload_sha256=hashlib.sha256(json.dumps(f).encode()).hexdigest(), concept_proposals=[ConceptProposal(label=thing)],
                     metadata={"context_id": f"c{n[0] % 3}"}))
    early = [t for t in things for _ in range(12)]; r.shuffle(early)
    for t in early:
        meet(t, old[t])
    late = [t for t in changed for _ in range(6)] + [t for t in things[4:] for _ in range(2)]; r.shuffle(late)
    for t in late:
        meet(t, new.get(t, old[t]))
    fingerprint = kernel.fingerprint(); label = {cid: c.label for cid, c in kernel.state.concepts.items()}

    def first(look, trials=10):
        hits = []
        for _ in range(trials):
            rep = kernel.inspect_resonance(see(look), "visual", top_k=len(label))
            best = max(rep.candidates, key=lambda c: c.contribution.profile_alignment)
            hits.append(label[best.concept_id])
        return hits
    score = lambda pairs: round(float(np.mean([h == t for t, look in pairs for h in first(look)])), 3)
    def best_match(look, trials=10):
        out = []
        for _ in range(trials):
            rep = kernel.inspect_resonance(see(look), "visual", top_k=len(label)); out.append(max(c.contribution.profile_alignment for c in rep.candidates))
        return out
    unseen = [r.standard_normal(DIM) for _ in range(4)]
    known_best = [x for t in things[4:] for x in best_match(old[t])]; unseen_best = [x for look in unseen for x in best_match(look)]
    report_extra = {"best_profile_match_known_vs_never_seen": [round(float(np.mean(known_best)), 3), round(float(np.mean(unseen_best)), 3)],
                    "never_seen_scores_below_every_known": round(float(np.mean([[u < k for k in known_best] for u in unseen_best])), 3)}
    report = {"schema": "verdant.observer.changing_look.v0", "seed": a.seed, "recent_profiles": a.recent, "noise": a.noise,
              "meetings": n[0], "named_first_by_profile_match": {
                  "new look of a changed thing": score([(t, new[t]) for t in changed]),
                  "old look of a changed thing": score([(t, old[t]) for t in changed]),
                  "unchanged thing": score([(t, old[t]) for t in things[4:]])}, "chance": round(1 / len(things), 3), **report_extra}
    if kernel.fingerprint() != fingerprint:
        raise RuntimeError("Probing changed canonical state.")
    a.out.write_text(json.dumps(report, indent=1), encoding="utf-8"); print(json.dumps(report["named_first_by_profile_match"]), report_extra)


if __name__ == "__main__":
    main()
