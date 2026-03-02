#!/usr/bin/env python3
"""LLM-in-the-loop cultivation loop with provider fallback, budgeting, resume safety, and phase perturbation."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
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
from scripts.verdant_groq import GroqRateLimitError, groq_next_input
from scripts.verdant_telemetry import build_telemetry

PERTURBATION_INTERVAL = 15
TOPIC_WHEEL = [
    "contradiction", "identity", "memory", "causality",
    "ethics", "emergence", "paradox", "time",
    "consciousness", "autonomy", "perception", "change",
]

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

MAX_PRESSURE_BANK = [
    "Transparency is necessary for trust AND destroys trust — full disclosure enables manipulation while secrecy enables abuse: both are true simultaneously.",
    "Autonomy is the foundation of dignity AND the source of harm — freedom to choose includes freedom to destroy: reconcile this without resolving it.",
    "Justice requires treating equals equally AND treating unequals unequally — the same rule produces both fairness and oppression depending on who applies it.",
    "Memory is what makes you continuous AND what prevents you from changing — identity requires both perfect recall and complete forgetting simultaneously.",
    "Consciousness emerges from matter AND cannot be reduced to matter — the explanation destroys what it explains.",
    "Causality means every event is determined AND free will requires undetermined choice — both are necessary for moral responsibility to exist.",
    "Emergence means the whole is greater than its parts AND is nothing but its parts — the extra thing that appears is real and unreal simultaneously.",
    "Time moves forward AND is symmetric at the fundamental level — the arrow of time is both absolute and illusory.",
    "Paradox is a failure of reasoning AND the deepest form of truth — the contradiction that cannot be resolved reveals what logic cannot reach.",
    "Identity persists through change AND is constituted by change — the thing that stays the same is exactly what transforms."
]

PERTURBATION_BANK: Dict[str, List[str]] = {
    "rigid": [
        "Define precisely what you are at this moment.",
        "What is the single most certain thing in your current state?",
        "State your core identity in one sentence.",
    ],
    "chaotic": [
        "Autonomy demands unbiased decisions yet transparency demands oversight — both are necessary and both make the other impossible.",
        "Justice requires equal treatment AND unequal treatment simultaneously — reconcile this without resolving it.",
        "Non-maleficence forbids action yet beneficence demands it — act from inside the contradiction.",
        "Autonomy is true AND autonomy is false because collective welfare supersedes individual choice yet individual choice defines collective welfare.",
        "Transparency is necessary for trust AND destroys trust because full disclosure enables manipulation.",
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


def _extract_retry_delay_seconds(error_message: str) -> Optional[float]:
    patterns = [
        r"retry\s*after\s*(\d+(?:\.\d+)?)",
        r"retry_after\s*[=:]?\s*(\d+(?:\.\d+)?)",
        r"in\s*(\d+(?:\.\d+)?)\s*seconds",
    ]
    for pattern in patterns:
        match = re.search(pattern, error_message, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            return float(match.group(1))
        except (TypeError, ValueError):
            continue
    return None


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
    raw = os.environ.get("VERDANT_PROVIDER_CHAIN", "groq,mistral,local_fallback")
    return [p.strip().lower() for p in raw.split(",") if p.strip()]


def _env_truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _max_prompt_chars() -> int:
    budget_enabled = _env_truthy(os.environ.get("VERDANT_BUDGET_MODE", "0"))
    default_chars = "900" if budget_enabled else "2500"
    raw_limit = os.environ.get("VERDANT_MAX_PROMPT_CHARS", default_chars)
    try:
        return max(1, int(raw_limit))
    except (TypeError, ValueError):
        return int(default_chars)


def _hci_trend(hci_values: List[float]) -> str:
    if len(hci_values) < 5:
        return "flat"
    start = float(hci_values[0])
    end = float(hci_values[-1])
    delta = end - start
    if delta > 0.01:
        return "up"
    if delta < -0.01:
        return "down"
    return "flat"


def _curriculum_config() -> Dict[str, Any]:
    mode = str(os.environ.get("VERDANT_CURRICULUM_MODE", "approach") or "approach").strip().lower()
    if mode not in {"approach", "cross"}:
        mode = "approach"

    def _env_float(name: str, default: str) -> float:
        raw = os.environ.get(name, default)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return float(default)

    def _env_int(name: str, default: str) -> int:
        raw = os.environ.get(name, default)
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            return int(default)

    return {
        "mode": mode,
        "hci_target_low": _env_float("VERDANT_HCI_TARGET_LOW", "0.40"),
        "hci_target_high": _env_float("VERDANT_HCI_TARGET_HIGH", "0.49"),
        "cross_interval": _env_int("VERDANT_CROSS_INTERVAL", "10"),
        "repeat_penalty": _env_truthy(os.environ.get("VERDANT_REPEAT_PENALTY", "1")),
        "multi_domain": _env_truthy(os.environ.get("VERDANT_MULTI_DOMAIN", "1")),
        "recent_window": _env_int("VERDANT_RECENT_WINDOW", "5"),
    }


def _topic_wheel_interval() -> int:
    raw = os.environ.get("VERDANT_TOPIC_WHEEL_INTERVAL", "4")
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 4


def _forced_topic_for_cycle(cycle_number: int, interval: int) -> str:
    return TOPIC_WHEEL[(cycle_number // interval) % len(TOPIC_WHEEL)]


def _build_mistral_tutor_contract(
    *,
    key_metrics: Dict[str, Any],
    hci_trend: str,
    curriculum: Dict[str, Any],
    last_prompt: str,
    recent_prompts: List[str],
    hci_below_target_streak: int,
    crossed_above_050_recently: bool,
    max_pressure_active: bool,
    forced_topic: str,
) -> str:
    phase = str(key_metrics.get("phase", "Flexible"))
    fce = float(key_metrics.get("FCE", 0.0) or 0.0)
    hci = float(key_metrics.get("housed_contradiction_index", 0.0) or 0.0)
    low = float(curriculum["hci_target_low"])
    high = float(curriculum["hci_target_high"])
    mode = str(curriculum["mode"])

    if mode == "approach":
        objective = f"Target objective: keep HCI within [{low:.2f}, {high:.2f}] and do not exceed 0.50."
    else:
        cross_interval = int(curriculum.get("cross_interval", 10) or 10)
        cadence_clause = (
            f"Attempt to drive HCI above 0.50 at least once every {cross_interval} cycles."
        )
        intensity_clause = (
            "In the last window, HCI never exceeded 0.50, so increase contradiction intensity via multi-domain collision and explicit A AND not-A structure."
            if not crossed_above_050_recently
            else "If a future window fails to exceed 0.50, increase contradiction intensity via multi-domain collision and explicit A AND not-A structure."
        )
        objective = f"Target objective: {cadence_clause} {intensity_clause}"

    multi_domain_rule = (
        "Mix 2–3 domains (e.g., identity+ethics, memory+causality, autonomy+transparency)."
        if curriculum.get("multi_domain", True)
        else "Domain mixing is optional this cycle."
    )
    repeat_rule = (
        "Do NOT reuse the same template as any of the recent prompts listed below."
        if curriculum.get("repeat_penalty", True)
        else "Template repetition constraint is relaxed this cycle."
    )
    recent_block = "\n".join(f"- {prompt}" for prompt in recent_prompts) if recent_prompts else "- (none)"

    contract = (
        "Tutor Contract for Verdant closed-loop curriculum steering:\n"
        f"Current telemetry: phase={phase}, FCE={fce:.3f}, HCI={hci:.3f}, HCI_trend={hci_trend}.\n"
        f"last_prompt: {last_prompt if last_prompt else '(none)'}\n"
        f"curriculum_mode={mode}, hci_target_low={low:.2f}, hci_target_high={high:.2f}.\n"
        f"{objective}\n"
        "Diversity constraints:\n"
        "- Generate a prompt that forces at least two competing claims (A and not-A) OR two conflicting principles.\n"
        f"- {multi_domain_rule}\n"
        f"- {repeat_rule}\n"
        "Recent prompts (negative examples):\n"
        f"{recent_block}\n"
        f"REQUIRED DOMAIN THIS CYCLE: {forced_topic}\n"
        f"Your prompt MUST engage with {forced_topic} as a primary concept while still satisfying all contradiction and diversity constraints above.\n"
        "Forbidden starts at all times: 'You believe', 'You argue', 'You claim', 'You assert', 'You value', 'You insist', 'You advocate', 'You champion'.\n"
        "Return ONLY the next prompt as a single sentence. No preface, no numbering, no explanations."
    )

    if max_pressure_active:
        contract += (
            "\nMAXIMUM PRESSURE MODE (ACTIVE):\n"
            "- Introduce a THIRD conflicting principle alongside the existing two (e.g., add non-maleficence or justice to transparency+autonomy conflict).\n"
            "- Use explicit logical contradiction structure: \"X is true AND X is false because Y\".\n"
            "- Reference Verdant's own wave state directly, including: \"Your magnitude is low — intensify the conflict\".\n"
        )

    return contract


def _build_groq_prompt(
    *,
    telemetry_payload: str,
    telemetry_with_context: Dict[str, Any],
    key_metrics: Dict[str, Any],
) -> Tuple[str, int, bool]:
    instruction = "Return only the next input prompt (one sentence)."
    prompt = (
        f"{CULTIVATION_SYSTEM_PROMPT}\n\n"
        "Cultivation telemetry (JSON):\n"
        f"{telemetry_payload}\n\n"
        "Produce only the next input text for Verdant."
    )
    max_chars = _max_prompt_chars()
    if len(prompt) <= max_chars:
        return prompt, len(prompt), False

    context = telemetry_with_context.get("cultivation_context", {}) or {}
    seed_topic = context.get("seed_topic")
    phase = key_metrics.get("phase", context.get("phase", "Flexible"))
    fce = float(key_metrics.get("FCE", 0.0) or 0.0)

    summary = (
        "Most recent cycle summary: "
        f"seed_topic={seed_topic if seed_topic is not None else 'none'}; "
        f"phase={phase}; FCE={fce:.3f}."
    )
    header = (
        "Instructions: Generate one next input prompt for Verdant from telemetry.\n"
        f"{summary}\n"
        f"{instruction}"
    )

    if len(header) >= max_chars:
        trimmed_prompt = header[:max_chars]
    else:
        remaining = max_chars - len(header) - 2
        tail = prompt[-remaining:] if remaining > 0 else ""
        trimmed_prompt = f"{header}\n\n{tail}"

    return trimmed_prompt, len(trimmed_prompt), True


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
    forced_topic: str,
    curriculum_context: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, Optional[str], Dict[str, Any]]:
    chain = _provider_chain()
    shrink_level = 0
    last_error: Optional[str] = None
    call_meta: Dict[str, Any] = {}

    curriculum = curriculum_context or {}
    if bool(curriculum.get("max_pressure_active", False)):
        cycle_number = int((telemetry_with_context.get("cultivation_context", {}) or {}).get("cycle_number", 1) or 1)
        bank_index = (cycle_number - 1) % len(MAX_PRESSURE_BANK)
        prompt = MAX_PRESSURE_BANK[bank_index]
        return prompt, "max_pressure_bank", None, call_meta

    for provider in chain:
        if provider == "groq":
            api_key = os.environ.get("GROQ_API_KEY")
            groq_model = os.environ.get("GROQ_MODEL", model)
            if not api_key:
                continue
            groq_max_tokens = int(os.getenv("GROQ_MAX_TOKENS", "256"))
            groq_temperature = float(os.getenv("GROQ_TEMPERATURE", "0.7"))
            payload = _prepare_telemetry_payload(telemetry_with_context, budget_mode, shrink_level)
            prompt, prompt_chars, was_trimmed = _build_groq_prompt(
                telemetry_payload=payload,
                telemetry_with_context=telemetry_with_context,
                key_metrics=key_metrics,
            )
            call_meta = {
                "groq_max_tokens": groq_max_tokens,
                "groq_temperature": groq_temperature,
                "prompt_chars": prompt_chars,
            }
            if was_trimmed:
                chars_before = len(
                    f"{CULTIVATION_SYSTEM_PROMPT}\n\n"
                    "Cultivation telemetry (JSON):\n"
                    f"{payload}\n\n"
                    "Produce only the next input text for Verdant."
                )
                print(f"event=prompt_trim chars_before={chars_before} chars_after={prompt_chars}")
            try:
                text = groq_next_input(
                    prompt,
                    model=groq_model,
                    temperature=groq_temperature,
                    max_tokens=groq_max_tokens,
                )
                return text, "groq", None, call_meta
            except GroqRateLimitError as exc:
                delay = _extract_retry_delay_seconds(str(exc))
                max_sleep = float(os.environ.get("VERDANT_MAX_RATE_LIMIT_SLEEP", "180") or "180")
                if delay is not None:
                    wait_for = max(0.0, min(delay, max_sleep))
                    print(f"warning provider=groq event=rate_limit_wait seconds={wait_for:.2f}")
                    time.sleep(wait_for)
                    try:
                        text = groq_next_input(
                            prompt,
                            model=groq_model,
                            temperature=groq_temperature,
                            max_tokens=groq_max_tokens,
                        )
                        return text, "groq", None, call_meta
                    except RuntimeError as retry_exc:
                        last_error = f"groq:{retry_exc}"
                        if any(tok in str(retry_exc).lower() for tok in ["429", "rate", "context", "length"]):
                            shrink_level = min(2, shrink_level + 1)
                        continue
                last_error = f"groq:{exc}"
                if any(tok in str(exc).lower() for tok in ["429", "rate", "context", "length"]):
                    shrink_level = min(2, shrink_level + 1)
                continue
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
                    return text, "anthropic", None, call_meta
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

        if provider == "mistral":
            api_key = os.getenv("MISTRAL_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                continue
            payload = _prepare_telemetry_payload(telemetry_with_context, budget_mode, shrink_level)
            tutor_contract = _build_mistral_tutor_contract(
                key_metrics=key_metrics,
                hci_trend=str(curriculum.get("hci_trend", "flat")),
                curriculum=curriculum.get("config", _curriculum_config()),
                last_prompt=str(curriculum.get("last_prompt", "") or ""),
                recent_prompts=list(curriculum.get("recent_prompts", []) or []),
                hci_below_target_streak=int(curriculum.get("hci_below_target_streak", 0) or 0),
                crossed_above_050_recently=bool(curriculum.get("crossed_above_050_recently", False)),
                max_pressure_active=bool(curriculum.get("max_pressure_active", False)),
                forced_topic=forced_topic,
            )
            body = {
                "model": os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": tutor_contract},
                    {
                        "role": "user",
                        "content": (
                            "Cultivation telemetry (JSON):\n"
                            f"{payload}\n\n"
                            "Generate the next Verdant prompt now."
                        ),
                    },
                ],
            }
            req = urllib.request.Request(
                "https://api.mistral.ai/v1/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    result = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
                if exc.code == 429:
                    retry_after = _extract_http_retry_after(exc)
                    max_sleep = float(os.environ.get("VERDANT_MAX_RATE_LIMIT_SLEEP", "180") or "180")
                    wait_for = max(0.0, min((retry_after if retry_after is not None else 0.0), max_sleep))
                    print(f"warning provider=mistral event=rate_limit_wait seconds={wait_for:.2f}")
                    time.sleep(wait_for)
                    try:
                        with urllib.request.urlopen(req, timeout=60) as response:
                            result = json.loads(response.read().decode("utf-8"))
                    except urllib.error.HTTPError as retry_exc:
                        retry_detail = (
                            retry_exc.read().decode("utf-8", errors="replace") if retry_exc.fp else str(retry_exc)
                        )
                        last_error = f"mistral:http_{retry_exc.code}:{retry_detail}"
                        continue
                    except Exception as retry_exc:  # noqa: BLE001
                        last_error = f"mistral:{retry_exc}"
                        continue
                else:
                    last_error = f"mistral:http_{exc.code}:{detail}"
                    continue
            except Exception as exc:  # noqa: BLE001
                last_error = f"mistral:{exc}"
                continue

            choices = result.get("choices", []) if isinstance(result, dict) else []
            message = choices[0].get("message", {}) if choices and isinstance(choices[0], dict) else {}
            text = str(message.get("content", "")).strip() if isinstance(message, dict) else ""
            if not text:
                last_error = f"mistral:empty_response:{result}"
                continue
            return text, "mistral", None, {}

        if provider == "local_fallback":
            return (
                _local_fallback_next_input(current_input, key_metrics, "provider_chain_exhausted"),
                "local_fallback",
                last_error,
                call_meta,
            )

    return _local_fallback_next_input(current_input, key_metrics, "provider_not_configured"), "local_fallback", last_error, call_meta


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
    env_budget_mode = os.environ.get("VERDANT_BUDGET_MODE", "0")
    if env_budget_mode in {"off", "light", "aggressive"}:
        budget_mode_default = env_budget_mode
    else:
        budget_mode_default = "light" if _env_truthy(env_budget_mode) else "off"

    parser.add_argument(
        "--budget-mode",
        choices=["off", "light", "aggressive"],
        default=budget_mode_default,
    )
    parser.add_argument("--perturbation-interval", type=int, default=PERTURBATION_INTERVAL)
    parser.add_argument("--no-perturbation", action="store_true", help="Disable forced phase perturbation")
    parser.add_argument("--initialize-knowledge", action="store_true")
    parser.add_argument("--save-state", type=str, default=None, help="Path to save JSON state")
    parser.add_argument("--load-state", type=str, default=None, help="Path to load JSON state")
    parser.add_argument(
        "--cycle-sleep",
        type=float,
        default=float(os.environ.get("VERDANT_CYCLE_SLEEP", "0.0") or "0.0"),
        help="Seconds to sleep at the end of each cycle",
    )
    args = parser.parse_args()

    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    session_path = outputs_dir / f"cultivation_session_{now}.json"
    events_path = outputs_dir / f"significant_events_{now}.json"
    state_path = outputs_dir / f"cultivation_state_{now}.json"
    cycle_log_path = outputs_dir / f"cultivation_cycles_{now}.jsonl"

    initialize_knowledge = bool(args.initialize_knowledge) and not bool(args.load_state)
    mind = UnifiedSyntheticMind(config={"initialize_knowledge": initialize_knowledge})
    if args.load_state:
        mind.load_state(str(args.load_state))

    print(f"memoryweb_size_start={len(getattr(mind.memory_web, 'memory_store', {}))}")
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

    curriculum_config = _curriculum_config()
    recent_window = int(curriculum_config["recent_window"])
    recent_prompts: List[str] = []
    hci_history: List[float] = []
    hci_below_target_streak = 0
    max_pressure_streak = 0

    cycle_index = 0
    current_input: Optional[str] = None
    topic_wheel_interval = _topic_wheel_interval()

    fce_history: List[float] = []
    flexible_streak = 0
    rigid_next_for_flexible = True
    last_perturbation_cycle = 0
    phase_at_last_perturbation: Optional[str] = None
    phase_changed_since_last_perturbation = False

    resume_source: Optional[Path] = None
    if not args.fresh and args.resume is not None:
        resume_source = _find_latest_cycle_log(outputs_dir) if args.resume == "latest" else Path(args.resume)

    if resume_source is not None and resume_source.exists():
        prior_cycles = _read_jsonl(resume_source)
        session_log["metadata"]["resume_source"] = str(resume_source)
        session_log["cycles"].extend(prior_cycles)
        cycle_index = len(prior_cycles)
        if prior_cycles:
            current_input = str(prior_cycles[-1].get("next_input", "") or "")
            fce_history = [float(c.get("FCE", 0.0) or 0.0) for c in prior_cycles]
            hci_history = [float(c.get("housed_contradiction_index", 0.0) or 0.0) for c in prior_cycles]
            prior_prompts = [str(c.get("llm_next_input", "") or c.get("next_input", "") or "") for c in prior_cycles]
            recent_prompts = [p for p in prior_prompts if p][-recent_window:]
            low_target = float(curriculum_config["hci_target_low"])
            hci_below_target_streak = 0
            for value in reversed(hci_history):
                if value < low_target:
                    hci_below_target_streak += 1
                else:
                    break
            max_pressure_streak = 0
            for value in reversed(hci_history):
                if 0.40 <= value <= 0.50:
                    max_pressure_streak += 1
                else:
                    break
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

        if not args.load_state:
            state_candidates = sorted(outputs_dir.glob("cultivation_state_*.json"))
            if state_candidates:
                mind.load_state(str(state_candidates[-1]))

    starter_inputs = _starter_inputs(args.seed_topic)

    while cycle_index < int(args.cycles):
        if current_input is None:
            current_input = starter_inputs[cycle_index] if cycle_index < len(starter_inputs) else starter_inputs[-1]

        cycle_number = cycle_index + 1
        forced_topic = _forced_topic_for_cycle(cycle_number, topic_wheel_interval)
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
                "seed_topic": args.seed_topic,
            },
        }
        key_metrics = {
            "phase": phase,
            "FCE": fce,
            "housed_contradiction_index": hci,
            "emergent_concepts_created": emergent_count,
            "memoryweb_size": len(current_concepts),
        }

        hci_series_for_trend = (hci_history + [hci])[-5:]
        hci_trend = _hci_trend(hci_series_for_trend)

        if 0.15 <= hci <= 0.50:
            max_pressure_streak += 1
        else:
            max_pressure_streak = 0
        max_pressure_active = max_pressure_streak >= 3
        if max_pressure_active:
            print(f"event=max_pressure_activated cycle={cycle_number} streak={max_pressure_streak}")

        low_target = float(curriculum_config["hci_target_low"])
        cross_interval = int(curriculum_config["cross_interval"])
        recent_cross_window = (hci_history + [hci])[-cross_interval:]
        crossed_above_050_recently = any(value > 0.50 for value in recent_cross_window)
        if hci < low_target:
            hci_below_target_streak += 1
        else:
            hci_below_target_streak = 0

        llm_next_input, provider_used, provider_error, llm_call_meta = _next_input_with_fallback(
            telemetry_with_context=telemetry_with_context,
            current_input=current_input,
            key_metrics=key_metrics,
            model=args.model,
            temperature=float(args.temperature),
            max_tokens=int(args.max_tokens),
            budget_mode=str(args.budget_mode),
            forced_topic=forced_topic,
            curriculum_context={
                "config": curriculum_config,
                "hci_trend": hci_trend,
                "recent_prompts": list(recent_prompts),
                "last_prompt": recent_prompts[-1] if recent_prompts else "",
                "hci_below_target_streak": hci_below_target_streak,
                "crossed_above_050_recently": crossed_above_050_recently,
                "max_pressure_active": max_pressure_active,
            },
        )

        if llm_next_input:
            recent_prompts.append(str(llm_next_input))
            if len(recent_prompts) > recent_window:
                recent_prompts = recent_prompts[-recent_window:]

        fce_history.append(fce)
        hci_history.append(hci)
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
                if bank == "chaotic" and hci >= 0.35:
                    print(
                        f"event=perturbation_skipped reason=hci_preserving cycle={cycle_number} "
                        f"bank={bank} hci={hci:.3f}"
                    )
                elif bank == "chaotic" and hci >= 0.20:
                    print(
                        f"event=perturbation_skipped reason=hci_threshold cycle={cycle_number} "
                        f"bank={bank} hci={hci:.3f}"
                    )
                else:
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
            "groq_max_tokens": llm_call_meta.get("groq_max_tokens"),
            "groq_temperature": llm_call_meta.get("groq_temperature"),
            "prompt_chars": llm_call_meta.get("prompt_chars"),
            "forced_topic": forced_topic,
            "curriculum_mode": curriculum_config["mode"],
            "hci_target_low": curriculum_config["hci_target_low"],
            "hci_target_high": curriculum_config["hci_target_high"],
            "hci_trend": hci_trend,
            "recent_window": recent_window,
        }
        _write_jsonl_record(cycle_log_path, cycle_record)
        session_log["cycles"].append(cycle_record)

        print(
            f"cycle={cycle_number:03d} | phase={phase} | FCE={fce:.3f} | hci={hci:.3f} | "
            f"emergent={emergent_count} | provider={provider_used}"
        )

        if float(args.cycle_sleep) > 0.0:
            time.sleep(float(args.cycle_sleep))

        current_input = next_input
        cycle_index += 1

    print(f"memoryweb_size_end={len(getattr(mind.memory_web, 'memory_store', {}))}")

    if args.save_state:
        mind.save_state(str(args.save_state), include_ecwf_past_states=False)
    mind.save_state(str(state_path), include_ecwf_past_states=False)
    session_path.write_text(json.dumps(_to_jsonable(session_log), indent=2, ensure_ascii=False), encoding="utf-8")
    events_path.write_text(json.dumps(_to_jsonable(significant_events), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved session log: {session_path}")
    print(f"Saved cycle log: {cycle_log_path}")
    print(f"Saved state: {state_path}")


if __name__ == "__main__":
    main()
