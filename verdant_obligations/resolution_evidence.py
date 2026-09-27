"""Coverage gate between matched traces and Resolution Contract observations.

The current counterfactual trace records structural overlay changes.  It does
not record retrieval, workspace admission, an outgoing action, or execution of
a dependency path.  This module makes that boundary content-addressed instead
of filling the Resolution Contract's required fields from hypothesis labels.
"""
from __future__ import annotations

from enum import Enum

from pydantic import ConfigDict, Field, model_validator

from verdant_kernel import ObligationFamily, VerdantKernel
from verdant_kernel.models import FrozenRecord, stable_id

from .counterfactual import CounterfactualRunResult, SimulationLedger
from .hypotheses import HypothesisOperator, StructuralHypothesis
from .trace_observations import (
    MatchedCounterfactualObserver,
    MatchedCounterfactualPlans,
    MatchedStructuralObservation,
    StructuralTraceEffect,
    TraceObservationIntegrityError,
)


TRACE_RESOLUTION_EVIDENCE_VERSION = "trace_resolution_evidence_coverage_v0.25"


class TraceResolutionEvidenceIntegrityError(RuntimeError):
    """Raised when a coverage receipt cannot be grounded in actual lineage."""


class ResolutionEvidenceRequirement(str, Enum):
    CUE_REFERENCE = "cue_reference"
    CONTEXT_FINGERPRINT = "context_fingerprint"
    CANONICAL_CHECKPOINT = "canonical_checkpoint"
    SETTLEMENT_LINEAGE = "settlement_lineage"
    RESOLUTION_STRUCTURE = "resolution_structure"
    STRUCTURAL_DELTA = "structural_delta"
    CANONICAL_RECORD_PRESERVATION = "canonical_record_preservation"
    CANDIDATE_PATH_LINEAGE = "candidate_path_lineage"
    RETRIEVED_REFS = "retrieved_refs"
    ADMITTED_REFS = "admitted_refs"
    OUTGOING_ACTION = "outgoing_action"
    EXECUTED_DEPENDENCY_PATH = "executed_dependency_path"
    STOCHASTIC_SEED = "stochastic_seed"
    TEMPORAL_HORIZON = "temporal_horizon"
    LENS_BINDING = "lens_binding"
    SLOT_BUDGET = "slot_budget"
    HELD_OUT_REPLICATION = "held_out_replication"


GROUNDED_TRACE_REQUIREMENTS = tuple(
    sorted(
        (
            ResolutionEvidenceRequirement.CUE_REFERENCE,
            ResolutionEvidenceRequirement.CONTEXT_FINGERPRINT,
            ResolutionEvidenceRequirement.CANONICAL_CHECKPOINT,
            ResolutionEvidenceRequirement.SETTLEMENT_LINEAGE,
            ResolutionEvidenceRequirement.RESOLUTION_STRUCTURE,
            ResolutionEvidenceRequirement.STRUCTURAL_DELTA,
            ResolutionEvidenceRequirement.CANONICAL_RECORD_PRESERVATION,
            ResolutionEvidenceRequirement.CANDIDATE_PATH_LINEAGE,
        ),
        key=lambda item: item.value,
    )
)

MISSING_OPERATIONAL_REQUIREMENTS = tuple(
    sorted(
        (
            ResolutionEvidenceRequirement.RETRIEVED_REFS,
            ResolutionEvidenceRequirement.ADMITTED_REFS,
            ResolutionEvidenceRequirement.OUTGOING_ACTION,
            ResolutionEvidenceRequirement.EXECUTED_DEPENDENCY_PATH,
            ResolutionEvidenceRequirement.STOCHASTIC_SEED,
            ResolutionEvidenceRequirement.TEMPORAL_HORIZON,
            ResolutionEvidenceRequirement.LENS_BINDING,
            ResolutionEvidenceRequirement.SLOT_BUDGET,
            ResolutionEvidenceRequirement.HELD_OUT_REPLICATION,
        ),
        key=lambda item: item.value,
    )
)


