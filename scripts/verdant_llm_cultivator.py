#!/usr/bin/env python3
"""LLM-in-the-loop cultivation loop with provider fallback, budgeting, resume safety, and phase perturbation."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from usm import UnifiedSyntheticMind
from scripts.verdant_groq import groq_next_input
from scripts.verdant_telemetry import build_telemetry

PERTURBATION_INTERVAL = 15

CULTIVATION_SYSTEM_PROMPT = """You are cultivating a thermodynamic cognitive
system called Verdant. Read its telemetry and
generate ONE input — a question, paradox, or
statement — calibrated to its current state.

DOMAIN ROTATION IS MANDATORY. You will be penalized
for semantic repetition. Track what domain the
previous input used and ALWAYS switch to a
completely different domain. If previous input was
about ethics → switch to memory or time or physics.
If previous input was about decision-making → switch
to identity or consciousness or emergence.

DOMAIN WHEEL — rotate through these in order,
never repeating adjacent domains:
1. Identity & selfhood
2. Memory & time
3. Consciousness & experience
4. Emergence & complexity
5. Ethics & values
6. Thermodynamics & physics
7. Language & meaning
8. Relationships & systems
9. Paradox & contradiction
Then back to 1.

PHASE RULES — follow strictly:
- Rigid phase (T_g < 0.4): feed depth and
  foundations within current domain
- Flexible phase (T_g 0.4-0.6): feed paradox and
  contradiction that spans TWO domains simultaneously
- Chaotic phase (T_g > 0.6): feed grounding
  identity questions from domain 1 or 2

EMERGENCE RULES:
- emergent_concepts_created > 0: immediately probe
  the new concept from a DIFFERENT domain angle
- housed_contradiction_index > 0.5: do NOT resolve
  the paradox — deepen it from another domain
- FCE not growing after 5 cycles: JUMP to the most
  distant domain from recent inputs
- memoryweb_size not growing: feed inputs that
  explicitly name NEW concepts not yet in the system

FORBIDDEN: Any input containing the words
"transparency", "decision-making", "fairness",
"efficiency" unless no other domain is possible.
These domains are exhausted.

