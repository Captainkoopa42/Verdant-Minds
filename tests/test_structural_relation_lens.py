"""Matched native-P structural discrimination and Q efficiency experiment.

Every P and Q is actually cultivated/promoted through the existing native
development, structure, interaction and Council pipelines. Only label/truth
expectations are synthetic researcher-specified controls, not learned facts.
"""
import hashlib
import pytest

from verdant_development import VerdantDevelopmentPipeline
from verdant_hierarchy import VerdantHierarchyPipeline
from verdant_interaction import VerdantStructureInteractionPipeline
from verdant_interaction.relation_lens import RelationAwareLens
from verdant_kernel import (
    EvidenceKind, ExperienceCommand, RelationProposal, VerdantKernel,
    load_checkpoint, save_checkpoint,
)
from verdant_structures import VerdantStructurePipeline


def teach_p(kernel, prefix, *, relation_type="supports", orientation="out", with_relations=True):
    labels = tuple(prefix + x for x in ("0", "1", "2"))
    if orientation == "out":
        arrows = ((labels[0], labels[1]), (labels[0], labels[2]))
    elif orientation == "in":
        arrows = ((labels[1], labels[0]), (labels[2], labels[0]))
    else:
        raise ValueError("Invalid fixture orientation")
    proposals = tuple(
        RelationProposal(
            source_label=a, target_label=b, relation_type=relation_type,
            directed=True, weight=0.8, confidence=0.9,
        )
        for a, b in arrows
    ) if with_relations else ()
    development = VerdantDevelopmentPipeline()
    for i in range(6):
        key = f"relation-lens:{prefix}:{i}"
        development.advance(kernel, ExperienceCommand(
            event_key=key,
            source_ref="controlled_testimony_not_physical_fact",
            modality="text",
            payload_sha256=hashlib.sha256(key.encode()).hexdigest(),
            feature_vector=(1.0, 0.0, 0.0),
            concept_labels=labels,
            relation_proposals=proposals,
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            semantic_evidence_details={"author_supplied": True},
            metadata={"context_id": f"{prefix}-context-{i%2}"},
        ))
    labelset = set(labels)
    candidates = [
        item for item in kernel.state.structure_candidates.values()
        if {kernel.state.concepts[cid].normalized_label
            for cid in item.member_concept_ids} == labelset
    ]
    assert candidates
    candidate = max(candidates, key=lambda x: x.occurrence_count)
    assert candidate.status.value == "eligible"
    sid = VerdantStructurePipeline().promote(kernel, candidate.candidate_id).event.structure_id
    if with_relations:
        assert len(kernel.state.structures[sid].member_relation_ids) == 2
    return sid


@pytest.fixture(scope="module")
def native_fixture():
    kernel = VerdantKernel(seed=170271, state_dim=16, run_label="relation-lens-native")
    kernel.update_plasticity_policy(decay_rate=0.0, learning_rate=0.40)
    kernel.update_structure_policy(
        minimum_members=3, maximum_members=3,
        maximum_neighbors_per_seed=2,
        minimum_member_association_strength=0.20,
        minimum_reconstructability=0.25,
        minimum_internal_cohesion=0.20,
        minimum_recurrence_events=2,
        minimum_evidence_events=2,
    )
    kernel.update_hierarchy_policy(minimum_interaction_events=3, minimum_evidence_events=6)
    group = {}
    for prefix, kind, orientation in (
        ("aa", "supports", "out"),
        ("bb", "supports", "out"),
        ("cc", "supports", "out"),
    ):
        group[prefix] = teach_p(kernel, prefix, relation_type=kind, orientation=orientation)
    native = VerdantStructureInteractionPipeline()
    hierarchy = VerdantHierarchyPipeline()
    for sid in group.values():
        native.interact(kernel, sid)
        hierarchy.observe(kernel)
    candidate = next(
        item for item in kernel.state.hierarchy_candidates.values()
        if set(item.member_structure_ids) == set(group.values())
    )
    assert candidate.status.value == "eligible"
    qid = hierarchy.promote(kernel, candidate.candidate_id).event.layered_structure_id
    assert kernel.state.layered_structures[qid].member_structure_ids

    # Holdouts are learned AFTER the native Q exists; their matching labels
    # are synthetic test annotations, not semantic truths installed by Q.
    group["novel"] = teach_p(kernel, "nn", relation_type="supports", orientation="out")
    group["type_negative"] = teach_p(kernel, "tt", relation_type="precedes", orientation="out")
    group["direction_negative"] = teach_p(kernel, "dd", relation_type="supports", orientation="in")
    group["missing"] = teach_p(kernel, "mm", with_relations=False)
    return kernel.snapshot(), group, qid


def fresh(native_fixture):
    state, group, qid = native_fixture
    return VerdantKernel.from_state(state.model_copy(deep=True)), dict(group), qid


