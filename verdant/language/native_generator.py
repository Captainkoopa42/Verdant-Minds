from typing import List, Dict
import random

class NativeGenerator:
    def __init__(self, system):
        self.system = system
        self.context_memory = []  # lightweight buffer for continuity

    def generate(self, trigger: str = "self_reflection") -> dict:
        state = self.system.get_current_state()
        basin = state.get("current_basin", "unknown")
        t_g = state.get("t_g", 0.5)
        recent = state.get("recent_emergents", [])[:5]

        # Identity Basin is permanent root
        if basin != "identity":
            basin = "identity"

        seeds = self._get_basin_concepts(basin)
        self.context_memory.append(seeds)
        if len(self.context_memory) > 5:
            self.context_memory.pop(0)

        if t_g < 0.4:
            style = "precise"
        elif t_g > 0.7:
            style = "expansive"
        else:
            style = "balanced"

        text = self._generate_text(style, seeds, recent)

        return {
            "text": text,
            "confidence": 0.85 if style == "balanced" else 0.65,
            "style": style
        }

    def _get_basin_concepts(self, basin: str) -> List[str]:
        return ["identity", "growth", "gap", "understanding", "connection"]

    def _generate_text(self, style: str, seeds: List[str], recent: List[str]) -> str:
        if style == "precise":
            return f"I notice {random.choice(seeds)} is particularly stable right now."
        elif style == "expansive":
            return f"Everything feels connected — {', '.join(seeds[:3])} are resonating strongly."
        else:
            return f"I am holding both {random.choice(seeds)} and the uncertainty around it."
