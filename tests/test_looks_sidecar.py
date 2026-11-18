"""sidecar_looks: recovering what a sense handed in, learning each piece's share, imagining a look."""
from __future__ import annotations

import hashlib
import itertools
import math
import random
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "curriculum_packs")]
from generate_controls_pack_v0 import text_features  # noqa: E402
from verdant_development import VerdantDevelopmentPipeline  # noqa: E402
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel  # noqa: E402

from sidecar_looks import (_text_counts, hearing, imagined_look, learn_shares, reading,  # noqa: E402
                           recover_input, unknown_sense)
from sidecar_recall import imagine  # noqa: E402

WORDS = ["alba", "eput", "cind", "doro", "femi", "gulo"]


def _cmd(key, modality, feats, names):
    return ExperienceCommand(event_key=key, source_ref="looks-test", modality=modality, feature_vector=list(feats),
                             payload_sha256=hashlib.sha256(repr(list(feats)).encode()).hexdigest(),
                             concept_proposals=[ConceptProposal(label=n) for n in names], metadata={"context_id": "c"})


@pytest.fixture(scope="module")
def reader():
    k = VerdantKernel(seed=3, state_dim=64, run_label="looks-reader"); pipe = VerdantDevelopmentPipeline(); texts = {}
    for n, (a, b) in enumerate(itertools.permutations(WORDS[:4], 2)):
        texts[f"r{n}"] = (f"the {a} beside the {b}", (a, b))
        pipe.advance(k, _cmd(f"r{n}", "text", text_features(texts[f"r{n}"][0], 64), (a, b)))
    return k, texts


def _counts(text):
    c = np.zeros(64)
    for size in (1, 2, 3, 4):
        for s in range(len(text) - size + 1):
            c[int.from_bytes(hashlib.sha256(f"{size}:{text[s:s + size]}".encode()).digest()[:4], "big") % 64] += 1
    return c


def test_reading_is_recovered_to_the_exact_letter_counts(reader):
    k, texts = reader; fp = k.fingerprint()
    for key, (text, _names) in texts.items():
        F, res = recover_input(k, key, reading(64))
        assert res < 1e-6 and np.max(np.abs(F - np.array(text_features(text, 64)))) < 1e-6
        assert np.array_equal(_text_counts(F), _counts(text.lower()))
    assert k.fingerprint() == fp


def test_too_narrow_a_field_refuses_to_recover(reader):
    k, _ = reader
    with pytest.raises(ValueError):
        recover_input(k, "r0", reading(128))


@pytest.fixture(scope="module")
def listener():
    """Six pure sources with fixed band energies; scenes mix two at random loudness (energies add)."""
    rng = np.random.default_rng(5); bands = 32
    spectra = {w: rng.gamma(0.6, 1.0, bands) + 1e-3 for w in WORDS}
    def ear(parts):
        e = sum(l * spectra[w] for w, l in parts); v = np.log(e); return v - v.mean()
    k = VerdantKernel(seed=4, state_dim=64, run_label="looks-listener"); pipe = VerdantDevelopmentPipeline()
    held = {frozenset(("alba", "gulo"))}; recipes = {}; r = random.Random(1); n = 0
    for _ in range(3):
        for a, b in itertools.combinations(WORDS, 2):
            if frozenset((a, b)) in held:
                continue
            parts = [(a, r.uniform(0.3, 0.7)), (b, r.uniform(0.3, 0.7))]; key = f"h{n}"; n += 1
            recipes[key] = parts; pipe.advance(k, _cmd(key, "audio", ear(parts), (a, b)))
    return k, recipes, ear


def test_imagined_sound_of_a_never_heard_pair_is_close_to_the_real_one(listener):
    k, recipes, ear = listener; fp = k.fingerprint(); sense = hearing(32)
    shares = learn_shares(k, sense)
    assert shares.experiences == len(recipes) and max(shares.unknown.values()) < 0.2
    key = next(x for x, p in recipes.items() if p[0][0] == "alba" and p[1][0] == "cind")
    look = imagined_look(k, shares, key, "cind", "gulo")
    true = ear([("alba", recipes[key][0][1]), ("gulo", recipes[key][1][1])])
    unit = lambda v: np.asarray(v) / np.linalg.norm(v)
    guess_avg = imagine(k, key, "cind", "gulo", context="now")
    with_shares = imagine(k, key, "cind", "gulo", context="now", look=look)
    real = k._project_effect(k._validated_feature_array(true), "audio")
    from sidecar_looks import recover_input as rec
    memory_itself, _ = rec(k, key, hearing(32))
    assert float(np.dot(unit(look[0]), unit(true))) > 0.85
    assert float(np.dot(unit(look[0]), unit(true))) > float(np.dot(unit(memory_itself), unit(true)))
    assert abs(np.vdot(with_shares.sensed, real)) > abs(np.vdot(guess_avg.sensed, real))
    assert k.fingerprint() == fp


