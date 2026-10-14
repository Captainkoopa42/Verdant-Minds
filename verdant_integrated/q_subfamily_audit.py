"""Read-only, evidence-grounded native P/Q grouping audit for older checkpoints.

Example:
    python -m verdant_integrated.q_subfamily_audit PATH_TO_003.vdk

Does NOT modify the old source-frozen study, commit Q candidates or promote P/Q.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean

from verdant_hierarchy import VerdantHierarchyPipeline
from verdant_kernel import VerdantKernel, load_checkpoint


def audit_checkpoint(path: str | Path) -> dict:
    path = Path(path)
    raw = path.read_bytes()
    kernel = VerdantKernel.from_state(load_checkpoint(path))
    fingerprint = kernel.fingerprint()
    hierarchy = VerdantHierarchyPipeline()
    adjacency, scores, _, field_only = hierarchy._verified_graph(kernel)
    policy = kernel.state.hierarchy_policy
    components = hierarchy._components(adjacency)
    report = []
    for component in components:
        members = set(component)
        links = {
            pair: max(vals)
            for pair, vals in scores.items()
            if vals and pair[0] in members and pair[1] in members
        }
        bounded = hierarchy._bounded_subfamilies(
            component, adjacency, scores,
            minimum_members=policy.minimum_members,
            maximum_members=policy.maximum_members,
        )
        proposed = [
            dict(
                count=len(group),
                p_ids=list(group),
                cross_verified_edges=sum(
                    (a in group) != (b in group)
                    for a, b in scores
                ),
            )
            for group in bounded
        ]
        report.append(dict(
            member_count=len(component),
            verified_pair_count=len(links),
            possible_pairs=len(component) * (len(component) - 1) // 2,
            symbolic_min=min(links.values(), default=None),
            symbolic_mean=mean(links.values()) if links else None,
            symbolic_max=max(links.values(), default=None),
            p_ids=list(component),
            bounded_subfamilies=proposed,
            blocked_oversize_no_supported_split=(
                len(component) > policy.maximum_members and not bounded
            ),
        ))
    if kernel.fingerprint() != fingerprint:
        raise RuntimeError("Read-only Q audit modified canonical native state")
    return dict(
        checkpoint_sha256=hashlib.sha256(raw).hexdigest(),
        native_fingerprint=fingerprint,
        native_cycles=kernel.state.cycle,
        experiences=len(kernel.state.processed_event_keys),
        promoted_p=len(kernel.state.structures),
        promoted_q=len(kernel.state.layered_structures),
        verified_interaction_events=len(kernel.state.structure_interaction_events),
        field_only_interaction_candidates=len(field_only),
        native_min_q_members=policy.minimum_members,
        native_max_q_members=policy.maximum_members,
        oversize_subgroup_policy="mutual-nearbest-margin-v0.1",
        component_reports=report,
        diagnostic_only=True,
        no_native_mutation=True,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", help="Existing native .vdk checkpoint file")
    args = parser.parse_args(argv)
    print(json.dumps(audit_checkpoint(args.checkpoint), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
