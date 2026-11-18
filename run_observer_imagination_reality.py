"""Observer: does imagination predict what real experience later shows?

On a grown organism, imagine an old experience with one piece swapped for a piece from another
family. Then, on throwaway copies of the organism, teach that exact combination for real: once
straight away ("now") and once after a stretch of unrelated new lessons ("later"). Compare what
imagination said with what the organism actually did.

What is compared (all decided before the run; see docs/IMAGINATION_REALITY_CHECK_V0.md):
  A. the moment itself: imagined experience vs the real one the field recorded (alignment, 0..1)
  B. what came to mind: imagination's top-6 readout vs the organism's real resonance top-6
  B'. diagnostic: the same readout given the true look of the new combination (imagination cannot
      know it; this splits the error into "model of the organism" and "guess of the look")
  C. the second step: what imagination said the newcomer would bring vs what the real workspace
     recalled by association in that beat
Controls, in the same units:
  - the unchanged memory (no swap) as the prediction
  - imagining with the WRONG newcomer (a piece from a third family)
  - step-two control: what the swapped-OUT piece would have brought
  - SIMULATED_RESULT: the real pipeline run now on a copy, compared with the real result later

The organism's saved state is never written; each real lesson runs on a fresh copy.
"""
from __future__ import annotations

import argparse, collections, copy, json, random, sys, tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "workbench" / "backend"), str(REPO / "curriculum_packs")]
from verdant_kernel import VerdantKernel  # noqa: E402
from verdant_kernel.models import KernelState  # noqa: E402

TOP = 6


def compile_items(pack_text: str, items: list[dict]):
    from run_observer_long_life import load_commands
    pack = json.loads(pack_text); sec = copy.deepcopy(pack["sections"][0]); sec["items"] = items
    pack["sections"] = [sec]
    with tempfile.NamedTemporaryFile("w", suffix=".vcpack", delete=False) as fh:
        json.dump(pack, fh); path = Path(fh.name)
    try:
        return load_commands(path)[1]
    finally:
        path.unlink()


def swapped_item(item: dict, out_label: str, in_label: str, key: str) -> dict:
    from generate_controls_pack_v0 import text_features
    new = copy.deepcopy(item); sub = lambda s: s.replace(out_label, in_label)
    new["source_text"] = sub(new["source_text"]); new["event_key"] = key; new["item_id"] = key
    new["concepts"] = [{"label": in_label if c["label"] == out_label else c["label"]} for c in new["concepts"]]
    for r in new.get("relations", []):
        r["source"], r["target"] = sub(r["source"]), sub(r["target"])
    new["claims"] = []
    new["source_ref"] = f"imagination-reality::{key}"
    new["feature_vector"] = text_features(new["source_text"], len(item["feature_vector"]))
    return new


def real_beat(kernel, command):
    """What the organism actually did with one real lesson: moment, resonance, association recall."""
    from sidecar_recall import relive, _experience_parts
    label = {c: x.label for c, x in kernel.state.concepts.items()}
    x = relive(kernel, command.event_key); sensed = _experience_parts(kernel, x)
    ev = next(e for e in reversed(kernel.state.resonance_events)
              if any(kernel.state.evidence[r].event_key == command.event_key for r in e.evidence_refs if r in kernel.state.evidence))
    resonance = [(label[c.concept_id], float(c.score)) for c in ev.query_report.candidates[:TOP]]
    wevent = next(w for w in kernel.state.workspace_cycle_events if w.report.cycle == ev.committed_cycle)
    offered, admitted = collections.defaultdict(set), collections.defaultdict(set)   # trigger label -> recalled labels
    scene = set(x.concept_ids)
    for a in wevent.report.assessments:
        kind = a.candidate.source_kind.value
        if kind not in ("local_association", "earned_structure") or a.carried_from_item_id is not None:
            continue
        triggers = a.candidate.metadata.get("trigger_concept_ids", ())
        for t in triggers:
            for m in a.candidate.binding_refs:
                if m not in scene:
                    offered[label[t]].add(label[m])
                    if a.disposition.value == "admit":
                        admitted[label[t]].add(label[m])
    return {"effect": x.effect, "sensed": sensed, "resonance": resonance, "offered": offered, "admitted": admitted, "after": _after(kernel, command.event_key),
            "scene": tuple(sorted(label[c] for c in x.concept_ids))}


