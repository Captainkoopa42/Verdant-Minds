"""Independent calibration/held-out controls for Contradiction Lens trials.

This module is an explicitly invoked extension of the v0.37 Lens-controlled
Contradiction probe.  A caller must preregister two disjoint canonical
contexts: one calibration context and one held-out context.  The contexts use
separate kernels, Attention records, evidence, source roots, and simulation
ledgers while sharing one exact, frozen Equivalence-Lens lineage.

Agreement between the resulting deterministic internal effects is recorded as
structural replication only.  It is not an external prediction, proof that
real-world sources are independent, dimensional separation, truth selection,
or authority to resolve an obligation or commit a simulated overlay.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .contradiction_hypotheses import (
    ContradictionHypothesisBundle,
    ContradictionHypothesisIntegrityError,
    ContradictionHypothesisProtocol,
)
from .contradiction_lens_control import (
    CONTRADICTION_LENS_GROUNDED_REQUIREMENTS,
    CONTRADICTION_LENS_MISSING_REQUIREMENTS,
    ContradictionLensControlledContext,
    ContradictionLensControlledObservation,
    ContradictionLensControlledProbeRunner,
    ContradictionLensControlledRun,
    ContradictionLensControlIntegrityError,
    ContradictionLensResolutionEvidenceReceipt,
)
from .contradiction_resolution_evidence import (
    ContradictionResolutionRequirement,
)
from .counterfactual import (
    CounterfactualRuntime,
    SimulationIntegrityError,
    SimulationLedger,
    derive_counterfactual_execution_trace,
)
from .equivalence import EquivalenceLensSystem, LensIntegrityError


CONTRADICTION_LENS_TRIAL_CONTROL_VERSION = (
    "contradiction_lens_trial_control_v0.38"
)
CONTRADICTION_LENS_HELD_OUT_REPLICATION_VERSION = (
    "contradiction_lens_held_out_replication_v0.38"
)
CONTRADICTION_LENS_TRIAL_SIDECAR_FORMAT = (
    "verdant-contradiction-lens-trial-sidecar-v1"
)
_MAX_TRIAL_SIDECAR_BYTES = 128 * 1024 * 1024


class ContradictionLensTrialIntegrityError(RuntimeError):
    """Raised when independent trial controls lose exact cross-ledger lineage."""


class ContradictionLensTrialSplit(str, Enum):
    CALIBRATION = "calibration"
    HELD_OUT = "held_out"


class ContradictionLensReplicationDisposition(str, Enum):
    STRUCTURAL_EFFECT_REPLICATED = "structural_effect_replicated"
    VALID_NULL_DIVERGENT_EFFECT = "valid_null_divergent_effect"


def _record_payload(values: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, BaseModel):
            payload[key] = value.model_dump(mode="json")
        elif isinstance(value, Enum):
            payload[key] = value.value
        elif isinstance(value, tuple):
            payload[key] = tuple(
                item.model_dump(mode="json")
                if isinstance(item, BaseModel)
                else item.value
                if isinstance(item, Enum)
                else item
                for item in value
            )
        else:
            payload[key] = value
    return payload


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


class ContradictionLensTrialContext(FrozenRecord):
    """One content-addressed context committed before either matched pair runs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    context_id: str
    control_version: str = CONTRADICTION_LENS_TRIAL_CONTROL_VERSION
    split: ContradictionLensTrialSplit
    controlled_context: ContradictionLensControlledContext
    canonical_checkpoint_fingerprint: str
    obligation_id: str
    obligation_event_ref: str
    contradiction_ref: str
    evidence_receipt_ref: str
    claim_refs: tuple[str, str]
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    source_root_universe: tuple[str, ...] = Field(min_length=1)
    lens_fingerprint: str
    definition_ref: str
    binding_ref: str
    lens_evidence_refs: tuple[str, ...] = Field(min_length=1)
    lens_governance_refs: tuple[str, ...] = Field(min_length=1)
    predeclared: bool = True
    independently_sourced_claim: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        kernel: VerdantKernel,
        bundle: ContradictionHypothesisBundle,
        lenses: EquivalenceLensSystem,
        *,
        split: ContradictionLensTrialSplit,
        source_event_key: str,
        hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
    ) -> "ContradictionLensTrialContext":
        protocol = hypothesis_protocol or ContradictionHypothesisProtocol()
        canonical_before = kernel.fingerprint()
        lens_before = lenses.fingerprint()
        try:
            bundle = ContradictionHypothesisBundle.model_validate(
                bundle.model_dump(mode="json")
            )
            protocol.validate(kernel, bundle)
            controlled = ContradictionLensControlledContext.build(
                bundle,
                lenses,
                source_event_key=source_event_key,
            )
            receipt = bundle.evidence_receipt
            values = {
                "control_version": CONTRADICTION_LENS_TRIAL_CONTROL_VERSION,
                "split": split,
                "controlled_context": controlled,
                "canonical_checkpoint_fingerprint": canonical_before,
                "obligation_id": receipt.obligation_id,
                "obligation_event_ref": receipt.obligation_event_ref,
                "contradiction_ref": receipt.contradiction_ref,
                "evidence_receipt_ref": receipt.receipt_id,
                "claim_refs": receipt.protected_claim_refs,
                "protected_evidence_refs": receipt.protected_evidence_refs,
                "source_root_universe": controlled.functional_context.source_root_universe,
                "lens_fingerprint": controlled.lens_fingerprint,
                "definition_ref": controlled.active_definition_ref,
                "binding_ref": controlled.active_binding_ref,
                "lens_evidence_refs": controlled.active_evidence_refs,
                "lens_governance_refs": controlled.active_governance_refs,
                "predeclared": True,
                "independently_sourced_claim": False,
                "observed_outcome_authority_enabled": False,
                "resolution_authority_enabled": False,
                "canonical_commit_permitted": False,
            }
            values["context_id"] = stable_id(
                "contradiction_lens_trial_context", _record_payload(values)
            )
            return cls(**values)
        except ContradictionLensTrialIntegrityError:
            raise
        except (
            ContradictionHypothesisIntegrityError,
            ContradictionLensControlIntegrityError,
            LensIntegrityError,
            ValueError,
            TypeError,
        ) as exc:
            raise ContradictionLensTrialIntegrityError(str(exc)) from exc
        finally:
            if kernel.fingerprint() != canonical_before:
                raise RuntimeError(
                    "Contradiction trial preregistration mutated canonical state."
                )
            if lenses.fingerprint() != lens_before:
                raise RuntimeError(
                    "Contradiction trial preregistration mutated its Lens sidecar."
                )

    @model_validator(mode="after")
    def validate_context(self) -> "ContradictionLensTrialContext":
        if self.control_version != CONTRADICTION_LENS_TRIAL_CONTROL_VERSION:
            raise ValueError("Unknown Contradiction Lens trial-control version.")
        if not _is_sha256(self.canonical_checkpoint_fingerprint):
            raise ValueError(
                "Contradiction Lens trial checkpoint must be a SHA-256 digest."
            )
        controlled = self.controlled_context
        functional = controlled.functional_context
        receipt = functional.hypothesis_bundle.evidence_receipt
        expected = {
            "obligation_id": receipt.obligation_id,
            "obligation_event_ref": receipt.obligation_event_ref,
            "contradiction_ref": receipt.contradiction_ref,
            "evidence_receipt_ref": receipt.receipt_id,
            "claim_refs": receipt.protected_claim_refs,
            "protected_evidence_refs": receipt.protected_evidence_refs,
            "source_root_universe": functional.source_root_universe,
            "lens_fingerprint": controlled.lens_fingerprint,
            "definition_ref": controlled.active_definition_ref,
            "binding_ref": controlled.active_binding_ref,
            "lens_evidence_refs": controlled.active_evidence_refs,
            "lens_governance_refs": controlled.active_governance_refs,
        }
        if any(getattr(self, key) != value for key, value in expected.items()):
            raise ValueError(
                "Contradiction Lens trial context lost canonical or Lens lineage."
            )
        for refs, label in (
            (self.claim_refs, "claims"),
            (self.protected_evidence_refs, "evidence"),
            (self.source_root_universe, "source roots"),
            (self.lens_evidence_refs, "Lens evidence"),
            (self.lens_governance_refs, "Lens governance"),
        ):
            if tuple(sorted(set(refs))) != refs:
                raise ValueError(
                    f"Contradiction Lens trial {label} must be sorted and unique."
                )
        if (
            not self.predeclared
            or self.independently_sourced_claim
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "Contradiction Lens trial context crossed its evidence boundary."
            )
        payload = self.model_dump(mode="json", exclude={"context_id"})
        if self.context_id != stable_id(
            "contradiction_lens_trial_context", payload
        ):
            raise ValueError("Contradiction Lens trial-context checksum mismatch.")
        return self


