"""Reactive condition parsing and evaluation for VCult specs."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from cultivation.schemas import ScaffoldContext


@dataclass(frozen=True)
class Condition:
    """Parsed scalar or temporal condition."""

    kind: str
    metric: str | None = None
    operator: str | None = None
    value: float | int | None = None
    cycles: int | None = None
    raw: str = ""


@dataclass
class SystemState:
    """Minimal runtime state exposed to the reactive evaluator."""

    scaffold_context: ScaffoldContext
    cycle: int
    phase_cycle: int
    emergent_rate_history: list[float] = field(default_factory=list)
    self_referential_count: int = 0
    last_bud_cycle: int | None = None
    last_self_reflection_cycle: int | None = None

    @property
    def latest_bud_cycle(self) -> int | None:
        if self.last_bud_cycle is not None:
            return self.last_bud_cycle
        recent = self.scaffold_context.recent_bud_events
        if not recent:
            return None
        return int(recent[-1].get("cycle", 0))


@dataclass(frozen=True)
class ConditionResult:
    """Detailed evaluation payload for telemetry."""

    met: bool
    details: dict[str, Any]


class ConditionEvaluator:
    """Evaluates milestone conditions against current system state."""

    _ROLLING_RE = re.compile(
        r"^(?P<metric>[a-z_]+)\s*(?P<op><|>)\s*(?P<value>\d+(?:\.\d+)?)\s+for\s+(?P<cycles>\d+)\s+cycles$"
    )
    _COMPARE_RE = re.compile(
        r"^(?P<metric>[a-z_]+)\s*(?P<op>>=|<=|==|>|<)\s*(?P<value>\d+(?:\.\d+)?)$"
    )
    _LATEST_BUD_RE = re.compile(r"^latest_bud_within\s+(?P<cycles>\d+)\s+cycles$")
    _NO_BUD_RE = re.compile(r"^no_bud_for\s+(?P<cycles>\d+)\s+cycles$")
    _INTERVAL_RE = re.compile(r"^interval\s+(?P<cycles>\d+)$")

    def parse_condition(self, condition_str: str) -> Condition:
        """Parse a condition string like 'emergent_count >= 50'."""
        text = str(condition_str or "").strip()
        if not text:
            raise ValueError("Condition string must be non-empty.")

        for pattern, kind in (
            (self._ROLLING_RE, "rolling_average"),
            (self._COMPARE_RE, "comparison"),
            (self._LATEST_BUD_RE, "latest_bud_within"),
            (self._NO_BUD_RE, "no_bud_for"),
            (self._INTERVAL_RE, "interval"),
        ):
            match = pattern.match(text)
            if match:
                groups = match.groupdict()
                return Condition(
                    kind=kind,
                    metric=groups.get("metric"),
                    operator=groups.get("op"),
                    value=self._coerce_number(groups.get("value")),
                    cycles=(int(groups["cycles"]) if groups.get("cycles") is not None else None),
                    raw=text,
                )

        raise ValueError(f"Unsupported condition: {condition_str}")

    def evaluate(self, condition: dict[str, Any] | list[Any] | str, state: SystemState) -> bool:
        """Check if a condition is met."""
        return self.evaluate_with_details(condition, state).met

    def evaluate_with_details(self, condition: dict[str, Any] | list[Any] | str, state: SystemState) -> ConditionResult:
        """Evaluate a condition and return detailed telemetry-friendly output."""
        if isinstance(condition, str):
            parsed = self.parse_condition(condition)
            return self._evaluate_leaf(parsed, state)

        if isinstance(condition, list):
            results = [self.evaluate_with_details(item, state) for item in condition]
            met = all(result.met for result in results)
            return ConditionResult(met=met, details={"mode": "all", "children": [result.details for result in results]})

        if not isinstance(condition, dict):
            raise TypeError("Condition must be a string, mapping, or list.")

        if "all" in condition:
            raw_children = condition.get("all") or []
            results = [self.evaluate_with_details(item, state) for item in raw_children]
            return ConditionResult(
                met=all(result.met for result in results),
                details={"mode": "all", "children": [result.details for result in results]},
            )
        if "any" in condition:
            raw_children = condition.get("any") or []
            results = [self.evaluate_with_details(item, state) for item in raw_children]
            return ConditionResult(
                met=any(result.met for result in results),
                details={"mode": "any", "children": [result.details for result in results]},
            )

        raise ValueError("Condition mapping must contain 'all' or 'any'.")

    def _evaluate_leaf(self, condition: Condition, state: SystemState) -> ConditionResult:
        if condition.kind == "comparison":
            actual = self._metric_value(condition.metric or "", state)
            met = self._compare(actual, condition.operator or "==", float(condition.value or 0))
            return ConditionResult(met=met, details={"condition": condition.raw, "actual": actual, "met": met})

        if condition.kind == "rolling_average":
            window = int(condition.cycles or 0)
            history = state.emergent_rate_history[-window:]
            actual = (sum(history) / len(history)) if history else None
            met = len(history) == window and self._compare(float(actual), condition.operator or "<", float(condition.value or 0))
            return ConditionResult(
                met=met,
                details={
                    "condition": condition.raw,
                    "actual": actual,
                    "window": window,
                    "history_length": len(history),
                    "met": met,
                },
            )

        if condition.kind == "latest_bud_within":
            latest = state.latest_bud_cycle
            window = int(condition.cycles or 0)
            actual = None if latest is None else state.cycle - latest
            met = latest is not None and actual <= window
            return ConditionResult(met=met, details={"condition": condition.raw, "actual": actual, "met": met})

        if condition.kind == "no_bud_for":
            latest = state.latest_bud_cycle
            window = int(condition.cycles or 0)
            actual = state.cycle if latest is None else state.cycle - latest
            met = actual >= window
            return ConditionResult(met=met, details={"condition": condition.raw, "actual": actual, "met": met})

        if condition.kind == "interval":
            interval = int(condition.cycles or 0)
            met = interval > 0 and state.phase_cycle > 0 and state.phase_cycle % interval == 0
            return ConditionResult(met=met, details={"condition": condition.raw, "actual": state.phase_cycle, "met": met})

        raise ValueError(f"Unsupported condition kind: {condition.kind}")

    @staticmethod
    def _coerce_number(value: str | None) -> float | int | None:
        if value is None:
            return None
        return float(value) if "." in value else int(value)

    @staticmethod
    def _compare(actual: float, operator: str, expected: float) -> bool:
        if operator == ">=":
            return actual >= expected
        if operator == "<=":
            return actual <= expected
        if operator == "==":
            return abs(actual - expected) < 1e-9
        if operator == ">":
            return actual > expected
        if operator == "<":
            return actual < expected
        raise ValueError(f"Unsupported operator: {operator}")

    @staticmethod
    def _metric_value(metric: str, state: SystemState) -> float:
        context = state.scaffold_context
        if metric == "emergent_count":
            return float(context.emergent_count)
        if metric == "basin_count":
            return float(context.basin_count)
        if metric == "earlier_share":
            return float(context.earlier_share)
        if metric == "t_g":
            return float(context.t_g)
        if metric == "dormant_count":
            return float(context.dormant_basin_count)
        if metric == "self_referential_count":
            return float(state.self_referential_count)
        if metric == "emergent_rate":
            return float(state.emergent_rate_history[-1] if state.emergent_rate_history else 0.0)
        raise ValueError(f"Unsupported metric: {metric}")
