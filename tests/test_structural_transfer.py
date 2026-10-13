"""Adversarial and native-compilation tests for structural transfer v0.1."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from verdant_kernel import VerdantKernel
from verdant_math.structural_transfer import experiment as t


def _native(role, seed=79101):
    kernel = VerdantKernel(seed=seed, state_dim=16, run_label=f"transfer-seed-{seed}")
    transition_ids = []
    for cycle in (t.RULE_CYCLE, *t.EDGE_CYCLES):
        transition, supplied, kind = t._teach(kernel, seed, role, cycle)
        assert transition and kind != "interference"
        transition_ids.append(transition)
    return kernel


def test_disjoint_task_design_and_opaque_labels():
    t._validate_design()
    for seed in t.SEEDS:
        nodes = t._nodes(seed)
        assert len(nodes) == len(set(nodes)) == 13
        assert all(t._LABEL.fullmatch(node) for node in nodes)
        direct = t._case_spec(seed, final=False)
        final = t._case_spec(seed, final=True)
        assert len(direct) == 8 and len(final) == 20
        assert all("expected" not in t._request(x) for x in final)
        assert sum(x["split"] == "transfer" for x in final) == 8
        assert sum(x["expected"] is None for x in final) == 4
        assert set((x["start"], x["steps"]) for x in direct).isdisjoint(
            (x["start"], x["steps"]) for x in final)


def test_native_multistep_composition_has_evidence_but_no_taught_path_answer():
    kernel = _native("progressive")
    source = t._nodes(79101)[0]
    before = kernel.fingerprint()
    response = t._respond(kernel, dict(start=source, steps=4))
    assert response["status"] == "derived"
    assert response["endpoint"] == t._nodes(79101)[4]
    assert len(response["steps"]) == 4
    assert len({hop["claim_ref"] for hop in response["steps"]}) == 4
    assert all(hop["evidence_refs"] for hop in response["steps"])
    assert response["rule_claim_refs"] and response["rule_evidence_refs"]
    assert kernel.fingerprint() == before
    assert not any(c.predicate == "route_path_answer" for c in kernel.state.claims.values())


def test_controls_do_not_fake_composition():
    seed = 79101
    task = dict(start=t._nodes(seed)[4], steps=2)
    good = t._respond(_native("progressive"), task)
    null = t._respond(_native("exact_null"), task)
    no_rule = t._respond(_native("no_rule"), task)
    incomplete = t._respond(_native("incomplete"), task)
    wrong = t._respond(_native("wrong_link"), task)
    assert good == null
    assert good["endpoint"] == t._nodes(seed)[6]
    assert no_rule["status"] == "abstained" and no_rule["reason"] == "missing_rule"
    assert incomplete["status"] == "abstained" and incomplete["reason"] == "missing_edge"
    assert len(incomplete["steps"]) == 1
    assert wrong["status"] == "derived" and wrong["endpoint"] == t._nodes(seed)[9]
    assert wrong["endpoint"] != good["endpoint"]


def test_ceiling_refuses_fabricated_edge():
    kernel = _native("progressive")
    result = t._respond(kernel, dict(start=t._nodes(79101)[11], steps=3))
    assert result["status"] == "abstained" and result["endpoint"] is None
    assert result["reason"] == "missing_edge"
    assert len(result["steps"]) == 1
    for request in (dict(start="route:node:12", steps=2),
                    dict(start=t._nodes(79101)[0], steps=5),
                    dict(start=t._nodes(79101)[0], steps=1.0)):
        with pytest.raises(t.TransferIntegrityError):
            t._respond(kernel, request)


def test_zero_cycle_is_checkpointed_graded_only_after_capture(tmp_path):
    output = t.start(tmp_path / "zero", cycles=0, seeds=(79101,))
    before = output.read_bytes()
    batch = json.loads(before)
    assert len(batch["arms"]) == 5
    assert all(arm["native_cycles"] == 0 for arm in batch["arms"])
    assert all(arm["probes"][0]["evaluation"] == "diagnostic"
               and len(arm["probes"][0]["records"]) == 8 for arm in batch["arms"])
    result = t.grade(tmp_path / "zero")
    assert output.read_bytes() == before
    grades = json.loads(result.read_bytes())
    assert all(arm["probes"][0]["abstained"] == 8 for arm in grades["grading"])
    assert t.resume(tmp_path / "zero").read_bytes() == before
    assert t.grade(tmp_path / "zero").read_bytes() == result.read_bytes()
    with pytest.raises(FileExistsError):
        t.start(tmp_path / "zero", cycles=0, seeds=(79101,))


def test_interrupted_run_recovers_to_identical_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "MILESTONES", (0, 3, 5))
    before = t._teach
    broken = [False]

    def stop_once(kernel, seed, role, cycle):
        if not broken[0] and role == "progressive" and cycle == 4:
            broken[0] = True
            raise RuntimeError("simulated interruption")
        return before(kernel, seed, role, cycle)

    monkeypatch.setattr(t, "_teach", stop_once)
    root = tmp_path / "partial"
    with pytest.raises(RuntimeError, match="interruption"):
        t.start(root, cycles=5, seeds=(79101,))
    assert (root / "stages" / "seed-79101" / "progressive" / "00003.vst").is_file()
    monkeypatch.setattr(t, "_teach", before)
    resumed = t.resume(root)
    original = t.start(tmp_path / "uninterrupted", cycles=5, seeds=(79101,))
    assert resumed.read_bytes() == original.read_bytes()
    assert t.resume(root).read_bytes() == resumed.read_bytes()


def test_tampered_checkpoint_and_foreign_code_manifest_fail_closed(tmp_path, monkeypatch):
    root = tmp_path / "trial"
    t.start(root, cycles=0, seeds=(79101,))
    stage = root / "stages" / "seed-79101" / "progressive" / "00000.vst"
    original = stage.read_bytes()
    data = json.loads(original)
    data["data"]["checkpoint_sha256"] = "0" * 64
    data["digest"] = t.util.digest(t.util._json(data["data"]))
    stage.write_bytes(t.util._json(data))
    with pytest.raises(t.TransferIntegrityError, match="Changed checkpoint"):
        t.resume(root)
    stage.write_bytes(original)
    original_manifest = t._manifest

    def drift(cycles, seeds):
        manifest = original_manifest(cycles, seeds)
        manifest["native_sources"]["requirements-lock.txt"] = "0" * 64
        return manifest
    monkeypatch.setattr(t, "_manifest", drift)
    with pytest.raises(t.TransferIntegrityError, match="Manifest"):
        t.resume(root)


def test_guard_original_evidence_digests():
    import hashlib
    base = Path(__file__).resolve().parents[1] / "artifacts" / "terminal_successor_v065"
    assert hashlib.sha256((base / "responses.vsrb").read_bytes()).hexdigest() == (
        "6f7fc01cfa4f380fd3b7f09e10fb0de4631cc1b5c1071823e59e864b6aad7f26")
    assert hashlib.sha256((base / "evaluation.vsrr").read_bytes()).hexdigest() == (
        "e704ee573b92f6bd9979502ae92d73f9f7f75a6928e1eb6e3a63d4900cfbea0f")


def test_200_native_cycles_per_arm_and_durable_grades(tmp_path):
    # Small genuine time-ordered native teaching run (5 private roles, one seed).
    root = tmp_path / "two-hundred"
    responses = t.start(root, cycles=200, seeds=(79101,))
    assert responses.is_file()
    assert t.resume(root).read_bytes() == responses.read_bytes()
    receipt = json.loads(t.grade(root).read_bytes())
    rows = {x["role"]: x for x in receipt["grading"]}
    assert len(rows) == 5
    assert all(x["probes"][-1]["cycle"] == 200 for x in rows.values())
    assert rows["progressive"]["probes"][-1]["correct"] >= 2
    assert rows["exact_null"]["probes"] == rows["progressive"]["probes"]
    assert rows["no_rule"]["probes"][-1]["correct"] == 0
    assert receipt["computed_after_durable_responses"] is True
    assert receipt["response_sha256"] == t.util.digest(responses.read_bytes())


def test_report_displays_verified_split_denominators(tmp_path, capsys):
    root = tmp_path / "report"
    t.start(root, cycles=0, seeds=(79101,))
    t.report(root)
    printed = capsys.readouterr().out
    assert "Verified response SHA-256:" in printed
    assert "progressive diagnostic correct 0 incorrect 0 abstained 8 total 8" in printed
    assert (root / "grades.json").is_file()
