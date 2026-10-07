"""Durable fixed-policy replication preregistration for Contradiction.

The v0.43 cohort falsified a bounded cardinality-only rule, but its normal
contexts all produced the same downstream outcome.  This opt-in v0.44 layer
does not execute another cohort.  It freezes the next experiment first:

* two canonically disjoint contexts for each actually constructible Lens
  cardinality profile;
* one low-background and one high-background native structure state per
  profile;
* a single trace-count-to-workspace policy shared by every context; and
* two profile-group-held-out partitions.

The planned observer may later consume only the structures collection's
``after_record_count`` from actual counterfactual traces.  At preregistration
time no trace, outcome, rule fit, predictive discrimination, or resolution is
observed.  The sidecar grants no truth, promotion, policy-rewrite, or
canonical-write authority.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

try:  # pragma: no cover - non-POSIX operation is rejected explicitly.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .contradiction_dimension_criterion import (
    ContradictionLensOutputDimension,
    ContradictionProjectionCardinalityProfile,
)
from .contradiction_downstream_outcome import (
    ContradictionDownstreamOutcomeDisposition,
)
from .contradiction_prediction_audit import (
    CONTRADICTION_PREDICTION_PROFILE_MAPPING,
    ContradictionCardinalityPredictionPolicy,
)
from .contradiction_prediction_cohort import (
    CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES,
    ContradictionPredictionCohortRuleFamily,
)
from .contradiction_trial_controls import ContradictionLensTrialPairContext
from .equivalence import EquivalenceLensSystem


CONTRADICTION_PREDICTION_REPLICATION_VERSION = (
    "contradiction_prediction_replication_v0.44"
)
CONTRADICTION_PREDICTION_REPLICATION_PREREGISTRATION_FORMAT = (
    "verdant-contradiction-prediction-replication-preregistration-v1"
)
CONTRADICTION_PREDICTION_REPLICATION_TRACE_FIELD = (
    "collection_deltas.structures.after_record_count"
)
CONTRADICTION_PREDICTION_REPLICATION_CONTEXT_COUNT = 4
_MAX_SIDECAR_BYTES = 256 * 1024 * 1024


class ContradictionPredictionReplicationIntegrityError(RuntimeError):
    """Raised when replication preregistration loses isolation or lineage."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value: Any) -> str:
    return _sha(canonical_json_bytes(value))


def _is_sha(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _json(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list)):
        return tuple(_json(item) for item in value)
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    return value


def _payload(values: dict[str, Any]) -> dict[str, Any]:
    return {key: _json(value) for key, value in values.items()}


def _declared_counts(pair: ContradictionLensTrialPairContext) -> tuple[int, int]:
    roots = pair.held_out.controlled_context.functional_context.query_source_roots
    return tuple(
        sum(bool(set(query).intersection(candidate)) for candidate in roots)
        for query in roots
    )


def _profile(counts: tuple[int, int]) -> ContradictionProjectionCardinalityProfile:
    if counts == (1, 1):
        return ContradictionProjectionCardinalityProfile.SINGLETON_PER_ROUTE
    if counts[0] == counts[1]:
        return (
            ContradictionProjectionCardinalityProfile.EQUAL_MULTI_REFERENCE_ROUTES
        )
    return ContradictionProjectionCardinalityProfile.ASYMMETRIC_ROUTE_CARDINALITY


class ContradictionPredictionReplicationTraceRole(str, Enum):
    """Pre-outcome trace-background role, not an observed outcome label."""

    LOW_TRACE_CONTROL = "low_trace_control"
    HIGH_TRACE_VARIATION = "high_trace_variation"

    @property
    def preexisting_structure_count(self) -> int:
        return 0 if self is self.LOW_TRACE_CONTROL else 1


