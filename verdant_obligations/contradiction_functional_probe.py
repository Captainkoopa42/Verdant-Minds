"""Trace-derived functional routing for matched Contradiction probes.

This observer reconstructs both copy-on-write overlays from their actual
settlements.  The baseline must lack the preregistered projection and the
treatment must contain its exact content-addressed context.  It then performs
only the two declared source-root queries.  The resulting routing difference
is a bounded simulated functional consequence, not prediction, truth,
external outcome, source independence, or resolution evidence.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, stable_id

from .contradiction_functional_context import (
    CONTRADICTION_FUNCTIONAL_CONTEXT_VERSION,
    ContradictionFunctionalDisposition,
    ContradictionFunctionalProbeContext,
)
from .contradiction_hypotheses import (
    ContradictionHypothesisBundle,
    ContradictionHypothesisIntegrityError,
    ContradictionHypothesisProtocol,
)
from .contradiction_probes import (
    ContradictionProvenanceObservation,
    ContradictionProvenanceProbe,
    ContradictionProvenanceProbeIntegrityError,
    ContradictionProvenanceProbeObserver,
    ContradictionProvenanceProbePolicy,
)
from .counterfactual import (
    CounterfactualOverlay,
    CounterfactualRunResult,
    SimulationIntegrityError,
    SimulationLedger,
)


CONTRADICTION_FUNCTIONAL_PROBE_VERSION = (
    "contradiction_functional_probe_v0.36"
)


class ContradictionFunctionalProbeIntegrityError(
    ContradictionProvenanceProbeIntegrityError
):
    """Raised when functional routing is not grounded in the matched ledgers."""


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


def _route_signature(
    *,
    context_ref: str,
    query_claim_ref: str,
    query_source_roots: tuple[str, ...],
    projection_present: bool,
    routed_claim_refs: tuple[str, ...],
) -> str:
    return stable_id(
        "contradiction_functional_route_state",
        CONTRADICTION_FUNCTIONAL_PROBE_VERSION,
        context_ref,
        query_claim_ref,
        query_source_roots,
        projection_present,
        routed_claim_refs,
    )


def _routed_claims(
    context: ContradictionFunctionalProbeContext,
    query_source_roots: tuple[str, ...],
) -> tuple[str, ...]:
    query = set(query_source_roots)
    return tuple(
        sorted(
            claim_ref
            for claim_ref, candidate_roots in zip(
                context.claim_refs,
                context.query_source_roots,
                strict=True,
            )
            if query.intersection(candidate_roots)
        )
    )


def _functional_disposition(
    context: ContradictionFunctionalProbeContext,
) -> ContradictionFunctionalDisposition:
    left = set(context.query_source_roots[0])
    right = set(context.query_source_roots[1])
    if not left.intersection(right):
        return ContradictionFunctionalDisposition.DISTINCT_CONTEXTUAL_ROUTING
    if left == right:
        return ContradictionFunctionalDisposition.VALID_NULL_SHARED_ROUTING
    return ContradictionFunctionalDisposition.INCONCLUSIVE_OVERLAPPING_ROUTING


class ContradictionFunctionalClaimRoute(FrozenRecord):
    """One preregistered claim-local query before and after the projection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    route_id: str
    route_version: str = CONTRADICTION_FUNCTIONAL_PROBE_VERSION
    context_ref: str
    query_claim_ref: str
    query_source_roots: tuple[str, ...] = Field(min_length=1)
    baseline_projection_present: bool = False
    treatment_projection_present: bool = True
    baseline_routed_claim_refs: tuple[str, ...] = ()
    treatment_routed_claim_refs: tuple[str, ...] = Field(min_length=1)
    baseline_route_signature: str
    treatment_route_signature: str
    truth_selection_authority_enabled: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        context: ContradictionFunctionalProbeContext,
        query_claim_ref: str,
        query_source_roots: tuple[str, ...],
    ) -> "ContradictionFunctionalClaimRoute":
        routed = _routed_claims(context, query_source_roots)
        values = {
            "route_version": CONTRADICTION_FUNCTIONAL_PROBE_VERSION,
            "context_ref": context.context_id,
            "query_claim_ref": query_claim_ref,
            "query_source_roots": query_source_roots,
            "baseline_projection_present": False,
            "treatment_projection_present": True,
            "baseline_routed_claim_refs": (),
            "treatment_routed_claim_refs": routed,
            "baseline_route_signature": _route_signature(
                context_ref=context.context_id,
                query_claim_ref=query_claim_ref,
                query_source_roots=query_source_roots,
                projection_present=False,
                routed_claim_refs=(),
            ),
            "treatment_route_signature": _route_signature(
                context_ref=context.context_id,
                query_claim_ref=query_claim_ref,
                query_source_roots=query_source_roots,
                projection_present=True,
                routed_claim_refs=routed,
            ),
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["route_id"] = stable_id(
            "contradiction_functional_claim_route", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_route(self) -> "ContradictionFunctionalClaimRoute":
        if self.route_version != CONTRADICTION_FUNCTIONAL_PROBE_VERSION:
            raise ValueError("Unknown Contradiction functional-route version.")
        if not self.context_ref.strip() or not self.query_claim_ref.strip():
            raise ValueError("Contradiction functional route lost its identity.")
        for refs, label in (
            (self.query_source_roots, "query roots"),
            (self.baseline_routed_claim_refs, "baseline claims"),
            (self.treatment_routed_claim_refs, "treatment claims"),
        ):
            if tuple(sorted(set(refs))) != refs:
                raise ValueError(
                    f"Contradiction functional {label} must be sorted and unique."
                )
        if (
            self.baseline_projection_present
            or not self.treatment_projection_present
            or self.baseline_routed_claim_refs
        ):
            raise ValueError(
                "Contradiction functional route lost its matched projection control."
            )
        expected_baseline = _route_signature(
            context_ref=self.context_ref,
            query_claim_ref=self.query_claim_ref,
            query_source_roots=self.query_source_roots,
            projection_present=False,
            routed_claim_refs=(),
        )
        expected_treatment = _route_signature(
            context_ref=self.context_ref,
            query_claim_ref=self.query_claim_ref,
            query_source_roots=self.query_source_roots,
            projection_present=True,
            routed_claim_refs=self.treatment_routed_claim_refs,
        )
        if (
            self.baseline_route_signature != expected_baseline
            or self.treatment_route_signature != expected_treatment
        ):
            raise ValueError("Contradiction functional route signature was altered.")
        if any(
            (
                self.truth_selection_authority_enabled,
                self.observed_outcome_authority_enabled,
                self.resolution_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError("Contradiction functional route cannot carry authority.")
        payload = self.model_dump(mode="json", exclude={"route_id"})
        if self.route_id != stable_id(
            "contradiction_functional_claim_route", payload
        ):
            raise ValueError("Contradiction functional-route checksum mismatch.")
        return self


def _expected_routes(
    context: ContradictionFunctionalProbeContext,
) -> tuple[ContradictionFunctionalClaimRoute, ContradictionFunctionalClaimRoute]:
    return tuple(
        ContradictionFunctionalClaimRoute.build(
            context=context,
            query_claim_ref=claim_ref,
            query_source_roots=query_roots,
        )
        for claim_ref, query_roots in zip(
            context.claim_refs,
            context.query_source_roots,
            strict=True,
        )
    )


class ContradictionFunctionalObservation(FrozenRecord):
    """Actual-overlay routing delta with hard non-authority boundaries."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    observer_version: str = CONTRADICTION_FUNCTIONAL_PROBE_VERSION
    functional_context: ContradictionFunctionalProbeContext
    provenance_observation: ContradictionProvenanceObservation
    claim_routes: tuple[
        ContradictionFunctionalClaimRoute,
        ContradictionFunctionalClaimRoute,
    ]
    disposition: ContradictionFunctionalDisposition
    baseline_function_signature: str
    treatment_function_signature: str
    functional_consequence_observed: bool = True
    context_conditioned_compatibility_observed: bool = True
    evidence_preserved: bool = True
    matched_control_verified: bool = True
    simulated_only: bool = True
    predictive_discrimination_observed: bool = False
    source_independence_observed: bool = False
    dimensional_separation_observed: bool = False
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
        functional_context: ContradictionFunctionalProbeContext,
        provenance_observation: ContradictionProvenanceObservation,
    ) -> "ContradictionFunctionalObservation":
        context = ContradictionFunctionalProbeContext.model_validate(
            functional_context.model_dump(mode="json")
        )
        provenance = ContradictionProvenanceObservation.model_validate(
            provenance_observation.model_dump(mode="json")
        )
        routes = _expected_routes(context)
        baseline_signature = stable_id(
            "contradiction_functional_baseline_signature",
            CONTRADICTION_FUNCTIONAL_PROBE_VERSION,
            context.context_id,
            tuple(route.baseline_route_signature for route in routes),
        )
        treatment_signature = stable_id(
            "contradiction_functional_treatment_signature",
            CONTRADICTION_FUNCTIONAL_PROBE_VERSION,
            context.context_id,
            tuple(route.treatment_route_signature for route in routes),
        )
        values = {
            "observer_version": CONTRADICTION_FUNCTIONAL_PROBE_VERSION,
            "functional_context": context,
            "provenance_observation": provenance,
            "claim_routes": routes,
            "disposition": _functional_disposition(context),
            "baseline_function_signature": baseline_signature,
            "treatment_function_signature": treatment_signature,
            "functional_consequence_observed": True,
            "context_conditioned_compatibility_observed": True,
            "evidence_preserved": True,
            "matched_control_verified": True,
            "simulated_only": True,
            "predictive_discrimination_observed": False,
            "source_independence_observed": False,
            "dimensional_separation_observed": False,
            "independent_held_out_replication_observed": False,
            "external_outcome_observed": False,
            "resolution_trial_ready": False,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["observation_id"] = stable_id(
            "contradiction_functional_observation", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_observation(self) -> "ContradictionFunctionalObservation":
        if self.observer_version != CONTRADICTION_FUNCTIONAL_PROBE_VERSION:
            raise ValueError("Unknown Contradiction functional-observer version.")
        context = self.functional_context
        provenance = self.provenance_observation
        if (
            provenance.probe.functional_context != context
            or provenance.probe.bundle_ref != context.bundle_ref
            or provenance.protected_claim_refs != context.claim_refs
            or provenance.protected_evidence_refs
            != context.protected_evidence_refs
        ):
            raise ValueError(
                "Contradiction functional observation lost protected lineage."
            )
        expected_routes = _expected_routes(context)
        if self.claim_routes != expected_routes:
            raise ValueError("Contradiction functional routes were altered.")
        expected_baseline = stable_id(
            "contradiction_functional_baseline_signature",
            self.observer_version,
            context.context_id,
            tuple(route.baseline_route_signature for route in expected_routes),
        )
        expected_treatment = stable_id(
            "contradiction_functional_treatment_signature",
            self.observer_version,
            context.context_id,
            tuple(route.treatment_route_signature for route in expected_routes),
        )
        if (
            self.baseline_function_signature != expected_baseline
            or self.treatment_function_signature != expected_treatment
            or self.baseline_function_signature == self.treatment_function_signature
        ):
            raise ValueError(
                "Contradiction functional before/after signatures were altered."
            )
        if self.disposition != _functional_disposition(context):
            raise ValueError("Contradiction functional disposition was altered.")
        if (
            not self.functional_consequence_observed
            or not self.context_conditioned_compatibility_observed
            or not self.evidence_preserved
            or not self.matched_control_verified
            or not self.simulated_only
            or self.predictive_discrimination_observed
            or self.source_independence_observed
            or self.dimensional_separation_observed
            or self.independent_held_out_replication_observed
            or self.external_outcome_observed
            or self.resolution_trial_ready
            or self.truth_selection_authority_enabled
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "Contradiction functional observation crossed its evidence boundary."
            )
        payload = self.model_dump(mode="json", exclude={"observation_id"})
        if self.observation_id != stable_id(
            "contradiction_functional_observation", payload
        ):
            raise ValueError("Contradiction functional-observation checksum mismatch.")
        return self


class ContradictionFunctionalProbeObserver:
    """Reconstruct matched overlays and execute only the declared routes."""

    def __init__(
        self,
        *,
        probe_policy: ContradictionProvenanceProbePolicy | None = None,
        hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
    ) -> None:
        self.hypothesis_protocol = (
            hypothesis_protocol or ContradictionHypothesisProtocol()
        )
        self.provenance_observer = ContradictionProvenanceProbeObserver(
            policy=probe_policy,
            hypothesis_protocol=self.hypothesis_protocol,
        )

    def observe(
        self,
        kernel: VerdantKernel,
        ledger: SimulationLedger,
        *,
        bundle: ContradictionHypothesisBundle,
        probe: ContradictionProvenanceProbe,
        baseline_result: CounterfactualRunResult,
        treatment_result: CounterfactualRunResult,
        provenance_observation: ContradictionProvenanceObservation,
    ) -> ContradictionFunctionalObservation:
        canonical_before = kernel.fingerprint()
        ledger_before = ledger.fingerprint()
        try:
            bundle = ContradictionHypothesisBundle.model_validate(
                bundle.model_dump(mode="json")
            )
            probe = ContradictionProvenanceProbe.model_validate(
                probe.model_dump(mode="json")
            )
            provenance = ContradictionProvenanceObservation.model_validate(
                provenance_observation.model_dump(mode="json")
            )
            self.hypothesis_protocol.validate(kernel, bundle)
            verified_provenance = self.provenance_observer.observe(
                kernel,
                ledger,
                bundle=bundle,
                probe=probe,
                baseline_result=baseline_result,
                treatment_result=treatment_result,
            )
            if verified_provenance != provenance:
                raise ContradictionFunctionalProbeIntegrityError(
                    "Contradiction functional probe lost provenance lineage."
                )

            baseline_overlay = CounterfactualOverlay(kernel)
            for patch in probe.baseline_plan.patches[
                : probe.baseline_plan.apply_patch_count
            ]:
                baseline_overlay.apply(patch)
            treatment_overlay = CounterfactualOverlay(kernel)
            for patch in probe.treatment_plan.patches[
                : probe.treatment_plan.apply_patch_count
            ]:
                treatment_overlay.apply(patch)
            if (
                baseline_overlay.fingerprint()
                != baseline_result.settlement.overlay_fingerprint
                or treatment_overlay.fingerprint()
                != treatment_result.settlement.overlay_fingerprint
            ):
                raise ContradictionFunctionalProbeIntegrityError(
                    "Contradiction functional overlays differ from settlement."
                )
            baseline_projection = baseline_overlay.read(
                "structures", probe.projection_id
            )
            treatment_projection = treatment_overlay.read(
                "structures", probe.projection_id
            )
            expected_projection = probe.treatment_plan.patches[0].value
            if baseline_projection is not None or treatment_projection != expected_projection:
                raise ContradictionFunctionalProbeIntegrityError(
                    "Contradiction functional projection was not actually controlled."
                )
            if treatment_projection is None:
                raise ContradictionFunctionalProbeIntegrityError(
                    "Contradiction treatment projection is missing."
                )
            context_payload = treatment_projection.get("functional_context")
            context = ContradictionFunctionalProbeContext.model_validate(
                context_payload
            )
            if (
                context != probe.functional_context
                or context.context_version
                != CONTRADICTION_FUNCTIONAL_CONTEXT_VERSION
                or context.context_id not in baseline_result.trace.result_refs
                or context.context_id not in treatment_result.trace.result_refs
            ):
                raise ContradictionFunctionalProbeIntegrityError(
                    "Contradiction functional context was not preregistered in both arms."
                )
            return ContradictionFunctionalObservation.build(
                functional_context=context,
                provenance_observation=provenance,
            )
        except ContradictionFunctionalProbeIntegrityError:
            raise
        except (
            ContradictionHypothesisIntegrityError,
            ContradictionProvenanceProbeIntegrityError,
            SimulationIntegrityError,
            ValueError,
            TypeError,
        ) as exc:
            raise ContradictionFunctionalProbeIntegrityError(str(exc)) from exc
        finally:
            if kernel.fingerprint() != canonical_before:
                raise RuntimeError(
                    "Contradiction functional observation mutated canonical state."
                )
            if ledger.fingerprint() != ledger_before:
                raise RuntimeError(
                    "Contradiction functional observation mutated simulation state."
                )
