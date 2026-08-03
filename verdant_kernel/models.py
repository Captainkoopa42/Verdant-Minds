from __future__ import annotations

import hashlib
import json
import math
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_ID_SAFE = re.compile(r"[^a-z0-9]+")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    digest = hashlib.sha256(canonical_json_bytes(parts)).hexdigest()[:length]
    return f"{prefix}_{digest}"


def normalize_label(label: str) -> str:
    normalized = _ID_SAFE.sub("_", label.strip().lower()).strip("_")
    if not normalized:
        raise ValueError("Concept labels must contain at least one letter or number.")
    return normalized


class FrozenRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceKind(str, Enum):
    OBSERVATION = "observation"
    TRANSLATION = "translation"
    TESTIMONY = "testimony"
    ACTION = "action"
    OUTCOME = "outcome"
    REVISION = "revision"
    SYSTEM = "system"


class RelationStatus(str, Enum):
    HYPOTHESIS = "hypothesis"
    SUPPORTED = "supported"
    CONFIRMED = "confirmed"
    CONTRADICTED = "contradicted"
    REJECTED = "rejected"


class ClaimPolarity(str, Enum):
    AFFIRMED = "affirmed"
    NEGATED = "negated"


class ClaimSourceClass(str, Enum):
    DIRECT_OBSERVATION = "direct_observation"
    PHYSICAL_OUTCOME = "physical_outcome"
    SELF_ACTION = "self_action"
    HUMAN_TESTIMONY = "human_testimony"
    EXTERNAL_TESTIMONY = "external_testimony"
    SYSTEM_INFERENCE = "system_inference"
    TRANSLATION = "translation"


class EvidenceStance(str, Enum):
    SUPPORT = "support"
    REFUTE = "refute"


class ClaimStatus(str, Enum):
    HYPOTHESIS = "hypothesis"
    SUPPORTED = "supported"
    CONFIRMED = "confirmed"
    CONTESTED = "contested"
    REVISED = "revised"
    REJECTED = "rejected"


class ContradictionStatus(str, Enum):
    ACTIVE = "active"
    WEIGHTED = "weighted"


class GovernanceProposalKind(str, Enum):
    INVESTIGATE = "investigate"
    ATTEND = "attend"
    ACT = "act"
    STRUCTURAL_PROMOTION = "structural_promotion"


class KingName(str, Enum):
    DATA = "DataKing"
    FOREFRONT = "ForefrontKing"
    ETHICS = "EthicsKing"


class KingRecommendation(str, Enum):
    SUPPORT = "support"
    OPPOSE = "oppose"
    REQUEST_EVIDENCE = "request_evidence"
    PRIORITIZE = "prioritize"
    DEPRIORITIZE = "deprioritize"
    PERMIT = "permit"
    CONSTRAIN = "constrain"
    DENY = "deny"
    NEUTRAL = "neutral"


class CouncilDisposition(str, Enum):
    APPROVE = "approve"
    APPROVE_WITH_CONSTRAINTS = "approve_with_constraints"
    DEFER = "defer"
    DENY = "deny"


class ShardStatus(str, Enum):
    ROOT = "root"
    ACTIVE = "active"
    DORMANT = "dormant"


class BridgeStatus(str, Enum):
    TRAVERSED = "traversed"


class RoutingDisposition(str, Enum):
    ROUTE = "route"
    STAY = "stay"
    REJECT = "reject"


class ObjectObservationKind(str, Enum):
    VISIBLE = "visible"
    OCCLUSION = "occlusion"


class ObjectCandidateStatus(str, Enum):
    TRACKING = "tracking"
    OCCLUDED = "occluded"
    CONTESTED = "contested"
    ELIGIBLE = "eligible"
    PROMOTED = "promoted"
    REJECTED = "rejected"


class ObjectAssociationDisposition(str, Enum):
    CREATE = "create"
    ASSOCIATE = "associate"
    UPDATE_TARGET = "update_target"
    REJECT = "reject"


class ObjectPromotionDisposition(str, Enum):
    PROMOTE = "promote"
    DEFER = "defer"
    REJECT = "reject"



class PlasticityUpdateKind(str, Enum):
    CREATE = "create"
    REINFORCE = "reinforce"
    DECAY = "decay"
    NORMALIZE = "normalize"
    PRUNE = "prune"


class StructureCandidateStatus(str, Enum):
    TRACKING = "tracking"
    ELIGIBLE = "eligible"
    PROMOTED = "promoted"
    REJECTED = "rejected"


class StructurePromotionDisposition(str, Enum):
    PROMOTE = "promote"
    DEFER = "defer"
    REJECT = "reject"


class WorkspaceSourceKind(str, Enum):
    CURRENT_EVIDENCE = "current_evidence"
    TEMPORAL_EVENT = "temporal_event"
    RECALLED_EVIDENCE = "recalled_evidence"
    LOCAL_ASSOCIATION = "local_association"
    RESONANCE = "resonance"
    EARNED_STRUCTURE = "earned_structure"
    CONTRADICTION = "contradiction"
    PROTO_OBJECT = "proto_object"
    SHARD_CONTEXT = "shard_context"
    GOVERNANCE_CONSTRAINT = "governance_constraint"
    AUTHORIZED_ACTION = "authorized_action"




class CompilationDisposition(str, Enum):
    USE_STRUCTURE = "use_structure"
    FALLBACK_LOW_LEVEL = "fallback_low_level"


class StructureAvailabilityAction(str, Enum):
    ABLATE = "ablate"
    RESTORE = "restore"


class StructureInteractionDisposition(str, Enum):
    VERIFIED_ALIGNMENT = "verified_alignment"
    FIELD_ONLY = "field_only"
    REJECT = "reject"


class HierarchyCandidateStatus(str, Enum):
    TRACKING = "tracking"
    ELIGIBLE = "eligible"
    PROMOTED = "promoted"
    REJECTED = "rejected"


class HierarchyPromotionDisposition(str, Enum):
    PROMOTE = "promote"
    DEFER = "defer"
    REJECT = "reject"


class LayeredProbeDisposition(str, Enum):
    USE_LAYERED_STRUCTURE = "use_layered_structure"
    FALLBACK_MEMBER_SCAN = "fallback_member_scan"


class RefoldDisposition(str, Enum):
    STABLE = "stable"
    REVISE = "revise"
    SPLIT = "split"
    UNRESOLVED = "unresolved"


class WorkspaceDisposition(str, Enum):
    ADMIT = "admit"
    SUPPRESS = "suppress"
    REJECT = "reject"


class WorkspaceWritebackDisposition(str, Enum):
    RESOLVE = "resolve"
    MAINTAIN = "maintain"


class NativeModality(str, Enum):
    VISION = "vision"
    AUDIO = "audio"


class TemporalBoundaryReason(str, Enum):
    STREAM_START = "stream_start"
    TIME_GAP = "time_gap"
    FEATURE_CHANGE = "feature_change"
    SAMPLE_LIMIT = "sample_limit"
    STREAM_END = "stream_end"


class KernelIdentity(FrozenRecord):
    kernel_id: str
    schema_version: str = "1.0.0-alpha"
    run_label: str = "independent-rebuild"


class EvidenceRecord(FrozenRecord):
    evidence_id: str
    kind: EvidenceKind
    source_ref: str
    event_key: str
    cycle: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    payload_sha256: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ConceptRecord(FrozenRecord):
    concept_id: str
    label: str
    normalized_label: str
    created_cycle: int = Field(ge=0)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    attributes: dict[str, Any] = Field(default_factory=dict)


class RelationRecord(FrozenRecord):
    relation_id: str
    source_concept_id: str
    target_concept_id: str
    relation_type: str
    directed: bool = True
    weight: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    created_cycle: int = Field(ge=0)
    updated_cycle: int = Field(ge=0)
    status: RelationStatus = RelationStatus.SUPPORTED


class ClaimEvidenceEntry(FrozenRecord):
    evidence_id: str
    source_class: ClaimSourceClass
    stance: EvidenceStance
    confidence: float = Field(ge=0.0, le=1.0)
    source_weight: float = Field(ge=0.0, le=1.0)
    effective_weight: float = Field(ge=0.0, le=1.0)
    cycle: int = Field(ge=0)
    rationale: str = ""


class ClaimRecord(FrozenRecord):
    claim_id: str
    claim_key: str
    subject_concept_id: str
    predicate: str
    object_concept_id: str
    polarity: ClaimPolarity
    created_cycle: int = Field(ge=0)
    updated_cycle: int = Field(ge=0)
    support_ledger: tuple[ClaimEvidenceEntry, ...] = Field(default_factory=tuple)
    refutation_ledger: tuple[ClaimEvidenceEntry, ...] = Field(default_factory=tuple)
    support_score: float = Field(default=0.0, ge=0.0, le=1.0)
    refutation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    net_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    status: ClaimStatus = ClaimStatus.HYPOTHESIS
    superseded_by_claim_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class ContradictionRecord(FrozenRecord):
    contradiction_id: str
    claim_key: str
    claim_ids: tuple[str, str]
    detected_cycle: int = Field(ge=0)
    updated_cycle: int = Field(ge=0)
    status: ContradictionStatus
    preferred_claim_id: str | None = None
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    latest_revision_id: str | None = None


class RevisionRecord(FrozenRecord):
    revision_id: str
    contradiction_id: str
    prior_claim_id: str
    revised_to_claim_id: str
    cycle: int = Field(ge=0)
    reason: str
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    policy_snapshot: dict[str, Any] = Field(default_factory=dict)


class EpistemicPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    source_weights: dict[str, float] = Field(
        default_factory=lambda: {
            ClaimSourceClass.DIRECT_OBSERVATION.value: 0.90,
            ClaimSourceClass.PHYSICAL_OUTCOME.value: 0.98,
            ClaimSourceClass.SELF_ACTION.value: 0.85,
            ClaimSourceClass.HUMAN_TESTIMONY.value: 0.60,
            ClaimSourceClass.EXTERNAL_TESTIMONY.value: 0.50,
            ClaimSourceClass.SYSTEM_INFERENCE.value: 0.40,
            ClaimSourceClass.TRANSLATION.value: 0.20,
        }
    )
    confirmation_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    resolution_margin: float = Field(default=0.15, ge=0.0, le=1.0)
    minimum_preference_score: float = Field(default=0.02, ge=-1.0, le=1.0)
    revision: int = Field(default=0, ge=0)

    @field_validator("source_weights")
    @classmethod
    def validate_source_weights(cls, value: dict[str, float]) -> dict[str, float]:
        required = {item.value for item in ClaimSourceClass}
        missing = required - set(value)
        if missing:
            raise ValueError(f"Missing source weights: {sorted(missing)}")
        for name, weight in value.items():
            if not math.isfinite(weight) or not 0.0 <= weight <= 1.0:
                raise ValueError(f"Invalid source weight for {name!r}.")
        return dict(sorted(value.items()))


class GovernanceState(BaseModel):
    """Persisted constitutional policy and learned consequence calibration."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    t_g: float = Field(default=0.5, ge=0.0, le=1.0)
    # Retained for checkpoint compatibility and diagnostics. Milestone 5 council
    # decisions are rule-structured and do not use a weighted average.
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            KingName.DATA.value: 1.0,
            KingName.FOREFRONT.value: 1.0,
            KingName.ETHICS.value: 1.5,
        }
    )
    enabled_kings: dict[str, bool] = Field(
        default_factory=lambda: {
            KingName.DATA.value: True,
            KingName.FOREFRONT.value: True,
            KingName.ETHICS.value: True,
        }
    )
    attention_budget: float = Field(default=1.0, gt=0.0)
    forefront_priority_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    ethics_veto_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    outcome_learning_rate: float = Field(default=0.80, gt=0.0, le=1.0)
    learned_action_risk: dict[str, float] = Field(default_factory=dict)
    policy_version: str = "council-v1"
    revision: int = Field(default=0, ge=0)

    @field_validator("weights")
    @classmethod
    def finite_nonnegative_weights(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("Governance weights cannot be empty.")
        for name, weight in value.items():
            if not name.strip() or not math.isfinite(weight) or weight < 0:
                raise ValueError("Governance weights must be finite and nonnegative.")
        return dict(sorted(value.items()))

    @field_validator("enabled_kings")
    @classmethod
    def validate_enabled_kings(cls, value: dict[str, bool]) -> dict[str, bool]:
        expected = {item.value for item in KingName}
        missing = expected - set(value)
        if missing:
            raise ValueError(f"Missing King enable flags: {sorted(missing)}")
        return {name: bool(value[name]) for name in sorted(expected)}

    @field_validator("learned_action_risk")
    @classmethod
    def validate_learned_risk(cls, value: dict[str, float]) -> dict[str, float]:
        cleaned: dict[str, float] = {}
        for action_class, risk in value.items():
            key = action_class.strip()
            if not key:
                raise ValueError("Learned action risk keys cannot be empty.")
            if not math.isfinite(risk) or not 0.0 <= risk <= 1.0:
                raise ValueError("Learned action risks must be finite probabilities.")
            cleaned[key] = risk
        return dict(sorted(cleaned.items()))


class LineageState(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    generation: int = Field(default=0, ge=0)
    parent_checkpoint_hashes: list[str] = Field(default_factory=list)
    ancestor_kernel_ids: list[str] = Field(default_factory=list)
    branch_id: str | None = None
    branch_label: str | None = None

    @field_validator("branch_id", "branch_label")
    @classmethod
    def validate_optional_lineage_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Optional lineage identifiers cannot be blank.")
        return cleaned


class AttentionCandidate(FrozenRecord):
    candidate_id: str
    source_ref: str
    created_cycle: int = Field(ge=0)
    priority: float = Field(ge=0.0)
    resource_request: float = Field(gt=0.0)
    reason: str
    evidence_refs: tuple[str, ...] = Field(min_length=1)


class FieldFrame(FrozenRecord):
    cycle: int = Field(ge=0)
    caused_by_refs: tuple[str, ...] = Field(min_length=1)
    real: tuple[float, ...]
    imag: tuple[float, ...]
    delta_norm: float = Field(ge=0.0)
    effect_sha256: str = ""
    bound_concept_ids: tuple[str, ...] = Field(default_factory=tuple)
    policy_revision: int = Field(default=0, ge=0)


class FieldState(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    state_dim: int = Field(gt=0)
    real: list[float]
    imag: list[float]
    history: list[FieldFrame] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dimensions(self) -> "FieldState":
        if len(self.real) != self.state_dim or len(self.imag) != self.state_dim:
            raise ValueError("Field real/imag arrays must match state_dim.")
        for value in [*self.real, *self.imag]:
            if not math.isfinite(value):
                raise ValueError("Field values must be finite.")
        return self




class ECWFPolicy(BaseModel):
    """Persisted operating policy for the rebuilt complex-valued field."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    retention: float = Field(default=0.72, ge=0.0, le=1.0)
    feature_coupling: float = Field(default=0.65, ge=0.0)
    concept_coupling: float = Field(default=0.55, ge=0.0)
    query_profile_weight: float = Field(default=0.50, ge=0.0)
    query_current_weight: float = Field(default=0.30, ge=0.0)
    query_history_weight: float = Field(default=0.20, ge=0.0)
    history_window: int = Field(default=16, ge=1)
    history_decay: float = Field(default=0.85, gt=0.0, le=1.0)
    default_top_k: int = Field(default=8, ge=1)
    default_attention_resource: float = Field(default=0.10, gt=0.0)
    address_revision: int = Field(default=1, ge=1)
    revision: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_query_weights(self) -> "ECWFPolicy":
        total = (
            self.query_profile_weight
            + self.query_current_weight
            + self.query_history_weight
        )
        if not math.isfinite(total) or total <= 0.0:
            raise ValueError("At least one resonance query weight must be positive.")
        return self


