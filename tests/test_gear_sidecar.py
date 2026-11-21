"""Boundary tests for the gear (sidecar_gear). IMPLEMENTED-EXPERIMENTAL."""
from __future__ import annotations

import pytest

from verdant_kernel import VerdantKernel
from verdant_structures import VerdantStructurePipeline
from sidecar_council import ConveningDevelopmentPipeline
from sidecar_gear import GearPipeline
from sidecar_rehearsal import RehearsalConfig, RehearsingDevelopmentPipeline
from tests.test_heat_sidecar import LESSONS


def _life(mode=None):
    kernel = VerdantKernel(seed=11, state_dim=32, run_label="gear-test")
    inner = RehearsingDevelopmentPipeline(config=RehearsalConfig(every_experiences=8, min_real_exposures=1))
    gear = GearPipeline(inner, mode=mode) if mode else inner
    pipe = ConveningDevelopmentPipeline(gear, VerdantStructurePipeline(), mode="ready")
    for lesson in LESSONS:
        pipe.advance(kernel, lesson)
    return kernel, gear


def test_watch_writes_nothing_and_measures_every_experience():
    plain, _ = _life(); watched, gear = _life("watch")
    assert watched.fingerprint() == plain.fingerprint()
    assert len(gear.gear_log.rows) == len(LESSONS)
    assert all(row[1] >= 0 for row in gear.gear_log.rows)          # T is strengthening only


def test_first_meeting_is_hotter_than_a_familiar_repeat():
    _, gear = _life("watch"); t = [row[1] for row in gear.gear_log.rows]
    assert t[0] > t[8]                                               # lesson 1 makes bonds; lesson 9 repeats


def test_drive_turns_off_the_clock_and_is_deterministic():
    a, ga = _life("drive"); b, _ = _life("drive")
    assert a.fingerprint() == b.fingerprint()
    assert ga.inner.rehearsal.config.every_experiences == 10 ** 9


def test_drive_needs_sleep_inside_and_bad_mode_refused():
    from verdant_development import VerdantDevelopmentPipeline
    with pytest.raises(ValueError):
        GearPipeline(VerdantDevelopmentPipeline(), mode="drive")
    with pytest.raises(ValueError):
        GearPipeline(None, mode="overdrive")
