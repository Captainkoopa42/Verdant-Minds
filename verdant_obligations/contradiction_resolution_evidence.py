"""Resolution-evidence coverage for matched Contradiction probes.

The v0.36 probe establishes trace-backed structural and context-conditioned
functional routing while leaving predictive, independent, dimensional, and
external evidence unobserved.  This module records that boundary as a
self-validating receipt.  It cannot turn a simulation into an observed
outcome, select either opposed claim, or resolve an obligation.
"""
from __future__ import annotations

from enum import Enum

from pydantic import ConfigDict, Field, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, stable_id

from .contradiction_hypotheses import (
    ContradictionHypothesisBundle,
    ContradictionHypothesisIntegrityError,
    ContradictionHypothesisProtocol,
)
from .contradiction_functional_context import ContradictionFunctionalDisposition
from .contradiction_functional_probe import (
    ContradictionFunctionalObservation,
    ContradictionFunctionalProbeIntegrityError,
    ContradictionFunctionalProbeObserver,
)
from .contradiction_probes import (
    ContradictionProvenanceDisposition,
    ContradictionProvenanceObservation,
    ContradictionProvenanceProbeIntegrityError,
    ContradictionProvenanceProbeObserver,
    ContradictionProvenanceProbePolicy,
)
from .counterfactual import (
    CounterfactualRunResult,
    SimulationIntegrityError,
    SimulationLedger,
)


CONTRADICTION_RESOLUTION_EVIDENCE_VERSION = (
    "contradiction_resolution_evidence_coverage_v0.36"
)


class ContradictionResolutionEvidenceIntegrityError(RuntimeError):
    """Raised when coverage is not grounded in the matched simulation pair."""


class ContradictionResolutionRequirement(str, Enum):
    ACTIVE_FAMILY_LOCAL_LENS = "active_family_local_lens"
    ATTENTION_AUTHORIZATION = "attention_authorization"
    CANONICAL_CHECKPOINT = "canonical_checkpoint"
    CANONICAL_RECORD_PRESERVATION = "canonical_record_preservation"
    COMPLETE_EVIDENCE_LEDGER = "complete_evidence_ledger"
    CONTEXT_CONDITIONED_COMPATIBILITY = "context_conditioned_compatibility"
    DIMENSIONAL_SEPARATION = "dimensional_separation"
    EXTERNAL_OUTCOME = "external_outcome"
    FUNCTIONAL_CONSEQUENCE = "functional_consequence"
    INDEPENDENT_HELD_OUT_REPLICATION = "independent_held_out_replication"
    MATCHED_CONTROL = "matched_control"
    NULL_INCONCLUSIVE_COUNTERWEIGHTS = "null_inconclusive_counterweights"
    OPPOSED_CLAIM_PRESERVATION = "opposed_claim_preservation"
    PREDICTIVE_DISCRIMINATION = "predictive_discrimination"
    SETTLEMENT_LINEAGE = "settlement_lineage"
    SOURCE_INDEPENDENCE = "source_independence"
    SOURCE_PARTITION_MATERIALIZATION = "source_partition_materialization"
    STRUCTURAL_DELTA = "structural_delta"


CONTRADICTION_GROUNDED_REQUIREMENTS = tuple(
    sorted(
        (
            ContradictionResolutionRequirement.ATTENTION_AUTHORIZATION,
            ContradictionResolutionRequirement.CANONICAL_CHECKPOINT,
            ContradictionResolutionRequirement.CANONICAL_RECORD_PRESERVATION,
            ContradictionResolutionRequirement.COMPLETE_EVIDENCE_LEDGER,
            ContradictionResolutionRequirement.CONTEXT_CONDITIONED_COMPATIBILITY,
            ContradictionResolutionRequirement.FUNCTIONAL_CONSEQUENCE,
            ContradictionResolutionRequirement.MATCHED_CONTROL,
            ContradictionResolutionRequirement.NULL_INCONCLUSIVE_COUNTERWEIGHTS,
            ContradictionResolutionRequirement.OPPOSED_CLAIM_PRESERVATION,
            ContradictionResolutionRequirement.SETTLEMENT_LINEAGE,
            ContradictionResolutionRequirement.SOURCE_PARTITION_MATERIALIZATION,
            ContradictionResolutionRequirement.STRUCTURAL_DELTA,
        ),
        key=lambda item: item.value,
    )
)

