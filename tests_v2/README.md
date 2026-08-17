# V2 test suite

The V2 suite contains 125 passing tests when the tracked `verdant` directory is exposed under the import name `verdant_v2` as described in [../INSTALL.md](../INSTALL.md).

Without that workaround, collection stops with `ModuleNotFoundError: No module named 'verdant_v2'`.

## Run

```bash
PYTHONPATH="/tmp/verdant-v2-import:$PWD" pytest -q tests_v2
```

## Coverage map

| Area | Tests |
| --- | ---: |
| Integration: basin micro-pipeline | 1 |
| Integration: basin telemetry | 2 |
| Integration: Colab smoke | 1 |
| Integration: cultivation cycle | 8 |
| Integration: cultivation runner | 1 |
| Integration: pipeline | 8 |
| Integration: scaffold ablation | 1 |
| Unit: basins | 1 |
| Unit: bridge | 12 |
| Unit: cognitive chunk | 12 |
| Unit: coherence | 12 |
| Unit: ECWF | 19 |
| Unit: governance | 9 |
| Unit: interventions | 4 |
| Unit: memory | 21 |
| Unit: phase | 13 |
| **Total** | **125** |

These tests validate the implemented mechanics and runner behavior. They do not validate the manuscript's interpretation of undirected edge endpoint order as causal direction. See [../TESTING.md](../TESTING.md) for additional manual verification and limitations.
