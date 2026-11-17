"""Boundary tests for the opt-in recall sidecar: honest labels, exact reliving, imagination that changes nothing."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "curriculum_packs"))
from generate_controls_pack_v0 import text_features  # noqa: E402

from sidecar_recall import _frames_by_event, _unit, imagine, recall, relive
from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel

DIM = 64
STRONG = [("alba", "brev", "cind"), ("dosk", "eput", "fram")]
TWICE = ("gelt", "hask", "iwen")
ONCE = ("jorn", "kalv", "lume")


@pytest.fixture(scope="module")
def grown():
    plan = [(f, e) for e in range(5) for f in STRONG] + [(TWICE, 0), (TWICE, 1), (ONCE, 0)]
    kernel = VerdantKernel(seed=4, state_dim=DIM, run_label="recall-test"); pipe = VerdantDevelopmentPipeline()
    for n, (fam, e) in enumerate(plan):
        text = f"the {fam[0]} near the {fam[1]} and the {fam[2]}, version {e}"
        pipe.advance(kernel, ExperienceCommand(event_key=f"recall-{n}", source_ref="recall-test", modality="text",
                     feature_vector=text_features(text, DIM), payload_sha256=hashlib.sha256(text.encode()).hexdigest(),
                     concept_proposals=[ConceptProposal(label=x) for x in fam], metadata={"context_id": f"c{e % 3}"}))
    return kernel


def test_labels_never_claim_more_than_the_record(grown):
    fp = grown.fingerprint()
    for fam in STRONG + [TWICE, ONCE]:
        for cue in fam:
            r = recall(grown, cue)
            for partner, how in r.partners:
                if how.startswith("SEARCHED"):
                    assert partner not in fam                      # "never met" must be true
                if partner in TWICE or (cue in TWICE and partner in fam):
                    assert not how.startswith(("EARNED", "REMEMBERED"))   # met twice is never presented as known
    assert recall(grown, "neverseenword").mode == "unknown"
    assert grown.fingerprint() == fp


def test_relive_recovers_each_experience_exactly(grown):
    r = grown.state.ecwf_policy.retention
    for key, i in _frames_by_event(grown).items():
        x = relive(grown, key); frame = grown.state.field.history[i]
        after = np.asarray(frame.real) + 1j * np.asarray(frame.imag)
        rebuilt = _unit(r * x.mind_before + x.effect) if np.linalg.norm(x.mind_before) else x.effect
        assert np.max(np.abs(rebuilt - after)) < 1e-12 and x.concept_ids == tuple(frame.bound_concept_ids)


def test_imagining_changes_neither_the_organism_nor_the_memory(grown):
    fp = grown.fingerprint(); label = {c: x.label for c, x in grown.state.concepts.items()}
    key = next(k for k, i in _frames_by_event(grown).items()
               if set(STRONG[0]) <= {label[c] for c in grown.state.field.history[i].bound_concept_ids})
    before = relive(grown, key)
    for context in ("then", "now"):
        im = imagine(grown, key, STRONG[0][0], STRONG[1][1], context=context)
        assert im.original_intact
        held = dict(im.held_in_mind)
        assert held.get(STRONG[1][1], "").startswith("IMAGINED")
        assert all(not how.startswith(("EARNED", "REMEMBERED")) for how in held.values())
    after = relive(grown, key)
    assert np.array_equal(before.effect, after.effect) and grown.fingerprint() == fp


def _texts():
    plan = [(f, e) for e in range(5) for f in STRONG] + [(TWICE, 0), (TWICE, 1), (ONCE, 0)]
    return {f"recall-{n}": f"the {fam[0]} near the {fam[1]} and the {fam[2]}, version {e}" for n, (fam, e) in enumerate(plan)}


def test_reliving_recovers_what_was_sensed_exactly(grown):
    from sidecar_recall import _experience_parts
    for key, text in _texts().items():
        sensed = _experience_parts(grown, relive(grown, key))
        truth = grown._project_effect(np.asarray(text_features(text, DIM), dtype=float), "text")
        assert np.max(np.abs(sensed - truth)) < 1e-8


def test_second_step_is_labelled_imagined_and_the_old_family_calls_its_piece_back(grown):
    from sidecar_recall import kind_of
    fp = grown.fingerprint(); label = {c: x.label for c, x in grown.state.concepts.items()}
    key = next(k for k, i in _frames_by_event(grown).items()
               if set(STRONG[0]) <= {label[c] for c in grown.state.field.history[i].bound_concept_ids})
    im = imagine(grown, key, STRONG[0][0], STRONG[1][1], context="now")
    assert {b for b, _ in im.brought} and {b for b, _ in im.brought} <= set(STRONG[1]) - {STRONG[1][1]}
    assert STRONG[0][0] in {b for b, _ in im.called_back}            # the rest of the old family calls the old piece back
    for _l, how in im.brought + im.called_back:
        assert kind_of(how) == "IMAGINED"
    for _l, how in im.held_in_mind:
        kind_of(how)                                                  # every label belongs to one of the five kinds
    assert not imagine(grown, key, STRONG[0][0], STRONG[1][1], second_step=False).brought
    assert grown.fingerprint() == fp


def test_simulation_matches_reality_and_changes_nothing(grown):
    from sidecar_recall import simulate
    text = "the alba near the eput and the cind, version 9"
    command = ExperienceCommand(event_key="recall-sim", source_ref="recall-test", modality="text",
                                feature_vector=text_features(text, DIM), payload_sha256=hashlib.sha256(text.encode()).hexdigest(),
                                concept_proposals=[ConceptProposal(label=x) for x in ("alba", "eput", "cind")], metadata={"context_id": "c1"})
    fp = grown.fingerprint()
    sim = simulate(grown, VerdantDevelopmentPipeline(), command)
    assert grown.fingerprint() == fp and sim.organism_unchanged
    real = VerdantKernel.from_state(grown.state.model_copy(deep=True)); VerdantDevelopmentPipeline().advance(real, command)
    label = {c: x.label for c, x in real.state.concepts.items()}
    ev = real.state.resonance_events[-1]
    assert sim.came_to_mind == tuple((label[c.concept_id], float(c.score)) for c in ev.query_report.candidates)
    assert np.array_equal(sim.effect, relive(real, "recall-sim").effect)
