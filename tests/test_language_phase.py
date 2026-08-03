from __future__ import annotations

from pathlib import Path

from verdant_kernel import VerdantKernel, load_checkpoint, save_checkpoint
from verdant_language import (
    GrammarRuleId,
    LexemeSpec,
    LexicalCategory,
    VerdantLanguagePipeline,
)


def concept_id(kernel: VerdantKernel, label: str) -> str:
    for identifier, concept in kernel.state.concepts.items():
        if concept.label == label:
            return identifier
    raise AssertionError(f"Missing concept {label!r}")


def relations_of_type(kernel: VerdantKernel, relation_type: str):
    return [
        relation
        for relation in kernel.state.relations.values()
        if relation.relation_type == relation_type
    ]


def teach_minimal_language(kernel: VerdantKernel) -> VerdantLanguagePipeline:
    pipeline = VerdantLanguagePipeline()
    for rule in GrammarRuleId:
        pipeline.teach_rule(kernel, rule)
    pipeline.teach_foundational_lexicon(kernel)
    return pipeline


def test_sentence_without_taught_rule_preserves_evidence_but_does_not_promote() -> None:
    kernel = VerdantKernel(seed=201, state_dim=32, run_label="no-rule")
    pipeline = VerdantLanguagePipeline()

    learned = pipeline.learn_sentence(
        kernel,
        "A pushes B.",
        event_key="unscaffolded-1",
    )

    assert not learned.analysis.parsed
    assert learned.kernel_result.concept_ids == ()
    assert learned.kernel_result.relation_ids == ()
    assert len(kernel.state.evidence) == 3
    assert len(kernel.state.field.history) == 1


def test_transitive_rule_preserves_agent_patient_direction() -> None:
    kernel = VerdantKernel(seed=202, state_dim=48, run_label="roles")
    pipeline = teach_minimal_language(kernel)

    first = pipeline.learn_sentence(kernel, "A pushes B.", event_key="push-ab")
    second = pipeline.learn_sentence(kernel, "B pushes A.", event_key="push-ba")

    assert first.analysis.parsed and second.analysis.parsed
    assert first.analysis.frame is not None
    assert second.analysis.frame is not None
    assert first.analysis.frame.subject == "a"
    assert first.analysis.frame.object == "b"
    assert second.analysis.frame.subject == "b"
    assert second.analysis.frame.object == "a"

    a_id = concept_id(kernel, "lexeme:a")
    b_id = concept_id(kernel, "lexeme:b")
    action_edges = relations_of_type(kernel, "action:push")
    assert {(edge.source_concept_id, edge.target_concept_id) for edge in action_edges} == {
        (a_id, b_id),
        (b_id, a_id),
    }


def test_negation_creates_distinct_claim_without_overwriting_affirmation() -> None:
    kernel = VerdantKernel(seed=203, state_dim=48, run_label="negation")
    pipeline = teach_minimal_language(kernel)

    positive = pipeline.learn_sentence(
        kernel,
        "The door is open.",
        event_key="door-open-positive",
    )
    negative = pipeline.learn_sentence(
        kernel,
        "The door is not open.",
        event_key="door-open-negative",
    )

    assert positive.analysis.frame is not None
    assert negative.analysis.frame is not None
    assert positive.analysis.frame.polarity.value == "affirmed"
    assert negative.analysis.frame.polarity.value == "negated"
    assert len(relations_of_type(kernel, "has_property")) == 1
    assert len(relations_of_type(kernel, "does_not_have_property")) == 1
    assert concept_id(kernel, "statement:door-open-positive")
    assert concept_id(kernel, "statement:door-open-negative")


