"""Boundary tests for local heat (sidecar_heat). IMPLEMENTED-EXPERIMENTAL."""
from __future__ import annotations

import pytest

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import VerdantKernel
from verdant_structures import VerdantStructurePipeline
from sidecar_council import ConveningDevelopmentPipeline
from sidecar_heat import HeatDevelopmentPipeline, drift, temperature
from tests.test_rehearsal_sidecar import _cmd

OLD = ("alef", "bet", "gimel", "dalet"); NEW = ("alef", "bet", "gimel", "zayin"); OTHER = ("he", "vav", "het", "tet")
LESSONS = ([_cmd(i, OLD if i % 2 == 0 else OTHER, f"ctx{i % 3}") for i in range(10)]
           + [_cmd(i, NEW if i % 2 == 0 else OTHER, f"ctx{i % 3}") for i in range(10, 26)])


def _life(mode=None):
    kernel = VerdantKernel(seed=11, state_dim=32, run_label="heat-test")
    pipe = ConveningDevelopmentPipeline(VerdantDevelopmentPipeline(), VerdantStructurePipeline(), mode="ready")
    if mode:
        pipe = HeatDevelopmentPipeline(pipe, mode=mode)
    for lesson in LESSONS:
        pipe.advance(kernel, lesson)
    return kernel, pipe


def _by_labels(kernel):
    label = {c: x.label for c, x in kernel.state.concepts.items()}
    return {sid: frozenset(label[m] for m in s.member_concept_ids) for sid, s in kernel.state.structures.items()}, label


def test_watch_writes_nothing():
    plain, _ = _life(); watched, pipe = _life("watch")
    assert watched.fingerprint() == plain.fingerprint()
    assert pipe.heat_log.temps and not pipe.heat_log.challenges


def test_heat_sits_on_the_departed_member_and_not_on_the_stable_family():
    kernel, _ = _life("watch"); groups, label = _by_labels(kernel)
    old = next(sid for sid, m in groups.items() if m == frozenset(OLD))
    other = next(sid for sid, m in groups.items() if m == frozenset(OTHER))
    d = {label[k]: v for k, v in drift(kernel, kernel.state.structures[old]).items()}
    assert max(d, key=d.get) == "dalet" and d["dalet"] > 0.3 and all(v < 0.1 for k, v in d.items() if k != "dalet")
    assert temperature(kernel, kernel.state.structures[old]) > 10 * (temperature(kernel, kernel.state.structures[other]) or 0) + 1e-3


def test_revise_retires_the_stale_fold_through_the_council_and_keeps_history():
    kernel, pipe = _life("revise"); groups, _ = _by_labels(kernel)
    old = next(sid for sid, m in groups.items() if m == frozenset(OLD))
    assert not kernel.structure_is_available(old) and old in kernel.state.structures      # preserved, not erased
    child = [sid for sid, m in groups.items() if m == frozenset(("alef", "bet", "gimel"))]
    assert child and kernel.structure_is_available(child[0])
    assert kernel.state.structures[child[0]].lineage_parent_structure_id == old
    assert all(e.council_decision_event_id for e in kernel.state.structure_refold_events if e.produced_structure_ids)
    other = next(sid for sid, m in groups.items() if m == frozenset(OTHER))
    assert kernel.structure_is_available(other)                                           # the unchanged family is untouched
    assert not pipe.heat_log.refusals


def test_revise_is_deterministic():
    a, _ = _life("revise"); b, _ = _life("revise")
    assert a.fingerprint() == b.fingerprint()


def test_bad_mode_refused():
    with pytest.raises(ValueError):
        HeatDevelopmentPipeline(None, mode="melt")


def test_a_member_that_keeps_coming_back_is_never_revised_away():
    partial = ("alef", "bet", "gimel")
    lessons = ([_cmd(i, OLD if i % 2 == 0 else OTHER, f"ctx{i % 3}") for i in range(10)]
               + [_cmd(i, (OLD if (i // 2) % 2 == 0 else partial) if i % 2 == 0 else OTHER, f"ctx{i % 3}") for i in range(10, 34)])
    kernel = VerdantKernel(seed=11, state_dim=32, run_label="heat-test")
    pipe = HeatDevelopmentPipeline(ConveningDevelopmentPipeline(VerdantDevelopmentPipeline(), VerdantStructurePipeline(), mode="ready"),
                                   mode="revise")
    for lesson in lessons:
        pipe.advance(kernel, lesson)
    groups, _ = _by_labels(kernel)
    old = next(sid for sid, m in groups.items() if m == frozenset(OLD))
    assert kernel.structure_is_available(old) and not any(r[2] == "revise" for r in pipe.heat_log.refolds)
    assert pipe.heat_log.voided >= 1                   # its absences were voided by its returns
