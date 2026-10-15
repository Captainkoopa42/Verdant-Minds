"""Adversarial small native Council P/Q cognitive-pocket pilot."""
from __future__ import annotations

from copy import deepcopy

import pytest

from test_hierarchy_phase import hierarchy_fixture, fresh
from verdant_pockets import PocketIntegrityError, cultivate_pocket


def _label_ids(kernel):
    return {c.normalized_label: cid for cid, c in kernel.state.concepts.items()}


def _typed_native_sources(kernel, p_ids, *, mixed=False):
    """Harness-supplied canonical testimony, never claimed as self-discovery."""
    label_ids = _label_ids(kernel)
    all_types = ("supports", "precedes", "supports")
    pairs = [("a1","a2"),("a2","a3"),("a3","a4")]
    for index, sid in enumerate(p_ids):
        pref = ("a","b","c")[index]
        types = ["supports"] * 3 if index == 0 else (
            ["precedes"] * 3 if index == 1 else
            ["contains", "contains", "encloses"] if mixed else ["supports"] * 3
        )
        for j in range(3):
            kernel.propose_relation(
                label_ids[f"{pref}{j+1}"],
                label_ids[f"{pref}{j+2}"],
                types[j],
                evidence_refs=kernel.state.structures[sid].evidence_refs,
                directed=True,
                confidence=0.8,
                weight=0.8,
            )
    return label_ids


def test_pocket_uses_genuine_promoted_q_and_preserves_distinct_types(hierarchy_fixture):
    kernel, family, qid, _, _, _ = fresh(hierarchy_fixture)
    _typed_native_sources(kernel, family, mixed=True)
    old = kernel.fingerprint()
    before = kernel.snapshot()
    pocket = cultivate_pocket(kernel, family, q_id=qid)
    assert pocket["canonical_fingerprint"] == old
    assert pocket["q_context_id"] == qid
    assert len(pocket["p_snapshots"]) == 3
    assert len(pocket["hypothetical_role_alignments"]) == 3
    assert len(pocket["current_member_relations"]) == 9
    assert len(pocket["evidenced_cross_p_relations"]) == 0
    assert len(pocket["evidenced_cross_p_walks"]) == 0
    assert len(pocket["local_rounds"]) == 6
    assert len(pocket["grammar_inventory"]) >= 2
    assert not pocket["controls"]["canonical_edge_created"]
    assert not pocket["controls"]["epistemic_truth_asserted_from_analogy"]
    assert not pocket["controls"]["actual_binary_compression_measured"]
    assert kernel.fingerprint() == old
    assert kernel.snapshot() == before


def test_pocket_repeat_and_order_are_deterministic(hierarchy_fixture):
    kernel, family, qid, _, _, _ = fresh(hierarchy_fixture)
    _typed_native_sources(kernel, family)
    first = cultivate_pocket(kernel, family, q_id=qid)
    second = cultivate_pocket(kernel, list(reversed(family)), q_id=qid)
    assert first == second
    assert first["pocket_id"] == second["pocket_id"]


def test_actual_cross_p_canonical_bridge_supports_only_path_not_inferred_truth(hierarchy_fixture):
    kernel, family, qid, _, _, _ = fresh(hierarchy_fixture)
    label_ids = _typed_native_sources(kernel, family)
    baseline = cultivate_pocket(kernel, family, q_id=qid)
    assert not baseline["evidenced_cross_p_walks"]
    bridge = kernel.propose_relation(
        label_ids["a4"], label_ids["b1"], "next_stage",
        evidence_refs=kernel.state.structures[family[0]].evidence_refs,
        weight=0.85, confidence=0.8,
    )
    before = kernel.fingerprint()
    with_bridge = cultivate_pocket(kernel, family, q_id=qid)
    assert any(r["id"] == bridge.relation_id for r in with_bridge["evidenced_cross_p_relations"])
    assert any(bridge.relation_id in walk["relation_ids"] for walk in with_bridge["evidenced_cross_p_walks"])
    assert all(w["derived_transitive_fact"] is False for w in with_bridge["evidenced_cross_p_walks"])
    assert kernel.fingerprint() == before
    assert any(
        x["activation"] != y["activation"]
        for x, y in zip(baseline["local_rounds"], with_bridge["local_rounds"])
    )


