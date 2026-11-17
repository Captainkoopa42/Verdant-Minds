"""Observer-only hard tests for the native vision and audio path.

Each scenario writes a small synthetic video (or audio clip) whose ground
truth is known only to this script, imports it through the ordinary
``VerdantMediaGateway`` and ``VerdantPerceptionPipeline`` with default
perceptual and objecthood policies, and then compares what the kernel
recorded against what was in the scene.

Ground truth is never given to the kernel. Nothing here changes a policy,
promotes an object, or has any authority. Scenarios are stress probes, not a
benchmark: several are expected to expose stated limits of a grayscale,
single-stream, saliency-by-median design.

    python run_observer_sensory_hard_tests.py --out sensory_hard_report.json
"""
from __future__ import annotations

import argparse
import json
import math
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf

from verdant_kernel import VerdantKernel
from verdant_media import ImportOptions, VerdantMediaGateway
from verdant_perception import VerdantPerceptionPipeline

SCHEMA = "verdant.observer.sensory_hard_tests.v0"
SIZE = 96
FPS = 5.0


def _kernel(seed: int, label: str) -> VerdantKernel:
    kernel = VerdantKernel(seed=seed, state_dim=64, run_label=label)
    # Same sensory grouping the repository's own perception tests use.
    kernel.update_sensory_policy(
        feature_change_threshold=1.0,
        maximum_event_gap_ns=300_000_000,
        minimum_modalities_per_group=1,
    )
    return kernel


def _write_video(path: Path, frames: list[np.ndarray]) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (SIZE, SIZE))
    if not writer.isOpened():
        raise RuntimeError("Could not open the video writer.")
    for frame in frames:
        writer.write(frame)
    writer.release()


def _box(frame: np.ndarray, cx: float, cy: float, half: int, color) -> None:
    x0, y0 = int(round(cx - half)), int(round(cy - half))
    frame[max(0, y0) : max(0, y0 + 2 * half), max(0, x0) : max(0, x0 + 2 * half)] = color


class Scene:
    """Frames plus the true centre of every object in every frame (or None)."""

    def __init__(self, n: int, background=0) -> None:
        self.frames = [np.full((SIZE, SIZE, 3), background, dtype=np.uint8) for _ in range(n)]
        self.truth: list[dict[str, tuple[float, float] | None]] = [dict() for _ in range(n)]

    def put(self, index: int, name: str, cx: float, cy: float, half: int, color,
            visible: bool = True) -> None:
        if visible:
            _box(self.frames[index], cx, cy, half, color)
            self.truth[index][name] = (cx / (SIZE - 1), cy / (SIZE - 1))
        else:
            self.truth[index][name] = None


def s_single(n=12):
    scene = Scene(n)
    for i in range(n):
        scene.put(i, "a", 12 + i * 6, 30, 7, (220, 220, 220))
    return scene


def s_two_distinct(n=12):
    scene = Scene(n)
    for i in range(n):
        scene.put(i, "a", 12 + i * 6, 26, 7, (230, 230, 230))
        scene.put(i, "b", 84 - i * 6, 68, 6, (130, 130, 130))
    return scene


def s_identical_crossing(n=14):
    scene = Scene(n)
    for i in range(n):
        scene.put(i, "a", 10 + i * 6, 48, 6, (210, 210, 210))
        scene.put(i, "b", 88 - i * 6, 48, 6, (210, 210, 210))
    return scene


def s_occlusion(n, hidden):
    scene = Scene(n)
    for i in range(n):
        scene.put(i, "a", 10 + i * 4.5, 40, 7, (220, 220, 220), visible=i not in hidden)
    return scene


def s_noise(n=12, sigma=14.0, seed=5):
    scene = s_single(n)
    rng = np.random.default_rng(seed)
    for i in range(n):
        noisy = scene.frames[i].astype(np.float64) + rng.normal(0.0, sigma, scene.frames[i].shape)
        scene.frames[i] = np.clip(noisy, 0, 255).astype(np.uint8)
    return scene


def s_lighting_ramp(n=12):
    scene = Scene(n)
    for i in range(n):
        level = int(10 + i * 9)
        scene.frames[i][:] = level
        scene.put(i, "a", 12 + i * 6, 40, 7, (min(255, level + 120),) * 3)
    return scene


def s_clutter(n=12):
    scene = Scene(n, background=20)
    static = [(20, 76, 5, 150), (70, 20, 5, 110), (78, 78, 4, 180)]
    for i in range(n):
        for index, (x, y, half, value) in enumerate(static):
            scene.put(i, f"static{index}", x, y, half, (value,) * 3)
        scene.put(i, "mover", 12 + i * 6, 46, 7, (235, 235, 235))
    return scene