class ContradictionPredictionReplicationOutcomePolicy(BaseModel):
    """One fixed mapping to be evaluated only after durable preregistration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = CONTRADICTION_PREDICTION_REPLICATION_VERSION
    trace_field: str = CONTRADICTION_PREDICTION_REPLICATION_TRACE_FIELD
    pressure_per_structure: float = Field(default=0.5, ge=0.0, le=1.0)
    maximum_pressure: float = Field(default=1.0, ge=0.0, le=1.0)
    candidate_resource_fraction: float = Field(default=0.10, gt=0.0, le=1.0)
    persistence_cycles: int = Field(default=1, ge=1, le=1)
    evidence_grounding_signal: float = Field(default=1.0, ge=0.0, le=1.0)
    minimum_admission_score: float = Field(default=0.35, ge=0.0, le=1.0)
    expected_treatment_added_structure_count: int = Field(default=1, ge=1, le=1)
    permitted_preexisting_structure_counts: tuple[int, int] = (0, 1)
    count_only_mapping: bool = True
    identical_policy_required_across_contexts: bool = True
    threshold_variation_permitted: bool = False
    added_record_identities_permitted: bool = False
    lens_projection_inputs_permitted: bool = False
    functional_disposition_input_permitted: bool = False
    trace_role_as_outcome_label_permitted: bool = False

    @model_validator(mode="after")
    def validate_policy(
        self,
    ) -> "ContradictionPredictionReplicationOutcomePolicy":
        if (
            self.policy_version != CONTRADICTION_PREDICTION_REPLICATION_VERSION
            or self.trace_field
            != CONTRADICTION_PREDICTION_REPLICATION_TRACE_FIELD
            or self.pressure_per_structure != 0.5
            or self.maximum_pressure != 1.0
            or self.candidate_resource_fraction != 0.10
            or self.persistence_cycles != 1
            or self.evidence_grounding_signal != 1.0
            or self.minimum_admission_score != 0.35
            or self.expected_treatment_added_structure_count != 1
            or self.permitted_preexisting_structure_counts != (0, 1)
            or not self.count_only_mapping
            or not self.identical_policy_required_across_contexts
            or self.threshold_variation_permitted
            or self.added_record_identities_permitted
            or self.lens_projection_inputs_permitted
            or self.functional_disposition_input_permitted
            or self.trace_role_as_outcome_label_permitted
        ):
            raise ValueError("Replication outcome policy crossed its fixed grammar.")
        return self

    def fingerprint(self) -> str:
        return _digest(self.model_dump(mode="json"))


class ContradictionPredictionReplicationRuleFamily(BaseModel):
    """Bounded profile-only rule family frozen before replication execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = CONTRADICTION_PREDICTION_REPLICATION_VERSION
    selected_dimension: ContradictionLensOutputDimension = (
        ContradictionLensOutputDimension.ACTIVATED_REFERENCE_CARDINALITY_PROFILE
    )
    training_profile_group_count: int = Field(default=1, ge=1, le=1)
    evaluation_profile_group_count: int = Field(default=1, ge=1, le=1)
    contexts_per_profile_group: int = Field(default=2, ge=2, le=2)
    unseen_profile_default: ContradictionDownstreamOutcomeDisposition = (
        ContradictionDownstreamOutcomeDisposition.VALID_NULL
    )
    cardinality_only: bool = True
    trace_background_role_input_permitted: bool = False
    trace_field_input_permitted: bool = False
    evaluation_outcome_input_permitted: bool = False
    negative_control_input_permitted: bool = False
    post_execution_tuning_permitted: bool = False

    @model_validator(mode="after")
    def validate_rule_family(
        self,
    ) -> "ContradictionPredictionReplicationRuleFamily":
        if (
            self.policy_version != CONTRADICTION_PREDICTION_REPLICATION_VERSION
            or self.selected_dimension
            != ContradictionLensOutputDimension.ACTIVATED_REFERENCE_CARDINALITY_PROFILE
            or self.training_profile_group_count != 1
            or self.evaluation_profile_group_count != 1
            or self.contexts_per_profile_group != 2
            or self.unseen_profile_default
            != ContradictionDownstreamOutcomeDisposition.VALID_NULL
            or not self.cardinality_only
            or self.trace_background_role_input_permitted
            or self.trace_field_input_permitted
            or self.evaluation_outcome_input_permitted
            or self.negative_control_input_permitted
            or self.post_execution_tuning_permitted
        ):
            raise ValueError("Replication rule family crossed its fixed grammar.")
        return self

    def fingerprint(self) -> str:
        return _digest(self.model_dump(mode="json"))


