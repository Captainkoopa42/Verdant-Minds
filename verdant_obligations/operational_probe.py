"""Overlay-local access probes derived from settled counterfactual runs.

The probe walks only relation records that actually materialized in an arm's
copy-on-write overlay. It retrieves evidence from the canonical target concept
rather than trusting evidence IDs carried by a hypothetical patch. This
establishes bounded overlay-local access behavior, not workspace admission, an
outgoing action, a canonical dependency path, or resolution.
"""
from __future__ import annotations

import hashlib
from collections import deque
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import EvidenceKind, VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .counterfactual import (
    CounterfactualOverlay,
    CounterfactualPlan,
    CounterfactualRunResult,
    SimulationDisposition,
    SimulationIntegrityError,
    SimulationLedger,
    derive_counterfactual_execution_trace,
)
from .trace_observations import (
    MatchedCounterfactualObserver,
    MatchedStructuralObservation,
    TraceObservationIntegrityError,
)


OVERLAY_OPERATIONAL_PROBE_VERSION = "overlay_operational_probe_v0.26"


class OperationalProbeIntegrityError(RuntimeError):
    """Raised when an operational observation lacks actual trace lineage."""


class OperationalProbeArm(str, Enum):
    BASELINE = "baseline"
    TREATMENT = "treatment"


class OperationalProbeDisposition(str, Enum):
    NO_QUALIFYING_ACCESS_PATH = "no_qualifying_access_path"
    CANONICAL_EVIDENCE_RETRIEVED = "canonical_evidence_retrieved"


class OverlayAccessEffect(str, Enum):
    ACCESS_GAIN = "access_gain"
    VALID_NULL = "valid_null"
    ACCESS_LOSS = "access_loss"
    ACCESS_CHANGED = "access_changed"