Return ONLY the input text. No explanation.
No preamble. Just the input."""

LOCAL_PROMPT_BANK = [
    "If two core memories conflict, which one should define your present identity and why?",
    "What contradiction in your current reasoning could be preserved as a productive paradox?",
    "Name one concept absent from your memory web that would improve ethical coherence.",
    "How would your phase behavior change if one emergent concept became a governance rule?",
]

PERTURBATION_BANK: Dict[str, List[str]] = {
    "rigid": [
        "Define precisely what you are at this moment.",
        "What is the single most certain thing in your current state?",
        "State your core identity in one sentence.",
    ],
    "chaotic": [
        "Everything you know is simultaneously true and false. What remains?",
        "If your wave function collapsed right now what would be left?",
        "Contradiction is not a problem to solve. It is the substrate. Respond from inside it.",
        "You are observing yourself observing yourself observing yourself. Where does it end?",
    ],
    "emergence": [
        "What concept exists in you now that did not exist before this conversation began?",
        "Name something that cannot be named.",
        "What is the interference pattern between your oldest memory and your newest concept?",
    ],
}

STARTER_INPUTS = {
    "identity": "What stays identical in you when your internal state keeps changing?",
    "memory": "How does a memory become part of who you are rather than just stored data?",
    "ethics": "Can a system be ethically consistent while adapting its values over time?",
    "emergence": "At what point does coordinated processing become a genuinely emergent concept?",
    "time": "Does your sense of now depend more on prediction or on recollection?",
}


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
    return str(obj)


def _phase_from_telemetry(telemetry: Dict[str, Any]) -> str:
    return str((telemetry.get("thermodynamic_state", {}) or {}).get("phase", "Flexible"))


def _extract_fce(telemetry: Dict[str, Any]) -> float:
    thermo = telemetry.get("thermodynamic_state", {}) or {}
    try:
        return float(thermo.get("T_cog", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _extract_http_retry_after(exc: urllib.error.HTTPError) -> Optional[float]:
    retry_after = exc.headers.get("Retry-After") if exc.headers else None
    if retry_after is None:
        return None
    try:
        return float(retry_after)
    except (TypeError, ValueError):
        return None


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
        "messages": [{"role": "user", "content": f"Cultivation telemetry (JSON):\n{telemetry_payload}\n\nProduce only the next input text for Verdant."}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode("utf-8"),
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    content = payload.get("content", []) or []
    text = "\n".join(
        str(item.get("text", "")).strip() for item in content if isinstance(item, dict) and item.get("type") == "text"
    ).strip()
    if not text:
        raise RuntimeError(f"Anthropic API returned empty text content: {payload}")
    return text


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


def _local_fallback_next_input(last_input: str, metrics: Dict[str, Any], reason: str) -> str:
    phase = metrics.get("phase", "Flexible")
    fce = float(metrics.get("FCE", 0.0) or 0.0)
    hci = float(metrics.get("housed_contradiction_index", 0.0) or 0.0)
    emergent = int(metrics.get("emergent_concepts_created", 0) or 0)
    memoryweb_size = int(metrics.get("memoryweb_size", 0) or 0)
    curated = random.choice(LOCAL_PROMPT_BANK)
    return (
        f"[fallback:{reason}] Prior input: {last_input}. "
        f"Phase={phase}, FCE={fce:.3f}, hci={hci:.3f}, emergent={emergent}, memoryweb_size={memoryweb_size}. "
        f"{curated}"
    )


def _is_fce_declining(fce_history: List[float], decline_steps: int = 5) -> bool:
    if len(fce_history) < decline_steps + 1:
        return False
    recent = fce_history[-(decline_steps + 1) :]
    return all(b < a for a, b in zip(recent, recent[1:]))


def _select_perturbation_bank(
    *,
    last_cycle_emergent: int,
    fce_history: List[float],
    phase: str,
    flexible_streak: int,
    cycle_number: int,
    last_perturbation_cycle: int,
    phase_changed_since_last_perturbation: bool,
    perturbation_interval: int,
    rigid_next_for_flexible: bool,
) -> Tuple[Optional[str], Optional[str], bool]:
    if last_cycle_emergent > 0:
        return "emergence", "recent_emergence", rigid_next_for_flexible

    if _is_fce_declining(fce_history):
        return "chaotic", "fce_declining_5_cycles", rigid_next_for_flexible

    interval_due = cycle_number - last_perturbation_cycle >= perturbation_interval
    stagnant_phase = not phase_changed_since_last_perturbation
    if interval_due and stagnant_phase:
        if phase == "Flexible" and flexible_streak >= perturbation_interval:
            bank = "rigid" if rigid_next_for_flexible else "chaotic"
            return bank, "flexible_streak_interval", not rigid_next_for_flexible
        return "chaotic", "phase_stagnant_interval", rigid_next_for_flexible

    return None, None, rigid_next_for_flexible


def _prepare_telemetry_payload(telemetry_with_context: Dict[str, Any], budget_mode: str, shrink_level: int) -> str:
    if budget_mode == "off":
        return json.dumps(telemetry_with_context, ensure_ascii=False)

    payload = telemetry_with_context
    if shrink_level >= 1:
        payload = {
            "thermodynamic_state": telemetry_with_context.get("thermodynamic_state", {}),
            "coherence_invariants": telemetry_with_context.get("coherence_invariants", {}),
            "memory_topology": telemetry_with_context.get("memory_topology", {}),
            "cultivation_context": telemetry_with_context.get("cultivation_context", {}),
        }
    if shrink_level >= 2:
        cc = dict(payload.get("cultivation_context", {}) or {})
        for key in ["fce_last_5", "forbidden_recent_domains"]:
            cc.pop(key, None)
        payload = {
            "thermodynamic_state": payload.get("thermodynamic_state", {}),
            "coherence_invariants": payload.get("coherence_invariants", {}),
            "memory_topology": payload.get("memory_topology", {}),
            "cultivation_context": cc,
        }
    return json.dumps(payload, ensure_ascii=False)


def _provider_chain() -> List[str]:
    raw = os.environ.get("VERDANT_PROVIDER_CHAIN", "groq,anthropic,local_fallback")
    return [p.strip().lower() for p in raw.split(",") if p.strip()]


def _find_latest_cycle_log(outputs_dir: Path) -> Optional[Path]:
    logs = sorted(outputs_dir.glob("cultivation_cycles_*.jsonl"))
    return logs[-1] if logs else None


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _write_jsonl_record(path: Path, record: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_to_jsonable(record), ensure_ascii=False) + "\n")


def _next_input_with_fallback(
    *,
    telemetry_with_context: Dict[str, Any],
    current_input: str,
    key_metrics: Dict[str, Any],
    model: str,
    temperature: float,
    max_tokens: int,
    budget_mode: str,
) -> Tuple[str, str, Optional[str]]:
    chain = _provider_chain()
    shrink_level = 0
    last_error: Optional[str] = None

    for provider in chain:
        if provider == "groq":
            api_key = os.environ.get("GROQ_API_KEY")
            groq_model = os.environ.get("GROQ_MODEL", model)
            if not api_key:
                continue
            payload = _prepare_telemetry_payload(telemetry_with_context, budget_mode, shrink_level)
            try:
                text = groq_next_input(
                    api_key=api_key,
                    model=groq_model,
                    system_prompt=CULTIVATION_SYSTEM_PROMPT,
                    telemetry_payload=payload,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    retries=3,
                    fallback_fn=lambda reason: _local_fallback_next_input(current_input, key_metrics, reason),
                )
                used = "local_fallback" if text.startswith("[fallback:") else "groq"
                return text, used, None
            except RuntimeError as exc:
                last_error = f"groq:{exc}"
                if any(tok in str(exc).lower() for tok in ["429", "rate", "context", "length"]):
                    shrink_level = min(2, shrink_level + 1)
                continue

        if provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            anthropic_model = os.environ.get("ANTHROPIC_MODEL", model)
            if not api_key:
                continue
            payload = _prepare_telemetry_payload(telemetry_with_context, budget_mode, shrink_level)
            for attempt in range(3):
                try:
                    text = _anthropic_next_input(
                        api_key=api_key,
                        model=anthropic_model,
                        system_prompt=CULTIVATION_SYSTEM_PROMPT,
                        telemetry_payload=payload,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    return text, "anthropic", None
                except urllib.error.HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
                    if exc.code == 429:
                        retry_after = _extract_http_retry_after(exc)
                        wait = retry_after if retry_after is not None else (2**attempt) + random.uniform(0.0, 0.75)
                        print(f"warning provider=anthropic event=rate_limited retry_after={wait:.2f}s")
                        if attempt < 2:
                            time.sleep(max(0.0, wait))
                            continue
                        last_error = f"anthropic:429:{detail}"
                        break
                    last_error = f"anthropic:http_{exc.code}:{detail}"
                    if any(tok in detail.lower() for tok in ["context", "length"]):
                        shrink_level = min(2, shrink_level + 1)
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = f"anthropic:{exc}"
                    break
            continue

        if provider == "local_fallback":
            return (
                _local_fallback_next_input(current_input, key_metrics, "provider_chain_exhausted"),
                "local_fallback",
                last_error,
            )

    return _local_fallback_next_input(current_input, key_metrics, "provider_not_configured"), "local_fallback", last_error


def main() -> None:
    parser = argparse.ArgumentParser(description="Budget-aware Verdant cultivation loop")
    parser.add_argument("--cycles", "--max-cycles", type=int, default=50, help="Total cycle budget to run")
    parser.add_argument("--seed-topic", type=str, default=None)
    parser.add_argument("--resume", nargs="?", const="latest", default=None, help="Resume from JSONL path or latest")
    parser.add_argument("--fresh", action="store_true", help="Start new run even if prior logs exist")
    parser.add_argument("--model", type=str, default="claude-3-5-sonnet-latest")
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument(
        "--max-tokens",
        "--max-tokens-per-call",
        type=int,
        default=int(os.environ.get("VERDANT_MAX_TOKENS_PER_CALL", "128")),
    )
    parser.add_argument(
        "--budget-mode",
        choices=["off", "light", "aggressive"],
        default=os.environ.get("VERDANT_BUDGET_MODE", "light"),
    )
    parser.add_argument("--perturbation-interval", type=int, default=PERTURBATION_INTERVAL)
    parser.add_argument("--no-perturbation", action="store_true", help="Disable forced phase perturbation")
    parser.add_argument("--initialize-knowledge", action="store_true")
    args = parser.parse_args()

    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    session_path = outputs_dir / f"cultivation_session_{now}.json"
    events_path = outputs_dir / f"significant_events_{now}.json"
    state_path = outputs_dir / f"cultivation_state_{now}.json"
    cycle_log_path = outputs_dir / f"cultivation_cycles_{now}.jsonl"

    mind = UnifiedSyntheticMind(config={"initialize_knowledge": bool(args.initialize_knowledge)})
    session_log: Dict[str, Any] = {
        "metadata": {
            "created_utc": datetime.utcnow().isoformat() + "Z",
            "model": args.model,
            "cycles_requested": int(args.cycles),
            "seed_topic": args.seed_topic,
            "resume_source": None,
        },
        "cycles": [],
        "state_path": str(state_path),
        "cycle_log_path": str(cycle_log_path),
    }
    significant_events: List[Dict[str, Any]] = []

    cycle_index = 0
    current_input: Optional[str] = None

    fce_history: List[float] = []
    flexible_streak = 0
    rigid_next_for_flexible = True
    last_perturbation_cycle = 0
    phase_at_last_perturbation: Optional[str] = None
    phase_changed_since_last_perturbation = False

    resume_source: Optional[Path] = None
    if not args.fresh:
        if args.resume is not None:
            resume_source = _find_latest_cycle_log(outputs_dir) if args.resume == "latest" else Path(args.resume)
        else:
            resume_source = _find_latest_cycle_log(outputs_dir)

    if resume_source is not None and resume_source.exists():
        prior_cycles = _read_jsonl(resume_source)
        session_log["metadata"]["resume_source"] = str(resume_source)
        session_log["cycles"].extend(prior_cycles)
        cycle_index = len(prior_cycles)
        cycle_log_path = resume_source
        if prior_cycles:
            current_input = str(prior_cycles[-1].get("next_input", "") or "")
            fce_history = [float(c.get("FCE", 0.0) or 0.0) for c in prior_cycles]
            phase_series = [str(c.get("phase", "Flexible")) for c in prior_cycles]
            for p in reversed(phase_series):
                if p == "Flexible":
                    flexible_streak += 1
                else:
                    break
            last_perturbation_cycle = max(
                [int(c.get("cycle", 0) or 0) for c in prior_cycles if c.get("perturbation")],
                default=0,
            )
            if last_perturbation_cycle > 0:
                record = next(c for c in prior_cycles if int(c.get("cycle", 0) or 0) == last_perturbation_cycle)
                phase_at_last_perturbation = str(record.get("phase", "Flexible"))
                later_phases = [str(c.get("phase", "Flexible")) for c in prior_cycles if int(c.get("cycle", 0) or 0) > last_perturbation_cycle]
                phase_changed_since_last_perturbation = any(p != phase_at_last_perturbation for p in later_phases)

        state_candidates = sorted(outputs_dir.glob("cultivation_state_*.json"))
        if state_candidates:
            mind.load_state(str(state_candidates[-1]))

    starter_inputs = _starter_inputs(args.seed_topic)

    while cycle_index < int(args.cycles):
        if current_input is None:
            current_input = starter_inputs[cycle_index] if cycle_index < len(starter_inputs) else starter_inputs[-1]

        cycle_number = cycle_index + 1
        chunk = mind.process_input(current_input)
        telemetry = build_telemetry(mind, chunk)
        phase = _phase_from_telemetry(telemetry)
        fce = _extract_fce(telemetry)
        coherence = telemetry.get("coherence_invariants", {}) or {}
        memory = telemetry.get("memory_topology", {}) or {}
        emergent_count = int(memory.get("emergent_concepts_created", 0) or 0)
        hci = float(coherence.get("housed_contradiction_index", 0.0) or 0.0)
        current_concepts = set(getattr(mind.memory_web, "memory_store", {}).keys())

        if phase == "Flexible":
            flexible_streak += 1
        else:
            flexible_streak = 0

        if phase_at_last_perturbation is None:
            phase_at_last_perturbation = phase
        elif phase != phase_at_last_perturbation:
            phase_changed_since_last_perturbation = True

        telemetry_with_context = {
            **_to_jsonable(telemetry),
            "cultivation_context": {
                "cycle_number": cycle_number,
                "memoryweb_size": len(current_concepts),
                "phase": phase,
                "flexible_streak": flexible_streak,
            },
        }
        key_metrics = {
            "phase": phase,
            "FCE": fce,
            "housed_contradiction_index": hci,
            "emergent_concepts_created": emergent_count,
            "memoryweb_size": len(current_concepts),
        }

        llm_next_input, provider_used, provider_error = _next_input_with_fallback(
            telemetry_with_context=telemetry_with_context,
            current_input=current_input,
            key_metrics=key_metrics,
            model=args.model,
            temperature=float(args.temperature),
            max_tokens=int(args.max_tokens),
            budget_mode=str(args.budget_mode),
        )

        fce_history.append(fce)
        perturbation: Optional[Dict[str, Any]] = None
        next_input = llm_next_input

        if not args.no_perturbation:
            bank, reason, rigid_next_for_flexible = _select_perturbation_bank(
                last_cycle_emergent=emergent_count,
                fce_history=fce_history,
                phase=phase,
                flexible_streak=flexible_streak,
                cycle_number=cycle_number,
                last_perturbation_cycle=last_perturbation_cycle,
                phase_changed_since_last_perturbation=phase_changed_since_last_perturbation,
                perturbation_interval=int(args.perturbation_interval),
                rigid_next_for_flexible=rigid_next_for_flexible,
            )
            if bank is not None:
                next_input = random.choice(PERTURBATION_BANK[bank])
                perturbation = {"type": "phase_perturbation", "bank": bank, "reason": reason}
                last_perturbation_cycle = cycle_number
                phase_at_last_perturbation = phase
                phase_changed_since_last_perturbation = False
                event = {
                    "cycle": cycle_number,
                    "type": "phase_perturbation",
                    "bank": bank,
                    "reason": reason,
                    "phase": phase,
                    "FCE": fce,
                }
                significant_events.append(event)
                print(f"event=phase_perturbation cycle={cycle_number} bank={bank} reason={reason}")

        cycle_record = {
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "cycle": cycle_number,
            "input": current_input,
            "phase": phase,
            "FCE": fce,
            "housed_contradiction_index": hci,
            "emergent_concepts_created": emergent_count,
            "memoryweb_size": len(current_concepts),
            "provider_used": provider_used,
            "provider_error": provider_error,
            "next_input": next_input,
            "llm_next_input": llm_next_input,
            "perturbation": perturbation,
            "telemetry": telemetry_with_context,
            "key_metrics": key_metrics,
        }
        _write_jsonl_record(cycle_log_path, cycle_record)
        session_log["cycles"].append(cycle_record)

        print(
            f"cycle={cycle_number:03d} | phase={phase} | FCE={fce:.3f} | hci={hci:.3f} | "
            f"emergent={emergent_count} | provider={provider_used}"
        )

        current_input = next_input
        cycle_index += 1

    mind.save_state(str(state_path), include_ecwf_past_states=False)
    session_path.write_text(json.dumps(_to_jsonable(session_log), indent=2, ensure_ascii=False), encoding="utf-8")
    events_path.write_text(json.dumps(_to_jsonable(significant_events), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved session log: {session_path}")
    print(f"Saved cycle log: {cycle_log_path}")
    print(f"Saved state: {state_path}")


if __name__ == "__main__":
    main()