def s_isoluminant(n=12):
    # Red square on a green field with equal luma under BT.601.
    green = (0, 128, 0)            # BGR; luma 0.587*128 = 75.1
    red = (0, 0, 251)              # BGR; luma 0.299*251 = 75.0
    scene = Scene(n)
    for i in range(n):
        scene.frames[i][:] = green
        scene.put(i, "a", 12 + i * 6, 40, 8, red)
    return scene


def s_camera_pan(n=12):
    scene = Scene(n)
    layout = [(20, 30, 6, 220), (48, 60, 6, 150), (70, 24, 5, 190)]
    for i in range(n):
        shift = i * 2
        for index, (x, y, half, value) in enumerate(layout):
            scene.put(i, f"fixed{index}", x + shift, y, half, (value,) * 3)
    return scene


def s_scale_change(n=12):
    scene = Scene(n)
    for i in range(n):
        scene.put(i, "a", 48, 48, 4 + i * 2, (220, 220, 220))
    return scene


def s_large_object(n=10):
    scene = Scene(n)
    for i in range(n):
        # A bright slab covering about 60% of the frame drifts sideways.
        frame = scene.frames[i]
        x0 = 4 + i * 2
        frame[10:86, x0 : x0 + 73] = 215
        scene.truth[i]["slab"] = ((x0 + 36.5) / (SIZE - 1), 48 / (SIZE - 1))
    return scene


def s_many(n=10, count=16):
    scene = Scene(n)
    for i in range(n):
        for k in range(count):
            row, col = divmod(k, 4)
            scene.put(i, f"o{k:02d}", 12 + col * 22 + i, 12 + row * 22, 4, (90 + k * 10,) * 3)
    return scene


def s_dark_on_bright(n=12):
    scene = Scene(n, background=235)
    for i in range(n):
        scene.put(i, "a", 12 + i * 6, 40, 7, (25, 25, 25))
    return scene


def s_static(n=12):
    scene = Scene(n)
    for i in range(n):
        scene.put(i, "a", 40, 40, 7, (220, 220, 220))
    return scene


def s_blank(n=8):
    return Scene(n)


def s_rotation(n=12):
    scene = Scene(n)
    for i in range(n):
        frame = scene.frames[i]
        angle = i * 90.0 / (n - 1)
        box = cv2.boxPoints(((48.0, 48.0), (40.0, 12.0), angle)).astype(np.int32)
        cv2.fillPoly(frame, [box], (220, 220, 220))
        scene.truth[i]["a"] = (48 / (SIZE - 1), 48 / (SIZE - 1))
    return scene


def s_contrast(delta, n=12):
    scene = Scene(n, background=100)
    for i in range(n):
        scene.put(i, "a", 12 + i * 6, 40, 7, (100 + delta,) * 3)
    return scene


def s_tiny(n=12):
    scene = Scene(n)
    for i in range(n):
        frame = scene.frames[i]
        x = 12 + i * 6
        frame[40:43, x : x + 3] = 230
        scene.truth[i]["a"] = ((x + 1) / (SIZE - 1), 41 / (SIZE - 1))
    return scene


def s_gradient_background(n=12):
    scene = Scene(n)
    ramp = np.tile(np.linspace(0, 200, SIZE, dtype=np.uint8), (SIZE, 1))
    for i in range(n):
        scene.frames[i][:] = ramp[:, :, None]
        scene.put(i, "a", 12 + i * 6, 40, 7, (255, 255, 255))
    return scene


def s_heavy_noise(n=12):
    return s_noise(n, sigma=40.0, seed=9)


def s_replacement(n=14):
    # One object leaves; two frames later a different-looking one appears there.
    scene = Scene(n)
    for i in range(n):
        if i < 6:
            scene.put(i, "first", 20 + i * 5, 40, 7, (225, 225, 225))
        elif i >= 8:
            scene.put(i, "second", 45 + (i - 8) * 5, 40, 4, (110, 110, 110))
    return scene


def s_brightness_jump(n=12):
    scene = Scene(n)
    for i in range(n):
        scene.put(i, "a", 12 + i * 6, 40, 7, ((230,) * 3 if i < 6 else (90,) * 3))
    return scene


def s_swap_behind_occluder(n=14):
    # Two identical squares vanish for two frames and return in each other's place.
    scene = Scene(n)
    for i in range(n):
        hidden = i in (6, 7)
        left, right = (30, 66) if i < 6 else (66, 30)
        scene.put(i, "a", left, 40 + (i % 2), 6, (210, 210, 210), visible=not hidden)
        scene.put(i, "b", right, 40 + (i % 2), 6, (210, 210, 210), visible=not hidden)
    return scene