class ContradictionPredictionReplicationContext(FrozenRecord):
    """One canonical pair and its pre-outcome trace-background declaration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    context_id: str
    context_version: str = CONTRADICTION_PREDICTION_REPLICATION_VERSION
    trace_role: ContradictionPredictionReplicationTraceRole
    pair_context: ContradictionLensTrialPairContext
    pair_context_ref: str
    calibration_canonical_fingerprint: str
    held_out_canonical_fingerprint: str
    lens_fingerprint: str
    expected_cardinalities: tuple[int, int]
    expected_profile: ContradictionProjectionCardinalityProfile
    calibration_claim_refs: tuple[str, str]
    calibration_evidence_refs: tuple[str, ...]
    evaluation_claim_refs: tuple[str, str]
    evaluation_evidence_refs: tuple[str, ...]
    canonical_preexisting_structure_count: int = Field(ge=0, le=1)
    background_structure_refs: tuple[str, ...]
    background_structure_sha256s: tuple[str, ...]
    background_evidence_refs: tuple[str, ...]
    background_council_decision_refs: tuple[str, ...]
    background_promotion_event_refs: tuple[str, ...]
    declared_baseline_after_structure_count: int = Field(ge=0, le=1)
    declared_treatment_after_structure_count: int = Field(ge=1, le=2)
    declared_treatment_added_structure_count: int = Field(default=1, ge=1, le=1)
    native_structure_lineage_verified: bool = True
    profile_source_topology_predeclared: bool = True
    actual_replication_trace_observed: bool = False
    downstream_outcome_observed: bool = False
    predictive_discrimination_observed: bool = False
    dimensional_separation_observed: bool = False
    authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        pair_context: ContradictionLensTrialPairContext,
        calibration_kernel: VerdantKernel,
        held_out_kernel: VerdantKernel,
        lenses: EquivalenceLensSystem,
        *,
        trace_role: ContradictionPredictionReplicationTraceRole,
    ) -> "ContradictionPredictionReplicationContext":
        pair = ContradictionLensTrialPairContext.model_validate(
            pair_context.model_dump(mode="json")
        )
        if (
            calibration_kernel.fingerprint()
            != pair.calibration.canonical_checkpoint_fingerprint
            or held_out_kernel.fingerprint()
            != pair.held_out.canonical_checkpoint_fingerprint
        ):
            raise ValueError("Replication context received a foreign canonical kernel.")
        if lenses.fingerprint() != pair.lens_fingerprint:
            raise ValueError("Replication context received a foreign Lens sidecar.")
        expected_count = trace_role.preexisting_structure_count
        structures = tuple(
            sorted(held_out_kernel.state.structures.values(), key=lambda item: item.structure_id)
        )
        if len(structures) != expected_count:
            raise ValueError("Replication trace role disagrees with canonical structures.")
        promotion_by_structure = {
            event.structure_id: event
            for event in held_out_kernel.state.structure_promotion_events
        }
        for structure in structures:
            event = promotion_by_structure.get(structure.structure_id)
            if (
                event is None
                or event.council_decision_event_id
                != structure.council_decision_event_id
                or event.semantic_mutation_permitted
                or structure.semantic_label_preinstalled
                or any(
                    evidence_ref not in held_out_kernel.state.evidence
                    for evidence_ref in structure.evidence_refs
                )
            ):
                raise ValueError("Replication background lacks native structure lineage.")
        counts = _declared_counts(pair)
        values = {
            "context_version": CONTRADICTION_PREDICTION_REPLICATION_VERSION,
            "trace_role": trace_role,
            "pair_context": pair,
            "pair_context_ref": pair.pair_id,
            "calibration_canonical_fingerprint": calibration_kernel.fingerprint(),
            "held_out_canonical_fingerprint": held_out_kernel.fingerprint(),
            "lens_fingerprint": lenses.fingerprint(),
            "expected_cardinalities": counts,
            "expected_profile": _profile(counts),
            "calibration_claim_refs": pair.calibration.claim_refs,
            "calibration_evidence_refs": pair.calibration.protected_evidence_refs,
            "evaluation_claim_refs": pair.held_out.claim_refs,
            "evaluation_evidence_refs": pair.held_out.protected_evidence_refs,
            "canonical_preexisting_structure_count": expected_count,
            "background_structure_refs": tuple(item.structure_id for item in structures),
            "background_structure_sha256s": tuple(
                _digest(item.model_dump(mode="json")) for item in structures
            ),
            "background_evidence_refs": tuple(
                sorted(
                    {
                        evidence_ref
                        for item in structures
                        for evidence_ref in item.evidence_refs
                    }
                )
            ),
            "background_council_decision_refs": tuple(
                item.council_decision_event_id for item in structures
            ),
            "background_promotion_event_refs": tuple(
                promotion_by_structure[item.structure_id].event_id
                for item in structures
            ),
            "declared_baseline_after_structure_count": expected_count,
            "declared_treatment_after_structure_count": expected_count + 1,
            "declared_treatment_added_structure_count": 1,
            "native_structure_lineage_verified": True,
            "profile_source_topology_predeclared": True,
            "actual_replication_trace_observed": False,
            "downstream_outcome_observed": False,
            "predictive_discrimination_observed": False,
            "dimensional_separation_observed": False,
            "authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["context_id"] = stable_id(
            "contradiction_prediction_replication_context", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_context(self) -> "ContradictionPredictionReplicationContext":
        pair = self.pair_context
        expected_count = self.trace_role.preexisting_structure_count
        refs = (
            self.background_structure_refs,
            self.background_structure_sha256s,
            self.background_council_decision_refs,
            self.background_promotion_event_refs,
        )
        if (
            self.context_version != CONTRADICTION_PREDICTION_REPLICATION_VERSION
            or self.pair_context_ref != pair.pair_id
            or self.calibration_canonical_fingerprint
            != pair.calibration.canonical_checkpoint_fingerprint
            or self.held_out_canonical_fingerprint
            != pair.held_out.canonical_checkpoint_fingerprint
            or self.lens_fingerprint != pair.lens_fingerprint
            or self.expected_cardinalities != _declared_counts(pair)
            or self.expected_profile != _profile(self.expected_cardinalities)
            or self.calibration_claim_refs != pair.calibration.claim_refs
            or self.calibration_evidence_refs
            != pair.calibration.protected_evidence_refs
            or self.evaluation_claim_refs != pair.held_out.claim_refs
            or self.evaluation_evidence_refs
            != pair.held_out.protected_evidence_refs
            or self.canonical_preexisting_structure_count != expected_count
            or any(len(items) != expected_count for items in refs)
            or any(not _is_sha(item) for item in self.background_structure_sha256s)
            or bool(self.background_evidence_refs) != bool(expected_count)
            or not set(self.background_evidence_refs).isdisjoint(
                (*self.calibration_evidence_refs, *self.evaluation_evidence_refs)
            )
            or self.declared_baseline_after_structure_count != expected_count
            or self.declared_treatment_after_structure_count != expected_count + 1
            or self.declared_treatment_added_structure_count != 1
        ):
            raise ValueError("Replication context changed its canonical trace plan.")
        for items in (
            self.calibration_claim_refs,
            self.calibration_evidence_refs,
            self.evaluation_claim_refs,
            self.evaluation_evidence_refs,
            self.background_structure_refs,
            self.background_evidence_refs,
            self.background_council_decision_refs,
            self.background_promotion_event_refs,
        ):
            if tuple(sorted(set(items))) != items:
                raise ValueError("Replication context refs must be sorted and unique.")
        if (
            not self.native_structure_lineage_verified
            or not self.profile_source_topology_predeclared
            or self.actual_replication_trace_observed
            or self.downstream_outcome_observed
            or self.predictive_discrimination_observed
            or self.dimensional_separation_observed
            or self.authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Replication context crossed its claim boundary.")
        expected = stable_id(
            "contradiction_prediction_replication_context",
            self.model_dump(mode="json", exclude={"context_id"}),
        )
        if self.context_id != expected:
            raise ValueError("Replication-context checksum mismatch.")
        return self


class ContradictionPredictionReplicationFold(FrozenRecord):
    """One profile-group-held-out partition frozen before outcomes exist."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fold_id: str
    fold_version: str = CONTRADICTION_PREDICTION_REPLICATION_VERSION
    training_profile: ContradictionProjectionCardinalityProfile
    evaluation_profile: ContradictionProjectionCardinalityProfile
    training_context_refs: tuple[str, str]
    evaluation_context_refs: tuple[str, str]
    profile_group_held_out: bool = True
    trace_roles_withheld_from_rule: bool = True
    evaluation_outcomes_withheld: bool = True

    @classmethod
    def build(
        cls,
        *,
        training_profile: ContradictionProjectionCardinalityProfile,
        evaluation_profile: ContradictionProjectionCardinalityProfile,
        training_context_refs: Sequence[str],
        evaluation_context_refs: Sequence[str],
    ) -> "ContradictionPredictionReplicationFold":
        training = tuple(sorted(training_context_refs))
        evaluation = tuple(sorted(evaluation_context_refs))
        if len(training) != 2 or len(evaluation) != 2:
            raise ValueError("Replication fold requires two contexts per profile.")
        values = {
            "fold_version": CONTRADICTION_PREDICTION_REPLICATION_VERSION,
            "training_profile": training_profile,
            "evaluation_profile": evaluation_profile,
            "training_context_refs": training,
            "evaluation_context_refs": evaluation,
            "profile_group_held_out": True,
            "trace_roles_withheld_from_rule": True,
            "evaluation_outcomes_withheld": True,
        }
        values["fold_id"] = stable_id(
            "contradiction_prediction_replication_fold", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_fold(self) -> "ContradictionPredictionReplicationFold":
        if (
            self.fold_version != CONTRADICTION_PREDICTION_REPLICATION_VERSION
            or self.training_profile == self.evaluation_profile
            or tuple(sorted(set(self.training_context_refs)))
            != self.training_context_refs
            or tuple(sorted(set(self.evaluation_context_refs)))
            != self.evaluation_context_refs
            or len(self.training_context_refs) != 2
            or len(self.evaluation_context_refs) != 2
            or not set(self.training_context_refs).isdisjoint(
                self.evaluation_context_refs
            )
            or not self.profile_group_held_out
            or not self.trace_roles_withheld_from_rule
            or not self.evaluation_outcomes_withheld
        ):
            raise ValueError("Replication fold crossed its fixed partition.")
        expected = stable_id(
            "contradiction_prediction_replication_fold",
            self.model_dump(mode="json", exclude={"fold_id"}),
        )
        if self.fold_id != expected:
            raise ValueError("Replication-fold checksum mismatch.")
        return self


class ContradictionPredictionReplicationDeclaration(FrozenRecord):
    """Four-context experiment design frozen before any replication trace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    declaration_id: str
    declaration_version: str = CONTRADICTION_PREDICTION_REPLICATION_VERSION
    contexts: tuple[ContradictionPredictionReplicationContext, ...]
    context_refs: tuple[str, ...]
    required_profiles: tuple[
        ContradictionProjectionCardinalityProfile,
        ContradictionProjectionCardinalityProfile,
    ] = CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES
    folds: tuple[
        ContradictionPredictionReplicationFold,
        ContradictionPredictionReplicationFold,
    ]
    outcome_policy: ContradictionPredictionReplicationOutcomePolicy
    outcome_policy_sha256: str
    rule_family: ContradictionPredictionReplicationRuleFamily
    rule_family_sha256: str
    preserved_v042_policy: ContradictionCardinalityPredictionPolicy
    preserved_v042_mapping: tuple[
        tuple[
            ContradictionProjectionCardinalityProfile,
            ContradictionDownstreamOutcomeDisposition,
        ],
        ...,
    ] = CONTRADICTION_PREDICTION_PROFILE_MAPPING
    preserved_v043_rule_family: ContradictionPredictionCohortRuleFamily
    durable_before_execution: bool = True
    disjoint_evidence_required: bool = True
    native_trace_variation_required: bool = True
    identical_threshold_required: bool = True
    untouched_low_trace_control_required: bool = True
    group_heldout_required: bool = True
    preserve_prior_falsifications_required: bool = True
    replication_executed: bool = False
    outcomes_observed: bool = False
    predictive_discrimination_observed: bool = False
    dimensional_separation_observed: bool = False
    independent_held_out_replication_observed: bool = False
    authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        contexts: Sequence[ContradictionPredictionReplicationContext],
    ) -> "ContradictionPredictionReplicationDeclaration":
        if len(contexts) != CONTRADICTION_PREDICTION_REPLICATION_CONTEXT_COUNT:
            raise ValueError("Replication preregistration requires four contexts.")
        declared = tuple(
            sorted(
                (
                    ContradictionPredictionReplicationContext.model_validate(
                        item.model_dump(mode="json")
                    )
                    for item in contexts
                ),
                key=lambda item: item.context_id,
            )
        )
        by_profile = {
            profile: tuple(
                item for item in declared if item.expected_profile == profile
            )
            for profile in CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES
        }
        folds = tuple(
            ContradictionPredictionReplicationFold.build(
                training_profile=training,
                evaluation_profile=evaluation,
                training_context_refs=tuple(
                    item.context_id for item in by_profile[training]
                ),
                evaluation_context_refs=tuple(
                    item.context_id for item in by_profile[evaluation]
                ),
            )
            for training, evaluation in (
                (
                    CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES[0],
                    CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES[1],
                ),
                (
                    CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES[1],
                    CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES[0],
                ),
            )
        )
        policy = ContradictionPredictionReplicationOutcomePolicy()
        family = ContradictionPredictionReplicationRuleFamily()
        values = {
            "declaration_version": CONTRADICTION_PREDICTION_REPLICATION_VERSION,
            "contexts": declared,
            "context_refs": tuple(item.context_id for item in declared),
            "required_profiles": CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES,
            "folds": folds,
            "outcome_policy": policy,
            "outcome_policy_sha256": policy.fingerprint(),
            "rule_family": family,
            "rule_family_sha256": family.fingerprint(),
            "preserved_v042_policy": ContradictionCardinalityPredictionPolicy(),
            "preserved_v042_mapping": CONTRADICTION_PREDICTION_PROFILE_MAPPING,
            "preserved_v043_rule_family": ContradictionPredictionCohortRuleFamily(),
            "durable_before_execution": True,
            "disjoint_evidence_required": True,
            "native_trace_variation_required": True,
            "identical_threshold_required": True,
            "untouched_low_trace_control_required": True,
            "group_heldout_required": True,
            "preserve_prior_falsifications_required": True,
            "replication_executed": False,
            "outcomes_observed": False,
            "predictive_discrimination_observed": False,
            "dimensional_separation_observed": False,
            "independent_held_out_replication_observed": False,
            "authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["declaration_id"] = stable_id(
            "contradiction_prediction_replication_declaration", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_declaration(
        self,
    ) -> "ContradictionPredictionReplicationDeclaration":
        if (
            self.declaration_version
            != CONTRADICTION_PREDICTION_REPLICATION_VERSION
            or len(self.contexts) != CONTRADICTION_PREDICTION_REPLICATION_CONTEXT_COUNT
            or tuple(sorted(self.contexts, key=lambda item: item.context_id))
            != self.contexts
            or self.context_refs
            != tuple(item.context_id for item in self.contexts)
            or len(set(self.context_refs)) != len(self.context_refs)
            or self.required_profiles
            != CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES
            or self.outcome_policy_sha256 != self.outcome_policy.fingerprint()
            or self.rule_family_sha256 != self.rule_family.fingerprint()
            or self.preserved_v042_mapping != CONTRADICTION_PREDICTION_PROFILE_MAPPING
            or self.preserved_v042_policy.profile_mapping
            != CONTRADICTION_PREDICTION_PROFILE_MAPPING
            or self.preserved_v043_rule_family
            != ContradictionPredictionCohortRuleFamily()
        ):
            raise ValueError("Replication declaration changed its frozen grammar.")
        by_profile = {
            profile: tuple(
                item for item in self.contexts if item.expected_profile == profile
            )
            for profile in self.required_profiles
        }
        for profile, contexts in by_profile.items():
            if len(contexts) != 2 or {
                item.trace_role for item in contexts
            } != set(ContradictionPredictionReplicationTraceRole):
                raise ValueError(
                    f"Replication profile {profile.value} lacks its matched roles."
                )
        expected_folds = tuple(
            ContradictionPredictionReplicationFold.build(
                training_profile=training,
                evaluation_profile=evaluation,
                training_context_refs=tuple(
                    item.context_id for item in by_profile[training]
                ),
                evaluation_context_refs=tuple(
                    item.context_id for item in by_profile[evaluation]
                ),
            )
            for training, evaluation in (
                (self.required_profiles[0], self.required_profiles[1]),
                (self.required_profiles[1], self.required_profiles[0]),
            )
        )
        if self.folds != expected_folds:
            raise ValueError("Replication declaration changed group-held-out folds.")
        checkpoints = {
            fingerprint
            for item in self.contexts
            for fingerprint in (
                item.calibration_canonical_fingerprint,
                item.held_out_canonical_fingerprint,
            )
        }
        if len(checkpoints) != 2 * len(self.contexts):
            raise ValueError("Replication contexts reuse canonical checkpoints.")
        for index, left in enumerate(self.contexts):
            left_claims = set(
                (*left.calibration_claim_refs, *left.evaluation_claim_refs)
            )
            left_evidence = set(
                (
                    *left.calibration_evidence_refs,
                    *left.evaluation_evidence_refs,
                    *left.background_evidence_refs,
                )
            )
            for right in self.contexts[index + 1 :]:
                right_claims = set(
                    (*right.calibration_claim_refs, *right.evaluation_claim_refs)
                )
                right_evidence = set(
                    (
                        *right.calibration_evidence_refs,
                        *right.evaluation_evidence_refs,
                        *right.background_evidence_refs,
                    )
                )
                if not left_claims.isdisjoint(
                    right_claims
                ) or not left_evidence.isdisjoint(right_evidence):
                    raise ValueError("Replication contexts reuse protected evidence.")
        high_structure_refs = tuple(
            ref
            for item in self.contexts
            if item.trace_role
            == ContradictionPredictionReplicationTraceRole.HIGH_TRACE_VARIATION
            for ref in item.background_structure_refs
        )
        high_lineage_refs = tuple(
            ref
            for item in self.contexts
            if item.trace_role
            == ContradictionPredictionReplicationTraceRole.HIGH_TRACE_VARIATION
            for refs in (
                item.background_council_decision_refs,
                item.background_promotion_event_refs,
            )
            for ref in refs
        )
        if (
            len(set(high_structure_refs)) != len(high_structure_refs)
            or len(set(high_lineage_refs)) != len(high_lineage_refs)
        ):
            raise ValueError("Replication contexts reuse background lineage.")
        if (
            not self.durable_before_execution
            or not self.disjoint_evidence_required
            or not self.native_trace_variation_required
            or not self.identical_threshold_required
            or not self.untouched_low_trace_control_required
            or not self.group_heldout_required
            or not self.preserve_prior_falsifications_required
            or self.replication_executed
            or self.outcomes_observed
            or self.predictive_discrimination_observed
            or self.dimensional_separation_observed
            or self.independent_held_out_replication_observed
            or self.authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Replication declaration crossed its claim boundary.")
        expected = stable_id(
            "contradiction_prediction_replication_declaration",
            self.model_dump(mode="json", exclude={"declaration_id"}),
        )
        if self.declaration_id != expected:
            raise ValueError("Replication-declaration checksum mismatch.")
        return self


class ContradictionPredictionReplicationPreregistrationEnvelope(BaseModel):
    """Canonical immutable bytes proving the four-context design existed first."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sidecar_format: str = (
        CONTRADICTION_PREDICTION_REPLICATION_PREREGISTRATION_FORMAT
    )
    declaration: ContradictionPredictionReplicationDeclaration
    declaration_sha256: str

    @classmethod
    def build(
        cls,
        declaration: ContradictionPredictionReplicationDeclaration,
    ) -> "ContradictionPredictionReplicationPreregistrationEnvelope":
        frozen = ContradictionPredictionReplicationDeclaration.model_validate(
            declaration.model_dump(mode="json")
        )
        return cls(
            declaration=frozen,
            declaration_sha256=_digest(frozen.model_dump(mode="json")),
        )

    @model_validator(mode="after")
    def validate_envelope(
        self,
    ) -> "ContradictionPredictionReplicationPreregistrationEnvelope":
        if (
            self.sidecar_format
            != CONTRADICTION_PREDICTION_REPLICATION_PREREGISTRATION_FORMAT
            or self.declaration_sha256
            != _digest(self.declaration.model_dump(mode="json"))
        ):
            raise ValueError("Replication preregistration digest mismatch.")
        return self


