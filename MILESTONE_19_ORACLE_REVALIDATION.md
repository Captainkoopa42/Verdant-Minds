# Milestone 19 Revalidation Notice — Oracle-Assisted Promotion

## Status

The original Milestone 19 A/B/C/D benchmark is **scientifically invalid for the claim of evaluator-independent P/Q promotion**.

The primitive curriculum correctly withheld the semantic family label (`path`) from Verdant state, but the original harness still used evaluator ground truth during promotion:

- P selection matched candidate member labels against the evaluator-known benchmark world before calling native promotion.
- Q selection matched hierarchy-candidate member IDs against the evaluator-known training family before calling native promotion.

The downstream P/Q use, ablation/restoration, and structural machinery remain implemented, but the original M19 reference run cannot establish that Verdant itself selected which candidate structures deserved promotion.

## Repair

The canonical benchmark export now uses `verdant_benchmarks/ethomorphism_oracle_free.py`.

The repaired formation boundary is:

```text
primitive curriculum
→ native candidate formation
→ all currently eligible P candidates receive the same native promotion opportunity
→ promoted P population interacts without family/world filtering
→ all currently eligible Q candidates receive the same native promotion opportunity
→ training ends
→ evaluator builds world/family mappings only for scoring
```

The scoring index is built after formation and checks the kernel fingerprint before and after indexing. Any scoring operation that mutates kernel state raises an error.

Regression coverage now requires both of the following:

1. P and Q must already exist in an unscored D-arm runtime while `structure_by_world` is still empty and `layered_structure_id` is unset.
2. After scoring, the controlled population must contain exactly the five expected P structures and one expected Q, with no missing world structure and no extra promoted P/Q false positives.

The repaired benchmark summary uses schema:

```text
verdant.ethomorphism_benchmark.v2_oracle_free
```

and adds headline gates for oracle-free P and Q promotion selectivity.

## Historical boundary

`verdant_benchmarks/ethomorphism.py` is retained as the historical oracle-assisted implementation so the failure is inspectable rather than erased. It is exported under the explicit name:

```text
LegacyOracleAssistedEthomorphismBenchmarkHarness
```

The normal package export:

```text
EthomorphismBenchmarkHarness
```

now resolves to the oracle-free implementation.

## Revalidation requirement

The numerical results recorded in the original `MILESTONE_19_REPORT.md` are **pre-fix historical reference values** until the repaired harness is rerun.

Do not cite the old M19 run as evidence of autonomous/evaluator-independent P or Q selection.

The repaired benchmark must be rerun before Milestone 19 can be considered validated again.
