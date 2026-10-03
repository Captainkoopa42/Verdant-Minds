"""Bounded, answer-agnostic hypotheses for canonical contradictions.

The protocol preserves both opposed claims and the complete native evidence
ledger.  It can describe a provenance-partition inquiry, a null-artifact
alternative, and an insufficient-evidence alternative, but it cannot select a
claim, suppress evidence, resolve an obligation, or mutate canonical state.
"""
from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import (
    ClaimPolarity,
    ContradictionObligationKernel,
    ObligationFamily,
    ObligationStatus,
    VerdantKernel,
)
from verdant_kernel.models import (
    EvidenceStance,
    FrozenRecord,
    canonical_json_bytes,
    stable_id,
)

from .pipeline import derive_obligation_view


CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION = (
    "contradiction_hypothesis_protocol_v0.33"
)
CONTRADICTION_PROVENANCE_ACTION_OPERATOR = "compare_contradiction_provenance"


class ContradictionHypothesisIntegrityError(RuntimeError):
    """Raised when a contradiction hypothesis loses canonical provenance."""


class ContradictionHypothesisKind(str, Enum):
    PROVENANCE_PARTITION_TEST = "provenance_partition_test"
    NULL_ENCODING_ARTIFACT = "null_encoding_artifact"
    DEFER_INSUFFICIENT_EVIDENCE = "defer_insufficient_evidence"


class ContradictionEvidenceCondition(str, Enum):
    PROVENANCE_DIFFERENCE_REMAINS_DISTINGUISHABLE = (
        "provenance_difference_remains_distinguishable"
    )
    NO_PROVENANCE_DISCRIMINATION = "no_provenance_discrimination"
    ADDITIONAL_CANONICAL_EVIDENCE_REQUIRED = (
        "additional_canonical_evidence_required"
    )


_CONDITION_BY_KIND = {
    ContradictionHypothesisKind.PROVENANCE_PARTITION_TEST: (
        ContradictionEvidenceCondition.PROVENANCE_DIFFERENCE_REMAINS_DISTINGUISHABLE
    ),
    ContradictionHypothesisKind.NULL_ENCODING_ARTIFACT: (
        ContradictionEvidenceCondition.NO_PROVENANCE_DISCRIMINATION
    ),
    ContradictionHypothesisKind.DEFER_INSUFFICIENT_EVIDENCE: (
        ContradictionEvidenceCondition.ADDITIONAL_CANONICAL_EVIDENCE_REQUIRED
    ),
}


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


class ContradictionHypothesisPolicy(BaseModel):
    """Visible bounds for the family-local hypothesis protocol."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol_version: str = CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION
    action_operator: str = CONTRADICTION_PROVENANCE_ACTION_OPERATOR
    minimum_attention_budget: float = Field(default=0.05, gt=0.0)
    hypothesis_count: int = Field(default=3, ge=3, le=3)

    @model_validator(mode="after")
    def validate_policy(self) -> "ContradictionHypothesisPolicy":
        if self.protocol_version != CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION:
            raise ValueError("Unknown contradiction hypothesis protocol version.")
        if self.action_operator != CONTRADICTION_PROVENANCE_ACTION_OPERATOR:
            raise ValueError("Unknown contradiction hypothesis action operator.")
        return self


class ContradictionEvidenceSide(FrozenRecord):
    """One polarity's exact canonical claim/evidence projection."""

    side_id: str
    claim_ref: str
    polarity: ClaimPolarity
    claim_snapshot_sha256: str
    support_evidence_refs: tuple[str, ...] = Field(min_length=1)
    refutation_evidence_refs: tuple[str, ...] = Field(min_length=1)
    support_source_roots: tuple[str, ...] = Field(min_length=1)
    refutation_source_roots: tuple[str, ...] = Field(min_length=1)

    @classmethod
    def build(cls, **values: Any) -> "ContradictionEvidenceSide":
        for key in (
            "support_evidence_refs",
            "refutation_evidence_refs",
            "support_source_roots",
            "refutation_source_roots",
        ):
            values[key] = tuple(sorted(set(values[key])))
        payload = {key: value for key, value in values.items() if key != "side_id"}
        values["side_id"] = stable_id("contradiction_evidence_side", payload)
        return cls(**values)

    @model_validator(mode="after")
    def validate_side(self) -> "ContradictionEvidenceSide":
        if not self.claim_ref.strip() or not _is_sha256(self.claim_snapshot_sha256):
            raise ValueError("Contradiction evidence side lost its claim snapshot.")
        for refs, label in (
            (self.support_evidence_refs, "support evidence"),
            (self.refutation_evidence_refs, "refutation evidence"),
            (self.support_source_roots, "support roots"),
            (self.refutation_source_roots, "refutation roots"),
        ):
            if tuple(sorted(set(refs))) != refs:
                raise ValueError(
                    f"Contradiction evidence side {label} must be sorted and unique."
                )
        if set(self.support_evidence_refs).intersection(self.refutation_evidence_refs):
            raise ValueError(
                "One evidence item cannot both support and refute one claim."
            )
        payload = self.model_dump(mode="json", exclude={"side_id"})
        if self.side_id != stable_id("contradiction_evidence_side", payload):
            raise ValueError("Contradiction evidence-side identity checksum mismatch.")
        return self