VIDEO_SCENARIOS = [
    ("single_moving_square", s_single, 1, "Baseline: one bright square moving right."),
    ("two_distinct_objects", s_two_distinct, 2, "Two squares of different brightness, opposite directions."),
    ("identical_objects_crossing", s_identical_crossing, 2, "Two identical squares pass through each other."),
    ("occlusion_2_frames", lambda: s_occlusion(14, {6, 7}), 1, "Hidden for 2 frames, returns on its path."),
    ("occlusion_8_frames", lambda: s_occlusion(18, set(range(5, 13))), 1, "Hidden for 8 frames; policy maximum_occlusion_gap is 6."),
    ("sensor_noise", s_noise, 1, "Baseline plus Gaussian pixel noise, sigma 14."),
    ("lighting_ramp", s_lighting_ramp, 1, "Whole scene brightens steadily while the square moves."),
    ("static_clutter", s_clutter, 4, "Three static patches and one mover."),
    ("isoluminant_colour", s_isoluminant, 1, "Red square on green with equal luma: visible only in colour."),
    ("camera_pan", s_camera_pan, 3, "Three fixed objects; the whole view shifts each frame."),
    ("scale_change", s_scale_change, 1, "One square grows from 8 to 52 pixels wide in place."),
    ("large_object", s_large_object, 1, "A slab covering about 60% of the frame drifts."),
    ("sixteen_objects", s_many, 16, "Sixteen small squares; maximum_regions_per_frame is 12."),
    ("dark_on_bright", s_dark_on_bright, 1, "Polarity reversed: dark square, bright field."),
    ("nothing_moves", s_static, 1, "One square that never moves."),
    ("blank_frames", s_blank, 0, "Empty black frames."),
    ("rotation_90", s_rotation, 1, "A 40x12 bar turns through 90 degrees in place."),
    ("contrast_15_levels", lambda: s_contrast(15), 1, "Square only 15 grey levels above the field (threshold is about 20)."),
    ("contrast_30_levels", lambda: s_contrast(30), 1, "Square 30 grey levels above the field."),
    ("tiny_3_pixels", s_tiny, 1, "A 3x3 pixel dot; below minimum_region_area_fraction."),
    ("gradient_background", s_gradient_background, 1, "White square over a strong left-to-right brightness ramp."),
    ("heavy_noise", s_heavy_noise, 1, "Baseline plus Gaussian pixel noise, sigma 40."),
    ("replacement", s_replacement, 2, "One object leaves; a smaller, dimmer one appears nearby 2 frames later."),
    ("brightness_jump", s_brightness_jump, 1, "The square abruptly dims from 230 to 90 mid-path."),
    ("swap_while_hidden", s_swap_behind_occluder, 2, "Two identical squares vanish and return in each other's place."),
]


