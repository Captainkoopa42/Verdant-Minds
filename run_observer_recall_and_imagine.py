"""Observer: recall that chooses how to remember, reliving, and imagining, on a grown organism.

Uses a saved long-life organism (default: the 406-lesson full-system life, seed 9001) and its
expectations file, so every cue's true history is known: earned families, things met twice,
things met many times in one setting, things met once, and words never met at all.
"""
from __future__ import annotations

import argparse, collections, json, random, sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "workbench" / "backend")]
from verdant_kernel import VerdantKernel  # noqa: E402
from verdant_kernel.models import KernelState  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--state", type=Path, required=True); ap.add_argument("--expectations", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    from sidecar_bond_clock import install_changes_only; install_changes_only()
    from sidecar_recall import imagine, recall, relive, _frames_by_event, _unit
    kernel = VerdantKernel.from_state(KernelState.model_validate_json(a.state.read_text())); fp = kernel.fingerprint()
    exp = json.loads(a.expectations.read_text()); rng = random.Random(1)
    report = {"schema": "verdant.observer.recall_and_imagine.v0", "lessons": len(kernel.state.processed_event_keys)}

    # 1. which way does recall choose to remember, for each kind of history?
    modes = collections.OrderedDict(); provenance = collections.defaultdict(collections.Counter); examples = {}
    for f in exp["families"]:
        if f["group"] not in ("massed", "spaced_long", "under_exposed", "single_context", "once"):
            continue
        for cue in f["members"]:
            r = recall(kernel, cue); modes.setdefault(f["group"], collections.Counter())[r.mode] += 1
            for _l, p in r.partners:
                provenance[f["group"]][p.split(",")[0].split(" (")[0]] += 1
                if p.startswith("SEARCHED"):
                    truly_never = not set(f["members"]) & {_l}
                    provenance[f["group"]]["SEARCHED and truly never met" if truly_never else "SEARCHED but WAS met (label wrong)"] += 1
            examples.setdefault(f"{f['group']}/{r.mode}", {"cue": cue, "partners": r.partners, "note": r.note})
    never = [recall(kernel, f"neverseen{i}").mode for i in range(10)]
    report["1_mode_chosen_by_history"] = {g: dict(v) for g, v in modes.items()} | {"never met": dict(collections.Counter(never))}
    report["1_how_each_partner_was_reached"] = {g: dict(v) for g, v in provenance.items()}
    report["1_examples"] = examples

    # 2. reliving: is each experience recovered exactly?
    frames = _frames_by_event(kernel); keys = sorted(frames); sample = rng.sample(keys, 40); r_ = kernel.state.ecwf_policy.retention
    errs, replay, concepts_ok = [], [], 0
    for key in sample:
        x = relive(kernel, key); after = np.asarray(kernel.state.field.history[frames[key]].real) + 1j * np.asarray(kernel.state.field.history[frames[key]].imag)
        rebuilt = _unit(r_ * x.mind_before + x.effect) if np.linalg.norm(x.mind_before) else x.effect
        errs.append(x.recovery_error); replay.append(float(np.max(np.abs(rebuilt - after))))
        concepts_ok += x.concept_ids == tuple(kernel.state.field.history[frames[key]].bound_concept_ids)
    report["2_relive"] = {"experiences": len(sample), "max_length_error": float(max(errs)), "max_replay_difference": float(max(replay)),
                          "concepts_exactly_as_recorded": f"{concepts_ok}/{len(sample)}"}

    # 3. imagining: an earned experience with one member swapped for a member of another earned family
    label = {cid: c.label for cid, c in kernel.state.concepts.items()}
    massed = [f for f in exp["families"] if f["group"] == "massed"]; trials = []
    for i in range(6):
        base, other = massed[i], massed[(i + 3) % len(massed)]
        key = next(k for k in keys if set(base["members"]) <= {label[c] for c in kernel.state.field.history[frames[k]].bound_concept_ids})
        out_c, in_c = base["members"][0], other["members"][1]
        for ctx in ("then", "now"):
            im = imagine(kernel, key, out_c, in_c, context=ctx); held = [l for l, _p in im.held_in_mind]
            trials.append({"context": ctx, "kept_from_the_memory": sorted(set(base["members"][1:]) & set(held)),
                           "swapped_out_still_held": out_c in held, "swapped_in_held": in_c in held,
                           "new_partners_called_up": sorted((set(other["members"]) - {in_c}) & set(held)),
                           "labels": collections.Counter(p.split(" (")[0] for _l, p in im.held_in_mind),
                           "original_intact": im.original_intact, "held_in_mind": im.held_in_mind})
    then = [t for t in trials if t["context"] == "then"]
    report["3_imagine_summary"] = {
        "trials": len(then), "rest_of_the_memory_kept": sum(len(t["kept_from_the_memory"]) == 2 for t in then),
        "swapped_out_dropped": sum(not t["swapped_out_still_held"] for t in then), "swapped_in_held": sum(t["swapped_in_held"] for t in then),
        "called_up_partners_of_the_new_piece": sum(bool(t["new_partners_called_up"]) for t in then),
        "original_memory_intact_after_imagining": sum(t["original_intact"] for t in trials), "of_all_trials": len(trials),
        "now_context_differs_from_then": sum(a_["held_in_mind"] != b_["held_in_mind"] for a_, b_ in zip(trials[0::2], trials[1::2]))}
    report["3_imagine_example"] = trials[0]
    report["4_organism_unchanged"] = kernel.fingerprint() == fp
    a.out.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8"); print(json.dumps({k: v for k, v in report.items() if k not in ("1_examples",)}, indent=1, default=str))


if __name__ == "__main__":
    main()
