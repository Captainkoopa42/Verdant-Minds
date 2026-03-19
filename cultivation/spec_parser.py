"""Parser and sequence generator for YAML-based cultivation specs (.vcult)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from cultivation.providers.topic_variation import vary_topic_for_pass


class SpecValidationError(ValueError):
    """Raised when a cultivation spec is invalid."""


@dataclass(frozen=True)
class PhaseSpec:
    """A single declarative cultivation phase."""

    name: str
    cycles: int
    topics: list[str]
    self_reflect_interval: int
    description: str = ""


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
        for idx, raw_phase in enumerate(raw_phases, start=1):
            if not isinstance(raw_phase, dict):
                raise SpecValidationError(f"Phase {idx} must be a mapping.")
            phase_name = _require_non_empty_string(raw_phase.get("name"), field=f"phases[{idx}].name")
            cycles = _require_positive_int(raw_phase.get("cycles"), field=f"phases[{idx}].cycles")
            topics = _validate_string_list(raw_phase.get("topics"), field=f"phases[{idx}].topics", allow_empty=False)
            self_reflect_interval = _require_non_negative_int(
                raw_phase.get("self_reflect_interval", 0),
                field=f"phases[{idx}].self_reflect_interval",
            )
            phase_description = str(raw_phase.get("description", "") or "")
            phases.append(
                PhaseSpec(
                    name=phase_name,
                    cycles=cycles,
                    topics=topics,
                    self_reflect_interval=self_reflect_interval,
                    description=phase_description,
                )
            )
            total_cycles += cycles

        validation = payload.get("validation", {}) or {}
        if not isinstance(validation, dict):
            raise SpecValidationError("'validation' must be a mapping when provided.")

        return cls(
            name=name,
            description=description,
            additional_seeds=additional_seeds,
            settings=dict(settings),
            phases=phases,
            validation=dict(validation),
            total_cycles=total_cycles,
        )

    def generate_input_sequence(self) -> list[dict[str, Any]]:
        """Generate the full per-cycle cultivation sequence for the spec."""
        sequence: list[dict[str, Any]] = []
        cycle_number = 0
        for phase in self.phases:
            topic_pass_counts = {topic: 0 for topic in phase.topics}
            for phase_cycle in range(1, phase.cycles + 1):
                cycle_number += 1
                is_self_reflection = (
                    phase.self_reflect_interval > 0 and phase_cycle % phase.self_reflect_interval == 0
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
