"""Persistent basin identity registry across community-detection refreshes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import time
from typing import Any

from verdant_v2.memory.basins import BasinInfo
from verdant_v2.memory.graph import MemoryWeb


@dataclass
class RegistryEvent:
    """Lifecycle event recorded by the basin registry."""

    cycle: int
    event_type: str
    basin_id: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegisteredBasin:
    """Persistent identity for a basin across detection cycles."""

    basin_id: str
    core_members: set[str]
    current_members: set[str]
    status: str
    created_cycle: int
    last_active_cycle: int
    parent_id: str | None
    emergent_count_peak: int
    emergent_count_current: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the basin into JSON-compatible primitives."""
        data = asdict(self)
        data["core_members"] = sorted(self.core_members)
        data["current_members"] = sorted(self.current_members)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegisteredBasin":
        """Restore a serialized basin record."""
        return cls(
            basin_id=str(data["basin_id"]),
            core_members={str(node) for node in data.get("core_members", [])},
            current_members={str(node) for node in data.get("current_members", [])},
            status=str(data.get("status", "active")),
            created_cycle=int(data.get("created_cycle", 0)),
            last_active_cycle=int(data.get("last_active_cycle", 0)),
            parent_id=(str(data["parent_id"]) if data.get("parent_id") is not None else None),
            emergent_count_peak=int(data.get("emergent_count_peak", 0)),
            emergent_count_current=int(data.get("emergent_count_current", 0)),
            metadata=dict(data.get("metadata", {})),
        )


