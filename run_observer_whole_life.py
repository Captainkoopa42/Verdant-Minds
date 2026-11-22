"""Observer: ONE life through the WHOLE organism, and every earlier check run on that same mind.

Why this exists. Until now each part was tested in its own setup (senses in their observers,
revision in text-only lives) and never all together. This observer is the standing whole-system
gate: one organism (``verdant_organism.Organism(Parts())``, every validated part on) grows through
one life that mixes every kind of input, and then every earlier ability is checked on that mind.

The life (one stream, interleaved, seeded):
  text      a changing-world curriculum (generator v1): families, reversals with controls,
            distractors, claims that are affirmed, negated, contested, reversed
  voices    8 voices taught by name through the REAL sensory pipeline (fine ear), 4 times each
  senses    6 things seen and heard by name; 2 pairs seen and heard at the same moment
            ("together"); 2 pairs seen and heard, never at the same moment ("apart")
  scenes    16 text families; 3 groups of 3 taught together 5 times; one group only twice and one
            group 5 times in a single context (neither may fold); the three groups all together

Checks (on the grown mind; probes run on throwaway copies; the mind's fingerprint is checked):
  T text: kept / promoted on the passing groups, wrong structures in use, reversals revised,
    controls revised, promotions from failing groups
  V voices: new recordings of known voices named by the wave readout; never-heard voices read
    as more than half unknown
  B binding: things met at the same moment bond more than things never met together; an unnamed
    sound brings its moment-partner to mind, and the never-together partner does not
  L look back: an unnamed sound is recognised, and its own look lines up better than any other
  F folds: scenes fold into folds of folds (depth >= 2); the twice-taught and one-context scenes do not
  S stance: reversed / contested claims carry more tension than claims only ever affirmed
  I imagination: relive / recall / imagine / simulate run on the grown mind and change nothing
"""
from __future__ import annotations

import argparse, collections, hashlib, json, random, statistics, sys, tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "workbench" / "backend"), str(REPO / "curriculum_packs")]

DIM = 128


