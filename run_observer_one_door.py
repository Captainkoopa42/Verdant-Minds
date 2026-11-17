"""Observer: one door. Can the same mind that learns from lessons see?

The eye   Synthetic video of a moving shape goes through the ordinary media gateway and
          perception pipeline in a throwaway kernel. All that is taken from it is the
          appearance description of the tracked region (the numbers the perception pipeline
          itself computes). The eye names nothing.
The mind  One kernel, one heartbeat. It is taught two ways through the same door:
          text lessons about families of made-up words, and "a parent pointing": a few
          video episodes of a shape, each given one of those words as its name.
Seeing    New episodes of each shape (new path, size, brightness, noise) arrive as
          appearance numbers only. The mind's own read-only resonance says what it is, and
          its own read-only recall says what goes with it.

Reported: named correctly from sight; the rest of the word's family recalled from sight;
the eye-only baseline (nearest average appearance); never-shown shapes; and two look-alikes
with and without recent context. Stock scoring and the wave sidecar are run side by side.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "curriculum_packs")]
from generate_controls_pack_v0 import RELATIONS, TEMPLATES, Tokens, text_features  # noqa: E402
from run_observer_sensory_hard_tests import FPS, SIZE, _kernel, _write_video  # noqa: E402
from verdant_compilation import VerdantCompilationPipeline  # noqa: E402
from verdant_development import VerdantDevelopmentPipeline  # noqa: E402
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel  # noqa: E402
from verdant_kernel.models import RelationProposal  # noqa: E402
from verdant_media import ImportOptions, VerdantMediaGateway  # noqa: E402
from verdant_perception import VerdantPerceptionPipeline  # noqa: E402
from verdant_structures import VerdantStructurePipeline  # noqa: E402

DIM = 128
KINDS = ("square", "wide_bar", "tall_bar", "disc", "ring", "triangle", "cross", "checker", "stripes", "dots")


def draw(frame: np.ndarray, kind: str, cx: float, cy: float, half: int, level: int) -> None:
    cx, cy = int(round(cx)), int(round(cy)); colour = (level, level, level)
    if kind == "square":
        cv2.rectangle(frame, (cx - half, cy - half), (cx + half, cy + half), colour, -1)
    elif kind == "wide_bar":
        cv2.rectangle(frame, (cx - half, cy - half // 3), (cx + half, cy + half // 3), colour, -1)
    elif kind == "tall_bar":
        cv2.rectangle(frame, (cx - half // 3, cy - half), (cx + half // 3, cy + half), colour, -1)
    elif kind == "disc":
        cv2.circle(frame, (cx, cy), half, colour, -1)
    elif kind == "ring":
        cv2.circle(frame, (cx, cy), half, colour, max(2, half // 3))
    elif kind == "triangle":
        cv2.fillPoly(frame, [np.array([[cx, cy - half], [cx - half, cy + half], [cx + half, cy + half]])], colour)
    elif kind == "cross":
        cv2.rectangle(frame, (cx - half, cy - half // 4), (cx + half, cy + half // 4), colour, -1)
        cv2.rectangle(frame, (cx - half // 4, cy - half), (cx + half // 4, cy + half), colour, -1)
    else:
        cv2.rectangle(frame, (cx - half, cy - half), (cx + half, cy + half), (level // 3,) * 3, -1)
        step = max(2, half // 3)
        for i, x in enumerate(range(cx - half, cx + half, step)):
            for j, y in enumerate(range(cy - half, cy + half, step)):
                on = (i + j) % 2 == 0 if kind == "checker" else i % 2 == 0 if kind == "stripes" else (i % 2 == 0 and j % 2 == 0)
                if on:
                    cv2.rectangle(frame, (x, y), (x + step - 1, y + step - 1), colour, -1)


def episode(kind: str, level: int, rng: random.Random, frames: int = 8) -> list[np.ndarray]:
    half = int(round(12 * rng.uniform(0.85, 1.15))); bright = int(level * rng.uniform(0.9, 1.0)); sigma = rng.uniform(0.0, 6.0)
    x, y = rng.uniform(26, 70), rng.uniform(26, 70); angle = rng.uniform(0, 2 * math.pi); dx, dy = 2.5 * math.cos(angle), 2.5 * math.sin(angle)
    noise = np.random.default_rng(rng.randrange(1 << 30)); out = []
    for _ in range(frames):
        frame = np.zeros((SIZE, SIZE, 3), dtype=np.uint8); draw(frame, kind, x, y, half, bright)
        if sigma:
            frame = np.clip(frame.astype(np.float64) + noise.normal(0, sigma, frame.shape), 0, 255).astype(np.uint8)
        out.append(frame); x = min(max(x + dx, 22), 74); y = min(max(y + dy, 22), 74)
    return out


def eye(frames: list[np.ndarray], workdir: Path, tag: str, seed: int) -> list[float] | None:
    """Appearance description of the most-tracked region, as the perception pipeline computed it."""
    path = workdir / f"{tag}.mp4"; _write_video(path, frames); kernel = _kernel(seed, f"eye-{tag}")
    imported = VerdantMediaGateway().import_path(kernel, path, output_dir=workdir / f"{tag}_out",
                                                 options=ImportOptions(video_fps=FPS, include_video_audio=False))
    archives = {imported.sensory_result.archive.archive_id: imported.sensory_result.archive_path}
    VerdantPerceptionPipeline().process(kernel, imported.temporal_event_ids, archives)
    best: list = []
    for candidate in kernel.state.object_candidates.values():
        seen = [kernel.state.object_observations[o] for o in candidate.observation_ids if o in kernel.state.object_observations]
        seen = [o for o in seen if o.kind.value == "visible" and o.appearance_features]
        if len(seen) > len(best):
            best = seen
    if not best:
        return None
    return [float(v) for v in np.mean([o.appearance_features for o in best], axis=0)]


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=2301); ap.add_argument("--shown", type=int, default=3)
    ap.add_argument("--tests", type=int, default=5); ap.add_argument("--wave", action="store_true"); ap.add_argument("--adapt", action="store_true", help="Describe each sight relative to the average sight shown so far (sensory adaptation).")
    ap.add_argument("--stack", action="store_true", help="Use the recurrence and bond-clock sidecars in the mind."); ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    if a.wave:
        from sidecar_wave import install_wave; install_wave()
    rng = random.Random(a.seed); tokens = Tokens(rng)
    taught = [{"kind": k, "level": 235 - 9 * i} for i, k in enumerate(KINDS[:8])]
    for obj in taught:
        obj["name"] = tokens.new(); obj["family"] = [obj["name"], tokens.new(), tokens.new()]
        obj["edges"] = [(obj["family"][0], rng.choice(RELATIONS), obj["family"][1]), (obj["family"][1], rng.choice(RELATIONS), obj["family"][2])]
    never_shown = [{"kind": KINDS[8], "level": 210}, {"kind": KINDS[9], "level": 190}]
    counter = [0]

    def text_lesson(obj, exposure):
        counter[0] += 1
        clauses = " and ".join(f"the {x} {r} the {y}" for x, r, y in (obj["edges"] if exposure % 2 == 0 else obj["edges"][::-1]))
        text = TEMPLATES[exposure % len(TEMPLATES)].format(clauses=clauses)
        return ExperienceCommand(event_key=f"door-text-{counter[0]}", source_ref="one-door-text", modality="text", feature_vector=text_features(text, DIM),
                                 payload_sha256=hashlib.sha256(text.encode()).hexdigest(), concept_proposals=[ConceptProposal(label=m) for m in obj["family"]],
                                 relation_proposals=[RelationProposal(source_label=x, target_label=y, relation_type=r) for x, r, y in obj["edges"]],
                                 metadata={"context_id": f"{obj['name']}_c{exposure % 3}"})

    def sight_lesson(obj, features):
        counter[0] += 1
        return ExperienceCommand(event_key=f"door-sight-{counter[0]}", source_ref="one-door-sight", modality="visual", feature_vector=features,
                                 payload_sha256=hashlib.sha256(json.dumps(features).encode()).hexdigest(),
                                 concept_proposals=[ConceptProposal(label=obj["name"])], metadata={"context_id": f"{obj['name']}_seen"})

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp); n = [0]

        def look(obj):
            n[0] += 1
            return eye(episode(obj["kind"], obj["level"], rng), work, f"ep{n[0]:03d}", a.seed)
        for obj in taught:
            obj["shown"] = [f for f in (look(obj) for _ in range(a.shown)) if f]; obj["tests"] = [f for f in (look(obj) for _ in range(a.tests)) if f]
        for obj in never_shown:
            obj["tests"] = [f for f in (look(obj) for _ in range(a.tests)) if f]
        blind = sum(a.shown - len(o["shown"]) + a.tests - len(o["tests"]) for o in taught)
    if a.adapt:
        # Adaptation uses only the episodes the parent named; test sights never touch it.
        shown_all = np.array([f for o in taught for f in o["shown"]]); mean, spread = shown_all.mean(axis=0), shown_all.std(axis=0) + 1e-6
        adapt = lambda f: [float(v) for v in (np.asarray(f) - mean) / spread]
        for o in taught + never_shown:
            o["shown"] = [adapt(f) for f in o.get("shown", [])]; o["tests"] = [adapt(f) for f in o["tests"]]

    kernel = VerdantKernel(seed=a.seed, state_dim=DIM, run_label="one-door"); pipe = VerdantDevelopmentPipeline(); structures = VerdantStructurePipeline()
    if a.stack:
        from sidecar_bond_clock import BondClockPlasticityPipeline
        from sidecar_recurrence import ExperienceRecurrenceStructurePipeline
        structures = ExperienceRecurrenceStructurePipeline()
        pipe = VerdantDevelopmentPipeline(structures=structures, plasticity=BondClockPlasticityPipeline())
    schedule = [("text", o, e) for o in taught for e in range(5)] + [("sight", o, i) for o in taught for i in range(len(o["shown"]))]
    rng.shuffle(schedule)
    for step, (how, obj, i) in enumerate(schedule, start=1):
        pipe.advance(kernel, text_lesson(obj, i) if how == "text" else sight_lesson(obj, obj["shown"][i]))
        if step % 20 == 0 or step == len(schedule):
            for cid, cand in sorted(kernel.state.structure_candidates.items()):
                if cand.status.value == "eligible":
                    structures.promote(kernel, cid)
    fingerprint = kernel.fingerprint(); state = kernel.state
    ids = {c.label: cid for cid, c in state.concepts.items()}; label = {v: k for k, v in ids.items()}; recall = VerdantCompilationPipeline()

    def named(features):
        report = kernel.inspect_resonance(features, "visual", top_k=len(ids))
        by_score = label[report.candidates[0].concept_id]
        match = [c.contribution.profile_alignment for c in report.candidates]
        by_profile = label[report.candidates[int(np.argmax(match))].concept_id]
        stand_out = (max(match) - float(np.mean(match))) / (float(np.std(match)) + 1e-12)
        return by_score, by_profile, stand_out
    centroids = {o["name"]: np.mean(o["shown"], axis=0) for o in taught if o["shown"]}
    rows = {"sights": 0, "named_by_the_mind": 0, "named_by_profile_term_alone": 0, "family_recalled_from_sight": 0, "named_by_eye_only_nearest_average": 0}
    known_out, per_object = [], {}
    for obj in taught:
        hits = 0
        for features in obj["tests"]:
            by_score, by_profile, stand_out = named(features); rows["sights"] += 1; known_out.append(stand_out)
            rows["named_by_the_mind"] += by_score == obj["name"]; rows["named_by_profile_term_alone"] += by_profile == obj["name"]; hits += by_score == obj["name"]
            got = {label[c] for c in recall.inspect(kernel, [ids[by_score]]).reconstructed_concept_ids}
            rows["family_recalled_from_sight"] += got == set(obj["family"])
            nearest = min(centroids, key=lambda k: float(np.linalg.norm(centroids[k] - np.asarray(features))))
            rows["named_by_eye_only_nearest_average"] += nearest == obj["name"]
        per_object[obj["kind"]] = f"{hits}/{len(obj['tests'])}"
    new_out = [named(f)[2] for o in never_shown for f in o["tests"]]
    # -M: share of a sight's field effect the known concepts cannot explain (run_observer_unknown_residual)
    from run_observer_unknown_residual import unknown_share
    prof = np.stack([np.asarray(p.real) + 1j * np.asarray(p.imag) for p in state.resonance_profiles.values()])
    def leftover(features, k=None):
        q = kernel._project_effect(kernel._validated_feature_array(features), "visual")
        basis = prof if k is None else prof[np.argsort(-np.abs(prof.conj() @ q))[:k]]
        return unknown_share(q, basis)
    def separation(known, new):
        """Share of (known, new) pairs where the new sight is more unknown: 0.5 = chance, 1.0 = perfect."""
        return round(float(np.mean([[n > k for k in known] for n in new])), 3)
    known_left = {k: [leftover(f, k) for o in taught for f in o["tests"]] for k in (1, 3, None)}
    new_left = {k: [leftover(f, k) for o in never_shown for f in o["tests"]] for k in (1, 3, None)}
    cut = (np.mean(known_out) + np.mean(new_out)) / 2 if new_out else 0.0
    report = {"schema": "verdant.observer.one_door.v0", "wave_installed": bool(a.wave), "adaptation": bool(a.adapt), "stack": bool(a.stack), "shapes_taught": len(taught), "showings_per_shape": a.shown,
              "lessons": len(schedule), "concepts_in_the_mind": len(ids), "structures_promoted": len(state.structures),
              "episodes_where_the_eye_tracked_nothing": blind, "chance": round(1 / len(ids), 3),
              "seeing": {k: (v if k == "sights" else round(v / max(1, rows["sights"]), 3)) for k, v in rows.items()},
              "named_per_shape": per_object,
              "never_shown_shapes": {"sights": len(new_out), "stand_out_known_mean": round(float(np.mean(known_out)), 2),
                                     "stand_out_never_shown_mean": round(float(np.mean(new_out)), 2) if new_out else None,
                                     "stand_out_separation_new_less_than_known": separation([-x for x in known_out], [-x for x in new_out]),
                                     "leftover_separation_by_basis": {("all known" if k is None else f"best {k}"): separation(known_left[k], new_left[k]) for k in known_left},
                                     "leftover_means_known_new_by_basis": {("all known" if k is None else f"best {k}"): [round(float(np.mean(known_left[k])), 3), round(float(np.mean(new_left[k])), 3)] for k in known_left},
                                     "told_apart_at_midpoint": round((sum(k > cut for k in known_out) + sum(x <= cut for x in new_out)) / max(1, len(known_out) + len(new_out)), 3)}}
    if kernel.fingerprint() != fingerprint:
        raise RuntimeError("Seeing changed canonical state.")
    a.out.write_text(json.dumps(report, indent=1), encoding="utf-8"); print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
