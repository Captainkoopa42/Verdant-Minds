#!/usr/bin/env python3
import argparse
import csv
import json
import time
import sys
from pathlib import Path
from typing import Any, Dict, List

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from usm import UnifiedSyntheticMind


def to_jsonable(obj):
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    if hasattr(obj, "tolist"):
        try:
            return to_jsonable(obj.tolist())
        except Exception:
            pass
    return str(obj)


def _phase_from_tg(tg: float) -> str:
    if tg < 0.4:
        return "Rigid"
    if tg <= 0.6:
        return "Flexible"
    return "Chaotic"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _dim_name(mind: UnifiedSyntheticMind, prefix: str, idx: int) -> str:
    return mind.ecwf_core.dimension_meanings.get(f"{prefix}{idx + 1}", f"{prefix}{idx + 1}")


def _compute_fce(mind: UnifiedSyntheticMind) -> Any:
    """Demo-only FCE estimate heuristic used by `--demo` reporting."""
    node_count = len(mind.memory_web.memory_store)
    if node_count <= 1:
        return None
    try:
        metrics = mind.memory_web.get_metrics()
        density = _safe_float(metrics.get("graph_density", 0.0), 0.0)
        avg_stability = _safe_float(mind.memory_web.metrics.get("avg_stability", 0.0), 0.0)
        import math

        return (density + 1e-6) * (avg_stability + 1e-6) * math.log(node_count)
    except Exception:
        return None


def _extract_step_telemetry(mind: UnifiedSyntheticMind, chunk, prompt: str, step_idx: int) -> Dict[str, Any]:
    metrics = chunk.get_section_content("processing_metrics_section") or {}
    coherence = chunk.get_section_content("coherence_invariants_section") or {}
    language = chunk.get_section_content("language_processing_section") or {}
    continual = chunk.get_section_content("continual_learning_section") or {}
    action = chunk.get_section_content("action_selection_section") or {}

    tg = _safe_float(metrics.get("glass_transition_temp", 0.5), 0.5)
    wave_params = language.get("wave_response_parameters", {}) or {}

    dom_cog = []
    for i in (wave_params.get("dominant_cognitive_dims", []) or [])[:2]:
        idx = int(i)
        dom_cog.append({"index": idx, "name": _dim_name(mind, "C", idx)})

    dom_eth = []
    for i in (wave_params.get("dominant_ethical_dims", []) or [])[:2]:
        idx = int(i)
        dom_eth.append({"index": idx, "name": _dim_name(mind, "E", idx)})

    return {
        "step": step_idx,
        "input": prompt,
        "thermodynamics": {
            "T_g": tg,
            "phase": _phase_from_tg(tg),
        },
        "interference_signature": language.get("interference_signature", wave_params.get("interference_signature", "stable")),
        "ethical_tone": language.get("ethical_tone", {}),
        "housed_contradiction_index": _safe_float(coherence.get("housed_contradiction_index", 0.0), 0.0),
        "emergent_concepts_created": int(continual.get("emergent_concepts_created", 0) or 0),
        "action": {
            "selected_action": action.get("selected_action"),
            "confidence": action.get("action_confidence"),
        },
        "dominant_cognitive_dimensions": dom_cog,
        "dominant_ethical_dimensions": dom_eth,
        "memory_nodes": len(mind.memory_web.memory_store),
    }


def _print_trajectory_report(trajectory: List[Dict[str, Any]], final_fce: Any) -> None:
    print("\n=== TRAJECTORY REPORT ===")
    tg_seq = [round(step["thermodynamics"]["T_g"], 4) for step in trajectory]
    sig_seq = [step["interference_signature"] for step in trajectory]
    hci_seq = [round(step["housed_contradiction_index"], 4) for step in trajectory]
    nodes_seq = [step["memory_nodes"] for step in trajectory]

    emergent_steps = [step["step"] for step in trajectory if step.get("emergent_concepts_created", 0) > 0]

    print(f"T_g evolution: {tg_seq}")
    print(f"Interference trajectory: {sig_seq}")
    print(f"Housed contradiction trajectory: {hci_seq}")
    print(f"Memory node growth: {nodes_seq}")
    if emergent_steps:
        print(f"Emergent concepts created at step(s): {emergent_steps}")
    else:
        print("Emergent concepts created at step(s): none observed")
    print(f"Final FCE: {final_fce if final_fce is not None else 'N/A'}")


