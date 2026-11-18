"""Observer: imagining how a never-met combination sounds or looks, then hearing or seeing it for real.

Two small worlds, each with ground truth known only to this script:
  hearing  8 synthetic voices (each a concept). The organism hears mixtures of 2 or 3 voices at
           varying loudness through a 48-band ear. Some pairs are never heard together.
  sight    8 shapes (each a concept). The organism sees scenes of two shapes through the media
           gateway and perception; a scene's description is the pooled appearance of the objects
           perception tracked. Some pairs are never seen together.

For each never-met pair (A, C): take a real memory of A with B, imagine it with B swapped for C,
then make that exact scene for real (same loudness / positions / noise) and teach it to throwaway
copies of the organism: straight away, and after 20 scenes of new things. Predictors compared
(fixed in docs/LOOKS_ACROSS_SENSES_V0.md before running): unchanged memory, average look (the old
guess), shares (each piece's own share, learned from the record), wrong newcomer, true look
(diagnostic ceiling).
"""
from __future__ import annotations

import argparse, hashlib, itertools, json, math, random, sys, tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "workbench" / "backend"), str(REPO / "curriculum_packs")]
from generate_controls_pack_v0 import Tokens  # noqa: E402
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel  # noqa: E402

RATE = 8000


# ------------------------------------------------------------------ hearing world
def make_voice(f0: float, tilt: float, breath: float, seed: int):
    def sound(loud: float, detune: float, seconds: float = 0.6) -> np.ndarray:
        t = np.arange(int(RATE * seconds)) / RATE; f = f0 * (1 + detune); w = np.zeros_like(t)
        for k in range(1, 16):
            if k * f < RATE / 2 - 200:
                w += np.sin(2 * np.pi * k * f * t) / k ** tilt
        w /= np.max(np.abs(w)) + 1e-9
        w = (1 - breath) * w + breath * np.random.default_rng(seed).standard_normal(t.size) * 0.5
        env = np.minimum(1.0, np.minimum(t, t[-1] - t) / 0.03)
        return loud * env * w / (np.max(np.abs(w)) + 1e-9)
    return sound


def fine_ear(sound: np.ndarray, bands: int = 48) -> list[float]:
    spectrum = np.abs(np.fft.rfft(sound * np.hanning(sound.size))) ** 2; freqs = np.fft.rfftfreq(sound.size, 1 / RATE)
    edges = np.geomspace(80.0, 3800.0, bands + 1)
    energy = np.array([spectrum[(freqs >= lo) & (freqs < hi)].sum() for lo, hi in zip(edges[:-1], edges[1:])]) + 1e-12
    level = np.log(energy); return [float(v) for v in level - level.mean()]


class Hearing:
    modality = "audio"

    def __init__(self, rng: random.Random, tokens: Tokens):
        recipes = [(110, 2.2, 0.0), (147, 0.6, 0.25), (196, 1.4, 0.0), (262, 2.0, 0.25),
                   (349, 0.8, 0.0), (466, 1.6, 0.25), (622, 1.0, 0.0), (831, 2.4, 0.0)]
        self.things = {tokens.new(): make_voice(f, t, b, 900 + i) for i, (f, t, b) in enumerate(recipes)}
        new = [(130, 1.2, 0.1), (520, 0.7, 0.0), (740, 1.9, 0.2), (175, 0.5, 0.0)]
        self.filler_things = {tokens.new(): make_voice(f, t, b, 950 + i) for i, (f, t, b) in enumerate(new)}
        self.rng = rng

    def recipe(self, names):
        return {"parts": [(n, self.rng.uniform(0.3, 0.7)) for n in names], "detune": self.rng.uniform(-0.005, 0.005)}

    def render(self, recipe, workdir: Path, tag: str):
        lib = {**self.things, **self.filler_things}
        return fine_ear(sum(lib[n](loud, recipe["detune"]) for n, loud in recipe["parts"]))