def test_relation_lens_rejects_type_and_direction_with_native_topology_held_equal(native_fixture):
    kernel, groups, _ = fresh(native_fixture)
    lens = RelationAwareLens()
    source = groups["aa"]
    expected = [
        ("bb", True),
        ("novel", True),
        ("type_negative", False),
        ("direction_negative", False),
    ]
    for name, truth in expected:
        report = lens.inspect(kernel, source, groups[name])
        assert report["baseline_accept"] is True
        assert report["verdict"] == ("accept" if truth else "reject")
        assert report["typed_f1"] == pytest.approx(1.0) if truth else report["typed_f1"] < 0.90
        assert report["evaluated_mappings"] == 6
        assert report["best_mapping"] or not truth


def test_lens_abstains_without_native_member_relation_provenance(native_fixture):
    kernel, groups, _ = fresh(native_fixture)
    report = RelationAwareLens().inspect(kernel, groups["aa"], groups["missing"])
    assert report["baseline_accept"]
    assert report["verdict"] == "abstain"
    assert report["typed_f1"] is None


def test_native_council_and_semantic_checkpoint_unchanged_by_lens(native_fixture, tmp_path):
    kernel, groups, qid = fresh(native_fixture)
    before = kernel.fingerprint()
    before_snapshot = kernel.snapshot()
    p = tmp_path / "untouched.vdk"
    save_checkpoint(p, kernel.snapshot())
    saved = p.read_bytes()
    for other in ("novel", "type_negative", "direction_negative", "missing"):
        RelationAwareLens().inspect(kernel, groups["aa"], groups[other])
    assert kernel.fingerprint() == before
    assert kernel.snapshot() == before_snapshot
    assert p.read_bytes() == saved
    restored = VerdantKernel.from_state(load_checkpoint(p))
    assert restored.fingerprint() == before
    assert qid in restored.state.layered_structures


def test_native_q_heldout_work_and_ablation_same_organism(native_fixture):
    kernel, groups, qid = fresh(native_fixture)
    hierarchy = VerdantHierarchyPipeline()
    novel = groups["novel"]
    assert kernel.state.structures[novel].created_cycle > kernel.state.layered_structures[qid].created_cycle
    with_q = hierarchy.inspect_probe(kernel, novel)
    assert with_q.disposition.value == "use_layered_structure"
    assert with_q.layered_structure_id == qid
    assert with_q.cost.comparison_work < with_q.baseline_cost.comparison_work

    # Matched ablation on a COPY, not the test fixture/original study.
    control = VerdantKernel.from_state(kernel.snapshot())
    hierarchy.ablate(control, qid, "matched read-only research snapshot ablation")
    without_q = hierarchy.inspect_probe(control, novel)
    assert without_q.disposition.value == "fallback_member_scan"
    assert without_q.cost.comparison_work == with_q.baseline_cost.comparison_work

    # Native Q still uses topology alone, and can misclassify a typed-negative.
    negative = hierarchy.inspect_probe(kernel, groups["type_negative"])
    assert negative.disposition.value == "use_layered_structure"
    assert RelationAwareLens().inspect(kernel, groups["aa"], groups["type_negative"])["verdict"] == "reject"


def test_synthetic_matched_accuracy_is_reportable_not_semantic_truth(native_fixture):
    kernel, groups, _ = fresh(native_fixture)
    cases = [("bb", True), ("novel", True),
             ("type_negative", False), ("direction_negative", False)]
    lens = RelationAwareLens()
    baseline_predictions = []
    typed_predictions = []
    for name, label in cases:
        result = lens.inspect(kernel, groups["aa"], groups[name])
        assert result["verdict"] != "abstain"
        baseline_predictions.append(result["baseline_accept"] == label)
        typed_predictions.append((result["verdict"] == "accept") == label)
    assert sum(baseline_predictions) == 2
    assert sum(typed_predictions) == 4



def test_readonly_checkpoint_audit_respects_original_vdk_bytes(native_fixture, tmp_path):
    from verdant_integrated.structural_lens_audit import audit_checkpoint
    kernel, groups, qid = fresh(native_fixture)
    p = tmp_path / "heldout.vdk"
    save_checkpoint(p, kernel.snapshot())
    original = p.read_bytes()
    original_fingerprint = kernel.fingerprint()

    report = audit_checkpoint(p, max_pairs=8)
    assert report["native_p"] == len(groups)
    assert report["native_q"] == 1
    assert report["pair_counts"]["total_pairs"] == 8
    assert report["pair_counts"]["native_topology_accept"] >= 1
    assert report["audit_only"] is True
    assert report["promotion_or_native_hierarchy_mutation"] is False
    assert p.read_bytes() == original
    assert report["canonical_fingerprint"] == original_fingerprint
    assert any(
        item["earlier_q_available"] >= 1
        for item in report["native_retrospective_q_work"]
    )

    with pytest.raises(ValueError):
        audit_checkpoint(p, max_pairs=300)
