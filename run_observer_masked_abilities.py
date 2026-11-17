"""Observer: two things the engine already computes or stores but nothing reads.

  P  A structure's field prototype (the mean of its members' resonance profiles) is written
     onto every candidate and every promoted P, and no stage reads it. Can it recognise a
     whole family from raw features?
  N  The workspace's prediction_error signal is a constant 0.15 for current evidence. Does
     resonance already contain a usable measure of "I have not met this before"?

Read-only after ordinary teaching: probes are features only and commit nothing.
"""
from __future__ import annotations

import argparse, hashlib, json, random, sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "curriculum_packs")]
from generate_controls_pack_v0 import RELATIONS, Tokens, text_features  # noqa: E402
from run_observer_field_function import DIM, lesson  # noqa: E402
from verdant_development import VerdantDevelopmentPipeline  # noqa: E402
from verdant_kernel import VerdantKernel  # noqa: E402
from verdant_structures import VerdantStructurePipeline  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--families", type=int, default=30); ap.add_argument("--seed", type=int, default=2301)
    ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    rng = random.Random(a.seed); tokens = Tokens(rng); families = []
    for i in range(a.families):
        m = [tokens.new() for _ in range(3)]
        families.append({"id": f"fam{i:02d}", "members": m, "edges": [(m[0], rng.choice(RELATIONS), m[1]), (m[1], rng.choice(RELATIONS), m[2])]})
    schedule = [(f, e) for e in range(5) for f in families]; rng.shuffle(schedule)
    kernel = VerdantKernel(seed=a.seed, state_dim=DIM, run_label="masked"); pipe = VerdantDevelopmentPipeline()
    for n, (family, exposure) in enumerate(schedule):
        pipe.advance(kernel, lesson(n, family, exposure))
    fingerprint = kernel.fingerprint(); ids = {c.label: cid for cid, c in kernel.state.concepts.items()}

    def proto(family):
        _dim, real, imag, _sha = VerdantStructurePipeline._field_prototype(kernel, tuple(sorted(ids[m] for m in family["members"])))
        return np.asarray(real) + 1j * np.asarray(imag)
    protos = np.stack([proto(f) for f in families]); centred = protos - protos.mean(axis=0)
    effect = lambda text: kernel._project_effect(kernel._validated_feature_array(text_features(text, DIM)), "text")

    def top(text, matrix, mean=None):
        q = effect(text) - (0 if mean is None else mean)
        return int(np.argmax(np.abs(matrix.conj() @ q)))
    mean_proto = protos.mean(axis=0)
    rows = {"raw prototype": [0, 0, 0], "prototype with the shared part removed": [0, 0, 0]}
    for i, f in enumerate(families):
        m = f["members"]
        probes = (f"Later someone noticed {m[2]}, {m[0]} and {m[1]} together.", f"Later someone noticed only {m[0]}.", f"Later someone noticed only {m[2]}.")
        for j, text in enumerate(probes):
            rows["raw prototype"][j] += top(text, protos) == i
            rows["prototype with the shared part removed"][j] += top(text, centred, mean_proto) == i
    report = {"schema": "verdant.observer.masked_abilities.v0", "families": a.families, "chance_top1": round(1 / a.families, 3),
              "P_whole_family_recognised_top1": {k: {"all members named": round(v[0] / a.families, 3), "first member only": round(v[1] / a.families, 3),
                                                     "last member only": round(v[2] / a.families, 3)} for k, v in rows.items()}}

    # ---- N: is novelty already measurable? ------------------------------------------------
    def stand_out(text):
        rep = kernel.inspect_resonance(text_features(text, DIM), "text", top_k=len(ids))
        p = np.array([c.contribution.profile_alignment for c in rep.candidates])
        return float((p.max() - p.mean()) / (p.std() + 1e-12))
    known = [stand_out(f"Later someone noticed {f['members'][2]}, {f['members'][0]} and {f['members'][1]} together.") for f in families]
    fresh = [stand_out("Later someone noticed {}, {} and {} together.".format(*[tokens.new() for _ in range(3)])) for _ in range(a.families)]
    cut = (np.mean(known) + np.mean(fresh)) / 2
    report["N_profile_stand_out_in_sds"] = {"sentences about taught families": [round(float(np.mean(known)), 2), round(float(np.min(known)), 2)],
                                            "sentences about never-taught tokens": [round(float(np.mean(fresh)), 2), round(float(np.max(fresh)), 2)],
                                            "layout": "[mean, worst case toward the other group]",
                                            "correctly_separated_at_midpoint": round((sum(k > cut for k in known) + sum(x <= cut for x in fresh)) / (2 * a.families), 3)}
    report["N_stock_prediction_error_signal"] = "constant 0.15 on every current-evidence item"
    if kernel.fingerprint() != fingerprint:
        raise RuntimeError("Probing changed canonical state.")
    a.out.write_text(json.dumps(report, indent=1), encoding="utf-8"); print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
