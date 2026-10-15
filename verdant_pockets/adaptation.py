"""Isolated local pocket plasticity across sequential bounded episodes.

Not a learned ontology: these are local Hebbian-style numeric weight updates in
private sidecar state, with frozen-weight matched evaluation on held-out stimuli.
No canonical relations, P/Q, obligations, or parent checkpoint are mutated.
"""
from __future__ import annotations

import hashlib
import json

from .experiment import PocketIntegrityError
from .dynamics import simulate


def _hash(record: object) -> str:
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def local_cultivation(
    pocket: dict,
    *,
    epochs: int = 3,
    rounds: int = 6,
    rate: float = 0.04,
    maximum_links_per_p: int = 2,
) -> dict:
    if not 1 <= epochs <= 8 or not 1 <= rounds <= 16:
        raise PocketIntegrityError("Local development exceeds bounded epochs or rounds")
    if not 0 <= rate <= 0.12:
        raise PocketIntegrityError("Invalid local development rate")

    sources = tuple(sorted(pocket["p_ids"]))
    if len(sources) < 2:
        raise PocketIntegrityError("Local development needs at least two native Ps")
    # Held-out means held-out STIMULUS presentations, not an independent
    # real-world outcome, ground truth, semantic transfer or new experience.
    train = sources[:-1]
    holdout = sources[-1]
    ref = simulate(
        pocket, source_p_id=train[0], mode="role_aligned",
        rounds=1, maximum_links_per_p=maximum_links_per_p,
    )
    initial = {
        f"{link['source']}|{link['target']}": link["strength"]
        for link in ref["links"] if link["kind"].startswith("hypothetical_")
    }
    if not initial:
        return {
            "schema": "verdant.cognitive_pocket_local_plasticity.v1",
            "source_pocket_id": pocket["pocket_id"],
            "training_source_p_ids": list(train),
            "held_out_source_p_id": holdout,
            "epochs": epochs,
            "local_rounds_per_session": rounds,
            "rate": rate,
            "maximum_links_per_p": maximum_links_per_p,
            "events": [],
            "initial_weights": {},
            "final_weights": {},
            "held_out": None,
            "status": "insufficient_grounded_candidate_roles",
            "no_canonical_learning": True,
        }

    weights = dict(initial)
    history = []
    prev = pocket["pocket_id"]
    for epoch in range(1, epochs + 1):
        for source in train:
            trial = simulate(
                pocket, source_p_id=source, mode="role_aligned",
                rounds=rounds, maximum_links_per_p=maximum_links_per_p,
                hypothetical_weights=weights,
            )
            # Paired coactivation of the same observed local nodes, not
            # reward from an external assessor. No semantic score is used.
            for link in trial["links"]:
                if not link["kind"].startswith("hypothetical_"):
                    continue
                key = f"{link['source']}|{link['target']}"
                if key not in weights:
                    continue
                correlations = [
                    frame["activation"][link["source"]] *
                    frame["activation"][link["target"]]
                    for frame in trial["frames"][1:]
                ]
                mean_coactivation = sum(correlations) / len(correlations)
                new_weight = weights[key] * 0.995 + rate * mean_coactivation * (0.40 - weights[key])
                weights[key] = round(min(0.40, max(0.0, new_weight)), 8)
            event = {
                "sequence": len(history),
                "prev_hash": prev,
                "epoch": epoch,
                "source_p_id": source,
                "activity_trace_sha256": _hash(trial["frames"]),
                "local_weights_sha256": _hash(weights),
                "no_semantic_writeback": True,
            }
            event["record_hash"] = _hash(event)
            prev = event["record_hash"]
            history.append(event)

    frozen_trial = simulate(
        pocket, source_p_id=holdout, mode="role_aligned", rounds=rounds,
        maximum_links_per_p=maximum_links_per_p,
        hypothetical_weights=initial,
    )
    adapted_trial = simulate(
        pocket, source_p_id=holdout, mode="role_aligned", rounds=rounds,
        maximum_links_per_p=maximum_links_per_p,
        hypothetical_weights=weights,
    )
    per_round_differences = [
        round(sum(abs(frozen_trial["frames"][i]["activation"][cid] -
                      adapted_trial["frames"][i]["activation"][cid])
                  for cid in frozen_trial["frames"][i]["activation"]), 9)
        for i in range(1, rounds + 1)
    ]
    result = {
        "schema": "verdant.cognitive_pocket_local_plasticity.v1",
        "source_pocket_id": pocket["pocket_id"],
        "training_source_p_ids": list(train),
        "held_out_source_p_id": holdout,
        "epochs": epochs,
        "local_rounds_per_session": rounds,
        "rate": rate,
        "maximum_links_per_p": maximum_links_per_p,
        "events": history,
        "head_hash": prev,
        "initial_weights": initial,
        "final_weights": weights,
        "held_out": {
            "frozen_trace_sha256": _hash(frozen_trial["frames"]),
            "adapted_trace_sha256": _hash(adapted_trial["frames"]),
            "per_round_l1_delta": per_round_differences,
            "measurable_local_plasticity_effect": any(v > 1e-8 for v in per_round_differences),
            "external_ground_truth_not_available": True,
            "semantic_transfer_demonstrated": False,
        },
        "status": "simulated_local_numeric_plasticity_only",
        "no_canonical_learning": True,
    }
    result["experiment_id"] = _hash(result)
    return result