def test_temporal_before_preserves_order_in_both_directions() -> None:
    kernel = VerdantKernel(seed=204, state_dim=48, run_label="temporal")
    pipeline = teach_minimal_language(kernel)

    pipeline.learn_sentence(
        kernel,
        "The sound occurred before the light.",
        event_key="sound-before-light",
    )
    pipeline.learn_sentence(
        kernel,
        "The light occurred before the sound.",
        event_key="light-before-sound",
    )

    sound_id = concept_id(kernel, "event:sound:occurrence")
    light_id = concept_id(kernel, "event:light:occurrence")
    before_edges = relations_of_type(kernel, "before")
    assert {(edge.source_concept_id, edge.target_concept_id) for edge in before_edges} == {
        (sound_id, light_id),
        (light_id, sound_id),
    }


def test_surface_variation_reuses_same_semantic_relation_and_adds_evidence() -> None:
    kernel = VerdantKernel(seed=205, state_dim=48, run_label="paraphrase")
    pipeline = teach_minimal_language(kernel)

    pipeline.learn_sentence(
        kernel,
        "The dog pushes the child.",
        event_key="dog-push-1",
    )
    pipeline.learn_sentence(
        kernel,
        "Dog pushed child.",
        event_key="dog-push-2",
    )

    action_edges = relations_of_type(kernel, "action:push")
    dog_id = concept_id(kernel, "lexeme:dog")
    child_id = concept_id(kernel, "lexeme:child")
    matching = [
        edge
        for edge in action_edges
        if edge.source_concept_id == dog_id and edge.target_concept_id == child_id
    ]
    assert len(matching) == 1
    assert len(matching[0].evidence_refs) == 6



def test_malformed_role_order_is_rejected_instead_of_force_parsed() -> None:
    kernel = VerdantKernel(seed=207, state_dim=48, run_label="reject")
    pipeline = teach_minimal_language(kernel)
    before_concepts = len(kernel.state.concepts)
    before_relations = len(kernel.state.relations)

    learned = pipeline.learn_sentence(
        kernel,
        "B A pushes.",
        event_key="malformed-order",
    )

    assert not learned.analysis.parsed
    assert learned.kernel_result.concept_ids == ()
    assert learned.kernel_result.relation_ids == ()
    assert len(kernel.state.concepts) == before_concepts
    assert len(kernel.state.relations) == before_relations


def test_language_checkpoint_round_trip_preserves_rules_lexicon_and_claims(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=208, state_dim=48, run_label="language-checkpoint")
    pipeline = teach_minimal_language(kernel)
    pipeline.learn_sentence(kernel, "A pushes B.", event_key="checkpoint-language")
    path = tmp_path / "language.vdk"

    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))

    assert restored.snapshot() == kernel.snapshot()
    assert restored.fingerprint() == kernel.fingerprint()
    assert len(restored.state.field.history) == kernel.state.cycle
    assert len(restored.state.concepts) == len(kernel.state.concepts)
    assert len(restored.state.relations) == len(kernel.state.relations)


def test_full_language_sequence_is_deterministic_across_fresh_chunk_ids() -> None:
    def build() -> VerdantKernel:
        kernel = VerdantKernel(seed=209, state_dim=40, run_label="language-replay")
        pipeline = VerdantLanguagePipeline()
        pipeline.teach_rule(kernel, GrammarRuleId.TRANSITIVE_SVO)
        for spec in (
            LexemeSpec(lemma="the", category=LexicalCategory.DETERMINER, forms=("the",)),
            LexemeSpec(lemma="dog", category=LexicalCategory.NOUN, forms=("dog",)),
            LexemeSpec(lemma="child", category=LexicalCategory.NOUN, forms=("child",)),
            LexemeSpec(lemma="push", category=LexicalCategory.VERB, forms=("push", "pushes", "pushed")),
        ):
            pipeline.teach_lexeme(kernel, spec)
        pipeline.learn_sentence(
            kernel,
            "The dog pushes the child.",
            event_key="deterministic-language",
        )
        return kernel

    left = build()
    right = build()
    assert left.snapshot() == right.snapshot()
    assert left.fingerprint() == right.fingerprint()
