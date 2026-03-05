# Verdant-Minds API and Script Entry Points

This document is a code-aligned API and CLI reference focused on practical usage.

---

## Table of Contents

- [1. Primary Python entry point](#1-primary-python-entry-point)
- [2. UnifiedSyntheticMind method reference](#2-unifiedsyntheticmind-method-reference)
- [3. Script entry points](#3-script-entry-points)
- [4. Cultivator CLI flags](#4-cultivator-cli-flags)
- [5. Analysis CLI flags](#5-analysis-cli-flags)
- [6. Telemetry field vocabulary](#6-telemetry-field-vocabulary)

---

## 1. Primary Python entry point

```python
from usm import UnifiedSyntheticMind
```

`UnifiedSyntheticMind` is an alias for `UnifiedSystem` defined in:

- `usm/__init__.py`
- `Verdant Source Codes/src/core/system.py`

---

## 2. UnifiedSyntheticMind method reference

| Method | Signature | Purpose |
|---|---|---|
| `process_input` | `(input_text: str, metadata: Dict[str, Any] = None) -> CognitiveChunk` | runs full nine-block pipeline and returns enriched chunk |
| `get_response` | `(input_text: str, metadata: Dict[str, Any] = None) -> str` | convenience method returning final text response |
| `initialize_knowledge` | `(ethical_concepts: List[str] = None) -> Dict[str, Any]` | seeds foundational memory concepts |
| `get_system_metrics` | `() -> Dict[str, Any]` | returns runtime/system metrics snapshot |
| `save_system_state` | `(filepath: str) -> bool` | persists system state to disk |
| `load_system_state` | `@classmethod (filepath: str) -> UnifiedSystem` | classmethod loader from saved state |

Minimal example:

```python
from usm import UnifiedSyntheticMind

mind = UnifiedSyntheticMind(config={"initialize_knowledge": True})
chunk = mind.process_input("How does memory interact with ethics?")
print(chunk.get_section_content("reasoning_section"))
```

---

## 3. Script entry points

| Script | Typical command | Purpose |
|---|---|---|
| `scripts/verdant_repl.py` | `python scripts/verdant_repl.py` | interactive shell loop |
| `scripts/verdant_telemetry.py` | `python scripts/verdant_telemetry.py --json` | telemetry-focused interactive loop |
| `scripts/kernel_loop.py` | `python scripts/kernel_loop.py --iterations 100` | baseline kernel logging loop |
| `scripts/kernel_loop.py --demo` | `python scripts/kernel_loop.py --demo` | fixed 5-step demo trajectory |
| `scripts/verdant_llm_cultivator.py` | `python scripts/verdant_llm_cultivator.py --cycles 20 ...` | LLM-in-the-loop cycle runner |
| `scripts/analysis/scaffolding_from_state.py` | `python scripts/analysis/scaffolding_from_state.py --state ...` | emergent scaffolding metrics/plots |

---

## 4. Cultivator CLI flags

From `scripts/verdant_llm_cultivator.py` argparse:

| Flag | Default | Notes |
|---|---|---|
| `--cycles`, `--max-cycles` | `50` | total cycles to run |
| `--seed-topic` | `None` | optional first-cycle seed topic |
| `--resume [PATH|latest]` | `None` | resume from cycle JSONL history (applies only when `--fresh` is not set) |
| `--fresh` | `False` | force new cycle sequence (skip resume) |
| `--model` | `claude-3-5-sonnet-latest` | model identifier used by provider adapter |
| `--temperature` | `0.8` | generation temperature |
| `--max-tokens`, `--max-tokens-per-call` | env-backed (`128` fallback) | token cap per generation call |
| `--budget-mode` | env-derived (`off/light/aggressive`) | prompt budgeting profile |
| `--perturbation-interval` | `15` | forced phase perturbation cadence |
| `--no-perturbation` | `False` | disable perturbation behavior |
| `--initialize-knowledge` | `False` | initialize baseline knowledge; applied only if `--load-state` is not set |
| `--save-state` | `None` | extra explicit state save location |
| `--load-state` | `None` | preload state before cycles |
| `--output-dir` | `None` | artifact directory override (default `outputs/`) |
| `--cycle-sleep` | env-backed (`0.0`) | post-cycle sleep duration |

---

## 5. Analysis CLI flags

From `scripts/analysis/scaffolding_from_state.py` argparse:

| Flag | Required | Default | Meaning |
|---|---|---|---|
| `--state` | yes | n/a | path to persisted Verdant JSON state |
| `--topk` | no | `6` | top-k weighted incident edges per node for backbone |
| `--trials` | no | `500` | shuffle trial count for baseline |
| `--outdir` | no | state directory | output directory for PNGs |

Outputs written:

- `emergent_scaffolding.png`
- `link_age_gaps.png`

---

## 6. Telemetry field vocabulary

Common fields referenced across docs/scripts:

- `T_g`: glass transition temperature.
- `system_entropy`: entropy telemetry from processing/wave context.
- `T_cog`: `1 - T_g + system_entropy` (cultivator telemetry expression).
- `housed_contradiction_index` (HCI): coherence tension scalar.
- `resonance_patterns`: continual-learning pattern telemetry structure.
- `pconnect`: memory edge policy used in connection logic.
- `mean_edge_delta_e`: kernel loop CSV edge ethical-distance summary.

Clarification:

- Demo `FCE` in `kernel_loop.py --demo` is a demo-only heuristic and should not be interpreted as the same variable as cultivator `T_cog`.