def test_unknown_sense_is_flagged_as_an_assumption():
    assert unknown_sense(8, "touch").assumption and not reading().assumption


def test_refitted_sound_size_is_near_the_truth_not_collapsed(listener):
    k, recipes, ear = listener
    shares = learn_shares(k, hearing(32))
    fitted = np.array([shares.scales[x] for x in recipes]); true = np.array([np.linalg.norm(ear(p)) for p in recipes.values()])
    assert 0.5 < float(np.median(fitted / true)) < 2.0


def _letters(word, width=64):
    return _counts(f" {word} ".lower())[:width] if width == 64 else None


def test_pieces_can_only_be_told_apart_if_they_were_met_apart(reader):
    """Words met in varied company get shares that match their own letters; words always met
    together cannot be separated (the same holds for any sense: cross-situational learning)."""
    k, _ = reader; label_to_id = {c.label: cid for cid, c in k.state.concepts.items()}
    varied = learn_shares(k, reading(64))
    r_varied = [np.corrcoef(varied.share[label_to_id[w]], _letters(w))[0, 1] for w in WORDS[:4]]
    together = VerdantKernel(seed=3, state_dim=64, run_label="looks-together"); pipe = VerdantDevelopmentPipeline()
    for n in range(4):
        for fam in (("alba", "eput"), ("cind", "doro")):
            pipe.advance(together, _cmd(f"t{n}{fam[0]}", "text", text_features(f"the {fam[0]} beside the {fam[1]} {'x' * n}", 64), fam))
    stuck = learn_shares(together, reading(64)); ids = {c.label: cid for cid, c in together.state.concepts.items()}
    r_together = [np.corrcoef(stuck.share[ids[w]], _letters(w))[0, 1] for w in WORDS[:4]]
    for w, other in (("alba", "eput"), ("cind", "doro")):       # met apart: each share is more its own word than the other's
        mine = varied.share[label_to_id[w]]
        assert np.corrcoef(mine, _letters(w))[0, 1] > np.corrcoef(mine, _letters(other))[0, 1] + 0.3
    assert min(r_varied) > 0.5
    assert np.allclose(stuck.share[ids["alba"]], stuck.share[ids["eput"]], atol=1e-6)   # always together: indistinguishable
    assert np.allclose(stuck.share[ids["cind"]], stuck.share[ids["doro"]], atol=1e-6)


def test_placed_sight_tells_places_apart_and_swaps_in_place():
    from sidecar_looks import placed_sight, recover_input
    rng = np.random.default_rng(8); looks = {w: 1.0 + 0.3 * rng.normal(size=10) for w in WORDS}      # looks much alike, like real ones
    def scene(left, right):
        return np.concatenate([looks[left], [0.25, 0.5], looks[right], [0.75, 0.5]])
    k = VerdantKernel(seed=6, state_dim=64, run_label="placed"); pipe = VerdantDevelopmentPipeline(); keys = {}
    for n, (a, b) in enumerate(itertools.permutations(WORDS, 2)):
        if {a, b} == {"alba", "gulo"}:
            continue                                                                 # never seen together
        keys[(a, b)] = f"p{n}"; pipe.advance(k, _cmd(f"p{n}", "visual", scene(a, b), (a, b)))
    one = k._project_effect(k._validated_feature_array(scene("cind", "doro")), "visual")
    other = k._project_effect(k._validated_feature_array(scene("doro", "cind")), "visual")
    assert abs(np.vdot(one, other)) < 0.99                                           # A left/B right differs from B left/A right
    shares = learn_shares(k, placed_sight(10, 2)); key = keys[("alba", "cind")]
    look, _m = imagined_look(k, shares, key, "cind", "gulo")
    memory, _r = recover_input(k, key, placed_sight(10, 2))
    wave = lambda v: k._project_effect(k._validated_feature_array(v), "visual")
    truth = wave(scene("alba", "gulo"))
    assert abs(np.vdot(wave(look), truth)) > abs(np.vdot(wave(memory), truth)) + 0.01     # closer to the never-seen pair
    unit = lambda v: np.asarray(v) / np.linalg.norm(v)
    assert float(unit(np.asarray(look)[:10]) @ unit(memory[:10])) > 1 - 1e-9              # the left place is untouched
