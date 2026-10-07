"""Preregistered multi-context prediction cohort for Contradiction.

The v0.42 cardinality rule remains frozen and falsified.  This opt-in v0.43
experiment preregisters two canonically disjoint contexts whose native Lens
outputs are the actually constructible ``(1, 1)`` and ``(2, 2)`` profiles.
Each context runs through the unchanged v0.42 five-artifact audit, including
its untouched zero-threshold control.  A rule family fixed before execution
learns only the other context's normal outcome and defaults an unseen profile
to ``VALID_NULL``.  Leave-one-context-out evaluation therefore cannot consult
the evaluation context or either control while deriving a fold rule.

The result is deliberately falsifying: the same cardinality input has a normal
admission-gain outcome and a valid-null control outcome.  This module grants no
truth, resolution, promotion, policy-rewrite, or canonical-write authority.
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

from pydantic import BaseModel, ConfigDict, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .contradiction_dimension_criterion import (
    ContradictionDimensionCriterionDeclaration,
    ContradictionLensOutputDimension,
    ContradictionProjectionCardinalityProfile,
)
from .contradiction_downstream_outcome import (
    ContradictionDownstreamOutcomeDeclaration,
    ContradictionDownstreamOutcomeDisposition,
    ContradictionDownstreamOutcomePolicy,
)
from .contradiction_prediction_audit import (
    CONTRADICTION_PREDICTION_PROFILE_MAPPING,
    ContradictionCardinalityPredictionPolicy,
    ContradictionDurablePredictionAuditRunner,
    ContradictionPredictionAuditDisposition,
    ContradictionPredictionAuditEnvelope,
    ContradictionPredictionAuditIntegrityError,
    ContradictionPredictionAuditRun,
    ContradictionPredictionContextEvaluation,
    ContradictionPredictionContextRole,
)
from .contradiction_trial_controls import ContradictionLensTrialPairContext
from .counterfactual import CounterfactualRuntime, SimulationLedger
from .equivalence import EquivalenceLensSystem


CONTRADICTION_PREDICTION_COHORT_VERSION = "contradiction_prediction_cohort_v0.43"
CONTRADICTION_PREDICTION_COHORT_PREREGISTRATION_FORMAT = (
    "verdant-contradiction-prediction-cohort-preregistration-v1"
)
CONTRADICTION_PREDICTION_COHORT_RESULT_FORMAT = (
    "verdant-contradiction-prediction-cohort-result-v1"
)
CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES = (
    ContradictionProjectionCardinalityProfile.SINGLETON_PER_ROUTE,
    ContradictionProjectionCardinalityProfile.EQUAL_MULTI_REFERENCE_ROUTES,
)
_POSITIVE_THRESHOLD = 0.28
_CONTROL_THRESHOLD = 0.0
_MAX_SIDECAR_BYTES = 256 * 1024 * 1024
_EMPTY_LEDGER = SimulationLedger().fingerprint()


class ContradictionPredictionCohortIntegrityError(RuntimeError):
    """Raised when cohort evidence loses preregistration or isolation."""


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


def _profile(counts: tuple[int, int]) -> ContradictionProjectionCardinalityProfile:
    if counts == (1, 1):
        return ContradictionProjectionCardinalityProfile.SINGLETON_PER_ROUTE
    if counts[0] == counts[1]:
        return ContradictionProjectionCardinalityProfile.EQUAL_MULTI_REFERENCE_ROUTES
    return ContradictionProjectionCardinalityProfile.ASYMMETRIC_ROUTE_CARDINALITY


def _declared_counts(pair: ContradictionLensTrialPairContext) -> tuple[int, int]:
    roots = pair.held_out.controlled_context.functional_context.query_source_roots
    return tuple(
        sum(bool(set(query).intersection(candidate)) for candidate in roots)
        for query in roots
    )


def _normalized_outcome(
    declaration: ContradictionDownstreamOutcomeDeclaration,
) -> dict[str, Any]:
    data = declaration.model_dump(mode="json")
    data["declaration_id"] = "normalized"
    data["policy"]["minimum_admission_score"] = "matched-control"
    data["policy_sha256"] = "normalized"
    data["shadow_workspace_policy"]["minimum_admission_score"] = "matched-control"
    data["shadow_workspace_policy_sha256"] = "normalized"
    return data


def _validate_outcomes(
    positive: ContradictionDownstreamOutcomeDeclaration,
    control: ContradictionDownstreamOutcomeDeclaration,
) -> None:
    if (
        positive.pair_context != control.pair_context
        or positive.policy.minimum_admission_score != _POSITIVE_THRESHOLD
        or control.policy.minimum_admission_score != _CONTROL_THRESHOLD
        or _normalized_outcome(positive) != _normalized_outcome(control)
    ):
        raise ValueError("Cohort outcomes are not exact matched controls.")


class ContradictionPredictionCohortRuleFamily(BaseModel):
    """Bounded rule grammar fixed before cohort execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = CONTRADICTION_PREDICTION_COHORT_VERSION
    selected_dimension: ContradictionLensOutputDimension = (
        ContradictionLensOutputDimension.ACTIVATED_REFERENCE_CARDINALITY_PROFILE
    )
    unseen_profile_default: ContradictionDownstreamOutcomeDisposition = (
        ContradictionDownstreamOutcomeDisposition.VALID_NULL
    )
    training_context_count: int = 1
    evaluation_context_count: int = 1
    positive_training_input_permitted: bool = True
    control_input_permitted: bool = False
    evaluation_input_permitted: bool = False
    cardinality_only: bool = True

    @model_validator(mode="after")
    def validate_policy(self) -> "ContradictionPredictionCohortRuleFamily":
        if (
            self.policy_version != CONTRADICTION_PREDICTION_COHORT_VERSION
            or self.selected_dimension
            != ContradictionLensOutputDimension.ACTIVATED_REFERENCE_CARDINALITY_PROFILE
            or self.unseen_profile_default
            != ContradictionDownstreamOutcomeDisposition.VALID_NULL
            or self.training_context_count != 1
            or self.evaluation_context_count != 1
            or not self.positive_training_input_permitted
            or self.control_input_permitted
            or self.evaluation_input_permitted
            or not self.cardinality_only
        ):
            raise ValueError("Cohort rule family crossed its fixed grammar.")
        return self

    def fingerprint(self) -> str:
        return _digest(self.model_dump(mode="json"))


