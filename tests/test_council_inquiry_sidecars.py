"""Boundary tests: the Council convenes itself (sidecar_council) and open questions in shadow
(sidecar_inquiry). Both IMPLEMENTED-EXPERIMENTAL."""
from __future__ import annotations

import pytest

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import VerdantKernel
from verdant_structures import VerdantStructurePipeline
from sidecar_council import ConveningDevelopmentPipeline, eligible_waiting
from sidecar_inquiry import InquiringDevelopmentPipeline, failing_gates
from tests.test_rehearsal_sidecar import _cmd

FAMS = [("alef", "bet", "gimel"), ("dalet", "he", "vav"), ("zayin", "het", "tet"), ("yod", "kaf", "lamed")]
LESSONS = [_cmd(i, FAMS[i % 4], f"ctx{i % 3}") for i in range(40)]


def _life(pipe):
    kernel = VerdantKernel(seed=11, state_dim=32, run_label="council-test")
    for lesson in LESSONS:
        pipe.advance(kernel, lesson)
    return kernel


def _council(mode):
    return ConveningDevelopmentPipeline(VerdantDevelopmentPipeline(), VerdantStructurePipeline(), mode=mode, every=10)


def _runner_clock_life():
    """The old runner's rule, written out: every 10 experiences, up to 4 eligible go to the Council."""
    kernel = VerdantKernel(seed=11, state_dim=32, run_label="council-test")
    pipe, structures = VerdantDevelopmentPipeline(), VerdantStructurePipeline()
    for n, lesson in enumerate(LESSONS, 1):
        pipe.advance(kernel, lesson)
        if n % 10 == 0:
            for cid in eligible_waiting(kernel)[:4]:
                structures.promote(kernel, cid)
    return kernel


def test_clock_mode_is_the_old_rule_byte_for_byte():
    assert _life(_council("clock")).fingerprint() == _runner_clock_life().fingerprint()


@pytest.mark.parametrize("mode", ["ready", "steady"])
def test_self_convening_is_deterministic_and_promotes_through_the_council(mode):
    a, b = _council(mode), _council(mode)
    ka, kb = _life(a), _life(b)
    assert ka.fingerprint() == kb.fingerprint()
    assert len(ka.state.structures) == 4 and not a.log.refusals
    events = ka.state.structure_promotion_events
    assert len(events) == 4 and all(e.council_decision_event_id for e in events)   # each one a Council decision
    assert a.log.lags() == ([0] * 4 if mode == "ready" else [1] * 4)


def test_ready_waits_for_nothing_but_never_promotes_what_is_not_eligible():
    pipe = _council("ready"); kernel = _life(pipe)
    assert not eligible_waiting(kernel)                 # nothing left waiting at the end
    for cid in pipe.log.promoted_at:
        assert kernel.state.structure_candidates[cid].status.value == "promoted"


def test_bad_mode_refused():
    with pytest.raises(ValueError):
        ConveningDevelopmentPipeline(VerdantDevelopmentPipeline(), VerdantStructurePipeline(), mode="whenever")


def test_inquiry_shadow_changes_nothing():
    plain = _life(_council("ready"))
    watched_pipe = InquiringDevelopmentPipeline(_council("ready"))
    watched_pipe.shadow.substrate_every = 1
    watched = _life(watched_pipe)
    assert watched.fingerprint() == plain.fingerprint()
    summary = watched_pipe.shadow.summary()
    assert summary["fingerprint_breaks"] == 0 and not summary["substrate_errors"]
    assert summary["questions"] >= 1


def test_inquiry_questions_name_real_gates_and_resolve_when_eligible():
    pipe = InquiringDevelopmentPipeline(_council("ready")); kernel = _life(pipe)
    for cid, q in pipe.shadow.questions.items():
        assert q.gates_at_open                              # a question is only opened for a failing gate
        cand = kernel.state.structure_candidates[cid]
        if q.state == "resolved":
            assert cand.status.value in ("eligible", "promoted")
        else:
            assert tuple(q.gates_now) == failing_gates(kernel, cand) or cand.status.value != "tracking"


def test_sleep_authority_is_fork_only_and_needs_sleep():
    with pytest.raises(ValueError):
        InquiringDevelopmentPipeline(_council("ready"), authority="sleep")      # nothing that sleeps inside
    with pytest.raises(ValueError):
        InquiringDevelopmentPipeline(_council("ready"), authority="council")


def test_directed_sleep_keeps_rehearsal_safety_and_is_deterministic():
    from sidecar_rehearsal import RehearsalConfig, RehearsingDevelopmentPipeline

    def pipe():
        sleeping = RehearsingDevelopmentPipeline(config=RehearsalConfig(every_experiences=4, min_real_exposures=1))
        return InquiringDevelopmentPipeline(ConveningDevelopmentPipeline(sleeping, VerdantStructurePipeline(), mode="ready"),
                                            authority="sleep")
    a, b = pipe(), pipe()
    ka, kb = _life(a), _life(b)
    assert ka.fingerprint() == kb.fingerprint()
    assert all(r.refusal in (None, "nothing_to_rehearse") for r in a.inner.inner.reports)
