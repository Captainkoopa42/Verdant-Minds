from __future__ import annotations

from dataclasses import dataclass

from cognitive_chunk_v2.archive import ResourceStore
from cognitive_chunk_v2.models import CognitiveChunkV2
from cognitive_chunk_v2.pipeline import ExperienceInput, PipelineOrchestrator
from verdant_kernel import (
    ConceptProposal,
    EvidenceKind,
    ExperienceCommand,
    ExperienceResult,
    RelationProposal,
    VerdantKernel,
)

from .grammar import ControlledGrammarAnalyzer, SemanticPlan
from .models import (
    GRAMMAR_RULES,
    GrammarRuleId,
    LanguageAnalysis,
    LexemeSpec,
    LexicalCategory,
)


@dataclass(frozen=True)
class LanguageLearningResult:
    kernel_result: ExperienceResult
    analysis: LanguageAnalysis
    chunk: CognitiveChunkV2
    store: ResourceStore


class VerdantLanguagePipeline:
    """Handwritten curriculum -> CognitiveChunk v2 -> grammar -> canonical kernel."""

    def __init__(
        self,
        *,
        orchestrator: PipelineOrchestrator | None = None,
        analyzer: ControlledGrammarAnalyzer | None = None,
    ) -> None:
        self.orchestrator = orchestrator or PipelineOrchestrator()
        self.analyzer = analyzer or ControlledGrammarAnalyzer()

    def teach_rule(
        self,
        kernel: VerdantKernel,
        rule_id: GrammarRuleId,
        *,
        event_key: str | None = None,
        source_ref: str = "handwritten_grammar_curriculum",
    ) -> LanguageLearningResult:
        spec = GRAMMAR_RULES[rule_id]
        key = event_key or f"grammar-rule:{rule_id.value}"
        chunk, store, payload, translation, source = self._text_chunk(
            spec.curriculum_text,
            source_ref=source_ref,
            source_name=f"{rule_id.value}.txt",
        )
        rule_label = f"grammar_rule:{rule_id.value}"
        concepts = [
            ConceptProposal(
                label=rule_label,
                attributes={
                    "kind": "grammar_rule",
                    "rule_id": rule_id.value,
                    "pattern": spec.pattern,
                    "description": spec.description,
                    "roles": list(spec.roles),
                    "status": "teacher_supplied_scaffold",
                },
            )
        ]
        relations: list[RelationProposal] = []
        for role in spec.roles:
            role_label = f"grammar_role:{role}"
            concepts.append(
                ConceptProposal(
                    label=role_label,
                    attributes={"kind": "grammar_role", "role": role},
                )
            )
            relations.append(
                RelationProposal(
                    source_label=rule_label,
                    target_label=role_label,
                    relation_type="uses_role",
                    confidence=1.0,
                    weight=0.9,
                )
            )
        command = ExperienceCommand(
            event_key=key,
            source_ref=source,
            modality="text",
            payload_sha256=payload.source_sha256,
            feature_vector=tuple(float(value) for value in store.get_array(translation.feature_ref).reshape(-1)),
            concept_proposals=tuple(concepts),
            relation_proposals=tuple(relations),
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            semantic_evidence_details={
                "source_type": "handwritten_teacher_rule",
                "rule_id": rule_id.value,
            },
            metadata={
                "event_type": "grammar_rule_curriculum",
                "rule_id": rule_id.value,
                "pattern": spec.pattern,
                "translator_id": translation.translator_id,
                "translator_version": translation.translator_version,
                "source_name": payload.source_name,
                "media_type": payload.media_type,
                "epistemic_status": "teacher_supplied_rule",
            },
        )
        result = kernel.apply_experience(command)
        analysis = LanguageAnalysis(
            sentence=spec.curriculum_text,
            parsed=False,
            enabled_rules=self.analyzer.enabled_rules(kernel),
            rejection_reason="curriculum rule registration; not a world statement",
        )
        return LanguageLearningResult(result, analysis, chunk, store)

    def teach_lexeme(
        self,
        kernel: VerdantKernel,
        spec: LexemeSpec,
        *,
        event_key: str | None = None,
        source_ref: str = "handwritten_lexicon_curriculum",
    ) -> LanguageLearningResult:
        key = event_key or f"lexeme:{spec.category.value}:{spec.lemma.lower()}"
        forms_text = ", ".join(spec.forms)
        curriculum_text = (
            f"Lexicon lesson: {spec.lemma} is taught as a {spec.category.value}. "
            f"Its recognized forms are {forms_text}."
        )
        chunk, store, payload, translation, source = self._text_chunk(
            curriculum_text,
            source_ref=source_ref,
            source_name=f"lexeme_{spec.lemma.lower()}.txt",
        )
        proposal = ConceptProposal(
            label=f"lexeme:{spec.lemma.lower()}",
            attributes={
                "kind": "lexeme",
                "lemma": spec.lemma.lower(),
                "category": spec.category.value,
                "forms": sorted({form.lower() for form in spec.forms}),
                "status": "teacher_supplied_lexicon",
                **spec.attributes,
            },
        )
        command = ExperienceCommand(
            event_key=key,
            source_ref=source,
            modality="text",
            payload_sha256=payload.source_sha256,
            feature_vector=tuple(float(value) for value in store.get_array(translation.feature_ref).reshape(-1)),
            concept_proposals=(proposal,),
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            semantic_evidence_details={
                "source_type": "handwritten_teacher_lexicon",
                "lemma": spec.lemma.lower(),
            },
            metadata={
                "event_type": "lexicon_curriculum",
                "lemma": spec.lemma.lower(),
                "category": spec.category.value,
                "forms": sorted({form.lower() for form in spec.forms}),
                "translator_id": translation.translator_id,
                "translator_version": translation.translator_version,
                "source_name": payload.source_name,
                "media_type": payload.media_type,
                "epistemic_status": "teacher_supplied_lexeme",
            },
        )
        result = kernel.apply_experience(command)
        analysis = LanguageAnalysis(
            sentence=curriculum_text,
            parsed=False,
            enabled_rules=self.analyzer.enabled_rules(kernel),
            rejection_reason="curriculum lexeme registration; not a world statement",
        )
        return LanguageLearningResult(result, analysis, chunk, store)

    def teach_foundational_lexicon(
        self,
        kernel: VerdantKernel,
    ) -> tuple[LanguageLearningResult, ...]:
        entries = (
            LexemeSpec(lemma="the", category=LexicalCategory.DETERMINER, forms=("the",)),
            LexemeSpec(lemma="a", category=LexicalCategory.NOUN, forms=("a",)),
            LexemeSpec(lemma="b", category=LexicalCategory.NOUN, forms=("b",)),
            LexemeSpec(lemma="dog", category=LexicalCategory.NOUN, forms=("dog",)),
            LexemeSpec(lemma="child", category=LexicalCategory.NOUN, forms=("child",)),
            LexemeSpec(lemma="door", category=LexicalCategory.NOUN, forms=("door",)),
            LexemeSpec(lemma="sound", category=LexicalCategory.NOUN, forms=("sound",)),
            LexemeSpec(lemma="light", category=LexicalCategory.NOUN, forms=("light",)),
            LexemeSpec(lemma="push", category=LexicalCategory.VERB, forms=("push", "pushes", "pushed")),
            LexemeSpec(lemma="chase", category=LexicalCategory.VERB, forms=("chase", "chases", "chased")),
            LexemeSpec(lemma="occur", category=LexicalCategory.VERB, forms=("occur", "occurs", "occurred")),
            LexemeSpec(lemma="be", category=LexicalCategory.COPULA, forms=("is", "was")),
            LexemeSpec(lemma="not", category=LexicalCategory.NEGATOR, forms=("not",)),
            LexemeSpec(lemma="open", category=LexicalCategory.ADJECTIVE, forms=("open",)),
            LexemeSpec(lemma="before", category=LexicalCategory.TEMPORAL_MARKER, forms=("before",)),
        )
        return tuple(self.teach_lexeme(kernel, entry) for entry in entries)

    def learn_sentence(
        self,
        kernel: VerdantKernel,
        sentence: str,
        *,
        event_key: str,
        source_ref: str = "handwritten_language_curriculum",
    ) -> LanguageLearningResult:
        chunk, store, payload, translation, source = self._text_chunk(
            sentence,
            source_ref=source_ref,
            source_name=f"{event_key}.txt",
        )
        plan: SemanticPlan = self.analyzer.plan(sentence, event_key, kernel)
        command = ExperienceCommand(
            event_key=event_key,
            source_ref=source,
            modality="text",
            payload_sha256=payload.source_sha256,
            feature_vector=tuple(float(value) for value in store.get_array(translation.feature_ref).reshape(-1)),
            concept_proposals=plan.concept_proposals,
            relation_proposals=plan.relation_proposals,
            claim_proposals=plan.claim_proposals,
            confidence=(plan.analysis.frame.confidence if plan.analysis.frame else 1.0),
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            semantic_evidence_details={
                "source_type": "handwritten_teacher_statement",
                "parsed": plan.analysis.parsed,
            },
            metadata={
                "event_type": "handwritten_language_experience",
                "sentence": sentence,
                "parsed": plan.analysis.parsed,
                "rule_id": (
                    plan.analysis.frame.rule_id.value
                    if plan.analysis.frame is not None
                    else None
                ),
                "rejection_reason": plan.analysis.rejection_reason,
                "translator_id": translation.translator_id,
                "translator_version": translation.translator_version,
                "source_name": payload.source_name,
                "media_type": payload.media_type,
                "semantic_promotion_policy": "grammar_rule_and_lexicon_evidence_required",
            },
        )
        result = kernel.apply_experience(command)
        return LanguageLearningResult(result, plan.analysis, chunk, store)

    def _text_chunk(
        self,
        text: str,
        *,
        source_ref: str,
        source_name: str,
    ) -> tuple[CognitiveChunkV2, ResourceStore, object, object, str]:
        chunk, store = self.orchestrator.process(
            ExperienceInput.from_text(
                text,
                source_id=source_ref,
                source_name=source_name,
            )
        )
        if len(chunk.payloads) != 1 or len(chunk.translations) != 1:
            raise ValueError("Text language pipeline expects one payload and one translation.")
        payload = chunk.payloads[0]
        translation = chunk.translations[0]
        observation = next(
            (item for item in chunk.observations if item.payload_id == payload.payload_id),
            None,
        )
        source = observation.source_id if observation is not None else source_ref
        return chunk, store, payload, translation, source
