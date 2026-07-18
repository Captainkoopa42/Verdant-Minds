"""Post-cultivation validation helpers for VCult runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analysis.extract_emergent_concepts import extract_emergent_concepts
from analysis.semantic_evaluation import evaluate_semantics


def compute_earlier_share_from_state_payload(state: dict[str, Any]) -> float:
    """Compute emergent earlier-share from a saved state payload."""
    memory = state.get("memory_web", {}) if isinstance(state, dict) else {}
    nodes = memory.get("memory_store", {}) if isinstance(memory, dict) else {}
    if not isinstance(nodes, dict):
        return 1.0

    total = 0
    earlier = 0
    for label, entry in nodes.items():
        if not (isinstance(label, str) and label.startswith("Emergent_")):
            continue
        if not isinstance(entry, dict):
            continue
        metadata = entry.get("metadata", {}) if isinstance(entry.get("metadata"), dict) else {}
        parents = metadata.get("parent_concepts", [])
        if not isinstance(parents, list) or not parents:
            continue
        creation_time = float(metadata.get("creation_time", entry.get("first_seen", 0.0)))
        parent_times: list[float] = []
        for parent in parents:
            parent_entry = nodes.get(parent)
            if not isinstance(parent_entry, dict):
                continue
            parent_metadata = parent_entry.get("metadata", {}) if isinstance(parent_entry.get("metadata"), dict) else {}
            parent_times.append(float(parent_metadata.get("creation_time", parent_entry.get("first_seen", 0.0))))
        if parent_times:
            total += 1
            if creation_time >= max(parent_times):
                earlier += 1
    return earlier / max(1, total)


def compute_earlier_share_from_state_path(path: Path) -> float:
    """Load a state file and compute earlier-share."""
    return compute_earlier_share_from_state_payload(json.loads(path.read_text(encoding="utf-8")))


def run_validation_checks(
    *,
    state_path: Path,
    expectations: dict[str, Any],
    actual_metrics: dict[str, float | int],
) -> dict[str, Any]:
    """Run validation checks and return a serializable result payload."""
    checks: dict[str, Any] = {}

    earlier_share = float(actual_metrics["earlier_share"])
    emergent_count = int(actual_metrics["emergent_count"])
    basin_count = int(actual_metrics["basin_count"])

    if "expect_earlier_share" in expectations:
        expected = float(expectations["expect_earlier_share"])
        checks["expect_earlier_share"] = {"expected": expected, "actual": earlier_share, "passed": earlier_share >= expected}

    if "expect_min_emergents" in expectations:
        expected = int(expectations["expect_min_emergents"])
        checks["expect_min_emergents"] = {"expected": expected, "actual": emergent_count, "passed": emergent_count >= expected}

    if "expect_min_basins" in expectations:
        expected = int(expectations["expect_min_basins"])
        checks["expect_min_basins"] = {"expected": expected, "actual": basin_count, "passed": basin_count >= expected}

    semantic_result = None
    semantic_score = None
    if "expect_min_semantic_score" in expectations:
        concepts_payload = extract_emergent_concepts(state_path)
        semantic_result = evaluate_semantics(concepts_payload, mode="local")
        semantic_score = float(semantic_result.get("scores", {}).get("mean_score", 0.0))
        expected = float(expectations["expect_min_semantic_score"])
        checks["expect_min_semantic_score"] = {
            "expected": expected,
            "actual": semantic_score,
            "passed": semantic_score >= expected,
        }

    return {
        "state_path": str(state_path),
        "actual_metrics": {
            "earlier_share": earlier_share,
            "emergent_count": emergent_count,
            "basin_count": basin_count,
            **({"semantic_score": semantic_score} if semantic_score is not None else {}),
        },
        "checks": checks,
        "all_passed": all(bool(item.get("passed", False)) for item in checks.values()) if checks else True,
        **({"semantic_evaluation": semantic_result} if semantic_result is not None else {}),
    }
