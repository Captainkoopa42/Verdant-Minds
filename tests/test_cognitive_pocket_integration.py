"""Explicit native obligation bridge, local plasticity and VDK end-to-end tests."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

from test_hierarchy_phase import hierarchy_fixture, fresh
from test_cognitive_pocket_cultivation import _typed_native_sources
from verdant_kernel import VerdantKernel, save_checkpoint
from verdant_pockets import PocketIntegrityError, cultivate_pocket
from verdant_pockets.adaptation import local_cultivation
from verdant_pockets.obligations import inspect_obligation_handoff
from verdant_pockets.dynamics import simulate
from verdant_pockets.lifecycle_cli import run_native
from verdant_pockets.lifecycle import load_lifecycle
from verdant_pockets.compression import pack_native_relations, unpack_native_relations, validate_native_dictionary


@pytest.fixture
def earned(hierarchy_fixture):
    kernel, family, qid, _, _, _ = fresh(hierarchy_fixture)
    labels = _typed_native_sources(kernel, family, mixed=True)
    pocket = cultivate_pocket(kernel, family, q_id=qid)
    return kernel, family, qid, pocket, labels


def test_bounded_private_adaptation_with_frozen_heldout_control(earned):
    kernel, family, qid, pocket, labels = earned
    old = kernel.fingerprint()
    adaptive = local_cultivation(pocket, epochs=3, rounds=8, rate=0.07)
    assert adaptive["source_pocket_id"] == pocket["pocket_id"]
    assert len(adaptive["events"]) == 3 * (len(family)-1)
    assert set(adaptive["initial_weights"]) == set(adaptive["final_weights"])
    assert any(adaptive["final_weights"][k] != adaptive["initial_weights"][k] for k in adaptive["initial_weights"])
    assert all(0 <= v <= 0.4 for v in adaptive["final_weights"].values())
    assert adaptive["held_out"]["semantic_transfer_demonstrated"] is False
    assert kernel.fingerprint() == old
    assert adaptive == local_cultivation(pocket, epochs=3, rounds=8, rate=0.07)


def test_bad_adaptation_policy_or_unknown_weights_rejected(earned):
    _, family, _, pocket, _ = earned
    with pytest.raises(PocketIntegrityError):
        local_cultivation(pocket, epochs=99)
    with pytest.raises(PocketIntegrityError):
        local_cultivation(pocket, rate=-0.5)
    with pytest.raises(PocketIntegrityError):
        simulate(pocket, source_p_id=family[0], mode="role_aligned", hypothetical_weights={"unknown|missing": 0.3})
    with pytest.raises(PocketIntegrityError):
        simulate(pocket, source_p_id=family[0], mode="role_aligned", hypothetical_weights={"unknown|missing": 999.0})


def test_real_native_detector_no_laundered_role_obligations(earned):
    kernel, family, qid, pocket, labels = earned
    before = kernel.fingerprint()
    result = inspect_obligation_handoff(kernel, pocket)
    assert result["candidate_obligations"] == []
    assert result["no_hypothetical_role_laundering"]
    assert kernel.fingerprint() == before
    assert len(kernel.state.obligation_kernels) == 0


def test_native_explicit_requires_generates_only_inspection_candidate(earned):
    kernel, family, qid, _, labels = earned
    relation = kernel.propose_relation(
        labels["a2"], labels["b2"], "requires",
        evidence_refs=kernel.state.structures[family[0]].evidence_refs,
        directed=True, weight=0.95,
    )
    pocket = cultivate_pocket(kernel, family, q_id=qid)
    old = kernel.fingerprint()
    observation = inspect_obligation_handoff(kernel, pocket)
    assert relation.relation_id in observation["inspected_canonical_dependency_relations_in_scope"]
    assert any(item["canonical_relation_id"] == relation.relation_id
               for item in observation["candidate_obligations"])
    assert all(item["status"] == "candidate_only_not_recorded"
               for item in observation["candidate_obligations"])
    assert len(kernel.state.obligation_kernels) == 0
    assert kernel.fingerprint() == old


def test_native_obligation_handoff_rejects_different_checkpoint(earned):
    kernel, family, qid, pocket, labels = earned
    kernel.propose_relation(labels["a1"], labels["b1"], "requires",
        evidence_refs=kernel.state.structures[family[0]].evidence_refs)
    with pytest.raises(PocketIntegrityError):
        inspect_obligation_handoff(kernel, pocket)


def test_full_cli_seals_native_q_and_verifies_without_rewriting_vdk(earned, tmp_path):
    kernel, family, qid, pocket, labels = earned
    vdk = tmp_path / "source.vdk"
    save_checkpoint(vdk, kernel.snapshot())
    before = vdk.read_bytes()
    dest = tmp_path / "first.vcpl"
    summary = run_native(vdk, dest, q_index=0, rounds=4)
    assert dest.is_file()
    lifecycle = load_lifecycle(dest)
    assert lifecycle["parent_pocket"]["q_context_id"] == qid
    assert lifecycle["local_plasticity"]["events"]
    assert lifecycle["compression"]["lossless_exact_reconstruction"]
    assert summary["no_native_vdk_changes"]
    assert summary["native_obligation_candidates"] == 0
    assert len(lifecycle["experimental_daughters"]["daughters"]) >= 1
    assert vdk.read_bytes() == before
    with pytest.raises(FileExistsError):
        run_native(vdk, dest, q_index=0, rounds=4)
    assert vdk.read_bytes() == before



def test_native_typed_relation_dictionary_is_lossless_and_evidence_complete(earned):
    kernel, family, qid, pocket, labels = earned
    before = kernel.fingerprint()
    result = pack_native_relations(pocket)
    restored = unpack_native_relations(result)
    assert restored == sorted(pocket["current_member_relations"], key=lambda e: e["id"])
    assert result["receipt"]["full_reconstruction"]
    assert result["receipt"]["type_and_evidence_retention"]
    assert not result["receipt"]["is_learned_semantic_compression"]
    assert result["receipt"]["dictionary_encoded_bytes"] > 0
    validate_native_dictionary(result, pocket)
    assert kernel.fingerprint() == before


def test_dictionary_tampering_and_wrong_pocket_rejected(earned):
    _, family, qid, pocket, labels = earned
    packed = pack_native_relations(pocket)
    mutated = deepcopy(packed)
    mutated["encoded_rows"][0][3] = len(mutated["relation_type_table"]) + 1
    with pytest.raises(PocketIntegrityError):
        validate_native_dictionary(mutated, pocket)
    changed = deepcopy(pocket)
    changed["pocket_id"] = "other"
    with pytest.raises(PocketIntegrityError):
        validate_native_dictionary(packed, changed)
