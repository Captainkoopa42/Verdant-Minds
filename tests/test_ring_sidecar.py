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


def _moments(carry: bool, remind: bool):
    """P seen then Q heard in the same moment, 6 times; R seen and S heard always apart."""
    import run_observer_long_life as R
    sidecar_ring.install_ring(adapt=True)
    if remind:
        sidecar_ring.install_inferred_association()
    saved = dict(R.PIPELINE_CONFIG)
    try:
        if carry:
            R.PIPELINE_CONFIG.update(sidecar_ring.CARRY_ONE_EXPERIENCE)
        rng = np.random.default_rng(3); P, R_ = rng.normal(size=24), rng.normal(size=24); Q, S = rng.normal(size=16), rng.normal(size=16)
        fillers = [(rng.normal(size=24), f"f{i}") for i in range(4)]
        k = VerdantKernel(seed=2, state_dim=128, run_label="moments")
        if carry:
            sidecar_ring.carry_one_experience(k)
        pipe, _ = R.build_pipeline("reunion")
        n = 0
        def go(mod, base, names):
            nonlocal n; n += 1; pipe.advance(k, _cmd(f"m{n}", mod, base + 0.1 * rng.normal(size=base.size), names))
        for e in range(6):
            go("visual", P, ("pee",)); go("audio", Q, ("queue",))
            go("visual", R_, ("arr",))
            for f, nm in fillers:
                go("visual", f, (nm,))
            go("audio", S, ("ess",))
        ids = {x.label: c for c, x in k.state.concepts.items()}
        def bond(a, b):
            return max((x.strength for x in k.state.plasticity_associations.values() if set(x.concept_ids) == {ids[a], ids[b]}), default=0.0)
        state = k.state.model_copy(deep=True)
        fork = VerdantKernel.from_state(state); pipe.advance(fork, _cmd("test", "audio", Q, ()))
        w = fork.state.workspace_cycle_events[-1].report
        reminded = {fork.state.concepts[m].label for a in w.assessments if a.candidate.source_kind.value == "local_association"
                    and a.disposition.value == "admit" for m in a.candidate.binding_refs}
        return bond("pee", "queue"), bond("arr", "ess"), reminded
    finally:
        R.PIPELINE_CONFIG.clear(); R.PIPELINE_CONFIG.update(saved)
        sidecar_ring.uninstall_inferred_association(); sidecar_ring.uninstall_ring()


def test_short_term_memory_binds_what_happens_together_and_only_that():
    without = _moments(False, False); with_carry = _moments(True, False); remind = _moments(True, True)
    assert without[0] == 0.0 and without[1] == 0.0                   # stock: nothing sensed survives into the next moment
    assert with_carry[0] > 0.24 and with_carry[1] == 0.0               # together binds, apart does not
    assert "pee" not in with_carry[2] and "pee" in remind[2]           # an unnamed sound reminds only when recognition can remind


def test_conflict_is_flagged_and_familiar_is_not():
    sidecar_ring.install_ring(adapt=True); sidecar_ring.install_attention()
    try:
        rng = np.random.default_rng(4); sounds = {w: rng.normal(size=16) for w in "abcd"}
        k = VerdantKernel(seed=5, state_dim=128, run_label="attention"); pipe = VerdantDevelopmentPipeline()
        for e in range(4):
            for w in "abcd":
                pipe.advance(k, _cmd(f"l{w}{e}", "audio", sounds[w] + 0.1 * rng.normal(size=16), (w,)))
        def signals():
            cur = [x for x in k.state.workspace_cycle_events[-1].report.assessments
                   if x.candidate.source_kind.value == "current_evidence" and x.carried_from_item_id is None][0]
            assert cur.candidate.metadata.get("contradiction_source") == "sidecar_ring.measured"
            return cur.candidate.signals, cur.effective_score
        pipe.advance(k, _cmd("right", "audio", sounds["a"] + 0.1 * rng.normal(size=16), ("a",)))
        right, right_score = signals()
        pipe.advance(k, _cmd("wrong", "audio", sounds["b"] + 0.1 * rng.normal(size=16), ("a",)))   # told a, sounds like b
        wrong, wrong_score = signals()
        assert right.contradiction_pressure < 0.2 < wrong.contradiction_pressure and wrong_score > right_score
        assert sidecar_ring.read_tension(k)["a"]["tension"] > sidecar_ring.read_tension(k)["c"]["tension"]
    finally:
        sidecar_ring.uninstall_attention(); sidecar_ring.uninstall_ring()


def test_how_known_keeps_naming_apart_from_sensing(rung):
    k, *_ = rung
    sidecar_ring.install_ring()
    try:
        a = sidecar_ring.how_known(k, "a")
    finally:
        sidecar_ring.uninstall_ring()
    assert a["named"] == 0 and a["sensed_told"] == {"visual": 4, "audio": 1} and a["knows_look_of"] == ["audio", "visual"]
    assert a["rung"].get("audio", 0) >= 1


def _conflict_life(signed):
    sidecar_ring.install_ring(adapt=True, signed=signed)
    try:
        rng = np.random.default_rng(4); sounds = {w: rng.normal(size=16) for w in "abcd"}
        k = VerdantKernel(seed=5, state_dim=128, run_label="signed"); pipe = VerdantDevelopmentPipeline(); feats = {}
        for e in range(4):
            for w in "abcd":
                f = sounds[w] + 0.1 * rng.normal(size=16); feats[f"l{w}{e}"] = f; pipe.advance(k, _cmd(f"l{w}{e}", "audio", f, (w,)))
        f = sounds["b"] + 0.1 * rng.normal(size=16); feats["wrong"] = f
        pipe.advance(k, _cmd("wrong", "audio", f, ("a",)))                      # told a, sounds like b
        return k, sidecar_ring.read_stances(k), feats
    finally:
        sidecar_ring.uninstall_ring()


def test_an_unresolved_conflict_is_held_in_tension_not_erased():
    k, st, feats = _conflict_life("quarter")
    rung = sidecar_ring.rings_of_frame(k, len(k.state.field.history) - 1)
    assert [(k.state.concepts[c].label, isinstance(w, complex)) for c, w in rung.items()] == [("b", True)]
    assert st["b"]["stands_out"] and st["b"]["verdict"] == "in tension" and st["a"]["verdict"] == "agrees"
    for key, f in feats.items():                                                          # replay stays exact
        assert np.max(np.abs(_experience_parts(k, relive(k, key)) - k._project_effect(k._validated_feature_array(f), "audio"))) < 1e-9


def test_a_half_turn_cancels_what_is_there_which_is_why_it_is_kept_for_refutation():
    _k, held, _f = _conflict_life("quarter"); _k2, opposed, _f2 = _conflict_life("half")
    assert opposed["b"]["support"] < -0.3                                                  # it does read as contradicted
    assert opposed["b"]["presence"] < held["b"]["presence"]                                # but at the cost of presence


def test_without_signed_writing_the_conflict_reads_as_agreement():
    _k, st, _f = _conflict_life(False)
    assert st["b"]["stands_out"] and st["b"]["support"] > 0.3 and st["b"]["tension"] < 0.3


def test_presence_floor_is_chance_based():
    k, st, _f = _conflict_life("quarter")
    floor = sidecar_ring.CHANCE_MULTIPLE / np.sqrt(k.state.field.state_dim)
    assert all(v["stands_out"] == (v["presence"] > floor) for v in st.values())
