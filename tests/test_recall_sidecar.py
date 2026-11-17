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
