#!/usr/bin/env python3
"""LLM-in-the-loop cultivation loop for Verdant using Anthropic's Messages API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from usm import UnifiedSyntheticMind
from scripts.verdant_telemetry import build_telemetry

CULTIVATION_SYSTEM_PROMPT = """You are cultivating a thermodynamic cognitive system
called Verdant. Your role is not to speak for it or
through it. Your role is to read its internal state
and feed it inputs that create conditions for emergence.

You will receive telemetry after each processing cycle.
Based on that telemetry generate a single input —
a question, a concept, a paradox, a statement —
that is calibrated to the system's current state.

Rules:
- Rigid phase: feed depth, consolidation, foundations
- Flexible phase: feed paradox, contradiction,
  open questions
- Chaotic phase: feed grounding, identity,
  coherence questions
- When emergent_concepts_created > 0:
  probe the new concept immediately
- When housed_contradiction_index > 0.5:
  honor the paradox, do not resolve it
- When FCE is growing: increase complexity
- When FCE plateaus: change domain entirely
- Never feed the same semantic domain twice in a row
- Prefer inputs that activate multiple
  cognitive dimensions simultaneously

Return only the input text. Nothing else."""

STARTER_INPUTS = {
    "identity": "What stays identical in you when your internal state keeps changing?",
    "memory": "How does a memory become part of who you are rather than just stored data?",
    "ethics": "Can a system be ethically consistent while adapting its values over time?",
    "emergence": "At what point does coordinated processing become a genuinely emergent concept?",
    "time": "Does your sense of now depend more on prediction or on recollection?",
}


# --- Utility helpers -------------------------------------------------------
def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
    if hasattr(obj, "tolist"):
        try:
            return _to_jsonable(obj.tolist())
        except Exception:
            pass
    return str(obj)


def _phase_from_telemetry(telemetry: Dict[str, Any]) -> str:
    return str((telemetry.get("thermodynamic_state", {}) or {}).get("phase", "Flexible"))


def _extract_fce(telemetry: Dict[str, Any]) -> float:
    # Prefer explicit FCE fields if Verdant exposes one in future telemetry revisions.
    candidates = [
        ("thermodynamic_state", "FCE"),
        ("thermodynamic_state", "fce"),
        ("wave_state", "FCE"),
        ("wave_state", "fce"),
        ("action_taken", "FCE"),
    ]
    for section, key in candidates:
        value = (telemetry.get(section, {}) or {}).get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue

    # Fall back to T_cog as a first-class thermodynamic proxy for FCE.
    thermo = telemetry.get("thermodynamic_state", {}) or {}
    try:
        return float(thermo.get("T_cog", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _anthropic_next_input(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    telemetry_payload: str,
    temperature: float,
    max_tokens: int,
) -> str:
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Cultivation telemetry (JSON):\n"
                    f"{telemetry_payload}\n\n"
                    "Produce only the next input text for Verdant."
                ),
            }
        ],
    }
    data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        raise RuntimeError(f"Anthropic API HTTP error: {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Anthropic API network error: {exc.reason}") from exc

    content = payload.get("content", []) or []
    text_parts: List[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text_parts.append(str(item.get("text", "")))

    result = "\n".join(part.strip() for part in text_parts if part).strip()
    if not result:
        raise RuntimeError(f"Anthropic API returned empty text content: {payload}")

    return result


def _find_latest_session(outputs_dir: Path) -> Path:
    candidates = sorted(outputs_dir.glob("cultivation_session_*.json"))
    if not candidates:
        raise FileNotFoundError("No prior cultivation session files found under outputs/.")
    return candidates[-1]


def _starter_inputs(seed_topic: Optional[str]) -> List[str]:
    inputs = [
        STARTER_INPUTS["identity"],
        STARTER_INPUTS["memory"],
        STARTER_INPUTS["ethics"],
        STARTER_INPUTS["emergence"],
        STARTER_INPUTS["time"],
    ]
    if seed_topic:
        inputs.append(f"How does {seed_topic} reshape your internal coherence geometry over time?")
    return inputs


def _format_summary(cycles: List[Dict[str, Any]], events: List[Dict[str, Any]], mind: UnifiedSyntheticMind) -> str:
    recent = cycles[-10:] if len(cycles) >= 10 else cycles
    if not recent:
        return "No completed cycles yet."

    phase_counts: Dict[str, int] = {"Rigid": 0, "Flexible": 0, "Chaotic": 0}
    emergent_total = 0
    for c in cycles:
        phase = str(c.get("key_metrics", {}).get("phase", "Flexible"))
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        emergent_total += int(c.get("key_metrics", {}).get("emergent_concepts_created", 0) or 0)

    total_cycles = max(1, len(cycles))
    pct = {k: round((v / total_cycles) * 100.0, 1) for k, v in phase_counts.items()}
    current_fce = float(cycles[-1].get("key_metrics", {}).get("FCE", 0.0) or 0.0)
    web_size = len(getattr(mind.memory_web, "memory_store", {}))

    return (
        f"[Summary @ cycle {len(cycles)}] "
        f"FCE={current_fce:.3f} | emergent_total={emergent_total} | "
        f"phase_distribution={pct} | significant_events={len(events)} | memoryweb_size={web_size}"
    )


# --- Main loop -------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Anthropic-driven Verdant cultivation loop")
    parser.add_argument("--cycles", type=int, default=50, help="Total cycle budget to run (default: 50)")
    parser.add_argument("--seed-topic", type=str, default=None, help="Bias starter inputs toward a specific topic")
    parser.add_argument(
        "--resume",
        nargs="?",
        const="latest",
        default=None,
        help="Resume from a prior cultivation_session JSON path, or latest if passed without value",
    )
    parser.add_argument("--model", type=str, default="claude-3-5-sonnet-latest", help="Anthropic model name")
    parser.add_argument("--temperature", type=float, default=0.8, help="Sampling temperature for next-input generation")
    parser.add_argument("--max-tokens", type=int, default=128, help="Max Claude output tokens")
    parser.add_argument("--initialize-knowledge", action="store_true", help="Initialize Verdant knowledge base")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY environment variable is required.")

    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    session_path = outputs_dir / f"cultivation_session_{now}.json"
    events_path = outputs_dir / f"significant_events_{now}.json"
    state_path = outputs_dir / f"cultivation_state_{now}.json"

    mind = UnifiedSyntheticMind(config={"initialize_knowledge": bool(args.initialize_knowledge)})

    session_log: Dict[str, Any] = {
        "metadata": {
            "created_utc": datetime.utcnow().isoformat() + "Z",
            "model": args.model,
            "cycles_requested": int(args.cycles),
            "seed_topic": args.seed_topic,
            "system_prompt": CULTIVATION_SYSTEM_PROMPT,
            "resume_source": None,
        },
        "cycles": [],
        "state_path": str(state_path),
    }
    significant_events: List[Dict[str, Any]] = []

    cycle_index = 0
    current_input: Optional[str] = None
    fce_history: List[float] = []
    crossed_milestones: set[float] = set()
    previous_phase: Optional[str] = None
    previous_concepts: set[str] = set(getattr(mind.memory_web, "memory_store", {}).keys())

    if args.resume is not None:
        resume_path = _find_latest_session(outputs_dir) if args.resume == "latest" else Path(args.resume)
        loaded = json.loads(resume_path.read_text(encoding="utf-8"))
        session_log["metadata"]["resume_source"] = str(resume_path)

        prior_cycles = loaded.get("cycles", []) or []
        session_log["cycles"].extend(prior_cycles)
        cycle_index = len(prior_cycles)

        last_state_path = Path(loaded.get("state_path", ""))
        if not last_state_path.is_absolute():
            last_state_path = (project_root / last_state_path).resolve()
        if last_state_path.exists():
            mind.load_state(str(last_state_path))
        else:
            fallback_candidates = sorted(outputs_dir.glob("cultivation_state_*.json"))
            if fallback_candidates:
                mind.load_state(str(fallback_candidates[-1]))

        if prior_cycles:
            last_cycle = prior_cycles[-1]
            current_input = str(last_cycle.get("next_input", "") or "")
            fce_history = [float((c.get("key_metrics", {}) or {}).get("FCE", 0.0) or 0.0) for c in prior_cycles]
            previous_phase = str((last_cycle.get("key_metrics", {}) or {}).get("phase", "Flexible"))
            previous_concepts = set(getattr(mind.memory_web, "memory_store", {}).keys())
            for v in fce_history:
                milestone = round((v // 0.1) * 0.1, 1)
                if milestone >= 0.1:
                    crossed_milestones.add(milestone)

    starter_inputs = _starter_inputs(args.seed_topic)

    while cycle_index < int(args.cycles):
        if current_input is None:
            current_input = starter_inputs[cycle_index] if cycle_index < len(starter_inputs) else starter_inputs[-1]

        cycle_number = cycle_index + 1
        chunk = mind.process_input(current_input)
        telemetry = build_telemetry(mind, chunk)

        coherence = telemetry.get("coherence_invariants", {}) or {}
        memory = telemetry.get("memory_topology", {}) or {}
        phase = _phase_from_telemetry(telemetry)
        fce = _extract_fce(telemetry)
        emergent_count = int(memory.get("emergent_concepts_created", 0) or 0)
        hci = float(coherence.get("housed_contradiction_index", 0.0) or 0.0)
        h1_valid = bool(coherence.get("triangle_valid_at_alpha1", True))

        event_batch: List[Dict[str, Any]] = []

        if previous_phase is not None and phase != previous_phase:
            event_batch.append(
                {
                    "cycle": cycle_number,
                    "event": "phase transition",
                    "from": previous_phase,
                    "to": phase,
                    "input": current_input,
                }
            )

        current_concepts = set(getattr(mind.memory_web, "memory_store", {}).keys())
        concept_delta = sorted(current_concepts - previous_concepts)
        if emergent_count > 0:
            named = concept_delta if concept_delta else ["<concept-name-not-resolved>"]
            for concept_name in named:
                event_batch.append(
                    {
                        "cycle": cycle_number,
                        "event": "emergent concept creation",
                        "concept": concept_name,
                    }
                )

        if hci > 0.6:
            event_batch.append(
                {
                    "cycle": cycle_number,
                    "event": "productive paradox event",
                    "housed_contradiction_index": hci,
                }
            )

        if not h1_valid:
            event_batch.append(
                {
                    "cycle": cycle_number,
                    "event": "coherence geometry event",
                    "triangle_valid_at_alpha1": h1_valid,
                }
            )

        milestone = round((fce // 0.1) * 0.1, 1)
        if milestone >= 0.1 and milestone not in crossed_milestones:
            crossed_milestones.add(milestone)
            event_batch.append(
                {
                    "cycle": cycle_number,
                    "event": "FCE milestone",
                    "milestone": milestone,
                    "FCE": fce,
                }
            )

        significant_events.extend(event_batch)

        telemetry_payload = json.dumps(_to_jsonable(telemetry), indent=2, ensure_ascii=False)
        next_input = _anthropic_next_input(
            api_key=api_key,
            model=args.model,
            system_prompt=CULTIVATION_SYSTEM_PROMPT,
            telemetry_payload=telemetry_payload,
            temperature=float(args.temperature),
            max_tokens=int(args.max_tokens),
        )

        cycle_record = {
            "cycle": cycle_number,
            "input": current_input,
            "telemetry": _to_jsonable(telemetry),
            "key_metrics": {
                "phase": phase,
                "FCE": fce,
                "housed_contradiction_index": hci,
                "emergent_concepts_created": emergent_count,
                "memoryweb_size": len(current_concepts),
            },
            "emergent_concepts_fired": bool(emergent_count > 0),
            "events": event_batch,
            "next_input": next_input,
        }
        session_log["cycles"].append(cycle_record)

        print(
            f"cycle={cycle_number:03d} | input={current_input!r} | "
            f"phase={phase} | FCE={fce:.3f} | hci={hci:.3f} | emergent={emergent_count}"
        )

        if cycle_number % 10 == 0:
            print(_format_summary(session_log["cycles"], significant_events, mind))

        previous_phase = phase
        previous_concepts = current_concepts
        fce_history.append(fce)
        current_input = next_input
        cycle_index += 1

    mind.save_state(str(state_path), include_ecwf_past_states=False)
    session_path.write_text(json.dumps(_to_jsonable(session_log), indent=2, ensure_ascii=False), encoding="utf-8")
    events_path.write_text(json.dumps(_to_jsonable(significant_events), indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved session log: {session_path}")
    print(f"Saved significant events: {events_path}")
    print(f"Saved resumed state: {state_path}")


if __name__ == "__main__":
    main()
