# Contributing to V2

V2 is a research generation with useful implementation and unresolved validity questions. Changes should make the branch easier to inspect and its conclusions easier to test.

## Before changing behavior

1. Read [STATUS.md](STATUS.md), [docs/architecture.md](docs/architecture.md), and [docs/reproducibility.md](docs/reproducibility.md).
2. State whether the change concerns packaging, architecture, experiment design, analysis, or manuscript interpretation.
3. Preserve the raw input/state artifacts needed to test the claim.

## Required checks

After applying the current import workaround:

```bash
python -m pytest tests_v2 -q
python -m compileall -q ethomorphic verdant cultivation analysis scripts tests_v2
```

For experiment or analysis changes, also run a small local cultivation panel and the full `analysis/run_all.py` pipeline.

## Evidence rules

- Do not infer direction from the order of endpoints in an undirected edge.
- Distinguish association, co-activation, parentage, and causal lineage.
- Record every seed used by the system and by statistical nulls.
- Keep current-code reproductions separate from archived older-run results.
- Include raw state, per-seed outputs, aggregation code, and failure/exclusion records.
- Update the status, testing, API, and manuscript summaries together when contracts change.

## Documentation structure

- Root files orient and operate the branch.
- `docs/` is the canonical engineering/evidence reference.
- Directory READMEs describe only their local artifacts.
- Manuscripts remain research artifacts and may preserve superseded conclusions, but their README must identify their evidence status.
- Replace stale instructions instead of layering another competing setup guide over them.
