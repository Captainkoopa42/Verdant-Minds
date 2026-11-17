"""Acceptance-style test for the opt-in generic folding sidecar (IMPLEMENTED-EXPERIMENTAL). Slow: one full run."""
from __future__ import annotations

import collections

import pytest

from run_observer_recursive_fold import run
from sidecar_fold import chunk, depth_of, fold_table, unfold
from verdant_compilation import VerdantCompilationPipeline
from verdant_kernel.models import StructurePromotionEvent


@pytest.fixture(scope="module")
def grown():
    return run(2301, True)


def test_one_promotion_path_reaches_three_depths_with_no_stray_folds(grown):
    kernel, _inner, fams, groups, _plan, _probes = grown
    state = kernel.state; label = {cid: c.label for cid, c in state.concepts.items()}
    depths = collections.Counter(depth_of(kernel, sid) for sid in state.structures)
    assert depths == {1: 16, 2: 3, 3: 1}
    assert all(type(e) is StructurePromotionEvent for e in state.structure_promotion_events)
    leaves = {frozenset(label[c] for c in unfold(kernel, s.member_concept_ids)) for s in state.structures.values()}
    for name in ("twice", "one_context"):                                   # taught together, but not enough: must not fold
        assert frozenset(m for f in groups[name] for m in f["members"]) not in leaves
    assert all(len(s) in (3, 9, 27) for s in leaves)


def test_handles_never_bond_with_their_own_contents(grown):
    kernel = grown[0]; table = fold_table(kernel, available_only=False)
    for bond in kernel.state.plasticity_associations.values():
        a, b = bond.concept_ids
        for handle, other in ((a, b), (b, a)):
            if handle in table:
                assert other not in unfold(kernel, [handle]) and other not in table[handle][1]


def test_removing_a_low_fold_silences_what_stands_on_it_and_restoring_brings_it_back(grown):
    kernel, _inner, fams, _groups, _plan, probes = grown
    ids = {c.label: cid for cid, c in kernel.state.concepts.items()}; label = {v: k for k, v in ids.items()}
    world = [ids[p.label] for p in probes["new_world"].concept_proposals]
    family = next(sid for sid, s in kernel.state.structures.items() if {label[m] for m in s.member_concept_ids} == set(fams[0]["members"]))
    before = kernel.state.fingerprint(include_transitions=False)
    assert len(chunk(kernel, world)[0]) == 1
    VerdantCompilationPipeline.ablate(kernel, family, "test")
    assert len(chunk(kernel, world)[0]) == 7
    VerdantCompilationPipeline.restore(kernel, family, "test")
    assert len(chunk(kernel, world)[0]) == 1
    assert set(kernel.state.structures) and kernel.state.fingerprint(include_transitions=False) != before   # availability events are recorded
