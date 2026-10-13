"""Tests for the isolated native long-horizon preflight, NOT its final outcome."""
from __future__ import annotations

import hashlib
import json

import pytest

from verdant_kernel import VerdantKernel
from verdant_math.long_horizon_preflight import __main__ as m


def test_schedule_has_distinct_progression_and_delayed_teaching():
    assert len(m.TRAIN) == 8
    assert len({*m.TRAIN, *m.REVERSED, *m.NOVEL}) == 20
    assert all(m.lesson_for("progressive", n) == p
               for n, p in zip(m._SLOTS, m.TRAIN))
    assert all(m.lesson_for("delayed", n) == p
               for n, p in zip(m._LATE_SLOTS, m.TRAIN))
    assert all(m.lesson_for("rehearsal", n) == m.TRAIN[0] for n in m._SLOTS)
    assert all(m.lesson_for("activity_control", n) is None
               for n in (*m._SLOTS, *m._LATE_SLOTS))
    assert m.lesson_for("progressive", 400) is None


def test_invalid_run_does_not_create_files(tmp_path):
    for bad in (-1, 1001, True):
        with pytest.raises(ValueError):
            m.execute(tmp_path / f"bad-{bad}", cycles=bad, seeds=(79066,))
    with pytest.raises(ValueError):
        m.execute(tmp_path / "bad-seeds", cycles=0, seeds=(1, 1))


def test_zero_cycle_native_checkpoint_and_all_responses_before_grading(tmp_path):
    path = m.execute(tmp_path / "cohort", cycles=0, seeds=(79066,))
    data = json.loads(path.read_bytes())
    assert data["version"] == m.VERSION and data["grading_performed"] is False
    assert len(data["arms"]) == 4
    for arm in data["arms"]:
        assert arm["native_cycles"] == 0
        assert len(arm["probes"]) == 1
        assert len(arm["probes"][0]["responses"]) == 20
        assert (tmp_path / "cohort" / "seed-79066" / arm["role"]
                / "cycle-00000.vdk").exists() is False
    before = path.read_bytes()
    grades = m.grade(path, tmp_path / "grade.json")
    assert path.read_bytes() == before
    result = json.loads(grades.read_bytes())
    assert result["response_sha256"] == hashlib.sha256(before).hexdigest()
    assert all(arm["probes"][0]["abstained"] == 20 for arm in result["grading"])
    with pytest.raises(m.PreflightError):
        m.grade(path, grades)
    with pytest.raises(m.PreflightError):
        m.execute(tmp_path / "cohort", cycles=0, seeds=(79066,))


def test_native_teacher_testimony_is_private_and_recalled():
    original = VerdantKernel(seed=79066, state_dim=16, run_label="test-preflight")
    before = original.fingerprint()
    private = VerdantKernel.from_state(original.snapshot())
    transition = m._teach(private, key="preflight:test:lesson-1", pair=(5, 1))
    assert transition and original.fingerprint() == before
    result = m._probe(private, cycle=1)
    taught = result["responses"][1]  # (5, 1)
    assert taught["reply"]["answer"] == 6
    assert result["responses"][9]["reply"]["answer"] is None  # reversed (1, 5)


def test_interference_is_native_but_does_not_prove_learning():
    kernel = VerdantKernel(seed=79066, state_dim=16, run_label="test-interference")
    initial_cycle = kernel.state.cycle
    m._unrelated_experience(kernel, key="preflight:test:interference", cycle=1)
    assert kernel.state.cycle == initial_cycle + 1
    assert not kernel.state.claims
    assert all(x["reply"]["answer"] is None for x in m._probe(kernel, cycle=1)["responses"])


def test_grade_detects_changed_order_even_with_canonical_json(tmp_path):
    path = m.execute(tmp_path / "cohort", cycles=0, seeds=(79066,))
    data = json.loads(path.read_bytes())
    first = data["arms"][0]["probes"][0]["responses"]
    first[0], first[1] = first[1], first[0]
    path.write_bytes(m._json(data))
    with pytest.raises(m.PreflightError, match="order"):
        m.grade(path, tmp_path / "grades.json")


def test_historical_v065_artifacts_remain_unchanged():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    checks = {
        "responses.vsrb": "6f7fc01cfa4f380fd3b7f09e10fb0de4631cc1b5c1071823e59e864b6aad7f26",
        "evaluation.vsrr": "e704ee573b92f6bd9979502ae92d73f9f7f75a6928e1eb6e3a63d4900cfbea0f",
    }
    for name, expected in checks.items():
        raw = (root / "artifacts" / "terminal_successor_v065" / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
