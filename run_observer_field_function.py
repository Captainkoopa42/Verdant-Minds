"""Observer: what does the wave field do when it is the only way in?

Every test so far handed the concepts over by name. Here, after ordinary teaching, the
organism is given FEATURES ONLY (the hashed text of a sentence it has never seen, with no
concept list) and asked, through its own read-only ``inspect_resonance``, what that
reminds it of. Nothing is committed by a probe.

  A  recognition without names   new wording that mentions all members / one member only
  B  context                     an ambiguous cue (one member each of two families) after
                                 one family or the other was just revisited
  C  width of the present        how long after an experience its concepts still stand out
                                 in the live field, against concepts not recently bound
  D  what the phases buy         the same write/read rule in plain numpy with complex phasor
                                 addresses vs real +-1 addresses (same dimension, and same
                                 number of stored numbers)

Each of A and B is run with the stock query weights and with each of the three resonance
terms alone (profile / live field / recent history), on throwaway copies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "curriculum_packs")]
from generate_controls_pack_v0 import RELATIONS, TEMPLATES, Tokens, text_features  # noqa: E402
from verdant_development import VerdantDevelopmentPipeline  # noqa: E402
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel  # noqa: E402
from verdant_kernel.models import RelationProposal  # noqa: E402

DIM = 128
WEIGHTS = {"stock": None, "profile only": (1.0, 0.0, 0.0), "live field only": (0.0, 1.0, 0.0), "history only": (0.0, 0.0, 1.0)}


def lesson(n: int, family: dict, exposure: int) -> ExperienceCommand:
    clauses = " and ".join(f"the {a} {r} the {b}" for a, r, b in (family["edges"] if exposure % 2 == 0 else family["edges"][::-1]))
    text = TEMPLATES[exposure % len(TEMPLATES)].format(clauses=clauses)
    return ExperienceCommand(event_key=f"field-fn-{n}", source_ref="field-function", modality="text",
                             feature_vector=text_features(text, DIM), payload_sha256=hashlib.sha256(text.encode()).hexdigest(),
                             concept_proposals=[ConceptProposal(label=m) for m in family["members"]],
                             relation_proposals=[RelationProposal(source_label=x, target_label=y, relation_type=r) for x, r, y in family["edges"]],
                             metadata={"context_id": f"{family['id']}_c{exposure % 3}"})


def with_weights(kernel: VerdantKernel, weights) -> VerdantKernel:
    copy = VerdantKernel.from_state(kernel.snapshot())
    if weights is not None:
        copy.update_ecwf_policy(query_profile_weight=weights[0], query_current_weight=weights[1], query_history_weight=weights[2])
    return copy


def ranked(kernel: VerdantKernel, text: str, k: int) -> list[str]:
    report = kernel.inspect_resonance(text_features(text, DIM), "text", top_k=k)
    return [kernel.state.concepts[c.concept_id].label for c in report.candidates]


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--families", type=int, default=30); ap.add_argument("--seed", type=int, default=2301)
    ap.add_argument("--out", type=Path, required=True); ap.add_argument("--wave", action="store_true"); a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    if a.wave:
        from sidecar_wave import install_wave; install_wave()
    rng = random.Random(a.seed); tokens = Tokens(rng); families = []
    for i in range(a.families):
        m = [tokens.new() for _ in range(3)]
        families.append({"id": f"fam{i:02d}", "members": m, "edges": [(m[0], rng.choice(RELATIONS), m[1]), (m[1], rng.choice(RELATIONS), m[2])]})
    schedule = [(f, e) for e in range(5) for f in families]; rng.shuffle(schedule)
    kernel = VerdantKernel(seed=a.seed, state_dim=DIM, run_label="field-function"); pipe = VerdantDevelopmentPipeline(); order = []
    for n, (family, exposure) in enumerate(schedule):
        pipe.advance(kernel, lesson(n, family, exposure)); order.append(family["id"])
    fingerprint = kernel.fingerprint(); n_concepts = len(kernel.state.concepts)
    report = {"schema": "verdant.observer.field_function.v0", "families": a.families, "lessons": len(schedule), "concepts": n_concepts,
              "chance_top3_contains_a_given_member": round(3 / n_concepts, 4)}

    # ---- A: recognition without names --------------------------------------------------
    A = {}
    for name, weights in WEIGHTS.items():
        k = with_weights(kernel, weights); full = part = part_hits = 0
        for f in families:
            m = f["members"]
            full += set(ranked(k, f"Later someone noticed {m[2]}, {m[0]} and {m[1]} together.", 3)) == set(m)
            got = ranked(k, f"Later someone noticed only {m[0]}.", 3)
            part += set(got) == set(m); part_hits += len(set(got) & set(m[1:]))
        A[name] = {"all_members_named_top3_exact": round(full / len(families), 3),
                   "one_member_named_top3_exact": round(part / len(families), 3),
                   "one_member_named_unnamed_partners_in_top3": round(part_hits / (2 * len(families)), 3)}
    report["A_recognition_without_names"] = A

    # ---- B: context tips an ambiguous cue ----------------------------------------------
    B = {name: [0, 0] for name in WEIGHTS}; pairs = [(families[i], families[i + 1]) for i in range(0, min(20, a.families) - 1, 2)]
    for fa, fb in pairs:
        cue = f"Later someone noticed {fa['members'][0]} beside {fb['members'][0]}."
        for recent, other in ((fa, fb), (fb, fa)):
            primed = VerdantKernel.from_state(kernel.snapshot())
            for j in range(2):
                pipe.advance(primed, lesson(10_000 + hash((recent["id"], j)) % 10_000, recent, j))
            for name, weights in WEIGHTS.items():
                got = ranked(with_weights(primed, weights), cue, n_concepts)
                pos = lambda fam: min(got.index(x) for x in fam["members"][1:])
                B[name][0] += pos(recent) < pos(other); B[name][1] += 1
    report["B_recently_active_family_wins_ambiguous_cue"] = {n: round(v[0] / v[1], 3) for n, v in B.items()}
    report["B_trials"] = B["stock"][1]

    # ---- C: width of the present --------------------------------------------------------
    field = np.asarray(kernel.state.field.real) + 1j * np.asarray(kernel.state.field.imag); field /= np.linalg.norm(field)
    label_id = {c.label: cid for cid, c in kernel.state.concepts.items()}; fam_by_id = {f["id"]: f for f in families}
    addr = lambda cid: np.asarray(kernel.state.field_addresses[cid].real) + 1j * np.asarray(kernel.state.field_addresses[cid].imag)
    align = lambda fam: float(np.mean([abs(np.vdot(addr(label_id[m]), field)) for m in fam["members"]]))
    last_seen = {}
    for position, fid in enumerate(order):
        last_seen[fid] = len(order) - 1 - position
    by_lag = sorted((lag, align(fam_by_id[fid])) for fid, lag in last_seen.items())
    report["C_alignment_with_live_field_by_lessons_since_last_seen"] = [(lag, round(v, 4)) for lag, v in by_lag[:14]]
    report["C_floor_mean_alignment_lag_over_20"] = round(float(np.mean([v for lag, v in by_lag if lag > 20] or [0])), 4)
    report["C_random_expectation"] = round(math.sqrt(math.pi / (4 * DIM)), 4)

    # ---- D: complex phasors vs real signs, same rule, plain numpy -----------------------
    def simulate(kind: str, dim: int, trials: int = 300) -> dict:
        r = np.random.default_rng(7); out = {}
        for lag in (0, 1, 2, 3, 4, 6, 8):
            sig, noise = [], []
            for _ in range(trials):
                if kind == "complex":
                    A_ = np.exp(1j * r.uniform(-np.pi, np.pi, (60, dim))) / np.sqrt(dim)
                else:
                    A_ = r.choice((-1.0, 1.0), (60, dim)) / np.sqrt(dim)
                f = np.zeros(dim, dtype=A_.dtype)
                for step in range(12):                      # 12 experiences of 3 concepts each
                    e = A_[3 * step:3 * step + 3].sum(axis=0); e /= np.linalg.norm(e)
                    f = 0.72 * f + e; f /= np.linalg.norm(f)
                target = A_[3 * (11 - lag)]; sig.append(abs(np.vdot(target, f))); noise.append(abs(np.vdot(A_[50], f)))
            out[lag] = round(float((np.mean(sig) - np.mean(noise)) / np.std(noise)), 2)
        return out
    report["D_separation_in_noise_sds_by_lag"] = {"complex phasors, 128 dims (256 stored numbers)": simulate("complex", 128),
                                                  "real signs, 128 dims (128 stored numbers)": simulate("real", 128),
                                                  "real signs, 256 dims (256 stored numbers)": simulate("real", 256)}

    # ---- E: the same three terms, each put on a common scale before weighting -------------
    def standardized_rank(k: VerdantKernel, text: str) -> list[str]:
        rep = k.inspect_resonance(text_features(text, DIM), "text", top_k=n_concepts)
        labels = [k.state.concepts[c.concept_id].label for c in rep.candidates]
        cols = np.array([[c.contribution.profile_alignment, c.contribution.current_field_alignment, c.contribution.history_alignment]
                         for c in rep.candidates])
        z = (cols - cols.mean(axis=0)) / (cols.std(axis=0) + 1e-12)
        score = z @ np.array([0.5, 0.3, 0.2])
        return [labels[i] for i in np.argsort(-score, kind="stable")]
    full = part_hits = 0
    for f in families:
        m = f["members"]
        full += set(standardized_rank(kernel, f"Later someone noticed {m[2]}, {m[0]} and {m[1]} together.")[:3]) == set(m)
        part_hits += len(set(standardized_rank(kernel, f"Later someone noticed only {m[0]}.")[:3]) & set(m[1:]))
    wins = trials = 0
    for fa, fb in pairs:
        cue = f"Later someone noticed {fa['members'][0]} beside {fb['members'][0]}."
        for recent, other in ((fa, fb), (fb, fa)):
            primed = VerdantKernel.from_state(kernel.snapshot())
            for j in range(2):
                pipe.advance(primed, lesson(20_000 + hash((recent["id"], j)) % 10_000, recent, j))
            got = standardized_rank(primed, cue); pos = lambda fam: min(got.index(x) for x in fam["members"][1:])
            wins += pos(recent) < pos(other); trials += 1
    report["E_standardized_terms_same_weights"] = {"all_members_named_top3_exact": round(full / len(families), 3),
        "one_member_named_unnamed_partners_in_top3": round(part_hits / (2 * len(families)), 3),
        "recently_active_family_wins_ambiguous_cue": round(wins / trials, 3)}

    # ---- F: can phase carry who-did-what? plain numpy, same write rule -------------------
    def roles(lag_list=(0, 1, 2), trials: int = 400) -> dict:
        r = np.random.default_rng(11); out = {}
        for lag in lag_list:
            ok = 0
            for _ in range(trials):
                A_ = np.exp(1j * r.uniform(-np.pi, np.pi, (40, DIM))) / np.sqrt(DIM); f = np.zeros(DIM, dtype=complex)
                for step in range(12):                       # each experience: source at phase 0, target a quarter turn later
                    e = A_[2 * step] + 1j * A_[2 * step + 1]; e /= np.linalg.norm(e)
                    f = 0.72 * f + e; f /= np.linalg.norm(f)
                src, tgt = A_[2 * (11 - lag)], A_[2 * (11 - lag) + 1]
                turn = lambda a: abs(np.angle(np.vdot(a, f)))          # 0 = in step, pi/2 = a quarter turn behind
                ok += (turn(src) < np.pi / 4) and (abs(turn(tgt) - np.pi / 2) < np.pi / 4)
            out[lag] = round(ok / trials, 3)
        return out
    report["F_role_read_from_phase_both_correct_by_lag"] = roles()
    report["F_note"] = "Stock field adds addresses with no phase offset and reads only |overlap|, so direction is not in the field today."
    # ---- G: is who-acted-on-whom in the real field's record? ------------------------------
    from sidecar_wave import field_direction
    right = total = 0; turns = []
    for relation in kernel.state.relations.values():
        angle, used = field_direction(kernel, relation.source_concept_id, relation.target_concept_id)
        if used:
            total += 1; right += angle > 0; turns.append(angle)
    report["G_direction_read_from_kernel_field_history"] = {"relations": total, "source_before_target": round(right / max(1, total), 3),
                                                            "mean_turn": round(float(np.mean(turns)) if turns else 0.0, 4), "wave_installed": bool(a.wave)}
    if kernel.fingerprint() != fingerprint:
        raise RuntimeError("Probing changed canonical state.")
    a.out.write_text(json.dumps(report, indent=1), encoding="utf-8"); print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
