# V1 reproducibility and evidence

## Evidence levels used in this documentation

| Label | Meaning |
| --- | --- |
| Implemented | A corresponding code path is present. |
| Executed | The path was run during the documentation audit. |
| Unit-tested | A focused automated assertion exists and passed. |
| Claimed | Prose reports an outcome, but the branch lacks enough artifacts to reproduce it. |
| Aspirational | The text describes an intended or future capability. |

Keeping these levels separate prevents code presence from being mistaken for scientific validation.

## Audit environment and commands

The branch was inspected as `V1` with the default seed (`42`). The following checks were executed in an isolated Python environment with NumPy, NetworkX, Matplotlib, and pytest available:

```bash
python -m pytest -q
python -m compileall -q "Verdant Source Codes/src" verdant_monolithic_test_runner.py verdant_loop_controller.py
python verdant_monolithic_test_runner.py
python verdant_monolithic_test_runner.py --user-input "How should an uncertain decision be evaluated fairly?"
```

Observed results:

- all three unit tests passed;
- all tracked Python sources compiled;
- the monolithic harness reported 10/10 successful cycles;
- a single-input diagnostic cycle completed;
- five PNG reports were generated: block activity, chunk linkage, confidence timeline, ethical-state heatmap, and memory activity.

These results establish that the tested paths ran in that environment. They do not establish the validity of the cognitive theory.

## Negative-path verification

Direct calls confirmed three public helper failures described in [../STATUS.md](../STATUS.md): metrics, integration tests, and the integration report. A save/load round trip also confirmed that restored state is not rebound into bridge-dependent blocks.

## Research-outline claims

The outline contains specific statements and numbers, including a reported `T_g` near `0.63`, a `217%` increase in solution diversity, a `340%` increase in connection formation, ethical consistency values, and evaluation across 150 scenarios.

This branch does not contain the raw datasets, exact scenario set, comparison implementation, experiment script, environment lock, run logs, statistical method, or acceptance criteria needed to reproduce those numbers. They must therefore be treated as unverified reported claims, not branch-verified results.

The outline also discusses consciousness, emergence, general intelligence, cross-domain reasoning, and a “Soul Equation.” Those are theoretical or philosophical proposals. The code does not contain an accepted measurement that establishes those properties.

## Minimum evidence package for a future claim

For each quantitative claim, add:

1. a falsifiable hypothesis;
2. exact inputs or a versioned dataset;
3. the executable experiment and baseline;
4. dependency and platform versions;
5. all configuration values and random seeds;
6. raw machine-readable outputs;
7. the metric definition and statistical analysis;
8. failure cases and excluded runs;
9. a command that reproduces the final table or figure.

For ethical-behavior claims, also define who created the scenarios, how disagreements are handled, and what “correct” means. For emergence or consciousness claims, define an operational measure before examining results.

## Current determinism limits

NumPy is seeded during system initialization, but the branch has no full environment lock or replay test. Time-based chunk identifiers, timestamps, mutable memory, plotting differences, dependency versions, and repeated system use can change outputs. A seed alone is not a reproducibility guarantee.