def _lens_lineage(context: ContradictionLensTrialContext) -> tuple[Any, ...]:
    controlled = context.controlled_context
    return (
        context.lens_fingerprint,
        context.definition_ref,
        context.binding_ref,
        context.lens_evidence_refs,
        context.lens_governance_refs,
        controlled.lens_ir_version,
        controlled.lens_ledger_schema_version,
        controlled.lens_definitions,
        controlled.lens_bindings,
        controlled.lens_evidence_history,
        controlled.lens_governance_history,
        controlled.operators,
    )


def _matched_control_signature(context: ContradictionLensTrialContext) -> str:
    functional = context.controlled_context.functional_context
    receipt = functional.hypothesis_bundle.evidence_receipt
    return stable_id(
        "contradiction_lens_trial_matched_controls",
        CONTRADICTION_LENS_TRIAL_CONTROL_VERSION,
        context.controlled_context.control_version,
        functional.context_version,
        functional.hypothesis_bundle.protocol_version,
        receipt.authorized_budget,
        functional.functional_alternatives,
        functional.route_count,
        context.controlled_context.operators,
        context.lens_fingerprint,
        context.definition_ref,
        context.binding_ref,
        context.lens_evidence_refs,
        context.lens_governance_refs,
    )


class ContradictionLensTrialPairContext(FrozenRecord):
    """Preregistered calibration and disjoint held-out contexts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pair_id: str
    control_version: str = CONTRADICTION_LENS_TRIAL_CONTROL_VERSION
    calibration: ContradictionLensTrialContext
    held_out: ContradictionLensTrialContext
    matched_control_signature: str
    lens_fingerprint: str
    definition_ref: str
    binding_ref: str
    independently_preregistered_contexts: bool = True
    disjoint_canonical_provenance_verified: bool = True
    identical_lens_lineage_verified: bool = True
    matched_controls_verified: bool = True
    real_world_source_independence_established: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        calibration: ContradictionLensTrialContext,
        held_out: ContradictionLensTrialContext,
    ) -> "ContradictionLensTrialPairContext":
        calibration = ContradictionLensTrialContext.model_validate(
            calibration.model_dump(mode="json")
        )
        held_out = ContradictionLensTrialContext.model_validate(
            held_out.model_dump(mode="json")
        )
        matched = _matched_control_signature(calibration)
        values = {
            "control_version": CONTRADICTION_LENS_TRIAL_CONTROL_VERSION,
            "calibration": calibration,
            "held_out": held_out,
            "matched_control_signature": matched,
            "lens_fingerprint": calibration.lens_fingerprint,
            "definition_ref": calibration.definition_ref,
            "binding_ref": calibration.binding_ref,
            "independently_preregistered_contexts": True,
            "disjoint_canonical_provenance_verified": True,
            "identical_lens_lineage_verified": True,
            "matched_controls_verified": True,
            "real_world_source_independence_established": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["pair_id"] = stable_id(
            "contradiction_lens_trial_pair_context", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_pair(self) -> "ContradictionLensTrialPairContext":
        if self.control_version != CONTRADICTION_LENS_TRIAL_CONTROL_VERSION:
            raise ValueError("Unknown Contradiction Lens pair-control version.")
        calibration = self.calibration
        held_out = self.held_out
        if (
            calibration.split != ContradictionLensTrialSplit.CALIBRATION
            or held_out.split != ContradictionLensTrialSplit.HELD_OUT
        ):
            raise ValueError(
                "Contradiction Lens pair requires calibration and held-out splits."
            )
        if _lens_lineage(calibration) != _lens_lineage(held_out):
            raise ValueError(
                "Contradiction Lens pair does not share identical Lens lineage."
            )
        calibration_controls = _matched_control_signature(calibration)
        held_out_controls = _matched_control_signature(held_out)
        if (
            calibration_controls != held_out_controls
            or self.matched_control_signature != calibration_controls
        ):
            raise ValueError("Contradiction Lens pair controls are not matched.")
        if (
            self.lens_fingerprint != calibration.lens_fingerprint
            or self.definition_ref != calibration.definition_ref
            or self.binding_ref != calibration.binding_ref
        ):
            raise ValueError("Contradiction Lens pair altered its shared Lens refs.")
        distinct_identifiers = (
            calibration.context_id != held_out.context_id,
            calibration.controlled_context.source_event_key
            != held_out.controlled_context.source_event_key,
            calibration.canonical_checkpoint_fingerprint
            != held_out.canonical_checkpoint_fingerprint,
            calibration.obligation_id != held_out.obligation_id,
            calibration.obligation_event_ref != held_out.obligation_event_ref,
            calibration.contradiction_ref != held_out.contradiction_ref,
            calibration.evidence_receipt_ref != held_out.evidence_receipt_ref,
        )
        disjoint_sets = (
            set(calibration.claim_refs).isdisjoint(held_out.claim_refs),
            set(calibration.protected_evidence_refs).isdisjoint(
                held_out.protected_evidence_refs
            ),
        )
        if not all((*distinct_identifiers, *disjoint_sets)):
            raise ValueError(
                "Contradiction held-out context is not canonically independent."
            )
        if (
            not self.independently_preregistered_contexts
            or not self.disjoint_canonical_provenance_verified
            or not self.identical_lens_lineage_verified
            or not self.matched_controls_verified
            or self.real_world_source_independence_established
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "Contradiction Lens pair crossed its evidence boundary."
            )
        payload = self.model_dump(mode="json", exclude={"pair_id"})
        if self.pair_id != stable_id(
            "contradiction_lens_trial_pair_context", payload
        ):
            raise ValueError("Contradiction Lens pair-context checksum mismatch.")
        return self


def _structural_effect_signature(
    observation: ContradictionLensControlledObservation,
) -> str:
    functional = observation.functional_observation
    provenance = functional.provenance_observation
    route_shapes = tuple(
        sorted(
            (
                len(route.query_source_roots),
                len(route.baseline_routed_claim_refs),
                len(route.treatment_routed_claim_refs),
                route.query_claim_ref in route.treatment_routed_claim_refs,
                len(projection.projected_claim_refs),
                projection.operator.value,
            )
            for route, projection in zip(
                functional.claim_routes,
                observation.route_projections,
                strict=True,
            )
        )
    )
    return stable_id(
        "contradiction_lens_trial_structural_effect",
        CONTRADICTION_LENS_TRIAL_CONTROL_VERSION,
        provenance.matched_observation.effect.value,
        provenance.disposition.value,
        functional.disposition.value,
        len(provenance.shared_support_source_roots),
        len(provenance.symmetric_difference_source_roots),
        len(provenance.matched_observation.added_record_refs),
        route_shapes,
        observation.controlled_context.operators,
    )


class ContradictionLensTrialObservation(FrozenRecord):
    """One actual v0.37 run verified against its preregistered split context."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    observer_version: str = CONTRADICTION_LENS_TRIAL_CONTROL_VERSION
    context: ContradictionLensTrialContext
    lens_observation: ContradictionLensControlledObservation
    resolution_evidence: ContradictionLensResolutionEvidenceReceipt
    structural_effect_signature: str
    context_lineage_verified: bool = True
    evidence_preserved: bool = True
    matched_control_verified: bool = True
    simulated_only: bool = True
    dimensional_separation_observed: bool = False
    source_independence_observed: bool = False
    predictive_discrimination_observed: bool = False
    independent_held_out_replication_observed: bool = False
    external_outcome_observed: bool = False
    resolution_trial_ready: bool = False
    truth_selection_authority_enabled: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        context: ContradictionLensTrialContext,
        run: ContradictionLensControlledRun,
    ) -> "ContradictionLensTrialObservation":
        context = ContradictionLensTrialContext.model_validate(
            context.model_dump(mode="json")
        )
        lens_observation = ContradictionLensControlledObservation.model_validate(
            run.lens_observation.model_dump(mode="json")
        )
        coverage = ContradictionLensResolutionEvidenceReceipt.model_validate(
            run.resolution_evidence.model_dump(mode="json")
        )
        if run.controlled_context != context.controlled_context:
            raise ValueError(
                "Contradiction Lens trial run differs from its preregistration."
            )
        values = {
            "observer_version": CONTRADICTION_LENS_TRIAL_CONTROL_VERSION,
            "context": context,
            "lens_observation": lens_observation,
            "resolution_evidence": coverage,
            "structural_effect_signature": _structural_effect_signature(
                lens_observation
            ),
            "context_lineage_verified": True,
            "evidence_preserved": True,
            "matched_control_verified": True,
            "simulated_only": True,
            "dimensional_separation_observed": False,
            "source_independence_observed": False,
            "predictive_discrimination_observed": False,
            "independent_held_out_replication_observed": False,
            "external_outcome_observed": False,
            "resolution_trial_ready": False,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["observation_id"] = stable_id(
            "contradiction_lens_trial_observation", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_observation(self) -> "ContradictionLensTrialObservation":
        if self.observer_version != CONTRADICTION_LENS_TRIAL_CONTROL_VERSION:
            raise ValueError("Unknown Contradiction Lens trial-observer version.")
        context = self.context
        lens_observation = self.lens_observation
        coverage = self.resolution_evidence
        base = coverage.base_resolution_evidence
        if (
            lens_observation.controlled_context != context.controlled_context
            or coverage.lens_observation != lens_observation
            or base.canonical_checkpoint_fingerprint
            != context.canonical_checkpoint_fingerprint
            or base.obligation_id != context.obligation_id
            or base.obligation_event_ref != context.obligation_event_ref
            or base.evidence_receipt_ref != context.evidence_receipt_ref
            or base.protected_claim_refs != context.claim_refs
            or base.protected_evidence_refs != context.protected_evidence_refs
            or coverage.lens_fingerprint != context.lens_fingerprint
            or coverage.definition_ref != context.definition_ref
            or coverage.binding_ref != context.binding_ref
        ):
            raise ValueError(
                "Contradiction Lens trial observation lost exact context lineage."
            )
        if self.structural_effect_signature != _structural_effect_signature(
            lens_observation
        ):
            raise ValueError(
                "Contradiction Lens trial structural signature was altered."
            )
        if (
            coverage.grounded_requirements
            != CONTRADICTION_LENS_GROUNDED_REQUIREMENTS
            or coverage.missing_requirements
            != CONTRADICTION_LENS_MISSING_REQUIREMENTS
        ):
            raise ValueError(
                "Contradiction Lens trial observation hid a resolution gap."
            )
        if (
            not self.context_lineage_verified
            or not self.evidence_preserved
            or not self.matched_control_verified
            or not self.simulated_only
            or self.dimensional_separation_observed
            or self.source_independence_observed
            or self.predictive_discrimination_observed
            or self.independent_held_out_replication_observed
            or self.external_outcome_observed
            or self.resolution_trial_ready
            or self.truth_selection_authority_enabled
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "Contradiction Lens trial observation crossed its claim boundary."
            )
        payload = self.model_dump(mode="json", exclude={"observation_id"})
        if self.observation_id != stable_id(
            "contradiction_lens_trial_observation", payload
        ):
            raise ValueError("Contradiction Lens trial-observation checksum mismatch.")
        return self


class ContradictionLensHeldOutReplicationReceipt(FrozenRecord):
    """Cross-context structural result without predictive or resolution authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    receipt_version: str = CONTRADICTION_LENS_HELD_OUT_REPLICATION_VERSION
    pair_context: ContradictionLensTrialPairContext
    calibration_observation: ContradictionLensTrialObservation
    held_out_observation: ContradictionLensTrialObservation
    calibration_effect_signature: str
    held_out_effect_signature: str
    disposition: ContradictionLensReplicationDisposition
    grounded_requirements: tuple[ContradictionResolutionRequirement, ...]
    missing_requirements: tuple[ContradictionResolutionRequirement, ...]
    independently_preregistered_contexts_verified: bool = True
    disjoint_canonical_provenance_verified: bool = True
    identical_lens_lineage_verified: bool = True
    matched_controls_verified: bool = True
    evidence_preserved: bool = True
    deterministic_internal_replication_only: bool = True
    structural_effect_replicated: bool
    dimensional_separation_observed: bool = False
    source_independence_observed: bool = False
    predictive_discrimination_observed: bool = False
    independent_held_out_replication_observed: bool = False
    external_outcome_observed: bool = False
    resolution_trial_ready: bool = False
    truth_selection_authority_enabled: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        pair_context: ContradictionLensTrialPairContext,
        calibration_observation: ContradictionLensTrialObservation,
        held_out_observation: ContradictionLensTrialObservation,
    ) -> "ContradictionLensHeldOutReplicationReceipt":
        pair_context = ContradictionLensTrialPairContext.model_validate(
            pair_context.model_dump(mode="json")
        )
        calibration_observation = ContradictionLensTrialObservation.model_validate(
            calibration_observation.model_dump(mode="json")
        )
        held_out_observation = ContradictionLensTrialObservation.model_validate(
            held_out_observation.model_dump(mode="json")
        )
        replicated = (
            calibration_observation.structural_effect_signature
            == held_out_observation.structural_effect_signature
        )
        disposition = (
            ContradictionLensReplicationDisposition.STRUCTURAL_EFFECT_REPLICATED
            if replicated
            else ContradictionLensReplicationDisposition.VALID_NULL_DIVERGENT_EFFECT
        )
        values = {
            "receipt_version": CONTRADICTION_LENS_HELD_OUT_REPLICATION_VERSION,
            "pair_context": pair_context,
            "calibration_observation": calibration_observation,
            "held_out_observation": held_out_observation,
            "calibration_effect_signature": (
                calibration_observation.structural_effect_signature
            ),
            "held_out_effect_signature": held_out_observation.structural_effect_signature,
            "disposition": disposition,
            "grounded_requirements": CONTRADICTION_LENS_GROUNDED_REQUIREMENTS,
            "missing_requirements": CONTRADICTION_LENS_MISSING_REQUIREMENTS,
            "independently_preregistered_contexts_verified": True,
            "disjoint_canonical_provenance_verified": True,
            "identical_lens_lineage_verified": True,
            "matched_controls_verified": True,
            "evidence_preserved": True,
            "deterministic_internal_replication_only": True,
            "structural_effect_replicated": replicated,
            "dimensional_separation_observed": False,
            "source_independence_observed": False,
            "predictive_discrimination_observed": False,
            "independent_held_out_replication_observed": False,
            "external_outcome_observed": False,
            "resolution_trial_ready": False,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["receipt_id"] = stable_id(
            "contradiction_lens_held_out_replication", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "ContradictionLensHeldOutReplicationReceipt":
        if self.receipt_version != CONTRADICTION_LENS_HELD_OUT_REPLICATION_VERSION:
            raise ValueError("Unknown Contradiction held-out receipt version.")
        pair = self.pair_context
        calibration = self.calibration_observation
        held_out = self.held_out_observation
        if (
            calibration.context != pair.calibration
            or held_out.context != pair.held_out
            or self.calibration_effect_signature
            != calibration.structural_effect_signature
            or self.held_out_effect_signature
            != held_out.structural_effect_signature
        ):
            raise ValueError(
                "Contradiction held-out receipt lost split observation lineage."
            )
        expected_replicated = (
            self.calibration_effect_signature == self.held_out_effect_signature
        )
        expected_disposition = (
            ContradictionLensReplicationDisposition.STRUCTURAL_EFFECT_REPLICATED
            if expected_replicated
            else ContradictionLensReplicationDisposition.VALID_NULL_DIVERGENT_EFFECT
        )
        if (
            self.structural_effect_replicated != expected_replicated
            or self.disposition != expected_disposition
        ):
            raise ValueError(
                "Contradiction held-out structural result was altered."
            )
        if (
            self.grounded_requirements
            != CONTRADICTION_LENS_GROUNDED_REQUIREMENTS
            or self.missing_requirements
            != CONTRADICTION_LENS_MISSING_REQUIREMENTS
        ):
            raise ValueError(
                "Contradiction held-out receipt hid or invented a requirement."
            )
        if set(self.grounded_requirements).intersection(self.missing_requirements):
            raise ValueError("Contradiction held-out requirements overlap.")
        if set((*self.grounded_requirements, *self.missing_requirements)) != set(
            ContradictionResolutionRequirement
        ):
            raise ValueError(
                "Contradiction held-out coverage is not exhaustive."
            )
        if (
            not self.independently_preregistered_contexts_verified
            or not self.disjoint_canonical_provenance_verified
            or not self.identical_lens_lineage_verified
            or not self.matched_controls_verified
            or not self.evidence_preserved
            or not self.deterministic_internal_replication_only
            or self.dimensional_separation_observed
            or self.source_independence_observed
            or self.predictive_discrimination_observed
            or self.independent_held_out_replication_observed
            or self.external_outcome_observed
            or self.resolution_trial_ready
            or self.truth_selection_authority_enabled
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "Contradiction held-out receipt crossed its claim boundary."
            )
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != stable_id(
            "contradiction_lens_held_out_replication", payload
        ):
            raise ValueError("Contradiction held-out receipt checksum mismatch.")
        return self


@dataclass(frozen=True)
class ContradictionLensHeldOutTrialRun:
    pair_context: ContradictionLensTrialPairContext
    calibration_run: ContradictionLensControlledRun
    held_out_run: ContradictionLensControlledRun
    receipt: ContradictionLensHeldOutReplicationReceipt

    @property
    def replayed(self) -> bool:
        return self.calibration_run.replayed and self.held_out_run.replayed


class ContradictionLensHeldOutTrialRunner:
    """Stage both independent pairs and publish both ledgers atomically."""

    def __init__(
        self,
        *,
        controlled_runner: ContradictionLensControlledProbeRunner | None = None,
        hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
    ) -> None:
        self.hypothesis_protocol = (
            hypothesis_protocol or ContradictionHypothesisProtocol()
        )
        self.controlled_runner = (
            controlled_runner
            or ContradictionLensControlledProbeRunner(
                hypothesis_protocol=self.hypothesis_protocol
            )
        )

    def run(
        self,
        calibration_kernel: VerdantKernel,
        calibration_runtime: CounterfactualRuntime,
        held_out_kernel: VerdantKernel,
        held_out_runtime: CounterfactualRuntime,
        lenses: EquivalenceLensSystem,
        *,
        calibration_bundle: ContradictionHypothesisBundle,
        held_out_bundle: ContradictionHypothesisBundle,
        pair_context: ContradictionLensTrialPairContext,
    ) -> ContradictionLensHeldOutTrialRun:
        if calibration_kernel is held_out_kernel:
            raise ContradictionLensTrialIntegrityError(
                "Contradiction held-out trial requires separate canonical kernels."
            )
        if (
            calibration_runtime is held_out_runtime
            or calibration_runtime.ledger is held_out_runtime.ledger
        ):
            raise ContradictionLensTrialIntegrityError(
                "Contradiction held-out trial requires separate simulation ledgers."
            )
        canonical_before = (
            calibration_kernel.fingerprint(),
            held_out_kernel.fingerprint(),
        )
        simulation_before = (
            calibration_runtime.ledger.fingerprint(),
            held_out_runtime.ledger.fingerprint(),
        )
        lens_before = lenses.fingerprint()
        original_calibration = calibration_runtime.ledger.snapshot()
        original_held_out = held_out_runtime.ledger.snapshot()
        published = False
        try:
            pair = ContradictionLensTrialPairContext.model_validate(
                pair_context.model_dump(mode="json")
            )
            expected_calibration = ContradictionLensTrialContext.build(
                calibration_kernel,
                calibration_bundle,
                lenses,
                split=ContradictionLensTrialSplit.CALIBRATION,
                source_event_key=(
                    pair.calibration.controlled_context.source_event_key
                ),
                hypothesis_protocol=self.hypothesis_protocol,
            )
            expected_held_out = ContradictionLensTrialContext.build(
                held_out_kernel,
                held_out_bundle,
                lenses,
                split=ContradictionLensTrialSplit.HELD_OUT,
                source_event_key=pair.held_out.controlled_context.source_event_key,
                hypothesis_protocol=self.hypothesis_protocol,
            )
            expected_pair = ContradictionLensTrialPairContext.build(
                calibration=expected_calibration,
                held_out=expected_held_out,
            )
            if pair != expected_pair:
                raise ContradictionLensTrialIntegrityError(
                    "Contradiction held-out controls are stale or substituted."
                )
            calibration_working = CounterfactualRuntime(
                SimulationLedger.from_state(original_calibration)
            )
            held_out_working = CounterfactualRuntime(
                SimulationLedger.from_state(original_held_out)
            )
            calibration_run = self.controlled_runner.run(
                calibration_kernel,
                calibration_working,
                lenses,
                bundle=calibration_bundle,
                controlled_context=pair.calibration.controlled_context,
                source_event_key=(
                    pair.calibration.controlled_context.source_event_key
                ),
            )
            held_out_run = self.controlled_runner.run(
                held_out_kernel,
                held_out_working,
                lenses,
                bundle=held_out_bundle,
                controlled_context=pair.held_out.controlled_context,
                source_event_key=pair.held_out.controlled_context.source_event_key,
            )
            calibration_observation = ContradictionLensTrialObservation.build(
                context=pair.calibration,
                run=calibration_run,
            )
            held_out_observation = ContradictionLensTrialObservation.build(
                context=pair.held_out,
                run=held_out_run,
            )
            receipt = ContradictionLensHeldOutReplicationReceipt.build(
                pair_context=pair,
                calibration_observation=calibration_observation,
                held_out_observation=held_out_observation,
            )
            if (
                calibration_kernel.fingerprint() != canonical_before[0]
                or held_out_kernel.fingerprint() != canonical_before[1]
                or lenses.fingerprint() != lens_before
            ):
                raise ContradictionLensTrialIntegrityError(
                    "Contradiction held-out trial crossed a protected ledger."
                )
            calibration_state = calibration_working.ledger.snapshot()
            held_out_state = held_out_working.ledger.snapshot()
            try:
                calibration_runtime.ledger.state = calibration_state
                held_out_runtime.ledger.state = held_out_state
            except Exception:
                calibration_runtime.ledger.state = original_calibration
                held_out_runtime.ledger.state = original_held_out
                raise
            published = True
            return ContradictionLensHeldOutTrialRun(
                pair_context=pair,
                calibration_run=calibration_run,
                held_out_run=held_out_run,
                receipt=receipt,
            )
        except ContradictionLensTrialIntegrityError:
            raise
        except (
            ContradictionHypothesisIntegrityError,
            ContradictionLensControlIntegrityError,
            LensIntegrityError,
            SimulationIntegrityError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            raise ContradictionLensTrialIntegrityError(str(exc)) from exc
        finally:
            if (
                calibration_kernel.fingerprint() != canonical_before[0]
                or held_out_kernel.fingerprint() != canonical_before[1]
            ):
                raise RuntimeError(
                    "Contradiction held-out runner mutated canonical state."
                )
            if lenses.fingerprint() != lens_before:
                raise RuntimeError(
                    "Contradiction held-out runner mutated its Lens sidecar."
                )
            if not published and (
                calibration_runtime.ledger.fingerprint() != simulation_before[0]
                or held_out_runtime.ledger.fingerprint() != simulation_before[1]
            ):
                raise RuntimeError(
                    "Failed Contradiction held-out runner published partial state."
                )


class ContradictionLensTrialSidecarEnvelope(BaseModel):
    """Durable preregistration and optional completed receipt, outside VDK."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: str = CONTRADICTION_LENS_TRIAL_SIDECAR_FORMAT
    pair_context_sha256: str
    receipt_sha256: str | None = None
    calibration_simulation_fingerprint: str | None = None
    held_out_simulation_fingerprint: str | None = None
    pair_context: ContradictionLensTrialPairContext
    receipt: ContradictionLensHeldOutReplicationReceipt | None = None

    @classmethod
    def build(
        cls,
        pair_context: ContradictionLensTrialPairContext,
        *,
        receipt: ContradictionLensHeldOutReplicationReceipt | None = None,
        calibration_ledger: SimulationLedger | None = None,
        held_out_ledger: SimulationLedger | None = None,
    ) -> "ContradictionLensTrialSidecarEnvelope":
        pair = ContradictionLensTrialPairContext.model_validate(
            pair_context.model_dump(mode="json")
        )
        if receipt is None:
            if calibration_ledger is not None or held_out_ledger is not None:
                raise ValueError(
                    "Preregistration-only sidecars cannot claim simulation state."
                )
            normalized_receipt = None
            receipt_sha256 = None
            calibration_fingerprint = None
            held_out_fingerprint = None
        else:
            if calibration_ledger is None or held_out_ledger is None:
                raise ValueError(
                    "Completed trial sidecars require both simulation ledgers."
                )
            normalized_receipt = (
                ContradictionLensHeldOutReplicationReceipt.model_validate(
                    receipt.model_dump(mode="json")
                )
            )
            receipt_sha256 = _digest(
                canonical_json_bytes(normalized_receipt.model_dump(mode="json"))
            )
            calibration_fingerprint = calibration_ledger.fingerprint()
            held_out_fingerprint = held_out_ledger.fingerprint()
        return cls(
            pair_context_sha256=_digest(
                canonical_json_bytes(pair.model_dump(mode="json"))
            ),
            receipt_sha256=receipt_sha256,
            calibration_simulation_fingerprint=calibration_fingerprint,
            held_out_simulation_fingerprint=held_out_fingerprint,
            pair_context=pair,
            receipt=normalized_receipt,
        )

    @model_validator(mode="after")
    def validate_envelope(self) -> "ContradictionLensTrialSidecarEnvelope":
        if self.format_version != CONTRADICTION_LENS_TRIAL_SIDECAR_FORMAT:
            raise ValueError("Unsupported Contradiction Lens trial sidecar format.")
        expected_pair = _digest(
            canonical_json_bytes(self.pair_context.model_dump(mode="json"))
        )
        if self.pair_context_sha256 != expected_pair:
            raise ValueError("Contradiction Lens trial pair checksum mismatch.")
        if self.receipt is None:
            if any(
                item is not None
                for item in (
                    self.receipt_sha256,
                    self.calibration_simulation_fingerprint,
                    self.held_out_simulation_fingerprint,
                )
            ):
                raise ValueError(
                    "Preregistration-only sidecar carries completed-run fields."
                )
            return self
        if self.receipt.pair_context != self.pair_context:
            raise ValueError("Contradiction trial receipt names a different pair.")
        expected_receipt = _digest(
            canonical_json_bytes(self.receipt.model_dump(mode="json"))
        )
        if self.receipt_sha256 != expected_receipt:
            raise ValueError("Contradiction Lens trial receipt checksum mismatch.")
        fingerprints = (
            self.calibration_simulation_fingerprint,
            self.held_out_simulation_fingerprint,
        )
        if any(item is None or not _is_sha256(item) for item in fingerprints):
            raise ValueError(
                "Completed Contradiction trial sidecar requires ledger fingerprints."
            )
        return self


def _validate_observation_ledger(
    kernel: VerdantKernel,
    ledger: SimulationLedger,
    observation: ContradictionLensTrialObservation,
) -> None:
    base = observation.resolution_evidence.base_resolution_evidence
    provenance = base.provenance_observation
    probe = provenance.probe
    matched = provenance.matched_observation
    by_reservation = {
        item.reservation_id: item for item in ledger.state.reservations
    }
    by_settlement = {
        item.settlement_id: item for item in ledger.state.settlements
    }
    for plan, trace in (
        (probe.baseline_plan, matched.baseline),
        (probe.treatment_plan, matched.treatment),
    ):
        reservation = by_reservation.get(trace.reservation_id)
        settlement = by_settlement.get(trace.settlement_id)
        if reservation is None or settlement is None:
            raise ContradictionLensTrialIntegrityError(
                "Contradiction trial sidecar lost a simulation settlement."
            )
        rebuilt = derive_counterfactual_execution_trace(
            kernel,
            ledger,
            plan=plan,
            reservation=reservation,
            settlement=settlement,
        )
        if rebuilt != trace:
            raise ContradictionLensTrialIntegrityError(
                "Contradiction trial sidecar crossed simulation lineage."
            )


def _validate_sidecar_pairing(
    envelope: ContradictionLensTrialSidecarEnvelope,
    *,
    calibration_kernel: VerdantKernel,
    held_out_kernel: VerdantKernel,
    lenses: EquivalenceLensSystem,
    calibration_ledger: SimulationLedger | None,
    held_out_ledger: SimulationLedger | None,
) -> None:
    pair = envelope.pair_context
    if (
        pair.calibration.canonical_checkpoint_fingerprint
        != calibration_kernel.fingerprint()
        or pair.held_out.canonical_checkpoint_fingerprint
        != held_out_kernel.fingerprint()
        or pair.lens_fingerprint != lenses.fingerprint()
    ):
        raise ContradictionLensTrialIntegrityError(
            "Contradiction trial sidecar is paired with different protected state."
        )
    expected_calibration = ContradictionLensTrialContext.build(
        calibration_kernel,
        pair.calibration.controlled_context.functional_context.hypothesis_bundle,
        lenses,
        split=ContradictionLensTrialSplit.CALIBRATION,
        source_event_key=pair.calibration.controlled_context.source_event_key,
    )
    expected_held_out = ContradictionLensTrialContext.build(
        held_out_kernel,
        pair.held_out.controlled_context.functional_context.hypothesis_bundle,
        lenses,
        split=ContradictionLensTrialSplit.HELD_OUT,
        source_event_key=pair.held_out.controlled_context.source_event_key,
    )
    if pair != ContradictionLensTrialPairContext.build(
        calibration=expected_calibration,
        held_out=expected_held_out,
    ):
        raise ContradictionLensTrialIntegrityError(
            "Contradiction trial sidecar controls are stale or substituted."
        )
    if envelope.receipt is None:
        return
    if calibration_ledger is None or held_out_ledger is None:
        raise ContradictionLensTrialIntegrityError(
            "Completed Contradiction trial sidecar requires both ledgers."
        )
    if (
        envelope.calibration_simulation_fingerprint
        != calibration_ledger.fingerprint()
        or envelope.held_out_simulation_fingerprint
        != held_out_ledger.fingerprint()
    ):
        raise ContradictionLensTrialIntegrityError(
            "Contradiction trial sidecar is paired with different simulation state."
        )
    _validate_observation_ledger(
        calibration_kernel,
        calibration_ledger,
        envelope.receipt.calibration_observation,
    )
    _validate_observation_ledger(
        held_out_kernel,
        held_out_ledger,
        envelope.receipt.held_out_observation,
    )


def contradiction_lens_trial_sidecar_bytes(
    pair_context: ContradictionLensTrialPairContext,
    *,
    receipt: ContradictionLensHeldOutReplicationReceipt | None = None,
    calibration_ledger: SimulationLedger | None = None,
    held_out_ledger: SimulationLedger | None = None,
) -> bytes:
    envelope = ContradictionLensTrialSidecarEnvelope.build(
        pair_context,
        receipt=receipt,
        calibration_ledger=calibration_ledger,
        held_out_ledger=held_out_ledger,
    )
    return canonical_json_bytes(envelope.model_dump(mode="json"))


def save_contradiction_lens_trial_sidecar(
    path: str | Path,
    pair_context: ContradictionLensTrialPairContext,
    *,
    receipt: ContradictionLensHeldOutReplicationReceipt | None = None,
    calibration_ledger: SimulationLedger | None = None,
    held_out_ledger: SimulationLedger | None = None,
) -> None:
    """Atomically save preregistration or completed evidence outside VDK/VOB."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = contradiction_lens_trial_sidecar_bytes(
        pair_context,
        receipt=receipt,
        calibration_ledger=calibration_ledger,
        held_out_ledger=held_out_ledger,
    )
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        temporary = None
        try:
            directory_fd = os.open(target.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def load_contradiction_lens_trial_sidecar(
    path: str | Path,
    *,
    calibration_kernel: VerdantKernel,
    held_out_kernel: VerdantKernel,
    lenses: EquivalenceLensSystem,
    calibration_ledger: SimulationLedger | None = None,
    held_out_ledger: SimulationLedger | None = None,
) -> ContradictionLensTrialSidecarEnvelope:
    """Load and revalidate a sidecar against both canonical and Lens states."""

    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_TRIAL_SIDECAR_BYTES:
            raise ContradictionLensTrialIntegrityError(
                "Contradiction Lens trial sidecar exceeds its size limit."
            )
        envelope = ContradictionLensTrialSidecarEnvelope.model_validate_json(data)
        _validate_sidecar_pairing(
            envelope,
            calibration_kernel=calibration_kernel,
            held_out_kernel=held_out_kernel,
            lenses=lenses,
            calibration_ledger=calibration_ledger,
            held_out_ledger=held_out_ledger,
        )
        return envelope
    except ContradictionLensTrialIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ContradictionLensTrialIntegrityError(str(exc)) from exc