def _after(kernel, key):
    from sidecar_recall import _frames_by_event, _vec
    return _vec(kernel.state.field.history[_frames_by_event(kernel)[key]])


def align(a, b) -> float:
    return float(abs(np.vdot(a, b)))


def overlap(pred, real) -> float:
    return len({p for p, *_ in pred} & {r for r, *_ in real}) / TOP


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", type=Path, required=True); ap.add_argument("--pack", type=Path, required=True)
    ap.add_argument("--expectations", type=Path, required=True); ap.add_argument("--filler", type=Path, required=True)
    ap.add_argument("--filler-lessons", type=int, default=20); ap.add_argument("--trials", type=int, default=12)
    ap.add_argument("--seed", type=int, default=1); ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    from sidecar_bond_clock import install_changes_only; install_changes_only()
    from sidecar_recall import imagine, relive, _frames_by_event, _experience_parts
    from run_observer_long_life import build_pipeline, load_commands

    state_text = a.state.read_text(); kernel = VerdantKernel.from_state(KernelState.model_validate_json(state_text)); fp = kernel.fingerprint()
    pack_text = a.pack.read_text(); items = {it["event_key"]: it for s in json.loads(pack_text)["sections"] for it in s["items"]}
    exp = json.loads(a.expectations.read_text()); filler = load_commands(a.filler)[1][: a.filler_lessons]
    label = {c: x.label for c, x in kernel.state.concepts.items()}; frames = _frames_by_event(kernel)
    filler_words = {p.label for c in filler for p in c.concept_proposals}
    assert not filler_words & set(label.values()), "filler lessons must be new to the organism"

    earned = {m for s in kernel.state.structures.values() if kernel.structure_is_available(s.structure_id)
              for m in s.member_concept_ids}
    families = [f for f in exp["families"] if f["group"] in ("massed", "spaced_short", "spaced_long", "returning")
                and all(m in {label[c] for c in earned} for m in f["members"])]
    rng = random.Random(a.seed); rng.shuffle(families)
    from sidecar_looks import reading, learn_shares, imagined_look
    width = len(next(iter(items.values()))["feature_vector"])
    shares = learn_shares(kernel, reading(width))
    reader_on = any("look::reading" in c.attributes for c in kernel.state.concepts.values())
    trials = []
    for i in range(min(a.trials, len(families) // 3 * 3)):
        base, other, third = families[i], families[(i + 1) % len(families)], families[(i + 2) % len(families)]
        key = next(k for k in sorted(frames) if set(base["members"]) <= {label[c] for c in kernel.state.field.history[frames[k]].bound_concept_ids})
        out_c, in_c, wrong_c = base["members"][0], other["members"][1], third["members"][1]
        trials.append((key, out_c, in_c, wrong_c))

    rows = []
    for n, (key, out_c, in_c, wrong_c) in enumerate(trials):
        im = imagine(kernel, key, out_c, in_c, context="now"); wrong = imagine(kernel, key, out_c, wrong_c, context="now")
        same = imagine(kernel, key, out_c, out_c, context="now", second_step=False)       # the memory replayed unchanged
        shared = imagine(kernel, key, out_c, in_c, context="now", look=imagined_look(kernel, shares, key, out_c, in_c))
        extra = {}
        if reader_on:
            from sidecar_reader import reread_look, word_shares
            extra["word_looks"] = imagine(kernel, key, out_c, in_c, context="now", look=imagined_look(kernel, word_shares(kernel, width), key, out_c, in_c))
            extra["reread"] = imagine(kernel, key, out_c, in_c, context="now", look=reread_look(kernel, key, out_c, in_c))
        true_look = imagine(kernel, key, out_c, in_c, context="now", look=(swapped_item(items[key], out_c, in_c, "x")["feature_vector"], "text"))
        base = relive(kernel, key); base_sensed = _experience_parts(kernel, base)
        from sidecar_recall import _brought_by
        ids = {v: k for k, v in label.items()}
        scene_ids = (set(base.concept_ids) - {ids[out_c]}) | {ids[in_c]}
        rest = {label[t]: {label[c] for c, _ in _brought_by(kernel, t, scene_ids, 0.24)} for t in scene_ids if t != ids[in_c]}
        rest = {t: v for t, v in rest.items() if v}
        from sidecar_recall import _unit
        mind_now = np.asarray(kernel.state.field.real) + 1j * np.asarray(kernel.state.field.imag)
        base_now = _unit(kernel.state.ecwf_policy.retention * mind_now + base.effect)
        command = compile_items(pack_text, [swapped_item(items[key], out_c, in_c, f"imagination-reality-{n:02d}")])[0]
        result = {}
        for when in ("now", "later"):
            fork = VerdantKernel.from_state(KernelState.model_validate_json(state_text)); pipe, _ = build_pipeline("reunion")
            if when == "later":
                for c in filler:
                    pipe.advance(fork, c)
            pipe.advance(fork, command); result[when] = real_beat(fork, command)
        brought = {l for l, _ in im.brought}
        row = {"trial": n, "memory": key, "swap": f"{out_c} -> {in_c}", "wrong_newcomer": wrong_c, "scene": im.scene}
        for when, real in result.items():
            row[when] = {
                "A_moment": {"imagined": align(im.effect, real["effect"]), "unchanged_memory": align(base.effect, real["effect"]),
                             "wrong_newcomer": align(wrong.effect, real["effect"]),
                             "sensing_imagined": align(im.sensed, real["sensed"]), "sensing_unchanged": align(base_sensed, real["sensed"]),
                             "shares_moment": align(shared.effect, real["effect"]), "sensing_shares": align(shared.sensed, real["sensed"]),
                             **{f"sensing_{n}": align(v.sensed, real["sensed"]) for n, v in extra.items()}},
                "B_came_to_mind": {"imagined": overlap(im.readout, real["resonance"]), "wrong_newcomer": overlap(wrong.readout, real["resonance"]),
                                   "unchanged_memory": overlap(same.readout, real["resonance"]),
                                   "shares": overlap(shared.readout, real["resonance"]),
                                   **{n: overlap(v.readout, real["resonance"]) for n, v in extra.items()},
                                   **{f"{n}_top1_match": v.readout[0][0] == real["resonance"][0][0] for n, v in extra.items()},
                                   "shares_top1_match": shared.readout[0][0] == real["resonance"][0][0],
                                   "diagnostic_given_the_true_look": overlap(true_look.readout, real["resonance"]),
                                   "diagnostic_true_look_exact_order": [l for l, _ in true_look.readout] == [l for l, _ in real["resonance"]],
                                   "newcomer_in_real_top6": in_c in {l for l, _ in real["resonance"]},
                                   "newcomer_in_imagined_top6": in_c in {l for l, _ in im.readout},
                                   "top1_match": im.readout[0][0] == real["resonance"][0][0],
                                   "imagined_list": im.readout, "real_list": real["resonance"]},
                "A_field_after": {"imagined_now": align(im.moment, real["after"]), "unchanged_memory_now": align(base_now, real["after"])},
                "C_second_step": {"newcomer_predicted": sorted(brought), "newcomer_really_offered": sorted(real["offered"].get(in_c, ())),
                                  "newcomer_won_attention": sorted(real["admitted"].get(in_c, ())),
                                  "hits": len(brought & real["offered"].get(in_c, set())),
                                  "false": sorted(brought - real["offered"].get(in_c, set())),
                                  "missed": sorted(real["offered"].get(in_c, set()) - brought),
                                  "rest_predicted": {t: sorted(v) for t, v in rest.items()},
                                  "rest_really_offered": {t: sorted(v) for t, v in real["offered"].items() if t != in_c},
                                  "rest_hits": sum(len(rest.get(t, set()) & v) for t, v in real["offered"].items() if t != in_c),
                                  "rest_offered_total": sum(len(v) for t, v in real["offered"].items() if t != in_c),
                                  "rest_predicted_total": sum(len(v) for v in rest.values()),
                                  "swapped_out_piece_came_back": out_c in set().union(*real["offered"].values()) if real["offered"] else False},
            }
        row["SIMULATED_now_vs_real_later"] = {"moment": align(result["now"]["effect"], result["later"]["effect"]),
                                              "came_to_mind": overlap(result["now"]["resonance"], result["later"]["resonance"])}
        rows.append(row); print(json.dumps({k: v for k, v in row.items() if k in ("trial", "swap")} | {
            w: {"A": round(row[w]["A_moment"]["imagined"], 3), "A0": round(row[w]["A_moment"]["unchanged_memory"], 3),
                "B": row[w]["B_came_to_mind"]["imagined"], "C": f'{row[w]["C_second_step"]["hits"]}/{len(row[w]["C_second_step"]["newcomer_really_offered"])}'}
            for w in ("now", "later")}), flush=True)

    def mean(xs):
        return round(float(np.mean(xs)), 3)
    summary = {}
    for when in ("now", "later"):
        R = [r[when] for r in rows]
        C = [r["C_second_step"] for r in R]
        predicted = sum(len(c["newcomer_predicted"]) for c in C); offered = sum(len(c["newcomer_really_offered"]) for c in C)
        hits = sum(c["hits"] for c in C)
        summary[when] = {
            "A_moment_alignment": {k: mean([r["A_moment"][k] for r in R]) for k in R[0]["A_moment"]},
            "A_imagined_beats_unchanged_memory": sum(r["A_moment"]["imagined"] > r["A_moment"]["unchanged_memory"] for r in R),
            "A_imagined_beats_wrong_newcomer": sum(r["A_moment"]["imagined"] > r["A_moment"]["wrong_newcomer"] for r in R),
            "B_top6_overlap": {k: mean([r["B_came_to_mind"][k] for r in R]) for k in ("imagined", "shares", "word_looks", "reread", "unchanged_memory", "wrong_newcomer", "diagnostic_given_the_true_look") if k in R[0]["B_came_to_mind"]},
            "B_top1": {k: sum(r["B_came_to_mind"].get(f"{k}_top1_match", False) for r in R) for k in ("word_looks", "reread")},
            "B_shares_top1_match": sum(r["B_came_to_mind"]["shares_top1_match"] for r in R),
            "B_shares_vs_average_per_trial": {"better": sum(r["B_came_to_mind"]["shares"] > r["B_came_to_mind"]["imagined"] for r in R),
                                              "same": sum(r["B_came_to_mind"]["shares"] == r["B_came_to_mind"]["imagined"] for r in R),
                                              "worse": sum(r["B_came_to_mind"]["shares"] < r["B_came_to_mind"]["imagined"] for r in R)},
            "A_sensing_shares_beats_average": sum(r["A_moment"]["sensing_shares"] > r["A_moment"]["sensing_imagined"] for r in R),
            "B_diagnostic_true_look_exact_order": sum(r["B_came_to_mind"]["diagnostic_true_look_exact_order"] for r in R),
            "B_newcomer_in_top6": {"imagined": sum(r["B_came_to_mind"]["newcomer_in_imagined_top6"] for r in R), "real": sum(r["B_came_to_mind"]["newcomer_in_real_top6"] for r in R),
                                   "agree": sum(r["B_came_to_mind"]["newcomer_in_imagined_top6"] == r["B_came_to_mind"]["newcomer_in_real_top6"] for r in R)},
            "B_top1_match": sum(r["B_came_to_mind"]["top1_match"] for r in R),
            "A_field_after": {k: mean([r["A_field_after"][k] for r in R]) for k in R[0]["A_field_after"]},
            "C_newcomer": {"predicted": predicted, "really_offered": offered, "hits": hits,
                           "won_attention": sum(len(c["newcomer_won_attention"]) for c in C)},
            "C_rest_of_scene": {"predicted": sum(c["rest_predicted_total"] for c in C), "really_offered": sum(c["rest_offered_total"] for c in C),
                                "hits": sum(c["rest_hits"] for c in C)},
            "C_swapped_out_piece_came_back": sum(c["swapped_out_piece_came_back"] for c in C),
            "C_imagination_said_it_would_come_back": sum(r["swap"].split(" -> ")[0] in set().union(*map(set, r[when]["C_second_step"]["rest_predicted"].values())) for r in rows),
        }
    summary["SIMULATED_now_vs_real_later"] = {k: mean([r["SIMULATED_now_vs_real_later"][k] for r in rows]) for k in ("moment", "came_to_mind")}
    summary["shares"] = {"experiences": shares.experiences, "concepts": len(shares.concept_ids),
                         "max_recovery_residual": shares.max_recovery_residual, "mean_unknown": round(float(np.mean(list(shares.unknown.values()))), 3)}
    summary["trials"] = len(rows); summary["filler_lessons_before_later"] = len(filler)
    summary["organism_unchanged"] = kernel.fingerprint() == fp
    a.out.write_text(json.dumps({"schema": "verdant.observer.imagination_reality.v0", "summary": summary, "trials": rows}, indent=1, default=str))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
