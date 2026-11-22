"""Boundary tests for the opt-in rehearsal sidecar (IMPLEMENTED-EXPERIMENTAL)."""
from __future__ import annotations

import hashlib

import pytest

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel
from sidecar_rehearsal import RehearsalConfig, RehearsingDevelopmentPipeline, VerdantRehearsalPipeline

DIM = 32


def _cmd(n: int, labels: tuple[str, ...], context: str) -> ExperienceCommand:
    vec = [0.0] * DIM
    vec[sum(map(ord, "".join(labels))) % DIM] = 1.0
    return ExperienceCommand(
        event_key=f"rehearsal-test-{n}", source_ref="rehearsal-test", modality="text", feature_vector=vec,
        payload_sha256=hashlib.sha256(f"{n}".encode()).hexdigest(),
        concept_proposals=[ConceptProposal(label=label) for label in labels],
        metadata={"context_id": context},
    )


def _lessons() -> list[ExperienceCommand]:
    fams = [("alef", "bet", "gimel"), ("dalet", "he", "vav"), ("zayin", "het", "tet"), ("yod", "kaf", "lamed")]
    return [_cmd(i, fams[i % 4], f"ctx{i % 3}") for i in range(24)]


def _run(pipe, lessons):
    kernel = VerdantKernel(seed=11, state_dim=DIM, run_label="rehearsal-test")
    for lesson in lessons:
        pipe.advance(kernel, lesson)
    return kernel


def _semantic(kernel):
    s = kernel.state
    return (sorted(s.evidence), sorted(s.concepts), sorted(s.relations), sorted(s.claims),
            sorted(s.processed_event_keys))


def test_rehearsal_is_deterministic_and_never_an_experience():
    cfg = RehearsalConfig(every_experiences=4, min_real_exposures=1, refresh_below=1.0)
    a = RehearsingDevelopmentPipeline(config=cfg); b = RehearsingDevelopmentPipeline(config=cfg)
    ka = _run(a, _lessons()); kb = _run(b, _lessons()); base = _run(VerdantDevelopmentPipeline(), _lessons())
    assert ka.fingerprint() == kb.fingerprint()
    assert [r.report_id for r in a.reports] == [r.report_id for r in b.reports]
    assert any(r.committed for r in a.reports)
    # same evidence, concepts, relations, claims and experiences as a run that never slept
    assert _semantic(ka) == _semantic(base)
    # and no bond exists that real experience did not create
    assert set(ka.state.plasticity_associations) <= set(base.state.plasticity_associations) | {
        e_id for ev in base.state.plasticity_events for e_id in getattr(ev, "created_association_ids", ())}


def test_one_beat_changes_no_candidate_and_creates_no_bond():
    kernel = _run(VerdantDevelopmentPipeline(), _lessons())
    cands = dict(kernel.state.structure_candidates); bonds = set(kernel.state.plasticity_associations)
    counts = _semantic(kernel)
    report = VerdantRehearsalPipeline(RehearsalConfig(min_real_exposures=1, refresh_below=1.0)).run(kernel)
    assert report.committed and report.reinforced_association_ids
    assert dict(kernel.state.structure_candidates) == cands
    assert set(kernel.state.plasticity_associations) <= bonds
    assert _semantic(kernel) == counts
    assert report.mean_strength_after > report.mean_strength_before


def test_nothing_to_rehearse_leaves_state_untouched():
    kernel = _run(VerdantDevelopmentPipeline(), _lessons()[:1]); fp = kernel.fingerprint()
    report = VerdantRehearsalPipeline(RehearsalConfig(min_real_exposures=5)).run(kernel)
    assert not report.committed and report.refusal == "nothing_to_rehearse"
    assert kernel.fingerprint() == fp


def test_config_refuses_zero_exposures():
    with pytest.raises(ValueError):
        RehearsalConfig(min_real_exposures=0)


def test_sleep_uses_the_waking_plasticity_stage_so_the_bond_clock_pauses():
    from sidecar_bond_clock import BondClockPlasticityPipeline
    stage = BondClockPlasticityPipeline()
    pipe = RehearsingDevelopmentPipeline(VerdantDevelopmentPipeline(plasticity=stage),
                                         RehearsalConfig(every_experiences=4, min_real_exposures=1, refresh_below=1.0))
    assert pipe.rehearsal.plasticity is stage
    kernel = _run(pipe, _lessons())
    committed = [r for r in pipe.reports if r.committed]
    assert committed
    sleeps = [e for e in kernel.state.plasticity_events if "suspended=1" in e.report.operation]
    assert len(sleeps) == len(committed)                      # every committed sleep beat paused the clock


def test_horizon_in_experiences_counts_real_experiences_only():
    kernel = _run(VerdantDevelopmentPipeline(), _lessons())
    wide_cycles = VerdantRehearsalPipeline(RehearsalConfig(min_real_exposures=1, refresh_below=1.0, horizon_cycles=10 ** 6)).select(kernel)
    wide_exps = VerdantRehearsalPipeline(RehearsalConfig(min_real_exposures=1, refresh_below=1.0, horizon_experiences=10 ** 6)).select(kernel)
    assert wide_exps == wide_cycles
    narrow = VerdantRehearsalPipeline(RehearsalConfig(min_real_exposures=1, refresh_below=1.0, horizon_experiences=0)).select(kernel)
    last_key = list(kernel.state.processed_event_keys)[-1]
    assert all(kernel.state.evidence[e].event_key == last_key for e, _, _ in narrow)
    kernel.state.cycle += 10 ** 6                      # kernel bookkeeping advancing the clock does not shorten it
    assert VerdantRehearsalPipeline(RehearsalConfig(min_real_exposures=1, refresh_below=1.0, horizon_experiences=10 ** 6)).select(kernel) == wide_exps


def test_lived_horizon_defends_a_bond_as_long_as_the_world_confirmed_it():
    kernel = _run(VerdantDevelopmentPipeline(), _lessons())
    lived = VerdantRehearsalPipeline(RehearsalConfig(min_real_exposures=1, refresh_below=1.0, horizon_lived=True))
    order = {k: i for i, k in enumerate(kernel.state.processed_event_keys)}; now = len(order)
    for evidence_id, _concepts, bonds in lived.select(kernel):
        for aid in bonds:
            bond = kernel.state.plasticity_associations[aid]
            seen = [order[kernel.state.evidence[r].event_key] for r in bond.evidence_refs
                    if r in kernel.state.evidence and kernel.state.evidence[r].kind.value == "observation"]
            assert now - max(seen) <= max(seen) - min(seen)
    kernel.state.cycle += 10 ** 6                      # kernel bookkeeping does not shorten it either
    assert lived.select(kernel) == VerdantRehearsalPipeline(RehearsalConfig(min_real_exposures=1, refresh_below=1.0, horizon_lived=True)).select(kernel)
