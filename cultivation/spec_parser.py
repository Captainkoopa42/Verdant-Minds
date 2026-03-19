"""Parser and sequence generator for YAML-based cultivation specs (.vcult)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from cultivation.providers.topic_variation import vary_topic_for_pass


class SpecValidationError(ValueError):
    """Raised when a cultivation spec is invalid."""


@dataclass(frozen=True)
class BasinTopicRule:
    """Rule for selecting a basin-targeted topic."""

    threshold: float
    topics: list[str]


@dataclass(frozen=True)
class BasinTopicsSpec:
    """Optional basin-aware topic routing configuration."""

    understimulated: BasinTopicRule | None = None
    dominant: BasinTopicRule | None = None


@dataclass(frozen=True)
class PhaseSpec:
    """A single declarative cultivation phase."""

    name: str
    topics: list[str]
    cycles: int | None = None
    self_reflect_interval: int = 0
    description: str = ""
    min_cycles: int = 0
    max_cycles: int | None = None
    advance_when: dict[str, list[str]] | None = None
    self_reflect_when: dict[str, list[str]] | None = None
    self_reflect_cooldown: int = 0
    basin_topics: BasinTopicsSpec | None = None
    on_start: list[str] = field(default_factory=list)
    on_end: list[str] = field(default_factory=list)

    @property
    def planned_cycles(self) -> int:
        if self.cycles is not None and self.advance_when is None:
            return self.cycles
        if self.max_cycles is not None:
            return self.max_cycles
        if self.cycles is not None:
            return self.cycles
        return self.min_cycles

    @property
    def fixed_cycles(self) -> bool:
        return self.advance_when is None and self.cycles is not None


@dataclass(frozen=True)
class ConvergenceSpec:
    """Optional whole-run convergence settings."""

    conditions: dict[str, list[str]]
    min_total_cycles: int = 0
    max_total_cycles: int | None = None


@dataclass(frozen=True)
class CultivationSpec:
    """A fully validated cultivation spec."""

    name: str
    description: str
    additional_seeds: list[str]
    settings: dict[str, Any]
    phases: list[PhaseSpec]
    validation: dict[str, Any]
    total_cycles: int
    convergence: ConvergenceSpec | None = None
    is_reactive: bool = False

    @classmethod
    def from_file(cls, path: str) -> "CultivationSpec":
        """Load and validate a cultivation spec from YAML."""
        spec_path = Path(path)
        payload = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise SpecValidationError("Spec root must be a YAML mapping.")
        return cls.from_dict(payload, source=str(spec_path))

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, source: str = "<memory>") -> "CultivationSpec":
        """Validate and build a cultivation spec from a parsed mapping."""
        required = ["name", "description", "phases"]
        missing = [field for field in required if field not in payload]
        if missing:
            raise SpecValidationError(f"Missing required field(s) in {source}: {', '.join(missing)}")

        name = _require_non_empty_string(payload.get("name"), field="name")
        description = _require_non_empty_string(payload.get("description"), field="description")

        seeds_section = payload.get("seeds", {}) or {}
        if not isinstance(seeds_section, dict):
            raise SpecValidationError("'seeds' must be a mapping when provided.")
        additional_seeds = _validate_string_list(seeds_section.get("additional", []), field="seeds.additional", allow_empty=True)

        settings = payload.get("settings", {}) or {}
        if not isinstance(settings, dict):
            raise SpecValidationError("'settings' must be a mapping when provided.")

        raw_phases = payload.get("phases")
        if not isinstance(raw_phases, list) or not raw_phases:
            raise SpecValidationError("'phases' must be a non-empty list.")

        phases: list[PhaseSpec] = []
        total_cycles = 0
        is_reactive = False
        for idx, raw_phase in enumerate(raw_phases, start=1):
            if not isinstance(raw_phase, dict):
                raise SpecValidationError(f"Phase {idx} must be a mapping.")
            phase = _parse_phase(raw_phase, idx=idx)
            phases.append(phase)
            total_cycles += phase.planned_cycles
            if not phase.fixed_cycles or phase.self_reflect_when is not None or phase.basin_topics is not None or phase.on_start or phase.on_end:
                is_reactive = True

        validation = payload.get("validation", {}) or {}
        if not isinstance(validation, dict):
            raise SpecValidationError("'validation' must be a mapping when provided.")

        convergence = None
        raw_convergence = payload.get("convergence")
        if raw_convergence is not None:
            convergence = _parse_convergence(raw_convergence)
            is_reactive = True

        return cls(
            name=name,
            description=description,
            additional_seeds=additional_seeds,
            settings=dict(settings),
            phases=phases,
            validation=dict(validation),
            total_cycles=total_cycles,
            convergence=convergence,
            is_reactive=is_reactive,
        )

    def generate_input_sequence(self) -> list[dict[str, Any]]:
        """Generate the full per-cycle cultivation sequence for the spec."""
        sequence: list[dict[str, Any]] = []
        cycle_number = 0
        for phase in self.phases:
            topic_pass_counts = {topic: 0 for topic in phase.topics}
            for phase_cycle in range(1, phase.planned_cycles + 1):
                cycle_number += 1
                is_self_reflection = (
                    phase.self_reflect_when is None
                    and phase.self_reflect_interval > 0
                    and phase_cycle % phase.self_reflect_interval == 0
                )
                topic = phase.topics[(phase_cycle - 1) % len(phase.topics)]
                if is_self_reflection:
                    input_text = "[SELF_REFLECTION]"
                else:
                    topic_pass_counts[topic] += 1
                    input_text = vary_topic_for_pass(topic, topic_pass_counts[topic])
                sequence.append(
                    {
                        "cycle": cycle_number,
                        "phase": phase.name,
                        "input_text": input_text,
                        "is_self_reflection": is_self_reflection,
                    }
                )
        return sequence


def _parse_phase(raw_phase: dict[str, Any], *, idx: int) -> PhaseSpec:
    phase_name = _require_non_empty_string(raw_phase.get("name"), field=f"phases[{idx}].name")
    topics = _validate_string_list(raw_phase.get("topics"), field=f"phases[{idx}].topics", allow_empty=False)
    phase_description = str(raw_phase.get("description", "") or "")
    advance_when = _parse_condition_group(raw_phase.get("advance_when"), field=f"phases[{idx}].advance_when")
    self_reflect_when = _parse_condition_group(raw_phase.get("self_reflect_when"), field=f"phases[{idx}].self_reflect_when")
    self_reflect_interval = _require_non_negative_int(
        raw_phase.get("self_reflect_interval", 0),
        field=f"phases[{idx}].self_reflect_interval",
    )
    self_reflect_cooldown = _require_non_negative_int(
        raw_phase.get("self_reflect_cooldown", 0),
        field=f"phases[{idx}].self_reflect_cooldown",
    )
    basin_topics = _parse_basin_topics(raw_phase.get("basin_topics"), field=f"phases[{idx}].basin_topics")
    on_start = _validate_string_list(raw_phase.get("on_start", []), field=f"phases[{idx}].on_start", allow_empty=True)
    on_end = _validate_string_list(raw_phase.get("on_end", []), field=f"phases[{idx}].on_end", allow_empty=True)

    raw_cycles = raw_phase.get("cycles")
    cycles = None if raw_cycles is None else _require_positive_int(raw_cycles, field=f"phases[{idx}].cycles")
    raw_min = raw_phase.get("min_cycles")
    raw_max = raw_phase.get("max_cycles")
    min_cycles = 0 if raw_min is None else _require_non_negative_int(raw_min, field=f"phases[{idx}].min_cycles")
    max_cycles = None if raw_max is None else _require_positive_int(raw_max, field=f"phases[{idx}].max_cycles")

    if cycles is None and max_cycles is None:
        raise SpecValidationError(
            f"Phase {idx} must define either 'cycles' or 'max_cycles' (with optional 'advance_when')."
        )
    if max_cycles is None and cycles is not None and advance_when is not None:
        max_cycles = cycles
    if max_cycles is not None and max_cycles < min_cycles:
        raise SpecValidationError(f"'phases[{idx}].max_cycles' must be >= 'phases[{idx}].min_cycles'.")
    if cycles is not None and advance_when is None:
        min_cycles = cycles
        max_cycles = cycles

    return PhaseSpec(
        name=phase_name,
        topics=topics,
        cycles=cycles,
        self_reflect_interval=self_reflect_interval,
        description=phase_description,
        min_cycles=min_cycles,
        max_cycles=max_cycles,
        advance_when=advance_when,
        self_reflect_when=self_reflect_when,
        self_reflect_cooldown=self_reflect_cooldown,
        basin_topics=basin_topics,
        on_start=on_start,
        on_end=on_end,
    )


def _parse_convergence(value: Any) -> ConvergenceSpec:
    if not isinstance(value, dict):
        raise SpecValidationError("'convergence' must be a mapping.")
    conditions = _parse_condition_group(value, field="convergence")
    if conditions is None:
        raise SpecValidationError("'convergence' must include 'all' or 'any'.")
    min_total_cycles = _require_non_negative_int(value.get("min_total_cycles", 0), field="convergence.min_total_cycles")
    max_total_cycles = value.get("max_total_cycles")
    if max_total_cycles is not None:
        max_total_cycles = _require_positive_int(max_total_cycles, field="convergence.max_total_cycles")
        if max_total_cycles < min_total_cycles:
            raise SpecValidationError("'convergence.max_total_cycles' must be >= 'convergence.min_total_cycles'.")
    return ConvergenceSpec(conditions=conditions, min_total_cycles=min_total_cycles, max_total_cycles=max_total_cycles)


def _parse_condition_group(value: Any, *, field: str) -> dict[str, list[str]] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SpecValidationError(f"'{field}' must be a mapping.")
    keys = [key for key in ("all", "any") if key in value]
    if len(keys) != 1:
        raise SpecValidationError(f"'{field}' must contain exactly one of 'all' or 'any'.")
    key = keys[0]
    items = _validate_string_list(value.get(key), field=f"{field}.{key}", allow_empty=False)
    return {key: items}


def _parse_basin_topics(value: Any, *, field: str) -> BasinTopicsSpec | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SpecValidationError(f"'{field}' must be a mapping.")
    return BasinTopicsSpec(
        understimulated=_parse_basin_topic_rule(value.get("understimulated"), field=f"{field}.understimulated"),
        dominant=_parse_basin_topic_rule(value.get("dominant"), field=f"{field}.dominant"),
    )


def _parse_basin_topic_rule(value: Any, *, field: str) -> BasinTopicRule | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SpecValidationError(f"'{field}' must be a mapping.")
    threshold = value.get("threshold")
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or threshold <= 0:
        raise SpecValidationError(f"'{field}.threshold' must be a positive number.")
    topics = _validate_string_list(value.get("topics"), field=f"{field}.topics", allow_empty=False)
    return BasinTopicRule(threshold=float(threshold), topics=topics)


def _require_non_empty_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SpecValidationError(f"'{field}' must be a non-empty string.")
    return value.strip()


def _validate_string_list(value: Any, *, field: str, allow_empty: bool) -> list[str]:
    if value is None:
        if allow_empty:
            return []
        raise SpecValidationError(f"'{field}' must be a non-empty list of strings.")
    if not isinstance(value, list):
        raise SpecValidationError(f"'{field}' must be a list of strings.")
    items: list[str] = []
    for idx, item in enumerate(value, start=1):
        if not isinstance(item, str) or not item.strip():
            raise SpecValidationError(f"'{field}[{idx}]' must be a non-empty string.")
        items.append(item.strip())
    if not allow_empty and not items:
        raise SpecValidationError(f"'{field}' must not be empty.")
    return items


def _require_positive_int(value: Any, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SpecValidationError(f"'{field}' must be a positive integer.")
    return int(value)


def _require_non_negative_int(value: Any, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise SpecValidationError(f"'{field}' must be a non-negative integer.")
    return int(value)
