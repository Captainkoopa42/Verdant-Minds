# V3 Results

This directory contains validation results from V3 experiments.

Results are organized by experiment type:

- `1000_cycle/` — 1000-cycle developmental validation
- `parameter_sweep/` — 8-axis parameter sweep (47 configurations)
- `vcult_specs/` — VCult cultivation spec validation runs
- `self_referential/` — Self-referential loop experiments

## Key Numbers

| Metric | Value |
|--------|-------|
| Earlier-share | 1.000 |
| Onset cycle | 9.0 |
| Onset T_g | 0.5725 |
| Emergent concepts (1000 cycles) | 300 |
| Semantic coherence | 97% |
| Basin count (1000 cycles) | 70 |
| Daughter forge fraction | 85.3% |
| H1 coherence valid | 100% |
| Baseline separation | 21σ |
| Self-referential concepts | 56% |

## Reproduction

All results can be reproduced from the Colab cells in `colab/cells/`
or by running the validation pipeline:

```bash
python analysis/run_full_validation.py \
  --run-dir <run_directory> \
  --seeds <N> \
  --outdir validation_output
```

Full data files (state.json, cycles.jsonl) are large and stored
locally or on Zenodo, not in this repository.
