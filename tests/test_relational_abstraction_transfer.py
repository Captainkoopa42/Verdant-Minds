"""Controlled exact typed-role abstraction and Q retrieval tests.

All Ps and the historical Q are truly earned/promoted in native kernel fixtures.
Synthetic labels define expected test outputs; no learned semantics are claimed.
"""
import pytest

from test_structural_relation_lens import native_fixture, fresh, teach_p
from verdant_hierarchy import VerdantHierarchyPipeline
from verdant_hierarchy.relational_abstraction import RelationalAbstractionProbe
from verdant_interaction import VerdantStructureInteractionPipeline
from verdant_kernel import VerdantKernel, load_checkpoint, save_checkpoint


def test_native_council_q_preserves_holdout_typed_results(native_fixture):
    kernel, ids, qid = fresh(native_fixture)
    probe = RelationalAbstractionProbe()
    before = kernel.snapshot()
    report = probe.inspect(kernel, ids["novel"])

    assert report["all_verdicts_identical"] is True
    assert report["exhaustive"]["accepted_ids"] == sorted([
        ids["aa"], ids["bb"], ids["cc"]
    ])
    assert ids["type_negative"] not in report["q_overlay"]["accepted_ids"]
    assert ids["direction_negative"] not in report["q_overlay"]["accepted_ids"]
    assert report["q_overlay"]["abstained_ids"] == [ids["missing"]]
    assert report["q_overlay"]["q_groups"] == 1
    assert report["q_overlay"]["q_ids_used"] == [qid]
    assert report["q_overlay"]["key_comparisons"] < report["p_keyed"]["key_comparisons"]
    assert report["q_overlay"]["exact_verifications"] == report["p_keyed"]["exact_verifications"]
    assert report["q_overlay"]["exact_verifications"] < report["exhaustive"]["exact_verifications"]
    assert report["measured_wall_clock_speedup"] is False
    assert kernel.snapshot() == before


@pytest.mark.parametrize("name", ["type_negative", "direction_negative", "missing", "aa"])
def test_no_false_positive_or_silent_incomplete_evidence(native_fixture, name):
    kernel, ids, qid = fresh(native_fixture)
    result = RelationalAbstractionProbe().inspect(kernel, ids[name])
    assert result["all_verdicts_identical"]
    assert result["q_overlay"]["all_verdicts"] == result["exhaustive"]["all_verdicts"]
    assert result["q_overlay"]["abstained_ids"] == result["exhaustive"]["abstained_ids"]
    assert result["q_overlay"]["accepted_ids"] == result["exhaustive"]["accepted_ids"]


def test_actual_q_ablation_removes_group_index_benefit_not_accuracy(native_fixture):
    kernel, ids, qid = fresh(native_fixture)
    unchanged = kernel.snapshot()
    with_q = RelationalAbstractionProbe().inspect(kernel, ids["novel"])
    control = VerdantKernel.from_state(kernel.snapshot())
    VerdantHierarchyPipeline.ablate(control, qid, "controlled native Q ablation")
    without_q = RelationalAbstractionProbe().inspect(control, ids["novel"])
    assert without_q["q_overlay"]["q_groups"] == 0
    assert without_q["q_overlay"]["key_comparisons"] == without_q["p_keyed"]["key_comparisons"]
    assert with_q["q_overlay"]["key_comparisons"] < without_q["q_overlay"]["key_comparisons"]
    assert without_q["q_overlay"]["all_verdicts"] == with_q["q_overlay"]["all_verdicts"]
    assert kernel.snapshot() == unchanged


def test_new_q_role_overlay_can_carry_multiple_strict_role_families():
    kernel = VerdantKernel(seed=171923, state_dim=16,
                           run_label="native-heterogeneous-q")
    kernel.update_plasticity_policy(decay_rate=0.0, learning_rate=0.40)
    kernel.update_structure_policy(
        minimum_members=3, maximum_members=3,
        maximum_neighbors_per_seed=2, minimum_member_association_strength=0.20,
        minimum_reconstructability=0.25, minimum_internal_cohesion=0.20,
        minimum_recurrence_events=2, minimum_evidence_events=2,
    )
    kernel.update_hierarchy_policy(minimum_interaction_events=3,
                                   minimum_evidence_events=6)
    historical = [
        teach_p(kernel, "ss", relation_type="supports"),
        teach_p(kernel, "pp", relation_type="precedes"),
        teach_p(kernel, "cc", relation_type="contains"),
    ]
    inter = VerdantStructureInteractionPipeline()
    hierarchy = VerdantHierarchyPipeline()
    for sid in historical:
        inter.interact(kernel, sid)
        hierarchy.observe(kernel)
    candidate = next(item for item in kernel.state.hierarchy_candidates.values()
                     if set(item.member_structure_ids) == set(historical))
    assert candidate.status.value == "eligible"
    qid = hierarchy.promote(kernel, candidate.candidate_id).event.layered_structure_id
    holdout = teach_p(kernel, "nn", relation_type="supports")
    probe = RelationalAbstractionProbe().inspect(kernel, holdout)

    assert probe["q_overlay"]["q_groups"] == 3
    assert probe["q_overlay"]["q_ids_used"] == [qid]
    assert probe["q_overlay"]["accepted_ids"] == [historical[0]]
    assert probe["q_overlay"]["rejected_count"] == 2
    assert probe["all_verdicts_identical"]
    # Three disparate relations in ONE real Q do not magically become synonyms.
    assert probe["learned_semantic_equivalence"] is False


def test_checkpoint_roundtrip_and_readonly_native_source(native_fixture, tmp_path):
    kernel, ids, qid = fresh(native_fixture)
    path = tmp_path / "native-q.vdk"
    save_checkpoint(path, kernel.snapshot())
    raw = path.read_bytes()
    original = kernel.fingerprint()
    restored = VerdantKernel.from_state(load_checkpoint(path))
    report = RelationalAbstractionProbe().inspect(restored, ids["novel"])
    assert report["q_overlay"]["all_verdicts"] == report["exhaustive"]["all_verdicts"]
    assert restored.fingerprint() == original
    assert path.read_bytes() == raw
    assert qid in restored.state.layered_structures


def test_exact_only_no_false_claims_from_strict_threshold(native_fixture):
    kernel, ids, _qid = fresh(native_fixture)
    r = RelationalAbstractionProbe().inspect(kernel, ids["type_negative"])
    assert r["exact_typed_f1_threshold"] == 1.0
    assert r["actual_prospective_accuracy_not_claimed"]
    assert not r["native_structure_or_q_mutation"]
    assert r["construction_ignored_in_query_cost"]
    assert not r["learned_semantic_equivalence"]
