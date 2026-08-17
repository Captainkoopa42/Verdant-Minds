# Verdant-V0 Test Suite

The tests in this directory exercise the canonical runtime imported through `usm`. During the documentation audit, the complete suite passed: **121 passed, 38 warnings**.

Run everything:

```bash
python -m pytest -q
```

List the current collected cases:

```bash
python -m pytest --collect-only -q
```

## File map

| File | Primary concern |
|---|---|
| `test_cognitive_chunk.py` | chunk identity, sections, updates, serialization behavior |
| `test_system_integration.py` | initialization and end-to-end system integration |
| `test_memoryweb_pconnect.py` | graph edge acceptance/pconnect mechanics |
| `test_ethics_pconnect.py` | ethical distance and pconnect interaction |
| `test_memory_storage_bridge_wave_properties.py` | Memory Storage and ECWF bridge output |
| `test_continual_learning_bridge_integration.py` | learning/bridge integration |
| `test_coherence_invariants_integration.py` | invariant calculation in full processing |
| `test_coherence_feedback_loop.py` | previous-cycle coherence feedback |
| `test_hci_current_cycle_calculation.py` | HCI inputs and current-cycle calculation |
| `test_ethics_coherence_modulation.py` | coherence effects on ethics oversight |
| `test_language_wave_response_modulation.py` | wave effects on language processing |
| `test_semantic_entropy_tg.py` | entropy proxies and `T_g` behavior |
| `test_phase_memory_management.py` | ECWF phase-history management |
| `test_persistence_smoke.py` | saved-state round trip |
| `test_kernel_loop_demo_mode.py` | real kernel demo structure/artifacts |
| `test_verdant_llm_cultivator.py` | cultivation helpers, configuration, artifacts |
| `test_verdant_telemetry_script.py` | telemetry script behavior |

## Targeted runs

```bash
python -m pytest tests/test_system_integration.py -vv
python -m pytest tests/test_persistence_smoke.py -vv
python -m pytest tests/test_verdant_llm_cultivator.py -vv
```

Use `-s` when terminal/log output is needed. Use `-x` to stop at the first failure.

## Warnings

The audited 38 warnings are deprecation warnings caused by `datetime.utcnow()` in cultivation code. They should be fixed in a later code change, but they do not indicate failed assertions in this branch state.

## Interpretation

This suite is implementation evidence. It verifies asserted behaviors and integration paths; it is not scientific validation of consciousness, intelligence, ethical correctness, or the generality of experimental findings.

See [../TESTING.md](../TESTING.md) for smoke checks and failure triage.