class OverlayOperationalProbePolicy(BaseModel):
    """Visible grammar for one bounded overlay-local graph walk."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = OVERLAY_OPERATIONAL_PROBE_VERSION
    traversable_relation_types: tuple[str, ...] = (
        "counterfactual_dependency_bridge",
    )
    qualifying_evidence_kinds: tuple[EvidenceKind, ...] = (
        EvidenceKind.ACTION,
        EvidenceKind.OUTCOME,
    )
    maximum_relation_hops: int = Field(default=4, ge=1, le=32)
    require_counterfactual_marker: bool = True

    @model_validator(mode="after")
    def validate_policy(self) -> "OverlayOperationalProbePolicy":
        relation_types = tuple(
            sorted(set(item.strip() for item in self.traversable_relation_types))
        )
        if not relation_types or not all(relation_types):
            raise ValueError("Operational probe requires relation types.")
        if relation_types != self.traversable_relation_types:
            raise ValueError(
                "Operational probe relation types must be sorted and unique."
            )
        evidence_kinds = tuple(
            sorted(set(self.qualifying_evidence_kinds), key=lambda item: item.value)
        )
        if not evidence_kinds or evidence_kinds != self.qualifying_evidence_kinds:
            raise ValueError(
                "Operational probe evidence kinds must be sorted and unique."
            )
        if self.policy_version != OVERLAY_OPERATIONAL_PROBE_VERSION:
            raise ValueError("Unsupported overlay operational probe version.")
        return self

    def fingerprint(self) -> str:
        return hashlib.sha256(
            canonical_json_bytes(self.model_dump(mode="json"))
        ).hexdigest()


def _identity_payload(values: dict[str, Any], identity_field: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in values.items():
        if key == identity_field:
            continue
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


class OverlayOperationalProbeObservation(FrozenRecord):
    """One arm's actual overlay-local access behavior."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    policy_version: str
    policy_sha256: str
    arm: OperationalProbeArm
    obligation_id: str
    hypothesis_ref: str
    plan_id: str
    reservation_id: str
    settlement_id: str
    structural_trace_ref: str
    canonical_checkpoint_fingerprint: str
    overlay_fingerprint: str
    source_node_ref: str
    inspected_relation_refs: tuple[str, ...] = ()
    traversed_node_refs: tuple[str, ...] = Field(min_length=1)
    traversed_relation_refs: tuple[str, ...] = ()
    terminal_concept_ref: str | None = None
    retrieved_evidence_refs: tuple[str, ...] = ()
    disposition: OperationalProbeDisposition
    simulated_only: bool = True
    workspace_admission_observed: bool = False
    outgoing_action_observed: bool = False
    canonical_dependency_path_established: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "OverlayOperationalProbeObservation":
        for key in (
            "inspected_relation_refs",
            "retrieved_evidence_refs",
        ):
            values[key] = tuple(sorted(set(values.get(key, ()))))
        values["traversed_node_refs"] = tuple(values["traversed_node_refs"])
        values["traversed_relation_refs"] = tuple(
            values.get("traversed_relation_refs", ())
        )
        values.setdefault("simulated_only", True)
        values.setdefault("workspace_admission_observed", False)
        values.setdefault("outgoing_action_observed", False)
        values.setdefault("canonical_dependency_path_established", False)
        values.setdefault("observed_outcome_authority_enabled", False)
        values.setdefault("resolution_authority_enabled", False)
        values.setdefault("canonical_commit_permitted", False)
        values["observation_id"] = stable_id(
            "overlay_operational_probe_observation",
            _identity_payload(values, "observation_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_observation(self) -> "OverlayOperationalProbeObservation":
        identifiers = (
            self.policy_version,
            self.obligation_id,
            self.hypothesis_ref,
            self.plan_id,
            self.reservation_id,
            self.settlement_id,
            self.structural_trace_ref,
            self.source_node_ref,
        )
        if not all(item.strip() for item in identifiers):
            raise ValueError("Operational probe references cannot be empty.")
        if self.policy_version != OVERLAY_OPERATIONAL_PROBE_VERSION:
            raise ValueError("Unsupported overlay operational probe version.")
        for digest in (
            self.policy_sha256,
            self.canonical_checkpoint_fingerprint,
            self.overlay_fingerprint,
        ):
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError("Operational probe digests must be SHA-256.")
        for refs, label in (
            (self.inspected_relation_refs, "inspected relations"),
            (self.retrieved_evidence_refs, "retrieved evidence"),
        ):
            if refs != tuple(sorted(set(refs))):
                raise ValueError(
                    f"Operational probe {label} must be sorted and unique."
                )
        if len(set(self.traversed_node_refs)) != len(self.traversed_node_refs):
            raise ValueError("Operational probe path cannot repeat a node.")
        if len(set(self.traversed_relation_refs)) != len(
            self.traversed_relation_refs
        ):
            raise ValueError("Operational probe path cannot repeat a relation.")
        if len(self.traversed_node_refs) != len(self.traversed_relation_refs) + 1:
            raise ValueError("Operational probe nodes and relations are not contiguous.")
        if self.traversed_node_refs[0] != self.source_node_ref:
            raise ValueError("Operational probe path lost its source node.")
        if not set(self.traversed_relation_refs).issubset(
            self.inspected_relation_refs
        ):
            raise ValueError("Operational probe traversed an uninspected relation.")
        retrieved = bool(self.retrieved_evidence_refs)
        if retrieved:
            if (
                self.disposition
                != OperationalProbeDisposition.CANONICAL_EVIDENCE_RETRIEVED
                or not self.traversed_relation_refs
                or self.terminal_concept_ref != self.traversed_node_refs[-1]
            ):
                raise ValueError("Operational retrieval path is incomplete.")
        elif (
            self.disposition
            != OperationalProbeDisposition.NO_QUALIFYING_ACCESS_PATH
            or self.traversed_node_refs != (self.source_node_ref,)
            or self.traversed_relation_refs
            or self.terminal_concept_ref is not None
        ):
            raise ValueError("Operational null observation carries a fabricated path.")
        if (
            not self.simulated_only
            or self.workspace_admission_observed
            or self.outgoing_action_observed
            or self.canonical_dependency_path_established
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Operational probe crossed its authority boundary.")
        expected = stable_id(
            "overlay_operational_probe_observation",
            self.model_dump(mode="json", exclude={"observation_id"}),
        )
        if self.observation_id != expected:
            raise ValueError("Operational probe observation checksum mismatch.")
        return self


class MatchedOverlayOperationalObservation(FrozenRecord):
    """A matched zero/full comparison of actual overlay-local access."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    match_id: str
    structural_observation_ref: str
    baseline: OverlayOperationalProbeObservation
    treatment: OverlayOperationalProbeObservation
    effect: OverlayAccessEffect
    newly_retrieved_evidence_refs: tuple[str, ...] = ()
    lost_retrieved_evidence_refs: tuple[str, ...] = ()
    path_changed: bool
    matched_control_verified: bool = True
    simulated_only: bool = True
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @staticmethod
    def _effect(
        baseline: OverlayOperationalProbeObservation,
        treatment: OverlayOperationalProbeObservation,
    ) -> tuple[OverlayAccessEffect, tuple[str, ...], tuple[str, ...], bool]:
        baseline_refs = set(baseline.retrieved_evidence_refs)
        treatment_refs = set(treatment.retrieved_evidence_refs)
        gained = tuple(sorted(treatment_refs - baseline_refs))
        lost = tuple(sorted(baseline_refs - treatment_refs))
        path_changed = (
            baseline.traversed_node_refs != treatment.traversed_node_refs
            or baseline.traversed_relation_refs
            != treatment.traversed_relation_refs
        )
        if gained and not lost:
            effect = OverlayAccessEffect.ACCESS_GAIN
        elif not gained and not lost and not path_changed:
            effect = OverlayAccessEffect.VALID_NULL
        elif lost and not gained:
            effect = OverlayAccessEffect.ACCESS_LOSS
        else:
            effect = OverlayAccessEffect.ACCESS_CHANGED
        return effect, gained, lost, path_changed

    @classmethod
    def build(
        cls,
        *,
        structural_observation_ref: str,
        baseline: OverlayOperationalProbeObservation,
        treatment: OverlayOperationalProbeObservation,
    ) -> "MatchedOverlayOperationalObservation":
        effect, gained, lost, path_changed = cls._effect(baseline, treatment)
        values = {
            "structural_observation_ref": structural_observation_ref,
            "baseline": baseline,
            "treatment": treatment,
            "effect": effect,
            "newly_retrieved_evidence_refs": gained,
            "lost_retrieved_evidence_refs": lost,
            "path_changed": path_changed,
            "matched_control_verified": True,
            "simulated_only": True,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["match_id"] = stable_id(
            "matched_overlay_operational_observation",
            _identity_payload(values, "match_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_match(self) -> "MatchedOverlayOperationalObservation":
        if not self.structural_observation_ref.strip():
            raise ValueError("Operational match requires structural lineage.")
        if (
            self.baseline.arm != OperationalProbeArm.BASELINE
            or self.treatment.arm != OperationalProbeArm.TREATMENT
        ):
            raise ValueError("Operational match crossed its declared arms.")
        shared_fields = (
            self.baseline.policy_version == self.treatment.policy_version,
            self.baseline.policy_sha256 == self.treatment.policy_sha256,
            self.baseline.obligation_id == self.treatment.obligation_id,
            self.baseline.hypothesis_ref == self.treatment.hypothesis_ref,
            self.baseline.canonical_checkpoint_fingerprint
            == self.treatment.canonical_checkpoint_fingerprint,
            self.baseline.source_node_ref == self.treatment.source_node_ref,
        )
        if not all(shared_fields):
            raise ValueError("Operational probe controls are not matched.")
        if self.baseline.settlement_id == self.treatment.settlement_id:
            raise ValueError("Operational probe arms reused one settlement.")
        expected_effect, gained, lost, path_changed = self._effect(
            self.baseline,
            self.treatment,
        )
        if (
            self.effect != expected_effect
            or self.newly_retrieved_evidence_refs != gained
            or self.lost_retrieved_evidence_refs != lost
            or self.path_changed != path_changed
        ):
            raise ValueError("Operational access effect was altered.")
        if (
            not self.matched_control_verified
            or not self.simulated_only
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Operational match crossed its authority boundary.")
        expected = stable_id(
            "matched_overlay_operational_observation",
            self.model_dump(mode="json", exclude={"match_id"}),
        )
        if self.match_id != expected:
            raise ValueError("Operational match checksum mismatch.")
        return self


class OverlayOperationalProbe:
    """Reconstruct an arm and execute a deterministic overlay-local graph walk."""

    def __init__(
        self,
        policy: OverlayOperationalProbePolicy | None = None,
    ) -> None:
        self.policy = policy or OverlayOperationalProbePolicy()

    def _observe_arm(
        self,
        kernel: VerdantKernel,
        ledger: SimulationLedger,
        *,
        arm: OperationalProbeArm,
        hypothesis_ref: str,
        plan: CounterfactualPlan,
        result: CounterfactualRunResult,
    ) -> OverlayOperationalProbeObservation:
        trace = derive_counterfactual_execution_trace(
            kernel,
            ledger,
            plan=plan,
            reservation=result.reservation,
            settlement=result.settlement,
        )
        if result.trace != trace:
            raise OperationalProbeIntegrityError(
                "Operational probe trace differs from the simulation ledger."
            )
        if (
            trace.disposition != SimulationDisposition.DISCARDED
            or hypothesis_ref not in trace.result_refs
        ):
            raise OperationalProbeIntegrityError(
                "Operational probe requires a completed run with hypothesis lineage."
            )
        obligation = kernel.state.obligation_kernels.get(trace.obligation_id)
        if obligation is None:
            raise OperationalProbeIntegrityError(
                "Operational probe lost its canonical obligation."
            )
        source_ref = obligation.target_action_node
        if source_ref not in kernel.state.concepts:
            raise OperationalProbeIntegrityError(
                "Operational probe source is not a canonical concept."
            )

        overlay = CounterfactualOverlay(kernel)
        for patch in plan.patches[: plan.apply_patch_count]:
            overlay.apply(patch)
        if overlay.fingerprint() != trace.overlay_fingerprint:
            raise OperationalProbeIntegrityError(
                "Operational probe overlay differs from the settled trace."
            )

        relation_types = set(self.policy.traversable_relation_types)
        adjacency: dict[str, list[tuple[str, str]]] = {}
        inspected: list[str] = []
        for relation_ref, record in overlay.materialize_collection(
            "relations"
        ).items():
            if record.get("relation_type") not in relation_types:
                continue
            if self.policy.require_counterfactual_marker and (
                record.get("counterfactual") is not True
            ):
                continue
            relation_source = record.get("source_concept_id")
            relation_target = record.get("target_concept_id")
            if (
                not isinstance(relation_source, str)
                or not isinstance(relation_target, str)
                or relation_source not in kernel.state.concepts
                or relation_target not in kernel.state.concepts
            ):
                raise OperationalProbeIntegrityError(
                    "Operational overlay relation escaped canonical concepts."
                )
            inspected.append(relation_ref)
            adjacency.setdefault(relation_source, []).append(
                (relation_ref, relation_target)
            )
        for edges in adjacency.values():
            edges.sort()

        qualifying_kinds = set(self.policy.qualifying_evidence_kinds)
        queue: deque[tuple[str, tuple[str, ...], tuple[str, ...]]] = deque(
            [(source_ref, (source_ref,), ())]
        )
        selected_nodes = (source_ref,)
        selected_relations: tuple[str, ...] = ()
        selected_evidence: tuple[str, ...] = ()
        terminal: str | None = None
        while queue:
            node_ref, node_path, relation_path = queue.popleft()
            if relation_path:
                concept = kernel.state.concepts[node_ref]
                evidence_refs = tuple(
                    sorted(
                        ref
                        for ref in concept.evidence_refs
                        if kernel.state.evidence[ref].kind in qualifying_kinds
                    )
                )
                if evidence_refs:
                    selected_nodes = node_path
                    selected_relations = relation_path
                    selected_evidence = evidence_refs
                    terminal = node_ref
                    break
            if len(relation_path) >= self.policy.maximum_relation_hops:
                continue
            for relation_ref, target_ref in adjacency.get(node_ref, ()):
                if target_ref in node_path:
                    continue
                queue.append(
                    (
                        target_ref,
                        (*node_path, target_ref),
                        (*relation_path, relation_ref),
                    )
                )

        disposition = (
            OperationalProbeDisposition.CANONICAL_EVIDENCE_RETRIEVED
            if selected_evidence
            else OperationalProbeDisposition.NO_QUALIFYING_ACCESS_PATH
        )
        return OverlayOperationalProbeObservation.build(
            policy_version=self.policy.policy_version,
            policy_sha256=self.policy.fingerprint(),
            arm=arm,
            obligation_id=trace.obligation_id,
            hypothesis_ref=hypothesis_ref,
            plan_id=trace.plan_id,
            reservation_id=trace.reservation_id,
            settlement_id=trace.settlement_id,
            structural_trace_ref=trace.trace_id,
            canonical_checkpoint_fingerprint=trace.canonical_fingerprint,
            overlay_fingerprint=trace.overlay_fingerprint,
            source_node_ref=source_ref,
            inspected_relation_refs=tuple(inspected),
            traversed_node_refs=selected_nodes,
            traversed_relation_refs=selected_relations,
            terminal_concept_ref=terminal,
            retrieved_evidence_refs=selected_evidence,
            disposition=disposition,
        )

    def observe(
        self,
        kernel: VerdantKernel,
        ledger: SimulationLedger,
        *,
        hypothesis_ref: str,
        baseline_plan: CounterfactualPlan,
        baseline_result: CounterfactualRunResult,
        treatment_plan: CounterfactualPlan,
        treatment_result: CounterfactualRunResult,
        structural_observation: MatchedStructuralObservation,
    ) -> MatchedOverlayOperationalObservation:
        try:
            verified_structural = MatchedCounterfactualObserver().observe(
                kernel,
                ledger,
                hypothesis_ref=hypothesis_ref,
                baseline_plan=baseline_plan,
                baseline_result=baseline_result,
                treatment_plan=treatment_plan,
                treatment_result=treatment_result,
            )
            if verified_structural != structural_observation:
                raise OperationalProbeIntegrityError(
                    "Operational probe lost its matched structural observation."
                )
            baseline = self._observe_arm(
                kernel,
                ledger,
                arm=OperationalProbeArm.BASELINE,
                hypothesis_ref=hypothesis_ref,
                plan=baseline_plan,
                result=baseline_result,
            )
            treatment = self._observe_arm(
                kernel,
                ledger,
                arm=OperationalProbeArm.TREATMENT,
                hypothesis_ref=hypothesis_ref,
                plan=treatment_plan,
                result=treatment_result,
            )
            return MatchedOverlayOperationalObservation.build(
                structural_observation_ref=structural_observation.observation_id,
                baseline=baseline,
                treatment=treatment,
            )
        except OperationalProbeIntegrityError:
            raise
        except (
            SimulationIntegrityError,
            TraceObservationIntegrityError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            raise OperationalProbeIntegrityError(str(exc)) from exc
