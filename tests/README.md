# V5 engine tests

This directory contains 191 tests for the canonical engine and controlled Milestone 1–19 mechanisms.

```bash
python -m pytest -q
```

Because root `pytest.ini` sets `testpaths = tests`, that command intentionally collects this directory only. It does not run the 67 Workbench tests under `workbench/backend/tests/`.

## Coverage groups

- canonical kernel, CognitiveChunk v2, deterministic replay, and exact persistence;
- language, claims, evidence, contradictions, and revisions;
- ECWF/resonance, Three Kings/Council, shards, and routing;
- sensory archives, media gateway, temporal events, perception, and objecthood;
- workspace, atomic development, plasticity, and anti-saturation caps;
- earned P structures, compilation, cross-symbolic verification, Q hierarchy, and refolding;
- oracle-free M19 formation, selectivity, negative controls, and causal ablation/restoration.

Tests validate explicit software contracts and controlled protocols. They do not establish general intelligence, consciousness, unrestricted transfer, production security, or embodiment readiness.

Use [../TESTING.md](../TESTING.md) for the full current 258-test procedure and Workbench test inventory.
