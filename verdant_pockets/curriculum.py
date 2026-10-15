"""Pre-registered, answer-independent selective composition curriculum evaluator.

Each task contains only the query. The expected result is supplied to an
external scoring ledger after the read-only composer has returned. False
positives and unlicensed rule inference are penalized; activation amplitude
and arbitrary topological link count do not earn credit.
"""
from __future__ import annotations

import hashlib
import json

from .composition import CompositionQuery, inspect_composition
from .experiment import PocketIntegrityError


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def grade_frozen_tasks(
    pocket: dict,
    tasks: tuple[dict, ...] | list[dict],
    grading_ledger: dict[str, dict],
) -> dict:
    """Grade v2 composition on precommitted distinct task IDs.

    The grading ledger is used ONLY after all composer calls have completed.
    Each expected disposition must be a specific supported or abstention
    outcome. Grades distinguish false-positive proofs from missing answers.
    """
    if not 1 <= len(tasks) <= 64:
        raise PocketIntegrityError("Frozen curriculum must contain 1..64 tasks")
    if len({t["task_id"] for t in tasks}) != len(tasks):
        raise PocketIntegrityError("Frozen curriculum task IDs must be unique")
    if set(grading_ledger) != {t["task_id"] for t in tasks}:
        raise PocketIntegrityError("Private grading ledger and task ID set differ")
    for item in grading_ledger.values():
        if item["expected"] not in ("supported_composition", "abstain"):
            raise PocketIntegrityError("Invalid external grade disposition")
    # Freeze task order before any evaluation. Grade labels are not passed to
    # the composer or pocket selector.
    outcomes = []
    for item in sorted(tasks, key=lambda t: t["task_id"]):
        q = CompositionQuery(
            item["source_concept_id"], item["target_concept_id"],
            item.get("relation_type", "precedes"),
            maximum_member_ps=item.get("maximum_member_ps", 3),
            maximum_hops=item.get("maximum_hops", 12),
            maximum_candidate_routes=item.get("maximum_candidate_routes", 32),
            maximum_search_expansions=item.get("maximum_search_expansions", 128),
        )
        result = inspect_composition(pocket, q)
        outcomes.append({
            "task_id": item["task_id"],
            "query": q.as_dict(),
            "disposition": result["disposition"],
            "proof": result["witness_native_relation_ids"],
            "selected_p_ids": result["selected_p_ids"],
            "evidence_refs": result["witness_canonical_evidence_refs"],
            "work": result["metrics"],
            "composition_report_id": result["evaluation_id"],
        })
    # No grading data was passed to inspect_composition above.
    results = []
    confusion = {"true_positive": 0, "true_negative": 0,
                 "false_positive": 0, "false_negative": 0}
    for result in outcomes:
        exp = grading_ledger[result["task_id"]]["expected"]
        predicted_positive = result["disposition"] == "supported_composition"
        expected_positive = exp == "supported_composition"
        cls = (
            "true_positive" if predicted_positive and expected_positive else
            "false_positive" if predicted_positive and not expected_positive else
            "false_negative" if not predicted_positive and expected_positive else
            "true_negative"
        )
        confusion[cls] += 1
        results.append({
            **result,
            "externally_graded_as": cls,
            "expected_positive": expected_positive,
            "actual_supported_composition": predicted_positive,
            "grade_correct": cls in ("true_positive", "true_negative"),
        })
    report = {
        "schema": "verdant.cognitive_pocket_frozen_curriculum.v2",
        "source_pocket_id": pocket["pocket_id"],
        "source_canonical_fingerprint": pocket["canonical_fingerprint"],
        "task_ids": sorted(item["task_id"] for item in tasks),
        "query_only_task_digest": _digest(sorted(tasks, key=lambda x:x["task_id"])),
        "grading_ledger_sha256": _digest(grading_ledger),
        "trials": results,
        "confusion": confusion,
        "graded_accuracy": round((confusion["true_positive"] + confusion["true_negative"]) / len(tasks), 8),
        "unsupported_claim_rate": round(confusion["false_positive"] / max(1, confusion["false_positive"] + confusion["true_negative"]), 8),
        "no_semantic_reinforcement_from_activation": True,
        "rule_was_externally_declared": True,
        "query_answer_not_supplied_to_composer": True,
        "no_native_kernel_mutation": True,
    }
    report["curriculum_id"] = _digest(report)
    return report