class BasinRegistry:
    """Persistent registry of basin identities across detection cycles.

    Basin identity is anchored to core membership rather than to a single
    community-detection pass.
    """

    def __init__(
        self,
        *,
        daughter_protection_cycles: int = 30,
        core_stability_cycles: int = 10,
        core_absence_tolerance: int = 3,
    ) -> None:
        self._basins: dict[str, RegisteredBasin] = {}
        self._next_id: int = 0
        self._history: list[RegistryEvent] = []
        self._last_cycle_events: list[RegistryEvent] = []
        self.daughter_protection_cycles = daughter_protection_cycles
        self.core_stability_cycles = core_stability_cycles
        self.core_absence_tolerance = core_absence_tolerance

    def update_from_detection(
        self,
        detected_communities: list[set[str]],
        cycle: int,
        *,
        core_overlap_threshold: float = 0.5,
        memory_web: MemoryWeb | None = None,
    ) -> list[BasinInfo]:
        """Match detected communities to registered basins and return active basin views."""
        normalized = [set(map(str, community)) for community in detected_communities if community]
        self._last_cycle_events = []

        basin_matches: dict[str, set[str]] = {}
        protected_community_claims: set[int] = set()
        community_claimed: set[int] = set()

        protected_ids = [
            basin.basin_id
            for basin in self._basins.values()
            if self._is_protected(basin, cycle)
        ]
        for basin_id in protected_ids:
            basin = self._basins[basin_id]
            best_idx, best_overlap = self._best_community_for_basin(basin, normalized)
            if best_idx is None or best_overlap < core_overlap_threshold:
                continue
            basin_matches[basin_id] = normalized[best_idx]
            protected_community_claims.add(best_idx)

        candidates: list[tuple[float, str, int]] = []
        for basin in self._basins.values():
            if basin.basin_id in basin_matches:
                continue
            best_idx, best_overlap = self._best_community_for_basin(basin, normalized)
            if best_idx is None or best_overlap < core_overlap_threshold:
                continue
            candidates.append((best_overlap, basin.basin_id, best_idx))
        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))

        assigned_basins: set[str] = set(basin_matches)
        for _, basin_id, community_idx in candidates:
            if basin_id in assigned_basins or community_idx in community_claimed:
                continue
            basin_matches[basin_id] = normalized[community_idx]
            assigned_basins.add(basin_id)
            community_claimed.add(community_idx)

        for idx, community in enumerate(normalized):
            if idx in community_claimed or idx in protected_community_claims:
                continue
            basin = self._register_new_basin(community, cycle=cycle)
            basin_matches[basin.basin_id] = community
            community_claimed.add(idx)

        active_ids = set(basin_matches)
        for basin_id, basin in self._basins.items():
            community = basin_matches.get(basin_id)
            if community is None:
                if basin.status == "active":
                    basin.status = "dormant"
                    self._record_event(cycle, "dormant", basin_id, {"core_size": len(basin.core_members)})
                self._update_core_tracking(basin, set(), cycle)
                continue

            was_dormant = basin.status == "dormant"
            basin.status = "active"
            basin.last_active_cycle = cycle
            basin.current_members = set(community)
            basin.emergent_count_current = self._count_emergents(community)
            basin.emergent_count_peak = max(basin.emergent_count_peak, basin.emergent_count_current)
            self._update_core_tracking(basin, community, cycle)
            event_type = "reactivated" if was_dormant else "updated"
            self._record_event(
                cycle,
                event_type,
                basin_id,
                {
                    "members": len(community),
                    "core_members": len(basin.core_members),
                    "protected": self._is_protected(basin, cycle),
                },
            )

        active_basins = [self._basins[basin_id] for basin_id in active_ids if self._basins[basin_id].status == "active"]
        basin_infos = [self._make_basin_info(basin, memory_web=memory_web) for basin in active_basins]
        basin_infos.sort(key=lambda basin: (-basin.size, basin.basin_id))
        return basin_infos

    def register_budded_basin(
        self,
        members: set[str] | list[str],
        *,
        cycle: int,
        parent_id: str | None,
        basin_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RegisteredBasin:
        """Register a newly budded daughter basin with temporary protection."""
        member_set = {str(node) for node in members}
        basin = self._register_new_basin(
            member_set,
            cycle=cycle,
            basin_id=basin_id,
            parent_id=parent_id,
            metadata=metadata,
        )
        basin.metadata["protected_until_cycle"] = cycle + self.daughter_protection_cycles
        self._record_event(
            cycle,
            "budded",
            basin.basin_id,
            {
                "parent_id": parent_id,
                "members": len(member_set),
                "protected_until_cycle": basin.metadata["protected_until_cycle"],
            },
        )
        return basin

    def get_basin(self, basin_id: str) -> RegisteredBasin | None:
        """Return a registered basin if present."""
        return self._basins.get(basin_id)

    def get_active_basins(self) -> list[RegisteredBasin]:
        """Return currently active basin identities."""
        return sorted(
            [basin for basin in self._basins.values() if basin.status == "active"],
            key=lambda basin: (-len(basin.current_members), basin.basin_id),
        )

    def get_dormant_basins(self) -> list[RegisteredBasin]:
        """Return dormant basin identities."""
        return sorted(
            [basin for basin in self._basins.values() if basin.status == "dormant"],
            key=lambda basin: (basin.last_active_cycle, basin.basin_id),
        )

    def get_history(self) -> list[RegistryEvent]:
        """Return a copy of the registry event history."""
        return list(self._history)

    def get_last_cycle_events(self) -> list[RegistryEvent]:
        """Return the events recorded during the latest update call."""
        return list(self._last_cycle_events)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full registry state."""
        return {
            "basins": {basin_id: basin.to_dict() for basin_id, basin in self._basins.items()},
            "next_id": self._next_id,
            "history": [asdict(event) for event in self._history],
            "daughter_protection_cycles": self.daughter_protection_cycles,
            "core_stability_cycles": self.core_stability_cycles,
            "core_absence_tolerance": self.core_absence_tolerance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BasinRegistry":
        """Restore a registry from serialized state."""
        registry = cls(
            daughter_protection_cycles=int(data.get("daughter_protection_cycles", 30)),
            core_stability_cycles=int(data.get("core_stability_cycles", 10)),
            core_absence_tolerance=int(data.get("core_absence_tolerance", 3)),
        )
        registry._next_id = int(data.get("next_id", 0))
        registry._basins = {
            str(basin_id): RegisteredBasin.from_dict(basin_data)
            for basin_id, basin_data in dict(data.get("basins", {})).items()
            if isinstance(basin_data, dict)
        }
        registry._history = [
            RegistryEvent(
                cycle=int(event.get("cycle", 0)),
                event_type=str(event.get("event_type", "updated")),
                basin_id=str(event.get("basin_id", "")),
                details=dict(event.get("details", {})),
            )
            for event in list(data.get("history", []))
            if isinstance(event, dict)
        ]
        return registry

    def _best_community_for_basin(
        self,
        basin: RegisteredBasin,
        communities: list[set[str]],
    ) -> tuple[int | None, float]:
        core = basin.core_members or basin.current_members
        if not core:
            return None, 0.0
        best_idx: int | None = None
        best_overlap = 0.0
        for idx, community in enumerate(communities):
            overlap = len(core & community) / max(1, len(core))
            if overlap > best_overlap:
                best_idx = idx
                best_overlap = overlap
        return best_idx, best_overlap

    def _register_new_basin(
        self,
        members: set[str],
        *,
        cycle: int,
        basin_id: str | None = None,
        parent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RegisteredBasin:
        assigned_id = basin_id or self._allocate_id()
        self._sync_next_id(assigned_id)
        member_set = {str(node) for node in members}
        meta = dict(metadata or {})
        member_streaks = {node: 1 for node in member_set}
        missing_streaks = {node: 0 for node in member_set}
        meta.setdefault("member_presence_streaks", member_streaks)
        meta.setdefault("member_absence_streaks", missing_streaks)
        basin = RegisteredBasin(
            basin_id=assigned_id,
            core_members=set(member_set),
            current_members=set(member_set),
            status="active",
            created_cycle=cycle,
            last_active_cycle=cycle,
            parent_id=parent_id,
            emergent_count_peak=self._count_emergents(member_set),
            emergent_count_current=self._count_emergents(member_set),
            metadata=meta,
        )
        self._basins[assigned_id] = basin
        self._record_event(
            cycle,
            "created",
            assigned_id,
            {"members": len(member_set), "parent_id": parent_id},
        )
        return basin

    def _allocate_id(self) -> str:
        basin_id = f"basin_{self._next_id}"
        self._next_id += 1
        return basin_id

    def _sync_next_id(self, basin_id: str) -> None:
        if basin_id.startswith("basin_") and basin_id.split("_")[-1].isdigit():
            numeric = int(basin_id.split("_")[-1]) + 1
            self._next_id = max(self._next_id, numeric)

    def _is_protected(self, basin: RegisteredBasin, cycle: int) -> bool:
        return cycle <= int(basin.metadata.get("protected_until_cycle", -1))

    def _update_core_tracking(self, basin: RegisteredBasin, members: set[str], cycle: int) -> None:
        presence = basin.metadata.setdefault("member_presence_streaks", {})
        absence = basin.metadata.setdefault("member_absence_streaks", {})
        tracked_nodes = set(presence) | set(absence) | set(basin.current_members) | set(basin.core_members)

        for node in tracked_nodes | set(members):
            if node in members:
                presence[node] = int(presence.get(node, 0)) + 1
                absence[node] = 0
            else:
                absence[node] = int(absence.get(node, 0)) + 1
                presence[node] = 0

        for node, streak in presence.items():
            if int(streak) >= self.core_stability_cycles:
                basin.core_members.add(str(node))

        removable = {
            str(node)
            for node in list(basin.core_members)
            if int(absence.get(node, 0)) >= self.core_absence_tolerance
        }
        basin.core_members.difference_update(removable)

        max_core = max(1, len(members) // 2) if members else len(basin.core_members)
        if members and len(basin.core_members) > max_core:
            ranked = sorted(
                basin.core_members,
                key=lambda node: (
                    int(presence.get(node, 0)),
                    -int(absence.get(node, 0)),
                    node,
                ),
                reverse=True,
            )
            basin.core_members = set(ranked[:max_core])

        basin.metadata["last_core_update_cycle"] = cycle

    def _make_basin_info(self, basin: RegisteredBasin, *, memory_web: MemoryWeb | None) -> BasinInfo:
        now = time.time()
        nodes = sorted(basin.current_members)
        if memory_web is None or not nodes:
            return BasinInfo(
                basin_id=basin.basin_id,
                nodes=nodes,
                size=len(nodes),
                internal_edges=0,
                boundary_edges=0,
                internal_density=0.0,
                emergent_count=basin.emergent_count_current,
                mean_stability=0.0,
                top_nodes_by_access=[],
                created_at=now,
            )

        node_set = set(nodes)
        sub = memory_web.graph.subgraph(node_set)
        internal_edges = int(sub.number_of_edges())
        boundary_edges = 0
        for u, v in memory_web.graph.edges():
            if (u in node_set) ^ (v in node_set):
                boundary_edges += 1

        max_edges = len(nodes) * (len(nodes) - 1) / 2
        density = float(internal_edges / max_edges) if max_edges > 0 else 0.0
        stabilities: list[float] = []
        accesses: list[tuple[str, int]] = []
        for node in nodes:
            entry = memory_web.get_concept(node) or {}
            stabilities.append(float(entry.get("stability", 0.0)))
            accesses.append((node, int(entry.get("access_count", 0))))
        accesses.sort(key=lambda item: (-item[1], item[0]))
        mean_stability = (sum(stabilities) / len(stabilities)) if stabilities else 0.0
        return BasinInfo(
            basin_id=basin.basin_id,
            nodes=nodes,
            size=len(nodes),
            internal_edges=internal_edges,
            boundary_edges=boundary_edges,
            internal_density=density,
            emergent_count=basin.emergent_count_current,
            mean_stability=float(mean_stability),
            top_nodes_by_access=accesses[:10],
            created_at=now,
        )

    def _count_emergents(self, members: set[str]) -> int:
        return sum(1 for node in members if node.startswith("Emergent_"))

    def _record_event(self, cycle: int, event_type: str, basin_id: str, details: dict[str, Any]) -> None:
        event = RegistryEvent(cycle=cycle, event_type=event_type, basin_id=basin_id, details=dict(details))
        self._history.append(event)
        self._last_cycle_events.append(event)