def contradiction_prediction_replication_preregistration_bytes(
    envelope: ContradictionPredictionReplicationPreregistrationEnvelope,
) -> bytes:
    validated = (
        ContradictionPredictionReplicationPreregistrationEnvelope.model_validate(
            envelope.model_dump(mode="json")
        )
    )
    data = canonical_json_bytes(validated.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise ContradictionPredictionReplicationIntegrityError(
            "Replication preregistration exceeds its size limit."
        )
    return data


def read_contradiction_prediction_replication_preregistration(
    path: str | Path,
) -> ContradictionPredictionReplicationPreregistrationEnvelope:
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise ContradictionPredictionReplicationIntegrityError(
                "Replication preregistration exceeds its size limit."
            )
        envelope = (
            ContradictionPredictionReplicationPreregistrationEnvelope.model_validate_json(
                data
            )
        )
        if contradiction_prediction_replication_preregistration_bytes(envelope) != data:
            raise ContradictionPredictionReplicationIntegrityError(
                "Replication preregistration is not canonical."
            )
        return envelope
    except ContradictionPredictionReplicationIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ContradictionPredictionReplicationIntegrityError(
            "Invalid replication preregistration."
        ) from exc


def _write_immutable(path: Path, data: bytes) -> None:
    if os.name != "posix" or fcntl is None:
        raise ContradictionPredictionReplicationIntegrityError(
            "Replication sidecars require POSIX flock support."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        if path.exists():
            if path.read_bytes() == data:
                return
            raise ContradictionPredictionReplicationIntegrityError(
                "Replication path already contains different evidence."
            )
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            temporary = None
            directory_fd = os.open(
                path.parent,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def save_contradiction_prediction_replication_preregistration(
    path: str | Path,
    envelope: ContradictionPredictionReplicationPreregistrationEnvelope,
) -> str:
    validated = (
        ContradictionPredictionReplicationPreregistrationEnvelope.model_validate(
            envelope.model_dump(mode="json")
        )
    )
    _write_immutable(
        Path(path),
        contradiction_prediction_replication_preregistration_bytes(validated),
    )
    return validated.declaration.declaration_id


@dataclass(frozen=True)
class ContradictionPredictionReplicationContextInput:
    calibration_kernel: VerdantKernel
    held_out_kernel: VerdantKernel
    lenses: EquivalenceLensSystem
    pair_context: ContradictionLensTrialPairContext
    trace_role: ContradictionPredictionReplicationTraceRole


class ContradictionPredictionReplicationPreregistrar:
    """Bind four pristine context states and publish only their declaration."""

    def register(
        self,
        path: str | Path,
        contexts: Sequence[ContradictionPredictionReplicationContextInput],
    ) -> ContradictionPredictionReplicationPreregistrationEnvelope:
        if len(contexts) != CONTRADICTION_PREDICTION_REPLICATION_CONTEXT_COUNT:
            raise ContradictionPredictionReplicationIntegrityError(
                "Replication preregistration requires four context inputs."
            )
        if len(
            {
                id(kernel)
                for item in contexts
                for kernel in (item.calibration_kernel, item.held_out_kernel)
            }
        ) != 2 * len(contexts):
            raise ContradictionPredictionReplicationIntegrityError(
                "Replication preregistration requires distinct canonical kernels."
            )
        snapshots = tuple(
            (
                item.calibration_kernel.fingerprint(),
                item.held_out_kernel.fingerprint(),
                item.lenses.fingerprint(),
            )
            for item in contexts
        )
        try:
            declared_contexts = tuple(
                ContradictionPredictionReplicationContext.build(
                    item.pair_context,
                    item.calibration_kernel,
                    item.held_out_kernel,
                    item.lenses,
                    trace_role=item.trace_role,
                )
                for item in contexts
            )
            declaration = ContradictionPredictionReplicationDeclaration.build(
                declared_contexts
            )
            envelope = (
                ContradictionPredictionReplicationPreregistrationEnvelope.build(
                    declaration
                )
            )
            save_contradiction_prediction_replication_preregistration(path, envelope)
            loaded = read_contradiction_prediction_replication_preregistration(path)
            if loaded != envelope:
                raise ContradictionPredictionReplicationIntegrityError(
                    "Persisted replication preregistration changed its declaration."
                )
            return loaded
        except ContradictionPredictionReplicationIntegrityError:
            raise
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ContradictionPredictionReplicationIntegrityError(str(exc)) from exc
        finally:
            after = tuple(
                (
                    item.calibration_kernel.fingerprint(),
                    item.held_out_kernel.fingerprint(),
                    item.lenses.fingerprint(),
                )
                for item in contexts
            )
            if after != snapshots:
                raise RuntimeError(
                    "Replication preregistration mutated canonical or Lens state."
                )