def run_video(name: str, scene: Scene, true_objects: int, note: str, workdir: Path, seed: int) -> dict:
    path = workdir / f"{name}.mp4"
    _write_video(path, scene.frames)
    kernel = _kernel(seed, f"sensory-hard-{name}")
    row: dict = {"scenario": name, "note": note, "true_objects": true_objects,
                 "frames_written": len(scene.frames)}
    try:
        imported = VerdantMediaGateway().import_path(
            kernel, path, output_dir=workdir / f"{name}_out",
            options=ImportOptions(video_fps=FPS, include_video_audio=False),
        )
        archives = {imported.sensory_result.archive.archive_id: imported.sensory_result.archive_path}
        bound = VerdantPerceptionPipeline().process(kernel, imported.temporal_event_ids, archives)
    except Exception as exc:  # recorded, not hidden
        row["error"] = f"{type(exc).__name__}: {exc}"[:300]
        return row
    state = kernel.state
    frames = bound.report.frames
    region_counts = [len(frame.region_proposals) for frame in frames]
    truth_visible = [sum(1 for value in truth.values() if value is not None) for truth in scene.truth]
    row["frames_decoded"] = len(frames)
    row["regions_per_frame"] = region_counts
    row["true_visible_per_frame"] = truth_visible[: len(frames)]
    row["frames_with_correct_region_count"] = sum(
        1 for found, real in zip(region_counts, truth_visible) if found == real
    )
    # Which true object does each recorded visible observation sit on?
    per_candidate: dict[str, list[str]] = defaultdict(list)
    for candidate_id, candidate in state.object_candidates.items():
        for observation_id in candidate.observation_ids:
            observation = state.object_observations.get(observation_id)
            if observation is None or observation.kind.value != "visible" or observation.position is None:
                continue
            if observation.frame_index >= len(scene.truth):
                continue
            truth = scene.truth[observation.frame_index]
            best, best_distance = "none", 0.12
            for label, centre in truth.items():
                if centre is None:
                    continue
                distance = math.dist(observation.position, centre)
                if distance < best_distance:
                    best, best_distance = label, distance
            per_candidate[candidate_id].append(best)
    candidates = []
    owners: dict[str, set[str]] = defaultdict(set)
    for candidate_id, candidate in sorted(state.object_candidates.items()):
        labels = Counter(per_candidate.get(candidate_id, []))
        dominant, dominant_count = (labels.most_common(1)[0] if labels else ("none", 0))
        total = sum(labels.values())
        for label in labels:
            if label != "none":
                owners[label].add(candidate_id)
        candidates.append({
            "status": candidate.status.value,
            "visible": candidate.visible_observation_count,
            "persistence": candidate.persistence_count,
            "common_motion": candidate.common_motion_count,
            "occlusions": candidate.occlusion_count,
            "reappearances": candidate.reappearance_count,
            "ambiguity": candidate.ambiguity_count,
            "support": round(candidate.support_score, 3),
            "true_objects_touched": dict(labels),
            "purity": round(dominant_count / total, 3) if total else None,
            "dominant": dominant,
        })
    row["object_candidates"] = len(candidates)
    row["candidates"] = candidates
    row["candidates_mixing_two_true_objects"] = sum(
        1 for item in candidates
        if len([key for key in item["true_objects_touched"] if key != "none"]) > 1
    )
    row["true_objects_split_across_candidates"] = sum(1 for ids in owners.values() if len(ids) > 1)
    row["true_objects_never_tracked"] = sum(
        1 for label in {key for truth in scene.truth for key in truth} if label not in owners
    )
    row["candidates_on_nothing"] = sum(1 for item in candidates if item["dominant"] == "none")
    row["fingerprint"] = kernel.fingerprint()
    return row


def run_cross_episode(workdir: Path, seed: int) -> list[dict]:
    """Does an object keep its identity across two separate videos?"""
    rows = []
    for name, second, expect in (
        ("same_object_second_video", s_single(12), 1),
        ("different_object_second_video", None, 2),
    ):
        kernel = _kernel(seed, f"sensory-hard-{name}")
        first = s_single(12)
        if second is None:
            second = Scene(12)
            for i in range(12):
                # A smaller, dimmer, differently placed square.
                second.put(i, "b", 84 - i * 6, 70, 4, (120, 120, 120))
        counts = []
        try:
            for index, scene in enumerate((first, second)):
                path = workdir / f"{name}_{index}.mp4"
                _write_video(path, scene.frames)
                imported = VerdantMediaGateway().import_path(
                    kernel, path, output_dir=workdir / f"{name}_{index}_out",
                    options=ImportOptions(video_fps=FPS, include_video_audio=False),
                )
                archives = {imported.sensory_result.archive.archive_id: imported.sensory_result.archive_path}
                VerdantPerceptionPipeline().process(kernel, imported.temporal_event_ids, archives)
                counts.append(len(kernel.state.object_candidates))
            rows.append({
                "scenario": name, "true_objects": expect,
                "candidates_after_each_video": counts,
                "statuses": sorted(item.status.value for item in kernel.state.object_candidates.values()),
                "episodes_per_candidate": sorted(len(item.episode_ids) for item in kernel.state.object_candidates.values()),
            })
        except Exception as exc:
            rows.append({"scenario": name, "error": f"{type(exc).__name__}: {exc}"[:300]})
    return rows


