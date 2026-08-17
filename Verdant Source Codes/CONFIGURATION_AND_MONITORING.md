# Verdant-V0 Configuration, Logging, and Benchmarking

This directory contains working configuration, enhanced-logging, and benchmark utilities. They are not all wired into the canonical `UnifiedSyntheticMind` runtime. This guide separates what exists from what the main system actually uses.

## Integration map

| Layer | Present? | Used automatically by `UnifiedSystem`? | Correct interpretation |
|---|---:|---:|---|
| flat runtime `config` dictionary | yes | yes | canonical V0 configuration path |
| YAML `ConfigManager` | yes | no | standalone loader/validator utility |
| YAML profiles under `config/` | yes | no | reference/proposed profiles until translated into runtime keys |
| basic `logging_utils.setup_logger` | yes | yes | canonical runtime logging path |
| `enhanced_logging` | yes | no | optional standalone structured/performance logging toolkit |
| `benchmarks/performance_tests.py` | yes | no | independent block harness, not full governed runtime |

## 1. Canonical runtime configuration

The real constructor accepts `seed` and a flat dictionary:

```python
from usm import UnifiedSyntheticMind

mind = UnifiedSyntheticMind(
    seed=42,
    config={
        "cognitive_dimensions": 5,
        "ethical_dimensions": 5,
        "wave_facets": 7,
        "bridge_influence_factor": 0.3,
        "learning_rate": 0.05,
        "decision_threshold": 0.7,
        "ethical_sensitivity": 0.6,
        "initialize_knowledge": True,
        "log_level": "INFO",
        "use_pconnect_edges": True,
    },
)
```

The defaults are defined in `src/core/system.py::_load_configuration()`.

The constructor does **not** accept `config_path=` or `config_override=`. YAML examples making that call describe intended integration, not current V0 behavior.

## 2. YAML ConfigManager

`src/utils/config_manager.py` can load, merge, validate, inspect, and save YAML configuration independently.

From the repository root:

```bash
PYTHONPATH="Verdant Source Codes" python - <<'PY'
from src.utils.config_manager import ConfigManager

config = ConfigManager()
print(config.get("ecwf.cognitive_dimensions"))
print(config.validate())
PY
```

Available profiles:

- `Verdant Source Codes/config/default_config.yaml`
- `Verdant Source Codes/config/ethical_reasoning_config.yaml`
- `Verdant Source Codes/config/performance_optimized_config.yaml`
- `Verdant Source Codes/config/research_debug_config.yaml`

These files use nested keys such as `ecwf.cognitive_dimensions`. `UnifiedSystem` expects flat keys such as `cognitive_dimensions`. Passing a ConfigManager dictionary directly to `UnifiedSyntheticMind(config=...)` will not automatically translate the nested structure.

Until an adapter is implemented, treat the YAML profiles as:

- configuration research and reference material;
- validation examples for ConfigManager;
- inputs that require an explicit translation step before affecting the canonical runtime.

## 3. Canonical logging

`UnifiedSystem` imports `src/utils/logging_utils.py` and calls `setup_logger()`. That helper supports:

- logger name;
- log level;
- console formatting;
- an optional file path.

The runtime currently initializes it directly at `INFO`; the `log_level` value in the flat configuration is stored but is not applied by the constructor.

## 4. Enhanced logging utility

`src/utils/enhanced_logging.py` provides:

- colored console formatting;
- rotating text logs;
- rotating structured JSON logs;
- contextual logger adapters;
- timing, memory, and throughput helpers;
- a timing context manager.

It works as a standalone utility but is not imported by the canonical blocks or orchestrator.

Example:

```bash
PYTHONPATH="Verdant Source Codes" python - <<'PY'
from src.utils.enhanced_logging import get_logger, setup_logging

setup_logging(level="INFO")
logger = get_logger("verdant.experiment", context={"run": "example"})
logger.info("Experiment logging initialized")
PY
```

Using this utility in an experiment does not automatically replace the runtime's existing loggers.

## 5. Independent benchmark harness

Run the available harness from the repository root:

```bash
python "Verdant Source Codes/benchmarks/performance_tests.py" \
  --mode quick \
  --output outputs/benchmark_results.json
```

Supported modes are `quick`, `full`, `block`, and `compare`.

```bash
python "Verdant Source Codes/benchmarks/performance_tests.py" \
  --mode full \
  --iterations 100 \
  --output outputs/benchmark_full.json

python "Verdant Source Codes/benchmarks/performance_tests.py" \
  --mode block \
  --block PatternRecognition \
  --output outputs/benchmark_pattern.json
```

### Benchmark boundary

The harness constructs individual block objects and processes chunks through them. By default it does not construct `UnifiedSystem`, a populated MemoryWeb/ECWF bridge, or Three Kings governance. Its timings therefore measure the isolated harness path, not the complete canonical runtime.

`--config` changes the label recorded in results. The current `compare` implementation cycles through configuration names but contains a TODO where actual YAML loading/reinitialization would occur. Its comparison output must not be described as a measurement of genuinely different configuration profiles.

For full-runtime timings, inspect `processing_metrics_section` from `mind.process_input()` or use `scripts/kernel_loop.py`.

## 6. Runtime telemetry and artifacts

| Tool | What it observes | Output |
|---|---|---|
| `scripts/verdant_telemetry.py` | interactive canonical runtime telemetry | terminal or JSON terminal output |
| `scripts/kernel_loop.py` | repeated canonical runtime processing | `artifacts/kernel_log.csv` |
| `scripts/kernel_loop.py --demo` | fixed five-input canonical run | trajectory and summary under `outputs/` |
| `scripts/verdant_llm_cultivator.py` | repeated/provider-driven cultivation | session, cycle, state, and event artifacts |
| `scripts/analysis/scaffolding_from_state.py` | saved MemoryWeb structure | two analysis PNGs |

## 7. Reporting requirements

For performance or monitoring claims, state:

- whether the measurement used the full runtime or isolated benchmark harness;
- whether Three Kings governance and the Memory–ECWF bridge were active;
- whether knowledge initialization was enabled;
- semantic mapping mode;
- input count and input sequence;
- fresh or restored state;
- Python/dependency environment;
- exact command and output path.

Do not compare harness labels as configuration experiments unless the configurations were actually loaded and applied.

## 8. Known integration work

Future code work could:

1. define a single authoritative configuration schema;
2. translate nested YAML profiles into the flat runtime keys or update the runtime to consume nested configuration;
3. apply configured logging levels during construction;
4. make enhanced logging an explicit optional runtime backend;
5. benchmark the fully composed system separately from isolated blocks;
6. make configuration comparison instantiate genuinely different systems.

Those items are integration opportunities, not claims about current behavior.
