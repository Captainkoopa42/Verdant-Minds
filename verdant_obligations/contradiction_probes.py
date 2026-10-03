"""Matched, isolated provenance probes for Contradiction obligations.

The treatment materializes one typed provenance projection in a copy-on-write
overlay while the matched baseline applies no patch. Both arms retain the
complete v0.33 evidence receipt in their result lineage. The derived result
describes only the structural source-root partition already present in that
receipt; it cannot select a claim, establish truth, or resolve an obligation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, stable_id

from .contradiction_hypotheses import (
    ContradictionEvidenceReceipt,
    ContradictionHypothesisBundle,
    ContradictionHypothesisIntegrityError,
    ContradictionHypothesisProtocol,
)
from .contradiction_functional_context import (
    ContradictionFunctionalProbeContext,
)
from .counterfactual import (
    CounterfactualPatch,
    CounterfactualPlan,
    CounterfactualRunResult,
    CounterfactualRuntime,
    SimulationDisposition,
    SimulationIntegrityError,
    SimulationLedger,
)
from .trace_observations import (
    MatchedCounterfactualObserver,
    MatchedStructuralObservation,
    StructuralTraceEffect,
    TraceObservationIntegrityError,
)

if TYPE_CHECKING:
    from .contradiction_functional_probe import (
        ContradictionFunctionalObservation,
        ContradictionFunctionalProbeObserver,
    )
    from .contradiction_resolution_evidence import (
        ContradictionResolutionEvidenceReceipt,
    )


CONTRADICTION_PROVENANCE_PROBE_VERSION = "contradiction_provenance_probe_v0.36"


class ContradictionProvenanceProbeIntegrityError(RuntimeError):
    """Raised when a matched Contradiction probe loses exact lineage."""


class ContradictionProvenanceDisposition(str, Enum):
    DISTINCT_SOURCE_PARTITION = "distinct_source_partition"
    VALID_NULL_SHARED_SOURCES = "valid_null_shared_sources"
    INCONCLUSIVE_OVERLAPPING_SOURCES = "inconclusive_overlapping_sources"


class ContradictionProvenanceProbePolicy(BaseModel):
    """Visible simulation budget for the two-arm structural probe."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    probe_version: str = CONTRADICTION_PROVENANCE_PROBE_VERSION
    requested_budget_per_arm: float = Field(default=0.025, gt=0.0)
    consumed_budget_per_arm: float = Field(default=0.025, ge=0.0)
    arm_count: int = Field(default=2, ge=2, le=2)

    @model_validator(mode="after")
    def validate_policy(self) -> "ContradictionProvenanceProbePolicy":
        if self.probe_version != CONTRADICTION_PROVENANCE_PROBE_VERSION:
            raise ValueError("Unknown Contradiction provenance-probe version.")
        if self.consumed_budget_per_arm > self.requested_budget_per_arm + 1e-12:
            raise ValueError("Probe consumption cannot exceed its arm reservation.")
        return self


def _projection_id(
    *,
    source_event_key: str,
    bundle_ref: str,
    evidence_receipt_ref: str,
    functional_context_ref: str,
) -> str:
    return stable_id(
        "contradiction_provenance_projection",
        CONTRADICTION_PROVENANCE_PROBE_VERSION,
        source_event_key,
        bundle_ref,
        evidence_receipt_ref,
        functional_context_ref,
    )


def _projection_value(
    *,
    projection_id: str,
    bundle_ref: str,
    receipt: ContradictionEvidenceReceipt,
    hypothesis_refs: tuple[str, ...],
    functional_context: ContradictionFunctionalProbeContext,
) -> dict[str, Any]:
    return {
        "schema_version": CONTRADICTION_PROVENANCE_PROBE_VERSION,
        "projection_id": projection_id,
        "bundle_ref": bundle_ref,
        "evidence_receipt": receipt.model_dump(mode="json"),
        "hypothesis_refs": hypothesis_refs,
        "functional_context": functional_context.model_dump(mode="json"),
        "protected_claim_refs": receipt.protected_claim_refs,
        "protected_evidence_refs": receipt.protected_evidence_refs,
        "truth_selection_authority_enabled": False,
        "evidence_suppression_permitted": False,
        "resolution_authority_enabled": False,
        "canonical_commit_permitted": False,
    }


