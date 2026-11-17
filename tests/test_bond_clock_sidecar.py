"""Boundary tests for the opt-in bond-clock plasticity stage (IMPLEMENTED-EXPERIMENTAL)."""
from __future__ import annotations

import hashlib

import pytest

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel
from sidecar_bond_clock import BondClockPlasticityPipeline, ChangesOnlyPlasticityPipeline, replay_tables

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


def test_single_exposure_bond_fades_exactly_as_stock():
    stock = _run(); clock = _run(BondClockPlasticityPipeline())
    assert _bonds(clock, ONCE) == _bonds(stock, ONCE)


def test_recurring_bond_is_more_durable_and_run_is_deterministic():
    stock = _run(); a = _run(BondClockPlasticityPipeline()); b = _run(BondClockPlasticityPipeline())
    assert a.fingerprint() == b.fingerprint()
    assert _bonds(a, OFTEN) and min(_bonds(a, OFTEN)) > max(_bonds(stock, OFTEN) or [0.0])
    assert min(_bonds(a, OFTEN)) >= 0.10
    assert sorted(a.state.evidence) == sorted(stock.state.evidence)
    assert sorted(a.state.concepts) == sorted(stock.state.concepts)


@pytest.mark.parametrize("rule", ["uniform", "bond_clock"])
def test_changes_only_record_leaves_exactly_the_same_bonds(rule):
    make = BondClockPlasticityPipeline if rule == "bond_clock" else ChangesOnlyPlasticityPipeline
    full = _run(make(changes_only=False)); slim = _run(make(changes_only=True))
    view = lambda k: {key: r.model_dump(exclude={"last_workspace_event_id"}) for key, r in k.state.plasticity_associations.items()}
    assert view(full) == view(slim)
    assert sorted(full.state.structure_candidates) == sorted(slim.state.structure_candidates)
    assert list(replay_tables(slim))[-1][1] == slim.state.plasticity_associations
    assert sum(len(e.report.proposed_associations) for e in slim.state.plasticity_events) < \
        sum(len(e.report.proposed_associations) for e in full.state.plasticity_events) / 3


def test_uniform_changes_only_is_the_stock_beat_with_a_smaller_record():
    stock = _run(); slim = _run(ChangesOnlyPlasticityPipeline())
    view = lambda k: {key: r.model_dump(exclude={"last_workspace_event_id"}) for key, r in k.state.plasticity_associations.items()}
    assert view(stock) == view(slim) and sorted(stock.state.evidence) == sorted(slim.state.evidence)