def build_life(seed: int, text_lessons: int, organism):
    from generate_controls_pack_v0 import RELATIONS, TEMPLATES, Tokens, text_features
    from generate_long_life_pack_v1 import build as build_text
    from run_observer_imagination_senses import RATE, make_voice
    from run_observer_long_life import load_commands
    from run_observer_one_wave import VOICES
    from verdant_kernel import ConceptProposal, ExperienceCommand
    from verdant_kernel.models import RelationProposal
    from verdant_sensory.pipeline import NativeModality, NativeSamplePacket, VerdantSensoryPipeline

    rng = random.Random(seed); nrng = np.random.default_rng(seed); tokens = Tokens(random.Random(seed + 1))
    work = Path(tempfile.mkdtemp(prefix="whole_life_"))
    pack, expectations = build_text(text_lessons, seed)
    pack_path = work / "text.vcpack"; pack_path.write_text(json.dumps(pack))
    _dim, text_commands, _sha = load_commands(pack_path)
    used = {c.label for cmd in text_commands for c in cmd.concept_proposals}
    def new_name():
        while True:
            n = tokens.new()
            if n not in used:
                used.add(n); return n
    n = [0]

    def cmd(mod, features, names, context, tag, relations=()):
        n[0] += 1
        return ExperienceCommand(event_key=f"whole-{tag}-{n[0]:05d}", source_ref=f"whole-life::{tag}", modality=mod,
                                 feature_vector=list(map(float, features)), payload_sha256=hashlib.sha256(repr(list(features)).encode()).hexdigest(),
                                 concept_proposals=[ConceptProposal(label=x) for x in names],
                                 relation_proposals=[RelationProposal(source_label=a, target_label=b, relation_type=r) for a, r, b in relations],
                                 metadata={"context_id": context})

    blocks: dict[str, list] = {}
    # voices through the real sensory pipeline (the fine ear is installed by the organism)
    sensory = VerdantSensoryPipeline(); seq = [0]
    def packet(sound):
        pcm = (np.clip(sound / (np.max(np.abs(sound)) + 1e-9) * 0.8, -1, 1) * 32767).astype("<i2").tobytes()
        seq[0] += 1
        return NativeSamplePacket(stream_id="mic", sequence_number=seq[0], timestamp_ns=seq[0] * 1_000_000_000,
                                  modality=NativeModality.AUDIO, media_type="audio/pcm", payload=pcm, sample_rate_hz=RATE)
    def take(voice, tag):
        r = random.Random(f"{seed}-{tag}"); return voice(r.uniform(0.3, 0.9), r.uniform(-0.01, 0.01))
    order = list(range(len(VOICES))); rng.shuffle(order)
    recipes = [VOICES[i] for i in order] + [(175, 0.5, 0.0), (740, 1.9, 0.2)]
    voices = [(new_name(), make_voice(*r, seed=600 + j)) for j, r in enumerate(recipes)]
    known, novel = voices[:8], voices[8:]
    scratch = organism.new_kernel(seed=seed, state_dim=DIM, run_label="whole-life-translate")
    blocks["voices"] = [[cmd("native_audio", sensory.translate(scratch, packet(take(v, f"{name}{e}")), None).feature_vector,
                             [name], "voice-lessons", "voice")] for name, v in known for e in range(4)]
    # senses: seen and heard
    look = lambda: nrng.normal(size=24); sound = lambda: nrng.normal(size=16)
    noisy = lambda base: base + 0.15 * nrng.normal(size=base.size)
    both = [{"name": new_name(), "look": look(), "sound": sound()} for _ in range(6)]
    together = [({"name": new_name(), "look": look()}, {"name": new_name(), "sound": sound()}) for _ in range(2)]
    apart = [({"name": new_name(), "look": look()}, {"name": new_name(), "sound": sound()}) for _ in range(2)]
    sb = []
    for t in both:
        for e in range(4):
            sb.append([cmd("visual", noisy(t["look"]), [t["name"]], f"see-{t['name']}-{e}", "see")])
            sb.append([cmd("audio", noisy(t["sound"]), [t["name"]], f"hear-{t['name']}-{e}", "hear")])
    for p, q in together:
        for e in range(6):
            ctx = f"moment-{p['name']}-{e}"
            sb.append([cmd("visual", noisy(p["look"]), [p["name"]], ctx, "moment"), cmd("audio", noisy(q["sound"]), [q["name"]], ctx, "moment")])
    for r_, s_ in apart:
        for e in range(6):
            sb.append([cmd("visual", noisy(r_["look"]), [r_["name"]], f"apart-r-{r_['name']}-{e}", "apart")])
            sb.append([cmd("audio", noisy(s_["sound"]), [s_["name"]], f"apart-s-{s_['name']}-{e}", "apart")])
    blocks["senses"] = sb
    # scenes
    fams = []
    for i in range(16):
        m = [new_name() for _ in range(3)]
        fams.append({"id": f"sf{i:02d}", "members": m, "edges": [(m[0], rng.choice(RELATIONS), m[1]), (m[1], rng.choice(RELATIONS), m[2])]})
    groups = {"g1": fams[0:3], "g2": fams[3:6], "g3": fams[6:9], "twice": fams[9:12], "one_context": fams[12:15]}
    def lesson(parts, exposure, tag, contexts=3):
        edges = [e for f in parts for e in f["edges"]]
        clauses = " and ".join(f"the {a} {r} the {b}" for a, r, b in (edges if exposure % 2 == 0 else edges[::-1]))
        text = TEMPLATES[exposure % len(TEMPLATES)].format(clauses=clauses)
        return [cmd("text", text_features(text, DIM), [m for f in parts for m in f["members"]], f"{tag}_c{exposure % contexts}", "scene", edges)]
    scene_blocks = [lesson([f], e, f["id"]) for f in fams for e in range(5)]
    scene_blocks += [lesson(groups[g], e, g) for g in ("g1", "g2", "g3") for e in range(5)]
    scene_blocks += [lesson(groups["twice"], e, "twice") for e in range(2)]
    scene_blocks += [lesson(groups["one_context"], e, "one_context", contexts=1) for e in range(5)]
    world = groups["g1"] + groups["g2"] + groups["g3"]
    scene_blocks += [lesson(world, e, "world") for e in range(5)]
    blocks["scenes"] = scene_blocks          # families before scenes before world: order is kept

    # interleave: the text stream is the backbone; the other blocks keep their own order, at random places
    stream = [[c] for c in text_commands]
    for name in ("voices", "senses", "scenes"):
        items = blocks[name] if name == "scenes" else rng.sample(blocks[name], len(blocks[name]))
        slots = sorted(rng.randrange(len(stream) + 1) for _ in items)
        out = []; i = 0
        for pos, item in zip(slots, items):
            while i < pos:
                out.append(stream[i]); i += 1
            out.append(item)
        out += stream[i:]; stream = out
    commands = [c for b in stream for c in b]
    meta = {"expectations": expectations, "known": known, "novel": novel, "both": both, "together": together, "apart": apart,
            "groups": groups, "fams": fams, "packet": packet, "take": take, "sensory": sensory, "cmd": cmd, "noisy": noisy,
            "text_events": {c.event_key for c in text_commands}}
    return commands, meta


