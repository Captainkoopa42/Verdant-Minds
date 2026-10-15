"""Read-only bridge from pocket native relations to Obligation Substrate.

No obligation is recorded, scheduled, resolved, or manufactured from a
topology/role analogy. Uses native DependencyGapDetector.inspect exactly.
"""
from __future__ import annotations

from verdant_kernel import VerdantKernel
from verdant_obligations.detection import DependencyGapDetector

from .experiment import PocketIntegrityError


def inspect_obligation_handoff(kernel: VerdantKernel, pocket: dict) -> dict:
    """Select actual native dependency findings whose relation is in pocket scope."""
    original = kernel.fingerprint()
    if original != pocket.get("canonical_fingerprint"):
        raise PocketIntegrityError("Obligation handoff source fingerprint does not match P pocket")
    members = {c["id"] for c in pocket["concepts"]}
    if not members:
        raise PocketIntegrityError("Pocket has no concepts")
    # This is the actual canonical detector. A typed R/S grammar alone is NOT
    # a dependency, and a simulated role edge cannot enter the detector.
    detector = DependencyGapDetector()
    inspected, candidates = detector.inspect(kernel)
    scoped = set()
    for r in kernel.state.relations.values():
        if r.source_concept_id in members and r.target_concept_id in members:
            scoped.add(r.relation_id)
    eligible = [
        {
            "candidate_id": c.candidate_id,
            "canonical_relation_id": c.relation_id,
            "trigger_relation": c.trigger_relation,
            "canonical_triggering_refs": list(c.canonical_triggering_refs),
            "scope_key": c.scope_key,
            "context_snapshot_hash": c.context_snapshot_hash,
            "policy_version": c.policy_version,
            "status": "candidate_only_not_recorded",
        }
        for c in candidates if c.relation_id in scoped
    ]
    if kernel.fingerprint() != original:
        raise PocketIntegrityError("Obligation detector modified canonical state")
    return {
        "schema": "verdant.cognitive_pocket_obligation_handoff.v1",
        "source_pocket_id": pocket["pocket_id"],
        "canonical_fingerprint": original,
        "detector_policy_version": detector.policy.policy_version,
        "inspected_canonical_dependency_relations_in_scope": sorted(set(inspected) & scoped),
        "candidate_obligations": eligible,
        "no_mutation": True,
        "no_automatic_invocation": True,
        "no_hypothetical_role_laundering": True,
    }
