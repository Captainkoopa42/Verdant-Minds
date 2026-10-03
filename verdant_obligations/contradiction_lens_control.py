"""Opt-in Equivalence-Lens control for the Contradiction functional probe.

The v0.36 provenance probe remains byte-for-byte compatible.  This module
adds a separately invoked wrapper whose caller must preregister a complete,
content-addressed snapshot of the active Contradiction-local Lens before the
matched simulation pair runs.  The Lens is then applied read-only to the two
actual treatment routes.  It cannot select a claim, alter a route, suppress
evidence, commit an overlay, or grant resolution authority.

The controlled context deliberately retains the complete Lens registry and
ledger histories rather than only a convenient binding identifier.  This
allows archive replay to reject validly rehashed substitution of another
definition, family binding, evidence history, or governance state.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import ObligationFamily, VerdantKernel
from verdant_kernel.models import FrozenRecord, stable_id

from .contradiction_functional_context import ContradictionFunctionalProbeContext
from .contradiction_functional_probe import (
    ContradictionFunctionalClaimRoute,
    ContradictionFunctionalObservation,
    ContradictionFunctionalProbeIntegrityError,
)
from .contradiction_hypotheses import (
    ContradictionHypothesisBundle,
    ContradictionHypothesisIntegrityError,
    ContradictionHypothesisProtocol,
)
from .contradiction_probes import (
    ContradictionProvenanceProbeIntegrityError,
    ContradictionProvenanceProbePolicy,
    ContradictionProvenanceProbeRun,
    ContradictionProvenanceProbeRunner,
)
from .contradiction_resolution_evidence import (
    CONTRADICTION_GROUNDED_REQUIREMENTS,
    CONTRADICTION_MISSING_REQUIREMENTS,
    ContradictionResolutionEvidenceDeriver,
    ContradictionResolutionEvidenceIntegrityError,
    ContradictionResolutionEvidenceReceipt,
    ContradictionResolutionRequirement,
)
from .counterfactual import (
    CounterfactualRuntime,
    SimulationIntegrityError,
    SimulationLedger,
)
from .equivalence import (
    EQUIVALENCE_LENS_IR_VERSION,
    LENS_LEDGER_SCHEMA_VERSION,
    EquivalenceLensDefinition,
    EquivalenceLensSystem,
    LensBinding,
    LensBindingLedgerState,
    LensBindingStatus,
    LensDefinitionRegistryState,
    LensEvidence,
    LensGovernanceEvent,
    LensIntegrityError,
    LensOpcode,
    LensUnavailableError,
)


CONTRADICTION_LENS_CONTROL_VERSION = "contradiction_lens_control_v0.37"
CONTRADICTION_LENS_COVERAGE_VERSION = (
    "contradiction_lens_resolution_evidence_v0.37"
)
CONTRADICTION_LENS_OPERATORS = (LensOpcode.SELECT_ACTIVATED_REFS,)

CONTRADICTION_LENS_GROUNDED_REQUIREMENTS = tuple(
    sorted(
        (
            *CONTRADICTION_GROUNDED_REQUIREMENTS,
            ContradictionResolutionRequirement.ACTIVE_FAMILY_LOCAL_LENS,
        ),
        key=lambda item: item.value,
    )
)
CONTRADICTION_LENS_MISSING_REQUIREMENTS = tuple(
    item
    for item in CONTRADICTION_MISSING_REQUIREMENTS
    if item != ContradictionResolutionRequirement.ACTIVE_FAMILY_LOCAL_LENS
)


class ContradictionLensControlIntegrityError(RuntimeError):
    """Raised when a controlled Lens use loses exact cross-ledger lineage."""


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


def _lens_system_from_history(
    *,
    definitions: tuple[EquivalenceLensDefinition, ...],
    bindings: tuple[LensBinding, ...],
    evidence: tuple[LensEvidence, ...],
    governance: tuple[LensGovernanceEvent, ...],
) -> EquivalenceLensSystem:
    registry = LensDefinitionRegistryState(
        definitions={item.definition_id: item for item in definitions}
    )
    ledger = LensBindingLedgerState(
        bindings=bindings,
        evidence=evidence,
        governance_events=governance,
    )
    return EquivalenceLensSystem(registry=registry, ledger=ledger)


class ContradictionLensControlledContext(FrozenRecord):
    """Immutable Lens plus functional context supplied before simulation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    context_id: str
    control_version: str = CONTRADICTION_LENS_CONTROL_VERSION
    source_event_key: str
    functional_context: ContradictionFunctionalProbeContext
    lens_ir_version: str = EQUIVALENCE_LENS_IR_VERSION
    lens_ledger_schema_version: str = LENS_LEDGER_SCHEMA_VERSION
    lens_definitions: tuple[EquivalenceLensDefinition, ...] = Field(min_length=1)
    lens_bindings: tuple[LensBinding, ...] = Field(min_length=1)
    lens_evidence_history: tuple[LensEvidence, ...] = Field(min_length=1)
    lens_governance_history: tuple[LensGovernanceEvent, ...] = Field(min_length=1)
    lens_fingerprint: str
    active_definition_ref: str
    active_binding_ref: str
    active_evidence_refs: tuple[str, ...] = Field(min_length=1)
    active_governance_refs: tuple[str, ...] = Field(min_length=1)
    obligation_family: ObligationFamily = ObligationFamily.CONTRADICTION
    operators: tuple[LensOpcode, ...] = CONTRADICTION_LENS_OPERATORS
    evidence_suppression_permitted: bool = False
    truth_selection_authority_enabled: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        hypothesis_bundle: ContradictionHypothesisBundle,
        lenses: EquivalenceLensSystem,
        *,
        source_event_key: str,
    ) -> "ContradictionLensControlledContext":
        if not source_event_key.strip():
            raise ContradictionLensControlIntegrityError(
                "Controlled Contradiction Lens context requires a source key."
            )
        bundle = ContradictionHypothesisBundle.model_validate(
            hypothesis_bundle.model_dump(mode="json")
        )
        registry, ledger = lenses.snapshot()
        snapshot = EquivalenceLensSystem(registry=registry, ledger=ledger)
        try:
            active = snapshot.active_binding(ObligationFamily.CONTRADICTION)
        except (LensIntegrityError, LensUnavailableError) as exc:
            raise ContradictionLensControlIntegrityError(str(exc)) from exc
        definition = snapshot.registry.definitions[active.binding.definition_id]
        if definition.operators != CONTRADICTION_LENS_OPERATORS:
            raise ContradictionLensControlIntegrityError(
                "Contradiction control requires the activated-reference Lens operator."
            )
        active_evidence = tuple(
            item
            for item in snapshot.ledger.evidence
            if item.binding_id == active.binding.binding_id
        )
        if not active_evidence:
            raise ContradictionLensControlIntegrityError(
                "Active Contradiction Lens requires an explicit evidence history."
            )
        active_governance = tuple(
            item
            for item in snapshot.ledger.governance_events
            if item.binding_id == active.binding.binding_id
            or item.target_binding_id == active.binding.binding_id
        )
        values = {
            "control_version": CONTRADICTION_LENS_CONTROL_VERSION,
            "source_event_key": source_event_key,
            "functional_context": ContradictionFunctionalProbeContext.build(bundle),
            "lens_ir_version": registry.ir_version,
            "lens_ledger_schema_version": ledger.schema_version,
            "lens_definitions": tuple(
                sorted(
                    registry.definitions.values(),
                    key=lambda item: item.definition_id,
                )
            ),
            "lens_bindings": ledger.bindings,
            "lens_evidence_history": ledger.evidence,
            "lens_governance_history": ledger.governance_events,
            "lens_fingerprint": snapshot.fingerprint(),
            "active_definition_ref": definition.definition_id,
            "active_binding_ref": active.binding.binding_id,
            "active_evidence_refs": tuple(
                item.evidence_id for item in active_evidence
            ),
            "active_governance_refs": tuple(
                item.event_id for item in active_governance
            ),
            "obligation_family": ObligationFamily.CONTRADICTION,
            "operators": CONTRADICTION_LENS_OPERATORS,
            "evidence_suppression_permitted": False,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["context_id"] = stable_id(
            "contradiction_lens_controlled_context", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_context(self) -> "ContradictionLensControlledContext":
        if self.control_version != CONTRADICTION_LENS_CONTROL_VERSION:
            raise ValueError("Unknown Contradiction Lens-control version.")
        if not self.source_event_key.strip():
            raise ValueError("Controlled Contradiction Lens source key is empty.")
        if (
            self.lens_ir_version != EQUIVALENCE_LENS_IR_VERSION
            or self.lens_ledger_schema_version != LENS_LEDGER_SCHEMA_VERSION
        ):
            raise ValueError("Contradiction Lens context uses an unsupported schema.")
        if tuple(
            sorted(self.lens_definitions, key=lambda item: item.definition_id)
        ) != self.lens_definitions:
            raise ValueError("Contradiction Lens definitions are not ID-sorted.")
        if len({item.definition_id for item in self.lens_definitions}) != len(
            self.lens_definitions
        ):
            raise ValueError("Contradiction Lens context duplicates a definition.")
        system = _lens_system_from_history(
            definitions=self.lens_definitions,
            bindings=self.lens_bindings,
            evidence=self.lens_evidence_history,
            governance=self.lens_governance_history,
        )
        if system.fingerprint() != self.lens_fingerprint:
            raise ValueError("Contradiction Lens snapshot fingerprint mismatch.")
        active = system.active_binding(ObligationFamily.CONTRADICTION)
        definition = system.registry.definitions[active.binding.definition_id]
        expected_evidence = tuple(
            item.evidence_id
            for item in system.ledger.evidence
            if item.binding_id == active.binding.binding_id
        )
        expected_governance = tuple(
            item.event_id
            for item in system.ledger.governance_events
            if item.binding_id == active.binding.binding_id
            or item.target_binding_id == active.binding.binding_id
        )
        if (
            active.status != LensBindingStatus.ACTIVE
            or self.obligation_family != ObligationFamily.CONTRADICTION
            or self.active_definition_ref != definition.definition_id
            or self.active_binding_ref != active.binding.binding_id
            or self.active_evidence_refs != expected_evidence
            or self.active_governance_refs != expected_governance
            or not expected_evidence
            or not expected_governance
            or active.last_governance_event_id != expected_governance[-1]
        ):
            raise ValueError(
                "Contradiction Lens context lost its active family-local lineage."
            )
        if (
            definition.operators != CONTRADICTION_LENS_OPERATORS
            or self.operators != CONTRADICTION_LENS_OPERATORS
        ):
            raise ValueError("Contradiction Lens operator boundary was altered.")
        expected_functional = ContradictionFunctionalProbeContext.build(
            self.functional_context.hypothesis_bundle
        )
        if self.functional_context != expected_functional:
            raise ValueError("Contradiction Lens context changed its functional query.")
        if any(
            (
                self.evidence_suppression_permitted,
                self.truth_selection_authority_enabled,
                self.observed_outcome_authority_enabled,
                self.resolution_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError("Contradiction Lens context cannot carry authority.")
        payload = self.model_dump(mode="json", exclude={"context_id"})
        if self.context_id != stable_id(
            "contradiction_lens_controlled_context", payload
        ):
            raise ValueError("Contradiction Lens-context checksum mismatch.")
        return self

    def lens_system(self) -> EquivalenceLensSystem:
        """Return a validated detached reconstruction of the embedded sidecar."""
        return _lens_system_from_history(
            definitions=self.lens_definitions,
            bindings=self.lens_bindings,
            evidence=self.lens_evidence_history,
            governance=self.lens_governance_history,
        )


class ContradictionLensRouteProjection(FrozenRecord):
    """Read-only activated-reference projection of one actual treatment route."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    projection_id: str
    projection_version: str = CONTRADICTION_LENS_CONTROL_VERSION
    controlled_context_ref: str
    functional_route_ref: str
    definition_ref: str
    binding_ref: str
    operator: LensOpcode = LensOpcode.SELECT_ACTIVATED_REFS
    query_claim_ref: str
    query_source_roots: tuple[str, ...] = Field(min_length=1)
    projected_claim_refs: tuple[str, ...] = Field(min_length=1)
    equivalence_signature: str
    truth_selection_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        context: ContradictionLensControlledContext,
        route: ContradictionFunctionalClaimRoute,
    ) -> "ContradictionLensRouteProjection":
        projected = route.treatment_routed_claim_refs
        signature = stable_id(
            "contradiction_lens_route_equivalence",
            CONTRADICTION_LENS_CONTROL_VERSION,
            context.active_definition_ref,
            LensOpcode.SELECT_ACTIVATED_REFS.value,
            projected,
        )
        values = {
            "projection_version": CONTRADICTION_LENS_CONTROL_VERSION,
            "controlled_context_ref": context.context_id,
            "functional_route_ref": route.route_id,
            "definition_ref": context.active_definition_ref,
            "binding_ref": context.active_binding_ref,
            "operator": LensOpcode.SELECT_ACTIVATED_REFS,
            "query_claim_ref": route.query_claim_ref,
            "query_source_roots": route.query_source_roots,
            "projected_claim_refs": projected,
            "equivalence_signature": signature,
            "truth_selection_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["projection_id"] = stable_id(
            "contradiction_lens_route_projection", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_projection(self) -> "ContradictionLensRouteProjection":
        if self.projection_version != CONTRADICTION_LENS_CONTROL_VERSION:
            raise ValueError("Unknown Contradiction Lens-projection version.")
        if self.operator != LensOpcode.SELECT_ACTIVATED_REFS:
            raise ValueError("Contradiction Lens projection changed operator.")
        for refs, label in (
            (self.query_source_roots, "query roots"),
            (self.projected_claim_refs, "projected claims"),
        ):
            if tuple(sorted(set(refs))) != refs:
                raise ValueError(
                    f"Contradiction Lens {label} must be sorted and unique."
                )
        expected_signature = stable_id(
            "contradiction_lens_route_equivalence",
            self.projection_version,
            self.definition_ref,
            self.operator.value,
            self.projected_claim_refs,
        )
        if self.equivalence_signature != expected_signature:
            raise ValueError("Contradiction Lens equivalence signature was altered.")
        if any(
            (
                self.truth_selection_authority_enabled,
                self.resolution_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError("Contradiction Lens projection cannot carry authority.")
        payload = self.model_dump(mode="json", exclude={"projection_id"})
        if self.projection_id != stable_id(
            "contradiction_lens_route_projection", payload
        ):
            raise ValueError("Contradiction Lens-projection checksum mismatch.")
        return self


def _expected_projections(
    context: ContradictionLensControlledContext,
    functional: ContradictionFunctionalObservation,
) -> tuple[ContradictionLensRouteProjection, ContradictionLensRouteProjection]:
    if functional.functional_context != context.functional_context:
        raise ValueError("Contradiction Lens and functional contexts disagree.")
    return tuple(
        ContradictionLensRouteProjection.build(context=context, route=route)
        for route in functional.claim_routes
    )


class ContradictionLensControlledObservation(FrozenRecord):
    """Verified Lens projection over the actual context-conditioned routes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    observer_version: str = CONTRADICTION_LENS_CONTROL_VERSION
    controlled_context: ContradictionLensControlledContext
    functional_observation: ContradictionFunctionalObservation
    route_projections: tuple[
        ContradictionLensRouteProjection,
        ContradictionLensRouteProjection,
    ]
    lens_fingerprint: str
    definition_ref: str
    binding_ref: str
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    governance_refs: tuple[str, ...] = Field(min_length=1)
    protected_claim_refs: tuple[str, str]
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    active_family_local_lens_observed: bool = True
    lens_projection_observed: bool = True
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
        controlled_context: ContradictionLensControlledContext,
        functional_observation: ContradictionFunctionalObservation,
    ) -> "ContradictionLensControlledObservation":
        context = ContradictionLensControlledContext.model_validate(
            controlled_context.model_dump(mode="json")
        )
        functional = ContradictionFunctionalObservation.model_validate(
            functional_observation.model_dump(mode="json")
        )
        values = {
            "observer_version": CONTRADICTION_LENS_CONTROL_VERSION,
            "controlled_context": context,
            "functional_observation": functional,
            "route_projections": _expected_projections(context, functional),
            "lens_fingerprint": context.lens_fingerprint,
            "definition_ref": context.active_definition_ref,
            "binding_ref": context.active_binding_ref,
            "evidence_refs": context.active_evidence_refs,
            "governance_refs": context.active_governance_refs,
            "protected_claim_refs": context.functional_context.claim_refs,
            "protected_evidence_refs": (
                context.functional_context.protected_evidence_refs
            ),
            "active_family_local_lens_observed": True,
            "lens_projection_observed": True,
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
            "contradiction_lens_controlled_observation", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_observation(self) -> "ContradictionLensControlledObservation":
        if self.observer_version != CONTRADICTION_LENS_CONTROL_VERSION:
            raise ValueError("Unknown Contradiction Lens observer version.")
        context = self.controlled_context
        functional = self.functional_observation
        expected = _expected_projections(context, functional)
        if self.route_projections != expected:
            raise ValueError("Contradiction Lens route projections were altered.")
        if (
            self.lens_fingerprint != context.lens_fingerprint
            or self.definition_ref != context.active_definition_ref
            or self.binding_ref != context.active_binding_ref
            or self.evidence_refs != context.active_evidence_refs
            or self.governance_refs != context.active_governance_refs
            or self.protected_claim_refs != context.functional_context.claim_refs
            or self.protected_evidence_refs
            != context.functional_context.protected_evidence_refs
        ):
            raise ValueError("Contradiction Lens observation lost exact lineage.")
        if (
            not self.active_family_local_lens_observed
            or not self.lens_projection_observed
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
                "Contradiction Lens observation crossed its evidence boundary."
            )
        payload = self.model_dump(mode="json", exclude={"observation_id"})
        if self.observation_id != stable_id(
            "contradiction_lens_controlled_observation", payload
        ):
            raise ValueError("Contradiction Lens-observation checksum mismatch.")
        return self


class ContradictionLensResolutionEvidenceReceipt(FrozenRecord):
    """Coverage extension that grounds only the active family-local Lens."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    coverage_version: str = CONTRADICTION_LENS_COVERAGE_VERSION
    base_resolution_evidence: ContradictionResolutionEvidenceReceipt
    lens_observation: ContradictionLensControlledObservation
    controlled_context_ref: str
    lens_fingerprint: str
    definition_ref: str
    binding_ref: str
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    governance_refs: tuple[str, ...] = Field(min_length=1)
    protected_claim_refs: tuple[str, str]
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    grounded_requirements: tuple[ContradictionResolutionRequirement, ...]
    missing_requirements: tuple[ContradictionResolutionRequirement, ...]
    active_family_local_lens_observed: bool = True
    evidence_preserved: bool = True
    matched_control_verified: bool = True
    resolution_trial_ready: bool = False
    simulated_only: bool = True
    truth_selection_authority_enabled: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        base_resolution_evidence: ContradictionResolutionEvidenceReceipt,
        lens_observation: ContradictionLensControlledObservation,
    ) -> "ContradictionLensResolutionEvidenceReceipt":
        base = ContradictionResolutionEvidenceReceipt.model_validate(
            base_resolution_evidence.model_dump(mode="json")
        )
        observation = ContradictionLensControlledObservation.model_validate(
            lens_observation.model_dump(mode="json")
        )
        values = {
            "coverage_version": CONTRADICTION_LENS_COVERAGE_VERSION,
            "base_resolution_evidence": base,
            "lens_observation": observation,
            "controlled_context_ref": observation.controlled_context.context_id,
            "lens_fingerprint": observation.lens_fingerprint,
            "definition_ref": observation.definition_ref,
            "binding_ref": observation.binding_ref,
            "evidence_refs": observation.evidence_refs,
            "governance_refs": observation.governance_refs,
            "protected_claim_refs": base.protected_claim_refs,
            "protected_evidence_refs": base.protected_evidence_refs,
            "grounded_requirements": CONTRADICTION_LENS_GROUNDED_REQUIREMENTS,
            "missing_requirements": CONTRADICTION_LENS_MISSING_REQUIREMENTS,
            "active_family_local_lens_observed": True,
            "evidence_preserved": True,
            "matched_control_verified": True,
            "resolution_trial_ready": False,
            "simulated_only": True,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["receipt_id"] = stable_id(
            "contradiction_lens_resolution_evidence", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "ContradictionLensResolutionEvidenceReceipt":
        if self.coverage_version != CONTRADICTION_LENS_COVERAGE_VERSION:
            raise ValueError("Unknown Contradiction Lens-coverage version.")
        base = self.base_resolution_evidence
        observation = self.lens_observation
        context = observation.controlled_context
        if (
            observation.functional_observation != base.functional_observation
            or context.functional_context
            != base.functional_observation.functional_context
            or self.controlled_context_ref != context.context_id
            or self.lens_fingerprint != observation.lens_fingerprint
            or self.definition_ref != observation.definition_ref
            or self.binding_ref != observation.binding_ref
            or self.evidence_refs != observation.evidence_refs
            or self.governance_refs != observation.governance_refs
            or self.protected_claim_refs != base.protected_claim_refs
            or self.protected_evidence_refs != base.protected_evidence_refs
        ):
            raise ValueError("Contradiction Lens coverage lost exact evidence lineage.")
        if (
            self.grounded_requirements
            != CONTRADICTION_LENS_GROUNDED_REQUIREMENTS
            or self.missing_requirements
            != CONTRADICTION_LENS_MISSING_REQUIREMENTS
        ):
            raise ValueError(
                "Contradiction Lens coverage hid or invented a requirement."
            )
        if set(self.grounded_requirements).intersection(self.missing_requirements):
            raise ValueError("Contradiction Lens coverage requirements overlap.")
        if set((*self.grounded_requirements, *self.missing_requirements)) != set(
            ContradictionResolutionRequirement
        ):
            raise ValueError("Contradiction Lens coverage is not exhaustive.")
        if (
            not self.active_family_local_lens_observed
            or not self.evidence_preserved
            or not self.matched_control_verified
            or self.resolution_trial_ready
            or not self.simulated_only
            or self.truth_selection_authority_enabled
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "Contradiction Lens coverage cannot claim truth or resolution."
            )
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != stable_id(
            "contradiction_lens_resolution_evidence", payload
        ):
            raise ValueError("Contradiction Lens-coverage checksum mismatch.")
        return self


class ContradictionLensControlledObserver:
    """Reverify both ledgers before applying the preregistered Lens."""

    def __init__(
        self,
        *,
        probe_policy: ContradictionProvenanceProbePolicy | None = None,
        hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
    ) -> None:
        self.hypothesis_protocol = (
            hypothesis_protocol or ContradictionHypothesisProtocol()
        )
        self.coverage_deriver = ContradictionResolutionEvidenceDeriver(
            probe_policy=probe_policy,
            hypothesis_protocol=self.hypothesis_protocol,
        )

    def observe(
        self,
        kernel: VerdantKernel,
        ledger: SimulationLedger,
        lenses: EquivalenceLensSystem,
        *,
        bundle: ContradictionHypothesisBundle,
        controlled_context: ContradictionLensControlledContext,
        probe_run: ContradictionProvenanceProbeRun,
    ) -> ContradictionLensControlledObservation:
        canonical_before = kernel.fingerprint()
        simulation_before = ledger.fingerprint()
        lens_before = lenses.fingerprint()
        try:
            bundle = ContradictionHypothesisBundle.model_validate(
                bundle.model_dump(mode="json")
            )
            context = ContradictionLensControlledContext.model_validate(
                controlled_context.model_dump(mode="json")
            )
            self.hypothesis_protocol.validate(kernel, bundle)
            expected_context = ContradictionLensControlledContext.build(
                bundle,
                lenses,
                source_event_key=context.source_event_key,
            )
            if context != expected_context:
                raise ContradictionLensControlIntegrityError(
                    "Controlled Contradiction Lens context differs from active sidecar."
                )
            base = self.coverage_deriver.derive(
                kernel,
                ledger,
                hypothesis_bundle=bundle,
                baseline_result=probe_run.baseline,
                treatment_result=probe_run.treatment,
                provenance_observation=probe_run.observation,
                functional_observation=probe_run.functional_observation,
            )
            if base != probe_run.resolution_evidence:
                raise ContradictionLensControlIntegrityError(
                    "Controlled Contradiction Lens run lost matched evidence."
                )
            if context.functional_context != probe_run.probe.functional_context:
                raise ContradictionLensControlIntegrityError(
                    "Controlled Contradiction Lens was not bound to the actual context."
                )
            return ContradictionLensControlledObservation.build(
                controlled_context=context,
                functional_observation=probe_run.functional_observation,
            )
        except ContradictionLensControlIntegrityError:
            raise
        except (
            ContradictionHypothesisIntegrityError,
            ContradictionProvenanceProbeIntegrityError,
            ContradictionFunctionalProbeIntegrityError,
            ContradictionResolutionEvidenceIntegrityError,
            LensIntegrityError,
            LensUnavailableError,
            SimulationIntegrityError,
            ValueError,
            TypeError,
        ) as exc:
            raise ContradictionLensControlIntegrityError(str(exc)) from exc
        finally:
            if kernel.fingerprint() != canonical_before:
                raise RuntimeError(
                    "Contradiction Lens observation mutated canonical state."
                )
            if ledger.fingerprint() != simulation_before:
                raise RuntimeError(
                    "Contradiction Lens observation mutated simulation state."
                )
            if lenses.fingerprint() != lens_before:
                raise RuntimeError(
                    "Contradiction Lens observation mutated its sidecar."
                )


@dataclass(frozen=True)
class ContradictionLensControlledRun:
    controlled_context: ContradictionLensControlledContext
    probe_run: ContradictionProvenanceProbeRun
    lens_observation: ContradictionLensControlledObservation
    resolution_evidence: ContradictionLensResolutionEvidenceReceipt

    @property
    def replayed(self) -> bool:
        return self.probe_run.replayed


class ContradictionLensControlledProbeRunner:
    """Atomically publish the old pair only after Lens-control verification."""

    def __init__(
        self,
        *,
        probe_policy: ContradictionProvenanceProbePolicy | None = None,
        hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
        probe_runner: ContradictionProvenanceProbeRunner | None = None,
        observer: ContradictionLensControlledObserver | None = None,
    ) -> None:
        self.hypothesis_protocol = (
            hypothesis_protocol or ContradictionHypothesisProtocol()
        )
        self.probe_runner = probe_runner or ContradictionProvenanceProbeRunner(
            policy=probe_policy,
            hypothesis_protocol=self.hypothesis_protocol,
        )
        self.observer = observer or ContradictionLensControlledObserver(
            probe_policy=probe_policy,
            hypothesis_protocol=self.hypothesis_protocol,
        )

    def run(
        self,
        kernel: VerdantKernel,
        runtime: CounterfactualRuntime,
        lenses: EquivalenceLensSystem,
        *,
        bundle: ContradictionHypothesisBundle,
        controlled_context: ContradictionLensControlledContext,
        source_event_key: str,
    ) -> ContradictionLensControlledRun:
        canonical_before = kernel.fingerprint()
        lens_before = lenses.fingerprint()
        simulation_before = runtime.ledger.fingerprint()
        original_ledger = runtime.ledger.snapshot()
        published = False
        try:
            context = ContradictionLensControlledContext.model_validate(
                controlled_context.model_dump(mode="json")
            )
            if context.source_event_key != source_event_key:
                raise ContradictionLensControlIntegrityError(
                    "Controlled Contradiction Lens source key changed after "
                    "preregistration."
                )
            expected_context = ContradictionLensControlledContext.build(
                bundle,
                lenses,
                source_event_key=source_event_key,
            )
            if context != expected_context:
                raise ContradictionLensControlIntegrityError(
                    "Controlled Contradiction Lens context is stale or substituted."
                )
            working_runtime = CounterfactualRuntime(
                SimulationLedger.from_state(original_ledger)
            )
            probe_run = self.probe_runner.run(
                kernel,
                working_runtime,
                bundle=bundle,
                source_event_key=source_event_key,
            )
            observation = self.observer.observe(
                kernel,
                working_runtime.ledger,
                lenses,
                bundle=bundle,
                controlled_context=context,
                probe_run=probe_run,
            )
            coverage = ContradictionLensResolutionEvidenceReceipt.build(
                base_resolution_evidence=probe_run.resolution_evidence,
                lens_observation=observation,
            )
            if (
                kernel.fingerprint() != canonical_before
                or lenses.fingerprint() != lens_before
            ):
                raise ContradictionLensControlIntegrityError(
                    "Controlled Contradiction Lens run crossed a protected ledger."
                )
            result = ContradictionLensControlledRun(
                controlled_context=context,
                probe_run=probe_run,
                lens_observation=observation,
                resolution_evidence=coverage,
            )
            runtime.ledger.state = working_runtime.ledger.snapshot()
            published = True
            return result
        except ContradictionLensControlIntegrityError:
            raise
        except (
            ContradictionHypothesisIntegrityError,
            ContradictionProvenanceProbeIntegrityError,
            ContradictionFunctionalProbeIntegrityError,
            ContradictionResolutionEvidenceIntegrityError,
            LensIntegrityError,
            LensUnavailableError,
            SimulationIntegrityError,
            ValueError,
            TypeError,
        ) as exc:
            raise ContradictionLensControlIntegrityError(str(exc)) from exc
        finally:
            if kernel.fingerprint() != canonical_before:
                raise RuntimeError("Contradiction Lens runner mutated canonical state.")
            if lenses.fingerprint() != lens_before:
                raise RuntimeError("Contradiction Lens runner mutated its sidecar.")
            if not published and runtime.ledger.fingerprint() != simulation_before:
                raise RuntimeError(
                    "Failed Contradiction Lens runner published partial simulation "
                    "state."
                )
