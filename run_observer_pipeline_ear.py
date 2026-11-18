"""Observer: voices through the REAL sensory pipeline (archive, verification, ingest), built-in ear vs fine ear.

8 known voices are taught by name (4 lessons each, features from the pipeline's own translator,
entering through the same doorway, native_audio). Then new recordings of the known voices and of 4
never-heard voices arrive UNNAMED through VerdantSensoryPipeline.ingest_samples, with ringing on.
Measured: does the right voice ring, does a never-heard voice ring nothing, and the wave readout's
naming and unknown share. Ears: built-in 10 numbers vs install_fine_ear(48).
"""
from __future__ import annotations

import argparse, hashlib, json, random, sys, tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "workbench" / "backend"), str(REPO / "curriculum_packs")]


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--ear", choices=("builtin", "fine"), required=True)
    ap.add_argument("--seed", type=int, default=41); ap.add_argument("--out", type=Path, required=True); a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    from sidecar_bond_clock import install_changes_only; install_changes_only()
    from sidecar_ring import install_ring, rings_of_frame; install_ring(adapt=True)
    if a.ear == "fine":
        from sidecar_ear import install_fine_ear; install_fine_ear(48)
    from generate_controls_pack_v0 import Tokens
    from run_observer_imagination_senses import RATE, make_voice
    from run_observer_long_life import build_pipeline
    from run_observer_one_wave import VOICES
    from sidecar_recall import _frames_by_event
    from sidecar_recognize import read_wave
    from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel
    from verdant_sensory.pipeline import NativeModality, NativeSamplePacket, VerdantSensoryPipeline

    rng = random.Random(a.seed); tokens = Tokens(rng); order = list(range(len(VOICES))); rng.shuffle(order)
    extra = [(175, 0.5, 0.0), (740, 1.9, 0.2)]
    recipes = [VOICES[i] for i in order] + extra
    voices = [(tokens.new(), make_voice(*r, seed=600 + j)) for j, r in enumerate(recipes)]
    known, novel = voices[:8], voices[8:]
    sensory = VerdantSensoryPipeline(); work = Path(tempfile.mkdtemp(prefix="pipeline_ear_")); seq = [0]

    def packet(sound):
        pcm = (np.clip(sound / (np.max(np.abs(sound)) + 1e-9) * 0.8, -1, 1) * 32767).astype("<i2").tobytes()
        seq[0] += 1
        return NativeSamplePacket(stream_id="mic", sequence_number=seq[0], timestamp_ns=seq[0] * 1_000_000_000,
                                  modality=NativeModality.AUDIO, media_type="audio/pcm", payload=pcm, sample_rate_hz=RATE)

    def take(voice, tag):
        r = random.Random(f"{a.seed}-{tag}"); return voice(r.uniform(0.3, 0.9), r.uniform(-0.01, 0.01))

    kernel = VerdantKernel(seed=a.seed, state_dim=128, run_label=f"pipeline-ear-{a.ear}")
    pipe, _ = build_pipeline("reunion"); lessons = []
    for name, v in known:
        for e in range(4):
            feats = list(sensory.translate(kernel, packet(take(v, f"{name}{e}")), None).feature_vector)
            lessons.append(ExperienceCommand(event_key=f"lesson-{name}-{e}", source_ref="pipeline-ear", modality="native_audio",
                                             feature_vector=feats, payload_sha256=hashlib.sha256(repr(feats).encode()).hexdigest(),
                                             concept_proposals=[ConceptProposal(label=name)], metadata={"context_id": "lessons"}))
    rng.shuffle(lessons)
    for c in lessons:
        pipe.advance(kernel, c)
    width = len(lessons[0].feature_vector)
    rows = []
    for group, items in (("known", known), ("never_heard", novel)):
        for name, v in items:
            for e in range(4):
                result = sensory.ingest_samples(kernel, [packet(take(v, f"test{name}{e}"))], batch_key=f"b{seq[0]}", archive_path=work / f"a{seq[0]}.tar")
                sample = result.samples[-1]; key = f"sensory:{sample.sample_id}"
                rung = {kernel.state.concepts[c].label for c in rings_of_frame(kernel, _frames_by_event(kernel)[key])}
                rd = read_wave(kernel, sample.feature_vector, "native_audio", view="per_sense")
                rows.append({"group": group, "voice": name, "rang": sorted(rung), "rang_right": rung == {name} if group == "known" else not rung,
                             "readout_best": rd.best if rd else None, "unknown": rd.unknown if rd else None})
    K = [r for r in rows if r["group"] == "known"]; N = [r for r in rows if r["group"] == "never_heard"]
    summary = {"ear": a.ear, "description_width": width, "lessons": len(lessons),
               "known_rang_exactly_right": f'{sum(r["rang_right"] for r in K)}/{len(K)}',
               "never_heard_rang_nothing": f'{sum(r["rang_right"] for r in N)}/{len(N)}',
               "readout_named_known": f'{sum(r["readout_best"] == r["voice"] for r in K)}/{len(K)}',
               "unknown_mean": {"known": round(float(np.mean([r["unknown"] for r in K])), 3), "never_heard": round(float(np.mean([r["unknown"] for r in N])), 3)},
               "never_heard_over_half_unknown": f'{sum(r["unknown"] > 0.5 for r in N)}/{len(N)}',
               "known_over_half_unknown": f'{sum(r["unknown"] > 0.5 for r in K)}/{len(K)}',
               "pipeline_samples_ingested": len(kernel.state.sensory_samples)}
    a.out.write_text(json.dumps({"schema": "verdant.observer.pipeline_ear.v0", "summary": summary, "rows": rows}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
