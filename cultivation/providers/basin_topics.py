"""Helpers for basin-targeted cultivation prompts."""

from __future__ import annotations

from typing import Any


def get_basin_domain(system_state: Any, basin_id: str) -> str:
    """Extract the dominant conceptual domain of a basin.

    Returns 2-3 concept names that best characterize the basin,
    based on the highest-access-count seeded concepts in the basin.
    """
    memory_store = getattr(getattr(system_state, "memory_web", None), "memory_store", {}) or {}
    basins = getattr(system_state, "_last_basins", []) or []

    selected: list[str] = []
    for basin in basins:
        if str(getattr(basin, "basin_id", "")) != str(basin_id):
            continue
        nodes = list(getattr(basin, "nodes", []) or [])
        scored: list[tuple[int, str]] = []
        fallback_scored: list[tuple[int, str]] = []
        for node in nodes:
            entry = memory_store.get(node, {}) if isinstance(memory_store, dict) else {}
            metadata = entry.get("metadata", {}) if isinstance(entry, dict) else {}
            access_count = int(entry.get("access_count", 0)) if isinstance(entry, dict) else 0
            name = str(node).replace("_", " ")
            fallback_scored.append((access_count, name))
            if metadata.get("origin") == "vcult_spec" or not str(node).startswith("Emergent"):
                scored.append((access_count, name))
        ranked = sorted(scored or fallback_scored, key=lambda item: (-item[0], item[1]))
        selected = [name for _, name in ranked[:3]]
        break

    if not selected:
        distribution = getattr(getattr(system_state, "get_scaffold_context", lambda: None)(), "basin_emergent_distribution", {})
        if isinstance(distribution, dict):
            selected = [str(key).replace("_", " ") for key in distribution][:3]

    if not selected:
        return "conceptual development"
    if len(selected) == 1:
        return selected[0]
    if len(selected) == 2:
        return f"{selected[0]} and {selected[1]}"
    return ", ".join(selected[:3])


def choose_basin_target(system_state: Any, basin_distribution: dict[str, int], basin_topics: Any) -> tuple[str | None, str | None]:
    """Pick a targeted basin/topic pair if a basin rule applies."""
    if not basin_distribution:
        return None, None

    counts = [count for count in basin_distribution.values()]
    mean_count = sum(counts) / max(1, len(counts))
    if mean_count <= 0:
        return None, None

    rules: list[tuple[str, Any, callable]] = []
    if getattr(basin_topics, "understimulated", None) is not None:
        rules.append(("understimulated", basin_topics.understimulated, lambda c, t: c < mean_count * t))
    if getattr(basin_topics, "dominant", None) is not None:
        rules.append(("dominant", basin_topics.dominant, lambda c, t: c > mean_count * t))

    for rule_name, rule, predicate in rules:
        candidates = [
            basin_id for basin_id, count in sorted(basin_distribution.items(), key=lambda item: (item[1], item[0]))
            if predicate(count, float(rule.threshold))
        ]
        if not candidates:
            continue
        basin_id = candidates[0] if rule_name == "understimulated" else candidates[-1]
        domain = get_basin_domain(system_state, basin_id)
        topic = rule.topics[0].format(basin_domain=domain)
        return basin_id, topic
    return None, None