class ContradictionPredictionCohortContext(FrozenRecord):
    """One preregistered pair, actual-profile hypothesis, and outcome pair."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    context_id: str
    context_version: str = CONTRADICTION_PREDICTION_COHORT_VERSION
    pair_context: ContradictionLensTrialPairContext
    pair_context_ref: str
    expected_cardinalities: tuple[int, int]
    expected_profile: ContradictionProjectionCardinalityProfile
    calibration_claim_refs: tuple[str, str]
    calibration_evidence_refs: tuple[str, ...]
    evaluation_claim_refs: tuple[str, str]
    evaluation_evidence_refs: tuple[str, ...]
    positive_declaration: ContradictionDownstreamOutcomeDeclaration
    positive_declaration_ref: str
    control_declaration: ContradictionDownstreamOutcomeDeclaration
    control_declaration_ref: str
    profile_predeclared_without_trace: bool = True
    valid_null_control_preregistered: bool = True
    evidence_suppression_permitted: bool = False
    authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        pair_context: ContradictionLensTrialPairContext,
        held_out_kernel: VerdantKernel,
    ) -> "ContradictionPredictionCohortContext":
        pair = ContradictionLensTrialPairContext.model_validate(
            pair_context.model_dump(mode="json")
        )
        if held_out_kernel.fingerprint() != pair.held_out.canonical_checkpoint_fingerprint:
            raise ValueError("Cohort context received a foreign held-out kernel.")
        counts = _declared_counts(pair)
        positive = ContradictionDownstreamOutcomeDeclaration.build(
            pair,
            held_out_kernel,
            policy=ContradictionDownstreamOutcomePolicy(
                minimum_admission_score=_POSITIVE_THRESHOLD
            ),
        )
        control = ContradictionDownstreamOutcomeDeclaration.build(
            pair,
            held_out_kernel,
            policy=ContradictionDownstreamOutcomePolicy(
                minimum_admission_score=_CONTROL_THRESHOLD
            ),
        )
        _validate_outcomes(positive, control)
        values = {
            "context_version": CONTRADICTION_PREDICTION_COHORT_VERSION,
            "pair_context": pair,
            "pair_context_ref": pair.pair_id,
            "expected_cardinalities": counts,
            "expected_profile": _profile(counts),
            "calibration_claim_refs": pair.calibration.claim_refs,
            "calibration_evidence_refs": pair.calibration.protected_evidence_refs,
            "evaluation_claim_refs": pair.held_out.claim_refs,
            "evaluation_evidence_refs": pair.held_out.protected_evidence_refs,
            "positive_declaration": positive,
            "positive_declaration_ref": positive.declaration_id,
            "control_declaration": control,
            "control_declaration_ref": control.declaration_id,
            "profile_predeclared_without_trace": True,
            "valid_null_control_preregistered": True,
            "evidence_suppression_permitted": False,
            "authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["context_id"] = stable_id(
            "contradiction_prediction_cohort_context", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_context(self) -> "ContradictionPredictionCohortContext":
        pair = self.pair_context
        expected = {
            "pair_context_ref": pair.pair_id,
            "expected_cardinalities": _declared_counts(pair),
            "expected_profile": _profile(_declared_counts(pair)),
            "calibration_claim_refs": pair.calibration.claim_refs,
            "calibration_evidence_refs": pair.calibration.protected_evidence_refs,
            "evaluation_claim_refs": pair.held_out.claim_refs,
            "evaluation_evidence_refs": pair.held_out.protected_evidence_refs,
            "positive_declaration_ref": self.positive_declaration.declaration_id,
            "control_declaration_ref": self.control_declaration.declaration_id,
        }
        if self.context_version != CONTRADICTION_PREDICTION_COHORT_VERSION:
            raise ValueError("Unknown prediction-cohort context version.")
        if any(getattr(self, key) != value for key, value in expected.items()):
            raise ValueError("Cohort context changed canonical provenance.")
        if (
            self.positive_declaration.pair_context != pair
            or self.control_declaration.pair_context != pair
        ):
            raise ValueError("Cohort context changed outcome lineage.")
        _validate_outcomes(self.positive_declaration, self.control_declaration)
        if (
            not set(self.calibration_claim_refs).isdisjoint(self.evaluation_claim_refs)
            or not set(self.calibration_evidence_refs).isdisjoint(
                self.evaluation_evidence_refs
            )
        ):
            raise ValueError("Cohort context mixed calibration and evaluation evidence.")
        if (
            not self.profile_predeclared_without_trace
            or not self.valid_null_control_preregistered
            or self.evidence_suppression_permitted
            or self.authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Cohort context crossed its claim boundary.")
        expected_id = stable_id(
            "contradiction_prediction_cohort_context",
            self.model_dump(mode="json", exclude={"context_id"}),
        )
        if self.context_id != expected_id:
            raise ValueError("Cohort-context checksum mismatch.")
        return self


class ContradictionPredictionCohortFold(FrozenRecord):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fold_id: str
    fold_version: str = CONTRADICTION_PREDICTION_COHORT_VERSION
    training_context_ref: str
    evaluation_context_ref: str
    disjoint_contexts_required: bool = True

    @classmethod
    def build(
        cls,
        training_context_ref: str,
        evaluation_context_ref: str,
    ) -> "ContradictionPredictionCohortFold":
        values = {
            "fold_version": CONTRADICTION_PREDICTION_COHORT_VERSION,
            "training_context_ref": training_context_ref,
            "evaluation_context_ref": evaluation_context_ref,
            "disjoint_contexts_required": True,
        }
        values["fold_id"] = stable_id("contradiction_prediction_cohort_fold", values)
        return cls(**values)

    @model_validator(mode="after")
    def validate_fold(self) -> "ContradictionPredictionCohortFold":
        if (
            self.fold_version != CONTRADICTION_PREDICTION_COHORT_VERSION
            or self.training_context_ref == self.evaluation_context_ref
            or not self.disjoint_contexts_required
        ):
            raise ValueError("Cohort fold crossed its fixed partition.")
        expected = stable_id(
            "contradiction_prediction_cohort_fold",
            self.model_dump(mode="json", exclude={"fold_id"}),
        )
        if self.fold_id != expected:
            raise ValueError("Cohort-fold checksum mismatch.")
        return self


class ContradictionPredictionCohortDeclaration(FrozenRecord):
    """Two-profile cohort frozen durably before either child audit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    declaration_id: str
    declaration_version: str = CONTRADICTION_PREDICTION_COHORT_VERSION
    contexts: tuple[
        ContradictionPredictionCohortContext,
        ContradictionPredictionCohortContext,
    ]
    context_refs: tuple[str, str]
    required_profiles: tuple[
        ContradictionProjectionCardinalityProfile,
        ContradictionProjectionCardinalityProfile,
    ] = CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES
    folds: tuple[ContradictionPredictionCohortFold, ContradictionPredictionCohortFold]
    rule_family: ContradictionPredictionCohortRuleFamily
    rule_family_sha256: str
    preserved_v042_policy: ContradictionCardinalityPredictionPolicy
    preserved_v042_mapping: tuple[
        tuple[
            ContradictionProjectionCardinalityProfile,
            ContradictionDownstreamOutcomeDisposition,
        ],
        ...,
    ] = CONTRADICTION_PREDICTION_PROFILE_MAPPING
    durable_before_execution: bool = True
    disjoint_evidence_required: bool = True
    untouched_controls_required: bool = True
    preserve_v042_falsification_required: bool = True
    authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        contexts: Sequence[tuple[ContradictionLensTrialPairContext, VerdantKernel]],
    ) -> "ContradictionPredictionCohortDeclaration":
        if len(contexts) != 2:
            raise ValueError("Prediction cohort requires exactly two contexts.")
        declared = tuple(
            sorted(
                (
                    ContradictionPredictionCohortContext.build(pair, kernel)
                    for pair, kernel in contexts
                ),
                key=lambda item: item.context_id,
            )
        )
        if len({item.context_id for item in declared}) != 2:
            raise ValueError("Prediction cohort contexts are not disjoint.")
        refs = tuple(item.context_id for item in declared)
        folds = (
            ContradictionPredictionCohortFold.build(refs[1], refs[0]),
            ContradictionPredictionCohortFold.build(refs[0], refs[1]),
        )
        family = ContradictionPredictionCohortRuleFamily()
        values = {
            "declaration_version": CONTRADICTION_PREDICTION_COHORT_VERSION,
            "contexts": declared,
            "context_refs": refs,
            "required_profiles": CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES,
            "folds": folds,
            "rule_family": family,
            "rule_family_sha256": family.fingerprint(),
            "preserved_v042_policy": ContradictionCardinalityPredictionPolicy(),
            "preserved_v042_mapping": CONTRADICTION_PREDICTION_PROFILE_MAPPING,
            "durable_before_execution": True,
            "disjoint_evidence_required": True,
            "untouched_controls_required": True,
            "preserve_v042_falsification_required": True,
            "authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["declaration_id"] = stable_id(
            "contradiction_prediction_cohort_declaration", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_declaration(self) -> "ContradictionPredictionCohortDeclaration":
        refs = tuple(item.context_id for item in self.contexts)
        folds = (
            ContradictionPredictionCohortFold.build(refs[1], refs[0]),
            ContradictionPredictionCohortFold.build(refs[0], refs[1]),
        )
        if (
            self.declaration_version != CONTRADICTION_PREDICTION_COHORT_VERSION
            or tuple(sorted(self.contexts, key=lambda item: item.context_id))
            != self.contexts
            or self.context_refs != refs
            or self.folds != folds
            or set(item.expected_profile for item in self.contexts)
            != set(CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES)
            or self.required_profiles
            != CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES
            or self.rule_family_sha256 != self.rule_family.fingerprint()
            or self.preserved_v042_mapping != CONTRADICTION_PREDICTION_PROFILE_MAPPING
            or self.preserved_v042_policy.profile_mapping
            != CONTRADICTION_PREDICTION_PROFILE_MAPPING
        ):
            raise ValueError("Cohort declaration changed profiles or rule grammar.")
        left, right = self.contexts
        left_claims = set((*left.calibration_claim_refs, *left.evaluation_claim_refs))
        right_claims = set((*right.calibration_claim_refs, *right.evaluation_claim_refs))
        left_evidence = set(
            (*left.calibration_evidence_refs, *left.evaluation_evidence_refs)
        )
        right_evidence = set(
            (*right.calibration_evidence_refs, *right.evaluation_evidence_refs)
        )
        checkpoints = {
            side.canonical_checkpoint_fingerprint
            for context in self.contexts
            for side in (context.pair_context.calibration, context.pair_context.held_out)
        }
        if (
            not left_claims.isdisjoint(right_claims)
            or not left_evidence.isdisjoint(right_evidence)
            or len(checkpoints) != 4
        ):
            raise ValueError("Cohort contexts do not have disjoint evidence.")
        if (
            not self.durable_before_execution
            or not self.disjoint_evidence_required
            or not self.untouched_controls_required
            or not self.preserve_v042_falsification_required
            or self.authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Cohort declaration crossed its claim boundary.")
        expected_id = stable_id(
            "contradiction_prediction_cohort_declaration",
            self.model_dump(mode="json", exclude={"declaration_id"}),
        )
        if self.declaration_id != expected_id:
            raise ValueError("Cohort-declaration checksum mismatch.")
        return self


class ContradictionPredictionCohortPreregistrationEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sidecar_format: str = CONTRADICTION_PREDICTION_COHORT_PREREGISTRATION_FORMAT
    declaration: ContradictionPredictionCohortDeclaration
    declaration_sha256: str

    @classmethod
    def build(
        cls,
        declaration: ContradictionPredictionCohortDeclaration,
    ) -> "ContradictionPredictionCohortPreregistrationEnvelope":
        frozen = ContradictionPredictionCohortDeclaration.model_validate(
            declaration.model_dump(mode="json")
        )
        return cls(
            declaration=frozen,
            declaration_sha256=_digest(frozen.model_dump(mode="json")),
        )

    @model_validator(mode="after")
    def validate_envelope(
        self,
    ) -> "ContradictionPredictionCohortPreregistrationEnvelope":
        if (
            self.sidecar_format
            != CONTRADICTION_PREDICTION_COHORT_PREREGISTRATION_FORMAT
            or self.declaration_sha256
            != _digest(self.declaration.model_dump(mode="json"))
        ):
            raise ValueError("Prediction-cohort preregistration digest mismatch.")
        return self


class ContradictionPredictionCohortFoldRule(FrozenRecord):
    """One fold rule derived from the training positive evaluation only."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    rule_version: str = CONTRADICTION_PREDICTION_COHORT_VERSION
    declaration_ref: str
    fold: ContradictionPredictionCohortFold
    fold_ref: str
    training_evaluation_ref: str
    training_evaluation_sha256: str
    trained_profile: ContradictionProjectionCardinalityProfile
    trained_outcome: ContradictionDownstreamOutcomeDisposition
    unseen_profile_default: ContradictionDownstreamOutcomeDisposition
    positive_training_only: bool = True
    control_consulted: bool = False
    evaluation_consulted: bool = False
    authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        declaration: ContradictionPredictionCohortDeclaration,
        fold: ContradictionPredictionCohortFold,
        training_evaluation: ContradictionPredictionContextEvaluation,
    ) -> "ContradictionPredictionCohortFoldRule":
        contexts = {item.context_id: item for item in declaration.contexts}
        training = ContradictionPredictionContextEvaluation.model_validate(
            training_evaluation.model_dump(mode="json")
        )
        source = contexts.get(fold.training_context_ref)
        if (
            source is None
            or fold not in declaration.folds
            or training.role != ContradictionPredictionContextRole.POSITIVE
            or training.declaration_ref != source.positive_declaration_ref
            or training.held_out_profile != source.expected_profile
            or training.held_out_cardinalities != source.expected_cardinalities
        ):
            raise ValueError("Cohort rule received foreign training evidence.")
        values = {
            "rule_version": CONTRADICTION_PREDICTION_COHORT_VERSION,
            "declaration_ref": declaration.declaration_id,
            "fold": fold,
            "fold_ref": fold.fold_id,
            "training_evaluation_ref": training.evaluation_id,
            "training_evaluation_sha256": _digest(training.model_dump(mode="json")),
            "trained_profile": training.held_out_profile,
            "trained_outcome": training.observed_outcome,
            "unseen_profile_default": declaration.rule_family.unseen_profile_default,
            "positive_training_only": True,
            "control_consulted": False,
            "evaluation_consulted": False,
            "authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["rule_id"] = stable_id(
            "contradiction_prediction_cohort_fold_rule", _payload(values)
        )
        return cls(**values)

    def prediction_for(
        self,
        profile: ContradictionProjectionCardinalityProfile,
    ) -> ContradictionDownstreamOutcomeDisposition:
        if profile == self.trained_profile:
            return self.trained_outcome
        return self.unseen_profile_default

    @model_validator(mode="after")
    def validate_rule(self) -> "ContradictionPredictionCohortFoldRule":
        if (
            self.rule_version != CONTRADICTION_PREDICTION_COHORT_VERSION
            or self.fold_ref != self.fold.fold_id
            or not _is_sha(self.training_evaluation_sha256)
            or self.unseen_profile_default
            != ContradictionDownstreamOutcomeDisposition.VALID_NULL
        ):
            raise ValueError("Cohort fold rule changed training evidence.")
        if (
            not self.positive_training_only
            or self.control_consulted
            or self.evaluation_consulted
            or self.authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Cohort fold rule crossed its claim boundary.")
        expected = stable_id(
            "contradiction_prediction_cohort_fold_rule",
            self.model_dump(mode="json", exclude={"rule_id"}),
        )
        if self.rule_id != expected:
            raise ValueError("Cohort-fold rule checksum mismatch.")
        return self


class ContradictionPredictionCohortFoldEvaluation(FrozenRecord):
    """Held-out normal result and untouched control for one fold."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_id: str
    evaluation_version: str = CONTRADICTION_PREDICTION_COHORT_VERSION
    declaration_ref: str
    fold_ref: str
    rule_ref: str
    training_context_ref: str
    evaluation_context_ref: str
    profile: ContradictionProjectionCardinalityProfile
    cardinalities: tuple[int, int]
    predicted_outcome: ContradictionDownstreamOutcomeDisposition
    positive_evaluation_ref: str
    positive_evaluation_sha256: str
    positive_outcome: ContradictionDownstreamOutcomeDisposition
    positive_match: bool
    control_evaluation_ref: str
    control_evaluation_sha256: str
    control_outcome: ContradictionDownstreamOutcomeDisposition
    control_match: bool
    same_input_verified: bool = True
    opposed_outcomes_observed: bool = True
    evaluation_evidence_disjoint: bool = True
    control_withheld_from_training: bool = True
    joint_discrimination_observed: bool = False
    predictive_discrimination_observed: bool = False
    authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        declaration: ContradictionPredictionCohortDeclaration,
        rule: ContradictionPredictionCohortFoldRule,
        positive_evaluation: ContradictionPredictionContextEvaluation,
        control_evaluation: ContradictionPredictionContextEvaluation,
    ) -> "ContradictionPredictionCohortFoldEvaluation":
        target = {item.context_id: item for item in declaration.contexts}.get(
            rule.fold.evaluation_context_ref
        )
        positive = ContradictionPredictionContextEvaluation.model_validate(
            positive_evaluation.model_dump(mode="json")
        )
        control = ContradictionPredictionContextEvaluation.model_validate(
            control_evaluation.model_dump(mode="json")
        )
        if (
            target is None
            or rule.declaration_ref != declaration.declaration_id
            or positive.role != ContradictionPredictionContextRole.POSITIVE
            or control.role != ContradictionPredictionContextRole.VALID_NULL_CONTROL
            or positive.declaration_ref != target.positive_declaration_ref
            or control.declaration_ref != target.control_declaration_ref
            or positive.held_out_observation_ref != control.held_out_observation_ref
            or positive.held_out_cardinalities != control.held_out_cardinalities
            or positive.held_out_profile != control.held_out_profile
            or positive.held_out_cardinalities != target.expected_cardinalities
            or positive.held_out_profile != target.expected_profile
        ):
            raise ValueError("Cohort fold received foreign evaluation evidence.")
        predicted = rule.prediction_for(positive.held_out_profile)
        positive_match = predicted == positive.observed_outcome
        control_match = predicted == control.observed_outcome
        values = {
            "evaluation_version": CONTRADICTION_PREDICTION_COHORT_VERSION,
            "declaration_ref": declaration.declaration_id,
            "fold_ref": rule.fold_ref,
            "rule_ref": rule.rule_id,
            "training_context_ref": rule.fold.training_context_ref,
            "evaluation_context_ref": rule.fold.evaluation_context_ref,
            "profile": positive.held_out_profile,
            "cardinalities": positive.held_out_cardinalities,
            "predicted_outcome": predicted,
            "positive_evaluation_ref": positive.evaluation_id,
            "positive_evaluation_sha256": _digest(positive.model_dump(mode="json")),
            "positive_outcome": positive.observed_outcome,
            "positive_match": positive_match,
            "control_evaluation_ref": control.evaluation_id,
            "control_evaluation_sha256": _digest(control.model_dump(mode="json")),
            "control_outcome": control.observed_outcome,
            "control_match": control_match,
            "same_input_verified": True,
            "opposed_outcomes_observed": (
                positive.observed_outcome != control.observed_outcome
            ),
            "evaluation_evidence_disjoint": True,
            "control_withheld_from_training": True,
            "joint_discrimination_observed": positive_match and control_match,
            "predictive_discrimination_observed": False,
            "authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["evaluation_id"] = stable_id(
            "contradiction_prediction_cohort_fold_evaluation", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_evaluation(
        self,
    ) -> "ContradictionPredictionCohortFoldEvaluation":
        positive_match = self.predicted_outcome == self.positive_outcome
        control_match = self.predicted_outcome == self.control_outcome
        opposed = self.positive_outcome != self.control_outcome
        if (
            self.evaluation_version != CONTRADICTION_PREDICTION_COHORT_VERSION
            or not _is_sha(self.positive_evaluation_sha256)
            or not _is_sha(self.control_evaluation_sha256)
            or self.positive_match != positive_match
            or self.control_match != control_match
            or self.opposed_outcomes_observed != opposed
            or self.joint_discrimination_observed != (positive_match and control_match)
        ):
            raise ValueError("Cohort fold evaluation was altered.")
        if (
            not self.same_input_verified
            or not self.opposed_outcomes_observed
            or not self.evaluation_evidence_disjoint
            or not self.control_withheld_from_training
            or self.joint_discrimination_observed
            or self.predictive_discrimination_observed
            or self.authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Cohort fold evaluation crossed its claim boundary.")
        expected = stable_id(
            "contradiction_prediction_cohort_fold_evaluation",
            self.model_dump(mode="json", exclude={"evaluation_id"}),
        )
        if self.evaluation_id != expected:
            raise ValueError("Cohort-fold evaluation checksum mismatch.")
        return self


class ContradictionPredictionCohortReceipt(FrozenRecord):
    """Falsifying leave-one-context-out cohort result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    receipt_version: str = CONTRADICTION_PREDICTION_COHORT_VERSION
    declaration: ContradictionPredictionCohortDeclaration
    declaration_ref: str
    declaration_sha256: str
    source_audit_refs: tuple[str, str]
    source_audit_sha256s: tuple[str, str]
    actual_profiles: tuple[
        ContradictionProjectionCardinalityProfile,
        ContradictionProjectionCardinalityProfile,
    ]
    fold_rules: tuple[
        ContradictionPredictionCohortFoldRule,
        ContradictionPredictionCohortFoldRule,
    ]
    fold_evaluations: tuple[
        ContradictionPredictionCohortFoldEvaluation,
        ContradictionPredictionCohortFoldEvaluation,
    ]
    two_actual_profiles_verified: bool = True
    evidence_partitions_disjoint: bool = True
    untouched_controls_verified: bool = True
    all_positive_outcomes_admission_gain: bool = True
    all_controls_valid_null: bool = True
    same_input_outcome_collision_observed: bool = True
    preserved_v042_false_positive: bool = True
    all_v042_audits_falsified: bool = True
    bounded_rule_family_falsified: bool = True
    evidence_preserved: bool = True
    anti_suppression_verified: bool = True
    simulated_only: bool = True
    predictive_discrimination_observed: bool = False
    dimensional_separation_observed: bool = False
    independent_held_out_replication_observed: bool = False
    source_independence_observed: bool = False
    external_outcome_observed: bool = False
    resolution_trial_ready: bool = False
    truth_selection_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    policy_rewrite_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        declaration: ContradictionPredictionCohortDeclaration,
        audits: Sequence[ContradictionPredictionAuditEnvelope],
    ) -> "ContradictionPredictionCohortReceipt":
        if len(audits) != 2:
            raise ValueError("Cohort receipt requires exactly two audits.")
        frozen = tuple(
            ContradictionPredictionAuditEnvelope.model_validate(
                audit.model_dump(mode="json")
            )
            for audit in audits
        )
        by_declaration = {
            audit.receipt.rule.positive_declaration_ref: audit for audit in frozen
        }
        if len(by_declaration) != 2:
            raise ValueError("Cohort audits are not distinct.")
        context_audits: dict[str, ContradictionPredictionAuditEnvelope] = {}
        for context in declaration.contexts:
            audit = by_declaration.get(context.positive_declaration_ref)
            if (
                audit is None
                or audit.receipt.rule.positive_declaration
                != context.positive_declaration
                or audit.receipt.rule.control_declaration
                != context.control_declaration
            ):
                raise ValueError("Cohort audit lost declared lineage.")
            context_audits[context.context_id] = audit
        rules = []
        evaluations = []
        for fold in declaration.folds:
            training = context_audits[fold.training_context_ref]
            evaluation = context_audits[fold.evaluation_context_ref]
            rule = ContradictionPredictionCohortFoldRule.build(
                declaration,
                fold,
                training.receipt.positive_evaluation,
            )
            rules.append(rule)
            evaluations.append(
                ContradictionPredictionCohortFoldEvaluation.build(
                    declaration,
                    rule,
                    evaluation.receipt.positive_evaluation,
                    evaluation.receipt.control_evaluation,
                )
            )
        ordered = tuple(context_audits[item.context_id] for item in declaration.contexts)
        profiles = tuple(
            audit.receipt.positive_evaluation.held_out_profile for audit in ordered
        )
        singleton = next(
            audit
            for audit in ordered
            if audit.receipt.positive_evaluation.held_out_profile
            == ContradictionProjectionCardinalityProfile.SINGLETON_PER_ROUTE
        )
        all_positive = all(
            audit.receipt.positive_evaluation.observed_outcome
            == ContradictionDownstreamOutcomeDisposition.ADMISSION_GAIN
            for audit in ordered
        )
        all_controls = all(
            audit.receipt.control_evaluation.observed_outcome
            == ContradictionDownstreamOutcomeDisposition.VALID_NULL
            for audit in ordered
        )
        values = {
            "receipt_version": CONTRADICTION_PREDICTION_COHORT_VERSION,
            "declaration": declaration,
            "declaration_ref": declaration.declaration_id,
            "declaration_sha256": _digest(declaration.model_dump(mode="json")),
            "source_audit_refs": tuple(audit.receipt.receipt_id for audit in ordered),
            "source_audit_sha256s": tuple(
                _digest(audit.model_dump(mode="json")) for audit in ordered
            ),
            "actual_profiles": profiles,
            "fold_rules": tuple(rules),
            "fold_evaluations": tuple(evaluations),
            "two_actual_profiles_verified": set(profiles)
            == set(CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES),
            "evidence_partitions_disjoint": True,
            "untouched_controls_verified": True,
            "all_positive_outcomes_admission_gain": all_positive,
            "all_controls_valid_null": all_controls,
            "same_input_outcome_collision_observed": all_positive and all_controls,
            "preserved_v042_false_positive": (
                singleton.receipt.disposition
                == ContradictionPredictionAuditDisposition.CARDINALITY_ONLY_FALSE_POSITIVE
                and singleton.receipt.valid_null_false_positive_observed
            ),
            "all_v042_audits_falsified": all(
                audit.receipt.cardinality_only_rule_falsified for audit in ordered
            ),
            "bounded_rule_family_falsified": all(
                not evaluation.joint_discrimination_observed
                for evaluation in evaluations
            ),
            "evidence_preserved": True,
            "anti_suppression_verified": True,
            "simulated_only": True,
            "predictive_discrimination_observed": False,
            "dimensional_separation_observed": False,
            "independent_held_out_replication_observed": False,
            "source_independence_observed": False,
            "external_outcome_observed": False,
            "resolution_trial_ready": False,
            "truth_selection_authority_enabled": False,
            "resolution_authority_enabled": False,
            "policy_rewrite_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["receipt_id"] = stable_id(
            "contradiction_prediction_cohort_receipt", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "ContradictionPredictionCohortReceipt":
        if (
            self.receipt_version != CONTRADICTION_PREDICTION_COHORT_VERSION
            or self.declaration_ref != self.declaration.declaration_id
            or self.declaration_sha256
            != _digest(self.declaration.model_dump(mode="json"))
            or len(set(self.source_audit_refs)) != 2
            or not all(_is_sha(item) for item in self.source_audit_sha256s)
            or set(self.actual_profiles)
            != set(CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES)
            or tuple(rule.fold for rule in self.fold_rules) != self.declaration.folds
            or tuple(item.fold_ref for item in self.fold_evaluations)
            != tuple(fold.fold_id for fold in self.declaration.folds)
        ):
            raise ValueError("Cohort receipt changed source or fold evidence.")
        positive = all(
            item.positive_outcome
            == ContradictionDownstreamOutcomeDisposition.ADMISSION_GAIN
            for item in self.fold_evaluations
        )
        controls = all(
            item.control_outcome == ContradictionDownstreamOutcomeDisposition.VALID_NULL
            for item in self.fold_evaluations
        )
        falsified = all(
            not item.joint_discrimination_observed for item in self.fold_evaluations
        )
        if (
            self.all_positive_outcomes_admission_gain != positive
            or self.all_controls_valid_null != controls
            or self.same_input_outcome_collision_observed != (positive and controls)
            or self.bounded_rule_family_falsified != falsified
        ):
            raise ValueError("Cohort receipt altered its observed result.")
        if any(
            (
                not self.two_actual_profiles_verified,
                not self.evidence_partitions_disjoint,
                not self.untouched_controls_verified,
                not self.same_input_outcome_collision_observed,
                not self.preserved_v042_false_positive,
                not self.all_v042_audits_falsified,
                not self.bounded_rule_family_falsified,
                not self.evidence_preserved,
                not self.anti_suppression_verified,
                not self.simulated_only,
                self.predictive_discrimination_observed,
                self.dimensional_separation_observed,
                self.independent_held_out_replication_observed,
                self.source_independence_observed,
                self.external_outcome_observed,
                self.resolution_trial_ready,
                self.truth_selection_authority_enabled,
                self.resolution_authority_enabled,
                self.policy_rewrite_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError("Cohort receipt crossed its claim boundary.")
        expected = stable_id(
            "contradiction_prediction_cohort_receipt",
            self.model_dump(mode="json", exclude={"receipt_id"}),
        )
        if self.receipt_id != expected:
            raise ValueError("Cohort-receipt checksum mismatch.")
        return self


class ContradictionPredictionCohortResultEnvelope(BaseModel):
    """Atomic cohort result containing two independently replayable audits."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sidecar_format: str = CONTRADICTION_PREDICTION_COHORT_RESULT_FORMAT
    receipt: ContradictionPredictionCohortReceipt
    receipt_sha256: str
    source_audits: tuple[
        ContradictionPredictionAuditEnvelope,
        ContradictionPredictionAuditEnvelope,
    ]
    source_audit_sha256s: tuple[str, str]

    @classmethod
    def build(
        cls,
        declaration: ContradictionPredictionCohortDeclaration,
        audits: Sequence[ContradictionPredictionAuditEnvelope],
    ) -> "ContradictionPredictionCohortResultEnvelope":
        receipt = ContradictionPredictionCohortReceipt.build(declaration, audits)
        by_ref = {audit.receipt.receipt_id: audit for audit in audits}
        ordered = tuple(by_ref[ref] for ref in receipt.source_audit_refs)
        return cls(
            receipt=receipt,
            receipt_sha256=_digest(receipt.model_dump(mode="json")),
            source_audits=ordered,
            source_audit_sha256s=tuple(
                _digest(audit.model_dump(mode="json")) for audit in ordered
            ),
        )

    @model_validator(mode="after")
    def validate_envelope(self) -> "ContradictionPredictionCohortResultEnvelope":
        if (
            self.sidecar_format != CONTRADICTION_PREDICTION_COHORT_RESULT_FORMAT
            or self.receipt_sha256 != _digest(self.receipt.model_dump(mode="json"))
            or self.source_audit_sha256s
            != tuple(_digest(audit.model_dump(mode="json")) for audit in self.source_audits)
            or self.receipt.source_audit_refs
            != tuple(audit.receipt.receipt_id for audit in self.source_audits)
            or self.receipt.source_audit_sha256s != self.source_audit_sha256s
        ):
            raise ValueError("Prediction-cohort result digest mismatch.")
        rebuilt = ContradictionPredictionCohortReceipt.build(
            self.receipt.declaration,
            self.source_audits,
        )
        if self.receipt != rebuilt:
            raise ValueError("Prediction-cohort result changed its source audits.")
        return self


def contradiction_prediction_cohort_preregistration_bytes(
    envelope: ContradictionPredictionCohortPreregistrationEnvelope,
) -> bytes:
    validated = ContradictionPredictionCohortPreregistrationEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    data = canonical_json_bytes(validated.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise ContradictionPredictionCohortIntegrityError(
            "Prediction-cohort preregistration exceeds its size limit."
        )
    return data


def contradiction_prediction_cohort_result_bytes(
    envelope: ContradictionPredictionCohortResultEnvelope,
) -> bytes:
    validated = ContradictionPredictionCohortResultEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    data = canonical_json_bytes(validated.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise ContradictionPredictionCohortIntegrityError(
            "Prediction-cohort result exceeds its size limit."
        )
    return data


def read_contradiction_prediction_cohort_preregistration(
    path: str | Path,
) -> ContradictionPredictionCohortPreregistrationEnvelope:
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise ContradictionPredictionCohortIntegrityError(
                "Prediction-cohort preregistration exceeds its size limit."
            )
        envelope = (
            ContradictionPredictionCohortPreregistrationEnvelope.model_validate_json(
                data
            )
        )
        if contradiction_prediction_cohort_preregistration_bytes(envelope) != data:
            raise ContradictionPredictionCohortIntegrityError(
                "Prediction-cohort preregistration is not canonical."
            )
        return envelope
    except ContradictionPredictionCohortIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ContradictionPredictionCohortIntegrityError(
            "Invalid prediction-cohort preregistration."
        ) from exc


def read_contradiction_prediction_cohort_result(
    path: str | Path,
) -> ContradictionPredictionCohortResultEnvelope:
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise ContradictionPredictionCohortIntegrityError(
                "Prediction-cohort result exceeds its size limit."
            )
        envelope = ContradictionPredictionCohortResultEnvelope.model_validate_json(data)
        if contradiction_prediction_cohort_result_bytes(envelope) != data:
            raise ContradictionPredictionCohortIntegrityError(
                "Prediction-cohort result is not canonical."
            )
        return envelope
    except ContradictionPredictionCohortIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ContradictionPredictionCohortIntegrityError(
            "Invalid prediction-cohort result."
        ) from exc


def _write_immutable(path: Path, data: bytes) -> None:
    if os.name != "posix" or fcntl is None:
        raise ContradictionPredictionCohortIntegrityError(
            "Prediction-cohort sidecars require POSIX flock support."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        if path.exists():
            if path.read_bytes() == data:
                return
            raise ContradictionPredictionCohortIntegrityError(
                "Prediction-cohort path already contains different evidence."
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


def save_contradiction_prediction_cohort_preregistration(
    path: str | Path,
    envelope: ContradictionPredictionCohortPreregistrationEnvelope,
) -> str:
    validated = ContradictionPredictionCohortPreregistrationEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    _write_immutable(
        Path(path), contradiction_prediction_cohort_preregistration_bytes(validated)
    )
    return validated.declaration.declaration_id


def save_contradiction_prediction_cohort_result(
    path: str | Path,
    envelope: ContradictionPredictionCohortResultEnvelope,
) -> str:
    validated = ContradictionPredictionCohortResultEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    _write_immutable(Path(path), contradiction_prediction_cohort_result_bytes(validated))
    return validated.receipt.receipt_id


@dataclass(frozen=True)
class ContradictionPredictionCohortContextInput:
    positive_preregistration_path: Path
    control_preregistration_path: Path
    stage_path: Path
    rule_path: Path
    audit_path: Path
    calibration_kernel: VerdantKernel
    calibration_runtime: CounterfactualRuntime
    held_out_kernel: VerdantKernel
    held_out_runtime: CounterfactualRuntime
    lenses: EquivalenceLensSystem
    pair_context: ContradictionLensTrialPairContext
    criterion_declaration: ContradictionDimensionCriterionDeclaration

    @property
    def artifact_paths(self) -> tuple[Path, Path, Path, Path, Path]:
        return tuple(
            Path(item)
            for item in (
                self.positive_preregistration_path,
                self.control_preregistration_path,
                self.stage_path,
                self.rule_path,
                self.audit_path,
            )
        )


@dataclass(frozen=True)
class ContradictionPredictionCohortRun:
    preregistration_path: Path
    result_path: Path
    preregistration: ContradictionPredictionCohortPreregistrationEnvelope
    result: ContradictionPredictionCohortResultEnvelope
    context_runs: tuple[ContradictionPredictionAuditRun, ...]
    replayed: bool

    @property
    def receipt(self) -> ContradictionPredictionCohortReceipt:
        return self.result.receipt


class ContradictionDurablePredictionCohortRunner:
    """Persist the declaration first, then execute/replay both v0.42 audits."""

    def __init__(
        self,
        *,
        prediction_runner: ContradictionDurablePredictionAuditRunner | None = None,
    ) -> None:
        self.prediction_runner = prediction_runner or ContradictionDurablePredictionAuditRunner()

    def run(
        self,
        preregistration_path: str | Path,
        result_path: str | Path,
        contexts: Sequence[ContradictionPredictionCohortContextInput],
    ) -> ContradictionPredictionCohortRun:
        if len(contexts) != 2:
            raise ContradictionPredictionCohortIntegrityError(
                "Prediction cohort requires exactly two context inputs."
            )
        prereg_path = Path(preregistration_path)
        completed_path = Path(result_path)
        inputs = tuple(contexts)
        canonical_before = tuple(
            (item.calibration_kernel.fingerprint(), item.held_out_kernel.fingerprint())
            for item in inputs
        )
        lens_before = tuple(item.lenses.fingerprint() for item in inputs)
        runtime_before = tuple(
            (
                item.calibration_runtime.ledger.snapshot(),
                item.held_out_runtime.ledger.snapshot(),
            )
            for item in inputs
        )
        published = False
        result_preexisted = completed_path.exists()
        try:
            if any(
                ledger.fingerprint() != _EMPTY_LEDGER
                for item in inputs
                for ledger in (item.calibration_runtime.ledger, item.held_out_runtime.ledger)
            ):
                raise ContradictionPredictionCohortIntegrityError(
                    "Prediction cohort requires pristine caller ledgers."
                )
            artifact_paths = tuple(path for item in inputs for path in item.artifact_paths)
            if len(set(artifact_paths)) != len(artifact_paths):
                raise ContradictionPredictionCohortIntegrityError(
                    "Prediction cohort contexts share an artifact path."
                )
            if completed_path.exists() and any(not path.exists() for path in artifact_paths):
                raise ContradictionPredictionCohortIntegrityError(
                    "Completed cohort predates a required context artifact."
                )
            expected_declaration = ContradictionPredictionCohortDeclaration.build(
                tuple((item.pair_context, item.held_out_kernel) for item in inputs)
            )
            if prereg_path.exists():
                preregistration = read_contradiction_prediction_cohort_preregistration(
                    prereg_path
                )
                if preregistration.declaration != expected_declaration:
                    raise ContradictionPredictionCohortIntegrityError(
                        "Existing cohort preregistration is different."
                    )
            else:
                if completed_path.exists() or any(path.exists() for path in artifact_paths):
                    raise ContradictionPredictionCohortIntegrityError(
                        "Context evidence predates cohort preregistration."
                    )
                preregistration = ContradictionPredictionCohortPreregistrationEnvelope.build(
                    expected_declaration
                )
                save_contradiction_prediction_cohort_preregistration(
                    prereg_path, preregistration
                )
            preregistration_bytes = prereg_path.read_bytes()
            by_pair = {item.pair_context.pair_id: item for item in inputs}
            if len(by_pair) != 2:
                raise ContradictionPredictionCohortIntegrityError(
                    "Prediction cohort contexts are not distinct."
                )
            ordered_inputs = tuple(
                by_pair[context.pair_context_ref]
                for context in preregistration.declaration.contexts
            )
            runs = []
            for item in ordered_inputs:
                runs.append(
                    self.prediction_runner.run(
                        item.positive_preregistration_path,
                        item.control_preregistration_path,
                        item.stage_path,
                        item.rule_path,
                        item.audit_path,
                        item.calibration_kernel,
                        item.calibration_runtime,
                        item.held_out_kernel,
                        item.held_out_runtime,
                        item.lenses,
                        pair_context=item.pair_context,
                        criterion_declaration=item.criterion_declaration,
                    )
                )
                if prereg_path.read_bytes() != preregistration_bytes:
                    raise ContradictionPredictionCohortIntegrityError(
                        "Cohort preregistration changed during execution."
                    )
            expected_result = ContradictionPredictionCohortResultEnvelope.build(
                preregistration.declaration, tuple(run.audit for run in runs)
            )
            if completed_path.exists():
                result = read_contradiction_prediction_cohort_result(completed_path)
                if result != expected_result:
                    raise ContradictionPredictionCohortIntegrityError(
                        "Completed cohort differs from replayed audits."
                    )
            else:
                result = expected_result
                save_contradiction_prediction_cohort_result(completed_path, result)
            if prereg_path.read_bytes() != preregistration_bytes:
                raise ContradictionPredictionCohortIntegrityError(
                    "Cohort preregistration changed during publication."
                )
            published = True
            return ContradictionPredictionCohortRun(
                preregistration_path=prereg_path,
                result_path=completed_path,
                preregistration=preregistration,
                result=result,
                context_runs=tuple(runs),
                replayed=result_preexisted and all(run.replayed for run in runs),
            )
        except ContradictionPredictionCohortIntegrityError:
            raise
        except (
            ContradictionPredictionAuditIntegrityError,
            OSError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            raise ContradictionPredictionCohortIntegrityError(str(exc)) from exc
        finally:
            for index, item in enumerate(inputs):
                if (
                    item.calibration_kernel.fingerprint() != canonical_before[index][0]
                    or item.held_out_kernel.fingerprint() != canonical_before[index][1]
                ):
                    raise RuntimeError("Prediction cohort mutated canonical state.")
                if item.lenses.fingerprint() != lens_before[index]:
                    raise RuntimeError("Prediction cohort mutated a Lens sidecar.")
            if not published:
                for item, snapshots in zip(inputs, runtime_before, strict=True):
                    item.calibration_runtime.ledger.state = snapshots[0]
                    item.held_out_runtime.ledger.state = snapshots[1]
