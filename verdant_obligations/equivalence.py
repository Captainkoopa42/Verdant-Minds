"""Typed Equivalence Lenses with local bindings and bounded tripwires.

Definitions are immutable, content-addressed operator programs.  Bindings,
evidence, and governance transitions occupy a separate append-only ledger.
Applying a lens is an ordinary read-only executive operation; approving,
suspending, or rolling back a binding is an explicit governance operation.

This experimental sidecar does not mutate Verdant ``KernelState``, learn lens
operators, create Diagnostic Obligations, or authorize resolution.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel.models import (
    FrozenRecord,
    ObligationFamily,
    canonical_json_bytes,
    stable_id,
)

from .hypotheses import FunctionalOutcome, StructuralHypothesis


EQUIVALENCE_LENS_IR_VERSION = "equivalence_lens_ir_v0.6"
LENS_LEDGER_SCHEMA_VERSION = "equivalence_lens_ledger_v0.6"


class LensIntegrityError(RuntimeError):
    pass


class LensUnavailableError(LensIntegrityError):
    pass


class LensOpcode(str, Enum):
    SELECT_ACTION = "select_action"
    SELECT_ACTIVATED_REFS = "select_activated_refs"
    SELECT_EDGE_ENDPOINTS = "select_edge_endpoints"
    SELECT_EDGE_TYPES = "select_edge_types"


class LensEvidenceResult(str, Enum):
    SUPPORTED = "supported"
    VALID_NULL = "valid_null"
    OVER_SMOOTHING = "over_smoothing"
    HYPER_DISCRIMINATION = "hyper_discrimination"
    NO_EXPLANATORY_GAIN = "no_explanatory_gain"

    @property
    def trips_failure_counter(self) -> bool:
        return self in {
            LensEvidenceResult.OVER_SMOOTHING,
            LensEvidenceResult.HYPER_DISCRIMINATION,
            LensEvidenceResult.NO_EXPLANATORY_GAIN,
        }


class LensGovernanceAction(str, Enum):
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    SUSPENDED = "suspended"
    ROLLED_BACK = "rolled_back"
    REACTIVATED = "reactivated"


class LensBindingStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    SUSPENDED = "suspended"
    ROLLED_BACK = "rolled_back"


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


class EquivalenceLensDefinition(FrozenRecord):
    definition_id: str
    ir_version: str
    operators: tuple[LensOpcode, ...] = Field(min_length=1)
    parent_definition_id: str | None = None
    provenance_refs: tuple[str, ...] = Field(min_length=1)

    @classmethod
    def build(
        cls,
        *,
        operators: Sequence[LensOpcode],
        provenance_refs: Sequence[str],
        parent_definition_id: str | None = None,
        ir_version: str = EQUIVALENCE_LENS_IR_VERSION,
    ) -> "EquivalenceLensDefinition":
        normalized_operators = tuple(sorted(set(operators), key=lambda item: item.value))
        normalized_provenance = tuple(sorted(set(provenance_refs)))
        payload = {
            "ir_version": ir_version,
            "operators": tuple(item.value for item in normalized_operators),
            "parent_definition_id": parent_definition_id,
            "provenance_refs": normalized_provenance,
        }
        return cls(
            definition_id=stable_id("equivalence_lens_definition", payload),
            ir_version=ir_version,
            operators=normalized_operators,
            parent_definition_id=parent_definition_id,
            provenance_refs=normalized_provenance,
        )

    @model_validator(mode="after")
    def validate_definition(self) -> "EquivalenceLensDefinition":
        if not self.ir_version.strip():
            raise ValueError("Equivalence Lens IR version cannot be empty.")
        if tuple(sorted(set(self.operators), key=lambda item: item.value)) != self.operators:
            raise ValueError("Equivalence Lens operators must be sorted and unique.")
        if tuple(sorted(set(self.provenance_refs))) != self.provenance_refs:
            raise ValueError("Equivalence Lens provenance must be sorted and unique.")
        payload = {
            "ir_version": self.ir_version,
            "operators": tuple(item.value for item in self.operators),
            "parent_definition_id": self.parent_definition_id,
            "provenance_refs": self.provenance_refs,
        }
        if self.definition_id != stable_id("equivalence_lens_definition", payload):
            raise ValueError("Equivalence Lens definition checksum mismatch.")
        return self


class LensBinding(FrozenRecord):
    binding_id: str
    definition_id: str
    obligation_family: ObligationFamily
    binding_version: int = Field(ge=1)
    failure_tripwire_count: int = Field(ge=1)
    activation_minimum_outcomes: int = Field(default=1, ge=1)
    predecessor_binding_id: str | None = None
    calibration_refs: tuple[str, ...] = Field(min_length=1)
    policy_version: str

    @classmethod
    def build(cls, **values: Any) -> "LensBinding":
        values["calibration_refs"] = tuple(sorted(set(values["calibration_refs"])))
        payload = {
            key: value.value if isinstance(value, Enum) else value
            for key, value in values.items()
            if key != "binding_id"
        }
        return cls(
            binding_id=stable_id("equivalence_lens_binding", payload),
            **values,
        )

    @model_validator(mode="after")
    def validate_binding(self) -> "LensBinding":
        if not self.definition_id.strip() or not self.policy_version.strip():
            raise ValueError("Lens bindings require definition and policy identifiers.")
        if tuple(sorted(set(self.calibration_refs))) != self.calibration_refs:
            raise ValueError("Lens binding calibration refs must be sorted and unique.")
        payload = self.model_dump(mode="json", exclude={"binding_id"})
        if self.binding_id != stable_id("equivalence_lens_binding", payload):
            raise ValueError("Lens binding checksum mismatch.")
        return self


class LensEvidence(FrozenRecord):
    evidence_id: str
    source_event_key: str
    binding_id: str
    result: LensEvidenceResult
    cycle: int = Field(ge=0)
    hypothesis_refs: tuple[str, ...] = ()
    outcome_refs: tuple[str, ...] = ()
    independent_consequence_refs: tuple[str, ...] = Field(min_length=1)
    evidence_sha256: str

    @classmethod
    def build(cls, **values: Any) -> "LensEvidence":
        for key in (
            "hypothesis_refs",
            "outcome_refs",
            "independent_consequence_refs",
        ):
            values[key] = tuple(sorted(set(values.get(key, ()))))
        payload = {
            key: value.value if isinstance(value, Enum) else value
            for key, value in values.items()
            if key not in {"evidence_id", "evidence_sha256"}
        }
        evidence_sha256 = _digest(payload)
        return cls(
            evidence_id=stable_id(
                "equivalence_lens_evidence",
                values["source_event_key"],
                evidence_sha256,
            ),
            evidence_sha256=evidence_sha256,
            **values,
        )

    @model_validator(mode="after")
    def validate_evidence(self) -> "LensEvidence":
        if not self.source_event_key.strip() or not self.binding_id.strip():
            raise ValueError("Lens evidence requires source and binding identifiers.")
        for values, label in (
            (self.hypothesis_refs, "hypothesis refs"),
            (self.outcome_refs, "outcome refs"),
            (self.independent_consequence_refs, "independent consequence refs"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Lens evidence {label} must be sorted and unique.")
        payload = self.model_dump(
            mode="json", exclude={"evidence_id", "evidence_sha256"}
        )
        if self.evidence_sha256 != _digest(payload):
            raise ValueError("Lens evidence payload checksum mismatch.")
        expected = stable_id(
            "equivalence_lens_evidence",
            self.source_event_key,
            self.evidence_sha256,
        )
        if self.evidence_id != expected:
            raise ValueError("Lens evidence identity checksum mismatch.")
        return self


class LensGovernanceEvent(FrozenRecord):
    event_id: str
    source_event_key: str
    sequence: int = Field(ge=1)
    cycle: int = Field(ge=0)
    action: LensGovernanceAction
    binding_id: str
    target_binding_id: str | None = None
    basis_refs: tuple[str, ...] = Field(min_length=1)
    policy_version: str
    payload_sha256: str

    @classmethod
    def build(cls, **values: Any) -> "LensGovernanceEvent":
        values.setdefault("target_binding_id", None)
        values["basis_refs"] = tuple(sorted(set(values["basis_refs"])))
        payload = {
            key: value.value if isinstance(value, Enum) else value
            for key, value in values.items()
            if key not in {"event_id", "payload_sha256"}
        }
        payload_sha256 = _digest(payload)
        return cls(
            event_id=stable_id(
                "equivalence_lens_governance",
                values["source_event_key"],
                payload_sha256,
            ),
            payload_sha256=payload_sha256,
            **values,
        )

    @model_validator(mode="after")
    def validate_event(self) -> "LensGovernanceEvent":
        required = (
            self.source_event_key,
            self.binding_id,
            self.policy_version,
        )
        if not all(item.strip() for item in required):
            raise ValueError("Lens governance identity fields cannot be empty.")
        if tuple(sorted(set(self.basis_refs))) != self.basis_refs:
            raise ValueError("Lens governance basis refs must be sorted and unique.")
        targeted_actions = {
            LensGovernanceAction.ROLLED_BACK,
            LensGovernanceAction.REACTIVATED,
        }
        if self.action in targeted_actions and not self.target_binding_id:
            raise ValueError("Lens rollback/reactivation requires a target binding.")
        if self.action not in targeted_actions and self.target_binding_id is not None:
            raise ValueError("This lens governance action cannot carry a target binding.")
        payload = self.model_dump(mode="json", exclude={"event_id", "payload_sha256"})
        if self.payload_sha256 != _digest(payload):
            raise ValueError("Lens governance payload checksum mismatch.")
        expected = stable_id(
            "equivalence_lens_governance",
            self.source_event_key,
            self.payload_sha256,
        )
        if self.event_id != expected:
            raise ValueError("Lens governance event checksum mismatch.")
        return self


class LensDefinitionRegistryState(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    ir_version: str = EQUIVALENCE_LENS_IR_VERSION
    definitions: dict[str, EquivalenceLensDefinition] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_registry(self) -> "LensDefinitionRegistryState":
        if self.ir_version != EQUIVALENCE_LENS_IR_VERSION:
            raise ValueError("Unsupported Equivalence Lens IR version.")
        if set(self.definitions) != {
            item.definition_id for item in self.definitions.values()
        }:
            raise ValueError("Lens definition registry key mismatch.")
        for definition in self.definitions.values():
            if (
                definition.parent_definition_id is not None
                and definition.parent_definition_id not in self.definitions
            ):
                raise ValueError("Lens definition lost its parent lineage.")
        return self


class LensBindingLedgerState(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    schema_version: str = LENS_LEDGER_SCHEMA_VERSION
    bindings: tuple[LensBinding, ...] = ()
    evidence: tuple[LensEvidence, ...] = ()
    governance_events: tuple[LensGovernanceEvent, ...] = ()

    @model_validator(mode="after")
    def validate_ledger(self) -> "LensBindingLedgerState":
        if self.schema_version != LENS_LEDGER_SCHEMA_VERSION:
            raise ValueError("Unsupported lens ledger schema.")
        binding_ids = tuple(item.binding_id for item in self.bindings)
        if len(set(binding_ids)) != len(binding_ids):
            raise ValueError("Lens ledger duplicates a binding.")
        versions = tuple(
            (item.obligation_family, item.binding_version) for item in self.bindings
        )
        if len(set(versions)) != len(versions):
            raise ValueError("Lens ledger duplicates a family binding version.")
        binding_set = set(binding_ids)
        for binding in self.bindings:
            if (
                binding.predecessor_binding_id is not None
                and binding.predecessor_binding_id not in binding_set
            ):
                raise ValueError("Lens binding lost its predecessor.")
        source_keys: set[str] = set()
        for item in (*self.evidence, *self.governance_events):
            if item.source_event_key in source_keys:
                raise ValueError("Lens ledger reuses a source event key.")
            source_keys.add(item.source_event_key)
            if item.binding_id not in binding_set:
                raise ValueError("Lens ledger event cites an unknown binding.")
            if (
                isinstance(item, LensGovernanceEvent)
                and item.target_binding_id is not None
                and item.target_binding_id not in binding_set
            ):
                raise ValueError("Lens governance target cites an unknown binding.")
        sequences = tuple(item.sequence for item in self.governance_events)
        if sequences != tuple(range(1, len(sequences) + 1)):
            raise ValueError("Lens governance sequence is not contiguous.")
        approvals = tuple(
            item.binding_id
            for item in self.governance_events
            if item.action == LensGovernanceAction.APPROVED
        )
        if len(set(approvals)) != len(approvals) or set(approvals) != binding_set:
            raise ValueError("Every lens binding requires exactly one approval event.")
        statuses: dict[str, LensBindingStatus] = {}
        previous_cycle = -1
        for event in self.governance_events:
            if event.cycle < previous_cycle:
                raise ValueError("Lens governance cycles must be nondecreasing.")
            previous_cycle = event.cycle
            if event.action == LensGovernanceAction.APPROVED:
                if event.binding_id in statuses:
                    raise ValueError("Lens binding was approved more than once.")
                statuses[event.binding_id] = LensBindingStatus.ACTIVE
            elif event.action == LensGovernanceAction.SUPERSEDED:
                if statuses.get(event.binding_id) != LensBindingStatus.ACTIVE:
                    raise ValueError("Only an active lens binding may be superseded.")
                statuses[event.binding_id] = LensBindingStatus.SUPERSEDED
            elif event.action == LensGovernanceAction.SUSPENDED:
                if statuses.get(event.binding_id) != LensBindingStatus.ACTIVE:
                    raise ValueError("Only an active lens binding may be suspended.")
                statuses[event.binding_id] = LensBindingStatus.SUSPENDED
            elif event.action == LensGovernanceAction.ROLLED_BACK:
                if statuses.get(event.binding_id) != LensBindingStatus.SUSPENDED:
                    raise ValueError("Only a suspended lens binding may be rolled back.")
                if statuses.get(event.target_binding_id or "") != LensBindingStatus.SUPERSEDED:
                    raise ValueError("Lens rollback target must be superseded.")
                statuses[event.binding_id] = LensBindingStatus.ROLLED_BACK
            elif event.action == LensGovernanceAction.REACTIVATED:
                if statuses.get(event.binding_id) != LensBindingStatus.ROLLED_BACK:
                    raise ValueError("Lens reactivation requires a rolled-back source.")
                if statuses.get(event.target_binding_id or "") != LensBindingStatus.SUPERSEDED:
                    raise ValueError("Lens reactivation target must be superseded.")
                statuses[event.target_binding_id or ""] = LensBindingStatus.ACTIVE
        binding_by_id = {item.binding_id: item for item in self.bindings}
        for binding_id, binding in binding_by_id.items():
            failures = sum(
                item.result.trips_failure_counter
                for item in self.evidence
                if item.binding_id == binding_id
            )
            if failures >= binding.failure_tripwire_count and statuses.get(binding_id) == LensBindingStatus.ACTIVE:
                raise ValueError("Lens failure tripwire lacks a suspension transition.")
        return self


class LensBindingView(FrozenRecord):
    binding: LensBinding
    status: LensBindingStatus
    support_count: int = Field(ge=0)
    valid_null_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    last_governance_event_id: str


class LensOutcomeClass(FrozenRecord):
    equivalence_signature: str
    member_outcome_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_class(self) -> "LensOutcomeClass":
        if tuple(sorted(set(self.member_outcome_ids))) != self.member_outcome_ids:
            raise ValueError("Lens outcome class members must be sorted and unique.")
        return self


class LensPartition(FrozenRecord):
    partition_id: str
    obligation_id: str
    definition_id: str
    binding_id: str
    equivalence_classes: tuple[LensOutcomeClass, ...] = Field(min_length=1)
    duplicate_outcome_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_partition(self) -> "LensPartition":
        signatures = tuple(item.equivalence_signature for item in self.equivalence_classes)
        if tuple(sorted(set(signatures))) != signatures:
            raise ValueError("Lens partition signatures must be sorted and unique.")
        if tuple(sorted(set(self.duplicate_outcome_ids))) != self.duplicate_outcome_ids:
            raise ValueError("Lens duplicate outcome IDs must be sorted and unique.")
        expected_duplicates = tuple(
            sorted(
                outcome_id
                for item in self.equivalence_classes
                for outcome_id in item.member_outcome_ids[1:]
            )
        )
        if self.duplicate_outcome_ids != expected_duplicates:
            raise ValueError("Lens duplicate outcome index disagrees with its classes.")
        payload = self.model_dump(mode="json", exclude={"partition_id"})
        if self.partition_id != stable_id("equivalence_lens_partition", payload):
            raise ValueError("Lens partition checksum mismatch.")
        return self


@dataclass(frozen=True)
class LensEvidenceResultRecord:
    evidence: LensEvidence
    suspended: bool
    replayed: bool


class EquivalenceLensSystem:
    """Registry plus append-only local binding/evidence governance ledger."""

    GOVERNANCE_POLICY_VERSION = "equivalence_lens_governance_v0.6"

    def __init__(
        self,
        *,
        registry: LensDefinitionRegistryState | None = None,
        ledger: LensBindingLedgerState | None = None,
    ) -> None:
        self.registry = LensDefinitionRegistryState.model_validate(
            (registry or LensDefinitionRegistryState()).model_dump(mode="json")
        )
        self.ledger = LensBindingLedgerState.model_validate(
            (ledger or LensBindingLedgerState()).model_dump(mode="json")
        )
        self._validate_cross_state()

    def _validate_cross_state(self) -> None:
        for binding in self.ledger.bindings:
            if binding.definition_id not in self.registry.definitions:
                raise LensIntegrityError("Lens binding references an unknown definition.")

    def snapshot(
        self,
    ) -> tuple[LensDefinitionRegistryState, LensBindingLedgerState]:
        return (
            self.registry.model_copy(deep=True),
            self.ledger.model_copy(deep=True),
        )

    def fingerprint(self) -> str:
        return _digest(
            {
                "registry": self.registry.model_dump(mode="json"),
                "ledger": self.ledger.model_dump(mode="json"),
            }
        )

    def register_definition(
        self,
        *,
        operators: Sequence[LensOpcode],
        provenance_refs: Sequence[str],
        parent_definition_id: str | None = None,
    ) -> EquivalenceLensDefinition:
        definition = EquivalenceLensDefinition.build(
            operators=operators,
            provenance_refs=provenance_refs,
            parent_definition_id=parent_definition_id,
        )
        existing = self.registry.definitions.get(definition.definition_id)
        if existing is not None:
            return existing
        definitions = dict(self.registry.definitions)
        definitions[definition.definition_id] = definition
        self.registry = LensDefinitionRegistryState(definitions=definitions)
        return definition

    def _statuses(self) -> dict[str, LensBindingStatus]:
        statuses: dict[str, LensBindingStatus] = {}
        for event in self.ledger.governance_events:
            if event.action in {
                LensGovernanceAction.APPROVED,
                LensGovernanceAction.REACTIVATED,
            }:
                target = event.target_binding_id or event.binding_id
                statuses[target] = LensBindingStatus.ACTIVE
            elif event.action == LensGovernanceAction.SUPERSEDED:
                statuses[event.binding_id] = LensBindingStatus.SUPERSEDED
            elif event.action == LensGovernanceAction.SUSPENDED:
                statuses[event.binding_id] = LensBindingStatus.SUSPENDED
            elif event.action == LensGovernanceAction.ROLLED_BACK:
                statuses[event.binding_id] = LensBindingStatus.ROLLED_BACK
        return statuses

    def binding_view(self, binding_id: str) -> LensBindingView:
        binding = next(
            (item for item in self.ledger.bindings if item.binding_id == binding_id),
            None,
        )
        if binding is None:
            raise LensIntegrityError("Unknown lens binding.")
        events = [
            item for item in self.ledger.governance_events if item.binding_id == binding_id
            or item.target_binding_id == binding_id
        ]
        if not events:
            raise LensIntegrityError("Lens binding has no governance lineage.")
        evidence = [item for item in self.ledger.evidence if item.binding_id == binding_id]
        return LensBindingView(
            binding=binding,
            status=self._statuses()[binding_id],
            support_count=sum(item.result == LensEvidenceResult.SUPPORTED for item in evidence),
            valid_null_count=sum(item.result == LensEvidenceResult.VALID_NULL for item in evidence),
            failure_count=sum(item.result.trips_failure_counter for item in evidence),
            last_governance_event_id=events[-1].event_id,
        )

    def active_binding(self, family: ObligationFamily) -> LensBindingView:
        candidates = [
            self.binding_view(item.binding_id)
            for item in self.ledger.bindings
            if item.obligation_family == family
        ]
        active = [item for item in candidates if item.status == LensBindingStatus.ACTIVE]
        if len(active) != 1:
            raise LensUnavailableError(
                "Obligation family must have exactly one active Equivalence Lens binding."
            )
        return active[0]

    def approve_binding(
        self,
        *,
        definition_id: str,
        obligation_family: ObligationFamily,
        failure_tripwire_count: int,
        calibration_refs: Sequence[str],
        source_event_key: str,
        cycle: int,
        activation_minimum_outcomes: int = 1,
    ) -> LensBinding:
        if definition_id not in self.registry.definitions:
            raise LensIntegrityError("Cannot bind an unknown lens definition.")
        replay = next(
            (
                item
                for item in self.ledger.governance_events
                if item.source_event_key == source_event_key
            ),
            None,
        )
        if replay is not None:
            existing = next(
                item
                for item in self.ledger.bindings
                if item.binding_id == replay.binding_id
            )
            request_matches = (
                replay.action == LensGovernanceAction.APPROVED
                and replay.cycle == cycle
                and existing.definition_id == definition_id
                and existing.obligation_family == obligation_family
                and existing.failure_tripwire_count == failure_tripwire_count
                and existing.activation_minimum_outcomes == activation_minimum_outcomes
                and existing.calibration_refs
                == tuple(sorted(set(calibration_refs)))
            )
            if not request_matches:
                raise LensIntegrityError(
                    "Lens governance source event key was reused with a changed request."
                )
            return existing
        occupied_source_keys = {
            item.source_event_key
            for item in (*self.ledger.evidence, *self.ledger.governance_events)
        }
        required_source_keys = {source_event_key, f"{source_event_key}:supersede"}
        if occupied_source_keys.intersection(required_source_keys):
            raise LensIntegrityError("Lens governance source event key is unavailable.")
        prior = None
        try:
            prior = self.active_binding(obligation_family).binding
        except LensUnavailableError:
            family_bindings = [
                item
                for item in self.ledger.bindings
                if item.obligation_family == obligation_family
            ]
            if family_bindings:
                raise LensIntegrityError(
                    "Cannot approve over a family with no unambiguous active binding."
                )
        versions = [
            item.binding_version
            for item in self.ledger.bindings
            if item.obligation_family == obligation_family
        ]
        binding = LensBinding.build(
            definition_id=definition_id,
            obligation_family=obligation_family,
            binding_version=max(versions, default=0) + 1,
            failure_tripwire_count=failure_tripwire_count,
            activation_minimum_outcomes=activation_minimum_outcomes,
            predecessor_binding_id=prior.binding_id if prior else None,
            calibration_refs=tuple(calibration_refs),
            policy_version=self.GOVERNANCE_POLICY_VERSION,
        )
        events: list[LensGovernanceEvent] = []
        next_sequence = len(self.ledger.governance_events) + 1
        if prior is not None:
            events.append(LensGovernanceEvent.build(
                source_event_key=f"{source_event_key}:supersede",
                sequence=next_sequence,
                cycle=cycle,
                action=LensGovernanceAction.SUPERSEDED,
                binding_id=prior.binding_id,
                basis_refs=(prior.binding_id, binding.binding_id),
                policy_version=self.GOVERNANCE_POLICY_VERSION,
            ))
            next_sequence += 1
        events.append(LensGovernanceEvent.build(
            source_event_key=source_event_key,
            sequence=next_sequence,
            cycle=cycle,
            action=LensGovernanceAction.APPROVED,
            binding_id=binding.binding_id,
            basis_refs=(definition_id, *calibration_refs),
            policy_version=self.GOVERNANCE_POLICY_VERSION,
        ))
        updated = self.ledger.model_copy(
            update={
                "bindings": (*self.ledger.bindings, binding),
                "governance_events": (*self.ledger.governance_events, *events),
            },
            deep=True,
        )
        self.ledger = LensBindingLedgerState.model_validate(updated.model_dump(mode="json"))
        return binding

    @staticmethod
    def _project(
        definition: EquivalenceLensDefinition,
        outcome: FunctionalOutcome,
    ) -> dict[str, Any]:
        consequence = outcome.consequence
        projection: dict[str, Any] = {}
        for opcode in definition.operators:
            if opcode == LensOpcode.SELECT_ACTION:
                projection[opcode.value] = consequence.action.value
            elif opcode == LensOpcode.SELECT_ACTIVATED_REFS:
                projection[opcode.value] = consequence.activated_canonical_refs
            elif opcode == LensOpcode.SELECT_EDGE_ENDPOINTS:
                projection[opcode.value] = tuple(
                    (item.source_ref, item.target_ref)
                    for item in consequence.added_edges
                )
            elif opcode == LensOpcode.SELECT_EDGE_TYPES:
                projection[opcode.value] = tuple(
                    item.relation_type for item in consequence.added_edges
                )
        return projection

    def partition(
        self,
        *,
        obligation_id: str,
        family: ObligationFamily,
        hypotheses: Sequence[StructuralHypothesis],
    ) -> LensPartition:
        view = self.active_binding(family)
        outcomes = [
            outcome
            for hypothesis in hypotheses
            if hypothesis.obligation_id == obligation_id
            for outcome in hypothesis.outcomes
        ]
        if len(outcomes) < view.binding.activation_minimum_outcomes:
            raise LensUnavailableError("Lens activation minimum outcome count was not met.")
        definition = self.registry.definitions[view.binding.definition_id]
        grouped: dict[str, list[str]] = {}
        for outcome in outcomes:
            signature = stable_id(
                "equivalence_lens_projection",
                definition.definition_id,
                self._project(definition, outcome),
            )
            grouped.setdefault(signature, []).append(outcome.outcome_id)
        classes = tuple(
            LensOutcomeClass(
                equivalence_signature=signature,
                member_outcome_ids=tuple(sorted(set(members))),
            )
            for signature, members in sorted(grouped.items())
        )
        duplicates = tuple(
            sorted(
                outcome_id
                for item in classes
                for outcome_id in item.member_outcome_ids[1:]
            )
        )
        payload = {
            "obligation_id": obligation_id,
            "definition_id": definition.definition_id,
            "binding_id": view.binding.binding_id,
            "equivalence_classes": [item.model_dump(mode="json") for item in classes],
            "duplicate_outcome_ids": duplicates,
        }
        return LensPartition(
            partition_id=stable_id("equivalence_lens_partition", payload),
            obligation_id=obligation_id,
            definition_id=definition.definition_id,
            binding_id=view.binding.binding_id,
            equivalence_classes=classes,
            duplicate_outcome_ids=duplicates,
        )

    def record_evidence(
        self,
        *,
        binding_id: str,
        result: LensEvidenceResult,
        independent_consequence_refs: Sequence[str],
        source_event_key: str,
        cycle: int,
        hypothesis_refs: Sequence[str] = (),
        outcome_refs: Sequence[str] = (),
    ) -> LensEvidenceResultRecord:
        prior = next(
            (
                item
                for item in self.ledger.evidence
                if item.source_event_key == source_event_key
            ),
            None,
        )
        candidate = LensEvidence.build(
            source_event_key=source_event_key,
            binding_id=binding_id,
            result=result,
            cycle=cycle,
            hypothesis_refs=tuple(hypothesis_refs),
            outcome_refs=tuple(outcome_refs),
            independent_consequence_refs=tuple(independent_consequence_refs),
        )
        if prior is not None:
            if prior != candidate:
                raise LensIntegrityError(
                    "Lens evidence source event key was reused with changed evidence."
                )
            return LensEvidenceResultRecord(
                evidence=prior,
                suspended=self.binding_view(binding_id).status
                == LensBindingStatus.SUSPENDED,
                replayed=True,
            )
        if any(
            item.source_event_key == source_event_key
            for item in self.ledger.governance_events
        ):
            raise LensIntegrityError(
                "Lens evidence source event key collides with governance history."
            )
        view = self.binding_view(binding_id)
        if view.status != LensBindingStatus.ACTIVE:
            raise LensUnavailableError("Cannot record inquiry evidence for an inactive lens.")
        will_suspend = (
            candidate.result.trips_failure_counter
            and view.failure_count + 1 >= view.binding.failure_tripwire_count
        )
        tripwire_event = None
        if will_suspend:
            tripwire_key = f"{source_event_key}:tripwire"
            occupied_source_keys = {
                item.source_event_key
                for item in (*self.ledger.evidence, *self.ledger.governance_events)
            }
            if tripwire_key in occupied_source_keys:
                raise LensIntegrityError("Lens tripwire source event key is unavailable.")
            tripwire_event = LensGovernanceEvent.build(
                source_event_key=f"{source_event_key}:tripwire",
                sequence=len(self.ledger.governance_events) + 1,
                cycle=cycle,
                action=LensGovernanceAction.SUSPENDED,
                binding_id=binding_id,
                basis_refs=(candidate.evidence_id, binding_id),
                policy_version=self.GOVERNANCE_POLICY_VERSION,
            )
        governance_events = self.ledger.governance_events
        if tripwire_event is not None:
            governance_events = (*governance_events, tripwire_event)
        updated = self.ledger.model_copy(
            update={
                "evidence": (*self.ledger.evidence, candidate),
                "governance_events": governance_events,
            },
            deep=True,
        )
        self.ledger = LensBindingLedgerState.model_validate(updated.model_dump(mode="json"))
        return LensEvidenceResultRecord(
            evidence=candidate,
            suspended=will_suspend,
            replayed=False,
        )

    def rollback(
        self,
        *,
        binding_id: str,
        target_binding_id: str,
        source_event_key: str,
        cycle: int,
        basis_refs: Sequence[str],
    ) -> LensBindingView:
        replay = next(
            (
                item
                for item in self.ledger.governance_events
                if item.source_event_key == source_event_key
            ),
            None,
        )
        if replay is not None:
            if (
                replay.action != LensGovernanceAction.ROLLED_BACK
                or replay.binding_id != binding_id
                or replay.target_binding_id != target_binding_id
                or replay.basis_refs != tuple(sorted(set(basis_refs)))
            ):
                raise LensIntegrityError(
                    "Lens rollback source event key was reused with a changed request."
                )
            return self.binding_view(target_binding_id)
        occupied_source_keys = {
            item.source_event_key
            for item in (*self.ledger.evidence, *self.ledger.governance_events)
        }
        required_source_keys = {source_event_key, f"{source_event_key}:reactivate"}
        if occupied_source_keys.intersection(required_source_keys):
            raise LensIntegrityError("Lens rollback source event key is unavailable.")
        source = self.binding_view(binding_id)
        target = self.binding_view(target_binding_id)
        if source.binding.obligation_family != target.binding.obligation_family:
            raise LensIntegrityError("Lens rollback crossed an obligation family.")
        if source.status != LensBindingStatus.SUSPENDED:
            raise LensIntegrityError("Lens rollback requires a suspended source binding.")
        if target.status != LensBindingStatus.SUPERSEDED:
            raise LensIntegrityError("Lens rollback target must be the superseded binding.")
        if source.binding.predecessor_binding_id != target_binding_id:
            raise LensIntegrityError("Lens rollback target is not the direct predecessor.")
        sequence = len(self.ledger.governance_events) + 1
        rolled_back = LensGovernanceEvent.build(
            source_event_key=source_event_key,
            sequence=sequence,
            cycle=cycle,
            action=LensGovernanceAction.ROLLED_BACK,
            binding_id=binding_id,
            target_binding_id=target_binding_id,
            basis_refs=tuple(basis_refs),
            policy_version=self.GOVERNANCE_POLICY_VERSION,
        )
        reactivated = LensGovernanceEvent.build(
            source_event_key=f"{source_event_key}:reactivate",
            sequence=sequence + 1,
            cycle=cycle,
            action=LensGovernanceAction.REACTIVATED,
            binding_id=binding_id,
            target_binding_id=target_binding_id,
            basis_refs=(binding_id, target_binding_id, *basis_refs),
            policy_version=self.GOVERNANCE_POLICY_VERSION,
        )
        updated = self.ledger.model_copy(
            update={
                "governance_events": (
                    *self.ledger.governance_events,
                    rolled_back,
                    reactivated,
                )
            },
            deep=True,
        )
        self.ledger = LensBindingLedgerState.model_validate(updated.model_dump(mode="json"))
        return self.binding_view(target_binding_id)
