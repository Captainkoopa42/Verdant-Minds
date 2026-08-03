from __future__ import annotations

import re
from dataclasses import dataclass

from verdant_kernel import (
    ClaimPolarity,
    ClaimProposal,
    ClaimSourceClass,
    ConceptProposal,
    RelationProposal,
    VerdantKernel,
)
from verdant_kernel.models import normalize_label, stable_id

from .models import (
    ClauseFrame,
    FrameType,
    GRAMMAR_RULES,
    GrammarRuleId,
    LanguageAnalysis,
    LexicalCategory,
    Polarity,
    TokenRecord,
)


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*|[.!?,;:]")
_PUNCTUATION = {".", "!", "?", ",", ";", ":"}


@dataclass(frozen=True)
class SemanticPlan:
    analysis: LanguageAnalysis
    concept_proposals: tuple[ConceptProposal, ...]
    relation_proposals: tuple[RelationProposal, ...]
    claim_proposals: tuple[ClaimProposal, ...] = ()


class ControlledGrammarAnalyzer:
    """
    Deterministic, evidence-gated grammar scaffold.

    The parser contains no pretrained language model and no statistical NLP model.
    A rule is usable only after an evidence-backed grammar-rule concept exists in
    the canonical Verdant kernel. Lexical categories likewise come from concepts
    explicitly taught through the handwritten curriculum.

    This milestone tests whether learned rules preserve relational distinctions.
    It does not claim autonomous grammar induction or unrestricted English parsing.
    """

    def enabled_rules(self, kernel: VerdantKernel) -> tuple[GrammarRuleId, ...]:
        enabled: list[GrammarRuleId] = []
        for concept in kernel.state.concepts.values():
            if concept.attributes.get("kind") != "grammar_rule":
                continue
            rule_value = concept.attributes.get("rule_id")
            try:
                enabled.append(GrammarRuleId(str(rule_value)))
            except ValueError:
                continue
        return tuple(sorted(set(enabled), key=lambda item: item.value))

    def lexicon(self, kernel: VerdantKernel) -> dict[str, tuple[str, LexicalCategory]]:
        forms: dict[str, tuple[str, LexicalCategory]] = {}
        for concept in kernel.state.concepts.values():
            if concept.attributes.get("kind") != "lexeme":
                continue
            lemma = str(concept.attributes.get("lemma", "")).strip().lower()
            category_value = concept.attributes.get("category")
            if not lemma:
                continue
            try:
                category = LexicalCategory(str(category_value))
            except ValueError:
                continue
            learned_forms = concept.attributes.get("forms", [lemma])
            for form in learned_forms:
                normalized = str(form).strip().lower()
                if normalized:
                    forms[normalized] = (lemma, category)
        return forms

    def tokenize(
        self,
        sentence: str,
        kernel: VerdantKernel,
    ) -> tuple[TokenRecord, ...]:
        lexicon = self.lexicon(kernel)
        records: list[TokenRecord] = []
        for index, surface in enumerate(_WORD_RE.findall(sentence)):
            normalized = surface.lower()
            lemma: str | None = None
            category: LexicalCategory | None = None
            if normalized not in _PUNCTUATION and normalized in lexicon:
                lemma, category = lexicon[normalized]
            records.append(
                TokenRecord(
                    surface=surface,
                    normalized=normalized,
                    index=index,
                    lemma=lemma,
                    category=category,
                )
            )
        return tuple(records)

    def analyze(self, sentence: str, kernel: VerdantKernel) -> LanguageAnalysis:
        enabled = self.enabled_rules(kernel)
        tokens = tuple(
            token for token in self.tokenize(sentence, kernel)
            if token.normalized not in _PUNCTUATION
        )
        if not tokens:
            return LanguageAnalysis(
                sentence=sentence,
                parsed=False,
                enabled_rules=enabled,
                rejection_reason="no lexical tokens",
            )

        if GrammarRuleId.TEMPORAL_BEFORE in enabled:
            frame = self._parse_temporal(sentence, tokens)
            if frame is not None:
                return LanguageAnalysis(
                    sentence=sentence,
                    parsed=True,
                    enabled_rules=enabled,
                    frame=frame,
                )
        if GrammarRuleId.COPULAR_PROPERTY in enabled:
            frame = self._parse_copular(sentence, tokens)
            if frame is not None:
                return LanguageAnalysis(
                    sentence=sentence,
                    parsed=True,
                    enabled_rules=enabled,
                    frame=frame,
                )
        if GrammarRuleId.TRANSITIVE_SVO in enabled:
            frame = self._parse_transitive(sentence, tokens)
            if frame is not None:
                return LanguageAnalysis(
                    sentence=sentence,
                    parsed=True,
                    enabled_rules=enabled,
                    frame=frame,
                )

        return LanguageAnalysis(
            sentence=sentence,
            parsed=False,
            enabled_rules=enabled,
            rejection_reason=(
                "no enabled rule matched the learned lexical categories and word order"
            ),
        )

    def plan(
        self,
        sentence: str,
        event_key: str,
        kernel: VerdantKernel,
    ) -> SemanticPlan:
        analysis = self.analyze(sentence, kernel)
        if not analysis.parsed or analysis.frame is None:
            return SemanticPlan(analysis, (), (), ())
        frame = analysis.frame
        statement_label = f"statement:{event_key}"
        rule_label = f"grammar_rule:{frame.rule_id.value}"
        concepts: dict[str, ConceptProposal] = {}
        relations: list[RelationProposal] = []
        claims: list[ClaimProposal] = []

        def add_concept(label: str, **attributes: object) -> str:
            concepts[label] = ConceptProposal(label=label, attributes=attributes)
            return label

        statement = add_concept(
            statement_label,
            kind="statement",
            frame_type=frame.frame_type.value,
            rule_id=frame.rule_id.value,
            polarity=frame.polarity.value,
            sentence=sentence,
        )
        add_concept(
            rule_label,
            kind="grammar_rule",
            rule_id=frame.rule_id.value,
            pattern=GRAMMAR_RULES[frame.rule_id].pattern,
        )
        relations.append(
            RelationProposal(
                source_label=statement,
                target_label=rule_label,
                relation_type="parsed_by",
                confidence=frame.confidence,
                weight=0.75,
            )
        )

        polarity_label = add_concept(
            f"polarity:{frame.polarity.value}",
            kind="polarity",
            value=frame.polarity.value,
        )
        relations.append(
            RelationProposal(
                source_label=statement,
                target_label=polarity_label,
                relation_type="polarity",
                confidence=frame.confidence,
                weight=0.8,
            )
        )

        if frame.frame_type == FrameType.TRANSITIVE:
            assert frame.subject and frame.predicate and frame.object
            subject = self._lexeme_label(frame.subject)
            predicate = self._lexeme_label(frame.predicate)
            object_label = self._lexeme_label(frame.object)
            add_concept(subject, kind="lexeme", lemma=frame.subject)
            add_concept(predicate, kind="lexeme", lemma=frame.predicate)
            add_concept(object_label, kind="lexeme", lemma=frame.object)
            relations.extend(
                [
                    self._relation(statement, subject, "agent", frame.confidence),
                    self._relation(statement, predicate, "predicate", frame.confidence),
                    self._relation(statement, object_label, "patient", frame.confidence),
                    self._relation(
                        subject,
                        object_label,
                        f"action:{normalize_label(frame.predicate)}",
                        frame.confidence,
                    ),
                ]
            )
            claims.append(
                ClaimProposal(
                    subject_label=subject,
                    predicate=f"action:{normalize_label(frame.predicate)}",
                    object_label=object_label,
                    polarity=ClaimPolarity.AFFIRMED,
                    source_class=ClaimSourceClass.HUMAN_TESTIMONY,
                    confidence=frame.confidence,
                    rationale="Handwritten teacher statement parsed by taught transitive grammar.",
                    attributes={"frame_type": frame.frame_type.value},
                )
            )

        elif frame.frame_type == FrameType.PROPERTY:
            assert frame.subject and frame.property
            subject = self._lexeme_label(frame.subject)
            property_label = self._lexeme_label(frame.property)
            add_concept(subject, kind="lexeme", lemma=frame.subject)
            add_concept(property_label, kind="lexeme", lemma=frame.property)
            relations.extend(
                [
                    self._relation(statement, subject, "subject", frame.confidence),
                    self._relation(statement, property_label, "property", frame.confidence),
                    self._relation(
                        subject,
                        property_label,
                        (
                            "has_property"
                            if frame.polarity == Polarity.AFFIRMED
                            else "does_not_have_property"
                        ),
                        frame.confidence,
                    ),
                ]
            )
            claims.append(
                ClaimProposal(
                    subject_label=subject,
                    predicate="has_property",
                    object_label=property_label,
                    polarity=(
                        ClaimPolarity.AFFIRMED
                        if frame.polarity == Polarity.AFFIRMED
                        else ClaimPolarity.NEGATED
                    ),
                    source_class=ClaimSourceClass.HUMAN_TESTIMONY,
                    confidence=frame.confidence,
                    rationale="Handwritten teacher property statement parsed by taught grammar.",
                    attributes={"frame_type": frame.frame_type.value},
                )
            )

        elif frame.frame_type == FrameType.TEMPORAL:
            assert frame.first_event and frame.second_event
            first = add_concept(
                f"event:{frame.first_event}:occurrence",
                kind="event_candidate",
                head=frame.first_event,
            )
            second = add_concept(
                f"event:{frame.second_event}:occurrence",
                kind="event_candidate",
                head=frame.second_event,
            )
            relations.extend(
                [
                    self._relation(statement, first, "first_event", frame.confidence),
                    self._relation(statement, second, "second_event", frame.confidence),
                    self._relation(first, second, "before", frame.confidence),
                ]
            )
            claims.append(
                ClaimProposal(
                    subject_label=first,
                    predicate="before",
                    object_label=second,
                    polarity=ClaimPolarity.AFFIRMED,
                    source_class=ClaimSourceClass.HUMAN_TESTIMONY,
                    confidence=frame.confidence,
                    rationale="Handwritten temporal statement parsed by taught grammar.",
                    attributes={"frame_type": frame.frame_type.value},
                )
            )

        return SemanticPlan(
            analysis=analysis,
            concept_proposals=tuple(
                concepts[key] for key in sorted(concepts)
            ),
            relation_proposals=tuple(relations),
            claim_proposals=tuple(claims),
        )

    @staticmethod
    def _relation(
        source: str,
        target: str,
        relation_type: str,
        confidence: float,
    ) -> RelationProposal:
        return RelationProposal(
            source_label=source,
            target_label=target,
            relation_type=relation_type,
            confidence=confidence,
            weight=0.7,
        )

    @staticmethod
    def _lexeme_label(lemma: str) -> str:
        return f"lexeme:{normalize_label(lemma)}"

    @staticmethod
    def _content_tokens(tokens: tuple[TokenRecord, ...]) -> tuple[TokenRecord, ...]:
        return tuple(
            token for token in tokens
            if token.category != LexicalCategory.DETERMINER
        )

    def _parse_transitive(
        self,
        sentence: str,
        tokens: tuple[TokenRecord, ...],
    ) -> ClauseFrame | None:
        content = self._content_tokens(tokens)
        verbs = [
            (index, token)
            for index, token in enumerate(content)
            if token.category == LexicalCategory.VERB
        ]
        if len(verbs) != 1:
            return None
        verb_index, verb = verbs[0]
        if verb_index != 1 or len(content) != 3:
            return None
        subject, _, object_token = content
        if subject.category != LexicalCategory.NOUN:
            return None
        if object_token.category != LexicalCategory.NOUN:
            return None
        return ClauseFrame(
            frame_type=FrameType.TRANSITIVE,
            rule_id=GrammarRuleId.TRANSITIVE_SVO,
            sentence=sentence,
            tokens=tokens,
            subject=subject.lemma,
            predicate=verb.lemma,
            object=object_token.lemma,
            confidence=0.92,
        )

    def _parse_copular(
        self,
        sentence: str,
        tokens: tuple[TokenRecord, ...],
    ) -> ClauseFrame | None:
        content = self._content_tokens(tokens)
        copulas = [
            index for index, token in enumerate(content)
            if token.category == LexicalCategory.COPULA
        ]
        if copulas != [1]:
            return None
        if len(content) not in {3, 4}:
            return None
        subject = content[0]
        if subject.category != LexicalCategory.NOUN:
            return None
        property_index = 2
        polarity = Polarity.AFFIRMED
        if len(content) == 4:
            if content[2].category != LexicalCategory.NEGATOR:
                return None
            property_index = 3
            polarity = Polarity.NEGATED
        property_token = content[property_index]
        if property_token.category not in {
            LexicalCategory.ADJECTIVE,
            LexicalCategory.NOUN,
        }:
            return None
        return ClauseFrame(
            frame_type=FrameType.PROPERTY,
            rule_id=GrammarRuleId.COPULAR_PROPERTY,
            sentence=sentence,
            tokens=tokens,
            subject=subject.lemma,
            property=property_token.lemma,
            polarity=polarity,
            confidence=0.95,
        )

    def _parse_temporal(
        self,
        sentence: str,
        tokens: tuple[TokenRecord, ...],
    ) -> ClauseFrame | None:
        content = self._content_tokens(tokens)
        markers = [
            index for index, token in enumerate(content)
            if token.category == LexicalCategory.TEMPORAL_MARKER
            and token.lemma == "before"
        ]
        if len(markers) != 1:
            return None
        marker_index = markers[0]
        left = content[:marker_index]
        right = content[marker_index + 1:]
        first = self._event_head(left)
        second = self._event_head(right)
        if first is None or second is None:
            return None
        return ClauseFrame(
            frame_type=FrameType.TEMPORAL,
            rule_id=GrammarRuleId.TEMPORAL_BEFORE,
            sentence=sentence,
            tokens=tokens,
            first_event=first,
            second_event=second,
            confidence=0.93,
        )

    @staticmethod
    def _event_head(tokens: tuple[TokenRecord, ...]) -> str | None:
        nouns = [token for token in tokens if token.category == LexicalCategory.NOUN]
        if len(nouns) != 1:
            return None
        other = [
            token for token in tokens
            if token.category not in {LexicalCategory.NOUN, LexicalCategory.VERB}
        ]
        if other:
            return None
        return nouns[0].lemma