CONTRADICTION_MISSING_REQUIREMENTS = tuple(
    sorted(
        (
            ContradictionResolutionRequirement.ACTIVE_FAMILY_LOCAL_LENS,
            ContradictionResolutionRequirement.DIMENSIONAL_SEPARATION,
            ContradictionResolutionRequirement.EXTERNAL_OUTCOME,
            ContradictionResolutionRequirement.INDEPENDENT_HELD_OUT_REPLICATION,
            ContradictionResolutionRequirement.PREDICTIVE_DISCRIMINATION,
            ContradictionResolutionRequirement.SOURCE_INDEPENDENCE,
        ),
        key=lambda item: item.value,
    )
)


class ContradictionResolutionEvidenceReceipt(FrozenRecord):
    """Exact account of what one matched provenance probe can establish."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    deriver_version: str = CONTRADICTION_RESOLUTION_EVIDENCE_VERSION
    hypothesis_bundle: ContradictionHypothesisBundle
    provenance_observation: ContradictionProvenanceObservation
    functional_observation: ContradictionFunctionalObservation
    obligation_id: str
    obligation_event_ref: str
    bundle_ref: str
    probe_ref: str
    evidence_receipt_ref: str
    matched_observation_ref: str
    functional_context_ref: str
    functional_observation_ref: str
    baseline_trace_ref: str
    treatment_trace_ref: str
    baseline_settlement_ref: str
    treatment_settlement_ref: str
    canonical_checkpoint_fingerprint: str
    protected_claim_refs: tuple[str, str]
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    shared_support_source_roots: tuple[str, ...] = ()
    symmetric_difference_source_roots: tuple[str, ...] = ()
    provenance_disposition: ContradictionProvenanceDisposition
    functional_disposition: ContradictionFunctionalDisposition
    baseline_function_signature: str
    treatment_function_signature: str
    structural_added_refs: tuple[str, ...] = Field(min_length=1)
    grounded_requirements: tuple[ContradictionResolutionRequirement, ...]
    missing_requirements: tuple[ContradictionResolutionRequirement, ...]
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
        hypothesis_bundle: ContradictionHypothesisBundle,
        provenance_observation: ContradictionProvenanceObservation,
        functional_observation: ContradictionFunctionalObservation,
    ) -> "ContradictionResolutionEvidenceReceipt":
        bundle = ContradictionHypothesisBundle.model_validate(
            hypothesis_bundle.model_dump(mode="json")
        )
        observation = ContradictionProvenanceObservation.model_validate(
            provenance_observation.model_dump(mode="json")
        )
        functional = ContradictionFunctionalObservation.model_validate(
            functional_observation.model_dump(mode="json")
        )
        probe = observation.probe
        evidence = probe.evidence_receipt
        matched = observation.matched_observation
        values = {
            "deriver_version": CONTRADICTION_RESOLUTION_EVIDENCE_VERSION,
            "hypothesis_bundle": bundle,
            "provenance_observation": observation,
            "functional_observation": functional,
            "obligation_id": evidence.obligation_id,
            "obligation_event_ref": evidence.obligation_event_ref,
            "bundle_ref": bundle.bundle_id,
            "probe_ref": probe.probe_id,
            "evidence_receipt_ref": evidence.receipt_id,
            "matched_observation_ref": observation.observation_id,
            "functional_context_ref": functional.functional_context.context_id,
            "functional_observation_ref": functional.observation_id,
            "baseline_trace_ref": matched.baseline.trace_id,
            "treatment_trace_ref": matched.treatment.trace_id,
            "baseline_settlement_ref": matched.baseline.settlement_id,
            "treatment_settlement_ref": matched.treatment.settlement_id,
            "canonical_checkpoint_fingerprint": (
                matched.baseline.canonical_fingerprint
            ),
            "protected_claim_refs": evidence.protected_claim_refs,
            "protected_evidence_refs": evidence.protected_evidence_refs,
            "shared_support_source_roots": evidence.shared_support_source_roots,
            "symmetric_difference_source_roots": (
                evidence.symmetric_difference_source_roots
            ),
            "provenance_disposition": observation.disposition,
            "functional_disposition": functional.disposition,
            "baseline_function_signature": (
                functional.baseline_function_signature
            ),
            "treatment_function_signature": (
                functional.treatment_function_signature
            ),
            "structural_added_refs": matched.added_record_refs,
            "grounded_requirements": CONTRADICTION_GROUNDED_REQUIREMENTS,
            "missing_requirements": CONTRADICTION_MISSING_REQUIREMENTS,
            "evidence_preserved": True,
            "matched_control_verified": True,
            "resolution_trial_ready": False,
            "simulated_only": True,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        payload = {
            key: (
                value.model_dump(mode="json")
                if hasattr(value, "model_dump")
                else value
            )
            for key, value in values.items()
        }
        values["receipt_id"] = stable_id(
            "contradiction_resolution_evidence_receipt",
            payload,
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "ContradictionResolutionEvidenceReceipt":
        if self.deriver_version != CONTRADICTION_RESOLUTION_EVIDENCE_VERSION:
            raise ValueError("Unknown Contradiction resolution-evidence version.")
        bundle = self.hypothesis_bundle
        observation = self.provenance_observation
        functional = self.functional_observation
        probe = observation.probe
        evidence = probe.evidence_receipt
        matched = observation.matched_observation
        hypothesis_refs = tuple(
            sorted(item.hypothesis_id for item in bundle.hypotheses)
        )
        if (
            bundle.bundle_id != probe.bundle_ref
            or bundle.evidence_receipt != evidence
            or probe.hypothesis_refs != hypothesis_refs
            or functional.provenance_observation != observation
            or functional.functional_context != probe.functional_context
        ):
            raise ValueError(
                "Contradiction coverage lost its complete hypothesis bundle."
            )
        expected = {
            "obligation_id": evidence.obligation_id,
            "obligation_event_ref": evidence.obligation_event_ref,
            "bundle_ref": bundle.bundle_id,
            "probe_ref": probe.probe_id,
            "evidence_receipt_ref": evidence.receipt_id,
            "matched_observation_ref": observation.observation_id,
            "functional_context_ref": functional.functional_context.context_id,
            "functional_observation_ref": functional.observation_id,
            "baseline_trace_ref": matched.baseline.trace_id,
            "treatment_trace_ref": matched.treatment.trace_id,
            "baseline_settlement_ref": matched.baseline.settlement_id,
            "treatment_settlement_ref": matched.treatment.settlement_id,
            "canonical_checkpoint_fingerprint": (
                matched.baseline.canonical_fingerprint
            ),
            "protected_claim_refs": evidence.protected_claim_refs,
            "protected_evidence_refs": evidence.protected_evidence_refs,
            "shared_support_source_roots": evidence.shared_support_source_roots,
            "symmetric_difference_source_roots": (
                evidence.symmetric_difference_source_roots
            ),
            "provenance_disposition": observation.disposition,
            "functional_disposition": functional.disposition,
            "baseline_function_signature": (
                functional.baseline_function_signature
            ),
            "treatment_function_signature": (
                functional.treatment_function_signature
            ),
            "structural_added_refs": matched.added_record_refs,
        }
        if any(getattr(self, key) != value for key, value in expected.items()):
            raise ValueError(
                "Contradiction coverage suppressed or altered matched evidence."
            )
        if self.grounded_requirements != CONTRADICTION_GROUNDED_REQUIREMENTS:
            raise ValueError("Contradiction grounded coverage was altered.")
        if self.missing_requirements != CONTRADICTION_MISSING_REQUIREMENTS:
            raise ValueError("Contradiction missing coverage was hidden or altered.")
        if set(self.grounded_requirements).intersection(self.missing_requirements):
            raise ValueError("Contradiction coverage requirements overlap.")
        if set((*self.grounded_requirements, *self.missing_requirements)) != set(
            ContradictionResolutionRequirement
        ):
            raise ValueError("Contradiction coverage does not account for every field.")
        if (
            not self.evidence_preserved
            or not self.matched_control_verified
            or self.resolution_trial_ready
            or not self.simulated_only
            or self.truth_selection_authority_enabled
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "Contradiction coverage cannot claim truth, outcome, or resolution."
            )
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != stable_id(
            "contradiction_resolution_evidence_receipt", payload
        ):
            raise ValueError("Contradiction resolution-evidence checksum mismatch.")
        return self


class ContradictionResolutionEvidenceDeriver:
    """Reconstruct one coverage receipt from the canonical and simulation ledgers."""

    def __init__(
        self,
        *,
        probe_policy: ContradictionProvenanceProbePolicy | None = None,
        hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
    ) -> None:
        self.hypothesis_protocol = (
            hypothesis_protocol or ContradictionHypothesisProtocol()
        )
        self.probe_observer = ContradictionProvenanceProbeObserver(
            policy=probe_policy,
            hypothesis_protocol=self.hypothesis_protocol,
        )
        self.functional_observer = ContradictionFunctionalProbeObserver(
            probe_policy=probe_policy,
            hypothesis_protocol=self.hypothesis_protocol,
        )

    def derive(
        self,
        kernel: VerdantKernel,
        ledger: SimulationLedger,
        *,
        hypothesis_bundle: ContradictionHypothesisBundle,
        baseline_result: CounterfactualRunResult,
        treatment_result: CounterfactualRunResult,
        provenance_observation: ContradictionProvenanceObservation,
        functional_observation: ContradictionFunctionalObservation,
    ) -> ContradictionResolutionEvidenceReceipt:
        canonical_before = kernel.fingerprint()
        ledger_before = ledger.fingerprint()
        try:
            bundle = ContradictionHypothesisBundle.model_validate(
                hypothesis_bundle.model_dump(mode="json")
            )
            observation = ContradictionProvenanceObservation.model_validate(
                provenance_observation.model_dump(mode="json")
            )
            functional = ContradictionFunctionalObservation.model_validate(
                functional_observation.model_dump(mode="json")
            )
            self.hypothesis_protocol.validate(kernel, bundle)
            verified = self.probe_observer.observe(
                kernel,
                ledger,
                bundle=bundle,
                probe=observation.probe,
                baseline_result=baseline_result,
                treatment_result=treatment_result,
            )
            if verified != observation:
                raise ContradictionResolutionEvidenceIntegrityError(
                    "Contradiction coverage observation differs from actual lineage."
                )
            verified_functional = self.functional_observer.observe(
                kernel,
                ledger,
                bundle=bundle,
                probe=observation.probe,
                baseline_result=baseline_result,
                treatment_result=treatment_result,
                provenance_observation=observation,
            )
            if verified_functional != functional:
                raise ContradictionResolutionEvidenceIntegrityError(
                    "Contradiction functional coverage differs from actual lineage."
                )
            evidence = observation.probe.evidence_receipt
            if (
                not set(evidence.protected_claim_refs).issubset(kernel.state.claims)
                or not set(evidence.protected_evidence_refs).issubset(
                    kernel.state.evidence
                )
            ):
                raise ContradictionResolutionEvidenceIntegrityError(
                    "Contradiction coverage lost protected canonical evidence."
                )
            if any(
                trace.canonical_fingerprint != canonical_before
                for trace in (
                    observation.matched_observation.baseline,
                    observation.matched_observation.treatment,
                )
            ):
                raise ContradictionResolutionEvidenceIntegrityError(
                    "Contradiction coverage crossed a canonical checkpoint."
                )
            return ContradictionResolutionEvidenceReceipt.build(
                hypothesis_bundle=bundle,
                provenance_observation=observation,
                functional_observation=functional,
            )
        except ContradictionResolutionEvidenceIntegrityError:
            raise
        except (
            ContradictionHypothesisIntegrityError,
            ContradictionProvenanceProbeIntegrityError,
            ContradictionFunctionalProbeIntegrityError,
            SimulationIntegrityError,
            ValueError,
            TypeError,
        ) as exc:
            raise ContradictionResolutionEvidenceIntegrityError(str(exc)) from exc
        finally:
            if kernel.fingerprint() != canonical_before:
                raise RuntimeError(
                    "Contradiction coverage derivation mutated canonical state."
                )
            if ledger.fingerprint() != ledger_before:
                raise RuntimeError(
                    "Contradiction coverage derivation mutated simulation state."
                )
