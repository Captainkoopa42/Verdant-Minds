"""Causally non-committing counterfactual overlays and resource accounting.

The runtime deliberately keeps simulation records outside ``KernelState``.
Canonical Verdant state is exposed to an overlay through read-through access;
writes are retained only as typed overlay patches.  Settlement is refused if
the canonical fingerprint changed while a simulation was open.

This module does not generate hypotheses, evaluate semantic truth, close an
obligation, or promote simulated state into canonical memory.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import (
    ObligationAttentionAllocation,
    ObligationAttentionDecisionRecord,
    VerdantKernel,
)
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id


COUNTERFACTUAL_RUNTIME_VERSION = "counterfactual_runtime_v0.4"
SIMULATION_LEDGER_SCHEMA_VERSION = "simulation_ledger_v0.4"
COUNTERFACTUAL_EXECUTION_TRACE_VERSION = "counterfactual_execution_trace_v0.23"
COUNTERFACTUAL_COLLECTIONS = frozenset(
    {
        "evidence",
        "concepts",
        "relations",
        "claims",
        "contradictions",
        "structures",
        "layered_structures",
        "obligation_kernels",
        "workspace_items",
    }
)


class SimulationIntegrityError(RuntimeError):
    pass


class CounterfactualLeakError(SimulationIntegrityError):
    pass


class OverlayOperation(str, Enum):
    UPSERT = "upsert"
    DELETE = "delete"


class SimulationDisposition(str, Enum):
    DISCARDED = "discarded"
    CANCELLED = "cancelled"
    FAILED = "failed"


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _json_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return an isolated JSON value and reject opaque/non-deterministic data."""

    return json.loads(canonical_json_bytes(dict(value)).decode("utf-8"))