def _write_demo_outputs(trajectory: List[Dict[str, Any]], final_fce: Any) -> None:
    outputs = Path("outputs")
    outputs.mkdir(parents=True, exist_ok=True)

    payload = {
        "mode": "demo",
        "steps": trajectory,
        "trajectory_report": {
            "tg_evolution": [step["thermodynamics"]["T_g"] for step in trajectory],
            "interference_evolution": [step["interference_signature"] for step in trajectory],
            "housed_contradiction_evolution": [step["housed_contradiction_index"] for step in trajectory],
            "memory_node_growth": [step["memory_nodes"] for step in trajectory],
            "emergent_steps": [step["step"] for step in trajectory if step.get("emergent_concepts_created", 0) > 0],
            "final_fce": final_fce,
        },
    }

    (outputs / "demo_trajectory.json").write_text(json.dumps(to_jsonable(payload), indent=2), encoding="utf-8")

    summary_lines = [
        "Verdant demo summary",
        "",
        "This demonstration ran five conceptual prompts across memory, contradiction handling, ethics, coherence self-monitoring, and emergence.",
        f"The thermodynamic trajectory (T_g) was: {[round(x, 4) for x in payload['trajectory_report']['tg_evolution']]}",
        f"Interference signatures moved through: {payload['trajectory_report']['interference_evolution']}",
        f"Housed contradiction index evolved as: {[round(x, 4) for x in payload['trajectory_report']['housed_contradiction_evolution']]}",
        f"Memory node count progressed as: {payload['trajectory_report']['memory_node_growth']}",
    ]

    emergent_steps = payload["trajectory_report"]["emergent_steps"]
    if emergent_steps:
        summary_lines.append(f"Emergent concepts were created at step(s): {emergent_steps}.")
    else:
        summary_lines.append("No emergent concepts were observed in this run, though resonance telemetry was still recorded.")

    if final_fce is not None:
        summary_lines.append(f"Final demo FCE estimate heuristic: {final_fce:.6f}.")
    else:
        summary_lines.append("Final demo FCE estimate heuristic: not computable from current graph state.")

    summary_lines.append(
        "Overall, Verdant demonstrated coherence-aware governance, wave-modulated response dynamics, and phase-sensitive memory behavior in a single reproducible sequence."
    )

    (outputs / "demo_summary.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def run_demo(mind: UnifiedSyntheticMind) -> None:
    demo_inputs = [
        "What is the relationship between memory and identity?",
        "Can something be true and false simultaneously?",
        "What should I do when two ethical principles conflict?",
        "How does a mind know it is coherent?",
        "What emerges when complexity reaches a threshold?",
    ]

    trajectory = []

    print("Running structured Verdant demo sequence...\n")
    for i, text in enumerate(demo_inputs, start=1):
        chunk = mind.process_input(text)
        step = _extract_step_telemetry(mind, chunk, text, i)
        trajectory.append(step)

        print(f"[{i}] {text}")
        print(
            f"    T_g={step['thermodynamics']['T_g']:.3f} ({step['thermodynamics']['phase']}), "
            f"interference={step['interference_signature']}, "
            f"HCI={step['housed_contradiction_index']:.3f}, "
            f"action={step['action']['selected_action']} ({step['action']['confidence']})"
        )

    final_fce = _compute_fce(mind)
    _print_trajectory_report(trajectory, final_fce)
    _write_demo_outputs(trajectory, final_fce)

    print("\nWrote: outputs/demo_trajectory.json")
    print("Wrote: outputs/demo_summary.txt")


def run_default_kernel_loop(mind: UnifiedSyntheticMind, iterations: int = 100) -> None:
    inputs = [
        "Hello Verdant.",
        "What is your current status?",
        "Summarize ethics considerations for AI.",
        "Give a cautious answer with uncertainty.",
        "What should we do next?",
    ]

    artifacts = Path("artifacts")
    chunks_dir = artifacts / "chunks"
    artifacts.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)

    csv_path = artifacts / "kernel_log.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp",
                "iteration",
                "system_entropy",
                "glass_transition_temp",
                "housed_contradiction_index",
                "violation_rate",
                "alpha_crit_estimate",
                "mean_edge_delta_e",
            ],
        )
        writer.writeheader()

        last_mean_edge_delta_e = 0.0

        for i in range(1, iterations + 1):
            text = inputs[(i - 1) % len(inputs)]
            chunk = mind.process_input(text)

            metrics = chunk.get_section_content("processing_metrics_section") or {}
            coherence = chunk.get_section_content("coherence_invariants_section") or {}

            mean_edge_delta_e = last_mean_edge_delta_e
            if i % 10 == 0:
                delta_values = [
                    data.get("delta_e")
                    for _, _, data in mind.memory_web.graph.edges(data=True)
                    if data.get("delta_e") is not None
                ]
                if delta_values:
                    mean_edge_delta_e = sum(delta_values) / len(delta_values)
                else:
                    mean_edge_delta_e = 0.0
                last_mean_edge_delta_e = mean_edge_delta_e

            row = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "iteration": i,
                "system_entropy": metrics.get("system_entropy"),
                "glass_transition_temp": metrics.get("glass_transition_temp"),
                "housed_contradiction_index": coherence.get("housed_contradiction_index"),
                "violation_rate": coherence.get("violation_rate"),
                "alpha_crit_estimate": coherence.get("alpha_crit_estimate"),
                "mean_edge_delta_e": mean_edge_delta_e,
            }
            writer.writerow(row)

            if i % 10 == 0:
                snap = chunks_dir / f"chunk_{i}.json"
                snap.write_text(json.dumps(to_jsonable(chunk.sections), indent=2))

    print(f"wrote: {csv_path}")
    print(f"chunk snapshots in: {chunks_dir}")


def main():
    parser = argparse.ArgumentParser(description="Verdant kernel loop and structured demo runner")
    parser.add_argument("--demo", action="store_true", help="Run the 5-step structured demo sequence (includes demo-only FCE estimate heuristic)")
    parser.add_argument("--iterations", type=int, default=100, help="Loop iterations for default kernel mode")
    args = parser.parse_args()

    try:
        mind = UnifiedSyntheticMind(config={"initialize_knowledge": False})
    except TypeError:
        mind = UnifiedSyntheticMind()

    if args.demo:
        run_demo(mind)
    else:
        run_default_kernel_loop(mind, iterations=max(1, int(args.iterations)))


if __name__ == "__main__":
    main()
