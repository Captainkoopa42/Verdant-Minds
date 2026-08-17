# V1 tests

Run from the repository root:

```bash
python -m pytest -q
```

## Current coverage

| Test | Scope |
| --- | --- |
| `test_logging_utils.py` | Logger propagation configuration |
| `test_memory_storage_block.py` | TTL expiration and expiration statistics |
| `test_memory_web.py` | Prevention of self-referential graph connections |

The suite has three focused tests. It does not cover the full nine-block pipeline, Three Kings outcomes, ECWF mathematics, integration helpers, persistence, authentication security, visual output, or claims in `Verdant Outline/`.

The root `verdant_monolithic_test_runner.py` is a diagnostic harness rather than a pytest test. See [../TESTING.md](../TESTING.md) for its use and the latest audit results.
