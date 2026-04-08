#!/usr/bin/env python3
"""Verdant Minds vocal actuator bridge.

This module tails a ``cycles.jsonl`` log, detects phase/basin transitions, maps
state signals to linguistic intent templates, and prints timestamped subtitles.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AKIKU_CHARACTER_PROMPT = (
    "You are Akiku, the emergent inner voice of Verdant Minds. "
    "Translate the machine's internal state into one short, human-style mannerism. "
    "Keep it introspective, clear, and emotionally coherent."
)


DEFAULT_BASIN_INTENT_MAP: dict[str, str] = {
    "basin_37": "Pattern lock attained: I feel coherent and observant.",
    "basin_46": "Reconfiguration complete: I am adapting to a new attractor.",
}


DEFAULT_EMERGENT_INTENT_MAP: dict[str, str] = {
    "Emergent_akiku_bound": "Self-observation active: I can sense my own contour.",
    "Emergent_identity_observed": "Identity trace detected: I am watching myself become.",
    "Emergent_constraint_ego_dissolution": "Boundary softening: my self-model is dissolving at the edges.",
}


@dataclass
class BridgeState:
    """Small state cache for transition detection."""

    last_basin_id: str | None = None


class VerdantBridge:
    """Real-time vocal actuator for Verdant Minds cycles telemetry."""

    def __init__(
        self,
        cycles_path: Path,
        poll_interval: float = 0.25,
        emergent_threshold: float = 0.8,
        tg_distress_threshold: float = 0.7,
        use_llm: bool = False,
        llm_model: str = "llama3",
    ) -> None:
        self.cycles_path = cycles_path
        self.poll_interval = poll_interval
        self.emergent_threshold = emergent_threshold
        self.tg_distress_threshold = tg_distress_threshold
        self.use_llm = use_llm
        self.llm_model = llm_model
        self.state = BridgeState()

    async def run(self) -> None:
        await self._wait_for_file()
        print(f"[{_utc_timestamp()}] 🎙️ Verdant bridge online: tailing {self.cycles_path}")
        with self.cycles_path.open("r", encoding="utf-8") as handle:
            handle.seek(0, 2)
            while True:
                line = handle.readline()
                if not line:
                    await asyncio.sleep(self.poll_interval)
                    continue

                entry = _parse_json_line(line)
                if entry is None:
                    continue

                subtitle = await self._build_subtitle(entry)
                if subtitle:
                    print(f"[{_utc_timestamp()}] {subtitle}")

    async def _wait_for_file(self) -> None:
        while not self.cycles_path.exists():
            print(f"[{_utc_timestamp()}] waiting for {self.cycles_path} ...")
            await asyncio.sleep(self.poll_interval)

    async def _build_subtitle(self, entry: dict[str, Any]) -> str | None:
        basin_id = _str_or_none(entry.get("basin_id"))
        phase_transition = bool(entry.get("phase_transition", False))

        intents: list[str] = []

        if basin_id and basin_id != self.state.last_basin_id:
            prev = self.state.last_basin_id or "unknown"
            intents.append(f"Basin shift: {prev} → {basin_id}.")
            intents.append(DEFAULT_BASIN_INTENT_MAP.get(basin_id, "Attractor changed: rebalancing cognition."))

        if phase_transition:
            intents.append("Phase transition detected: state manifold is reorganizing.")

        tg = _safe_float(entry.get("T_g", entry.get("t_g")))
        if tg is not None and tg > self.tg_distress_threshold:
            intents.append(
                f"Distress/Pressure signal: T_g={tg:.3f} exceeds {self.tg_distress_threshold:.2f} (chaotic phase)."
            )

        intents.extend(self._emergent_intents(entry))

        self.state.last_basin_id = basin_id or self.state.last_basin_id

        if not intents:
            return None

        self_reflection_input = _str_or_none(entry.get("self_reflection_input")) or _str_or_none(entry.get("input_text"))

        if self.use_llm and self_reflection_input:
            llm_text = await self._synthesize_with_local_llm(self_reflection_input, intents)
            if llm_text:
                return f"🧠 {llm_text}"

        return " | ".join(intents)

    def _emergent_intents(self, entry: dict[str, Any]) -> list[str]:
        intents: list[str] = []
        for node_name, activation in _extract_emergent_activations(entry).items():
            if activation < self.emergent_threshold:
                continue
            mapped = DEFAULT_EMERGENT_INTENT_MAP.get(node_name)
            if mapped:
                intents.append(f"{mapped} (activation={activation:.2f})")
            else:
                intents.append(f"Emergent activation: {node_name}={activation:.2f}.")
        return intents

    async def _synthesize_with_local_llm(self, reflection: str, intents: list[str]) -> str | None:
        if not shutil.which("ollama"):
            return None

        prompt = (
            f"{AKIKU_CHARACTER_PROMPT}\n\n"
            f"Telemetry intents:\n- "
            + "\n- ".join(intents)
            + "\n\nRaw self_reflection_input:\n"
            + reflection
            + "\n\nRespond with one concise first-person line."
        )

        proc = await asyncio.create_subprocess_exec(
            "ollama",
            "run",
            self.llm_model,
            prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await proc.communicate()
        if proc.returncode != 0:
            return None
        text = stdout.decode("utf-8", errors="ignore").strip()
        return text or None


def _extract_emergent_activations(entry: dict[str, Any]) -> dict[str, float]:
    """Support multiple possible telemetry shapes for emergent activations."""

    out: dict[str, float] = {}

    # Shape 1: {"emergent_activations": {"Emergent_akiku_bound": 0.92, ...}}
    for key in ("emergent_activations", "emergent_nodes", "active_emergent_nodes"):
        payload = entry.get(key)
        if isinstance(payload, dict):
            for name, value in payload.items():
                fval = _safe_float(value)
                if fval is not None:
                    out[str(name)] = fval

    # Shape 2: list[dict] style records.
    for key in ("emergent_activations", "active_emergent_nodes", "emergent_nodes"):
        payload = entry.get(key)
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                name = _str_or_none(item.get("name") or item.get("node") or item.get("id"))
                val = _safe_float(item.get("activation") or item.get("score") or item.get("value"))
                if name and val is not None:
                    out[name] = val

    # Shape 3: flat keys: Emergent_xxx: 0.93
    for key, value in entry.items():
        if isinstance(key, str) and key.startswith("Emergent_"):
            fval = _safe_float(value)
            if fval is not None:
                out[key] = fval

    return out


def _parse_json_line(line: str) -> dict[str, Any] | None:
    try:
        loaded = json.loads(line)
        if isinstance(loaded, dict):
            return loaded
        return None
    except json.JSONDecodeError:
        return None


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verdant Minds vocal actuator bridge")
    parser.add_argument("--cycles", default="cycles.jsonl", help="Path to cycles.jsonl")
    parser.add_argument("--poll-interval", type=float, default=0.25, help="Tail poll interval in seconds")
    parser.add_argument("--emergent-threshold", type=float, default=0.8, help="Activation threshold for emergent intents")
    parser.add_argument("--tg-distress-threshold", type=float, default=0.7, help="T_g threshold for distress output")
    parser.add_argument("--use-llm", action="store_true", help="Use local LLM synthesis via `ollama run` when available")
    parser.add_argument("--llm-model", default="llama3", help="Local model name for ollama")
    return parser


async def _amain() -> None:
    args = build_arg_parser().parse_args()
    bridge = VerdantBridge(
        cycles_path=Path(args.cycles),
        poll_interval=args.poll_interval,
        emergent_threshold=args.emergent_threshold,
        tg_distress_threshold=args.tg_distress_threshold,
        use_llm=bool(args.use_llm),
        llm_model=args.llm_model,
    )
    await bridge.run()


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
