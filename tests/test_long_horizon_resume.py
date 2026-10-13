"""Recovery acceptance tests: native state, zero-grade barrier, and fail-closed restart."""
from __future__ import annotations

import json

import pytest

from verdant_math.long_horizon_preflight import __main__ as m
from verdant_math.long_horizon_preflight import resumable as r


def test_resumable_zero_cycle_and_external_grade(tmp_path):
    location = tmp_path / "zero"
    result = r.start(location, cycles=0, seeds=(79066,))
    assert result.exists()
    assert r.resume(location).read_bytes() == result.read_bytes()
    receipt = json.loads(result.read_bytes())
    assert len(receipt["arms"]) == 4
    assert all(x["native_cycles"] == 0 for x in receipt["arms"])
    grades = m.grade(result, tmp_path / "grades.json")
    assert all(p["probes"][0]["abstained"] == 20
               for p in json.loads(grades.read_bytes())["grading"])


def test_interruption_after_committed_milestone_replays_only_tail(tmp_path, monkeypatch):
    # Dedicated test milestone schedule. The real protocol still uses 0/250/500/750/1000.
    monkeypatch.setattr(m, "PROBES", (0, 3, 5))
    real = m._unrelated_experience
    count = [0]

    def interrupt(kernel, *, key, cycle):
        if ":role:progressive:" in key and cycle == 4 and count[0] == 0:
            count[0] += 1
            raise InterruptedError("intentional simulated power loss")
        return real(kernel, key=key, cycle=cycle)

    monkeypatch.setattr(m, "_unrelated_experience", interrupt)
    partial = tmp_path / "partial"
    with pytest.raises(InterruptedError, match="power loss"):
        r.start(partial, cycles=5, seeds=(79066,))
    assert (partial / "stages" / "seed-79066" / "progressive" / "00003.vstage").exists()
    assert not (partial / "responses.json").exists()
    monkeypatch.setattr(m, "_unrelated_experience", real)
    finished = r.resume(partial)
    reference = r.start(tmp_path / "reference", cycles=5, seeds=(79066,))
    assert finished.read_bytes() == reference.read_bytes()
    assert r.resume(partial).read_bytes() == finished.read_bytes()


def test_rejects_tampered_milestone_without_overwriting(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "PROBES", (0, 2))
    root = tmp_path / "trial"
    output = r.start(root, cycles=2, seeds=(79066,))
    frozen_output = output.read_bytes()
    stage = root / "stages" / "seed-79066" / "progressive" / "00002.vstage"
    envelope = json.loads(stage.read_bytes())
    envelope["payload"]["checkpoint_sha256"] = "0" * 64
    envelope["sha256"] = m.digest(m._json(envelope["payload"]))
    stage.write_bytes(m._json(envelope))
    with pytest.raises(m.PreflightError, match="Checkpoint bytes changed"):
        r.resume(root)
    assert output.read_bytes() == frozen_output


def test_changed_source_manifest_fails_closed(tmp_path, monkeypatch):
    root = tmp_path / "trial"
    r.start(root, cycles=0, seeds=(79066,))
    original = r._manifest
    def altered(cycles, seeds):
        result = original(cycles, seeds)
        result["code_sha256"]["requirements-lock.txt"] = "0" * 64
        return result
    monkeypatch.setattr(r, "_manifest", altered)
    with pytest.raises(m.PreflightError, match="Frozen trial"):
        r.resume(root)


def test_invalid_resume_does_not_make_a_cohort(tmp_path):
    with pytest.raises(m.PreflightError, match="manifest"):
        r.resume(tmp_path / "missing")
    with pytest.raises(ValueError):
        r.start(tmp_path / "invalid", cycles=12000, seeds=(79066,))


def test_native_fifty_cycle_recovery_runner_keeps_supplied_fact(tmp_path):
    root = tmp_path / "fifty"
    result = r.start(root, cycles=50, seeds=(79066,))
    batch = json.loads(result.read_bytes())
    assert len(batch["arms"]) == 4
    by_role = {arm["role"]: arm for arm in batch["arms"]}
    for role, count in (("progressive", 1), ("rehearsal", 1),
                        ("activity_control", 0), ("delayed", 0)):
        arm = by_role[role]
        assert arm["native_cycles"] == 50
        assert len(arm["teaching"]) == count
        assert len(arm["probes"]) == 2
        answers = [item["reply"]["answer"] for item in arm["probes"][-1]["responses"]]
        assert answers.count(5) == count  # First taught fact: 5 + 0 = 5
        assert all(answer is None or answer == 5 for answer in answers)
        stage = root / "stages" / "seed-79066" / role / "00050.vstage"
        assert stage.is_file()
    assert r.resume(root).read_bytes() == result.read_bytes()
