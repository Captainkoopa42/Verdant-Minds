#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from usm import UnifiedSyntheticMind


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


def _phase_from_tg(tg: float) -> str:
    if tg < 0.4:
        return "Rigid"
    if tg <= 0.6:
        return "Flexible"
    return "Chaotic"


def _dim_name(mind: UnifiedSyntheticMind, prefix: str, idx: int) -> str:
    key = f"{prefix}{idx + 1}"
    return mind.ecwf_core.dimension_meanings.get(key, key)


def _top_items(d: Dict[str, Any], n: int = 5) -> List[Tuple[str, float]]:
    items = []
    for k, v in (d or {}).items():
        try:
            items.append((str(k), float(v)))
        except Exception:
            continue
    return sorted(items, key=lambda x: x[1], reverse=True)[:n]


def build_telemetry(mind: UnifiedSyntheticMind, chunk) -> Dict[str, Any]:
    metrics = chunk.get_section_content("processing_metrics_section") or {}
    memory = chunk.get_section_content("memory_section") or {}
    wave = chunk.get_section_content("wave_function_section") or {}
    coherence = chunk.get_section_content("coherence_invariants_section") or {}
    language = chunk.get_section_content("language_processing_section") or {}
    continual = chunk.get_section_content("continual_learning_section") or {}
    action = chunk.get_section_content("action_selection_section") or {}
    forefront = chunk.get_section_content("forefront_king_section") or {}
    ethics = chunk.get_section_content("ethics_king_section") or {}
    data_king = chunk.get_section_content("data_king_section") or {}

    tg = float(metrics.get("glass_transition_temp", 0.5) or 0.5)
    phase = _phase_from_tg(tg)
    system_entropy = float(metrics.get("system_entropy", wave.get("entropy", 0.0)) or 0.0)
    t_cog = float(1.0 - tg + system_entropy)

    wave_params = language.get("wave_response_parameters", {}) or {}
    dom_cog = wave_params.get("dominant_cognitive_dims", []) or []
    dom_eth = wave_params.get("dominant_ethical_dims", []) or []

    top_activated = _top_items(memory.get("activated_concepts", {}), n=5)

    resonance_patterns = continual.get("resonance_patterns", {}) or {}
    resonance_count = (
        int(resonance_patterns.get("pattern_count", 0))
        if isinstance(resonance_patterns, dict)
        else 0
    )

    phase_state = forefront.get("phase_state", phase)
    phase_bias_map = {
        "Rigid": {"answer_query": 1.15, "provide_partial_answer": 1.10, "ask_clarification": 0.85},
        "Chaotic": {"ask_clarification": 1.20, "defer_decision": 1.20, "answer_query": 0.80},
        "Flexible": {},
    }
    inferred_phase_bias = phase_bias_map.get(str(phase_state), {}).get(action.get("selected_action"), 1.0)

    return {
        "thermodynamic_state": {
            "T_g": tg,
            "phase": phase,
            "system_entropy": system_entropy,
            "T_cog": t_cog,
            "phase_memory_management": memory.get("phase_memory_management", {}),
        },
        "wave_state": {
            "interference_signature": language.get("interference_signature", wave_params.get("interference_signature", "stable")),
            "dominant_cognitive_dimensions": [
                {"index": int(i), "name": _dim_name(mind, "C", int(i))} for i in dom_cog[:2]
            ],
            "dominant_ethical_dimensions": [
                {"index": int(i), "name": _dim_name(mind, "E", int(i))} for i in dom_eth[:2]
            ],
            "wave_entropy": float(wave_params.get("wave_entropy", wave.get("entropy", 0.0)) or 0.0),
            "phase_coherence": float(wave_params.get("phase_coherence", 0.0) or 0.0),
        },
        "coherence_invariants": {
            "triangle_valid_at_alpha1": bool(coherence.get("triangle_valid_at_alpha1", True)),
            "housed_contradiction_index": float(coherence.get("housed_contradiction_index", 0.0) or 0.0),
            "violation_rate": float(coherence.get("violation_rate", 0.0) or 0.0),
            "alpha_critical_estimate": coherence.get("alpha_crit_estimate"),
        },
        "memory_topology": {
            "total_concepts": len(getattr(mind.memory_web, "memory_store", {})),
            "average_stability": float(getattr(mind.memory_web, "metrics", {}).get("average_stability", 0.0) or 0.0),
            "top_activated_concepts": top_activated,
            "emergent_concepts_created": int(continual.get("emergent_concepts_created", 0) or 0),
            "resonance_patterns_detected": resonance_count,
        },
        "kings_status": {
            "forefront_king": {
                "decision_threshold": forefront.get("decision_threshold"),
                "phase_state": forefront.get("phase_state"),
                "cognitive_load": forefront.get("cognitive_load"),
                "coherence_influence": forefront.get("coherence_influence", {}),
            },
            "ethics_king": {
                "overall_score": (ethics.get("evaluation", {}) or {}).get("overall_score"),
                "status": (ethics.get("evaluation", {}) or {}).get("status"),
                "concerns": (ethics.get("evaluation", {}) or {}).get("concerns", []),
                "coherence_influence": ethics.get("coherence_influence", {}),
            },
            "data_king": {
                "quality_score": data_king.get("information_quality"),
                "novelty_score": data_king.get("novelty"),
                "relevance_score": data_king.get("relevance"),
            },
        },
        "action_taken": {
            "selected_action": action.get("selected_action"),
            "confidence": action.get("action_confidence"),
            "phase_bias_applied": {
                "phase_state": phase_state,
                "inferred_multiplier": inferred_phase_bias,
                "explicit_telemetry_present": "phase_bias" in action,
            },
            "ethical_tone": language.get("ethical_tone", {}),
            "interference_signature_applied": language.get("interference_signature", "stable"),
        },
    }