# ------------------------------------------------------------------ sight world
class Sight:
    modality = "visual"

    def __init__(self, rng: random.Random, tokens: Tokens):
        from run_observer_one_door import KINDS
        self.things = {tokens.new(): (k, 235 - 9 * i) for i, k in enumerate(KINDS[:8])}
        self.filler_things = {tokens.new(): (KINDS[8], 210), tokens.new(): (KINDS[9], 190)}
        self.rng = rng

    def recipe(self, names):
        names = list(names); self.rng.shuffle(names); parts = []
        for side, n in enumerate(names):
            x0 = 14 + side * (82 // max(1, len(names)))
            parts.append((n, x0 + self.rng.uniform(8, 18), self.rng.uniform(26, 70), int(round(11 * self.rng.uniform(0.9, 1.1)))))
        return {"parts": parts, "noise": self.rng.uniform(0, 4), "seed": self.rng.randrange(1 << 30)}

    def render(self, recipe, workdir: Path, tag: str):
        import cv2
        from run_observer_one_door import draw
        from run_observer_sensory_hard_tests import FPS, SIZE, _kernel, _write_video
        from verdant_media import ImportOptions, VerdantMediaGateway
        from verdant_perception import VerdantPerceptionPipeline
        lib = {**self.things, **self.filler_things}; noise = np.random.default_rng(recipe["seed"]); frames = []
        for f in range(8):
            frame = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
            for n, x, y, half in recipe["parts"]:
                kind, level = lib[n]; draw(frame, kind, x, y + 1.5 * f * (1 if x < 48 else -1), half, level)
            if recipe["noise"]:
                frame = np.clip(frame.astype(np.float64) + noise.normal(0, recipe["noise"], frame.shape), 0, 255).astype(np.uint8)
            frames.append(frame)
        path = workdir / f"{tag}.mp4"; _write_video(path, frames); eye = _kernel(7, f"eye-{tag}")
        got = VerdantMediaGateway().import_path(eye, path, output_dir=workdir / f"{tag}_out", options=ImportOptions(video_fps=FPS, include_video_audio=False))
        VerdantPerceptionPipeline().process(eye, got.temporal_event_ids, {got.sensory_result.archive.archive_id: got.sensory_result.archive_path})
        tracks = []
        for cand in eye.state.object_candidates.values():
            seen = [eye.state.object_observations[o] for o in cand.observation_ids if o in eye.state.object_observations]
            seen = [o for o in seen if o.kind.value == "visible" and o.appearance_features]
            if seen:
                where = [o.position for o in seen if o.position is not None]
                xy = np.mean(where, axis=0) if where else np.array([0.5, 0.5])
                xy = xy / SIZE if np.max(xy) > 1.5 else xy
                tracks.append((len(seen), np.mean([o.appearance_features for o in seen], axis=0), xy))
        tracks.sort(key=lambda t: -t[0]); used = tracks[: len(recipe["parts"])]
        self.last_objects = len(tracks)
        if not getattr(self, "placed", False):
            return [float(v) for v in np.mean([a for _n, a, _xy in used], axis=0)]
        used.sort(key=lambda t: t[2][0]); lw = len(used[0][1]); out = np.zeros(2 * (lw + 2))   # what is where, left to right
        for i, (_n, a, xy) in enumerate(used[:2]):
            out[i * (lw + 2):i * (lw + 2) + lw] = a; out[i * (lw + 2) + lw:(i + 1) * (lw + 2)] = xy
        return [float(v) for v in out]


# ------------------------------------------------------------------ the run
def command(world, key: str, names, features) -> ExperienceCommand:
    return ExperienceCommand(event_key=key, source_ref=f"senses::{key}", modality=world.modality, feature_vector=features,
                             payload_sha256=hashlib.sha256(json.dumps(features).encode()).hexdigest(),
                             concept_proposals=[ConceptProposal(label=n) for n in sorted(names)],
                             metadata={"context_id": "scene_" + "_".join(sorted(names))})


def align(a, b) -> float:
    return float(abs(np.vdot(a, b)))


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--sense", choices=("hearing", "sight"), required=True)
    ap.add_argument("--seed", type=int, default=11); ap.add_argument("--exposures", type=int, default=3)
    ap.add_argument("--held-out", type=int, default=8); ap.add_argument("--filler", type=int, default=20)
    ap.add_argument("--sight-description", choices=("pooled", "placed"), default="pooled")
    ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    from sidecar_bond_clock import install_changes_only; install_changes_only()
    from run_observer_long_life import build_pipeline, promote_eligible
    from run_observer_imagination_reality import real_beat
    from sidecar_recall import imagine, relive, _experience_parts
    from sidecar_looks import hearing, sight, placed_sight, learn_shares, imagined_look

    rng = random.Random(a.seed); tokens = Tokens(rng)
    world = Hearing(rng, tokens) if a.sense == "hearing" else Sight(rng, tokens)
    world.placed = a.sight_description == "placed"
    names = sorted(world.things); pairs = list(itertools.combinations(names, 2)); rng.shuffle(pairs)
    held = pairs[: a.held_out]; heard = pairs[a.held_out:]
    held_set = {frozenset(p) for p in held}
    scenes = [p for p in heard for _ in range(a.exposures)]
    if a.sense == "hearing":
        triples = [t for t in itertools.combinations(names, 3) if not any(frozenset(x) in held_set for x in itertools.combinations(t, 2))]
        rng.shuffle(triples); scenes += triples[:20]
    rng.shuffle(scenes)
    work = Path(tempfile.mkdtemp(prefix=f"senses_{a.sense}_"))
    kernel = VerdantKernel(seed=a.seed, state_dim=64, run_label=f"senses-{a.sense}")
    pipe, structures = build_pipeline("reunion"); recipes = {}; objects = []
    for i, scene in enumerate(scenes):
        key = f"{a.sense}-{i:03d}"; recipes[key] = world.recipe(scene)
        feats = world.render(recipes[key], work, key); objects.append(getattr(world, "last_objects", len(scene)))
        pipe.advance(kernel, command(world, key, scene, feats))
        if (i + 1) % 20 == 0:
            promote_eligible(kernel, structures, 4)
    print(f"grew on {len(scenes)} scenes; concepts {len(kernel.state.concepts)}; structures {len(kernel.state.structures)}", flush=True)
    if a.sense == "hearing":
        sense = hearing(len(feats), world.modality)
    elif world.placed:
        sense = placed_sight(len(feats) // 2 - 2, 2, world.modality)
    else:
        sense = sight(len(feats), world.modality)
    # how different two scenes look: same pair, places swapped (pooled sight cannot tell them apart)
    order_test = []
    if a.sense == "sight":
        for j, (x, y) in enumerate(heard[:4]):
            r1 = world.recipe((x, y)); r2 = json.loads(json.dumps(r1)); r2["parts"] = [(r1["parts"][1][0], *r1["parts"][0][1:]), (r1["parts"][0][0], *r1["parts"][1][1:])]
            f1, f2 = world.render(r1, work, f"ord{j}a"), world.render(r2, work, f"ord{j}b")
            order_test.append(align(kernel._project_effect(kernel._validated_feature_array(f1), world.modality),
                                    kernel._project_effect(kernel._validated_feature_array(f2), world.modality)))
    shares = learn_shares(kernel, sense)
    filler = []
    fnames = sorted(world.filler_things)
    for j in range(a.filler):
        sc = tuple(rng.sample(fnames, 2)) if len(fnames) > 2 else (tuple(fnames) if j % 3 else (fnames[j % len(fnames)],))
        r = world.recipe(sc); filler.append(command(world, f"{a.sense}-filler-{j:02d}", sc, world.render(r, work, f"filler{j}")))
    fp = kernel.fingerprint(); state_json = kernel.state.model_dump_json()
    label = {c: x.label for c, x in kernel.state.concepts.items()}
    top = 3 if len(kernel.state.concepts) < 20 else 6
    rows = []
    for n, (A, C) in enumerate(held):
        key = next(k for k in sorted(recipes) if A in {p[0] for p in recipes[k]["parts"]} and len(recipes[k]["parts"]) == 2)
        B = next(p[0] for p in recipes[key]["parts"] if p[0] != A)
        wrong = next(x for x in names if x not in (A, B, C))
        real_recipe = json.loads(json.dumps(recipes[key])); real_recipe["parts"] = [(C if p[0] == B else p[0], *p[1:]) for p in real_recipe["parts"]]
        true = world.render(real_recipe, work, f"real{n}"); scene = {A, C}
        cmd = command(world, f"{a.sense}-real-{n:02d}", scene, true)
        preds = {"unchanged": imagine(kernel, key, B, B, context="now", second_step=False, top=top),
                 "average_look": imagine(kernel, key, B, C, context="now", top=top),
                 "shares": imagine(kernel, key, B, C, context="now", top=top, look=imagined_look(kernel, shares, key, B, C)),
                 "wrong_newcomer": imagine(kernel, key, B, wrong, context="now", top=top),
                 "true_look": imagine(kernel, key, B, C, context="now", top=top, look=(true, world.modality))}
        row = {"trial": n, "memory": key, "swap": f"{B} -> {C}", "kept": A}
        for when in ("now", "later"):
            from verdant_kernel.models import KernelState
            fork = VerdantKernel.from_state(KernelState.model_validate_json(state_json)); p2, _ = build_pipeline("reunion")
            if when == "later":
                for c in filler:
                    p2.advance(fork, c)
            p2.advance(fork, cmd); real = real_beat(fork, cmd)
            got = [l for l, _ in real["resonance"][:top]]
            row[when] = {"real_top": got,
                         "sensing": {k: align(v.sensed, real["sensed"]) for k, v in preds.items()},
                         "came_to_mind": {k: len({l for l, _ in v.readout[:top]} & set(got)) / top for k, v in preds.items()},
                         "top1": {k: v.readout[0][0] == got[0] for k, v in preds.items()}}
        rows.append(row); print(json.dumps({"swap": row["swap"], **{w: {k: round(x, 3) for k, x in row[w]["sensing"].items()} for w in ("now",)},
                                            "mind_now": row["now"]["came_to_mind"]}), flush=True)
    summary = {"sense": a.sense, "sight_description": a.sight_description if a.sense == "sight" else None,
               "places_swapped_alike": round(float(np.mean(order_test)), 4) if order_test else None, "scenes": len(scenes), "trials": len(rows), "top_k": top, "description_width": len(feats),
               "concepts": len(kernel.state.concepts), "structures": len(kernel.state.structures),
               "objects_tracked_per_scene": None if a.sense == "hearing" else {"mean": float(np.mean(objects)), "min": int(min(objects))},
               "shares": {"experiences": shares.experiences, "max_recovery_residual": shares.max_recovery_residual,
                          "mean_unknown": round(float(np.mean(list(shares.unknown.values()))), 3)}}
    for when in ("now", "later"):
        R = [r[when] for r in rows]
        summary[when] = {"sensing": {k: round(float(np.mean([r["sensing"][k] for r in R])), 4) for k in R[0]["sensing"]},
                         "came_to_mind": {k: round(float(np.mean([r["came_to_mind"][k] for r in R])), 3) for k in R[0]["came_to_mind"]},
                         "top1": {k: sum(r["top1"][k] for r in R) for k in R[0]["top1"]},
                         "shares_beat_average_on_sensing": sum(r["sensing"]["shares"] > r["sensing"]["average_look"] for r in R),
                         "shares_vs_average_came_to_mind": {"better": sum(r["came_to_mind"]["shares"] > r["came_to_mind"]["average_look"] for r in R),
                                                            "same": sum(r["came_to_mind"]["shares"] == r["came_to_mind"]["average_look"] for r in R),
                                                            "worse": sum(r["came_to_mind"]["shares"] < r["came_to_mind"]["average_look"] for r in R)}}
    summary["organism_unchanged"] = kernel.fingerprint() == fp
    a.out.write_text(json.dumps({"schema": "verdant.observer.imagination_senses.v0", "summary": summary, "trials": rows}, indent=1, default=str))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
