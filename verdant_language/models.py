from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FrozenRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class LexicalCategory(str, Enum):
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    DETERMINER = "determiner"
    COPULA = "copula"
    NEGATOR = "negator"
    TEMPORAL_MARKER = "temporal_marker"


class GrammarRuleId(str, Enum):
    TRANSITIVE_SVO = "transitive_svo"
    COPULAR_PROPERTY = "copular_property"
    TEMPORAL_BEFORE = "temporal_before"


class FrameType(str, Enum):
    TRANSITIVE = "transitive"
    PROPERTY = "property"
    TEMPORAL = "temporal"


class Polarity(str, Enum):
    AFFIRMED = "affirmed"
    NEGATED = "negated"


class LexemeSpec(FrozenRecord):
    lemma: str
    category: LexicalCategory
    forms: tuple[str, ...] = Field(min_length=1)
    attributes: dict[str, Any] = Field(default_factory=dict)


class GrammarRuleSpec(FrozenRecord):
    rule_id: GrammarRuleId
    pattern: str
    description: str
    curriculum_text: str
    roles: tuple[str, ...]


class TokenRecord(FrozenRecord):
    surface: str
    normalized: str
    index: int = Field(ge=0)
    lemma: str | None = None
    category: LexicalCategory | None = None


class ClauseFrame(FrozenRecord):
    frame_type: FrameType
    rule_id: GrammarRuleId
    sentence: str
    tokens: tuple[TokenRecord, ...]
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    property: str | None = None
    first_event: str | None = None
    second_event: str | None = None
    polarity: Polarity = Polarity.AFFIRMED
    confidence: float = Field(ge=0.0, le=1.0)


class LanguageAnalysis(FrozenRecord):
    sentence: str
    parsed: bool
    enabled_rules: tuple[GrammarRuleId, ...]
    frame: ClauseFrame | None = None
    rejection_reason: str | None = None


GRAMMAR_RULES: dict[GrammarRuleId, GrammarRuleSpec] = {
    GrammarRuleId.TRANSITIVE_SVO: GrammarRuleSpec(
        rule_id=GrammarRuleId.TRANSITIVE_SVO,
        pattern="SUBJECT VERB OBJECT",
        description=(
            "A transitive declarative clause places the acting participant before "
            "the action and the affected participant after it."
        ),
        curriculum_text=(
            "Grammar rule: a transitive declarative clause follows SUBJECT VERB "
            "OBJECT. The subject carries the agent role, the verb carries the "
            "predicate role, and the object carries the patient role."
        ),
        roles=("agent", "predicate", "patient"),
    ),
    GrammarRuleId.COPULAR_PROPERTY: GrammarRuleSpec(
        rule_id=GrammarRuleId.COPULAR_PROPERTY,
        pattern="SUBJECT COPULA [NEGATOR] PROPERTY",
        description=(
            "A copular property clause links a subject to a property and preserves "
            "whether the claim is affirmed or negated."
        ),
        curriculum_text=(
            "Grammar rule: a property clause follows SUBJECT COPULA PROPERTY, and "
            "a negator after the copula reverses the polarity of the claim."
        ),
        roles=("subject", "property", "polarity"),
    ),
    GrammarRuleId.TEMPORAL_BEFORE: GrammarRuleSpec(
        rule_id=GrammarRuleId.TEMPORAL_BEFORE,
        pattern="EVENT [EVENT-VERB] BEFORE EVENT",
        description=(
            "A temporal-before clause places one event earlier than another and "
            "preserves direction."
        ),
        curriculum_text=(
            "Grammar rule: when one event is stated before another with the word "
            "before, the first event is earlier and the second event is later."
        ),
        roles=("first_event", "second_event", "before"),
    ),
}