class ContradictionEvidenceReceipt(FrozenRecord):
    """Complete non-suppressing evidence snapshot authorized by Attention."""

    receipt_id: str
    protocol_version: str = CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION
    obligation_id: str
    obligation_event_ref: str
    contradiction_ref: str
    claim_key: str
    claim_sides: tuple[ContradictionEvidenceSide, ContradictionEvidenceSide]
    protected_claim_refs: tuple[str, str]
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    shared_support_evidence_refs: tuple[str, ...] = ()
    symmetric_difference_evidence_refs: tuple[str, ...] = ()
    shared_support_source_roots: tuple[str, ...] = ()
    symmetric_difference_source_roots: tuple[str, ...] = ()
    attention_decision_ref: str
    attention_bid_ref: str
    attention_allocation_ref: str
    authorized_budget: float = Field(gt=0.0)
    context_snapshot_sha256: str
    evidence_suppression_permitted: bool = False
    truth_selection_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "ContradictionEvidenceReceipt":
        sides = tuple(sorted(values["claim_sides"], key=lambda item: item.claim_ref))
        values["claim_sides"] = sides
        values["protected_claim_refs"] = tuple(item.claim_ref for item in sides)
        values["protected_evidence_refs"] = tuple(
            sorted(set(values["protected_evidence_refs"]))
        )
        left_support = set(sides[0].support_evidence_refs)
        right_support = set(sides[1].support_evidence_refs)
        values["shared_support_evidence_refs"] = tuple(
            sorted(left_support.intersection(right_support))
        )
        values["symmetric_difference_evidence_refs"] = tuple(
            sorted(left_support.symmetric_difference(right_support))
        )
        left_roots = set(sides[0].support_source_roots)
        right_roots = set(sides[1].support_source_roots)
        values["shared_support_source_roots"] = tuple(
            sorted(left_roots.intersection(right_roots))
        )
        values["symmetric_difference_source_roots"] = tuple(
            sorted(left_roots.symmetric_difference(right_roots))
        )
        values.setdefault("protocol_version", CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION)
        values.setdefault("evidence_suppression_permitted", False)
        values.setdefault("truth_selection_authority_enabled", False)
        values.setdefault("resolution_authority_enabled", False)
        values.setdefault("canonical_commit_permitted", False)
        payload = {key: value for key, value in values.items() if key != "receipt_id"}
        values["receipt_id"] = stable_id(
            "contradiction_evidence_receipt",
            {
                key: (
                    tuple(item.model_dump(mode="json") for item in value)
                    if key == "claim_sides"
                    else value
                )
                for key, value in payload.items()
            },
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "ContradictionEvidenceReceipt":
        identifiers = (
            self.obligation_id,
            self.obligation_event_ref,
            self.contradiction_ref,
            self.claim_key,
            self.attention_decision_ref,
            self.attention_bid_ref,
            self.attention_allocation_ref,
        )
        if not all(value.strip() for value in identifiers):
            raise ValueError(
                "Contradiction evidence receipt references cannot be empty."
            )
        if self.protocol_version != CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION:
            raise ValueError("Unknown contradiction evidence protocol version.")
        if not _is_sha256(self.context_snapshot_sha256):
            raise ValueError("Contradiction evidence context must be a SHA-256 digest.")
        if (
            tuple(sorted(self.claim_sides, key=lambda item: item.claim_ref))
            != self.claim_sides
        ):
            raise ValueError("Contradiction evidence sides must be claim-sorted.")
        if (
            tuple(item.claim_ref for item in self.claim_sides)
            != self.protected_claim_refs
        ):
            raise ValueError(
                "Contradiction evidence receipt suppressed an opposed claim."
            )
        if {item.polarity for item in self.claim_sides} != {
            ClaimPolarity.AFFIRMED,
            ClaimPolarity.NEGATED,
        }:
            raise ValueError(
                "Contradiction evidence receipt requires opposed polarities."
            )
        for refs, label in (
            (self.protected_claim_refs, "protected claims"),
            (self.protected_evidence_refs, "protected evidence"),
            (self.shared_support_evidence_refs, "shared support evidence"),
            (
                self.symmetric_difference_evidence_refs,
                "symmetric-difference evidence",
            ),
            (self.shared_support_source_roots, "shared support roots"),
            (self.symmetric_difference_source_roots, "symmetric-difference roots"),
        ):
            if tuple(sorted(set(refs))) != refs:
                raise ValueError(
                    f"Contradiction evidence receipt {label} must be sorted and unique."
                )
        support_sets = [set(item.support_evidence_refs) for item in self.claim_sides]
        refutation_sets = [
            set(item.refutation_evidence_refs) for item in self.claim_sides
        ]
        protected = set(self.protected_evidence_refs)
        if (
            set.union(*support_sets) != protected
            or set.union(*refutation_sets) != protected
        ):
            raise ValueError(
                "Contradiction evidence receipt suppressed canonical evidence."
            )
        if self.shared_support_evidence_refs != tuple(
            sorted(support_sets[0].intersection(support_sets[1]))
        ):
            raise ValueError("Shared contradiction evidence partition drift detected.")
        if self.symmetric_difference_evidence_refs != tuple(
            sorted(support_sets[0].symmetric_difference(support_sets[1]))
        ):
            raise ValueError(
                "Contradiction evidence symmetric difference drift detected."
            )
        root_sets = [set(item.support_source_roots) for item in self.claim_sides]
        if self.shared_support_source_roots != tuple(
            sorted(root_sets[0].intersection(root_sets[1]))
        ):
            raise ValueError("Shared contradiction source partition drift detected.")
        if self.symmetric_difference_source_roots != tuple(
            sorted(root_sets[0].symmetric_difference(root_sets[1]))
        ):
            raise ValueError(
                "Contradiction source symmetric difference drift detected."
            )
        if any(
            (
                self.evidence_suppression_permitted,
                self.truth_selection_authority_enabled,
                self.resolution_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError("Contradiction evidence receipts cannot carry authority.")
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != stable_id("contradiction_evidence_receipt", payload):
            raise ValueError("Contradiction evidence receipt checksum mismatch.")
        return self


class ContradictionHypothesis(FrozenRecord):
    """One preregistered explanation class without a preferred claim."""

    hypothesis_id: str
    protocol_version: str = CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION
    obligation_id: str
    contradiction_ref: str
    kind: ContradictionHypothesisKind
    anticipated_condition: ContradictionEvidenceCondition
    claim_refs: tuple[str, str]
    evidence_receipt_ref: str
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    candidate_discriminating_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = Field(min_length=1)
    preferred_claim_ref: str | None = None
    evidence_suppression_permitted: bool = False
    truth_selection_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "ContradictionHypothesis":
        values.setdefault("protocol_version", CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION)
        values["anticipated_condition"] = _CONDITION_BY_KIND[values["kind"]]
        for key in (
            "claim_refs",
            "protected_evidence_refs",
            "candidate_discriminating_refs",
            "provenance_refs",
        ):
            values[key] = tuple(sorted(set(values.get(key, ()))))
        values.setdefault("preferred_claim_ref", None)
        values.setdefault("evidence_suppression_permitted", False)
        values.setdefault("truth_selection_authority_enabled", False)
        values.setdefault("resolution_authority_enabled", False)
        values.setdefault("canonical_commit_permitted", False)
        payload = {
            key: value for key, value in values.items() if key != "hypothesis_id"
        }
        values["hypothesis_id"] = stable_id("contradiction_hypothesis", payload)
        return cls(**values)

    @model_validator(mode="after")
    def validate_hypothesis(self) -> "ContradictionHypothesis":
        if self.protocol_version != CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION:
            raise ValueError("Unknown contradiction hypothesis protocol version.")
        if self.anticipated_condition != _CONDITION_BY_KIND[self.kind]:
            raise ValueError(
                "Contradiction hypothesis condition does not match its kind."
            )
        for refs, label in (
            (self.claim_refs, "claim refs"),
            (self.protected_evidence_refs, "protected evidence"),
            (self.candidate_discriminating_refs, "discriminating refs"),
            (self.provenance_refs, "provenance refs"),
        ):
            if tuple(sorted(set(refs))) != refs:
                raise ValueError(
                    f"Contradiction hypothesis {label} must be sorted and unique."
                )
        if self.kind != ContradictionHypothesisKind.PROVENANCE_PARTITION_TEST and (
            self.candidate_discriminating_refs
        ):
            raise ValueError(
                "Only the provenance hypothesis may name discriminating refs."
            )
        if self.preferred_claim_ref is not None:
            raise ValueError(
                "Contradiction hypotheses cannot select a preferred claim."
            )
        if any(
            (
                self.evidence_suppression_permitted,
                self.truth_selection_authority_enabled,
                self.resolution_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError("Contradiction hypotheses cannot carry authority.")
        payload = self.model_dump(mode="json", exclude={"hypothesis_id"})
        if self.hypothesis_id != stable_id("contradiction_hypothesis", payload):
            raise ValueError("Contradiction hypothesis identity checksum mismatch.")
        return self


class ContradictionHypothesisBundle(FrozenRecord):
    """Mandatory three-way hypothesis set plus its complete evidence receipt."""

    bundle_id: str
    protocol_version: str = CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION
    obligation_id: str
    obligation_event_ref: str
    attention_decision_ref: str
    attention_bid_ref: str
    attention_allocation_ref: str
    context_snapshot_sha256: str
    evidence_receipt: ContradictionEvidenceReceipt
    hypotheses: tuple[ContradictionHypothesis, ...] = Field(
        min_length=3,
        max_length=3,
    )
    selected_hypothesis_ref: str | None = None
    truth_selection_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "ContradictionHypothesisBundle":
        values.setdefault("protocol_version", CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION)
        values["hypotheses"] = tuple(
            sorted(values["hypotheses"], key=lambda item: item.hypothesis_id)
        )
        values.setdefault("selected_hypothesis_ref", None)
        values.setdefault("truth_selection_authority_enabled", False)
        values.setdefault("resolution_authority_enabled", False)
        values.setdefault("canonical_commit_permitted", False)
        payload = {key: value for key, value in values.items() if key != "bundle_id"}
        values["bundle_id"] = stable_id(
            "contradiction_hypothesis_bundle",
            {
                key: (
                    value.model_dump(mode="json")
                    if isinstance(value, BaseModel)
                    else tuple(item.model_dump(mode="json") for item in value)
                    if key == "hypotheses"
                    else value
                )
                for key, value in payload.items()
            },
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_bundle(self) -> "ContradictionHypothesisBundle":
        if self.protocol_version != CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION:
            raise ValueError("Unknown contradiction hypothesis bundle version.")
        if not _is_sha256(self.context_snapshot_sha256):
            raise ValueError("Contradiction bundle context must be a SHA-256 digest.")
        if (
            tuple(sorted(self.hypotheses, key=lambda item: item.hypothesis_id))
            != self.hypotheses
        ):
            raise ValueError("Contradiction hypotheses must be identity-sorted.")
        if {item.kind for item in self.hypotheses} != set(ContradictionHypothesisKind):
            raise ValueError(
                "Contradiction bundle requires provenance, null, and defer arms."
            )
        receipt = self.evidence_receipt
        lineage = (
            (self.obligation_id, receipt.obligation_id),
            (self.obligation_event_ref, receipt.obligation_event_ref),
            (self.attention_decision_ref, receipt.attention_decision_ref),
            (self.attention_bid_ref, receipt.attention_bid_ref),
            (self.attention_allocation_ref, receipt.attention_allocation_ref),
            (self.context_snapshot_sha256, receipt.context_snapshot_sha256),
        )
        if any(left != right for left, right in lineage):
            raise ValueError("Contradiction bundle lost evidence-receipt lineage.")
        required_provenance = tuple(
            sorted(
                {
                    self.obligation_id,
                    self.obligation_event_ref,
                    self.attention_decision_ref,
                    self.attention_bid_ref,
                    self.attention_allocation_ref,
                    receipt.receipt_id,
                    receipt.contradiction_ref,
                    *receipt.protected_claim_refs,
                    *receipt.protected_evidence_refs,
                }
            )
        )
        for hypothesis in self.hypotheses:
            if (
                hypothesis.obligation_id != self.obligation_id
                or hypothesis.contradiction_ref != receipt.contradiction_ref
                or hypothesis.claim_refs != receipt.protected_claim_refs
                or hypothesis.evidence_receipt_ref != receipt.receipt_id
                or hypothesis.protected_evidence_refs != receipt.protected_evidence_refs
                or hypothesis.provenance_refs != required_provenance
            ):
                raise ValueError(
                    "Contradiction hypothesis suppressed bundle provenance."
                )
            expected_discriminating = (
                receipt.symmetric_difference_evidence_refs
                if hypothesis.kind
                == ContradictionHypothesisKind.PROVENANCE_PARTITION_TEST
                else ()
            )
            if hypothesis.candidate_discriminating_refs != expected_discriminating:
                raise ValueError(
                    "Contradiction hypothesis evidence partition drift detected."
                )
        if self.selected_hypothesis_ref is not None:
            raise ValueError("Contradiction bundles cannot select a hypothesis.")
        if any(
            (
                self.truth_selection_authority_enabled,
                self.resolution_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError("Contradiction hypothesis bundles cannot carry authority.")
        payload = self.model_dump(mode="json", exclude={"bundle_id"})
        if self.bundle_id != stable_id("contradiction_hypothesis_bundle", payload):
            raise ValueError("Contradiction hypothesis bundle checksum mismatch.")
        return self


class ContradictionHypothesisProtocol:
    """Generate and validate one bounded family-local hypothesis bundle."""

    ELIGIBLE_STATUSES = frozenset(
        {
            ObligationStatus.OPEN,
            ObligationStatus.INVESTIGATING,
            ObligationStatus.MAY_WAKE,
            ObligationStatus.REOPENED,
        }
    )

    def __init__(self, policy: ContradictionHypothesisPolicy | None = None) -> None:
        self.policy = policy or ContradictionHypothesisPolicy()

    @staticmethod
    def _last_event(kernel: VerdantKernel, obligation_id: str):
        events = tuple(
            item
            for item in kernel.state.obligation_history
            if item.obligation_id == obligation_id
        )
        if not events:
            raise ContradictionHypothesisIntegrityError(
                "Contradiction obligation has no canonical history."
            )
        return events[-1]

    def _attention_lineage(self, kernel: VerdantKernel, allocation_id: str):
        matches = []
        for decision in kernel.state.obligation_attention_decisions:
            for allocation in decision.allocations:
                if allocation.allocation_id == allocation_id:
                    bid = next(
                        (
                            item
                            for item in decision.bids
                            if item.bid_id == allocation.bid_id
                        ),
                        None,
                    )
                    matches.append((decision, bid, allocation))
        if len(matches) != 1 or matches[0][1] is None:
            raise ContradictionHypothesisIntegrityError(
                "Contradiction hypothesis requires one canonical Attention allocation."
            )
        decision, bid, allocation = matches[0]
        assert bid is not None
        if (
            decision.epistemic_authority_enabled
            or bid.action_operator != self.policy.action_operator
            or bid.generator_version != self.policy.protocol_version
        ):
            raise ContradictionHypothesisIntegrityError(
                "Attention allocation does not authorize this contradiction protocol."
            )
        if allocation.granted_budget + 1e-12 < self.policy.minimum_attention_budget:
            raise ContradictionHypothesisIntegrityError(
                "Attention allocation is below the contradiction protocol minimum."
            )
        return decision, bid, allocation

    @staticmethod
    def _evidence_side(kernel: VerdantKernel, claim) -> ContradictionEvidenceSide:
        ledgers = (
            (claim.support_ledger, EvidenceStance.SUPPORT, "support"),
            (claim.refutation_ledger, EvidenceStance.REFUTE, "refutation"),
        )
        refs_by_label: dict[str, tuple[str, ...]] = {}
        roots_by_label: dict[str, tuple[str, ...]] = {}
        for entries, expected_stance, label in ledgers:
            refs = tuple(item.evidence_id for item in entries)
            if not refs or len(set(refs)) != len(refs):
                raise ContradictionHypothesisIntegrityError(
                    f"Contradiction claim requires a unique nonempty {label} ledger."
                )
            if any(item.stance != expected_stance for item in entries):
                raise ContradictionHypothesisIntegrityError(
                    f"Contradiction claim {label} stance drift detected."
                )
            if any(ref not in kernel.state.evidence for ref in refs):
                raise ContradictionHypothesisIntegrityError(
                    "Contradiction claim cites missing canonical evidence."
                )
            refs_by_label[label] = tuple(sorted(refs))
            roots_by_label[label] = tuple(
                sorted({kernel.state.evidence[ref].source_ref for ref in refs})
            )
        return ContradictionEvidenceSide.build(
            claim_ref=claim.claim_id,
            polarity=claim.polarity,
            claim_snapshot_sha256=_sha256(claim.model_dump(mode="json")),
            support_evidence_refs=refs_by_label["support"],
            refutation_evidence_refs=refs_by_label["refutation"],
            support_source_roots=roots_by_label["support"],
            refutation_source_roots=roots_by_label["refutation"],
        )

    def _generate(
        self,
        kernel: VerdantKernel,
        *,
        obligation_id: str,
        attention_allocation_id: str,
    ) -> ContradictionHypothesisBundle:
        obligation = kernel.state.obligation_kernels.get(obligation_id)
        if not isinstance(obligation, ContradictionObligationKernel) or (
            obligation.family != ObligationFamily.CONTRADICTION
        ):
            raise ContradictionHypothesisIntegrityError(
                "Hypothesis protocol requires a canonical Contradiction obligation."
            )
        if (
            derive_obligation_view(kernel, obligation_id).current_status
            not in self.ELIGIBLE_STATUSES
        ):
            raise ContradictionHypothesisIntegrityError(
                "Contradiction obligation is not eligible for hypothesis attention."
            )
        event = self._last_event(kernel, obligation_id)
        decision, bid, allocation = self._attention_lineage(
            kernel,
            attention_allocation_id,
        )
        if (
            allocation.obligation_id != obligation_id
            or bid.obligation_id != obligation_id
        ):
            raise ContradictionHypothesisIntegrityError(
                "Attention allocation belongs to another obligation."
            )
        if bid.basis_event_id != event.event_id:
            raise ContradictionHypothesisIntegrityError(
                "Attention allocation is stale relative to contradiction history."
            )
        if not set(event.triggering_refs).issubset(bid.metric_provenance_refs):
            raise ContradictionHypothesisIntegrityError(
                "Attention bid suppressed current contradiction triggering evidence."
            )

        contradiction = kernel.state.contradictions.get(obligation.contradiction_ref)
        if contradiction is None or (
            contradiction.claim_key != obligation.claim_key
            or tuple(sorted(contradiction.claim_ids)) != obligation.claim_refs
        ):
            raise ContradictionHypothesisIntegrityError(
                "Contradiction obligation drifted from its native record."
            )
        claims = tuple(kernel.state.claims.get(ref) for ref in obligation.claim_refs)
        if any(item is None for item in claims):
            raise ContradictionHypothesisIntegrityError(
                "Contradiction hypothesis lost an opposed claim."
            )
        typed_claims = tuple(item for item in claims if item is not None)
        if (
            any(item.claim_key != contradiction.claim_key for item in typed_claims)
            or {item.polarity for item in typed_claims}
            != {ClaimPolarity.AFFIRMED, ClaimPolarity.NEGATED}
        ):
            raise ContradictionHypothesisIntegrityError(
                "Contradiction hypothesis requires one claim of each polarity."
            )
        protected_evidence = tuple(sorted(set(contradiction.evidence_refs)))
        if not protected_evidence or any(
            ref not in kernel.state.evidence for ref in protected_evidence
        ):
            raise ContradictionHypothesisIntegrityError(
                "Contradiction hypothesis requires complete canonical evidence."
            )
        sides = tuple(self._evidence_side(kernel, item) for item in typed_claims)
        context_payload = {
            "protocol": self.policy.model_dump(mode="json"),
            "obligation": obligation.model_dump(mode="json"),
            "obligation_event": event.model_dump(mode="json"),
            "contradiction": contradiction.model_dump(mode="json"),
            "claims": tuple(
                item.model_dump(mode="json")
                for item in sorted(typed_claims, key=lambda item: item.claim_id)
            ),
            "evidence": tuple(
                kernel.state.evidence[ref].model_dump(mode="json")
                for ref in protected_evidence
            ),
            "attention_decision": decision.model_dump(mode="json"),
            "attention_bid": bid.model_dump(mode="json"),
            "attention_allocation": allocation.model_dump(mode="json"),
        }
        context_hash = _sha256(context_payload)
        try:
            receipt = ContradictionEvidenceReceipt.build(
                obligation_id=obligation_id,
                obligation_event_ref=event.event_id,
                contradiction_ref=contradiction.contradiction_id,
                claim_key=contradiction.claim_key,
                claim_sides=sides,
                protected_evidence_refs=protected_evidence,
                attention_decision_ref=decision.decision_id,
                attention_bid_ref=bid.bid_id,
                attention_allocation_ref=allocation.allocation_id,
                authorized_budget=allocation.granted_budget,
                context_snapshot_sha256=context_hash,
            )
        except ValueError as exc:
            raise ContradictionHypothesisIntegrityError(
                "Canonical contradiction evidence is not a symmetric complete ledger."
            ) from exc

        provenance = tuple(
            sorted(
                {
                    obligation_id,
                    event.event_id,
                    decision.decision_id,
                    bid.bid_id,
                    allocation.allocation_id,
                    receipt.receipt_id,
                    contradiction.contradiction_id,
                    *receipt.protected_claim_refs,
                    *receipt.protected_evidence_refs,
                }
            )
        )
        hypotheses = tuple(
            ContradictionHypothesis.build(
                obligation_id=obligation_id,
                contradiction_ref=contradiction.contradiction_id,
                kind=kind,
                claim_refs=receipt.protected_claim_refs,
                evidence_receipt_ref=receipt.receipt_id,
                protected_evidence_refs=receipt.protected_evidence_refs,
                candidate_discriminating_refs=(
                    receipt.symmetric_difference_evidence_refs
                    if kind
                    == ContradictionHypothesisKind.PROVENANCE_PARTITION_TEST
                    else ()
                ),
                provenance_refs=provenance,
            )
            for kind in ContradictionHypothesisKind
        )
        return ContradictionHypothesisBundle.build(
            obligation_id=obligation_id,
            obligation_event_ref=event.event_id,
            attention_decision_ref=decision.decision_id,
            attention_bid_ref=bid.bid_id,
            attention_allocation_ref=allocation.allocation_id,
            context_snapshot_sha256=context_hash,
            evidence_receipt=receipt,
            hypotheses=hypotheses,
        )

    def generate(
        self,
        kernel: VerdantKernel,
        *,
        obligation_id: str,
        attention_allocation_id: str,
    ) -> ContradictionHypothesisBundle:
        fingerprint = kernel.fingerprint()
        try:
            return self._generate(
                kernel,
                obligation_id=obligation_id,
                attention_allocation_id=attention_allocation_id,
            )
        finally:
            if kernel.fingerprint() != fingerprint:
                raise RuntimeError(
                    "Contradiction hypothesis generation mutated canonical state."
                )

    def validate(
        self,
        kernel: VerdantKernel,
        bundle: ContradictionHypothesisBundle,
    ) -> ContradictionHypothesisBundle:
        expected = self.generate(
            kernel,
            obligation_id=bundle.obligation_id,
            attention_allocation_id=bundle.attention_allocation_ref,
        )
        if bundle != expected:
            raise ContradictionHypothesisIntegrityError(
                "Contradiction hypothesis bundle does not match canonical provenance."
            )
        return expected
