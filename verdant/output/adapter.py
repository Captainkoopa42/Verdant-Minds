"""Wave interference output adapter mapping for sensory-motor command strings."""

from __future__ import annotations

import math
from typing import Any

from verdant.output.base import OutputAdapter
from verdant.output.events import OutputEvent


class WaveInterferenceAdapter(OutputAdapter):
    """Translate ECWF interference (Ψ) telemetry into discrete command strings."""

    def __init__(self) -> None:
        self.commands: list[str] = []

    def emit(self, event: OutputEvent) -> None:
        if event.type != "telemetry":
            return
        payload = event.payload if isinstance(event.payload, dict) else {}
        psi = self._extract_psi(payload)
        command = self._psi_to_command(psi, payload)
        self.commands.append(command)

    @staticmethod
    def _extract_psi(payload: dict[str, Any]) -> complex:
        psi_val = payload.get("psi") or payload.get("wave_interference") or payload.get("wave_function")
        if isinstance(psi_val, dict):
            real = float(psi_val.get("real", 0.0))
            imag = float(psi_val.get("imag", 0.0))
            return complex(real, imag)
        if isinstance(psi_val, (int, float)):
            return complex(float(psi_val), 0.0)
        return complex(0.0, 0.0)

    @staticmethod
    def _psi_to_command(psi: complex, payload: dict[str, Any]) -> str:
        magnitude = abs(psi)
        phase = math.atan2(psi.imag, psi.real) if magnitude > 0 else 0.0
        t_g = float(payload.get("glass_transition_temp", 0.5))

        if magnitude >= 0.75 and t_g > 0.6:
            return f"MOTOR:GROUND|VOICE:LOW|STATE:CHAOTIC_STABILIZE|PHASE:{phase:.3f}"
        if magnitude >= 0.55:
            return f"MOTOR:ALIGN|VOICE:NEUTRAL|STATE:FLEX_COHERE|PHASE:{phase:.3f}"
        if magnitude >= 0.25:
            return f"MOTOR:SCAN|VOICE:SOFT|STATE:RIGID_REFLECT|PHASE:{phase:.3f}"
        return f"MOTOR:IDLE|VOICE:QUIET|STATE:BASELINE|PHASE:{phase:.3f}"