class ConceptFieldAddress(FrozenRecord):
    concept_id: str
    address_sha256: str
    created_cycle: int = Field(ge=0)
    state_dim: int = Field(gt=0)
    derivation_nonce: int = Field(default=0, ge=0)
    real: tuple[float, ...]
    imag: tuple[float, ...]

    @model_validator(mode="after")
    def validate_address(self) -> "ConceptFieldAddress":
        if len(self.real) != self.state_dim or len(self.imag) != self.state_dim:
            raise ValueError("Concept field address arrays must match state_dim.")
        norm_sq = sum(value * value for value in self.real) + sum(
            value * value for value in self.imag
        )
        if not math.isfinite(norm_sq) or abs(math.sqrt(norm_sq) - 1.0) > 1e-6:
            raise ValueError("Concept field addresses must be finite unit vectors.")
        return self




class ConceptResonanceProfile(FrozenRecord):
    concept_id: str
    state_dim: int = Field(gt=0)
    exposure_count: int = Field(ge=1)
    created_cycle: int = Field(ge=0)
    updated_cycle: int = Field(ge=0)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    real: tuple[float, ...]
    imag: tuple[float, ...]

    @model_validator(mode="after")
    def validate_profile(self) -> "ConceptResonanceProfile":
        if len(self.real) != self.state_dim or len(self.imag) != self.state_dim:
            raise ValueError("Concept resonance profile arrays must match state_dim.")
        norm_sq = sum(value * value for value in self.real) + sum(
            value * value for value in self.imag
        )
        if not math.isfinite(norm_sq) or abs(math.sqrt(norm_sq) - 1.0) > 1e-6:
            raise ValueError("Concept resonance profiles must be finite unit vectors.")
        return self


class ResonanceContribution(FrozenRecord):
    profile_alignment: float = Field(ge=0.0, le=1.0)
    current_field_alignment: float = Field(ge=0.0, le=1.0)
    history_alignment: float = Field(ge=0.0, le=1.0)
    profile_weight: float = Field(ge=0.0, le=1.0)
    current_field_weight: float = Field(ge=0.0, le=1.0)
    history_weight: float = Field(ge=0.0, le=1.0)
    weighted_profile: float = Field(ge=0.0, le=1.0)
    weighted_current_field: float = Field(ge=0.0, le=1.0)
    weighted_history: float = Field(ge=0.0, le=1.0)


class ResonanceCandidate(FrozenRecord):
    rank: int = Field(ge=1)
    concept_id: str
    score: float = Field(ge=0.0, le=1.0)
    profile_exposure_count: int = Field(default=0, ge=0)
    profile_evidence_count: int = Field(default=0, ge=0)
    contribution: ResonanceContribution


class ResonanceReport(FrozenRecord):
    query_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    modality: str
    query_features: tuple[float, ...]
    query_feature_sha256: str
    state_fingerprint: str
    field_fingerprint: str
    policy_revision: int = Field(ge=0)
    candidate_scope_count: int = Field(ge=0)
    candidate_scope_ids: tuple[str, ...] = Field(default_factory=tuple)
    candidates: tuple[ResonanceCandidate, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_report_integrity(self) -> "ResonanceReport":
        if not self.modality.strip():
            raise ValueError("Resonance report modality cannot be empty.")
        if not self.query_features or any(
            not math.isfinite(value) for value in self.query_features
        ):
            raise ValueError("Resonance query features must be finite and non-empty.")
        if self.candidate_scope_count != len(self.candidate_scope_ids):
            raise ValueError("Resonance candidate scope count does not match its IDs.")
        if tuple(sorted(set(self.candidate_scope_ids))) != self.candidate_scope_ids:
            raise ValueError("Resonance candidate scope IDs must be sorted and unique.")
        actual_feature_hash = hashlib.sha256(
            canonical_json_bytes(list(self.query_features))
        ).hexdigest()
        if actual_feature_hash != self.query_feature_sha256:
            raise ValueError("Resonance query feature checksum mismatch.")
        expected_query_id = stable_id(
            "resonance_query",
            self.kernel_id,
            self.cycle,
            self.modality,
            self.query_feature_sha256,
            self.state_fingerprint,
            self.field_fingerprint,
            self.policy_revision,
            self.candidate_scope_ids,
            tuple(item.model_dump(mode="json") for item in self.candidates),
        )
        if expected_query_id != self.query_id:
            raise ValueError("Resonance report identity checksum mismatch.")
        return self


class ResonanceEvent(FrozenRecord):
    resonance_event_id: str
    query_report: ResonanceReport
    committed_cycle: int = Field(ge=1)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    attention_candidate_ids: tuple[str, ...] = Field(default_factory=tuple)
    semantic_mutation_permitted: bool = False


class CouncilProposal(FrozenRecord):
    proposal_id: str
    kernel_id: str
    created_cycle: int = Field(ge=0)
    proposal_kind: GovernanceProposalKind
    operation: str
    action_class: str
    description: str
    target_claim_id: str | None = None
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    attention_candidate_ids: tuple[str, ...] = Field(default_factory=tuple)
    resonance_event_ids: tuple[str, ...] = Field(default_factory=tuple)
    requested_resource: float = Field(default=0.10, gt=0.0)
    relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    urgency: float = Field(default=0.0, ge=0.0, le=1.0)
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    predicted_information_gain: float = Field(default=0.0, ge=0.0, le=1.0)
    harm_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    reversibility: float = Field(default=1.0, ge=0.0, le=1.0)
    consent_required: bool = False
    consent_present: bool = False
    boundary_sensitive: bool = False
    safe_alternatives: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)
    state_fingerprint: str
    governance_fingerprint: str

    @field_validator("operation", "action_class", "description")
    @classmethod
    def nonempty_proposal_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Council proposal text fields cannot be empty.")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> "CouncilProposal":
        expected = stable_id(
            "council_proposal",
            self.kernel_id,
            self.created_cycle,
            self.proposal_kind.value,
            self.operation,
            self.action_class,
            self.description,
            self.target_claim_id,
            self.evidence_refs,
            self.attention_candidate_ids,
            self.resonance_event_ids,
            self.requested_resource,
            self.relevance,
            self.urgency,
            self.novelty,
            self.predicted_information_gain,
            self.harm_risk,
            self.reversibility,
            self.consent_required,
            self.consent_present,
            self.boundary_sensitive,
            self.safe_alternatives,
            self.metadata,
            self.state_fingerprint,
            self.governance_fingerprint,
        )
        if expected != self.proposal_id:
            raise ValueError("Council proposal identity checksum mismatch.")
        return self


class KingAssessment(FrozenRecord):
    assessment_id: str
    proposal_id: str
    king: KingName
    jurisdiction: str
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    recommendation: KingRecommendation
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    attention_candidate_ids: tuple[str, ...] = Field(default_factory=tuple)
    constraints: tuple[str, ...] = Field(default_factory=tuple)
    rationale_codes: tuple[str, ...] = Field(default_factory=tuple)
    details: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_identity(self) -> "KingAssessment":
        expected = stable_id(
            "king_assessment",
            self.proposal_id,
            self.king.value,
            self.jurisdiction,
            self.score,
            self.confidence,
            self.recommendation.value,
            self.evidence_refs,
            self.attention_candidate_ids,
            self.constraints,
            self.rationale_codes,
            self.details,
        )
        if expected != self.assessment_id:
            raise ValueError("King assessment identity checksum mismatch.")
        return self


class CouncilReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    state_fingerprint: str
    governance_fingerprint: str
    proposal: CouncilProposal
    assessments: tuple[KingAssessment, ...]
    disposition: CouncilDisposition
    authorized_operations: tuple[str, ...] = Field(default_factory=tuple)
    blocked_operations: tuple[str, ...] = Field(default_factory=tuple)
    constraints: tuple[str, ...] = Field(default_factory=tuple)
    required_evidence: tuple[str, ...] = Field(default_factory=tuple)
    safe_alternatives: tuple[str, ...] = Field(default_factory=tuple)
    rationale_codes: tuple[str, ...] = Field(default_factory=tuple)
    policy_snapshot: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_report(self) -> "CouncilReport":
        kings = tuple(item.king.value for item in self.assessments)
        if len(kings) != len(set(kings)):
            raise ValueError("Council reports may contain only one assessment per King.")
        expected = stable_id(
            "council_report",
            self.kernel_id,
            self.cycle,
            self.state_fingerprint,
            self.governance_fingerprint,
            self.proposal.model_dump(mode="json"),
            tuple(item.model_dump(mode="json") for item in self.assessments),
            self.disposition.value,
            self.authorized_operations,
            self.blocked_operations,
            self.constraints,
            self.required_evidence,
            self.safe_alternatives,
            self.rationale_codes,
            self.policy_snapshot,
        )
        if expected != self.report_id:
            raise ValueError("Council report identity checksum mismatch.")
        return self


class CouncilDecisionEvent(FrozenRecord):
    decision_event_id: str
    report: CouncilReport
    committed_cycle: int = Field(ge=1)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    semantic_mutation_permitted: bool = False
    governance_policy_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_identity(self) -> "CouncilDecisionEvent":
        expected = stable_id(
            "council_decision",
            self.report.report_id,
            self.committed_cycle,
            self.evidence_refs,
        )
        if expected != self.decision_event_id:
            raise ValueError("Council decision identity checksum mismatch.")
        if self.semantic_mutation_permitted or self.governance_policy_mutation_permitted:
            raise ValueError("Council decisions cannot carry silent mutation permission.")
        return self


class GovernanceOutcomeRecord(FrozenRecord):
    outcome_id: str
    decision_event_id: str
    action_class: str
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    succeeded: bool
    harm_score: float = Field(ge=0.0, le=1.0)
    prediction_error: float = Field(ge=0.0, le=1.0)
    cycle: int = Field(ge=1)
    learned_risk_before: float = Field(ge=0.0, le=1.0)
    learned_risk_after: float = Field(ge=0.0, le=1.0)
    policy_revision_before: int = Field(ge=0)
    policy_revision_after: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_identity(self) -> "GovernanceOutcomeRecord":
        expected = stable_id(
            "governance_outcome",
            self.decision_event_id,
            self.action_class,
            self.evidence_refs,
            self.succeeded,
            self.harm_score,
            self.learned_risk_before,
            self.learned_risk_after,
            self.cycle,
        )
        if expected != self.outcome_id:
            raise ValueError("Governance outcome identity checksum mismatch.")
        if self.policy_revision_after != self.policy_revision_before + 1:
            raise ValueError("Governance outcome policy revision must advance by one.")
        return self


