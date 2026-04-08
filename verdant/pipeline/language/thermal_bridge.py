"""Thermal bridge utilities for generation-time parameter adaptation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from verdant.memory.basins import BasinInfo, detect_basins

if TYPE_CHECKING:
    from verdant.system import VerdantSystem


class ThermalBridge:
    """Maps Verdant thermodynamic state into language generation controls."""

    _BASELINE: float = 0.5
    _TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]*")
    _SELF_IDENTITY_HINTS = {
        "self",
        "identity",
        "agency",
        "autonomy",
        "consciousness",
        "mind",
        "introspection",
        "reflection",
        "selfhood",
        "ego",
        "personhood",
    }

    def __init__(self, system: "VerdantSystem") -> None:
        self.system = system

    def get_generation_config(self) -> dict[str, Any]:
        """Build generation controls from telemetry + ECWF state.

        Mapping:
        - temperature = 0.2 + (T_g * 1.6)
        - top_p = clamp(0.6 + (h_sys * 0.5), 0.1, 1.0)
        - frequency_penalty = 0.1 + (T_g * 0.9)
        """
        t_g = self._extract_t_g()
        h_sys = self._extract_h_sys()
        phase = self._extract_phase(t_g)

        return {
            "temperature": 0.2 + (t_g * 1.6),
            "top_p": self._clamp(0.6 + (h_sys * 0.5), 0.1, 1.0),
            "frequency_penalty": 0.1 + (t_g * 0.9),
            "phase": phase,
            "identity_bias_tokens": self.get_identity_bias_tokens(),
        }

    def get_identity_bias_tokens(self, top_k: int = 24) -> list[str]:
        """Identity-bias placeholder.

        Finds the basin most aligned with self-identity semantics in MemoryWeb,
        then returns high-weight concept tokens for later logit boosting.
        """
        memory_web = getattr(self.system, "memory_web", None)
        if memory_web is None:
            return []

        try:
            basins = detect_basins(
                memory_web,
                k=int(getattr(getattr(self.system, "config", object()), "basin_scan_k", 6)),
                min_size=max(3, int(getattr(getattr(self.system, "config", object()), "basin_min_size", 5))),
            )
        except Exception:
            basins = []

        if not basins:
            return []

        target = self._select_self_identity_basin(basins)
        if target is None:
            return []

        token_weights: dict[str, float] = {}
        graph = memory_web.graph
        for label in target.nodes:
            concept = memory_web.get_concept(label) or {}
            stability = float(concept.get("stability", self._BASELINE))
            edge_weight = 0.0
            if label in graph:
                edge_weight = sum(float(d.get("weight", self._BASELINE)) for _, _, d in graph.edges(label, data=True))
            node_weight = stability + (0.25 * edge_weight)

            for token in self._tokenize(label):
                token_weights[token] = token_weights.get(token, 0.0) + node_weight

        ranked = sorted(token_weights.items(), key=lambda kv: kv[1], reverse=True)
        return [token for token, _ in ranked[:top_k]]

    def _extract_t_g(self) -> float:
        metrics = self._safe_metrics()
        raw_t_g = metrics.get("t_g", getattr(self.system, "_t_g", self._BASELINE))
        return self._clamp(self._coerce_float(raw_t_g, self._BASELINE), 0.0, 1.0)

    def _extract_h_sys(self) -> float:
        entropy_history = getattr(self.system, "_entropy_history", None)
        if isinstance(entropy_history, list) and entropy_history:
            return self._clamp(self._coerce_float(entropy_history[-1], self._BASELINE), 0.0, 1.0)

        ecwf = getattr(self.system, "ecwf", None)
        past_states = getattr(ecwf, "past_states", None)
        if isinstance(past_states, list) and past_states:
            try:
                entropy = float(ecwf.calculate_entropy(past_states[-1]))
                return self._clamp(entropy, 0.0, 1.0)
            except Exception:
                pass

        metrics = self._safe_metrics()
        return self._clamp(self._coerce_float(metrics.get("avg_entropy", self._BASELINE), self._BASELINE), 0.0, 1.0)

    def _extract_phase(self, t_g: float) -> str:
        metrics = self._safe_metrics()
        phase = metrics.get("phase")
        if isinstance(phase, str) and phase:
            return phase
        if t_g < 0.4:
            return "Rigid"
        if t_g <= 0.6:
            return "Flexible"
        return "Chaotic"

    def _safe_metrics(self) -> dict[str, Any]:
        get_metrics = getattr(self.system, "get_metrics", None)
        if callable(get_metrics):
            try:
                metrics = get_metrics()
                if isinstance(metrics, dict):
                    return metrics
            except Exception:
                pass
        return {}

    @classmethod
    def _select_self_identity_basin(cls, basins: list[BasinInfo]) -> BasinInfo | None:
        best: BasinInfo | None = None
        best_score = float("-inf")

        for basin in basins:
            matches = 0
            for label in basin.nodes:
                tokens = cls._tokenize(label)
                matches += sum(1 for tok in tokens if tok in cls._SELF_IDENTITY_HINTS)

            # prefer semantically matching basins, then denser/stabler ones
            score = (2.5 * matches) + (0.4 * basin.mean_stability) + (0.05 * basin.size)
            if score > best_score:
                best_score = score
                best = basin

        if best_score <= 0.0:
            return None
        return best

    @classmethod
    def _tokenize(cls, text: str) -> list[str]:
        return [m.group(0).lower() for m in cls._TOKEN_RE.finditer(str(text))]

    @staticmethod
    def _coerce_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))
