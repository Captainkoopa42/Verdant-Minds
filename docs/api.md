# Verdant-V0 API and Command Reference

## Python entry point

```python
from usm import UnifiedSyntheticMind
```

This is an alias for `src.core.system.UnifiedSystem`. Import through `usm`; do not import the incomplete top-level `verdant/` runtime.

## Constructor

```python
UnifiedSyntheticMind(seed: int = 42, config: dict | None = None)
```

Default configuration:

| Key | Default | Meaning |
|---|---:|---|
| `cognitive_dimensions` | 5 | ECWF cognitive dimensions |
| `ethical_dimensions` | 5 | ECWF ethical dimensions |
| `wave_facets` | 7 | wave facets |
| `bridge_influence_factor` | 0.3 | graph/wave coupling strength |
| `learning_rate` | 0.05 | learning configuration |
| `decision_threshold` | 0.7 | action threshold configuration |
| `ethical_sensitivity` | 0.6 | ethics configuration |
| `initialize_knowledge` | `True` | seed the built-in knowledge set |
| `log_level` | `INFO` | configured logging level |
| `use_pconnect_edges` | `True` | use pconnect memory-edge policy |

## Public runtime methods

| Method | Return | Purpose |
|---|---|---|
| `process_input(input_text, metadata=None)` | `CognitiveChunk` | run the complete pipeline |
| `get_response(input_text, metadata=None)` | `str` | run pipeline and format built-in text |
| `initialize_knowledge(ethical_concepts=None)` | `dict` | seed the knowledge graph/mappings |
| `get_system_metrics()` | `dict` | runtime, graph, wave, and governance metrics |
| `run_integration_tests()` | `dict` | invoke the in-code integration framework |
| `generate_integration_report()` | `dict` | produce its integration report |
| `save_system_state(filepath)` | `bool` | write pickle state |
| `load_system_state(filepath)` | `UnifiedSystem` | classmethod loading pickle state |
| `to_state_dict(include_ecwf_past_states=False)` | `dict` | build JSON-compatible state |
| `from_state_dict(state)` | `None` | mutate instance from state dictionary |
| `save_state(path, include_ecwf_past_states=False)` | `None` | write JSON state |
| `load_state(path)` | `None` | mutate instance from JSON state |

### Minimal inspection

```python
from usm import UnifiedSyntheticMind

mind = UnifiedSyntheticMind(seed=42)
chunk = mind.process_input("What relationships were activated?")

print(chunk.get_section_content("memory_section"))
print(chunk.get_section_content("wave_function_section"))
print(chunk.get_section_content("three_kings_layer_section"))
print(chunk.get_section_content("coherence_invariants_section"))
```

## Script entry points

| Command | Purpose | Artifact behavior |
|---|---|---|
| `python -m usm` | simple interactive module | none unless code path saves |
| `python scripts/verdant_repl.py` | interactive runtime shell | optional state path |
| `python scripts/verdant_telemetry.py --json` | interactive telemetry | terminal output |
| `python scripts/kernel_loop.py --iterations 100` | repeated kernel loop | `artifacts/kernel_log.csv` |
| `python scripts/kernel_loop.py --demo` | fixed real-engine demo | two files under `outputs/` |
| `python scripts/verdant_llm_cultivator.py ...` | repeated/provider-backed cultivation | timestamped run artifacts |
| `python scripts/analysis/scaffolding_from_state.py ...` | analyze saved graph state | two PNG files |

## Cultivator flags

| Flag | Default | Meaning |
|---|---|---|
| `--cycles`, `--max-cycles` | 50 | cycles in this run segment |
| `--seed-topic` | none | first topic/input seed |
| `--resume [latest|PATH]` | none | restore cycle JSONL context |
| `--fresh` | false | do not resume prior cycle history |
| `--model` | `claude-3-5-sonnet-latest` | provider-facing model string |
| `--temperature` | 0.8 | generation temperature |
| `--max-tokens`, `--max-tokens-per-call` | env or 128 | per-call token cap |
| `--budget-mode {off,light,aggressive}` | environment-derived | prompt/token budgeting |
| `--perturbation-interval` | 15 | phase perturbation cadence |
| `--no-perturbation` | false | disable forced perturbation |
| `--initialize-knowledge` | false | seed knowledge unless loading state |
| `--save-state PATH` | none | extra JSON state destination |
| `--load-state PATH` | none | load JSON system state |
| `--output-dir PATH` | `outputs/` | run artifact root |
| `--cycle-sleep` | env or 0 | delay after each cycle |

`--resume` restores cycle-history context. `--load-state` restores architecture state. They are separate inputs and may be used together.

## Scaffolding analysis flags

```bash
python scripts/analysis/scaffolding_from_state.py \
  --state outputs/run_A/state.json \
  --topk 6 \
  --trials 500 \
  --outdir outputs/run_A/analysis
```

| Flag | Required | Default |
|---|---:|---:|
| `--state` | yes | — |
| `--topk` | no | 6 |
| `--trials` | no | 500 |
| `--outdir` | no | state-file directory |

Outputs are `emergent_scaffolding.png` and `link_age_gaps.png`.

## Telemetry vocabulary

| Name | Code-level meaning |
|---|---|
| `T_g` | implementation-defined glass transition temperature |
| `system_entropy` | current stored entropy proxy |
| `T_cog` | cultivator expression `1 - T_g + system_entropy` |
| HCI | housed contradiction index from coherence calculation |
| `pconnect` | probabilistic memory connection policy |
| `mean_edge_delta_e` | kernel summary of ethical edge-distance values |
| `resonance_patterns` | continual-learning resonance telemetry |

The kernel demo’s FCE estimate is a demo-only heuristic and is not `T_cog`.
