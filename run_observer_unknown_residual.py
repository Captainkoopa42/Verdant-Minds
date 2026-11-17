"""Observer: is -M (the unknown) already present in the field as what the knowns cannot explain?

Reading of U = (M + -M)^i tested here: when an experience arrives, the part of it the
organism's known concepts can account for is M; what is left over is -M. In the field that
is a projection: express the experience's field effect through the known concepts' resonance
profiles; the share of its energy left unexplained is the unknown share.

After ordinary teaching (30 three-word families, 150 lessons), probes are FEATURES ONLY
(unseen sentences, no concept list), read-only. If the reading is right, the unknown share
should rise step by step as 0, 1, 2 and 3 of the three words in a sentence are new, and not
merely flip between "known" and "new".

Two projections are reported: onto the 3 best-matching known profiles, and onto every known
profile at once (a subspace test). Nothing is committed.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "curriculum_packs")]
from generate_controls_pack_v0 import RELATIONS, Tokens, text_features  # noqa: E402
from run_observer_field_function import DIM, lesson  # noqa: E402
from verdant_development import VerdantDevelopmentPipeline  # noqa: E402
from verdant_kernel import VerdantKernel  # noqa: E402


def unknown_share(q: np.ndarray, basis: np.ndarray) -> float:
    """Energy of q left after least-squares projection onto the rows of basis (complex)."""
    coeffs, *_ = np.linalg.lstsq(basis.T, q, rcond=None)
    residual = q - basis.T @ coeffs
    return float(np.vdot(residual, residual).real / np.vdot(q, q).real)


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--families", type=int, default=30); ap.add_argument("--seed", type=int, default=2301)
    ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    rng = random.Random(a.seed); tokens = Tokens(rng); families = []
    for i in range(a.families):
        m = [tokens.new() for _ in range(3)]
        families.append({"id": f"fam{i:02d}", "members": m, "edges": [(m[0], rng.choice(RELATIONS), m[1]), (m[1], rng.choice(RELATIONS), m[2])]})
    schedule = [(f, e) for e in range(5) for f in families]; rng.shuffle(schedule)
    kernel = VerdantKernel(seed=a.seed, state_dim=DIM, run_label="unknown-residual"); pipe = VerdantDevelopmentPipeline()
    for n, (family, exposure) in enumerate(schedule):
        pipe.advance(kernel, lesson(n, family, exposure))
    fingerprint = kernel.fingerprint()
    profiles = {cid: np.asarray(p.real) + 1j * np.asarray(p.imag) for cid, p in kernel.state.resonance_profiles.items()}
    ids = sorted(profiles); every = np.stack([profiles[c] for c in ids])
    effect = lambda text: kernel._project_effect(kernel._validated_feature_array(text_features(text, DIM)), "text")

    def top3(q):
        scores = np.abs(every.conj() @ q)
        return unknown_share(q, every[np.argsort(-scores)[:3]])

    rows = {}
    for new_words in (0, 1, 2, 3):
        t3, full = [], []
        for f in families:
            words = list(f["members"])
            for j in range(new_words):
                words[j] = tokens.new()
            q = effect(f"Later someone noticed {words[2]}, {words[0]} and {words[1]} together.")
            t3.append(top3(q)); full.append(unknown_share(q, every))
        rows[f"{new_words} of 3 words new"] = {"unknown_share_top3": [round(float(np.mean(t3)), 3), round(float(np.std(t3)), 3)],
                                               "unknown_share_all_known": [round(float(np.mean(full)), 3), round(float(np.std(full)), 3)]}
    order = [rows[k]["unknown_share_top3"][0] for k in rows]
    report = {"schema": "verdant.observer.unknown_residual.v0", "families": a.families, "known_concepts": len(ids), "field_dim": DIM,
              "by_new_words": rows, "top3_rises_at_every_step": all(x < y for x, y in zip(order, order[1:])),
              "layout": "[mean, sd] across 30 sentences"}
    if kernel.fingerprint() != fingerprint:
        raise RuntimeError("Probing changed canonical state.")
    a.out.write_text(json.dumps(report, indent=1), encoding="utf-8"); print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