class ShardPolicy(BaseModel):
    """Persisted limits and score weights for bounded specialization."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    max_concepts_per_shard: int = Field(default=32, ge=2)
    max_relations_per_shard: int = Field(default=96, ge=1)
    max_portals_per_bridge: int = Field(default=8, ge=1)
    minimum_direct_grounding: float = Field(default=0.34, ge=0.0, le=1.0)
    minimum_route_score: float = Field(default=0.45, ge=0.0, le=1.0)
    direct_weight: float = Field(default=0.50, ge=0.0)
    relation_weight: float = Field(default=0.18, ge=0.0)
    resonance_weight: float = Field(default=0.12, ge=0.0)
    continuity_weight: float = Field(default=0.10, ge=0.0)
    evidence_weight: float = Field(default=0.10, ge=0.0)
    contamination_penalty: float = Field(default=0.12, ge=0.0)
    thaw_penalty: float = Field(default=0.06, ge=0.0)
    revision: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_weights(self) -> "ShardPolicy":
        positive = (
            self.direct_weight
            + self.relation_weight
            + self.resonance_weight
            + self.continuity_weight
            + self.evidence_weight
        )
        if not math.isfinite(positive) or positive <= 0.0:
            raise ValueError("At least one positive routing weight is required.")
        return self


class ShardRecord(FrozenRecord):
    shard_id: str
    label: str
    normalized_label: str
    status: ShardStatus
    created_cycle: int = Field(ge=0)
    updated_cycle: int = Field(ge=0)
    parent_shard_id: str | None = None
    concept_ids: tuple[str, ...] = Field(default_factory=tuple)
    relation_ids: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    specialization_signature: tuple[str, ...] = Field(default_factory=tuple)
    formation_event_id: str | None = None

    @model_validator(mode="after")
    def validate_membership(self) -> "ShardRecord":
        if tuple(sorted(set(self.concept_ids))) != self.concept_ids:
            raise ValueError("Shard concept IDs must be sorted and unique.")
        if tuple(sorted(set(self.relation_ids))) != self.relation_ids:
            raise ValueError("Shard relation IDs must be sorted and unique.")
        if tuple(sorted(set(self.evidence_refs))) != self.evidence_refs:
            raise ValueError("Shard evidence refs must be sorted and unique.")
        if tuple(sorted(set(self.specialization_signature))) != self.specialization_signature:
            raise ValueError("Shard specialization signatures must be sorted and unique.")
        if self.shard_id == "root" and self.status not in {ShardStatus.ROOT, ShardStatus.ACTIVE}:
            raise ValueError("Root shard must retain root or active status.")
        if self.shard_id != "root" and not self.concept_ids:
            raise ValueError("Specialized shards require at least one concept.")
        return self


class ShardFormationReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    shard_label: str
    normalized_label: str
    proposed_shard_id: str
    parent_shard_id: str
    concept_ids: tuple[str, ...]
    relation_ids: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[str, ...]
    specialization_signature: tuple[str, ...]
    operation: str
    policy_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report(self) -> "ShardFormationReport":
        if not self.concept_ids or not self.evidence_refs:
            raise ValueError("Shard formation requires concepts and evidence.")
        for values, label in (
            (self.concept_ids, "concept"),
            (self.relation_ids, "relation"),
            (self.evidence_refs, "evidence"),
            (self.specialization_signature, "signature"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Shard formation {label} values must be sorted and unique.")
        expected = stable_id(
            "shard_formation_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.shard_label,
            self.normalized_label,
            self.proposed_shard_id,
            self.parent_shard_id,
            self.concept_ids,
            self.relation_ids,
            self.evidence_refs,
            self.specialization_signature,
            self.operation,
            self.policy_revision,
        )
        if expected != self.report_id:
            raise ValueError("Shard formation report identity checksum mismatch.")
        return self


class ShardFormationEvent(FrozenRecord):
    formation_event_id: str
    report: ShardFormationReport
    council_decision_event_id: str
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "ShardFormationEvent":
        expected = stable_id(
            "shard_formation_event",
            self.report.report_id,
            self.council_decision_event_id,
            self.committed_cycle,
        )
        if expected != self.formation_event_id:
            raise ValueError("Shard formation event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Shard formation cannot create semantic truth.")
        return self


class RouteScoreComponents(FrozenRecord):
    direct_grounding: float = Field(ge=0.0, le=1.0)
    relation_support: float = Field(ge=0.0, le=1.0)
    resonance_support: float = Field(ge=0.0, le=1.0)
    continuity_support: float = Field(ge=0.0, le=1.0)
    evidence_coverage: float = Field(ge=0.0, le=1.0)
    contamination: float = Field(ge=0.0, le=1.0)
    thaw_cost: float = Field(ge=0.0, le=1.0)
    weighted_positive: float = Field(ge=0.0)
    weighted_penalty: float = Field(ge=0.0)


class RouteCandidate(FrozenRecord):
    rank: int = Field(ge=1)
    shard_id: str
    score: float = Field(ge=0.0, le=1.0)
    eligible: bool
    rejection_codes: tuple[str, ...] = Field(default_factory=tuple)
    directly_grounded_concept_ids: tuple[str, ...] = Field(default_factory=tuple)
    portal_concept_ids: tuple[str, ...] = Field(default_factory=tuple)
    components: RouteScoreComponents


class RoutingReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    source_shard_id: str
    cue_concept_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    resonance_event_ids: tuple[str, ...] = Field(default_factory=tuple)
    candidates: tuple[RouteCandidate, ...] = Field(default_factory=tuple)
    disposition: RoutingDisposition
    selected_shard_id: str | None = None
    operation: str
    policy_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report(self) -> "RoutingReport":
        for values, label in (
            (self.cue_concept_ids, "cue concept"),
            (self.evidence_refs, "evidence"),
            (self.resonance_event_ids, "resonance event"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Routing {label} values must be sorted and unique.")
        expected = stable_id(
            "routing_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.source_shard_id,
            self.cue_concept_ids,
            self.evidence_refs,
            self.resonance_event_ids,
            tuple(item.model_dump(mode="json") for item in self.candidates),
            self.disposition.value,
            self.selected_shard_id,
            self.operation,
            self.policy_revision,
        )
        if expected != self.report_id:
            raise ValueError("Routing report identity checksum mismatch.")
        if self.disposition == RoutingDisposition.ROUTE and not self.selected_shard_id:
            raise ValueError("A route disposition requires a selected shard.")
        return self


class ShardBridgeRecord(FrozenRecord):
    bridge_id: str
    source_shard_id: str
    target_shard_id: str
    portal_concept_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    traversal_count: int = Field(ge=1)
    created_cycle: int = Field(ge=1)
    last_traversed_cycle: int = Field(ge=1)
    status: BridgeStatus = BridgeStatus.TRAVERSED

    @model_validator(mode="after")
    def validate_bridge(self) -> "ShardBridgeRecord":
        if self.source_shard_id >= self.target_shard_id:
            raise ValueError("Bridge shard endpoints must be canonicalized.")
        if tuple(sorted(set(self.portal_concept_ids))) != self.portal_concept_ids:
            raise ValueError("Bridge portal concepts must be sorted and unique.")
        if tuple(sorted(set(self.evidence_refs))) != self.evidence_refs:
            raise ValueError("Bridge evidence refs must be sorted and unique.")
        return self


class RoutingEvent(FrozenRecord):
    routing_event_id: str
    report: RoutingReport
    council_decision_event_id: str
    committed_cycle: int = Field(ge=1)
    from_shard_id: str
    to_shard_id: str
    bridge_id: str
    direct_cue_concept_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "RoutingEvent":
        expected = stable_id(
            "routing_event",
            self.report.report_id,
            self.council_decision_event_id,
            self.committed_cycle,
            self.from_shard_id,
            self.to_shard_id,
            self.bridge_id,
            self.direct_cue_concept_ids,
            self.evidence_refs,
        )
        if expected != self.routing_event_id:
            raise ValueError("Routing event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Routing cannot create semantic truth.")
        return self



class ObjecthoodPolicy(BaseModel):
    """Persisted evidence thresholds for earned proto-object promotion."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    maximum_appearance_distance: float = Field(default=0.38, gt=0.0)
    maximum_position_error: float = Field(default=0.35, gt=0.0)
    maximum_motion_error: float = Field(default=0.45, gt=0.0)
    association_threshold: float = Field(default=0.62, ge=0.0, le=1.0)
    ambiguity_margin: float = Field(default=0.04, ge=0.0, le=1.0)
    transformation_novelty_distance: float = Field(default=0.06, ge=0.0)
    maximum_frame_gap: int = Field(default=3, ge=1)
    maximum_occlusion_gap: int = Field(default=6, ge=1)

    minimum_visible_observations: int = Field(default=6, ge=2)
    minimum_episode_count: int = Field(default=2, ge=1)
    minimum_persistence_count: int = Field(default=3, ge=1)
    minimum_transformation_count: int = Field(default=2, ge=0)
    minimum_common_motion_count: int = Field(default=2, ge=0)
    minimum_reappearance_count: int = Field(default=1, ge=0)
    minimum_support_score: float = Field(default=0.72, ge=0.0, le=1.0)

    recurrence_weight: float = Field(default=0.15, ge=0.0)
    persistence_weight: float = Field(default=0.20, ge=0.0)
    transformation_weight: float = Field(default=0.15, ge=0.0)
    common_motion_weight: float = Field(default=0.15, ge=0.0)
    reappearance_weight: float = Field(default=0.15, ge=0.0)
    ambiguity_penalty: float = Field(default=0.20, ge=0.0)
    revision: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_weights(self) -> "ObjecthoodPolicy":
        total = (
            self.recurrence_weight
            + self.persistence_weight
            + self.transformation_weight
            + self.common_motion_weight
            + self.reappearance_weight
        )
        if not math.isfinite(total) or total <= 0.0:
            raise ValueError("Objecthood support weights must have a positive sum.")
        return self


class ObjectObservationInput(FrozenRecord):
    episode_id: str
    frame_index: int = Field(ge=0)
    evidence_ref: str
    modality: str
    kind: ObjectObservationKind
    appearance_features: tuple[float, ...] = Field(default_factory=tuple)
    position: tuple[float, float] | None = None
    motion: tuple[float, float] | None = None
    common_motion_supported: bool = False
    target_candidate_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_observation_input(self) -> "ObjectObservationInput":
        if not self.episode_id.strip() or not self.evidence_ref.strip() or not self.modality.strip():
            raise ValueError("Object observation identity fields cannot be empty.")
        if self.kind == ObjectObservationKind.VISIBLE:
            if not self.appearance_features or self.position is None or self.motion is None:
                raise ValueError("Visible observations require appearance, position, and motion.")
            if self.target_candidate_id is not None:
                raise ValueError("Visible observations cannot force a target candidate.")
        else:
            if self.target_candidate_id is None:
                raise ValueError("Occlusion observations require a target candidate.")
        numeric = [*self.appearance_features]
        if self.position is not None:
            numeric.extend(self.position)
        if self.motion is not None:
            numeric.extend(self.motion)
        if any(not math.isfinite(value) for value in numeric):
            raise ValueError("Object observation values must be finite.")
        return self