def run_audio(workdir: Path, seed: int) -> dict:
    rate, duration = 8000, 1.0
    t = np.arange(int(rate * duration)) / rate
    rng = np.random.default_rng(11)
    clips = {
        "silence": np.zeros_like(t),
        "tone_440": 0.5 * np.sin(2 * np.pi * 440 * t),
        "tone_440_quiet": 0.05 * np.sin(2 * np.pi * 440 * t),
        "tone_1760": 0.5 * np.sin(2 * np.pi * 1760 * t),
        "white_noise": 0.3 * rng.standard_normal(t.size),
        "clipped_tone": np.clip(3.0 * np.sin(2 * np.pi * 440 * t), -1.0, 1.0),
        "click_then_silence": np.concatenate([np.ones(8) * 0.9, np.zeros(t.size - 8)]),
    }
    names = ("mean", "rms", "mean_abs", "peak", "zero_crossing", "centroid",
             "band_low", "band_mid", "band_high", "delta")
    out: dict = {}
    for label, data in clips.items():
        kernel = _kernel(seed, f"sensory-hard-audio-{label}")
        path = workdir / f"{label}.wav"
        sf.write(path, data.astype(np.float32), rate, subtype="PCM_16")
        try:
            VerdantMediaGateway().import_path(
                kernel, path, output_dir=workdir / f"{label}_out",
                options=ImportOptions(audio_window_seconds=0.20),
            )
        except Exception as exc:
            out[label] = {"error": f"{type(exc).__name__}: {exc}"[:300]}
            continue
        samples = sorted(kernel.state.sensory_samples.values(), key=lambda item: item.sequence_number)
        vectors = np.asarray([item.feature_vector for item in samples], dtype=np.float64)
        signatures = np.asarray([item.native_signature for item in samples], dtype=np.float64)
        out[label] = {
            "windows": len(samples),
            "features_mean": {name: round(float(value), 4) for name, value in zip(names, vectors.mean(axis=0))},
            "signature_mean": [round(float(value), 4) for value in signatures.mean(axis=0)],
            "all_finite": bool(np.isfinite(vectors).all() and np.isfinite(signatures).all()),
        }

    def distance(a: str, b: str) -> float | None:
        if "signature_mean" not in out.get(a, {}) or "signature_mean" not in out.get(b, {}):
            return None
        return round(float(np.linalg.norm(np.asarray(out[a]["signature_mean"]) - np.asarray(out[b]["signature_mean"]))), 4)

    out["_signature_distances"] = {
        "tone_440 vs tone_440_quiet (same pitch, 10x quieter)": distance("tone_440", "tone_440_quiet"),
        "tone_440 vs tone_1760 (different pitch)": distance("tone_440", "tone_1760"),
        "tone_440 vs white_noise": distance("tone_440", "white_noise"),
        "tone_440 vs clipped_tone": distance("tone_440", "clipped_tone"),
    }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seed", type=int, default=3101)
    parser.add_argument("--out", type=Path, default=None, help="Exclusive-create JSON report path.")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temp:
        workdir = Path(temp)
        video_rows = [
            run_video(name, builder(), true_objects, note, workdir, args.seed)
            for name, builder, true_objects, note in VIDEO_SCENARIOS
        ]
        # Determinism: the same scene in a second fresh kernel.
        repeat = run_video("single_moving_square", s_single(), 1, "repeat", workdir / "..", args.seed) \
            if False else run_video("single_moving_square", s_single(), 1, "repeat", workdir, args.seed)
        cross = run_cross_episode(workdir, args.seed)
        audio = run_audio(workdir, args.seed)
    deterministic = repeat.get("fingerprint") == video_rows[0].get("fingerprint")
    print(f"{'scenario':<28}{'true':>5}{'cands':>6}{'mixed':>6}{'split':>6}{'lost':>5}{'ghost':>6}  regions/frame (found)")
    for row in video_rows:
        if "error" in row:
            print(f"{row['scenario']:<28}{row['true_objects']:>5}  ERROR {row['error']}")
            continue
        print(
            f"{row['scenario']:<28}{row['true_objects']:>5}{row['object_candidates']:>6}"
            f"{row['candidates_mixing_two_true_objects']:>6}{row['true_objects_split_across_candidates']:>6}"
            f"{row['true_objects_never_tracked']:>5}{row['candidates_on_nothing']:>6}  "
            f"{''.join(str(min(9, value)) for value in row['regions_per_frame'])}"
            f"  ({row['frames_with_correct_region_count']}/{row['frames_decoded']} frames right)"
        )
    print(f"\ndeterministic repeat of baseline: {deterministic}")
    for row in cross:
        print("cross-episode:", json.dumps(row))
    print("\naudio:")
    for label, item in audio.items():
        if label.startswith("_"):
            continue
        if "error" in item:
            print(f"  {label:<20} ERROR {item['error']}")
            continue
        f = item["features_mean"]
        print(f"  {label:<20} windows {item['windows']}  rms {f['rms']:.3f}  peak {f['peak']:.3f}  "
              f"zcr {f['zero_crossing']:.3f}  centroid {f['centroid']:.3f}  finite {item['all_finite']}")
    for label, value in audio["_signature_distances"].items():
        print(f"  signature distance, {label}: {value}")
    report = {"schema": SCHEMA, "seed": args.seed, "video": video_rows,
              "deterministic_repeat": deterministic, "cross_episode": cross, "audio": audio,
              "ground_truth_given_to_kernel": False, "behavioral_authority": False}
    if args.out is not None:
        with open(args.out, "x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