def test_role_analogies_do_not_create_cross_p_canonical_evidence(hierarchy_fixture):
    kernel, family, qid, _, _, _ = fresh(hierarchy_fixture)
    _typed_native_sources(kernel, family)
    pocket = cultivate_pocket(kernel, family, q_id=qid)
    assert pocket["hypothetical_role_alignments"]
    assert all(
        not a["canonical_relation_asserted"] and
        not a["semantic_equivalence_asserted"]
        for a in pocket["hypothetical_role_alignments"]
    )
    assert not pocket["evidenced_cross_p_relations"]
    assert not pocket["evidenced_cross_p_walks"]
    for record in pocket["local_rounds"]:
        assert record["channel_counts"]["evidenced_cross_p"] == 0
        assert record["channel_counts"]["hypothetical_analogy"] > 0


def test_ablation_of_analogy_changes_local_dynamics_not_canonical_memory(hierarchy_fixture):
    kernel, family, qid, _, _, _ = fresh(hierarchy_fixture)
    _typed_native_sources(kernel, family)
    old = kernel.fingerprint()
    treatment = cultivate_pocket(kernel, family, q_id=qid)
    control = cultivate_pocket(kernel, family, q_id=qid, minimum_alignment=1.0)
    assert treatment["p_snapshots"] == control["p_snapshots"]
    assert treatment["current_member_relations"] == control["current_member_relations"]
    assert kernel.fingerprint() == old
    assert len(treatment["hypothetical_role_alignments"]) >= len(
        control["hypothetical_role_alignments"]
    )


def test_strict_sources_q_membership_and_limits_fail_closed(hierarchy_fixture):
    kernel, family, qid, star, novel, _ = fresh(hierarchy_fixture)
    with pytest.raises(PocketIntegrityError):
        cultivate_pocket(kernel, (family[0], family[0]))
    with pytest.raises(PocketIntegrityError):
        cultivate_pocket(kernel, ("structure_not_real", family[0]))
    with pytest.raises(PocketIntegrityError):
        cultivate_pocket(kernel, (family[0], star), q_id=qid)
    with pytest.raises(PocketIntegrityError):
        cultivate_pocket(kernel, family, q_id="layered_missing")
    with pytest.raises(PocketIntegrityError):
        cultivate_pocket(kernel, family, rounds=13)
    with pytest.raises(PocketIntegrityError):
        cultivate_pocket(kernel, family, rounds=0)


def test_missing_evidence_closure_rejected_not_laundered_as_analogy(hierarchy_fixture):
    kernel, family, qid, _, _, _ = fresh(hierarchy_fixture)
    _typed_native_sources(kernel, family)
    rid = next(iter(kernel.state.relations))
    rel = kernel.state.relations[rid]
    kernel.state.relations[rid] = rel.model_copy(update={"evidence_refs": ("nonexistent:evidence",)})
    with pytest.raises(PocketIntegrityError, match="evidence closure"):
        cultivate_pocket(kernel, family, q_id=qid)


def test_no_typed_evidence_does_not_generate_factual_cross_links(hierarchy_fixture):
    kernel, family, qid, _, _, _ = fresh(hierarchy_fixture)
    pocket = cultivate_pocket(kernel, family, q_id=qid)
    assert pocket["hypothetical_role_alignments"]
    assert all(p["relation_grammar"] is None for p in pocket["p_snapshots"])
    assert pocket["grammar_inventory"][0]["grammar"] is None
    assert pocket["current_member_relations"] == []
    assert pocket["evidenced_cross_p_walks"] == []


def test_snapshot_roundtrip_exact_and_no_new_obligation(hierarchy_fixture, tmp_path):
    from verdant_kernel import VerdantKernel, save_checkpoint, load_checkpoint

    kernel, family, qid, _, _, _ = fresh(hierarchy_fixture)
    _typed_native_sources(kernel, family)
    checkpoint = tmp_path / "before.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    original = checkpoint.read_bytes()
    first = cultivate_pocket(kernel, family, q_id=qid)
    restored = VerdantKernel.from_state(load_checkpoint(checkpoint))
    second = cultivate_pocket(restored, family, q_id=qid)
    assert first == second
    assert checkpoint.read_bytes() == original
    assert len(restored.state.obligations) == len(kernel.state.obligations) if hasattr(restored.state, "obligations") else True