class ObjectObservationRecord(FrozenRecord):
    observation_id: str
    episode_id: str
    frame_index: int = Field(ge=0)
    evidence_ref: str
    modality: str
    kind: ObjectObservationKind
    appearance_features: tuple[float, ...] = Field(default_factory=tuple)
    position: tuple[float, float] | None = None
    motion: tuple[float, float] | None = None
    common_motion_supported: bool = False
    target_candidate_id: str | None = None
    committed_cycle: int = Field(ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObjectSupportComponents(FrozenRecord):
    recurrence: float = Field(ge=0.0, le=1.0)
    persistence: float = Field(ge=0.0, le=1.0)
    transformation: float = Field(ge=0.0, le=1.0)
    common_motion: float = Field(ge=0.0, le=1.0)
    reappearance: float = Field(ge=0.0, le=1.0)
    ambiguity_penalty: float = Field(ge=0.0)
    weighted_positive: float = Field(ge=0.0)
    weighted_penalty: float = Field(ge=0.0)


class ObjectCandidateRecord(FrozenRecord):
    candidate_id: str
    status: ObjectCandidateStatus
    created_cycle: int = Field(ge=1)
    updated_cycle: int = Field(ge=1)
    observation_ids: tuple[str, ...] = Field(min_length=1)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    episode_ids: tuple[str, ...] = Field(min_length=1)
    appearance_centroid: tuple[float, ...]
    last_position: tuple[float, float] | None = None
    last_motion: tuple[float, float] | None = None
    last_episode_id: str
    last_frame_index: int = Field(ge=0)
    visible_observation_count: int = Field(ge=1)
    persistence_count: int = Field(default=0, ge=0)
    transformation_count: int = Field(default=0, ge=0)
    common_motion_count: int = Field(default=0, ge=0)
    occlusion_count: int = Field(default=0, ge=0)
    reappearance_count: int = Field(default=0, ge=0)
    ambiguity_count: int = Field(default=0, ge=0)
    competing_candidate_ids: tuple[str, ...] = Field(default_factory=tuple)
    support_score: float = Field(default=0.0, ge=0.0, le=1.0)
    support_components: ObjectSupportComponents
    promoted_concept_id: str | None = None

    @model_validator(mode="after")
    def validate_candidate(self) -> "ObjectCandidateRecord":
        for values, label in (
            (self.observation_ids, "observation"),
            (self.evidence_refs, "evidence"),
            (self.episode_ids, "episode"),
            (self.competing_candidate_ids, "competing candidate"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Object candidate {label} IDs must be sorted and unique.")
        if self.candidate_id in self.competing_candidate_ids:
            raise ValueError("An object candidate cannot compete with itself.")
        if self.status == ObjectCandidateStatus.PROMOTED and not self.promoted_concept_id:
            raise ValueError("Promoted object candidates require a concept ID.")
        return self


class ObjectAssociationCandidate(FrozenRecord):
    rank: int = Field(ge=1)
    candidate_id: str
    score: float = Field(ge=0.0, le=1.0)
    eligible: bool
    appearance_similarity: float = Field(ge=0.0, le=1.0)
    position_fit: float = Field(ge=0.0, le=1.0)
    motion_alignment: float = Field(ge=0.0, le=1.0)
    episode_continuity: float = Field(ge=0.0, le=1.0)
    rejection_codes: tuple[str, ...] = Field(default_factory=tuple)


class ObjectObservationReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    observation: ObjectObservationInput
    candidates: tuple[ObjectAssociationCandidate, ...] = Field(default_factory=tuple)
    disposition: ObjectAssociationDisposition
    selected_candidate_id: str | None = None
    competing_candidate_ids: tuple[str, ...] = Field(default_factory=tuple)
    proposed_candidate: ObjectCandidateRecord
    operation: str
    policy_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report(self) -> "ObjectObservationReport":
        if tuple(sorted(set(self.competing_candidate_ids))) != self.competing_candidate_ids:
            raise ValueError("Object report competing IDs must be sorted and unique.")
        expected = stable_id(
            "object_observation_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.observation.model_dump(mode="json"),
            tuple(item.model_dump(mode="json") for item in self.candidates),
            self.disposition.value,
            self.selected_candidate_id,
            self.competing_candidate_ids,
            self.proposed_candidate.model_dump(mode="json"),
            self.operation,
            self.policy_revision,
        )
        if expected != self.report_id:
            raise ValueError("Object observation report identity checksum mismatch.")
        return self


class ObjectObservationEvent(FrozenRecord):
    event_id: str
    report: ObjectObservationReport
    observation_id: str
    candidate_id: str
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "ObjectObservationEvent":
        expected = stable_id(
            "object_observation_event",
            self.report.report_id,
            self.observation_id,
            self.candidate_id,
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Object observation event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Object tracking cannot create semantic truth.")
        return self


class ObjectPromotionReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    candidate_id: str
    disposition: ObjectPromotionDisposition
    rejection_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    proposed_label: str
    proposed_concept_id: str
    operation: str
    policy_revision: int = Field(ge=0)
    candidate_snapshot: ObjectCandidateRecord

    @model_validator(mode="after")
    def validate_report(self) -> "ObjectPromotionReport":
        if tuple(sorted(set(self.rejection_codes))) != self.rejection_codes:
            raise ValueError("Object promotion rejection codes must be sorted and unique.")
        if tuple(sorted(set(self.evidence_refs))) != self.evidence_refs:
            raise ValueError("Object promotion evidence refs must be sorted and unique.")
        expected = stable_id(
            "object_promotion_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.candidate_id,
            self.disposition.value,
            self.rejection_codes,
            self.evidence_refs,
            self.proposed_label,
            self.proposed_concept_id,
            self.operation,
            self.policy_revision,
            self.candidate_snapshot.model_dump(mode="json"),
        )
        if expected != self.report_id:
            raise ValueError("Object promotion report identity checksum mismatch.")
        return self


class ObjectPromotionEvent(FrozenRecord):
    event_id: str
    report: ObjectPromotionReport
    council_decision_event_id: str
    concept_id: str
    committed_cycle: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_event(self) -> "ObjectPromotionEvent":
        expected = stable_id(
            "object_promotion_event",
            self.report.report_id,
            self.council_decision_event_id,
            self.concept_id,
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Object promotion event identity checksum mismatch.")
        return self



class PlasticityPolicy(BaseModel):
    """Bounded, nonsemantic local-association policy.

    These associations are developmental traces, not canonical semantic
    relations.  They exist to recover V4-style local plasticity without
    allowing repeated coactivation to turn the whole cognitive graph into a
    clique.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    minimum_foreground_score: float = Field(default=0.32, ge=0.0, le=1.0)
    current_evidence_activation_floor: float = Field(default=0.62, ge=0.0, le=1.0)
    creation_threshold: float = Field(default=0.52, ge=0.0, le=1.0)
    reinforcement_threshold: float = Field(default=0.34, ge=0.0, le=1.0)
    initial_strength: float = Field(default=0.08, ge=0.0, le=1.0)
    learning_rate: float = Field(default=0.20, ge=0.0, le=1.0)
    decay_rate: float = Field(default=0.025, ge=0.0, le=1.0)
    minimum_strength: float = Field(default=0.035, ge=0.0, le=1.0)
    max_degree: int = Field(default=8, ge=1)
    max_edge_ratio: float = Field(default=4.0, gt=0.0)
    strength_budget_per_concept: float = Field(default=2.4, gt=0.0)
    max_new_associations_per_cycle: int = Field(default=6, ge=0)
    max_reinforcements_per_cycle: int = Field(default=12, ge=0)
    max_evidence_refs_per_association: int = Field(default=32, ge=1)
    require_current_evidence_for_creation: bool = True
    scope_to_active_shard: bool = True
    revision: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_plasticity_policy(self) -> "PlasticityPolicy":
        if self.reinforcement_threshold > self.creation_threshold:
            raise ValueError(
                "Plasticity reinforcement_threshold cannot exceed creation_threshold."
            )
        if self.minimum_strength > 1.0:
            raise ValueError("Plasticity minimum_strength cannot exceed 1.")
        return self


class PlasticityAssociationRecord(FrozenRecord):
    association_id: str
    concept_ids: tuple[str, str]
    strength: float = Field(gt=0.0, le=1.0)
    exposure_count: int = Field(ge=1)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    created_cycle: int = Field(ge=0)
    updated_cycle: int = Field(ge=0)
    last_reinforced_cycle: int = Field(ge=0)
    last_workspace_event_id: str

    @model_validator(mode="after")
    def validate_association(self) -> "PlasticityAssociationRecord":
        if len(self.concept_ids) != 2 or self.concept_ids[0] == self.concept_ids[1]:
            raise ValueError("Plasticity associations require two distinct concepts.")
        if tuple(sorted(self.concept_ids)) != self.concept_ids:
            raise ValueError("Plasticity association concept IDs must be sorted.")
        if tuple(sorted(set(self.evidence_refs))) != self.evidence_refs:
            raise ValueError("Plasticity association evidence refs must be sorted and unique.")
        expected = stable_id("plasticity_association", *self.concept_ids)
        if expected != self.association_id:
            raise ValueError("Plasticity association identity checksum mismatch.")
        return self


class PlasticityPairAssessment(FrozenRecord):
    association_id: str
    concept_ids: tuple[str, str]
    coactivation_score: float = Field(ge=0.0, le=1.0)
    current_evidence_touched: bool
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    disposition: PlasticityUpdateKind
    prior_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    proposed_strength: float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_pair(self) -> "PlasticityPairAssessment":
        if tuple(sorted(self.concept_ids)) != self.concept_ids:
            raise ValueError("Plasticity pair concept IDs must be sorted.")
        if tuple(sorted(set(self.evidence_refs))) != self.evidence_refs:
            raise ValueError("Plasticity pair evidence refs must be sorted and unique.")
        expected = stable_id("plasticity_association", *self.concept_ids)
        if expected != self.association_id:
            raise ValueError("Plasticity pair identity checksum mismatch.")
        return self


class PlasticityReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    workspace_event_id: str
    candidate_concept_ids: tuple[str, ...]
    assessments: tuple[PlasticityPairAssessment, ...]
    proposed_associations: tuple[PlasticityAssociationRecord, ...]
    created_association_ids: tuple[str, ...]
    reinforced_association_ids: tuple[str, ...]
    decayed_association_ids: tuple[str, ...]
    pruned_association_ids: tuple[str, ...]
    edge_count_before: int = Field(ge=0)
    edge_count_after: int = Field(ge=0)
    max_degree_after: int = Field(ge=0)
    edge_ratio_after: float = Field(ge=0.0)
    operation: str
    policy_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report(self) -> "PlasticityReport":
        for values, label in (
            (self.candidate_concept_ids, "candidate concept"),
            (self.created_association_ids, "created association"),
            (self.reinforced_association_ids, "reinforced association"),
            (self.decayed_association_ids, "decayed association"),
            (self.pruned_association_ids, "pruned association"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Plasticity {label} IDs must be sorted and unique.")
        proposed_ids = tuple(item.association_id for item in self.proposed_associations)
        if tuple(sorted(proposed_ids)) != proposed_ids or len(set(proposed_ids)) != len(proposed_ids):
            raise ValueError("Proposed plasticity associations must be sorted and unique.")
        expected = stable_id(
            "plasticity_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.workspace_event_id,
            self.candidate_concept_ids,
            tuple(item.model_dump(mode="json") for item in self.assessments),
            tuple(item.model_dump(mode="json") for item in self.proposed_associations),
            self.created_association_ids,
            self.reinforced_association_ids,
            self.decayed_association_ids,
            self.pruned_association_ids,
            self.edge_count_before,
            self.edge_count_after,
            self.max_degree_after,
            self.edge_ratio_after,
            self.operation,
            self.policy_revision,
        )
        if expected != self.report_id:
            raise ValueError("Plasticity report identity checksum mismatch.")
        return self


class PlasticityEvent(FrozenRecord):
    event_id: str
    report: PlasticityReport
    active_association_ids: tuple[str, ...]
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "PlasticityEvent":
        if tuple(sorted(set(self.active_association_ids))) != self.active_association_ids:
            raise ValueError("Plasticity event association IDs must be sorted and unique.")
        expected = stable_id(
            "plasticity_event",
            self.report.report_id,
            self.active_association_ids,
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Plasticity event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Plasticity events cannot create semantic truth.")
        return self


class StructurePolicy(BaseModel):
    """Milestone 14 policy for earned, nonsemantic relational structures.

    The policy defines *conditions for objecthood*, never semantic labels.  A
    candidate can only be observed after lower-level plastic traces exist, and
    promotion remains a separate Council-authorized operation.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    minimum_members: int = Field(default=3, ge=3)
    maximum_members: int = Field(default=8, ge=3)
    maximum_candidates_per_cycle: int = Field(default=4, ge=1)
    minimum_member_association_strength: float = Field(default=0.28, ge=0.0, le=1.0)
    maximum_neighbors_per_seed: int = Field(default=7, ge=2)
    minimum_recurrence_events: int = Field(default=4, ge=2)
    minimum_evidence_events: int = Field(default=4, ge=2)
    minimum_contexts: int = Field(default=2, ge=1)
    minimum_reconstructability: float = Field(default=0.50, ge=0.0, le=1.0)
    minimum_boundary_selectivity: float = Field(default=0.65, ge=0.0, le=1.0)
    minimum_internal_cohesion: float = Field(default=0.38, ge=0.0, le=1.0)
    max_evidence_refs: int = Field(default=64, ge=4)
    max_observation_history: int = Field(default=64, ge=4)
    scope_to_active_shard: bool = True
    revision: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_structure_policy(self) -> "StructurePolicy":
        if self.maximum_members < self.minimum_members:
            raise ValueError("Structure maximum_members cannot be below minimum_members.")
        if self.maximum_neighbors_per_seed < self.minimum_members - 1:
            raise ValueError(
                "Structure maximum_neighbors_per_seed is too small for minimum_members."
            )
        return self


class StructureQualityVector(FrozenRecord):
    recurrence: float = Field(ge=0.0, le=1.0)
    reconstructability: float = Field(ge=0.0, le=1.0)
    boundary_selectivity: float = Field(ge=0.0, le=1.0)
    internal_cohesion: float = Field(ge=0.0, le=1.0)
    evidence_diversity: float = Field(ge=0.0, le=1.0)
    cross_context_stability: float = Field(ge=0.0, le=1.0)
    perturbation_survival: float = Field(default=0.0, ge=0.0, le=1.0)
    compression_gain: float = Field(default=0.0, ge=0.0, le=1.0)
    contradiction_tolerance: float = Field(default=1.0, ge=0.0, le=1.0)


class StructureCandidateRecord(FrozenRecord):
    candidate_id: str
    status: StructureCandidateStatus
    member_concept_ids: tuple[str, ...] = Field(min_length=3)
    member_relation_ids: tuple[str, ...] = Field(default_factory=tuple)
    internal_association_ids: tuple[str, ...] = Field(min_length=2)
    boundary_association_ids: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    workspace_event_ids: tuple[str, ...] = Field(min_length=1)
    observed_cycles: tuple[int, ...] = Field(min_length=1)
    occurrence_count: int = Field(ge=1)
    created_cycle: int = Field(ge=1)
    updated_cycle: int = Field(ge=1)
    quality: StructureQualityVector
    field_state_dim: int = Field(ge=0)
    field_prototype_real: tuple[float, ...] = Field(default_factory=tuple)
    field_prototype_imag: tuple[float, ...] = Field(default_factory=tuple)
    field_prototype_sha256: str = ""
    promoted_structure_id: str | None = None

    @model_validator(mode="after")
    def validate_candidate(self) -> "StructureCandidateRecord":
        for values, label in (
            (self.member_concept_ids, "member concept"),
            (self.member_relation_ids, "member relation"),
            (self.internal_association_ids, "internal association"),
            (self.boundary_association_ids, "boundary association"),
            (self.evidence_refs, "evidence"),
            (self.workspace_event_ids, "workspace event"),
            (self.observed_cycles, "observed cycle"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Structure candidate {label} values must be sorted and unique.")
        expected = stable_id("structure_candidate", self.member_concept_ids)
        if expected != self.candidate_id:
            raise ValueError("Structure candidate identity checksum mismatch.")
        if self.updated_cycle < self.created_cycle:
            raise ValueError("Structure candidate update cannot precede creation.")
        if self.occurrence_count < len(self.workspace_event_ids):
            raise ValueError("Structure candidate occurrence count cannot trail preserved events.")
        if self.field_state_dim == 0:
            if self.field_prototype_real or self.field_prototype_imag or self.field_prototype_sha256:
                raise ValueError("Empty structure field prototype must have no vector/checksum.")
        else:
            if len(self.field_prototype_real) != self.field_state_dim or len(self.field_prototype_imag) != self.field_state_dim:
                raise ValueError("Structure field prototype arrays must match state_dim.")
            expected_hash = hashlib.sha256(
                canonical_json_bytes(
                    {"real": self.field_prototype_real, "imag": self.field_prototype_imag}
                )
            ).hexdigest()
            if expected_hash != self.field_prototype_sha256:
                raise ValueError("Structure field prototype checksum mismatch.")
        if self.status == StructureCandidateStatus.PROMOTED and not self.promoted_structure_id:
            raise ValueError("Promoted structure candidates require a structure ID.")
        return self


class StructureObservationReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    plasticity_event_id: str
    observed_candidate_ids: tuple[str, ...]
    proposed_candidates: tuple[StructureCandidateRecord, ...]
    operation: str
    policy_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report(self) -> "StructureObservationReport":
        if tuple(sorted(set(self.observed_candidate_ids))) != self.observed_candidate_ids:
            raise ValueError("Structure observed candidate IDs must be sorted and unique.")
        proposed_ids = tuple(item.candidate_id for item in self.proposed_candidates)
        if tuple(sorted(set(proposed_ids))) != proposed_ids:
            raise ValueError("Structure proposed candidates must be sorted and unique.")
        if self.observed_candidate_ids != proposed_ids:
            raise ValueError("Structure observed candidate index must match proposed candidates.")
        expected = stable_id(
            "structure_observation_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.plasticity_event_id,
            self.observed_candidate_ids,
            tuple(item.model_dump(mode="json") for item in self.proposed_candidates),
            self.operation,
            self.policy_revision,
        )
        if expected != self.report_id:
            raise ValueError("Structure observation report identity checksum mismatch.")
        return self


class StructureObservationEvent(FrozenRecord):
    event_id: str
    report: StructureObservationReport
    active_candidate_ids: tuple[str, ...]
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "StructureObservationEvent":
        if tuple(sorted(set(self.active_candidate_ids))) != self.active_candidate_ids:
            raise ValueError("Structure event candidate IDs must be sorted and unique.")
        expected = stable_id(
            "structure_observation_event",
            self.report.report_id,
            self.active_candidate_ids,
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Structure observation event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Structure observation cannot create semantic truth.")
        return self


class StructureEdgeSnapshot(FrozenRecord):
    association_id: str
    concept_ids: tuple[str, str]
    strength: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_edge_snapshot(self) -> "StructureEdgeSnapshot":
        if tuple(sorted(self.concept_ids)) != self.concept_ids:
            raise ValueError("Structure edge snapshot endpoints must be sorted.")
        if self.concept_ids[0] == self.concept_ids[1]:
            raise ValueError("Structure edge snapshot requires distinct endpoints.")
        expected = stable_id("plasticity_association", *self.concept_ids)
        if expected != self.association_id:
            raise ValueError("Structure edge snapshot association identity mismatch.")
        return self


class StructureRecord(FrozenRecord):
    structure_id: str
    source_candidate_id: str
    opaque_name: str
    member_concept_ids: tuple[str, ...] = Field(min_length=3)
    member_relation_ids: tuple[str, ...] = Field(default_factory=tuple)
    internal_association_ids: tuple[str, ...] = Field(min_length=2)
    internal_edge_snapshots: tuple[StructureEdgeSnapshot, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    quality_at_promotion: StructureQualityVector
    field_state_dim: int = Field(ge=0)
    field_prototype_real: tuple[float, ...] = Field(default_factory=tuple)
    field_prototype_imag: tuple[float, ...] = Field(default_factory=tuple)
    field_prototype_sha256: str = ""
    created_cycle: int = Field(ge=1)
    council_decision_event_id: str
    promotion_policy_revision: int = Field(ge=0)
    lineage_parent_structure_id: str | None = None
    lineage_root_structure_id: str | None = None
    revision_index: int = Field(default=0, ge=0)
    refold_basis_challenge_ids: tuple[str, ...] = Field(default_factory=tuple)
    semantic_label_preinstalled: bool = False

    @model_validator(mode="after")
    def validate_structure(self) -> "StructureRecord":
        for values, label in (
            (self.member_concept_ids, "member concept"),
            (self.member_relation_ids, "member relation"),
            (self.internal_association_ids, "internal association"),
            (self.evidence_refs, "evidence"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Structure {label} values must be sorted and unique.")
        if self.internal_edge_snapshots:
            snapshot_ids = tuple(item.association_id for item in self.internal_edge_snapshots)
            if tuple(sorted(set(snapshot_ids))) != snapshot_ids:
                raise ValueError("Structure edge snapshots must be sorted and unique.")
            if not set(snapshot_ids).issubset(set(self.internal_association_ids)):
                raise ValueError("Structure edge snapshot escaped internal association lineage.")
            if any(
                not set(item.concept_ids).issubset(set(self.member_concept_ids))
                for item in self.internal_edge_snapshots
            ):
                raise ValueError("Structure edge snapshot escaped structure membership.")
        if self.lineage_parent_structure_id is None:
            expected = stable_id("structure", self.source_candidate_id)
            if self.revision_index != 0 or self.refold_basis_challenge_ids:
                raise ValueError("Root earned structures cannot carry refold lineage.")
            if self.lineage_root_structure_id not in {None, self.structure_id}:
                raise ValueError("Root structure lineage root must be itself or omitted.")
        else:
            if self.revision_index < 1:
                raise ValueError("Refolded structures require a positive revision index.")
            if not self.refold_basis_challenge_ids:
                raise ValueError("Refolded structures require challenge lineage.")
            if tuple(sorted(set(self.refold_basis_challenge_ids))) != self.refold_basis_challenge_ids:
                raise ValueError("Refold challenge lineage must be sorted and unique.")
            expected = stable_id(
                "refolded_structure",
                self.lineage_parent_structure_id,
                self.member_concept_ids,
                tuple(item.model_dump(mode="json") for item in self.internal_edge_snapshots),
                self.refold_basis_challenge_ids,
            )
            if self.lineage_root_structure_id is None:
                raise ValueError("Refolded structures require a lineage root.")
        if expected != self.structure_id:
            raise ValueError("Structure identity checksum mismatch.")
        if self.semantic_label_preinstalled:
            raise ValueError("Earned structures may not carry a preinstalled semantic label.")
        if self.field_state_dim:
            if len(self.field_prototype_real) != self.field_state_dim or len(self.field_prototype_imag) != self.field_state_dim:
                raise ValueError("Structure field prototype arrays must match state_dim.")
            expected_hash = hashlib.sha256(
                canonical_json_bytes(
                    {"real": self.field_prototype_real, "imag": self.field_prototype_imag}
                )
            ).hexdigest()
            if expected_hash != self.field_prototype_sha256:
                raise ValueError("Structure field prototype checksum mismatch.")
        return self


class StructurePromotionReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    candidate_id: str
    disposition: StructurePromotionDisposition
    rejection_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    proposed_structure_id: str
    proposed_opaque_name: str
    operation: str
    policy_revision: int = Field(ge=0)
    candidate_snapshot: StructureCandidateRecord

    @model_validator(mode="after")
    def validate_report(self) -> "StructurePromotionReport":
        for values, label in ((self.rejection_codes, "rejection"), (self.evidence_refs, "evidence")):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Structure promotion {label} values must be sorted and unique.")
        expected = stable_id(
            "structure_promotion_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.candidate_id,
            self.disposition.value,
            self.rejection_codes,
            self.evidence_refs,
            self.proposed_structure_id,
            self.proposed_opaque_name,
            self.operation,
            self.policy_revision,
            self.candidate_snapshot.model_dump(mode="json"),
        )
        if expected != self.report_id:
            raise ValueError("Structure promotion report identity checksum mismatch.")
        return self


class StructurePromotionEvent(FrozenRecord):
    event_id: str
    report: StructurePromotionReport
    council_decision_event_id: str
    structure_id: str
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "StructurePromotionEvent":
        expected = stable_id(
            "structure_promotion_event",
            self.report.report_id,
            self.council_decision_event_id,
            self.structure_id,
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Structure promotion event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Structure promotion does not install semantic truth.")
        return self


class CompilationPolicy(BaseModel):
    """Milestone 15 policy for use-driven cognitive compilation.

    A promoted structure may act as one bounded operand when a cue overlaps it.
    If unavailable or no structure qualifies, the same reconstruction operation
    falls back to bounded low-level plastic traversal.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    minimum_trigger_members: int = Field(default=1, ge=1)
    minimum_association_strength: float = Field(default=0.24, ge=0.0, le=1.0)
    maximum_low_level_hops: int = Field(default=4, ge=1)
    maximum_low_level_concepts: int = Field(default=64, ge=3)
    structure_workspace_resource: float = Field(default=0.06, gt=0.0, le=1.0)
    structure_workspace_persistence: int = Field(default=1, ge=1)
    structure_relevance_floor: float = Field(default=0.58, ge=0.0, le=1.0)
    revision: int = Field(default=0, ge=0)


class CompilationCost(FrozenRecord):
    concepts_inspected: int = Field(ge=0)
    associations_traversed: int = Field(ge=0)
    structures_inspected: int = Field(ge=0)
    structure_operands_used: int = Field(ge=0)
    reconstructed_concepts: int = Field(ge=0)
    estimated_workspace_resource: float = Field(ge=0.0)

    @property
    def low_level_work(self) -> int:
        return self.concepts_inspected + self.associations_traversed


class CompilationProbeReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    cue_concept_ids: tuple[str, ...] = Field(min_length=1)
    reconstructed_concept_ids: tuple[str, ...] = Field(min_length=1)
    disposition: CompilationDisposition
    structure_id: str | None = None
    cost: CompilationCost
    baseline_cost: CompilationCost
    compression_gain: float = Field(ge=0.0, le=1.0)
    operation: str = "reconstruct_relational_region"
    policy_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report(self) -> "CompilationProbeReport":
        for values, label in (
            (self.cue_concept_ids, "cue concept"),
            (self.reconstructed_concept_ids, "reconstructed concept"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Compilation {label} IDs must be sorted and unique.")
        if self.disposition == CompilationDisposition.USE_STRUCTURE and not self.structure_id:
            raise ValueError("Compiled reconstruction requires a structure ID.")
        if self.disposition == CompilationDisposition.FALLBACK_LOW_LEVEL and self.structure_id is not None:
            raise ValueError("Low-level reconstruction may not claim a structure ID.")
        expected = stable_id(
            "compilation_probe_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.cue_concept_ids,
            self.reconstructed_concept_ids,
            self.disposition.value,
            self.structure_id,
            self.cost.model_dump(mode="json"),
            self.baseline_cost.model_dump(mode="json"),
            self.compression_gain,
            self.operation,
            self.policy_revision,
        )
        if expected != self.report_id:
            raise ValueError("Compilation probe identity checksum mismatch.")
        return self


class CompilationProbeEvent(FrozenRecord):
    event_id: str
    report: CompilationProbeReport
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "CompilationProbeEvent":
        expected = stable_id(
            "compilation_probe_event",
            self.report.report_id,
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Compilation probe event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Compilation probes cannot create semantic truth.")
        return self


class StructureAvailabilityEvent(FrozenRecord):
    event_id: str
    structure_id: str
    action: StructureAvailabilityAction
    reason: str
    committed_cycle: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_event(self) -> "StructureAvailabilityEvent":
        if not self.reason.strip():
            raise ValueError("Structure availability changes require a reason.")
        expected = stable_id(
            "structure_availability_event",
            self.structure_id,
            self.action.value,
            self.reason.strip(),
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Structure availability event identity checksum mismatch.")
        return self


class StructureInteractionPolicy(BaseModel):
    """Milestone 16 policy for cross-symbolic structure interaction.

    Field retrieval is driven by a continuous, permutation-invariant signature
    of relational form.  A retrieved candidate is not accepted as an analogy
    until an exact symbolic comparison independently verifies the alignment.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    signature_dim: int = Field(default=32, ge=8, le=256)
    maximum_field_candidates: int = Field(default=8, ge=1)
    minimum_field_similarity: float = Field(default=0.90, ge=0.0, le=1.0)
    minimum_symbolic_similarity: float = Field(default=0.90, ge=0.0, le=1.0)
    edge_presence_threshold: float = Field(default=0.20, ge=0.0, le=1.0)
    maximum_exact_members: int = Field(default=8, ge=3, le=9)
    revision: int = Field(default=0, ge=0)


class StructureFieldSignature(FrozenRecord):
    structure_id: str
    feature_values: tuple[float, ...] = Field(min_length=1)
    state_dim: int = Field(ge=1)
    real: tuple[float, ...] = Field(min_length=1)
    imag: tuple[float, ...] = Field(min_length=1)
    sha256: str

    @model_validator(mode="after")
    def validate_signature(self) -> "StructureFieldSignature":
        if len(self.real) != self.state_dim or len(self.imag) != self.state_dim:
            raise ValueError("Structure interaction signature arrays must match state_dim.")
        expected = hashlib.sha256(
            canonical_json_bytes({
                "feature_values": self.feature_values,
                "real": self.real,
                "imag": self.imag,
            })
        ).hexdigest()
        if expected != self.sha256:
            raise ValueError("Structure interaction signature checksum mismatch.")
        return self


class StructureInteractionCandidate(FrozenRecord):
    target_structure_id: str
    field_rank: int = Field(ge=1)
    field_similarity: float = Field(ge=0.0, le=1.0)
    symbolic_similarity: float = Field(ge=0.0, le=1.0)
    member_mapping: tuple[tuple[str, str], ...] = Field(default_factory=tuple)
    disposition: StructureInteractionDisposition

    @model_validator(mode="after")
    def validate_candidate(self) -> "StructureInteractionCandidate":
        left = tuple(pair[0] for pair in self.member_mapping)
        right = tuple(pair[1] for pair in self.member_mapping)
        if len(set(left)) != len(left) or len(set(right)) != len(right):
            raise ValueError("Structure interaction mapping must be one-to-one.")
        return self


class StructureInteractionReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    source_structure_id: str
    source_signature: StructureFieldSignature
    candidates: tuple[StructureInteractionCandidate, ...]
    best_target_structure_id: str | None = None
    operation: str = "cross_symbolic_structure_interaction"
    policy_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report(self) -> "StructureInteractionReport":
        target_ids = tuple(item.target_structure_id for item in self.candidates)
        if len(set(target_ids)) != len(target_ids):
            raise ValueError("Structure interaction targets must be unique.")
        verified = [
            item.target_structure_id for item in self.candidates
            if item.disposition == StructureInteractionDisposition.VERIFIED_ALIGNMENT
        ]
        if self.best_target_structure_id is not None and self.best_target_structure_id not in verified:
            raise ValueError("Best interaction target must be a verified alignment.")
        expected = stable_id(
            "structure_interaction_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.source_structure_id,
            self.source_signature.model_dump(mode="json"),
            tuple(item.model_dump(mode="json") for item in self.candidates),
            self.best_target_structure_id,
            self.operation,
            self.policy_revision,
        )
        if expected != self.report_id:
            raise ValueError("Structure interaction report identity checksum mismatch.")
        return self


class StructureInteractionEvent(FrozenRecord):
    event_id: str
    report: StructureInteractionReport
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "StructureInteractionEvent":
        expected = stable_id(
            "structure_interaction_event",
            self.report.report_id,
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Structure interaction event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Structure interaction cannot create semantic truth.")
        return self



class HierarchyPolicy(BaseModel):
    """Milestone 17 policy for structures whose constituents are earned structures.

    Higher-order objecthood is earned from repeated verified interactions among
    already-promoted structures.  The policy does not provide semantic names or
    category labels; it only specifies when a recurring family of cognitive
    operands is stable enough to become another opaque operand.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    minimum_members: int = Field(default=3, ge=3)
    maximum_members: int = Field(default=8, ge=3)
    minimum_interaction_events: int = Field(default=3, ge=2)
    minimum_pair_coverage: float = Field(default=0.66, ge=0.0, le=1.0)
    minimum_alignment_cohesion: float = Field(default=0.90, ge=0.0, le=1.0)
    minimum_prototype_cohesion: float = Field(default=0.96, ge=0.0, le=1.0)
    minimum_boundary_selectivity: float = Field(default=0.55, ge=0.0, le=1.0)
    minimum_evidence_events: int = Field(default=6, ge=3)
    maximum_candidates_per_cycle: int = Field(default=4, ge=1)
    layered_probe_similarity: float = Field(default=0.985, ge=0.0, le=1.0)
    revision: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_policy(self) -> "HierarchyPolicy":
        if self.maximum_members < self.minimum_members:
            raise ValueError("Hierarchy maximum_members cannot be below minimum_members.")
        return self


class HierarchyQualityVector(FrozenRecord):
    recurrence: float = Field(ge=0.0, le=1.0)
    pair_coverage: float = Field(ge=0.0, le=1.0)
    alignment_cohesion: float = Field(ge=0.0, le=1.0)
    prototype_cohesion: float = Field(ge=0.0, le=1.0)
    boundary_selectivity: float = Field(ge=0.0, le=1.0)
    evidence_diversity: float = Field(ge=0.0, le=1.0)
    causal_utility: float = Field(default=0.0, ge=0.0, le=1.0)


class HierarchyCandidateRecord(FrozenRecord):
    candidate_id: str
    status: HierarchyCandidateStatus
    member_structure_ids: tuple[str, ...] = Field(min_length=3)
    interaction_event_ids: tuple[str, ...] = Field(min_length=1)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    observed_cycles: tuple[int, ...] = Field(min_length=1)
    occurrence_count: int = Field(ge=1)
    created_cycle: int = Field(ge=1)
    updated_cycle: int = Field(ge=1)
    quality: HierarchyQualityVector
    prototype_dim: int = Field(ge=1)
    prototype_real: tuple[float, ...] = Field(min_length=1)
    prototype_imag: tuple[float, ...] = Field(min_length=1)
    prototype_sha256: str
    promoted_layered_structure_id: str | None = None

    @model_validator(mode="after")
    def validate_candidate(self) -> "HierarchyCandidateRecord":
        for values, label in (
            (self.member_structure_ids, "member structure"),
            (self.interaction_event_ids, "interaction event"),
            (self.evidence_refs, "evidence"),
            (self.observed_cycles, "observed cycle"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Hierarchy candidate {label} values must be sorted and unique.")
        expected = stable_id("hierarchy_candidate", self.member_structure_ids)
        if expected != self.candidate_id:
            raise ValueError("Hierarchy candidate identity checksum mismatch.")
        if self.updated_cycle < self.created_cycle:
            raise ValueError("Hierarchy candidate update cannot precede creation.")
        if len(self.prototype_real) != self.prototype_dim or len(self.prototype_imag) != self.prototype_dim:
            raise ValueError("Hierarchy candidate prototype arrays must match prototype_dim.")
        expected_hash = hashlib.sha256(
            canonical_json_bytes({"real": self.prototype_real, "imag": self.prototype_imag})
        ).hexdigest()
        if expected_hash != self.prototype_sha256:
            raise ValueError("Hierarchy candidate prototype checksum mismatch.")
        if self.status == HierarchyCandidateStatus.PROMOTED and not self.promoted_layered_structure_id:
            raise ValueError("Promoted hierarchy candidates require a layered structure ID.")
        return self


class HierarchyObservationReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    latest_interaction_event_id: str
    observed_candidate_ids: tuple[str, ...]
    proposed_candidates: tuple[HierarchyCandidateRecord, ...]
    operation: str
    policy_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report(self) -> "HierarchyObservationReport":
        proposed_ids = tuple(item.candidate_id for item in self.proposed_candidates)
        if self.observed_candidate_ids != proposed_ids:
            raise ValueError("Hierarchy observation candidate index mismatch.")
        if tuple(sorted(set(proposed_ids))) != proposed_ids:
            raise ValueError("Hierarchy observation candidates must be sorted and unique.")
        expected = stable_id(
            "hierarchy_observation_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.latest_interaction_event_id,
            self.observed_candidate_ids,
            tuple(item.model_dump(mode="json") for item in self.proposed_candidates),
            self.operation,
            self.policy_revision,
        )
        if expected != self.report_id:
            raise ValueError("Hierarchy observation report identity checksum mismatch.")
        return self


class HierarchyObservationEvent(FrozenRecord):
    event_id: str
    report: HierarchyObservationReport
    active_candidate_ids: tuple[str, ...]
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "HierarchyObservationEvent":
        if tuple(sorted(set(self.active_candidate_ids))) != self.active_candidate_ids:
            raise ValueError("Hierarchy observation active candidates must be sorted and unique.")
        expected = stable_id(
            "hierarchy_observation_event",
            self.report.report_id,
            self.active_candidate_ids,
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Hierarchy observation event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Hierarchy observation cannot install semantic truth.")
        return self


class LayeredStructureRecord(FrozenRecord):
    layered_structure_id: str
    source_candidate_id: str
    opaque_name: str
    member_structure_ids: tuple[str, ...] = Field(min_length=3)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    quality_at_promotion: HierarchyQualityVector
    prototype_dim: int = Field(ge=1)
    prototype_real: tuple[float, ...] = Field(min_length=1)
    prototype_imag: tuple[float, ...] = Field(min_length=1)
    prototype_sha256: str
    created_cycle: int = Field(ge=1)
    council_decision_event_id: str
    promotion_policy_revision: int = Field(ge=0)
    depth: int = Field(default=2, ge=2)
    semantic_label_preinstalled: bool = False

    @model_validator(mode="after")
    def validate_record(self) -> "LayeredStructureRecord":
        for values, label in (
            (self.member_structure_ids, "member structure"),
            (self.evidence_refs, "evidence"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Layered structure {label} values must be sorted and unique.")
        expected = stable_id("layered_structure", self.source_candidate_id)
        if expected != self.layered_structure_id:
            raise ValueError("Layered structure identity checksum mismatch.")
        if self.semantic_label_preinstalled:
            raise ValueError("Layered earned structures may not carry a semantic label.")
        if len(self.prototype_real) != self.prototype_dim or len(self.prototype_imag) != self.prototype_dim:
            raise ValueError("Layered structure prototype arrays must match prototype_dim.")
        expected_hash = hashlib.sha256(
            canonical_json_bytes({"real": self.prototype_real, "imag": self.prototype_imag})
        ).hexdigest()
        if expected_hash != self.prototype_sha256:
            raise ValueError("Layered structure prototype checksum mismatch.")
        return self


class HierarchyPromotionReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    candidate_id: str
    disposition: HierarchyPromotionDisposition
    rejection_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    proposed_layered_structure_id: str
    proposed_opaque_name: str
    operation: str
    policy_revision: int = Field(ge=0)
    candidate_snapshot: HierarchyCandidateRecord

    @model_validator(mode="after")
    def validate_report(self) -> "HierarchyPromotionReport":
        if tuple(sorted(set(self.rejection_codes))) != self.rejection_codes:
            raise ValueError("Hierarchy promotion rejection codes must be sorted and unique.")
        if tuple(sorted(set(self.evidence_refs))) != self.evidence_refs:
            raise ValueError("Hierarchy promotion evidence refs must be sorted and unique.")
        expected = stable_id(
            "hierarchy_promotion_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.candidate_id,
            self.disposition.value,
            self.rejection_codes,
            self.evidence_refs,
            self.proposed_layered_structure_id,
            self.proposed_opaque_name,
            self.operation,
            self.policy_revision,
            self.candidate_snapshot.model_dump(mode="json"),
        )
        if expected != self.report_id:
            raise ValueError("Hierarchy promotion report identity checksum mismatch.")
        return self


class HierarchyPromotionEvent(FrozenRecord):
    event_id: str
    report: HierarchyPromotionReport
    council_decision_event_id: str
    layered_structure_id: str
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "HierarchyPromotionEvent":
        expected = stable_id(
            "hierarchy_promotion_event",
            self.report.report_id,
            self.council_decision_event_id,
            self.layered_structure_id,
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Hierarchy promotion event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Hierarchy promotion cannot install semantic truth.")
        return self


class LayeredStructureAvailabilityEvent(FrozenRecord):
    event_id: str
    layered_structure_id: str
    action: StructureAvailabilityAction
    reason: str
    committed_cycle: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_event(self) -> "LayeredStructureAvailabilityEvent":
        if not self.reason.strip():
            raise ValueError("Layered structure availability changes require a reason.")
        expected = stable_id(
            "layered_structure_availability_event",
            self.layered_structure_id,
            self.action.value,
            self.reason.strip(),
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Layered structure availability event identity checksum mismatch.")
        return self


class LayeredProbeCost(FrozenRecord):
    layered_prototypes_compared: int = Field(ge=0)
    base_structures_compared: int = Field(ge=0)
    symbolic_verifications: int = Field(ge=0)
    matched_members: int = Field(ge=0)

    @property
    def comparison_work(self) -> int:
        return self.layered_prototypes_compared + self.base_structures_compared + self.symbolic_verifications


class LayeredProbeReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    query_structure_id: str
    disposition: LayeredProbeDisposition
    layered_structure_id: str | None
    matched_structure_ids: tuple[str, ...]
    cost: LayeredProbeCost
    baseline_cost: LayeredProbeCost
    compression_gain: float = Field(ge=0.0, le=1.0)
    operation: str = "recognize_structural_family"
    policy_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report(self) -> "LayeredProbeReport":
        if tuple(sorted(set(self.matched_structure_ids))) != self.matched_structure_ids:
            raise ValueError("Layered probe matches must be sorted and unique.")
        if self.disposition == LayeredProbeDisposition.USE_LAYERED_STRUCTURE and not self.layered_structure_id:
            raise ValueError("Layered probe use requires a layered structure ID.")
        if self.disposition == LayeredProbeDisposition.FALLBACK_MEMBER_SCAN and self.layered_structure_id is not None:
            raise ValueError("Fallback layered probe may not claim a layered structure.")
        expected = stable_id(
            "layered_probe_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.query_structure_id,
            self.disposition.value,
            self.layered_structure_id,
            self.matched_structure_ids,
            self.cost.model_dump(mode="json"),
            self.baseline_cost.model_dump(mode="json"),
            self.compression_gain,
            self.operation,
            self.policy_revision,
        )
        if expected != self.report_id:
            raise ValueError("Layered probe report identity checksum mismatch.")
        return self


class LayeredProbeEvent(FrozenRecord):
    event_id: str
    report: LayeredProbeReport
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "LayeredProbeEvent":
        expected = stable_id("layered_probe_event", self.report.report_id, self.committed_cycle)
        if expected != self.event_id:
            raise ValueError("Layered probe event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Layered probes cannot install semantic truth.")
        return self



class RefoldingPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    minimum_challenge_events: int = Field(default=2, ge=1)
    minimum_combined_confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    minimum_component_members: int = Field(default=3, ge=3)
    minimum_component_edges: int = Field(default=2, ge=1)
    ablate_parent_on_success: bool = True
    revision: int = Field(default=0, ge=0)


class StructuralChallengeObservation(FrozenRecord):
    event_key: str
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    cycle: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_observation(self) -> "StructuralChallengeObservation":
        if tuple(sorted(set(self.evidence_refs))) != self.evidence_refs:
            raise ValueError("Structural challenge evidence refs must be sorted and unique.")
        if not self.event_key.strip():
            raise ValueError("Structural challenge event key cannot be empty.")
        return self


class StructuralChallengeRecord(FrozenRecord):
    challenge_id: str
    structure_id: str
    concept_ids: tuple[str, str]
    observations: tuple[StructuralChallengeObservation, ...] = Field(min_length=1)
    combined_confidence: float = Field(ge=0.0, le=1.0)
    created_cycle: int = Field(ge=1)
    updated_cycle: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_challenge(self) -> "StructuralChallengeRecord":
        if tuple(sorted(self.concept_ids)) != self.concept_ids or self.concept_ids[0] == self.concept_ids[1]:
            raise ValueError("Structural challenge endpoints must be distinct and sorted.")
        expected = stable_id("structural_challenge", self.structure_id, self.concept_ids)
        if expected != self.challenge_id:
            raise ValueError("Structural challenge identity checksum mismatch.")
        keys = tuple(item.event_key for item in self.observations)
        if tuple(sorted(set(keys))) != keys:
            raise ValueError("Structural challenge observations must be sorted and unique by event key.")
        remaining = 1.0
        for item in self.observations:
            remaining *= 1.0 - item.confidence
        expected_confidence = max(0.0, min(1.0, 1.0 - remaining))
        if abs(expected_confidence - self.combined_confidence) > 1e-9:
            raise ValueError("Structural challenge combined confidence mismatch.")
        if self.updated_cycle < self.created_cycle:
            raise ValueError("Structural challenge update cannot precede creation.")
        return self


class RefoldComponentProposal(FrozenRecord):
    proposed_structure_id: str
    proposed_opaque_name: str
    parent_structure_id: str
    lineage_root_structure_id: str
    revision_index: int = Field(ge=1)
    member_concept_ids: tuple[str, ...] = Field(min_length=3)
    internal_association_ids: tuple[str, ...] = Field(min_length=2)
    internal_edge_snapshots: tuple[StructureEdgeSnapshot, ...] = Field(min_length=2)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    quality: StructureQualityVector
    field_state_dim: int = Field(ge=0)
    field_prototype_real: tuple[float, ...] = Field(default_factory=tuple)
    field_prototype_imag: tuple[float, ...] = Field(default_factory=tuple)
    field_prototype_sha256: str = ""
    refold_basis_challenge_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_proposal(self) -> "RefoldComponentProposal":
        for values, label in (
            (self.member_concept_ids, "member concept"),
            (self.internal_association_ids, "internal association"),
            (self.evidence_refs, "evidence"),
            (self.refold_basis_challenge_ids, "challenge"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Refold proposal {label} values must be sorted and unique.")
        snapshot_ids = tuple(item.association_id for item in self.internal_edge_snapshots)
        if tuple(sorted(set(snapshot_ids))) != snapshot_ids:
            raise ValueError("Refold proposal edge snapshots must be sorted and unique.")
        if snapshot_ids != self.internal_association_ids:
            raise ValueError("Refold proposal associations must match frozen edge snapshots exactly.")
        expected = stable_id(
            "refolded_structure",
            self.parent_structure_id,
            self.member_concept_ids,
            tuple(item.model_dump(mode="json") for item in self.internal_edge_snapshots),
            self.refold_basis_challenge_ids,
        )
        if expected != self.proposed_structure_id:
            raise ValueError("Refold proposal structure identity checksum mismatch.")
        if self.field_state_dim == 0:
            if self.field_prototype_real or self.field_prototype_imag or self.field_prototype_sha256:
                raise ValueError("Empty refold field prototype must have no vector/checksum.")
        else:
            if len(self.field_prototype_real) != self.field_state_dim or len(self.field_prototype_imag) != self.field_state_dim:
                raise ValueError("Refold field prototype arrays must match state_dim.")
            expected_hash = hashlib.sha256(
                canonical_json_bytes({"real": self.field_prototype_real, "imag": self.field_prototype_imag})
            ).hexdigest()
            if expected_hash != self.field_prototype_sha256:
                raise ValueError("Refold field prototype checksum mismatch.")
        return self


class StructureRefoldReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    parent_structure_id: str
    disposition: RefoldDisposition
    challenge_ids: tuple[str, ...]
    removed_association_ids: tuple[str, ...]
    proposals: tuple[RefoldComponentProposal, ...]
    evidence_refs: tuple[str, ...]
    rejection_codes: tuple[str, ...]
    operation: str = "refold_structure"
    policy_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report(self) -> "StructureRefoldReport":
        for values, label in (
            (self.challenge_ids, "challenge"),
            (self.removed_association_ids, "removed association"),
            (self.evidence_refs, "evidence"),
            (self.rejection_codes, "rejection"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Refold report {label} values must be sorted and unique.")
        proposed_ids = tuple(item.proposed_structure_id for item in self.proposals)
        if tuple(sorted(set(proposed_ids))) != tuple(sorted(proposed_ids)):
            raise ValueError("Refold report proposed structures must be unique.")
        expected = stable_id(
            "structure_refold_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.parent_structure_id,
            self.disposition.value,
            self.challenge_ids,
            self.removed_association_ids,
            tuple(item.model_dump(mode="json") for item in self.proposals),
            self.evidence_refs,
            self.rejection_codes,
            self.operation,
            self.policy_revision,
        )
        if expected != self.report_id:
            raise ValueError("Structure refold report identity checksum mismatch.")
        return self


class StructureRefoldEvent(FrozenRecord):
    event_id: str
    report: StructureRefoldReport
    council_decision_event_id: str | None = None
    produced_structure_ids: tuple[str, ...] = Field(default_factory=tuple)
    parent_ablated: bool = False
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "StructureRefoldEvent":
        if tuple(sorted(set(self.produced_structure_ids))) != self.produced_structure_ids:
            raise ValueError("Refold event produced structure IDs must be sorted and unique.")
        expected = stable_id(
            "structure_refold_event",
            self.report.report_id,
            self.council_decision_event_id,
            self.produced_structure_ids,
            self.parent_ablated,
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Structure refold event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Refolding cannot install semantic truth.")
        return self

class WorkspacePolicy(BaseModel):
    """Finite-resource policy for the shared developmental present."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    resource_budget: float = Field(default=1.0, gt=0.0)
    max_active_items: int = Field(default=7, ge=1)
    minimum_admission_score: float = Field(default=0.28, ge=0.0, le=1.0)
    broadcast_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    maximum_persistence_cycles: int = Field(default=4, ge=1)
    carry_decay: float = Field(default=0.72, gt=0.0, le=1.0)
    stickiness_weight: float = Field(default=0.08, ge=0.0)
    resource_penalty_weight: float = Field(default=0.08, ge=0.0)
    current_evidence_reserve: float = Field(default=0.25, ge=0.0)
    resonance_budget_fraction: float = Field(default=0.20, ge=0.0, le=1.0)
    evidence_weight: float = Field(default=0.24, ge=0.0)
    relevance_weight: float = Field(default=0.17, ge=0.0)
    prediction_error_weight: float = Field(default=0.14, ge=0.0)
    contradiction_weight: float = Field(default=0.14, ge=0.0)
    action_weight: float = Field(default=0.10, ge=0.0)
    ethics_weight: float = Field(default=0.10, ge=0.0)
    novelty_weight: float = Field(default=0.06, ge=0.0)
    resonance_weight: float = Field(default=0.05, ge=0.0)
    revision: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_workspace_policy(self) -> "WorkspacePolicy":
        positive = (
            self.evidence_weight
            + self.relevance_weight
            + self.prediction_error_weight
            + self.contradiction_weight
            + self.action_weight
            + self.ethics_weight
            + self.novelty_weight
            + self.resonance_weight
        )
        if not math.isfinite(positive) or positive <= 0.0:
            raise ValueError("Workspace score weights require a positive sum.")
        if self.current_evidence_reserve > self.resource_budget:
            raise ValueError("Current-evidence reserve cannot exceed the workspace budget.")
        return self


class WorkspaceSignals(FrozenRecord):
    evidence_grounding: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    prediction_error: float = Field(default=0.0, ge=0.0, le=1.0)
    contradiction_pressure: float = Field(default=0.0, ge=0.0, le=1.0)
    action_value: float = Field(default=0.0, ge=0.0, le=1.0)
    ethical_salience: float = Field(default=0.0, ge=0.0, le=1.0)
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    resonance: float = Field(default=0.0, ge=0.0, le=1.0)


class WorkspaceCandidateInput(FrozenRecord):
    source_kind: WorkspaceSourceKind
    source_ref: str
    label: str
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    resource_request: float = Field(gt=0.0)
    persistence_cycles: int = Field(default=1, ge=1)
    signals: WorkspaceSignals
    operation: str | None = None
    binding_refs: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_candidate(self) -> "WorkspaceCandidateInput":
        if not self.source_ref.strip() or not self.label.strip():
            raise ValueError("Workspace source and label cannot be empty.")
        if tuple(sorted(set(self.evidence_refs))) != self.evidence_refs:
            raise ValueError("Workspace evidence refs must be sorted and unique.")
        if tuple(sorted(set(self.binding_refs))) != self.binding_refs:
            raise ValueError("Workspace binding refs must be sorted and unique.")
        if self.source_kind == WorkspaceSourceKind.AUTHORIZED_ACTION:
            if self.operation is None or not self.operation.strip():
                raise ValueError("Authorized-action candidates require an operation.")
        elif self.operation is not None:
            raise ValueError("Only authorized-action candidates may carry an operation.")
        return self


class WorkspaceScoreComponents(FrozenRecord):
    evidence: float = Field(ge=0.0)
    relevance: float = Field(ge=0.0)
    prediction_error: float = Field(ge=0.0)
    contradiction: float = Field(ge=0.0)
    action: float = Field(ge=0.0)
    ethics: float = Field(ge=0.0)
    novelty: float = Field(ge=0.0)
    resonance: float = Field(ge=0.0)
    stickiness: float = Field(ge=0.0)
    resource_penalty: float = Field(ge=0.0)


class WorkspaceCandidateAssessment(FrozenRecord):
    rank: int = Field(ge=1)
    candidate_id: str
    candidate: WorkspaceCandidateInput
    disposition: WorkspaceDisposition
    raw_score: float = Field(ge=0.0, le=1.0)
    effective_score: float = Field(ge=0.0, le=1.0)
    allocated_resource: float = Field(default=0.0, ge=0.0)
    rejection_codes: tuple[str, ...] = Field(default_factory=tuple)
    components: WorkspaceScoreComponents
    carried_from_item_id: str | None = None


class WorkspaceAdmissionReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    assessments: tuple[WorkspaceCandidateAssessment, ...]
    admitted_candidate_ids: tuple[str, ...]
    suppressed_candidate_ids: tuple[str, ...]
    evicted_item_ids: tuple[str, ...]
    total_allocated_resource: float = Field(ge=0.0)
    resource_budget: float = Field(gt=0.0)
    operation: str
    policy_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report(self) -> "WorkspaceAdmissionReport":
        for values, label in (
            (self.admitted_candidate_ids, "admitted candidate"),
            (self.suppressed_candidate_ids, "suppressed candidate"),
            (self.evicted_item_ids, "evicted item"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Workspace {label} IDs must be sorted and unique.")
        expected = stable_id(
            "workspace_admission_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            tuple(item.model_dump(mode="json") for item in self.assessments),
            self.admitted_candidate_ids,
            self.suppressed_candidate_ids,
            self.evicted_item_ids,
            self.total_allocated_resource,
            self.resource_budget,
            self.operation,
            self.policy_revision,
        )
        if expected != self.report_id:
            raise ValueError("Workspace admission report identity checksum mismatch.")
        return self


class WorkspaceItemRecord(FrozenRecord):
    item_id: str
    candidate_id: str
    source_kind: WorkspaceSourceKind
    source_ref: str
    label: str
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    operation: str | None = None
    binding_refs: tuple[str, ...] = Field(default_factory=tuple)
    allocated_resource: float = Field(gt=0.0)
    raw_score: float = Field(ge=0.0, le=1.0)
    effective_score: float = Field(ge=0.0, le=1.0)
    components: WorkspaceScoreComponents
    signals: WorkspaceSignals
    admitted_cycle: int = Field(ge=1)
    updated_cycle: int = Field(ge=1)
    expires_cycle: int = Field(ge=1)
    admission_report_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_item(self) -> "WorkspaceItemRecord":
        if self.expires_cycle < self.updated_cycle:
            raise ValueError("Workspace item expiry cannot precede its update cycle.")
        return self


class WorkspaceCycleEvent(FrozenRecord):
    event_id: str
    report: WorkspaceAdmissionReport
    active_item_ids: tuple[str, ...]
    broadcast_item_ids: tuple[str, ...]
    suppressed_candidate_ids: tuple[str, ...]
    evicted_item_ids: tuple[str, ...]
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "WorkspaceCycleEvent":
        expected = stable_id(
            "workspace_cycle_event",
            self.report.report_id,
            self.active_item_ids,
            self.broadcast_item_ids,
            self.suppressed_candidate_ids,
            self.evicted_item_ids,
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Workspace cycle event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Workspace cycles cannot create semantic truth.")
        return self


class WorkspaceWritebackEvent(FrozenRecord):
    event_id: str
    item_snapshot: WorkspaceItemRecord
    disposition: WorkspaceWritebackDisposition
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    reason: str
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> "WorkspaceWritebackEvent":
        expected = stable_id(
            "workspace_writeback_event",
            self.item_snapshot.model_dump(mode="json"),
            self.disposition.value,
            self.evidence_refs,
            self.reason,
            self.committed_cycle,
        )
        if expected != self.event_id:
            raise ValueError("Workspace writeback identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Workspace writeback cannot silently create semantic truth.")
        return self


class SensoryPolicy(BaseModel):
    """Nonsemantic translation and temporal event assembly policy."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    synchronization_tolerance_ns: int = Field(default=20_000_000, ge=0)
    maximum_event_gap_ns: int = Field(default=250_000_000, ge=1)
    feature_change_threshold: float = Field(default=0.42, ge=0.0)
    maximum_samples_per_event: int = Field(default=96, ge=1)
    minimum_modalities_per_group: int = Field(default=2, ge=1, le=2)
    vision_signature_side: int = Field(default=8, ge=2, le=32)
    audio_signature_bins: int = Field(default=16, ge=4, le=64)
    translator_revision: int = Field(default=1, ge=1)
    revision: int = Field(default=0, ge=0)


class SensoryArchiveRecord(FrozenRecord):
    archive_id: str
    batch_key: str
    archive_sha256: str
    sample_ids: tuple[str, ...] = Field(min_length=1)
    manifest_sha256: str
    format_revision: int = Field(default=1, ge=1)
    created_cycle: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_archive(self) -> "SensoryArchiveRecord":
        for digest, label in ((self.archive_sha256, "archive"), (self.manifest_sha256, "manifest")):
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError(f"Sensory {label} digest must be lowercase SHA-256.")
        if tuple(sorted(set(self.sample_ids))) != self.sample_ids:
            raise ValueError("Sensory archive sample IDs must be sorted and unique.")
        expected = stable_id(
            "sensory_archive",
            self.batch_key,
            self.manifest_sha256,
            self.sample_ids,
            self.format_revision,
        )
        if expected != self.archive_id:
            raise ValueError("Sensory archive identity checksum mismatch.")
        return self


class SensorySampleRecord(FrozenRecord):
    sample_id: str
    archive_id: str
    archive_member_path: str
    stream_id: str
    sequence_number: int = Field(ge=0)
    timestamp_ns: int = Field(ge=0)
    clock_domain: str
    modality: NativeModality
    media_type: str
    payload_sha256: str
    payload_nbytes: int = Field(ge=1)
    shape: tuple[int, ...] = Field(default_factory=tuple)
    sample_rate_hz: int | None = Field(default=None, ge=1)
    channel_names: tuple[str, ...] = Field(default_factory=tuple)
    feature_vector: tuple[float, ...] = Field(min_length=1)
    native_signature: tuple[float, ...] = Field(min_length=1)
    delta_score: float = Field(ge=0.0)
    previous_sample_id: str | None = None
    observation_evidence_id: str
    translation_evidence_id: str
    committed_cycle: int = Field(ge=1)
    translator_revision: int = Field(ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_sample(self) -> "SensorySampleRecord":
        required = (self.archive_member_path, self.stream_id, self.clock_domain, self.media_type)
        if any(not value.strip() for value in required):
            raise ValueError("Sensory sample identity fields cannot be empty.")
        if len(self.payload_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in self.payload_sha256):
            raise ValueError("Sensory payload digest must be lowercase SHA-256.")
        if any(not math.isfinite(value) for value in (*self.feature_vector, *self.native_signature, self.delta_score)):
            raise ValueError("Sensory numerical values must be finite.")
        if any(value <= 0 for value in self.shape):
            raise ValueError("Sensory sample shape dimensions must be positive.")
        if tuple(item.strip() for item in self.channel_names) != self.channel_names:
            raise ValueError("Sensory channel names must already be stripped.")
        expected = stable_id(
            "sensory_sample",
            self.stream_id,
            self.sequence_number,
            self.timestamp_ns,
            self.clock_domain,
            self.modality.value,
            self.media_type,
            self.payload_sha256,
            self.payload_nbytes,
            self.shape,
            self.sample_rate_hz,
            self.channel_names,
            self.translator_revision,
        )
        if expected != self.sample_id:
            raise ValueError("Sensory sample identity checksum mismatch.")
        return self


class SynchronizationGroupRecord(FrozenRecord):
    group_id: str
    anchor_timestamp_ns: int = Field(ge=0)
    sample_ids: tuple[str, ...] = Field(min_length=1)
    modalities: tuple[NativeModality, ...] = Field(min_length=1)
    maximum_skew_ns: int = Field(ge=0)
    complete: bool
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    summary_vector: tuple[float, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_group(self) -> "SynchronizationGroupRecord":
        if tuple(sorted(set(self.sample_ids))) != self.sample_ids:
            raise ValueError("Synchronization sample IDs must be sorted and unique.")
        modality_values = tuple(sorted(set(item.value for item in self.modalities)))
        if modality_values != tuple(item.value for item in self.modalities):
            raise ValueError("Synchronization modalities must be sorted and unique.")
        if tuple(sorted(set(self.evidence_refs))) != self.evidence_refs:
            raise ValueError("Synchronization evidence refs must be sorted and unique.")
        if any(not math.isfinite(value) for value in self.summary_vector):
            raise ValueError("Synchronization summary values must be finite.")
        expected = stable_id(
            "sensory_sync_group",
            self.anchor_timestamp_ns,
            self.sample_ids,
            tuple(item.value for item in self.modalities),
            self.maximum_skew_ns,
            self.complete,
            self.evidence_refs,
            self.summary_vector,
        )
        if expected != self.group_id:
            raise ValueError("Synchronization group identity checksum mismatch.")
        return self


class TemporalEventRecord(FrozenRecord):
    event_id: str
    start_timestamp_ns: int = Field(ge=0)
    end_timestamp_ns: int = Field(ge=0)
    sample_ids: tuple[str, ...] = Field(min_length=1)
    synchronization_group_ids: tuple[str, ...] = Field(min_length=1)
    modalities: tuple[NativeModality, ...] = Field(min_length=1)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    feature_summary: tuple[float, ...] = Field(min_length=1)
    maximum_change_score: float = Field(ge=0.0)
    boundary_reason: TemporalBoundaryReason
    archive_ids: tuple[str, ...] = Field(min_length=1)
    committed_cycle: int = Field(ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_event(self) -> "TemporalEventRecord":
        if self.end_timestamp_ns < self.start_timestamp_ns:
            raise ValueError("Temporal event end cannot precede start.")
        for values, label in (
            (self.sample_ids, "sample"),
            (self.synchronization_group_ids, "synchronization group"),
            (self.evidence_refs, "evidence"),
            (self.archive_ids, "archive"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Temporal event {label} IDs must be sorted and unique.")
        modality_values = tuple(sorted(set(item.value for item in self.modalities)))
        if modality_values != tuple(item.value for item in self.modalities):
            raise ValueError("Temporal event modalities must be sorted and unique.")
        if any(not math.isfinite(value) for value in (*self.feature_summary, self.maximum_change_score)):
            raise ValueError("Temporal event numerical values must be finite.")
        expected = stable_id(
            "temporal_event",
            self.start_timestamp_ns,
            self.end_timestamp_ns,
            self.sample_ids,
            self.synchronization_group_ids,
            tuple(item.value for item in self.modalities),
            self.evidence_refs,
            self.feature_summary,
            self.maximum_change_score,
            self.boundary_reason.value,
            self.archive_ids,
        )
        if expected != self.event_id:
            raise ValueError("Temporal event identity checksum mismatch.")
        return self


class TemporalEventAssemblyReport(FrozenRecord):
    report_id: str
    kernel_id: str
    cycle: int = Field(ge=0)
    structural_fingerprint: str
    sample_ids: tuple[str, ...] = Field(min_length=1)
    synchronization_groups: tuple[SynchronizationGroupRecord, ...] = Field(min_length=1)
    proposed_events: tuple[TemporalEventRecord, ...] = Field(min_length=1)
    operation: str
    policy_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_report(self) -> "TemporalEventAssemblyReport":
        if tuple(sorted(set(self.sample_ids))) != self.sample_ids:
            raise ValueError("Temporal event report sample IDs must be sorted and unique.")
        expected = stable_id(
            "temporal_event_report",
            self.kernel_id,
            self.cycle,
            self.structural_fingerprint,
            self.sample_ids,
            tuple(item.model_dump(mode="json") for item in self.synchronization_groups),
            tuple(item.model_dump(mode="json") for item in self.proposed_events),
            self.operation,
            self.policy_revision,
        )
        if expected != self.report_id:
            raise ValueError("Temporal event report identity checksum mismatch.")
        return self


class TemporalEventAssemblyEvent(FrozenRecord):
    assembly_event_id: str
    report: TemporalEventAssemblyReport
    committed_event_ids: tuple[str, ...] = Field(min_length=1)
    committed_group_ids: tuple[str, ...] = Field(min_length=1)
    committed_cycle: int = Field(ge=1)
    semantic_mutation_permitted: bool = False

    @model_validator(mode="after")
    def validate_assembly_event(self) -> "TemporalEventAssemblyEvent":
        expected = stable_id(
            "temporal_event_assembly",
            self.report.report_id,
            self.committed_event_ids,
            self.committed_group_ids,
            self.committed_cycle,
        )
        if expected != self.assembly_event_id:
            raise ValueError("Temporal event assembly identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Temporal event assembly cannot create semantic truth.")
        return self


class PerceptualPolicy(BaseModel):
    """Deterministic, nonsemantic visual-region and continuity policy."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    minimum_region_area_fraction: float = Field(default=0.0025, gt=0.0, lt=1.0)
    maximum_region_area_fraction: float = Field(default=0.70, gt=0.0, le=1.0)
    maximum_regions_per_frame: int = Field(default=12, ge=1, le=128)
    saliency_standard_deviations: float = Field(default=0.65, ge=0.0)
    minimum_saliency_threshold: float = Field(default=0.08, ge=0.0, le=1.0)
    morphology_kernel_size: int = Field(default=3, ge=1, le=15)
    appearance_signature_side: int = Field(default=4, ge=2, le=16)
    histogram_bins: int = Field(default=8, ge=4, le=32)
    prior_match_threshold: float = Field(default=0.58, ge=0.0, le=1.0)
    prior_appearance_weight: float = Field(default=0.62, ge=0.0)
    prior_position_weight: float = Field(default=0.38, ge=0.0)
    occlusion_after_missing_frames: int = Field(default=1, ge=1, le=12)
    maximum_tracking_frames: int = Field(default=600, ge=1)
    revision: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_policy(self) -> "PerceptualPolicy":
        if self.minimum_region_area_fraction >= self.maximum_region_area_fraction:
            raise ValueError("Perceptual region area bounds are inverted.")
        if self.prior_appearance_weight + self.prior_position_weight <= 0:
            raise ValueError("Perceptual prior-match weights require a positive sum.")
        if self.morphology_kernel_size % 2 == 0:
            raise ValueError("Perceptual morphology kernel size must be odd.")
        return self


class PerceptualBindingEvent(FrozenRecord):
    event_id: str
    report_id: str
    report_sha256: str
    temporal_event_ids: tuple[str, ...] = Field(min_length=1)
    sample_ids: tuple[str, ...] = Field(min_length=1)
    object_observation_event_ids: tuple[str, ...] = Field(default_factory=tuple)
    object_candidate_ids: tuple[str, ...] = Field(default_factory=tuple)
    committed_cycle: int = Field(ge=1)
    policy_revision: int = Field(ge=0)
    semantic_mutation_permitted: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_event(self) -> "PerceptualBindingEvent":
        for values, label in (
            (self.temporal_event_ids, "temporal event"),
            (self.sample_ids, "sample"),
            (self.object_observation_event_ids, "object observation event"),
            (self.object_candidate_ids, "object candidate"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Perceptual binding {label} IDs must be sorted and unique.")
        if len(self.report_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in self.report_sha256):
            raise ValueError("Perceptual binding report digest must be lowercase SHA-256.")
        expected = stable_id(
            "perceptual_binding_event",
            self.report_id,
            self.report_sha256,
            self.temporal_event_ids,
            self.sample_ids,
            self.object_observation_event_ids,
            self.object_candidate_ids,
            self.committed_cycle,
            self.policy_revision,
        )
        if expected != self.event_id:
            raise ValueError("Perceptual binding event identity checksum mismatch.")
        if self.semantic_mutation_permitted:
            raise ValueError("Perceptual binding cannot create semantic truth.")
        return self


class TransitionRecord(FrozenRecord):
    transition_id: str
    sequence: int = Field(ge=1)
    cycle: int = Field(ge=1)
    operation: str
    command_hash: str
    input_fingerprint: str
    output_fingerprint: str
    input_refs: tuple[str, ...] = Field(default_factory=tuple)
    output_refs: tuple[str, ...] = Field(default_factory=tuple)


class ConceptProposal(FrozenRecord):
    label: str
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("label")
    @classmethod
    def nonempty_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Concept proposal label cannot be empty.")
        return value


class RelationProposal(FrozenRecord):
    source_label: str
    target_label: str
    relation_type: str
    directed: bool = True
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: RelationStatus = RelationStatus.SUPPORTED

    @field_validator("source_label", "target_label", "relation_type")
    @classmethod
    def nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Relation proposal fields cannot be empty.")
        return value


class ClaimProposal(FrozenRecord):
    subject_label: str
    predicate: str
    object_label: str
    polarity: ClaimPolarity = ClaimPolarity.AFFIRMED
    source_class: ClaimSourceClass
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str = ""
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("subject_label", "predicate", "object_label")
    @classmethod
    def nonempty_claim_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Claim proposal fields cannot be empty.")
        return value


class ExperienceCommand(FrozenRecord):
    event_key: str
    source_ref: str
    modality: str
    payload_sha256: str
    feature_vector: tuple[float, ...]
    concept_labels: tuple[str, ...] = Field(default_factory=tuple)
    concept_proposals: tuple[ConceptProposal, ...] = Field(default_factory=tuple)
    relation_proposals: tuple[RelationProposal, ...] = Field(default_factory=tuple)
    claim_proposals: tuple[ClaimProposal, ...] = Field(default_factory=tuple)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    semantic_evidence_kind: EvidenceKind | None = None
    semantic_evidence_details: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_key", "source_ref", "modality")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Experience command text fields cannot be empty.")
        return value

    @field_validator("payload_sha256")
    @classmethod
    def valid_sha256(cls, value: str) -> str:
        value = value.lower()
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("payload_sha256 must be a lowercase SHA-256 digest.")
        return value

    @field_validator("feature_vector")
    @classmethod
    def finite_features(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if not value:
            raise ValueError("feature_vector cannot be empty.")
        if any(not math.isfinite(item) for item in value):
            raise ValueError("feature_vector values must be finite.")
        return value


class KernelState(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    identity: KernelIdentity
    seed: int
    cycle: int = Field(default=0, ge=0)
    event_sequence: int = Field(default=0, ge=0)
    processed_event_keys: dict[str, str] = Field(default_factory=dict)

    evidence: dict[str, EvidenceRecord] = Field(default_factory=dict)
    concepts: dict[str, ConceptRecord] = Field(default_factory=dict)
    relations: dict[str, RelationRecord] = Field(default_factory=dict)
    claims: dict[str, ClaimRecord] = Field(default_factory=dict)
    contradictions: dict[str, ContradictionRecord] = Field(default_factory=dict)
    revisions: list[RevisionRecord] = Field(default_factory=list)
    epistemic_policy: EpistemicPolicy = Field(default_factory=EpistemicPolicy)

    field: FieldState
    ecwf_policy: ECWFPolicy = Field(default_factory=ECWFPolicy)
    field_addresses: dict[str, ConceptFieldAddress] = Field(default_factory=dict)
    resonance_profiles: dict[str, ConceptResonanceProfile] = Field(default_factory=dict)
    resonance_events: list[ResonanceEvent] = Field(default_factory=list)
    shard_policy: ShardPolicy = Field(default_factory=ShardPolicy)
    shards: dict[str, ShardRecord] = Field(default_factory=dict)
    shard_formation_events: list[ShardFormationEvent] = Field(default_factory=list)
    shard_bridges: dict[str, ShardBridgeRecord] = Field(default_factory=dict)
    routing_events: list[RoutingEvent] = Field(default_factory=list)
    active_shard_id: str = "root"
    object_policy: ObjecthoodPolicy = Field(default_factory=ObjecthoodPolicy)
    object_observations: dict[str, ObjectObservationRecord] = Field(default_factory=dict)
    object_candidates: dict[str, ObjectCandidateRecord] = Field(default_factory=dict)
    object_observation_events: list[ObjectObservationEvent] = Field(default_factory=list)
    object_promotion_events: list[ObjectPromotionEvent] = Field(default_factory=list)
    sensory_policy: SensoryPolicy = Field(default_factory=SensoryPolicy)
    sensory_archives: dict[str, SensoryArchiveRecord] = Field(default_factory=dict)
    sensory_samples: dict[str, SensorySampleRecord] = Field(default_factory=dict)
    synchronization_groups: dict[str, SynchronizationGroupRecord] = Field(default_factory=dict)
    temporal_events: dict[str, TemporalEventRecord] = Field(default_factory=dict)
    temporal_event_assembly_events: list[TemporalEventAssemblyEvent] = Field(default_factory=list)
    perceptual_policy: PerceptualPolicy = Field(default_factory=PerceptualPolicy)
    perceptual_binding_events: list[PerceptualBindingEvent] = Field(default_factory=list)
    plasticity_policy: PlasticityPolicy = Field(default_factory=PlasticityPolicy)
    plasticity_associations: dict[str, PlasticityAssociationRecord] = Field(default_factory=dict)
    plasticity_events: list[PlasticityEvent] = Field(default_factory=list)
    structure_policy: StructurePolicy = Field(default_factory=StructurePolicy)
    structure_candidates: dict[str, StructureCandidateRecord] = Field(default_factory=dict)
    structure_observation_events: list[StructureObservationEvent] = Field(default_factory=list)
    structures: dict[str, StructureRecord] = Field(default_factory=dict)
    structure_promotion_events: list[StructurePromotionEvent] = Field(default_factory=list)
    compilation_policy: CompilationPolicy = Field(default_factory=CompilationPolicy)
    ablated_structure_ids: tuple[str, ...] = Field(default_factory=tuple)
    structure_availability_events: list[StructureAvailabilityEvent] = Field(default_factory=list)
    compilation_probe_events: list[CompilationProbeEvent] = Field(default_factory=list)
    structure_interaction_policy: StructureInteractionPolicy = Field(default_factory=StructureInteractionPolicy)
    structure_interaction_events: list[StructureInteractionEvent] = Field(default_factory=list)
    hierarchy_policy: HierarchyPolicy = Field(default_factory=HierarchyPolicy)
    hierarchy_candidates: dict[str, HierarchyCandidateRecord] = Field(default_factory=dict)
    hierarchy_observation_events: list[HierarchyObservationEvent] = Field(default_factory=list)
    layered_structures: dict[str, LayeredStructureRecord] = Field(default_factory=dict)
    hierarchy_promotion_events: list[HierarchyPromotionEvent] = Field(default_factory=list)
    ablated_layered_structure_ids: tuple[str, ...] = Field(default_factory=tuple)
    layered_structure_availability_events: list[LayeredStructureAvailabilityEvent] = Field(default_factory=list)
    layered_probe_events: list[LayeredProbeEvent] = Field(default_factory=list)
    refolding_policy: RefoldingPolicy = Field(default_factory=RefoldingPolicy)
    structural_challenges: dict[str, StructuralChallengeRecord] = Field(default_factory=dict)
    structure_refold_events: list[StructureRefoldEvent] = Field(default_factory=list)
    workspace_policy: WorkspacePolicy = Field(default_factory=WorkspacePolicy)
    workspace_items: dict[str, WorkspaceItemRecord] = Field(default_factory=dict)
    workspace_cycle_events: list[WorkspaceCycleEvent] = Field(default_factory=list)
    workspace_writeback_events: list[WorkspaceWritebackEvent] = Field(default_factory=list)
    lineage: LineageState = Field(default_factory=LineageState)
    governance: GovernanceState = Field(default_factory=GovernanceState)
    attention_candidates: dict[str, AttentionCandidate] = Field(default_factory=dict)
    council_decisions: list[CouncilDecisionEvent] = Field(default_factory=list)
    governance_outcomes: list[GovernanceOutcomeRecord] = Field(default_factory=list)
    transitions: list[TransitionRecord] = Field(default_factory=list)

    def canonical_payload(self, *, include_transitions: bool = True) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        if not include_transitions:
            payload["transitions"] = []
        return payload

    def fingerprint(self, *, include_transitions: bool = True) -> str:
        return hashlib.sha256(
            canonical_json_bytes(
                self.canonical_payload(include_transitions=include_transitions)
            )
        ).hexdigest()
