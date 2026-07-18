"""Detect self-referential emergent concepts in a completed Verdant run."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.extract_emergent_concepts import extract_emergent_concepts
from analysis.telemetry_analysis_common import load_cycles, write_json
from analysis.state_adapter import VerdantState

SELF_TERMS = {
    "basin",
    "emergent",
    "dormant",
    "growth",
    "cycle",
    "t_g",
    "boundary",
    "consolidation",
    "flexibility",
    "active",
    "rest",
    "consolidation",
}


def _tokenize(text: str) -> set[str]:
    lowered = text.lower().replace("-", "_")
    return {token.strip("_.,:;!?()[]{}\"'") for token in lowered.split() if token.strip("_.,:;!?()[]{}\"'")}


def _reflection_cycles(rows: list[dict[str, Any]]) -> list[int]:
    return [int(row.get("cycle_index", 0)) for row in rows if bool(row.get("is_self_reflection", False))]


def _resolve_path(spec: str) -> Path:
    if "*" not in spec:
        return Path(spec)
    matches = sorted(Path().glob(spec))
    if not matches:
        raise FileNotFoundError(f"No path matches: {spec}")
    return matches[-1]


def _creation_order(vs: VerdantState) -> list[dict[str, Any]]:
    concepts = []
    for node in vs.emergent_nodes:
        concepts.append(
            {
                "name": str(node["name"]),
                "creation_time": node.get("creation_time"),
                "metadata": node.get("metadata", {}),
            }
        )
    concepts.sort(key=lambda item: ((item["creation_time"] is None), item["creation_time"], item["name"]))
    return concepts


def _estimate_concept_cycles(vs: VerdantState, rows: list[dict[str, Any]]) -> dict[str, int]:
    ordered = _creation_order(vs)
    total_cycles = max((int(row.get("cycle_index", 0)) for row in rows), default=-1) + 1
    if not ordered or total_cycles <= 0:
        return {}
    estimate: dict[str, int] = {}
    for idx, item in enumerate(ordered):
        cycle_estimate = min(total_cycles - 1, math.floor((idx / max(1, len(ordered))) * total_cycles))
        metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
        explicit_cycle = metadata.get("creation_cycle")
        if isinstance(explicit_cycle, int):
            cycle_estimate = explicit_cycle
        estimate[str(item["name"])] = int(cycle_estimate)
    return estimate


def detect_self_referential_concepts(state_path: Path, cycles_jsonl: Path) -> dict[str, Any]:
    rows = load_cycles(cycles_jsonl)
    concepts_payload = extract_emergent_concepts(state_path, basins_path=state_path.parent / "basins.json")
    vs = VerdantState.load(state_path)
    reflection_cycles = _reflection_cycles(rows)
    concept_cycle_estimates = _estimate_concept_cycles(vs, rows)
    reflection_set = set(reflection_cycles)
    temporal_window = {cycle + delta for cycle in reflection_cycles for delta in (-2, -1, 0, 1, 2)}

    reflection_cycle_inputs = {
        int(row.get("cycle_index", 0)): str(row.get("self_reflection_input") or row.get("input_text") or "")
        for row in rows
        if bool(row.get("is_self_reflection", False))
    }
    reflection_vocab = set().union(*(_tokenize(text) for text in reflection_cycle_inputs.values())) if reflection_cycle_inputs else set()

    concept_by_name = {str(item["name"]): item for item in concepts_payload.get("concepts", [])}
    self_referential: list[dict[str, Any]] = []
    basin_counter: Counter[str] = Counter()

    for concept in concepts_payload.get("concepts", []):
        name = str(concept.get("name", ""))
        lower_name = name.lower()
        structural_name = lower_name.removeprefix("emergent_")
        tokens = _tokenize(structural_name)
        parents = [str(parent) for parent in concept.get("parents", [])]
        est_cycle = concept_cycle_estimates.get(name)
        nearest_reflection = None
        if reflection_cycles and est_cycle is not None:
            nearest_reflection = min(reflection_cycles, key=lambda cycle: abs(cycle - est_cycle))
        basin_id = str(concept.get("basin_id") or "")

        methods: list[str] = []
        if any(
            term in structural_name
            or any(token == term or token.startswith(f"{term}_") or token.endswith(f"_{term}") for token in tokens)
            for term in SELF_TERMS
        ):
            methods.append("naming")
        if any(parent in concept_cycle_estimates and concept_cycle_estimates[parent] in temporal_window for parent in parents):
            methods.append("parent")
        if est_cycle is not None and est_cycle in temporal_window:
            methods.append("temporal")
        if basin_id and reflection_vocab and len(tokens & reflection_vocab & SELF_TERMS) >= 1:
            methods.append("basin")

        if not methods:
            continue

        if basin_id:
            basin_counter[basin_id] += 1
        self_referential.append(
            {
                "name": name,
                "parents": parents,
                "creation_time": concept.get("creation_time"),
                "nearest_reflection_cycle": nearest_reflection,
                "detection_method": "|".join(sorted(set(methods))),
                "basin_id": concept.get("basin_id"),
            }
        )

    total_emergent = int(concepts_payload.get("total_emergent", 0))
    self_count = len(self_referential)
    self_fraction = (self_count / total_emergent) if total_emergent else 0.0

    self_model_basin = None
    self_model_basin_size = 0
    if basin_counter:
        candidate_basin, candidate_count = basin_counter.most_common(1)[0]
        if candidate_count >= max(2, math.ceil(self_count * 0.4)):
            self_model_basin = candidate_basin
            self_model_basin_size = candidate_count

    reflection_series = [1.0 if int(row.get("cycle_index", 0)) in reflection_set else 0.0 for row in rows]
    creation_series = [0.0 for _ in rows]
    for concept_name, cycle_est in concept_cycle_estimates.items():
        if concept_name in {item["name"] for item in self_referential} and 0 <= cycle_est < len(creation_series):
            creation_series[cycle_est] += 1.0

    def _corr(xs: list[float], ys: list[float]) -> float:
        if len(xs) != len(ys) or len(xs) < 2:
            return 0.0
        mean_x = sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
        den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
        if den_x == 0 or den_y == 0:
            return 0.0
        return num / (den_x * den_y)

    temporal_correlation = _corr(reflection_series, creation_series)

    self_set = {item["name"] for item in self_referential}
    earlier_self = 0
    total_self_parent_links = 0
    earlier_cross = 0
    total_cross_parent_links = 0
    for concept in concepts_payload.get("concepts", []):
        name = str(concept.get("name", ""))
        creation_time = concept.get("creation_time")
        if creation_time is None:
            continue
        for parent in concept.get("parents", []):
            parent_concept = concept_by_name.get(str(parent))
            if parent_concept is None:
                continue
            parent_time = parent_concept.get("creation_time")
            if parent_time is None:
                continue
            if name in self_set and str(parent) in self_set:
                total_self_parent_links += 1
                earlier_self += int(float(parent_time) <= float(creation_time))
            elif (name in self_set) ^ (str(parent) in self_set):
                total_cross_parent_links += 1
                earlier_cross += int(float(parent_time) <= float(creation_time))

    return {
        "total_emergent": total_emergent,
        "self_referential_count": self_count,
        "self_referential_fraction": self_fraction,
        "self_referential_concepts": self_referential,
        "self_model_basin": self_model_basin,
        "self_model_basin_size": self_model_basin_size,
        "temporal_correlation": temporal_correlation,
        "earlier_share_self_concepts": (earlier_self / total_self_parent_links) if total_self_parent_links else 1.0,
        "earlier_share_cross": (earlier_cross / total_cross_parent_links) if total_cross_parent_links else 1.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect self-referential emergent concepts from a Verdant run")
    parser.add_argument("--state", required=True)
    parser.add_argument("--cycles-jsonl", required=True)
    parser.add_argument("--outfile", required=True)
    args = parser.parse_args()

    payload = detect_self_referential_concepts(_resolve_path(args.state), _resolve_path(args.cycles_jsonl))
    write_json(Path(args.outfile), payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