def _box_section(title: str, rows: List[Tuple[str, Any]], width: int = 108) -> str:
    lines = [f"┌{'─' * (width - 2)}┐"]
    header = f" {title} "
    lines.append(f"│{header:<{width-2}}│")
    lines.append(f"├{'─' * (width - 2)}┤")
    for key, value in rows:
        rendered = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list, tuple)) else str(value)
        text = f" {key:<36} {rendered}"
        if len(text) > width - 2:
            text = text[: width - 5] + "..."
        lines.append(f"│{text:<{width-2}}│")
    lines.append(f"└{'─' * (width - 2)}┘")
    return "\n".join(lines)


def render_text(telemetry: Dict[str, Any]) -> str:
    thermo = telemetry["thermodynamic_state"]
    wave = telemetry["wave_state"]
    coherence = telemetry["coherence_invariants"]
    memory = telemetry["memory_topology"]
    kings = telemetry["kings_status"]
    action = telemetry["action_taken"]

    sections = [
        _box_section("THERMODYNAMIC STATE", [
            ("T_g / Phase", f"{thermo['T_g']:.3f} / {thermo['phase']}"),
            ("System entropy", f"{thermo['system_entropy']:.3f}"),
            ("Cognitive temperature T_cog", f"{thermo['T_cog']:.3f}"),
            ("Phase memory management", thermo.get("phase_memory_management", {})),
        ]),
        _box_section("WAVE STATE", [
            ("Interference signature", wave.get("interference_signature")),
            ("Dominant cognitive dims", wave.get("dominant_cognitive_dimensions", [])),
            ("Dominant ethical dims", wave.get("dominant_ethical_dimensions", [])),
            ("Wave entropy", f"{wave.get('wave_entropy', 0.0):.3f}"),
            ("Phase coherence", f"{wave.get('phase_coherence', 0.0):.3f}"),
        ]),
        _box_section("COHERENCE INVARIANTS", [
            ("H1 triangle valid @ alpha=1.0", coherence.get("triangle_valid_at_alpha1")),
            ("Housed contradiction index", f"{coherence.get('housed_contradiction_index', 0.0):.3f}"),
            ("Violation rate", f"{coherence.get('violation_rate', 0.0):.3f}"),
            ("Alpha critical estimate", coherence.get("alpha_critical_estimate")),
        ]),
        _box_section("MEMORY TOPOLOGY", [
            ("Total concepts", memory.get("total_concepts")),
            ("Average stability", f"{memory.get('average_stability', 0.0):.3f}"),
            ("Top 5 activated concepts", memory.get("top_activated_concepts", [])),
            ("Emergent concepts created", memory.get("emergent_concepts_created")),
            ("Resonance patterns detected", memory.get("resonance_patterns_detected")),
        ]),
        _box_section("KINGS STATUS", [
            ("ForefrontKing", kings.get("forefront_king", {})),
            ("EthicsKing", kings.get("ethics_king", {})),
            ("DataKing", kings.get("data_king", {})),
        ]),
        _box_section("ACTION TAKEN", [
            ("Selected action / confidence", f"{action.get('selected_action')} / {action.get('confidence')}"),
            ("Phase bias applied", action.get("phase_bias_applied", {})),
            ("Ethical tone", action.get("ethical_tone", {})),
            ("Interference signature applied", action.get("interference_signature_applied")),
        ]),
    ]

    return "\n\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verdant real-time telemetry display (includes T_cog = 1 - T_g + system_entropy)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output telemetry as JSON")
    parser.add_argument("--initialize-knowledge", action="store_true", help="Initialize knowledge base")
    args = parser.parse_args()

    mind = UnifiedSyntheticMind(config={"initialize_knowledge": bool(args.initialize_knowledge)})

    print("Verdant Telemetry ready. Type input (or 'exit').")
    while True:
        try:
            text = input("telemetry> ").strip()
        except EOFError:
            print()
            break

        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            break

        chunk = mind.process_input(text)
        telemetry = build_telemetry(mind, chunk)

        if args.as_json:
            print(json.dumps(_to_jsonable(telemetry), indent=2, ensure_ascii=False))
        else:
            print(render_text(telemetry))


if __name__ == "__main__":
    main()
