"""Observer: one wave for every sense. Recognition, dilution, priming, the unknown, and conflict.

World: 8 things, each with a look (a shape through the media gateway and perception: the eye),
a sound (a synthetic voice through an ear) and a name (text: "look, the NAME"). Exposure groups:
  mostly_heard   heard 6, seen 1          mostly_seen   seen 6, heard 1
  balanced       heard 3, seen 3          together      heard 3, seen 3, each sight followed at
                                                        once by its sound (the same moment)
Every thing also gets 2 name lessons. Plus 2 never-shown shapes and 2 never-heard voices.
Ears: "fine" (48 log-energy bands) or "pipeline" (the built-in audio translator's 10 numbers).
Minds: full stack ("reunion") or full stack with the wave sidecar ("whole").

Measured (fixed in docs/RECOGNITION_IN_THE_WAVE_V0.md before running):
 1 dilution   naming new sights and new sounds of each thing, by the organism's own resonance and
              by the wave readout (chord view, per-sense view, per-sense + adaptation), per group;
              baseline: the sense alone (nearest average raw description of the named examples)
 2 priming    on a copy, an unlabelled sound of X arrives; then a hard sight of X is read by the
              organism's own resonance. Rank of X: no sound / sound of X / sound of another thing
 3 unknown    leftover for new sights/sounds of known things vs never-shown/never-heard ones,
              per group (does a rarely-seen known thing look unknown?)
 4 conflict   a sight of X with a sound of X, of another known thing Y, or of a never-heard voice:
              does the readout say agree / two different things / unknown, and how does the
              expected sound of X line up with the sound heard (in-phase part, Re<expected, heard>)?
"""
from __future__ import annotations

import argparse, hashlib, json, random, sys, tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "workbench" / "backend"), str(REPO / "curriculum_packs")]
from generate_controls_pack_v0 import Tokens, text_features  # noqa: E402
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel  # noqa: E402

GROUPS = {"mostly_heard": (6, 1), "mostly_seen": (1, 6), "balanced": (3, 3), "together": (3, 3)}
VOICES = [(110, 2.2, 0.0), (147, 0.6, 0.25), (196, 1.4, 0.0), (262, 2.0, 0.25), (349, 0.8, 0.0), (466, 1.6, 0.25),
          (622, 1.0, 0.0), (831, 2.4, 0.0), (130, 1.2, 0.1), (520, 0.7, 0.0)]


def pipeline_ear(sound: np.ndarray, rate: int) -> list[float]:
    from verdant_sensory.pipeline import NativeModality, NativeSamplePacket, VerdantSensoryPipeline
    pcm = (np.clip(sound / (np.max(np.abs(sound)) + 1e-9) * 0.8, -1, 1) * 32767).astype("<i2").tobytes()
    packet = NativeSamplePacket(stream_id="ear", sequence_number=0, timestamp_ns=0, modality=NativeModality.AUDIO,
                                media_type="audio/pcm", payload=pcm, sample_rate_hz=rate)
    return list(VerdantSensoryPipeline()._translate_audio(packet, None, 16).feature_vector)


