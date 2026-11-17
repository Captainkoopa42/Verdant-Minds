"""Observer: can the mind learn to use a voice by listening to itself?

The voice  An adjustable sound-maker with three controls: pitch (5 settings), brightness
           (3: how much of the sound is in its upper harmonics) and breath (2: clean or airy).
The ear    Every sound, its own or anyone's, is written to a WAV and goes through the ordinary
           media gateway. Only the ear's own description of what it heard is kept.
Babbling   The mind works the controls and hears the result. Each babble is one ordinary
           experience through the same door as lessons and sight: what it heard, together
           with the three control settings it used (its own action, marked as such).
           Only SOME combinations of the controls are ever babbled.
Imitation  A "parent" makes a sound (different loudness, slightly off pitch, fresh noise).
           The mind hears it as numbers only, asks its own read-only resonance which control
           settings that sounds like, and answers with its own voice.

Reported: imitation of combinations it babbled, and of combinations it never tried; per
control; how close the echo sounds to the target by the ear's own measure, against a random
setting; and a WAV of target-then-echo pairs to listen to.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "curriculum_packs")]
from generate_controls_pack_v0 import Tokens  # noqa: E402
from run_observer_sensory_hard_tests import _kernel  # noqa: E402
from verdant_development import VerdantDevelopmentPipeline  # noqa: E402
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel  # noqa: E402
from verdant_media import ImportOptions, VerdantMediaGateway  # noqa: E402

RATE = 8000
PITCH = (110.0, 165.0, 220.0, 330.0, 440.0)
BRIGHT = (2.2, 1.2, 0.5)          # spectral tilt: large = dull, small = bright
BREATH = (0.0, 0.25)


def voice(pitch_i: int, bright_i: int, breath_i: int, rng: np.random.Generator, *, loud: float = 0.5, detune: float = 0.0,
          seconds: float = 0.6) -> np.ndarray:
    t = np.arange(int(RATE * seconds)) / RATE; f0 = PITCH[pitch_i] * (1.0 + detune); wave = np.zeros_like(t)
    for k in range(1, 16):
        if k * f0 < RATE / 2 - 200:
            wave += np.sin(2 * np.pi * k * f0 * t) / (k ** BRIGHT[bright_i])
    wave /= np.max(np.abs(wave)) + 1e-9
    wave = (1 - BREATH[breath_i]) * wave + BREATH[breath_i] * rng.standard_normal(t.size) * 0.5
    envelope = np.minimum(1.0, np.minimum(t, t[-1] - t) / 0.03)
    return (loud * envelope * wave / (np.max(np.abs(wave)) + 1e-9)).astype(np.float32)


def ear(sound: np.ndarray, workdir: Path, tag: str, seed: int) -> list[float]:
    path = workdir / f"{tag}.wav"; sf.write(path, sound, RATE, subtype="PCM_16"); kernel = _kernel(seed, f"ear-{tag}")
    VerdantMediaGateway().import_path(kernel, path, output_dir=workdir / f"{tag}_out", options=ImportOptions(audio_window_seconds=0.20))
    samples = sorted(kernel.state.sensory_samples.values(), key=lambda item: item.sequence_number)
    signature = np.mean([s.native_signature for s in samples], axis=0); features = np.mean([s.feature_vector for s in samples], axis=0)
    return [float(v) for v in np.concatenate([signature, features])]


def fine_ear(sound: np.ndarray, bands: int = 48) -> list[float]:
    """A finer ear written for this test only (NOT the media gateway): loudness-normalised energy in
    48 log-spaced frequency bands, 80 Hz to 3.8 kHz, the way a cochlea splits sound by frequency."""
    spectrum = np.abs(np.fft.rfft(sound * np.hanning(sound.size))) ** 2; freqs = np.fft.rfftfreq(sound.size, 1 / RATE)
    edges = np.geomspace(80.0, 3800.0, bands + 1)
    energy = np.array([spectrum[(freqs >= lo) & (freqs < hi)].sum() for lo, hi in zip(edges[:-1], edges[1:])]) + 1e-12
    level = np.log(energy); return [float(v) for v in level - level.mean()]


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=2301); ap.add_argument("--babbles", type=int, default=3)
    ap.add_argument("--wave", action="store_true"); ap.add_argument("--ear", choices=("gateway", "fine"), default="gateway"); ap.add_argument("--gain", type=float, default=1.0, help="Scale of the adapted ear numbers before they enter the field."); ap.add_argument("--out", type=Path, required=True); ap.add_argument("--audio-out", type=Path, default=None)
    a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    if a.wave:
        from sidecar_wave import install_wave; install_wave()
    rng = random.Random(a.seed); noise = np.random.default_rng(a.seed); tokens = Tokens(rng)
    names = {("pitch", i): tokens.new() for i in range(len(PITCH))}
    names.update({("bright", i): tokens.new() for i in range(len(BRIGHT))}); names.update({("breath", i): tokens.new() for i in range(len(BREATH))})
    combos = list(itertools.product(range(len(PITCH)), range(len(BRIGHT)), range(len(BREATH)))); rng.shuffle(combos)
    tried, never_tried = combos[:18], combos[18:]
    # every single setting must have been used at least once, or it has no name to answer with
    assert all(any(c[d] == i for c in tried) for d, n in enumerate((len(PITCH), len(BRIGHT), len(BREATH))) for i in range(n))

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp); count = [0]

        def hear(sound):
            count[0] += 1
            return fine_ear(sound) if a.ear == "fine" else ear(sound, work, f"s{count[0]:04d}", a.seed)
        babbles = [(c, hear(voice(*c, noise, loud=rng.uniform(0.3, 0.8), detune=rng.uniform(-0.02, 0.02)))) for c in tried for _ in range(a.babbles)]
        heard_all = np.array([h for _, h in babbles]); mean, spread = heard_all.mean(axis=0), heard_all.std(axis=0) + 1e-6
        adapt = lambda h: [float(v) for v in a.gain * (np.asarray(h) - mean) / spread]       # adaptation from its own babbling only

        kernel = VerdantKernel(seed=a.seed, state_dim=128, run_label="voice-loop"); pipe = VerdantDevelopmentPipeline(); rng.shuffle(babbles)
        for n, (combo, heard) in enumerate(babbles):
            labels = [names[("pitch", combo[0])], names[("bright", combo[1])], names[("breath", combo[2])]]
            features = adapt(heard)
            pipe.advance(kernel, ExperienceCommand(event_key=f"babble-{n}", source_ref="self-babble", modality="audio", feature_vector=features,
                         payload_sha256=hashlib.sha256(json.dumps(features).encode()).hexdigest(),
                         concept_proposals=[ConceptProposal(label=x) for x in labels],
                         metadata={"context_id": f"babble_{n % 3}", "provenance": "self_action", "is_external_observation": False}))
        fingerprint = kernel.fingerprint(); ids = {c.label: cid for cid, c in kernel.state.concepts.items()}
        # ear-only baseline: nearest average of its own babbles, one control at a time (no mind involved)
        centroid = {(d, i): np.mean([adapt(h) for c, h in babbles if c[d] == i], axis=0) for d, n in enumerate((len(PITCH), len(BRIGHT), len(BREATH))) for i in range(n)}
        ear_only = lambda heard: tuple(min(range(n), key=lambda i: float(np.linalg.norm(centroid[(d, i)] - np.asarray(adapt(heard)))))
                                       for d, n in enumerate((len(PITCH), len(BRIGHT), len(BREATH))))

        def answer(heard) -> tuple[int, int, int]:
            report = kernel.inspect_resonance(adapt(heard), "audio", top_k=len(ids))
            score = {c.concept_id: (c.score, c.contribution.profile_alignment) for c in report.candidates}
            pick = lambda dim, n: max(range(n), key=lambda i: score[ids[names[(dim, i)]]][1 if not a.wave else 0])
            return pick("pitch", len(PITCH)), pick("bright", len(BRIGHT)), pick("breath", len(BREATH))

        def trial(combos_, label):
            rows = {"sounds": 0, "all_three_controls_right": 0, "pitch_right": 0, "brightness_right": 0, "breath_right": 0}
            echo_d, random_d, pairs = [], [], []
            for combo in combos_:
                for _ in range(3):
                    target = voice(*combo, noise, loud=rng.uniform(0.2, 0.9), detune=rng.uniform(-0.03, 0.03)); heard = hear(target)
                    got = answer(heard); rows["sounds"] += 1; base = ear_only(heard)
                    rows["ear_only_all_three"] = rows.get("ear_only_all_three", 0) + (base == combo)
                    rows["ear_only_pitch"] = rows.get("ear_only_pitch", 0) + (base[0] == combo[0])
                    rows["all_three_controls_right"] += got == combo; rows["pitch_right"] += got[0] == combo[0]
                    rows["brightness_right"] += got[1] == combo[1]; rows["breath_right"] += got[2] == combo[2]
                    echo = voice(*got, noise); other = voice(*rng.choice(combos), noise)
                    h_t, h_e, h_o = (np.asarray(adapt(x)) for x in (heard, hear(echo), hear(other)))
                    echo_d.append(float(np.linalg.norm(h_t - h_e))); random_d.append(float(np.linalg.norm(h_t - h_o))); pairs.append((target, echo))
            out = {k: (v if k == "sounds" else round(v / rows["sounds"], 3)) for k, v in rows.items()}
            out["echo_distance_by_ear"] = round(float(np.mean(echo_d)), 3); out["random_setting_distance_by_ear"] = round(float(np.mean(random_d)), 3)
            return out, pairs
        babbled, pairs_a = trial(tried, "babbled"); novel, pairs_b = trial(never_tried, "never tried")
        if kernel.fingerprint() != fingerprint:
            raise RuntimeError("Imitation changed canonical state.")
        if a.audio_out:
            gap = np.zeros(int(RATE * 0.25), dtype=np.float32); long_gap = np.zeros(int(RATE * 0.7), dtype=np.float32); parts = []
            for target, echo in pairs_b[:6]:
                parts += [target, gap, echo, long_gap]
            sf.write(a.audio_out, np.concatenate(parts), RATE, subtype="PCM_16")
    report = {"schema": "verdant.observer.voice_loop.v0", "wave_installed": bool(a.wave), "ear": a.ear, "gain": a.gain, "control_settings": {"pitch": len(PITCH), "brightness": len(BRIGHT), "breath": len(BREATH)},
              "combinations": len(combos), "combinations_babbled": len(tried), "babbles": len(babbles), "ear_numbers_per_sound": len(mean),
              "chance_all_three": round(1 / len(combos), 3), "imitating_combinations_it_babbled": babbled, "imitating_combinations_it_never_tried": novel}
    a.out.write_text(json.dumps(report, indent=1), encoding="utf-8"); print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