def check(organism, kernel, meta, seed) -> dict:
    from run_observer_long_life import checkpoint_score
    from sidecar_heat import score_changing_world
    from sidecar_recall import imagine, recall, relive, simulate
    from sidecar_recognize import read_wave
    from sidecar_ring import recognise
    from sidecar_fold import depth_of, unfold
    from sidecar_stance import proposition_key, read_stance
    from verdant_kernel import VerdantKernel
    from verdant_kernel.models import KernelState
    fp = kernel.fingerprint(); out: dict = {}
    label = {c: x.label for c, x in kernel.state.concepts.items()}; ids = {v: k for k, v in label.items()}
    E = meta["expectations"]
    lesson_n = len(kernel.state.processed_event_keys)

    # T text
    try:
        heat = organism.layer("HeatDevelopmentPipeline")
        score = checkpoint_score(kernel, E, 10 ** 9)
        cw = score_changing_world(kernel, E, heat.heat_log if heat else None, 10 ** 9)
        sp = {frozenset(f["members"]) for f in E["families"] if f["expectation"].get("exact_candidate_promotion_eligible")} | \
             {frozenset(f["revision"]["allowed_revision"]) for f in E["families"] if f.get("revision", {}).get("allowed_revision")}
        text_labels = {m for f in E["families"] for m in f["members"]} | {m for f in E["families"] for m in f.get("late_members", [])}
        active = [frozenset(label[m] for m in unfold(kernel, s.member_concept_ids)) for sid, s in kernel.state.structures.items()
                  if kernel.structure_is_available(sid)]
        active_text = [a for a in active if a <= text_labels]
        g = score["groups"]; P = [x for x in ("massed", "spaced_short", "spaced_long", "returning") if x in g]
        out["T_text"] = {"kept": f'{sum(g[x].get("kept", 0) for x in P)}/{sum(g[x]["cues"] for x in P)}',
                         "promoted": f'{sum(g[x].get("promoted", 0) for x in P)}/{sum(g[x]["families"] for x in P)}',
                         "active_wrong": len([a for a in active_text if a not in sp]),
                         "reversals_revised": f'{cw["revision"]["revised_correctly"]}/{sum(1 for r in cw["families"].values() if r["should_revise"] and r["promoted"])}',
                         "controls_revised": cw["revision"]["revised_wrongly"],
                         "failing_group_promotions": sum(g[x].get("promoted", 0) for x in ("under_exposed", "single_context", "once", "pairs_only") if x in g),
                         "heat_auc_at_end": cw["heat"]["auc_reversed_vs_controls_at_end"]}
    except Exception as exc:
        out["T_text"] = {"error": f"{type(exc).__name__}: {exc}"}

    # V voices
    try:
        rows = []
        for group, items in (("known", meta["known"]), ("never_heard", meta["novel"])):
            for name, v in items:
                for e in range(3):
                    f = meta["sensory"].translate(kernel, meta["packet"](meta["take"](v, f"test{name}{e}")), None).feature_vector
                    rd = read_wave(kernel, f, "native_audio", view="per_sense")
                    rows.append((group, name, rd.best if rd else None, rd.unknown if rd else None))
        K = [r for r in rows if r[0] == "known"]; N = [r for r in rows if r[0] == "never_heard"]
        out["V_voices"] = {"known_named": f"{sum(r[2] == r[1] for r in K)}/{len(K)}",
                           "never_heard_over_half_unknown": f"{sum((r[3] or 0) > 0.5 for r in N)}/{len(N)}",
                           "unknown_mean": {"known": round(float(np.mean([r[3] or 0 for r in K])), 3), "never_heard": round(float(np.mean([r[3] or 0 for r in N])), 3)}}
    except Exception as exc:
        out["V_voices"] = {"error": f"{type(exc).__name__}: {exc}"}

    # B binding
    state_json = kernel.state.model_dump_json()
    def bond(x, y):
        return max((b.strength for b in kernel.state.plasticity_associations.values() if set(b.concept_ids) == {ids.get(x), ids.get(y)}), default=0.0)
    def brought(sound_base, name=None):
        from verdant_organism import Organism
        fork = VerdantKernel.from_state(KernelState.model_validate_json(state_json)); twin = Organism(organism.parts)
        c = meta["cmd"]("audio", meta["noisy"](sound_base), [name] if name else [], "probe", "probe"); twin.advance(fork, c)
        w = next(w for w in reversed(fork.state.workspace_cycle_events) if any(a.candidate.source_kind.value in ("local_association", "earned_structure") for a in w.report.assessments)) \
            if fork.state.workspace_cycle_events else None
        flab = {cc: x.label for cc, x in fork.state.concepts.items()}
        return set() if w is None else {flab[m] for a in w.report.assessments if a.candidate.source_kind.value in ("local_association", "earned_structure")
                                        and a.disposition.value == "admit" for m in a.candidate.binding_refs if m in flab}
    try:
        tb = [bond(p["name"], q["name"]) for p, q in meta["together"]]; ab = [bond(p["name"], q["name"]) for p, q in meta["apart"]]
        out["B_binding"] = {"bond_together": [round(x, 3) for x in tb], "bond_apart": [round(x, 3) for x in ab],
                            "unnamed_sound_brings_partner": {"together": f'{sum(p["name"] in brought(q["sound"]) for p, q in meta["together"])}/{len(meta["together"])}',
                                                             "apart": f'{sum(p["name"] in brought(q["sound"]) for p, q in meta["apart"])}/{len(meta["apart"])}'}}
    except Exception as exc:
        out["B_binding"] = {"error": f"{type(exc).__name__}: {exc}"}

    # L look back
    try:
        views = {t["name"]: kernel.state.concepts[ids[t["name"]]].attributes.get("view::visual") for t in meta["both"]}
        def unitv(v):
            z = np.asarray(v["real"]) + 1j * np.asarray(v["imag"]); return z / np.linalg.norm(z)
        hits = 0
        for t in meta["both"]:
            S = kernel._project_effect(kernel._validated_feature_array(meta["noisy"](t["sound"])), "audio")
            shares, _u = recognise(kernel, S, "audio"); heard_as = label[shares[0][0]] if shares else None
            fresh = kernel._project_effect(kernel._validated_feature_array(meta["noisy"](t["look"])), "visual")
            if heard_as == t["name"] and views.get(heard_as):
                own = abs(np.vdot(unitv(views[heard_as]), fresh)); other = max(abs(np.vdot(unitv(views[o]), fresh)) for o in views if o != t["name"] and views[o])
                hits += own > other
        out["L_look_back"] = f"{hits}/{len(meta['both'])}"
    except Exception as exc:
        out["L_look_back"] = {"error": f"{type(exc).__name__}: {exc}"}

    # F folds
    try:
        def leaves(sid):
            return frozenset(label[m] for m in unfold(kernel, kernel.state.structures[sid].member_concept_ids))
        rows = {}
        for gname, fams in meta["groups"].items():
            want = frozenset(m for f in fams for m in f["members"])
            hit = [sid for sid in kernel.state.structures if kernel.structure_is_available(sid) and leaves(sid) == want]
            rows[gname] = {"folded": bool(hit), "depth": max((depth_of(kernel, s) for s in hit), default=0)}
        world = frozenset(m for g in ("g1", "g2", "g3") for f in meta["groups"][g] for m in f["members"])
        rows["world"] = {"folded": any(kernel.structure_is_available(s) and leaves(s) == world for s in kernel.state.structures)}
        out["F_folds"] = rows
    except Exception as exc:
        out["F_folds"] = {"error": f"{type(exc).__name__}: {exc}"}

    # S stance
    try:
        st = read_stance(kernel); by_kind = collections.defaultdict(list)
        for c in E.get("claims", []):
            key = proposition_key(c["subject"], c["predicate"], c["object"])
            if key in st:
                by_kind[c["kind"]].append(st[key]["tension"])
        out["S_stance"] = {k: round(statistics.median(v), 3) for k, v in sorted(by_kind.items())}
    except Exception as exc:
        out["S_stance"] = {"error": f"{type(exc).__name__}: {exc}"}

    # I imagination / simulation
    try:
        keys = [k for k in kernel.state.processed_event_keys if k in meta["text_events"]]
        r = random.Random(seed); picks = r.sample(keys, 5)
        relived = sum(1 for k in picks if relive(kernel, k) is not None)
        cue = meta["both"][0]["name"]; rec = recall(kernel, cue)
        base = picks[0]; names = list(relive(kernel, base).concept_ids)
        other = next(l for l in label.values() if l not in names)
        im = imagine(kernel, base, label[names[0]] if names[0] in label else names[0], other)
        from verdant_organism import Organism
        twin = Organism(organism.parts)
        sim = simulate(kernel, twin.pipeline, meta["cmd"]("visual", meta["noisy"](meta["both"][0]["look"]), [], "probe-sim", "sim"))
        out["I_imagination"] = {"relived": f"{relived}/5", "recall_ok": rec is not None, "imagined_kinds": sorted({b[1].split(' ')[0] for b in getattr(im, "brought", ())})[:3],
                                "simulate_left_mind_unchanged": sim.organism_unchanged}
    except Exception as exc:
        out["I_imagination"] = {"error": f"{type(exc).__name__}: {exc}"}
    out["mind_unchanged_by_checks"] = kernel.fingerprint() == fp
    out["lessons"] = lesson_n
    return out


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=9001); ap.add_argument("--text-lessons", type=int, default=200)
    ap.add_argument("--parts", choices=("default", "lean"), default="default"); ap.add_argument("--horizon", choices=("76", "lived"), default="76"); ap.add_argument("--sleep-priority", choices=("confirmed", "neglected"), default=None); ap.add_argument("--save-state", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    from verdant_organism import Organism, Parts
    import dataclasses
    parts = Parts() if a.parts == "default" else Parts().lean()
    if a.horizon == "lived":
        parts = dataclasses.replace(parts, horizon_lived=True)
    if a.sleep_priority:
        parts = dataclasses.replace(parts, sleep_priority=a.sleep_priority)
    organism = Organism(parts)
    commands, meta = build_life(a.seed, a.text_lessons, organism)
    kernel = organism.new_kernel(seed=2301, state_dim=DIM, run_label="whole-life")
    import time; t0 = time.time()
    for i, c in enumerate(commands, 1):
        organism.advance(kernel, c)
        if i % 100 == 0:
            print(f"lesson {i}/{len(commands)}  {time.time() - t0:.0f}s", flush=True)
    result = {"schema": "verdant.observer.whole_life.v0", "seed": a.seed, "parts": a.parts, "horizon": a.horizon, "lessons": len(commands),
              "fingerprint": kernel.fingerprint(), "organism": organism.report(), "checks": check(organism, kernel, meta, a.seed),
              "minutes": round((time.time() - t0) / 60, 1)}
    result["organism"].get("questions", {}).pop("by_group", None); result["sleep_priority"] = parts.sleep_priority
    if a.save_state:
        a.save_state.write_text(kernel.state.model_dump_json())
    a.out.write_text(json.dumps(result, indent=1, default=str))
    print(json.dumps({"fingerprint": result["fingerprint"][:16], **result["checks"]}, indent=1, default=str))


if __name__ == "__main__":
    main()
