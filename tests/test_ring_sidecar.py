"""sidecar_ring (recognition rings the wave) and sidecar_recognize (one readout for every sense)."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO)]
from verdant_development import VerdantDevelopmentPipeline  # noqa: E402
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel  # noqa: E402

import sidecar_ring  # noqa: E402
from sidecar_recall import _experience_parts, _frames_by_event, relive  # noqa: E402
from sidecar_recognize import read_wave  # noqa: E402

THINGS = "abcdef"


def _cmd(key, modality, feats, names):
    return ExperienceCommand(event_key=key, source_ref="ring-test", modality=modality, feature_vector=list(feats),
                             payload_sha256=hashlib.sha256(repr(list(feats)).encode()).hexdigest(),
                             concept_proposals=[ConceptProposal(label=n) for n in names], metadata={"context_id": "c"})


def _life(ring: bool):
    if ring:
        sidecar_ring.install_ring()
    try:
        rng = np.random.default_rng(0); looks = {w: rng.normal(size=24) for w in THINGS}; sounds = {w: rng.normal(size=16) for w in THINGS}
        k = VerdantKernel(seed=1, state_dim=64, run_label="ring"); p = VerdantDevelopmentPipeline(); feats = {}
        for e in range(4):
            for w in THINGS:
                for key, mod, base, n in ((f"s{w}{e}", "visual", looks, 24), (f"h{w}{e}", "audio", sounds, 16)):
                    if mod == "audio" and w in "ab" and e > 0:
                        continue                                    # a and b: heard once, seen four times
                    f = base[w] + 0.1 * rng.normal(size=n); feats[key] = (mod, f); p.advance(k, _cmd(key, mod, f, (w,)))
        for w in "abc":
            f = sounds[w] + 0.1 * rng.normal(size=16); feats[f"u{w}"] = ("audio", f); p.advance(k, _cmd(f"u{w}", "audio", f, ()))
        return k, feats, looks, sounds
    finally:
        if ring:
            sidecar_ring.uninstall_ring()


@pytest.fixture(scope="module")
def rung():
    return _life(True)


def test_unnamed_input_rings_what_it_is_and_replay_stays_exact(rung):
    k, feats, *_ = rung; fr = _frames_by_event(k); label = {c: x.label for c, x in k.state.concepts.items()}
    for w in "abc":
        assert {label[c] for c in sidecar_ring.rings_of_frame(k, fr[f"u{w}"])} == {w}
    sidecar_ring.install_ring()
    try:
        for key, (mod, f) in feats.items():
            truth = k._project_effect(k._validated_feature_array(f), mod)
            assert np.max(np.abs(_experience_parts(k, relive(k, key)) - truth)) < 1e-9
    finally:
        sidecar_ring.uninstall_ring()


def test_a_guess_never_teaches(rung):
    """A rung concept's profile and views are exactly what its told experiences made them."""
    k, feats, *_ = rung; ids = {x.label: c for c, x in k.state.concepts.items()}
    a = k.state.concepts[ids["a"]].attributes["view::audio"]
    told = [f for key, (mod, f) in feats.items() if key.startswith("ha")]
    mean = np.mean([k._project_effect(k._validated_feature_array(f), "audio") for f in told], axis=0)
    assert a["count"] == len(told) == 1 and np.allclose(np.asarray(a["real"]) + 1j * np.asarray(a["imag"]), mean)
    assert k.state.resonance_profiles[ids["a"]].exposure_count == 4 + 1                      # 4 sights + 1 sound, no rings


def test_without_ringing_the_organism_is_stock():
    stock = _life(False)[0]
    sidecar_ring.install_ring(); sidecar_ring.uninstall_ring()
    again = _life(False)[0]
    assert stock.fingerprint() == again.fingerprint()


def test_per_sense_reading_beats_the_diluted_chord_and_flags_the_unknown(rung):
    k, _feats, looks, sounds = rung; rng = np.random.default_rng(9); fp = k.fingerprint()
    for w in "ab":                                                    # heard once, seen four times
        f = sounds[w] + 0.1 * rng.normal(size=16)
        assert read_wave(k, f, "audio", view="per_sense").best == w
    known = read_wave(k, sounds["c"] + 0.1 * rng.normal(size=16), "audio").unknown
    novel = read_wave(k, rng.normal(size=16), "audio").unknown
    assert novel > 0.5 > known
    assert k.fingerprint() == fp


def test_adaptation_reads_the_cosine_after_removing_the_usual(rung):
    k, *_ = rung; sidecar_ring.install_ring(adapt=True)
    try:
        prof = next(iter(k.state.resonance_profiles.values()))
        F = k._project_effect(k._validated_feature_array(np.ones(24)), "visual"); m = sidecar_ring._sense_mean(k, "visual")
        k._ring_query_modality = "visual"; k._ring_query = (F, m)
        u = k._profile_array(prof)
        a = k.state.concepts[prof.concept_id].attributes["view::visual"]; v = np.asarray(a["real"]) + 1j * np.asarray(a["imag"])
        want = np.vdot(v - m, F - m) / (np.linalg.norm(v - m) * np.linalg.norm(F - m))
        assert abs(np.vdot(u, F) - want) < 1e-12
    finally:
        k._ring_query_modality = None; k._ring_query = None; sidecar_ring.uninstall_ring()
