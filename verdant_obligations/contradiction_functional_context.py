"""Preregistered functional contexts for Contradiction provenance probes.

The context fixes two claim-local source-root queries and all admissible
outcome classes before either matched arm is executed.  It is deliberately
derived from the complete family-local hypothesis bundle: this makes the
probe replayable and tamper evident, but does not establish source
independence, prediction, truth, or external generalization.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel.models import FrozenRecord, stable_id

from .contradiction_hypotheses import ContradictionHypothesisBundle


CONTRADICTION_FUNCTIONAL_CONTEXT_VERSION = (
    "contradiction_functional_context_v0.36"
)


class ContradictionFunctionalDisposition(str, Enum):
    """Bounded result classes for the two preregistered routes."""

    DISTINCT_CONTEXTUAL_ROUTING = "distinct_contextual_routing"
    VALID_NULL_SHARED_ROUTING = "valid_null_shared_routing"
    INCONCLUSIVE_OVERLAPPING_ROUTING = "inconclusive_overlapping_routing"


CONTRADICTION_FUNCTIONAL_ALTERNATIVES = (
    ContradictionFunctionalDisposition.DISTINCT_CONTEXTUAL_ROUTING,
    ContradictionFunctionalDisposition.VALID_NULL_SHARED_ROUTING,
    ContradictionFunctionalDisposition.INCONCLUSIVE_OVERLAPPING_ROUTING,
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


class ContradictionFunctionalProbeContext(FrozenRecord):
    """Content-addressed two-route context committed before execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    context_id: str
    context_version: str = CONTRADICTION_FUNCTIONAL_CONTEXT_VERSION
    hypothesis_bundle: ContradictionHypothesisBundle
    obligation_id: str
    obligation_event_ref: str
    contradiction_ref: str
    bundle_ref: str
    evidence_receipt_ref: str
    claim_refs: tuple[str, str]
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    query_source_roots: tuple[tuple[str, ...], tuple[str, ...]]
    source_root_universe: tuple[str, ...] = Field(min_length=1)
    functional_alternatives: tuple[ContradictionFunctionalDisposition, ...] = (
        CONTRADICTION_FUNCTIONAL_ALTERNATIVES
    )
    route_count: int = Field(default=2, ge=2, le=2)
    evidence_suppression_permitted: bool = False
    truth_selection_authority_enabled: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        hypothesis_bundle: ContradictionHypothesisBundle,
    ) -> "ContradictionFunctionalProbeContext":
        bundle = ContradictionHypothesisBundle.model_validate(
            hypothesis_bundle.model_dump(mode="json")
        )
        receipt = bundle.evidence_receipt
        queries = tuple(side.support_source_roots for side in receipt.claim_sides)
        universe = tuple(sorted({root for roots in queries for root in roots}))
        values = {
            "context_version": CONTRADICTION_FUNCTIONAL_CONTEXT_VERSION,
            "hypothesis_bundle": bundle,
            "obligation_id": receipt.obligation_id,
            "obligation_event_ref": receipt.obligation_event_ref,
            "contradiction_ref": receipt.contradiction_ref,
            "bundle_ref": bundle.bundle_id,
            "evidence_receipt_ref": receipt.receipt_id,
            "claim_refs": receipt.protected_claim_refs,
            "protected_evidence_refs": receipt.protected_evidence_refs,
            "query_source_roots": queries,
            "source_root_universe": universe,
            "functional_alternatives": CONTRADICTION_FUNCTIONAL_ALTERNATIVES,
            "route_count": 2,
            "evidence_suppression_permitted": False,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["context_id"] = stable_id(
            "contradiction_functional_probe_context",
            _record_payload(values),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_context(self) -> "ContradictionFunctionalProbeContext":
        if self.context_version != CONTRADICTION_FUNCTIONAL_CONTEXT_VERSION:
            raise ValueError("Unknown Contradiction functional-context version.")
        bundle = self.hypothesis_bundle
        receipt = bundle.evidence_receipt
        expected_queries = tuple(
            side.support_source_roots for side in receipt.claim_sides
        )
        expected_universe = tuple(
            sorted({root for roots in expected_queries for root in roots})
        )
        expected = {
            "obligation_id": receipt.obligation_id,
            "obligation_event_ref": receipt.obligation_event_ref,
            "contradiction_ref": receipt.contradiction_ref,
            "bundle_ref": bundle.bundle_id,
            "evidence_receipt_ref": receipt.receipt_id,
            "claim_refs": receipt.protected_claim_refs,
            "protected_evidence_refs": receipt.protected_evidence_refs,
            "query_source_roots": expected_queries,
            "source_root_universe": expected_universe,
        }
        if any(getattr(self, key) != value for key, value in expected.items()):
            raise ValueError(
                "Contradiction functional context altered its canonical query roots."
            )
        if any(not roots for roots in self.query_source_roots):
            raise ValueError("Contradiction functional routes require source roots.")
        if any(
            tuple(sorted(set(roots))) != roots
            for roots in self.query_source_roots
        ):
            raise ValueError(
                "Contradiction functional query roots must be sorted and unique."
            )
        if self.source_root_universe != tuple(
            sorted(set(self.source_root_universe))
        ):
            raise ValueError(
                "Contradiction functional source universe must be sorted and unique."
            )
        if (
            self.route_count != 2
            or self.functional_alternatives
            != CONTRADICTION_FUNCTIONAL_ALTERNATIVES
        ):
            raise ValueError(
                "Contradiction functional context lost its bounded alternatives."
            )
        if any(
            (
                self.evidence_suppression_permitted,
                self.truth_selection_authority_enabled,
                self.observed_outcome_authority_enabled,
                self.resolution_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError(
                "Contradiction functional context cannot carry authority."
            )
        payload = self.model_dump(mode="json", exclude={"context_id"})
        if self.context_id != stable_id(
            "contradiction_functional_probe_context", payload
        ):
            raise ValueError("Contradiction functional-context checksum mismatch.")
        return self