class TraceResolutionEvidenceReceipt(FrozenRecord):
    """Exact account of what one matched trace can and cannot establish."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    deriver_version: str = TRACE_RESOLUTION_EVIDENCE_VERSION
    obligation_id: str
    obligation_event_ref: str
    hypothesis_ref: str
    matched_observation_ref: str
    cue_ref: str
    context_fingerprint: str
    canonical_checkpoint_fingerprint: str
    baseline_trace_ref: str
    treatment_trace_ref: str
    baseline_settlement_ref: str
    treatment_settlement_ref: str
    protected_canonical_refs: tuple[str, ...] = Field(min_length=1)
    candidate_path_relation_refs: tuple[str, ...] = Field(min_length=1)
    candidate_evidence_refs: tuple[str, ...] = Field(min_length=1)
    structural_effect: StructuralTraceEffect
    structural_added_refs: tuple[str, ...] = ()
    structural_removed_refs: tuple[str, ...] = ()
    structural_changed_refs: tuple[str, ...] = ()
    canonical_records_preserved: bool
    grounded_requirements: tuple[ResolutionEvidenceRequirement, ...]
    missing_requirements: tuple[ResolutionEvidenceRequirement, ...]
    resolution_trial_ready: bool = False
    simulated_only: bool = True
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, **values) -> "TraceResolutionEvidenceReceipt":
        def identity_value(value):
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, tuple):
                return tuple(identity_value(item) for item in value)
            return value

        for key in (
            "protected_canonical_refs",
            "candidate_evidence_refs",
            "structural_added_refs",
            "structural_removed_refs",
            "structural_changed_refs",
        ):
            values[key] = tuple(sorted(set(values.get(key, ()))))
        values["candidate_path_relation_refs"] = tuple(
            values["candidate_path_relation_refs"]
        )
        values.setdefault("deriver_version", TRACE_RESOLUTION_EVIDENCE_VERSION)
        values["grounded_requirements"] = GROUNDED_TRACE_REQUIREMENTS
        values["missing_requirements"] = MISSING_OPERATIONAL_REQUIREMENTS
        values.setdefault("resolution_trial_ready", False)
        values.setdefault("simulated_only", True)
        values.setdefault("observed_outcome_authority_enabled", False)
        values.setdefault("resolution_authority_enabled", False)
        values.setdefault("canonical_commit_permitted", False)
        payload = {
            key: identity_value(value)
            for key, value in values.items()
            if key != "receipt_id"
        }
        values["receipt_id"] = stable_id(
            "trace_resolution_evidence_receipt",
            payload,
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "TraceResolutionEvidenceReceipt":
        identifiers = (
            self.obligation_id,
            self.obligation_event_ref,
            self.hypothesis_ref,
            self.matched_observation_ref,
            self.cue_ref,
            self.baseline_trace_ref,
            self.treatment_trace_ref,
            self.baseline_settlement_ref,
            self.treatment_settlement_ref,
        )
        if not all(item.strip() for item in identifiers):
            raise ValueError("Trace resolution evidence references cannot be empty.")
        if self.deriver_version != TRACE_RESOLUTION_EVIDENCE_VERSION:
            raise ValueError("Unknown trace resolution evidence derivation version.")
        for digest in (
            self.context_fingerprint,
            self.canonical_checkpoint_fingerprint,
        ):
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError(
                    "Trace resolution evidence fingerprints must be SHA-256."
                )
        for refs, label in (
            (self.protected_canonical_refs, "protected canonical refs"),
            (self.candidate_evidence_refs, "candidate evidence refs"),
            (self.structural_added_refs, "added refs"),
            (self.structural_removed_refs, "removed refs"),
            (self.structural_changed_refs, "changed refs"),
        ):
            if tuple(sorted(set(refs))) != refs:
                raise ValueError(
                    f"Trace resolution evidence {label} must be sorted and unique."
                )
        if len(set(self.candidate_path_relation_refs)) != len(
            self.candidate_path_relation_refs
        ):
            raise ValueError("Candidate path relation lineage cannot repeat an edge.")
        if self.grounded_requirements != GROUNDED_TRACE_REQUIREMENTS:
            raise ValueError("Trace-grounded requirement coverage was altered.")
        if self.missing_requirements != MISSING_OPERATIONAL_REQUIREMENTS:
            raise ValueError("Missing operational requirement coverage was altered.")
        if (
            self.resolution_trial_ready
            or not self.simulated_only
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "Trace coverage cannot claim an observed or resolvable trial."
            )
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != stable_id(
            "trace_resolution_evidence_receipt",
            payload,
        ):
            raise ValueError("Trace resolution evidence checksum mismatch.")
        return self


class TraceResolutionEvidenceDeriver:
    """Ground available fields and preserve every missing operational field."""

    @staticmethod
    def _canonical_refs(kernel: VerdantKernel) -> set[str]:
        collections = (
            kernel.state.evidence,
            kernel.state.concepts,
            kernel.state.relations,
            kernel.state.claims,
            kernel.state.structures,
            kernel.state.layered_structures,
            kernel.state.obligation_kernels,
        )
        return {ref for collection in collections for ref in collection}

    def derive(
        self,
        kernel: VerdantKernel,
        ledger: SimulationLedger,
        *,
        obligation_event_ref: str,
        hypothesis: StructuralHypothesis,
        plans: MatchedCounterfactualPlans,
        baseline_result: CounterfactualRunResult,
        treatment_result: CounterfactualRunResult,
        observation: MatchedStructuralObservation,
    ) -> TraceResolutionEvidenceReceipt:
        try:
            hypothesis = StructuralHypothesis.model_validate(
                hypothesis.model_dump(mode="json")
            )
            observation = MatchedStructuralObservation.model_validate(
                observation.model_dump(mode="json")
            )
            obligation = kernel.state.obligation_kernels.get(
                hypothesis.obligation_id
            )
            if (
                obligation is None
                or obligation.family != ObligationFamily.DEPENDENCY_GAP
            ):
                raise TraceResolutionEvidenceIntegrityError(
                    "Trace resolution evidence requires a DependencyGap obligation."
                )
            event = next(
                (
                    item
                    for item in kernel.state.obligation_history
                    if item.event_id == obligation_event_ref
                ),
                None,
            )
            if (
                event is None
                or event.obligation_id != obligation.kernel_id
                or not (event.context_snapshot_hash or "").strip()
            ):
                raise TraceResolutionEvidenceIntegrityError(
                    "Trace resolution evidence lost its detection context."
                )
            if (
                hypothesis.operator
                != HypothesisOperator.EVIDENCE_PATH_PROJECTION
                or not hypothesis.patches
                or not hypothesis.derivation_path_relation_ids
            ):
                raise TraceResolutionEvidenceIntegrityError(
                    "Trace resolution evidence requires a projected evidence path."
                )
            if not set(hypothesis.derivation_path_relation_ids).issubset(
                kernel.state.relations
            ):
                raise TraceResolutionEvidenceIntegrityError(
                    "Projected path lineage is not canonical."
                )
            if not set(obligation.canonical_triggering_refs).issubset(
                hypothesis.provenance_refs
            ):
                raise TraceResolutionEvidenceIntegrityError(
                    "Projected hypothesis lost the obligation's protected lineage."
                )
            if (
                plans.baseline.patches != hypothesis.patches
                or plans.treatment.patches != hypothesis.patches
                or plans.baseline.apply_patch_count != 0
                or plans.treatment.apply_patch_count != len(hypothesis.patches)
            ):
                raise TraceResolutionEvidenceIntegrityError(
                    "Matched plans differ from the projected hypothesis."
                )
            verified = MatchedCounterfactualObserver().observe(
                kernel,
                ledger,
                hypothesis_ref=hypothesis.hypothesis_id,
                baseline_plan=plans.baseline,
                baseline_result=baseline_result,
                treatment_plan=plans.treatment,
                treatment_result=treatment_result,
            )
            if verified != observation:
                raise TraceResolutionEvidenceIntegrityError(
                    "Matched structural observation differs from actual lineage."
                )
            checkpoint = kernel.fingerprint()
            if (
                observation.baseline.canonical_fingerprint != checkpoint
                or observation.treatment.canonical_fingerprint != checkpoint
            ):
                raise TraceResolutionEvidenceIntegrityError(
                    "Matched structural observation crossed a checkpoint."
                )
            protected = obligation.canonical_triggering_refs
            if not set(protected).issubset(self._canonical_refs(kernel)):
                raise TraceResolutionEvidenceIntegrityError(
                    "Protected obligation references are not canonical."
                )
            evidence_refs = tuple(
                sorted(
                    ref
                    for ref in hypothesis.provenance_refs
                    if ref in kernel.state.evidence
                )
            )
            if not evidence_refs:
                raise TraceResolutionEvidenceIntegrityError(
                    "Projected evidence path has no canonical evidence lineage."
                )
            return TraceResolutionEvidenceReceipt.build(
                obligation_id=obligation.kernel_id,
                obligation_event_ref=event.event_id,
                hypothesis_ref=hypothesis.hypothesis_id,
                matched_observation_ref=observation.observation_id,
                cue_ref=obligation.missing_input_signature,
                context_fingerprint=event.context_snapshot_hash,
                canonical_checkpoint_fingerprint=checkpoint,
                baseline_trace_ref=observation.baseline.trace_id,
                treatment_trace_ref=observation.treatment.trace_id,
                baseline_settlement_ref=observation.baseline.settlement_id,
                treatment_settlement_ref=observation.treatment.settlement_id,
                protected_canonical_refs=protected,
                candidate_path_relation_refs=(
                    hypothesis.derivation_path_relation_ids
                ),
                candidate_evidence_refs=evidence_refs,
                structural_effect=observation.effect,
                structural_added_refs=observation.added_record_refs,
                structural_removed_refs=observation.removed_record_refs,
                structural_changed_refs=observation.changed_record_refs,
                canonical_records_preserved=(
                    observation.canonical_records_preserved
                ),
            )
        except TraceResolutionEvidenceIntegrityError:
            raise
        except (TraceObservationIntegrityError, ValueError, TypeError) as exc:
            raise TraceResolutionEvidenceIntegrityError(str(exc)) from exc
