"""verdant_organism: the folded-in organism equals the stack it was validated as, and its switches work.

Process-global candidate parts (senses, wave, profiles, stance, reader, ear) and the accelerator
patch shared classes, so these tests keep them off and stay within one configuration."""
from __future__ import annotations

import pytest

from verdant_organism import Organism, Parts
from tests.test_heat_sidecar import LESSONS

QUIET = dict(acceleration=False, senses=False, fine_ear=False, reader=False, wave_fold=False, profiles=False, stance=False)


def _grow(parts):
    organism = Organism(parts)
    kernel = organism.new_kernel(seed=11, state_dim=32, run_label="organism-test")
    for lesson in LESSONS:
        organism.advance(kernel, lesson)
    return organism, kernel


def test_default_parts_include_every_validated_part():
    parts = Parts()
    assert all((parts.senses, parts.fine_ear, parts.reader, parts.wave_fold, parts.profiles, parts.stance))
    assert parts.heat == "revise" and parts.council == "ready" and parts.question_sleep and parts.horizon_experiences == 76
    assert Parts().lean().senses is False


def test_lean_organism_is_the_validated_stack():
    from sidecar_bond_clock import BondClockPlasticityPipeline
    from sidecar_council import ConveningDevelopmentPipeline
    from sidecar_gear import GearPipeline
    from sidecar_heat import HeatDevelopmentPipeline
    from sidecar_inquiry import InquiringDevelopmentPipeline
    from sidecar_recurrence import ExperienceRecurrenceStructurePipeline
    from sidecar_rehearsal import RehearsalConfig, RehearsingDevelopmentPipeline
    from sidecar_surprise import SurpriseDevelopmentPipeline, surprise_plasticity
    structures = ExperienceRecurrenceStructurePipeline()
    beat = SurpriseDevelopmentPipeline(structures=structures, plasticity=surprise_plasticity(BondClockPlasticityPipeline, reunion=True)())
    beat = RehearsingDevelopmentPipeline(beat, RehearsalConfig(min_real_exposures=1, horizon_experiences=76))
    beat = InquiringDevelopmentPipeline(HeatDevelopmentPipeline(ConveningDevelopmentPipeline(GearPipeline(beat, mode="watch"), structures,
                                                                                             mode="ready"), mode="revise"), authority="sleep")
    kernel = Organism.new_kernel(seed=11, state_dim=32, run_label="organism-test")
    for lesson in LESSONS:
        beat.advance(kernel, lesson)
    _, grown = _grow(Parts(**QUIET))
    assert grown.fingerprint() == kernel.fingerprint()


def test_organism_revises_and_reports():
    organism, kernel = _grow(Parts(**QUIET))
    report = organism.report()
    assert report["revision"] == "verdant_organism_v0"
    assert report["council"]["promoted"] >= 1 and any(r[2] == "revise" for r in report["heat"]["refolds"])
    assert set(report) >= {"parts", "council", "heat", "gear", "questions", "sleep_beats_committed"}


def test_switches_turn_parts_off():
    organism, _ = _grow(Parts(**QUIET, heat=None, question_sleep=False, gear=None, council=None))
    assert organism.layer("HeatDevelopmentPipeline") is None and organism.layer("ConveningDevelopmentPipeline") is None
    with pytest.raises(ValueError):
        Organism(Parts(**QUIET, sleep=False))                 # question_sleep needs sleep


def test_organism_is_deterministic():
    _, a = _grow(Parts(**QUIET)); _, b = _grow(Parts(**QUIET))
    assert a.fingerprint() == b.fingerprint()
