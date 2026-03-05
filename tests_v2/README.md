# Verdant v2 Tests

- `unit/` — Unit tests for ethomorphic core (43 tests)
  - `test_ecwf.py` — Wave function: shape, dims, entropy, serialization
  - `test_bridge.py` — Bridge: protocol, updates, emergence, dedup
  - `test_coherence.py` — Coherence: triangle, HCI, alpha-critical
- `integration/` — Integration tests for verdant_v2 pipeline (71 tests)

## Run

```bash
# All tests
pytest tests_v2/ -v

# Just ethomorphic core
pytest tests_v2/unit/ -v

# Just v2 pipeline
pytest tests_v2/integration/ -v
```