class CounterfactualPatch(FrozenRecord):
    patch_id: str
    operation: OverlayOperation
    collection: str
    record_key: str
    value: dict[str, Any] | None = None
    value_sha256: str

    @classmethod
    def upsert(
        cls,
        collection: str,
        record_key: str,
        value: Mapping[str, Any],
    ) -> "CounterfactualPatch":
        normalized = _json_mapping(value)
        return cls._build(
            operation=OverlayOperation.UPSERT,
            collection=collection,
            record_key=record_key,
            value=normalized,
        )

    @classmethod
    def delete(cls, collection: str, record_key: str) -> "CounterfactualPatch":
        return cls._build(
            operation=OverlayOperation.DELETE,
            collection=collection,
            record_key=record_key,
            value=None,
        )

    @classmethod
    def _build(cls, **values: Any) -> "CounterfactualPatch":
        value_sha256 = _digest(values.get("value"))
        values["value_sha256"] = value_sha256
        values["patch_id"] = stable_id(
            "counterfactual_patch",
            values["operation"].value,
            values["collection"],
            values["record_key"],
            value_sha256,
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_patch(self) -> "CounterfactualPatch":
        if not self.collection.strip() or not self.record_key.strip():
            raise ValueError("Counterfactual patch identity fields cannot be empty.")
        if self.collection not in COUNTERFACTUAL_COLLECTIONS:
            raise ValueError("Counterfactual patch collection is not authorized.")
        if self.operation == OverlayOperation.UPSERT and self.value is None:
            raise ValueError("Counterfactual upsert requires a value.")
        if self.operation == OverlayOperation.DELETE and self.value is not None:
            raise ValueError("Counterfactual delete cannot carry a value.")
        expected_value = _digest(self.value)
        if self.value_sha256 != expected_value:
            raise ValueError("Counterfactual patch value checksum mismatch.")
        expected_id = stable_id(
            "counterfactual_patch",
            self.operation.value,
            self.collection,
            self.record_key,
            self.value_sha256,
        )
        if self.patch_id != expected_id:
            raise ValueError("Counterfactual patch identity checksum mismatch.")
        return self


class CounterfactualPlan(FrozenRecord):
    plan_id: str
    source_event_key: str
    operator_version: str
    requested_budget: float = Field(gt=0.0)
    consumed_budget: float = Field(ge=0.0)
    patches: tuple[CounterfactualPatch, ...] = ()
    apply_patch_count: int = Field(ge=0)
    disposition: SimulationDisposition = SimulationDisposition.DISCARDED
    termination_code: str | None = None
    result_refs: tuple[str, ...] = ()

    @classmethod
    def build(
        cls,
        *,
        source_event_key: str,
        operator_version: str,
        requested_budget: float,
        consumed_budget: float,
        patches: Sequence[CounterfactualPatch] = (),
        apply_patch_count: int | None = None,
        disposition: SimulationDisposition = SimulationDisposition.DISCARDED,
        termination_code: str | None = None,
        result_refs: Sequence[str] = (),
    ) -> "CounterfactualPlan":
        normalized_patches = tuple(patches)
        count = len(normalized_patches) if apply_patch_count is None else apply_patch_count
        values = {
            "source_event_key": source_event_key,
            "operator_version": operator_version,
            "requested_budget": requested_budget,
            "consumed_budget": consumed_budget,
            "patches": normalized_patches,
            "apply_patch_count": count,
            "disposition": disposition,
            "termination_code": termination_code,
            "result_refs": tuple(sorted(set(result_refs))),
        }
        payload = _model_payload(values)
        values["plan_id"] = stable_id("counterfactual_plan", payload)
        return cls(**values)

    @model_validator(mode="after")
    def validate_plan(self) -> "CounterfactualPlan":
        if not self.source_event_key.strip() or not self.operator_version.strip():
            raise ValueError("Counterfactual plan identifiers cannot be empty.")
        if self.consumed_budget > self.requested_budget + 1e-12:
            raise ValueError("Simulation consumption cannot exceed its reservation.")
        if self.apply_patch_count > len(self.patches):
            raise ValueError("Applied patch count exceeds the declared plan.")
        patch_ids = tuple(item.patch_id for item in self.patches)
        if len(set(patch_ids)) != len(patch_ids):
            raise ValueError("Counterfactual plan contains a duplicate patch.")
        if tuple(sorted(set(self.result_refs))) != self.result_refs:
            raise ValueError("Counterfactual result refs must be sorted and unique.")
        if self.disposition == SimulationDisposition.DISCARDED:
            if self.termination_code is not None:
                raise ValueError("A completed discarded run has no termination code.")
        elif self.termination_code is None or not self.termination_code.strip():
            raise ValueError("Cancelled and failed runs require a termination code.")
        payload = self.model_dump(mode="json", exclude={"plan_id"})
        if self.plan_id != stable_id("counterfactual_plan", payload):
            raise ValueError("Counterfactual plan identity checksum mismatch.")
        return self


def _model_payload(values: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, BaseModel):
            payload[key] = value.model_dump(mode="json")
        elif isinstance(value, Enum):
            payload[key] = value.value
        elif isinstance(value, (tuple, list)):
            payload[key] = [
                item.model_dump(mode="json") if isinstance(item, BaseModel)
                else item.value if isinstance(item, Enum)
                else item
                for item in value
            ]
        else:
            payload[key] = value
    return payload


class SimulationReservation(FrozenRecord):
    reservation_id: str
    source_event_key: str
    plan_id: str
    attention_decision_id: str
    allocation_id: str
    obligation_id: str
    requested_budget: float = Field(gt=0.0)
    allocation_granted_budget: float = Field(gt=0.0)
    canonical_fingerprint: str
    canonical_cycle: int = Field(ge=0)
    runtime_version: str
    epistemic_authority_enabled: bool = False
    request_sha256: str

    @classmethod
    def build(cls, **values: Any) -> "SimulationReservation":
        values.setdefault("epistemic_authority_enabled", False)
        payload = _model_payload(
            {
                key: value
                for key, value in values.items()
                if key not in {"reservation_id", "request_sha256"}
            }
        )
        values["request_sha256"] = _digest(payload)
        values["reservation_id"] = stable_id(
            "simulation_reservation",
            values["source_event_key"],
            values["request_sha256"],
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_reservation(self) -> "SimulationReservation":
        identifiers = (
            self.source_event_key,
            self.plan_id,
            self.attention_decision_id,
            self.allocation_id,
            self.obligation_id,
            self.runtime_version,
        )
        if not all(item.strip() for item in identifiers):
            raise ValueError("Simulation reservation identifiers cannot be empty.")
        if self.epistemic_authority_enabled:
            raise ValueError("Simulation reservations cannot carry epistemic authority.")
        if self.requested_budget > self.allocation_granted_budget + 1e-12:
            raise ValueError("Simulation reservation exceeds its attention allocation.")
        for digest in (self.canonical_fingerprint, self.request_sha256):
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError("Simulation reservation digests must be lowercase SHA-256.")
        payload = self.model_dump(
            mode="json", exclude={"reservation_id", "request_sha256"}
        )
        if self.request_sha256 != _digest(payload):
            raise ValueError("Simulation reservation request checksum mismatch.")
        expected_id = stable_id(
            "simulation_reservation",
            self.source_event_key,
            self.request_sha256,
        )
        if self.reservation_id != expected_id:
            raise ValueError("Simulation reservation identity checksum mismatch.")
        return self


class SimulationSettlement(FrozenRecord):
    settlement_id: str
    reservation_id: str
    disposition: SimulationDisposition
    consumed_budget: float = Field(ge=0.0)
    overlay_fingerprint: str
    applied_patch_ids: tuple[str, ...] = ()
    result_refs: tuple[str, ...] = ()
    termination_code: str | None = None
    canonical_before_fingerprint: str
    canonical_after_fingerprint: str
    canonical_unchanged: bool = True
    canonical_commit_permitted: bool = False
    epistemic_authority_enabled: bool = False
    payload_sha256: str

    @classmethod
    def build(cls, **values: Any) -> "SimulationSettlement":
        values.setdefault("canonical_unchanged", True)
        values.setdefault("canonical_commit_permitted", False)
        values.setdefault("epistemic_authority_enabled", False)
        payload = _model_payload(
            {
                key: value
                for key, value in values.items()
                if key not in {"settlement_id", "payload_sha256"}
            }
        )
        values["payload_sha256"] = _digest(payload)
        values["settlement_id"] = stable_id(
            "simulation_settlement",
            values["reservation_id"],
            values["payload_sha256"],
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_settlement(self) -> "SimulationSettlement":
        if not self.reservation_id.strip():
            raise ValueError("Simulation settlement requires a reservation.")
        for digest in (
            self.overlay_fingerprint,
            self.canonical_before_fingerprint,
            self.canonical_after_fingerprint,
            self.payload_sha256,
        ):
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError("Simulation settlement digests must be lowercase SHA-256.")
        if not self.canonical_unchanged:
            raise ValueError("A leaking simulation cannot produce a valid settlement.")
        if self.canonical_before_fingerprint != self.canonical_after_fingerprint:
            raise ValueError("Simulation settlement fingerprints reveal canonical mutation.")
        if self.canonical_commit_permitted or self.epistemic_authority_enabled:
            raise ValueError("Simulation settlement cannot commit or assert epistemic authority.")
        if len(set(self.applied_patch_ids)) != len(self.applied_patch_ids):
            raise ValueError("Simulation settlement contains a duplicate applied patch.")
        if tuple(sorted(set(self.result_refs))) != self.result_refs:
            raise ValueError("Simulation settlement result refs must be sorted and unique.")
        if self.disposition == SimulationDisposition.DISCARDED:
            if self.termination_code is not None:
                raise ValueError("Discarded simulation cannot have a termination code.")
        elif self.termination_code is None or not self.termination_code.strip():
            raise ValueError("Cancelled and failed settlements require a termination code.")
        payload = self.model_dump(
            mode="json", exclude={"settlement_id", "payload_sha256"}
        )
        if self.payload_sha256 != _digest(payload):
            raise ValueError("Simulation settlement payload checksum mismatch.")
        expected_id = stable_id(
            "simulation_settlement",
            self.reservation_id,
            self.payload_sha256,
        )
        if self.settlement_id != expected_id:
            raise ValueError("Simulation settlement identity checksum mismatch.")
        return self


def _execution_match_signature(
    *,
    operator_version: str,
    obligation_id: str,
    attention_decision_id: str,
    allocation_id: str,
    canonical_fingerprint: str,
    requested_budget: float,
    consumed_budget: float,
    disposition: SimulationDisposition,
    termination_code: str | None,
    declared_patch_ids: tuple[str, ...],
    result_refs: tuple[str, ...],
) -> str:
    return stable_id(
        "counterfactual_match_signature",
        COUNTERFACTUAL_EXECUTION_TRACE_VERSION,
        {
            "operator_version": operator_version,
            "obligation_id": obligation_id,
            "attention_decision_id": attention_decision_id,
            "allocation_id": allocation_id,
            "canonical_fingerprint": canonical_fingerprint,
            "requested_budget": requested_budget,
            "consumed_budget": consumed_budget,
            "disposition": disposition.value,
            "termination_code": termination_code,
            "declared_patch_ids": declared_patch_ids,
            "result_refs": result_refs,
        },
    )


class CounterfactualCollectionDelta(FrozenRecord):
    """Complete record-key delta for one materialized overlay collection."""

    collection: str
    before_sha256: str
    after_sha256: str
    before_record_count: int = Field(ge=0)
    after_record_count: int = Field(ge=0)
    added_record_keys: tuple[str, ...] = ()
    removed_record_keys: tuple[str, ...] = ()
    changed_record_keys: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_delta(self) -> "CounterfactualCollectionDelta":
        if self.collection not in COUNTERFACTUAL_COLLECTIONS:
            raise ValueError("Counterfactual trace contains an unknown collection.")
        for digest in (self.before_sha256, self.after_sha256):
            if len(digest) != 64 or any(
                ch not in "0123456789abcdef" for ch in digest
            ):
                raise ValueError(
                    "Counterfactual collection fingerprints must be lowercase SHA-256."
                )
        groups = (
            self.added_record_keys,
            self.removed_record_keys,
            self.changed_record_keys,
        )
        if any(tuple(sorted(set(values))) != values for values in groups):
            raise ValueError(
                "Counterfactual collection delta keys must be sorted and unique."
            )
        added, removed, changed = (set(values) for values in groups)
        if added & removed or added & changed or removed & changed:
            raise ValueError("Counterfactual collection delta classes must be disjoint.")
        if self.after_record_count != (
            self.before_record_count + len(added) - len(removed)
        ):
            raise ValueError("Counterfactual collection delta record counts disagree.")
        has_delta = bool(added or removed or changed)
        if has_delta == (self.before_sha256 == self.after_sha256):
            raise ValueError(
                "Counterfactual collection delta disagrees with its fingerprints."
            )
        return self


class CounterfactualExecutionTrace(FrozenRecord):
    """Reconstructable structural receipt derived from an executed overlay."""

    trace_id: str
    trace_version: str = COUNTERFACTUAL_EXECUTION_TRACE_VERSION
    match_signature: str
    source_event_key: str
    operator_version: str
    obligation_id: str
    attention_decision_id: str
    allocation_id: str
    plan_id: str
    reservation_id: str
    settlement_id: str
    canonical_fingerprint: str
    overlay_fingerprint: str
    requested_budget: float = Field(gt=0.0)
    consumed_budget: float = Field(ge=0.0)
    disposition: SimulationDisposition
    termination_code: str | None = None
    declared_patch_ids: tuple[str, ...] = ()
    applied_patch_ids: tuple[str, ...] = ()
    result_refs: tuple[str, ...] = ()
    collection_deltas: tuple[CounterfactualCollectionDelta, ...]
    canonical_unchanged: bool = True
    canonical_commit_permitted: bool = False
    epistemic_authority_enabled: bool = False

    @classmethod
    def build(cls, **values: Any) -> "CounterfactualExecutionTrace":
        deltas = tuple(
            item
            if isinstance(item, CounterfactualCollectionDelta)
            else CounterfactualCollectionDelta.model_validate(item)
            for item in values["collection_deltas"]
        )
        values["collection_deltas"] = tuple(
            sorted(deltas, key=lambda item: item.collection)
        )
        values.setdefault("trace_version", COUNTERFACTUAL_EXECUTION_TRACE_VERSION)
        values.setdefault("canonical_unchanged", True)
        values.setdefault("canonical_commit_permitted", False)
        values.setdefault("epistemic_authority_enabled", False)
        values["trace_id"] = stable_id(
            "counterfactual_execution_trace",
            _model_payload(
                {
                    key: value
                    for key, value in values.items()
                    if key != "trace_id"
                }
            ),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_trace(self) -> "CounterfactualExecutionTrace":
        if self.trace_version != COUNTERFACTUAL_EXECUTION_TRACE_VERSION:
            raise ValueError("Unsupported counterfactual execution trace version.")
        identifiers = (
            self.match_signature,
            self.source_event_key,
            self.operator_version,
            self.obligation_id,
            self.attention_decision_id,
            self.allocation_id,
            self.plan_id,
            self.reservation_id,
            self.settlement_id,
        )
        if not all(item.strip() for item in identifiers):
            raise ValueError("Counterfactual execution trace identifiers cannot be empty.")
        for digest in (
            self.canonical_fingerprint,
            self.overlay_fingerprint,
        ):
            if len(digest) != 64 or any(
                ch not in "0123456789abcdef" for ch in digest
            ):
                raise ValueError(
                    "Counterfactual execution trace digests must be lowercase SHA-256."
                )
        if self.consumed_budget > self.requested_budget + 1e-12:
            raise ValueError("Counterfactual execution trace exceeds its reservation.")
        if self.disposition == SimulationDisposition.DISCARDED:
            if self.termination_code is not None:
                raise ValueError("Discarded execution trace cannot have a termination code.")
        elif self.termination_code is None or not self.termination_code.strip():
            raise ValueError(
                "Cancelled and failed execution traces require a termination code."
            )
        if len(set(self.declared_patch_ids)) != len(self.declared_patch_ids):
            raise ValueError("Counterfactual trace repeats a declared patch.")
        if self.applied_patch_ids != self.declared_patch_ids[
            : len(self.applied_patch_ids)
        ]:
            raise ValueError("Counterfactual trace applied a non-prefix patch set.")
        if tuple(sorted(set(self.result_refs))) != self.result_refs:
            raise ValueError("Counterfactual trace result refs must be sorted and unique.")
        collections = tuple(item.collection for item in self.collection_deltas)
        if collections != tuple(sorted(COUNTERFACTUAL_COLLECTIONS)):
            raise ValueError(
                "Counterfactual execution trace must cover every overlay collection."
            )
        if (
            not self.canonical_unchanged
            or self.canonical_commit_permitted
            or self.epistemic_authority_enabled
        ):
            raise ValueError(
                "Counterfactual execution traces cannot mutate or assert authority."
            )
        expected_match = _execution_match_signature(
            operator_version=self.operator_version,
            obligation_id=self.obligation_id,
            attention_decision_id=self.attention_decision_id,
            allocation_id=self.allocation_id,
            canonical_fingerprint=self.canonical_fingerprint,
            requested_budget=self.requested_budget,
            consumed_budget=self.consumed_budget,
            disposition=self.disposition,
            termination_code=self.termination_code,
            declared_patch_ids=self.declared_patch_ids,
            result_refs=self.result_refs,
        )
        if self.match_signature != expected_match:
            raise ValueError("Counterfactual execution match signature was altered.")
        payload = self.model_dump(mode="json", exclude={"trace_id"})
        if self.trace_id != stable_id("counterfactual_execution_trace", payload):
            raise ValueError("Counterfactual execution trace checksum mismatch.")
        return self


class SimulationLedgerState(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    schema_version: str = SIMULATION_LEDGER_SCHEMA_VERSION
    reservations: tuple[SimulationReservation, ...] = ()
    settlements: tuple[SimulationSettlement, ...] = ()

    @model_validator(mode="after")
    def validate_ledger(self) -> "SimulationLedgerState":
        if self.schema_version != SIMULATION_LEDGER_SCHEMA_VERSION:
            raise ValueError("Unsupported simulation ledger schema.")
        reservation_ids = tuple(item.reservation_id for item in self.reservations)
        source_keys = tuple(item.source_event_key for item in self.reservations)
        if len(set(reservation_ids)) != len(reservation_ids):
            raise ValueError("Simulation ledger duplicates a reservation.")
        if len(set(source_keys)) != len(source_keys):
            raise ValueError("Simulation ledger reuses a source event key.")
        settlement_ids = tuple(item.settlement_id for item in self.settlements)
        if len(set(settlement_ids)) != len(settlement_ids):
            raise ValueError("Simulation ledger duplicates a settlement.")
        by_reservation = {item.reservation_id: item for item in self.reservations}
        settled_reservations: set[str] = set()
        for settlement in self.settlements:
            reservation = by_reservation.get(settlement.reservation_id)
            if reservation is None:
                raise ValueError("Simulation settlement lost its reservation.")
            if settlement.reservation_id in settled_reservations:
                raise ValueError("Simulation reservation was settled more than once.")
            if settlement.consumed_budget > reservation.requested_budget + 1e-12:
                raise ValueError("Simulation settlement exceeds its reservation.")
            settled_reservations.add(settlement.reservation_id)
        for allocation_id in {item.allocation_id for item in self.reservations}:
            reservations = [
                item for item in self.reservations if item.allocation_id == allocation_id
            ]
            grants = {item.allocation_granted_budget for item in reservations}
            if len(grants) != 1:
                raise ValueError("Simulation allocation grant drift detected.")
            grant = next(iter(grants))
            spent = sum(
                settlement.consumed_budget
                for settlement in self.settlements
                if by_reservation[settlement.reservation_id].allocation_id
                == allocation_id
            )
            outstanding = sum(
                item.requested_budget
                for item in reservations
                if item.reservation_id not in settled_reservations
            )
            if spent + outstanding > grant + 1e-12:
                raise ValueError("Simulation ledger exceeds an attention allocation.")
        return self

    def fingerprint(self) -> str:
        return _digest(self.model_dump(mode="json"))


class CounterfactualOverlay:
    """Read-through canonical projection plus local copy-on-write patches."""

    ALLOWED_COLLECTIONS = COUNTERFACTUAL_COLLECTIONS

    def __init__(self, kernel: VerdantKernel) -> None:
        self._kernel = kernel
        self.base_fingerprint = kernel.fingerprint()
        self._writes: dict[tuple[str, str], dict[str, Any]] = {}
        self._deletes: set[tuple[str, str]] = set()
        self._patches: list[CounterfactualPatch] = []

    @staticmethod
    def _base_value(value: Any) -> dict[str, Any]:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, Mapping):
            return _json_mapping(value)
        raise SimulationIntegrityError("Overlay records must be typed or mapping values.")

    @classmethod
    def _validate_collection(cls, collection: str) -> None:
        if collection not in cls.ALLOWED_COLLECTIONS:
            raise SimulationIntegrityError(
                f"Counterfactual collection {collection!r} is not authorized."
            )

    def read(self, collection: str, record_key: str) -> dict[str, Any] | None:
        self._validate_collection(collection)
        address = (collection, record_key)
        if address in self._deletes:
            return None
        if address in self._writes:
            return deepcopy(self._writes[address])
        base = getattr(self._kernel.state, collection)
        value = base.get(record_key)
        return None if value is None else deepcopy(self._base_value(value))

    def apply(self, patch: CounterfactualPatch) -> None:
        self._validate_collection(patch.collection)
        address = (patch.collection, patch.record_key)
        if patch.operation == OverlayOperation.UPSERT:
            assert patch.value is not None
            self._writes[address] = deepcopy(patch.value)
            self._deletes.discard(address)
        else:
            self._writes.pop(address, None)
            self._deletes.add(address)
        self._patches.append(patch)

    @property
    def patches(self) -> tuple[CounterfactualPatch, ...]:
        return tuple(self._patches)

    def materialize_collection(self, collection: str) -> dict[str, dict[str, Any]]:
        self._validate_collection(collection)
        base = getattr(self._kernel.state, collection)
        materialized = {
            key: self._base_value(value)
            for key, value in base.items()
        }
        for (candidate_collection, key), value in self._writes.items():
            if candidate_collection == collection:
                materialized[key] = deepcopy(value)
        for candidate_collection, key in self._deletes:
            if candidate_collection == collection:
                materialized.pop(key, None)
        return dict(sorted(materialized.items()))

    def fingerprint(self) -> str:
        return _digest(
            {
                "base_fingerprint": self.base_fingerprint,
                "patches": [item.model_dump(mode="json") for item in self._patches],
            }
        )


def derive_counterfactual_execution_trace(
    kernel: VerdantKernel,
    ledger: "SimulationLedger",
    *,
    plan: CounterfactualPlan,
    reservation: SimulationReservation,
    settlement: SimulationSettlement,
) -> CounterfactualExecutionTrace:
    """Reconstruct and validate the materialized overlay for one real settlement."""

    plan = CounterfactualPlan.model_validate(plan.model_dump(mode="json"))
    reservation = SimulationReservation.model_validate(
        reservation.model_dump(mode="json")
    )
    settlement = SimulationSettlement.model_validate(
        settlement.model_dump(mode="json")
    )
    canonical_reservation = next(
        (
            item
            for item in ledger.state.reservations
            if item.reservation_id == reservation.reservation_id
        ),
        None,
    )
    canonical_settlement = next(
        (
            item
            for item in ledger.state.settlements
            if item.settlement_id == settlement.settlement_id
        ),
        None,
    )
    if canonical_reservation != reservation or canonical_settlement != settlement:
        raise SimulationIntegrityError(
            "Counterfactual trace cites a foreign or altered simulation record."
        )
    if (
        reservation.plan_id != plan.plan_id
        or reservation.source_event_key != plan.source_event_key
        or reservation.canonical_fingerprint != kernel.fingerprint()
        or settlement.reservation_id != reservation.reservation_id
        or settlement.disposition != plan.disposition
        or abs(settlement.consumed_budget - plan.consumed_budget) > 1e-12
        or settlement.result_refs != plan.result_refs
    ):
        raise SimulationIntegrityError(
            "Counterfactual trace lost its plan, checkpoint, or settlement lineage."
        )
    expected_applied = tuple(
        item.patch_id for item in plan.patches[: plan.apply_patch_count]
    )
    if settlement.applied_patch_ids != expected_applied:
        raise SimulationIntegrityError(
            "Counterfactual trace patch application differs from its plan."
        )

    baseline = CounterfactualOverlay(kernel)
    overlay = CounterfactualOverlay(kernel)
    for patch in plan.patches[: plan.apply_patch_count]:
        overlay.apply(patch)
    if overlay.fingerprint() != settlement.overlay_fingerprint:
        raise SimulationIntegrityError(
            "Counterfactual trace overlay fingerprint differs from its settlement."
        )

    deltas = []
    for collection in sorted(COUNTERFACTUAL_COLLECTIONS):
        before = baseline.materialize_collection(collection)
        after = overlay.materialize_collection(collection)
        before_keys = set(before)
        after_keys = set(after)
        common = before_keys & after_keys
        deltas.append(
            CounterfactualCollectionDelta(
                collection=collection,
                before_sha256=_digest(before),
                after_sha256=_digest(after),
                before_record_count=len(before),
                after_record_count=len(after),
                added_record_keys=tuple(sorted(after_keys - before_keys)),
                removed_record_keys=tuple(sorted(before_keys - after_keys)),
                changed_record_keys=tuple(
                    sorted(key for key in common if before[key] != after[key])
                ),
            )
        )

    declared_patch_ids = tuple(item.patch_id for item in plan.patches)
    match_signature = _execution_match_signature(
        operator_version=plan.operator_version,
        obligation_id=reservation.obligation_id,
        attention_decision_id=reservation.attention_decision_id,
        allocation_id=reservation.allocation_id,
        canonical_fingerprint=reservation.canonical_fingerprint,
        requested_budget=plan.requested_budget,
        consumed_budget=plan.consumed_budget,
        disposition=plan.disposition,
        termination_code=plan.termination_code,
        declared_patch_ids=declared_patch_ids,
        result_refs=plan.result_refs,
    )
    return CounterfactualExecutionTrace.build(
        match_signature=match_signature,
        source_event_key=plan.source_event_key,
        operator_version=plan.operator_version,
        obligation_id=reservation.obligation_id,
        attention_decision_id=reservation.attention_decision_id,
        allocation_id=reservation.allocation_id,
        plan_id=plan.plan_id,
        reservation_id=reservation.reservation_id,
        settlement_id=settlement.settlement_id,
        canonical_fingerprint=reservation.canonical_fingerprint,
        overlay_fingerprint=settlement.overlay_fingerprint,
        requested_budget=plan.requested_budget,
        consumed_budget=plan.consumed_budget,
        disposition=plan.disposition,
        termination_code=plan.termination_code,
        declared_patch_ids=declared_patch_ids,
        applied_patch_ids=settlement.applied_patch_ids,
        result_refs=settlement.result_refs,
        collection_deltas=tuple(deltas),
    )


class SimulationLedger:
    def __init__(self, state: SimulationLedgerState | None = None) -> None:
        self.state = (state or SimulationLedgerState()).model_copy(deep=True)

    @classmethod
    def from_state(cls, state: SimulationLedgerState) -> "SimulationLedger":
        return cls(SimulationLedgerState.model_validate(state.model_dump(mode="json")))

    def snapshot(self) -> SimulationLedgerState:
        return self.state.model_copy(deep=True)

    def fingerprint(self) -> str:
        return self.state.fingerprint()

    def _settlement_for(self, reservation_id: str) -> SimulationSettlement | None:
        return next(
            (
                item
                for item in self.state.settlements
                if item.reservation_id == reservation_id
            ),
            None,
        )

    def reserve(
        self,
        *,
        kernel: VerdantKernel,
        decision: ObligationAttentionDecisionRecord,
        allocation: ObligationAttentionAllocation,
        plan: CounterfactualPlan,
    ) -> tuple[SimulationReservation, bool]:
        canonical_decision = next(
            (
                item
                for item in kernel.state.obligation_attention_decisions
                if item.decision_id == decision.decision_id
            ),
            None,
        )
        if canonical_decision != decision:
            raise SimulationIntegrityError(
                "Simulation reservation cites a non-canonical attention decision."
            )
        canonical_allocation = next(
            (
                item
                for item in decision.allocations
                if item.allocation_id == allocation.allocation_id
            ),
            None,
        )
        if canonical_allocation != allocation:
            raise SimulationIntegrityError(
                "Simulation reservation cites a non-canonical attention allocation."
            )
        candidate = SimulationReservation.build(
            source_event_key=plan.source_event_key,
            plan_id=plan.plan_id,
            attention_decision_id=decision.decision_id,
            allocation_id=allocation.allocation_id,
            obligation_id=allocation.obligation_id,
            requested_budget=plan.requested_budget,
            allocation_granted_budget=allocation.granted_budget,
            canonical_fingerprint=kernel.fingerprint(),
            canonical_cycle=kernel.state.cycle,
            runtime_version=COUNTERFACTUAL_RUNTIME_VERSION,
        )
        prior = next(
            (
                item
                for item in self.state.reservations
                if item.source_event_key == plan.source_event_key
            ),
            None,
        )
        if prior is not None:
            if prior != candidate:
                raise SimulationIntegrityError(
                    "Simulation source event key was reused with a different request."
                )
            return prior, True
        updated = self.state.model_copy(
            update={"reservations": (*self.state.reservations, candidate)},
            deep=True,
        )
        self.state = SimulationLedgerState.model_validate(updated.model_dump(mode="json"))
        return candidate, False

    def settle(
        self,
        *,
        reservation: SimulationReservation,
        plan: CounterfactualPlan,
        overlay: CounterfactualOverlay,
        kernel: VerdantKernel,
    ) -> SimulationSettlement:
        canonical_reservation = next(
            (
                item
                for item in self.state.reservations
                if item.reservation_id == reservation.reservation_id
            ),
            None,
        )
        if canonical_reservation != reservation:
            raise SimulationIntegrityError(
                "Simulation settlement cites an unknown or altered reservation."
            )
        if reservation.plan_id != plan.plan_id:
            raise SimulationIntegrityError(
                "Simulation settlement plan differs from its reservation."
            )
        if overlay.base_fingerprint != reservation.canonical_fingerprint:
            raise SimulationIntegrityError(
                "Simulation overlay was opened from a different canonical state."
            )
        expected_patches = plan.patches[: plan.apply_patch_count]
        if overlay.patches != expected_patches:
            raise SimulationIntegrityError(
                "Simulation overlay patches differ from the reserved plan."
            )
        prior = self._settlement_for(reservation.reservation_id)
        if prior is not None:
            return prior
        after = kernel.fingerprint()
        if after != reservation.canonical_fingerprint:
            raise CounterfactualLeakError(
                "Canonical state changed during counterfactual execution."
            )
        settlement = SimulationSettlement.build(
            reservation_id=reservation.reservation_id,
            disposition=plan.disposition,
            consumed_budget=plan.consumed_budget,
            overlay_fingerprint=overlay.fingerprint(),
            applied_patch_ids=tuple(item.patch_id for item in overlay.patches),
            result_refs=plan.result_refs,
            termination_code=plan.termination_code,
            canonical_before_fingerprint=reservation.canonical_fingerprint,
            canonical_after_fingerprint=after,
        )
        updated = self.state.model_copy(
            update={"settlements": (*self.state.settlements, settlement)},
            deep=True,
        )
        self.state = SimulationLedgerState.model_validate(updated.model_dump(mode="json"))
        return settlement


@dataclass(frozen=True)
class CounterfactualRunResult:
    reservation: SimulationReservation
    settlement: SimulationSettlement
    trace: CounterfactualExecutionTrace
    replayed: bool


class CounterfactualRuntime:
    def __init__(self, ledger: SimulationLedger | None = None) -> None:
        self.ledger = ledger or SimulationLedger()

    @staticmethod
    def _allocation(
        kernel: VerdantKernel,
        allocation_id: str,
    ) -> tuple[ObligationAttentionDecisionRecord, ObligationAttentionAllocation]:
        for decision in kernel.state.obligation_attention_decisions:
            for allocation in decision.allocations:
                if allocation.allocation_id == allocation_id:
                    return decision, allocation
        raise SimulationIntegrityError(
            "Counterfactual execution requires a canonical attention allocation."
        )

    def execute(
        self,
        kernel: VerdantKernel,
        *,
        allocation_id: str,
        plan: CounterfactualPlan,
    ) -> CounterfactualRunResult:
        decision, allocation = self._allocation(kernel, allocation_id)
        reservation, replayed = self.ledger.reserve(
            kernel=kernel,
            decision=decision,
            allocation=allocation,
            plan=plan,
        )
        prior = self.ledger._settlement_for(reservation.reservation_id)
        if replayed and prior is not None:
            trace = derive_counterfactual_execution_trace(
                kernel,
                self.ledger,
                plan=plan,
                reservation=reservation,
                settlement=prior,
            )
            return CounterfactualRunResult(
                reservation=reservation,
                settlement=prior,
                trace=trace,
                replayed=True,
            )
        overlay = CounterfactualOverlay(kernel)
        for patch in plan.patches[: plan.apply_patch_count]:
            overlay.apply(patch)
        settlement = self.ledger.settle(
            reservation=reservation,
            plan=plan,
            overlay=overlay,
            kernel=kernel,
        )
        trace = derive_counterfactual_execution_trace(
            kernel,
            self.ledger,
            plan=plan,
            reservation=reservation,
            settlement=settlement,
        )
        return CounterfactualRunResult(
            reservation=reservation,
            settlement=settlement,
            trace=trace,
            replayed=replayed,
        )
