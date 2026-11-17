"""Boundary tests for the opt-in bond-clock plasticity stage (IMPLEMENTED-EXPERIMENTAL)."""
from __future__ import annotations

import hashlib
import inspect

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel
from verdant_plasticity.pipeline import VerdantPlasticityPipeline
from sidecar_bond_clock import STOCK_INSPECT_SHA256, BondClockPlasticityPipeline

DIM = 32


def _cmd(n, labels, context):
    vec = [0.0] * DIM
    vec[sum(map(ord, "".join(labels))) % DIM] = 1.0
    return ExperienceCommand(event_key=f"bond-clock-{n}", source_ref="bond-clock-test", modality="text",
                             feature_vector=vec, payload_sha256=hashlib.sha256(f"{n}".encode()).hexdigest(),
                             concept_proposals=[ConceptProposal(label=x) for x in labels], metadata={"context_id": context})


ONCE = ("solo_a", "solo_b", "solo_c")
OFTEN = ("rep_a", "rep_b", "rep_c")


def _lessons():
    filler = [(f"f{i}_a", f"f{i}_b", f"f{i}_c") for i in range(30)]
    order = [ONCE] + [OFTEN]
    for i, fam in enumerate(filler):
        order.append(fam)
        if i in (5, 11, 17):
            order.append(OFTEN)
    return [_cmd(i, fam, f"ctx{i % 3}") for i, fam in enumerate(order)]


def _run(plasticity=None):
    pipe = VerdantDevelopmentPipeline(plasticity=plasticity) if plasticity else VerdantDevelopmentPipeline()
    kernel = VerdantKernel(seed=11, state_dim=DIM, run_label="bond-clock-test")
    for lesson in _lessons():
        pipe.advance(kernel, lesson)
    return kernel


def _bonds(kernel, family):
    ids = {c.label: cid for cid, c in kernel.state.concepts.items()}
    want = {ids[x] for x in family}
    return sorted(a.strength for a in kernel.state.plasticity_associations.values() if set(a.concept_ids) <= want)


def test_stock_inspect_has_not_drifted_from_the_derived_copy():
    src = inspect.getsource(VerdantPlasticityPipeline.inspect)
    assert hashlib.sha256(src.encode()).hexdigest() == STOCK_INSPECT_SHA256


def test_single_exposure_bond_fades_exactly_as_stock():
    stock = _run(); clock = _run(BondClockPlasticityPipeline())
    assert _bonds(clock, ONCE) == _bonds(stock, ONCE)


def test_recurring_bond_is_more_durable_and_run_is_deterministic():
    stock = _run(); a = _run(BondClockPlasticityPipeline()); b = _run(BondClockPlasticityPipeline())
    assert a.fingerprint() == b.fingerprint()
    assert _bonds(a, OFTEN) and min(_bonds(a, OFTEN)) > max(_bonds(stock, OFTEN) or [0.0])
    assert min(_bonds(a, OFTEN)) >= 0.10
    # same evidence, concepts and experiences: only bond strengths differ
    assert sorted(a.state.evidence) == sorted(stock.state.evidence)
    assert sorted(a.state.concepts) == sorted(stock.state.concepts)
