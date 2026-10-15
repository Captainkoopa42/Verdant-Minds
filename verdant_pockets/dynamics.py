"""Experimental local memory interaction dynamics with paired, directional controls.

This module accepts ONLY the read-only, canonical-fingerprint-anchored P/Q
inspection from experiment.cultivate_pocket. Everything it calculates remains
hypothetical numeric activity; no canonical interpretation or writeback.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
import math

from .experiment import PocketIntegrityError


_MODES = (
    "null",
    "native_only",
    "role_aligned",
    "role_scrambled",
    "same_grammar_only",
    "canonical_only",
    "canonical_reversed",
    "combined",
)


def _digest(record: object) -> str:
    return sha256(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _grammar(p: dict) -> str | None:
    v = p.get("relation_grammar")
    return json.dumps(v, sort_keys=True, separators=(",", ":")) if v is not None else None


def _validate(pocket: dict, source_p: str, rounds: int) -> tuple[dict, dict]:
    if pocket.get("schema") != "verdant.cognitive_pocket.v0":
        raise PocketIntegrityError("Only native read-only pocket v0 reports are admissible")
    if not isinstance(rounds, int) or not 1 <= rounds <= 32:
        raise PocketIntegrityError("Must use 1..32 bounded experimental rounds")
    ps = {p["id"]: p for p in pocket["p_snapshots"]}
    if source_p not in ps or len(ps) != len(pocket["p_snapshots"]):
        raise PocketIntegrityError("Source must be a unique, actual P member of the pocket")
    concepts = {c["id"]: c for c in pocket["concepts"]}
    if len(concepts) != len(pocket["concepts"]):
        raise PocketIntegrityError("Duplicate concept in pocket")
    if not 2 <= len(ps) <= 8 or not concepts:
        raise PocketIntegrityError("Pocket must have 2..8 P sources and nodes")
    if set(pocket["p_ids"]) != set(ps) or len(pocket["p_ids"]) != len(ps):
        raise PocketIntegrityError("Pocket P identity mismatch")
    for pid, p in ps.items():
        for cid in p["members"]:
            if cid not in concepts or pid not in concepts[cid]["owner_p_ids"]:
                raise PocketIntegrityError("P concept membership missing provenance")
    for e in pocket["native_plastic_edges"]:
        a, b = e["nodes"]
        if a not in concepts or b not in concepts or a == b:
            raise PocketIntegrityError("Plastic association escaped pocket scope")
        if not 0 <= float(e["strength_at_p_promotion"]) <= 1:
            raise PocketIntegrityError("Invalid plastic association strength")
    for r in [*pocket["current_member_relations"], *pocket["evidenced_cross_p_relations"]]:
        if r["source"] not in concepts or r["target"] not in concepts or not r["evidence_refs"]:
            raise PocketIntegrityError("Relation lacks membership or evidence reference")
    return ps, concepts


def _role_edges(pocket: dict, ps: dict, *, scramble: bool, maximum_links_per_p: int, same_grammar_only: bool = False) -> list[dict]:
    if not 0 <= maximum_links_per_p <= 4:
        raise PocketIntegrityError("Role link budget per P must be 0..4")
    taken: dict[str, int] = defaultdict(int)
    collected = []
    candidates = sorted(
        pocket["hypothetical_role_alignments"],
        key=lambda x: (-float(x["topology_score"]), x["from_p"], x["to_p"]),
    )
    for row in candidates:
        a, b = row["from_p"], row["to_p"]
        if a not in ps or b not in ps or a == b:
            raise PocketIntegrityError("Role mapping has unknown source P")
        if row["status"] != "hypothetical_role_correspondence" or row["canonical_relation_asserted"] or row["semantic_equivalence_asserted"]:
            raise PocketIntegrityError("Analogical mapping tried to assert semantic truth")
        left_grammar, right_grammar = _grammar(ps[a]), _grammar(ps[b])
        if left_grammar is None or right_grammar is None:
            continue  # no typed relation basis for this transfer protocol
        cross_grammar = left_grammar != right_grammar
        if cross_grammar and same_grammar_only:
            continue
        if taken[a] >= maximum_links_per_p or taken[b] >= maximum_links_per_p:
            continue
        members_a, members_b = set(ps[a]["members"]), set(ps[b]["members"])
        mapping = [tuple(x) for x in row["mapped_roles"]]
        if (len(mapping) != len(set(mapping)) or
                len({x for x, _ in mapping}) != len(mapping) or
                len({y for _, y in mapping}) != len(mapping) or
                any(x not in members_a or y not in members_b for x, y in mapping)):
            raise PocketIntegrityError("Role mapping violates endpoint identity")
        if scramble:
            # Matched number and strength, wrong target pairing; does not
            # fabricate extra edges or gain unfair compute budget.
            mapping = sorted(mapping)
            targets = [y for _, y in mapping]
            if len(targets) >= 2:
                targets = targets[1:] + targets[:1]
            mapping = [(x, y) for (x, _), y in zip(mapping, targets)]
        collected.extend({
            "source": x,
            "target": y,
            "from_p": a,
            "to_p": b,
            "strength": round((0.08 if cross_grammar else 0.22) * float(row["topology_score"]), 8),
            "kind": "hypothetical_cross_grammar" if cross_grammar else "hypothetical_role",
            "source_grammar_differs": cross_grammar,
        } for x, y in mapping)
        taken[a] += 1
        taken[b] += 1
    return collected


def _edges(pocket: dict, ps: dict, mode: str, maximum_links_per_p: int) -> list[dict]:
    selected = []
    if mode not in _MODES:
        raise PocketIntegrityError("Unknown experimental arm")
    if mode == "null":
        return selected
    if mode in {"native_only", "role_aligned", "role_scrambled", "same_grammar_only", "combined", "canonical_only", "canonical_reversed"}:
        for edge in pocket["native_plastic_edges"]:
            a, b = edge["nodes"]
            selected.append({
                "source": a, "target": b, "strength": round(float(edge["strength_at_p_promotion"]) * 0.72, 8),
                "directed": False, "kind": "native_plastic",
            })
    if mode in {"canonical_only", "canonical_reversed", "combined"}:
        for r in pocket["evidenced_cross_p_relations"]:
            if r["status"] not in {"supported", "confirmed"}:
                raise PocketIntegrityError("Unsupported relation used as canonical cross-P bridge")
            a, b = r["source"], r["target"]
            if mode == "canonical_reversed" and r["directed"]:
                a, b = b, a
            selected.append({
                "source": a, "target": b, "strength": round(float(r["weight"]) * 0.40, 8),
                "directed": bool(r["directed"]), "kind": "evidenced_cross_p",
                "relation_id": r["id"],
            })
    if mode in {"role_aligned", "role_scrambled", "same_grammar_only", "combined"}:
        for e in _role_edges(
            pocket, ps, scramble=(mode == "role_scrambled"),
            maximum_links_per_p=maximum_links_per_p,
            same_grammar_only=(mode == "same_grammar_only"),
        ):
            selected.append({**e, "directed": False})
    return sorted(selected, key=lambda x: (x["kind"], x["source"], x["target"], x.get("relation_id", "")))


def simulate(
    pocket: dict,
    *,
    source_p_id: str,
    mode: str,
    rounds: int = 8,
    maximum_links_per_p: int = 2,
    hypothetical_weights: dict[str, float] | None = None,
) -> dict:
    """Isolated local stimulus; exact channel-accounted additive activation.

    The only supplied impulse is at the lexicographically first concept of
    source P. Other memories begin inactive. This fixes the earlier failure
    where every P was seeded and hypothetical cross-links were invisible.
    """
    ps, concepts = _validate(pocket, source_p_id, rounds)
    edges = _edges(pocket, ps, mode, maximum_links_per_p)
    if hypothetical_weights is not None:
        link_keys = {
            f"{e['source']}|{e['target']}": e for e in edges
            if e["kind"].startswith("hypothetical_")
        }
        if not set(hypothetical_weights).issubset(link_keys):
            raise PocketIntegrityError("Unknown/forged local plasticity link identity")
        for k, weight in hypothetical_weights.items():
            if not isinstance(weight, (int, float)) or not math.isfinite(weight) or not 0 <= weight <= 0.40:
                raise PocketIntegrityError("Local plasticity weights must be finite in [0, 0.40]")
            link_keys[k]["strength"] = round(float(weight), 8)
    nodes = sorted(concepts)
    seed = min(ps[source_p_id]["members"])
    activated = {cid: (1.0 if cid == seed and mode != "null" else 0.0) for cid in nodes}
    traces = [{
        "round": 0, "activation": activated.copy(),
        "transfer_attempts": [], "total_activation": sum(activated.values()),
        "active_non_source_p": 0,
    }]
    source_members = set(ps[source_p_id]["members"])
    for tick in range(1, rounds + 1):
        next_value = {cid: activated[cid] * 0.55 for cid in nodes}
        transfers = []
        channel_inputs: dict[str, float] = defaultdict(float)
        for e in edges:
            directions = [(e["source"], e["target"])]
            if not e["directed"]:
                directions.append((e["target"], e["source"]))
            for src, dst in directions:
                amount = activated[src] * e["strength"]
                if amount <= 1e-12:
                    continue
                next_value[dst] += amount
                channel_inputs[e["kind"]] += amount
                transfers.append({
                    "source": src, "target": dst,
                    "source_p_ids": concepts[src]["owner_p_ids"],
                    "target_p_ids": concepts[dst]["owner_p_ids"],
                    "channel": e["kind"], "amount": round(amount, 9),
                    "canonical_evidence_asserted": e["kind"] == "evidenced_cross_p",
                    "relation_id": e.get("relation_id"),
                })
        activated = {cid: round(min(1.0, next_value[cid]), 9) for cid in nodes}
        outside = sum(1 for cid in nodes if cid not in source_members and activated[cid] > 1e-8)
        traces.append({
            "round": tick,
            "activation": activated.copy(),
            "transfer_attempts": transfers,
            "total_activation": round(sum(activated.values()), 9),
            "active_non_source_p": outside,
            "input_by_channel": {k: round(v, 9) for k, v in sorted(channel_inputs.items())},
        })
    return {
        "schema": "verdant.cognitive_pocket_trial.v1",
        "source_p_id": source_p_id,
        "seed_concept_id": seed,
        "arm": mode,
        "rounds": rounds,
        "links": edges,
        "frames": traces,
        "final_non_source_active": traces[-1]["active_non_source_p"],
        "source_pocket_id": pocket["pocket_id"],
        "scope_fingerprint": pocket["canonical_fingerprint"],
        "interpretation": "simulated_numeric_activity_only",
    }


def paired_cohort(
    pocket: dict, *, rounds: int = 8, maximum_links_per_p: int = 2,
    sources: tuple[str, ...] | None = None,
) -> dict:
    """Matched arms, identical sources and budgets; measures exact deltas."""
    selected = tuple(sorted(sources if sources is not None else pocket["p_ids"]))
    if not selected or len(selected) != len(set(selected)):
        raise PocketIntegrityError("Invalid source cohort")
    trials = []
    effects = []
    for sid in selected:
        arm_trials = {
            arm: simulate(pocket, source_p_id=sid, mode=arm, rounds=rounds,
                          maximum_links_per_p=maximum_links_per_p)
            for arm in _MODES
        }
        baseline = arm_trials["native_only"]
        for arm, trial in arm_trials.items():
            if arm == "null":
                continue
            deltas = [
                round(sum(abs(trial["frames"][i]["activation"][cid] -
                              baseline["frames"][i]["activation"][cid])
                          for cid in baseline["frames"][i]["activation"]), 9)
                for i in range(1, rounds + 1)
            ]
            effects.append({
                "source_p_id": sid,
                "arm": arm,
                "per_round_l1_delta_from_native": deltas,
                "measurable_effect": any(x > 1e-8 for x in deltas),
                "final_non_source_active": trial["final_non_source_active"],
                "is_evidenced_compositional_gain": False,
            })
            trials.append(trial)
        trials.append(arm_trials["null"])
    out = {
        "schema": "verdant.cognitive_pocket_matched_cohort.v1",
        "source_pocket_id": pocket["pocket_id"],
        "scope_fingerprint": pocket["canonical_fingerprint"],
        "source_p_ids": list(selected),
        "rounds": rounds,
        "arms": list(_MODES),
        "trials": trials,
        "effects": effects,
        "controls": {
            "all_source_p_seeds_local_only": True,
            "matched_budget_and_initial_source_per_arm": True,
            "wrong_role_scrambling_preserves_pair_count": True,
            "null_impulse": True,
            "reverse_canonical_direction": True,
            "no_canonical_writeback": True,
            "measurable_activation_is_not_semantic_composition": True,
        },
    }
    out["cohort_id"] = _digest(out)
    return out