def cmd(key, modality, feats, names, context="world"):
    return ExperienceCommand(event_key=key, source_ref=f"one-wave::{key}", modality=modality, feature_vector=list(feats),
                             payload_sha256=hashlib.sha256(repr(list(feats)).encode()).hexdigest(),
                             concept_proposals=[ConceptProposal(label=n) for n in names], metadata={"context_id": context})


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=31)
    ap.add_argument("--arm", choices=("reunion", "whole"), default="reunion"); ap.add_argument("--ear", choices=("fine", "pipeline"), default="fine")
    ap.add_argument("--ring", action="store_true", help="per-sense views + recognition rings the wave (sidecar_ring)")
    ap.add_argument("--adapt", action="store_true", help="with --ring: adaptation in the wave for the resonance profile term")
    ap.add_argument("--signed", choices=("none", "half", "quarter"), default="none", help="with --ring: how a conflicting ring is turned (roadmap Stage A)")
    ap.add_argument("--tests", type=int, default=4); ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    from sidecar_bond_clock import install_changes_only; install_changes_only()
    if a.ring:
        from sidecar_ring import install_ring; install_ring(adapt=a.adapt, signed={"none": False, "half": "half", "quarter": "quarter"}[a.signed])
    from run_observer_long_life import build_pipeline, promote_eligible
    from run_observer_one_door import KINDS, episode, eye
    from run_observer_imagination_senses import RATE, fine_ear, make_voice
    from sidecar_recognize import read_wave, sensed_wave, sense_views
    from verdant_kernel.models import KernelState

    rng = random.Random(a.seed); tokens = Tokens(rng); work = Path(tempfile.mkdtemp(prefix="one_wave_"))
    kinds = list(KINDS); rng.shuffle(kinds); voices = list(range(len(VOICES))); rng.shuffle(voices)
    things = []
    for i, g in enumerate([g for g in GROUPS for _ in range(2)]):
        things.append({"name": tokens.new(), "group": g, "kind": kinds[i], "level": 235 - 8 * i, "voice": make_voice(*VOICES[voices[i]], seed=700 + i)})
    novel_looks = [{"kind": kinds[8 + j], "level": 200 - 10 * j} for j in range(2)]
    novel_voices = [make_voice(*VOICES[voices[8 + j]], seed=780 + j) for j in range(2)]
    ear = (lambda s: fine_ear(s)) if a.ear == "fine" else (lambda s: pipeline_ear(s, RATE))
    n_eye = [0]

    def see(look, tag, hard=False):
        r = random.Random(f"{a.seed}-{tag}"); frames = episode(look["kind"], int(look["level"] * (0.75 if hard else 1.0)), r)
        if hard:
            noise = np.random.default_rng(r.randrange(1 << 30))
            frames = [np.clip(f.astype(np.float64) + noise.normal(0, 14, f.shape), 0, 255).astype(np.uint8) for f in frames]
        n_eye[0] += 1; return eye(frames, work, f"e{n_eye[0]}", a.seed)

    def hear(voice, tag):
        r = random.Random(f"{a.seed}-{tag}"); return ear(voice(r.uniform(0.3, 0.9), r.uniform(-0.01, 0.01)))

    # ---- a life
    lessons = []
    for t in things:
        heard, seen = GROUPS[t["group"]]
        for e in range(2):
            lessons.append([cmd(f"name-{t['name']}-{e}", "text", text_features(f"look, the {t['name']}", 128), [t["name"]])])
        if t["group"] == "together":
            for e in range(3):
                lessons.append([cmd(f"see-{t['name']}-{e}", "visual", see(t, f"see{t['name']}{e}"), [t["name"]], f"moment-{t['name']}-{e}"),
                                cmd(f"hear-{t['name']}-{e}", "audio", hear(t["voice"], f"hear{t['name']}{e}"), [t["name"]], f"moment-{t['name']}-{e}")])
        else:
            for e in range(seen):
                lessons.append([cmd(f"see-{t['name']}-{e}", "visual", see(t, f"see{t['name']}{e}"), [t["name"]])])
            for e in range(heard):
                lessons.append([cmd(f"hear-{t['name']}-{e}", "audio", hear(t["voice"], f"hear{t['name']}{e}"), [t["name"]])])
    rng.shuffle(lessons)
    kernel = VerdantKernel(seed=a.seed, state_dim=128, run_label=f"one-wave-{a.arm}-{a.ear}")
    pipe, structures = build_pipeline(a.arm); n = 0
    for group in lessons:
        for c in group:
            pipe.advance(kernel, c); n += 1
            if n % 20 == 0:
                promote_eligible(kernel, structures, 4)
    print(f"grew on {n} experiences", flush=True)
    fp = kernel.fingerprint(); state_json = kernel.state.model_dump_json(); names = [t["name"] for t in things]
    label = {c: x.label for c, x in kernel.state.concepts.items()}; name_ids = [c for c, x in kernel.state.concepts.items() if x.label in names]

    # the sense alone: nearest average raw description of the named examples
    raw = {"visual": {}, "audio": {}}
    for group in lessons:
        for c in group:
            if c.modality in raw:
                raw[c.modality].setdefault(c.concept_proposals[0].label, []).append(np.asarray(c.feature_vector))
    def sense_alone(feats, modality):
        f = np.asarray(feats); return min(raw[modality], key=lambda nm: np.linalg.norm(np.mean(raw[modality][nm], axis=0) - f))

    def organism(feats, modality, k=None):
        rep = (k or kernel).inspect_resonance(feats, modality, top_k=len(name_ids), candidate_concept_ids=name_ids)
        return [label[c.concept_id] for c in rep.candidates]

    # ---- 1 dilution and 3 unknown
    tests = {"visual": [], "audio": []}
    for t in things:
        for e in range(a.tests):
            tests["visual"].append((t, see(t, f"test-see{t['name']}{e}"))); tests["audio"].append((t, hear(t["voice"], f"test-hear{t['name']}{e}")))
    novel = {"visual": [see(l, f"novel-see{j}{e}") for j, l in enumerate(novel_looks) for e in range(a.tests)],
             "audio": [hear(v, f"novel-hear{j}{e}") for j, v in enumerate(novel_voices) for e in range(a.tests)]}
    readers = {"organism": None, "chord": ("chord", False), "per_sense": ("per_sense", False), "per_sense_adapted": ("per_sense", True)}
    naming = {}; unknown_rows = {}
    for m in ("visual", "audio"):
        for t, f in tests[m]:
            res = {"sense_alone": sense_alone(f, m) == t["name"], "organism": organism(f, m)[0] == t["name"]}
            for rname, spec in readers.items():
                if spec:
                    rd = read_wave(kernel, f, m, view=spec[0], adapt=spec[1], top=len(names) + 12)
                    best = next((x[0] for x in rd.known if x[0] in names), None)
                    res[rname] = best == t["name"]
                    unknown_rows.setdefault((m, rname), {"known": {}, "novel": []})["known"].setdefault(t["group"], []).append(rd.unknown)
            for k_, v in res.items():
                naming.setdefault((m, t["group"], k_), []).append(v)
        for f in novel[m]:
            for rname, spec in readers.items():
                if spec:
                    unknown_rows[(m, rname)]["novel"].append(read_wave(kernel, f, m, view=spec[0], adapt=spec[1]).unknown)
    naming_out = {}
    for (m, g, k_), v in naming.items():
        naming_out.setdefault(m, {}).setdefault(k_, {})[g] = round(float(np.mean(v)), 3)
    unknown_out = {}
    for (m, rname), d in unknown_rows.items():
        allk = [x for v in d["known"].values() for x in v]
        sep = float(np.mean([nv > kv for nv in d["novel"] for kv in allk]))
        sep_g = {g: round(float(np.mean([nv > kv for nv in d["novel"] for kv in v])), 3) for g, v in d["known"].items()}
        unknown_out.setdefault(m, {})[rname] = {"known_mean": {g: round(float(np.mean(v)), 3) for g, v in d["known"].items()},
                                                 "novel_mean": round(float(np.mean(d["novel"])), 3), "separation": round(sep, 3),
                                                 "separation_by_group": sep_g}

    # ---- 2 priming
    priming = []
    for i, t in enumerate(things):
        other = things[(i + 3) % len(things)]
        hard = see(t, f"prime-see{t['name']}", hard=True)
        ranks = {}
        for cond, voice in (("no_sound", None), ("sound_of_it", t["voice"]), ("sound_of_other", other["voice"])):
            fork = VerdantKernel.from_state(KernelState.model_validate_json(state_json)); p2, _ = build_pipeline(a.arm)
            if voice is not None:
                p2.advance(fork, cmd(f"prime-{t['name']}-{cond}", "audio", hear(voice, f"prime{t['name']}{cond}"), []))
            else:
                p2.advance(fork, cmd(f"prime-{t['name']}-{cond}", "text", text_features("and then", 128), []))
            order = organism(hard, "visual", fork); ranks[cond] = order.index(t["name"]) + 1
            ranks[cond + "_other_rank"] = order.index(other["name"]) + 1
        priming.append({"thing": t["name"], "group": t["group"], **ranks})

    # ---- 4 conflict
    views = sense_views(kernel)["audio"]["views"]; ids = {v: k for k, v in label.items()}
    conflict = []
    for i, (t, sight_f) in enumerate([x for x in tests["visual"] if True][:: a.tests]):
        y = things[(things.index(t) + 1) % len(things)]
        seen = read_wave(kernel, sight_f, "visual", view="per_sense", adapt=True, top=3)
        expected = views.get(ids[t["name"]], (None,))[0]
        for cond, sound in (("same_thing", hear(t["voice"], f"c-same{i}")), ("other_known", hear(y["voice"], f"c-other{i}")),
                            ("never_heard", hear(novel_voices[i % 2], f"c-novel{i}"))):
            heard = read_wave(kernel, sound, "audio", view="per_sense", adapt=True, top=3)
            S = sensed_wave(kernel, sound, "audio")
            inphase = float(np.vdot(expected / np.linalg.norm(expected), S).real) if expected is not None else None
            verdict = "unknown" if heard.unknown > 0.5 else ("agree" if heard.best == seen.best else "two different things")
            conflict.append({"thing": t["name"], "condition": cond, "sight_says": seen.best, "sound_says": heard.best,
                             "sound_unknown": round(heard.unknown, 3), "verdict": verdict, "expected_vs_heard_in_phase": inphase,
                             "phase_of_best_turns": heard.known[0][2] if heard.known else None})
    conf_sum = {}
    for cond in ("same_thing", "other_known", "never_heard"):
        rows = [r for r in conflict if r["condition"] == cond]
        conf_sum[cond] = {"verdicts": {v: sum(r["verdict"] == v for r in rows) for v in ("agree", "two different things", "unknown")},
                          "in_phase_mean": round(float(np.mean([r["expected_vs_heard_in_phase"] for r in rows if r["expected_vs_heard_in_phase"] is not None])), 3)}

    rung = [(c.label, len(c.attributes.get("rings", {})), c.attributes.get("ring_disagreements", 0)) for c in kernel.state.concepts.values()]
    summary = {"arm": a.arm, "ear": a.ear, "ring": a.ring, "adapt": a.adapt, "signed": a.signed,
               "half_turn_rings_during_life": sum(1 for c in kernel.state.concepts.values() for w in c.attributes.get("rings", {}).values() if isinstance(w, dict) or w < 0),
               "rings_during_life": {"total": sum(r[1] for r in rung), "while_told_something_else": sum(r[2] for r in rung)}, "experiences": n, "concepts": len(kernel.state.concepts),
               "structures": len(kernel.state.structures), "chance": round(1 / len(names), 3),
               "1_naming": naming_out, "3_unknown": unknown_out,
               "2_priming": {"mean_rank": {c: round(float(np.mean([p[c] for p in priming])), 2) for c in ("no_sound", "sound_of_it", "sound_of_other")},
                             "rank1": {c: sum(p[c] == 1 for p in priming) for c in ("no_sound", "sound_of_it", "sound_of_other")},
                             "other_thing_mean_rank": {c: round(float(np.mean([p[c + "_other_rank"] for p in priming])), 2) for c in ("no_sound", "sound_of_other")}},
               "4_conflict": conf_sum, "organism_unchanged": kernel.fingerprint() == fp}
    a.out.write_text(json.dumps({"schema": "verdant.observer.one_wave.v0", "summary": summary, "priming": priming, "conflict": conflict}, indent=1, default=str))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