def _result_refs(
    *,
    projection_id: str,
    bundle_ref: str,
    receipt: ContradictionEvidenceReceipt,
    hypothesis_refs: tuple[str, ...],
    functional_context_ref: str,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                projection_id,
                bundle_ref,
                receipt.receipt_id,
                functional_context_ref,
                *hypothesis_refs,
                *receipt.protected_claim_refs,
                *receipt.protected_evidence_refs,
            }
        )
    )


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


class ContradictionProvenanceProbe(FrozenRecord):
    """Preregistered zero/full matched plans for one v0.33 bundle."""

    probe_id: str
    probe_version: str = CONTRADICTION_PROVENANCE_PROBE_VERSION
    source_event_key: str
    projection_id: str
    bundle_ref: str
    evidence_receipt: ContradictionEvidenceReceipt
    functional_context: ContradictionFunctionalProbeContext
    hypothesis_refs: tuple[str, ...] = Field(min_length=3, max_length=3)
    authorized_budget: float = Field(gt=0.0)
    requested_budget_per_arm: float = Field(gt=0.0)
    consumed_budget_per_arm: float = Field(ge=0.0)
    baseline_plan: CounterfactualPlan
    treatment_plan: CounterfactualPlan
    evidence_suppression_permitted: bool = False
    truth_selection_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        bundle: ContradictionHypothesisBundle,
        *,
        source_event_key: str,
        policy: ContradictionProvenanceProbePolicy | None = None,
    ) -> "ContradictionProvenanceProbe":
        policy = policy or ContradictionProvenanceProbePolicy()
        bundle = ContradictionHypothesisBundle.model_validate(
            bundle.model_dump(mode="json")
        )
        if not source_event_key.strip():
            raise ValueError("Contradiction provenance probe requires a source key.")
        receipt = bundle.evidence_receipt
        functional_context = ContradictionFunctionalProbeContext.build(bundle)
        hypothesis_refs = tuple(
            sorted(item.hypothesis_id for item in bundle.hypotheses)
        )
        projection_id = _projection_id(
            source_event_key=source_event_key,
            bundle_ref=bundle.bundle_id,
            evidence_receipt_ref=receipt.receipt_id,
            functional_context_ref=functional_context.context_id,
        )
        patch = CounterfactualPatch.upsert(
            "structures",
            projection_id,
            _projection_value(
                projection_id=projection_id,
                bundle_ref=bundle.bundle_id,
                receipt=receipt,
                hypothesis_refs=hypothesis_refs,
                functional_context=functional_context,
            ),
        )
        result_refs = _result_refs(
            projection_id=projection_id,
            bundle_ref=bundle.bundle_id,
            receipt=receipt,
            hypothesis_refs=hypothesis_refs,
            functional_context_ref=functional_context.context_id,
        )
        shared = {
            "operator_version": policy.probe_version,
            "requested_budget": policy.requested_budget_per_arm,
            "consumed_budget": policy.consumed_budget_per_arm,
            "patches": (patch,),
            "disposition": SimulationDisposition.DISCARDED,
            "result_refs": result_refs,
        }
        baseline = CounterfactualPlan.build(
            source_event_key=stable_id(
                "contradiction_provenance_baseline",
                policy.probe_version,
                source_event_key,
                bundle.bundle_id,
            ),
            apply_patch_count=0,
            **shared,
        )
        treatment = CounterfactualPlan.build(
            source_event_key=stable_id(
                "contradiction_provenance_treatment",
                policy.probe_version,
                source_event_key,
                bundle.bundle_id,
            ),
            apply_patch_count=1,
            **shared,
        )
        values = {
            "probe_version": policy.probe_version,
            "source_event_key": source_event_key,
            "projection_id": projection_id,
            "bundle_ref": bundle.bundle_id,
            "evidence_receipt": receipt,
            "functional_context": functional_context,
            "hypothesis_refs": hypothesis_refs,
            "authorized_budget": receipt.authorized_budget,
            "requested_budget_per_arm": policy.requested_budget_per_arm,
            "consumed_budget_per_arm": policy.consumed_budget_per_arm,
            "baseline_plan": baseline,
            "treatment_plan": treatment,
            "evidence_suppression_permitted": False,
            "truth_selection_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["probe_id"] = stable_id(
            "contradiction_provenance_probe", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_probe(self) -> "ContradictionProvenanceProbe":
        if self.probe_version != CONTRADICTION_PROVENANCE_PROBE_VERSION:
            raise ValueError("Unknown Contradiction provenance-probe version.")
        if not self.source_event_key.strip():
            raise ValueError("Contradiction provenance probe requires a source key.")
        if tuple(sorted(set(self.hypothesis_refs))) != self.hypothesis_refs:
            raise ValueError("Probe hypothesis refs must be sorted and unique.")
        expected_projection = _projection_id(
            source_event_key=self.source_event_key,
            bundle_ref=self.bundle_ref,
            evidence_receipt_ref=self.evidence_receipt.receipt_id,
            functional_context_ref=self.functional_context.context_id,
        )
        if self.projection_id != expected_projection:
            raise ValueError("Contradiction provenance projection identity drifted.")
        if self.authorized_budget != self.evidence_receipt.authorized_budget:
            raise ValueError("Probe Attention budget lost receipt lineage.")
        expected_context = ContradictionFunctionalProbeContext.build(
            self.functional_context.hypothesis_bundle
        )
        if (
            self.functional_context != expected_context
            or self.functional_context.hypothesis_bundle.bundle_id
            != self.bundle_ref
            or self.functional_context.hypothesis_bundle.evidence_receipt
            != self.evidence_receipt
            or self.functional_context.evidence_receipt_ref
            != self.evidence_receipt.receipt_id
            or tuple(
                sorted(
                    item.hypothesis_id
                    for item in self.functional_context.hypothesis_bundle.hypotheses
                )
            )
            != self.hypothesis_refs
        ):
            raise ValueError(
                "Contradiction probe lost its preregistered functional context."
            )
        if 2 * self.requested_budget_per_arm > self.authorized_budget + 1e-12:
            raise ValueError("Matched probe reservations exceed Attention budget.")
        if self.consumed_budget_per_arm > self.requested_budget_per_arm + 1e-12:
            raise ValueError("Probe consumption exceeds one arm reservation.")
        expected_patch = CounterfactualPatch.upsert(
            "structures",
            self.projection_id,
            _projection_value(
                projection_id=self.projection_id,
                bundle_ref=self.bundle_ref,
                receipt=self.evidence_receipt,
                hypothesis_refs=self.hypothesis_refs,
                functional_context=self.functional_context,
            ),
        )
        expected_refs = _result_refs(
            projection_id=self.projection_id,
            bundle_ref=self.bundle_ref,
            receipt=self.evidence_receipt,
            hypothesis_refs=self.hypothesis_refs,
            functional_context_ref=self.functional_context.context_id,
        )
        if any(
            plan.operator_version != self.probe_version
            or plan.requested_budget != self.requested_budget_per_arm
            or plan.consumed_budget != self.consumed_budget_per_arm
            or plan.patches != (expected_patch,)
            or plan.disposition != SimulationDisposition.DISCARDED
            or plan.termination_code is not None
            or plan.result_refs != expected_refs
            for plan in (self.baseline_plan, self.treatment_plan)
        ):
            raise ValueError("Contradiction matched plans lost exact probe controls.")
        expected_sources = (
            stable_id(
                "contradiction_provenance_baseline",
                self.probe_version,
                self.source_event_key,
                self.bundle_ref,
            ),
            stable_id(
                "contradiction_provenance_treatment",
                self.probe_version,
                self.source_event_key,
                self.bundle_ref,
            ),
        )
        if (
            self.baseline_plan.source_event_key != expected_sources[0]
            or self.treatment_plan.source_event_key != expected_sources[1]
            or self.baseline_plan.apply_patch_count != 0
            or self.treatment_plan.apply_patch_count != 1
        ):
            raise ValueError("Contradiction probe arm assignment drifted.")
        if any(
            (
                self.evidence_suppression_permitted,
                self.truth_selection_authority_enabled,
                self.resolution_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError("Contradiction provenance probes cannot carry authority.")
        payload = self.model_dump(mode="json", exclude={"probe_id"})
        if self.probe_id != stable_id("contradiction_provenance_probe", payload):
            raise ValueError("Contradiction provenance-probe checksum mismatch.")
        return self


def _disposition(
    receipt: ContradictionEvidenceReceipt,
) -> ContradictionProvenanceDisposition:
    shared = receipt.shared_support_source_roots
    distinct = receipt.symmetric_difference_source_roots
    if distinct and not shared:
        return ContradictionProvenanceDisposition.DISTINCT_SOURCE_PARTITION
    if not distinct:
        return ContradictionProvenanceDisposition.VALID_NULL_SHARED_SOURCES
    return ContradictionProvenanceDisposition.INCONCLUSIVE_OVERLAPPING_SOURCES


class ContradictionProvenanceObservation(FrozenRecord):
    """Trace-derived structural result with no truth or resolution authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    observer_version: str = CONTRADICTION_PROVENANCE_PROBE_VERSION
    probe: ContradictionProvenanceProbe
    matched_observation: MatchedStructuralObservation
    disposition: ContradictionProvenanceDisposition
    protected_claim_refs: tuple[str, str]
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    shared_support_source_roots: tuple[str, ...] = ()
    symmetric_difference_source_roots: tuple[str, ...] = ()
    evidence_preserved: bool = True
    matched_control_verified: bool = True
    simulated_only: bool = True
    truth_selection_authority_enabled: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        probe: ContradictionProvenanceProbe,
        matched_observation: MatchedStructuralObservation,
    ) -> "ContradictionProvenanceObservation":
        receipt = probe.evidence_receipt
        values = {
            "observer_version": CONTRADICTION_PROVENANCE_PROBE_VERSION,
            "probe": probe,
            "matched_observation": matched_observation,
            "disposition": _disposition(receipt),
            "protected_claim_refs": receipt.protected_claim_refs,
            "protected_evidence_refs": receipt.protected_evidence_refs,
            "shared_support_source_roots": receipt.shared_support_source_roots,
            "symmetric_difference_source_roots": (
                receipt.symmetric_difference_source_roots
            ),
            "evidence_preserved": True,
            "matched_control_verified": True,
            "simulated_only": True,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["observation_id"] = stable_id(
            "contradiction_provenance_observation", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_observation(self) -> "ContradictionProvenanceObservation":
        if self.observer_version != CONTRADICTION_PROVENANCE_PROBE_VERSION:
            raise ValueError("Unknown Contradiction provenance observer version.")
        receipt = self.probe.evidence_receipt
        if (
            self.protected_claim_refs != receipt.protected_claim_refs
            or self.protected_evidence_refs != receipt.protected_evidence_refs
            or self.shared_support_source_roots
            != receipt.shared_support_source_roots
            or self.symmetric_difference_source_roots
            != receipt.symmetric_difference_source_roots
        ):
            raise ValueError("Contradiction observation suppressed receipt evidence.")
        if self.disposition != _disposition(receipt):
            raise ValueError("Contradiction provenance disposition was altered.")
        matched = self.matched_observation
        expected_refs = self.probe.baseline_plan.result_refs
        if (
            matched.hypothesis_ref != self.probe.projection_id
            or matched.baseline.plan_id != self.probe.baseline_plan.plan_id
            or matched.treatment.plan_id != self.probe.treatment_plan.plan_id
            or matched.baseline.result_refs != expected_refs
            or matched.treatment.result_refs != expected_refs
        ):
            raise ValueError("Contradiction observation lost matched-plan lineage.")
        if any(
            trace.operator_version != self.probe.probe_version
            or trace.obligation_id != receipt.obligation_id
            or trace.attention_decision_id != receipt.attention_decision_ref
            or trace.allocation_id != receipt.attention_allocation_ref
            or trace.canonical_fingerprint
            != matched.baseline.canonical_fingerprint
            for trace in (matched.baseline, matched.treatment)
        ):
            raise ValueError("Contradiction observation crossed canonical lineage.")
        projection_ref = f"structures:{self.probe.projection_id}"
        if (
            matched.effect != StructuralTraceEffect.ADDITIVE_OVERLAY_EFFECT
            or matched.added_record_refs != (projection_ref,)
            or matched.removed_record_refs
            or matched.changed_record_refs
            or not matched.canonical_records_preserved
            or matched.baseline.applied_patch_ids
            or matched.treatment.applied_patch_ids
            != matched.treatment.declared_patch_ids
        ):
            raise ValueError(
                "Contradiction observation is not the declared additive projection."
            )
        if (
            not self.evidence_preserved
            or not self.matched_control_verified
            or not self.simulated_only
            or self.truth_selection_authority_enabled
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "Contradiction provenance observation crossed its authority boundary."
            )
        payload = self.model_dump(mode="json", exclude={"observation_id"})
        if self.observation_id != stable_id(
            "contradiction_provenance_observation", payload
        ):
            raise ValueError("Contradiction provenance observation checksum mismatch.")
        return self


class ContradictionProvenanceProbeObserver:
    """Rebuild real ledger traces and classify only their typed projection."""

    def __init__(
        self,
        *,
        policy: ContradictionProvenanceProbePolicy | None = None,
        hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
        matched_observer: MatchedCounterfactualObserver | None = None,
    ) -> None:
        self.policy = policy or ContradictionProvenanceProbePolicy()
        self.hypothesis_protocol = (
            hypothesis_protocol or ContradictionHypothesisProtocol()
        )
        self.matched_observer = matched_observer or MatchedCounterfactualObserver()

    def observe(
        self,
        kernel: VerdantKernel,
        ledger: SimulationLedger,
        *,
        bundle: ContradictionHypothesisBundle,
        probe: ContradictionProvenanceProbe,
        baseline_result: CounterfactualRunResult,
        treatment_result: CounterfactualRunResult,
    ) -> ContradictionProvenanceObservation:
        canonical_before = kernel.fingerprint()
        ledger_before = ledger.fingerprint()
        try:
            bundle = ContradictionHypothesisBundle.model_validate(
                bundle.model_dump(mode="json")
            )
            probe = ContradictionProvenanceProbe.model_validate(
                probe.model_dump(mode="json")
            )
            self.hypothesis_protocol.validate(kernel, bundle)
            expected_probe = ContradictionProvenanceProbe.build(
                bundle,
                source_event_key=probe.source_event_key,
                policy=self.policy,
            )
            if probe != expected_probe:
                raise ContradictionProvenanceProbeIntegrityError(
                    "Contradiction probe does not match its canonical bundle."
                )
            matched = self.matched_observer.observe(
                kernel,
                ledger,
                hypothesis_ref=probe.projection_id,
                baseline_plan=probe.baseline_plan,
                baseline_result=baseline_result,
                treatment_plan=probe.treatment_plan,
                treatment_result=treatment_result,
            )
            return ContradictionProvenanceObservation.build(
                probe=probe, matched_observation=matched
            )
        except ContradictionProvenanceProbeIntegrityError:
            raise
        except (
            ContradictionHypothesisIntegrityError,
            TraceObservationIntegrityError,
            SimulationIntegrityError,
            ValueError,
            TypeError,
        ) as exc:
            raise ContradictionProvenanceProbeIntegrityError(str(exc)) from exc
        finally:
            if kernel.fingerprint() != canonical_before:
                raise RuntimeError(
                    "Contradiction provenance observation mutated canonical state."
                )
            if ledger.fingerprint() != ledger_before:
                raise RuntimeError(
                    "Contradiction provenance observation mutated simulation state."
                )


@dataclass(frozen=True)
class ContradictionProvenanceProbeRun:
    probe: ContradictionProvenanceProbe
    baseline: CounterfactualRunResult
    treatment: CounterfactualRunResult
    observation: ContradictionProvenanceObservation
    functional_observation: "ContradictionFunctionalObservation"
    resolution_evidence: "ContradictionResolutionEvidenceReceipt"

    @property
    def replayed(self) -> bool:
        return self.baseline.replayed and self.treatment.replayed


class ContradictionProvenanceProbeRunner:
    """Stage both arms and publish only a complete verified simulation pair."""

    def __init__(
        self,
        *,
        policy: ContradictionProvenanceProbePolicy | None = None,
        hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
        observer: ContradictionProvenanceProbeObserver | None = None,
        functional_observer: "ContradictionFunctionalProbeObserver | None" = None,
    ) -> None:
        self.policy = policy or ContradictionProvenanceProbePolicy()
        self.hypothesis_protocol = (
            hypothesis_protocol or ContradictionHypothesisProtocol()
        )
        self.observer = observer or ContradictionProvenanceProbeObserver(
            policy=self.policy,
            hypothesis_protocol=self.hypothesis_protocol,
        )
        from .contradiction_functional_probe import (
            ContradictionFunctionalProbeObserver,
        )

        self.functional_observer = (
            functional_observer
            or ContradictionFunctionalProbeObserver(
                probe_policy=self.policy,
                hypothesis_protocol=self.hypothesis_protocol,
            )
        )

    def run(
        self,
        kernel: VerdantKernel,
        runtime: CounterfactualRuntime,
        *,
        bundle: ContradictionHypothesisBundle,
        source_event_key: str,
    ) -> ContradictionProvenanceProbeRun:
        canonical_before = kernel.fingerprint()
        original_ledger = runtime.ledger.snapshot()
        try:
            self.hypothesis_protocol.validate(kernel, bundle)
            probe = ContradictionProvenanceProbe.build(
                bundle,
                source_event_key=source_event_key,
                policy=self.policy,
            )
            if probe.projection_id in kernel.state.structures:
                raise ContradictionProvenanceProbeIntegrityError(
                    "Contradiction projection collides with a canonical structure."
                )
            working_runtime = CounterfactualRuntime(
                SimulationLedger.from_state(original_ledger)
            )
            baseline = working_runtime.execute(
                kernel,
                allocation_id=bundle.attention_allocation_ref,
                plan=probe.baseline_plan,
            )
            treatment = working_runtime.execute(
                kernel,
                allocation_id=bundle.attention_allocation_ref,
                plan=probe.treatment_plan,
            )
            observation = self.observer.observe(
                kernel,
                working_runtime.ledger,
                bundle=bundle,
                probe=probe,
                baseline_result=baseline,
                treatment_result=treatment,
            )
            functional_observation = self.functional_observer.observe(
                kernel,
                working_runtime.ledger,
                bundle=bundle,
                probe=probe,
                baseline_result=baseline,
                treatment_result=treatment,
                provenance_observation=observation,
            )
            from .contradiction_resolution_evidence import (
                ContradictionResolutionEvidenceDeriver,
            )

            resolution_evidence = ContradictionResolutionEvidenceDeriver(
                probe_policy=self.policy,
                hypothesis_protocol=self.hypothesis_protocol,
            ).derive(
                kernel,
                working_runtime.ledger,
                hypothesis_bundle=bundle,
                baseline_result=baseline,
                treatment_result=treatment,
                provenance_observation=observation,
                functional_observation=functional_observation,
            )
            if kernel.fingerprint() != canonical_before:
                raise ContradictionProvenanceProbeIntegrityError(
                    "Contradiction probe leaked into canonical state."
                )
            runtime.ledger.state = working_runtime.ledger.snapshot()
            return ContradictionProvenanceProbeRun(
                probe=probe,
                baseline=baseline,
                treatment=treatment,
                observation=observation,
                functional_observation=functional_observation,
                resolution_evidence=resolution_evidence,
            )
        except ContradictionProvenanceProbeIntegrityError:
            raise
        except (
            ContradictionHypothesisIntegrityError,
            TraceObservationIntegrityError,
            SimulationIntegrityError,
            ValueError,
            TypeError,
        ) as exc:
            raise ContradictionProvenanceProbeIntegrityError(str(exc)) from exc
        finally:
            if kernel.fingerprint() != canonical_before:
                raise RuntimeError("Contradiction provenance probe mutated canonical state.")
