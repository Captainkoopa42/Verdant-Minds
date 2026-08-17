# Milestone 19 Revalidation Notice — Oracle-Assisted Promotion

## Status

V5-X inherited a flaw from the frozen V5 Milestone 19 benchmark. The original A/B/C/D benchmark is **scientifically invalid for the claim of evaluator-independent P/Q promotion**.

The primitive curriculum correctly withheld the semantic family label (`path`) from Verdant state, but the original harness still used evaluator ground truth during promotion:

- P selection matched candidate member labels against the evaluator-known benchmark world before calling native promotion.
- Q selection matched hierarchy-candidate member IDs against the evaluator-known training family before calling native promotion.

That means V5-X validation and lesion work built on the old M19 formation path also require revalidation. The lesion mechanisms themselves are not erased by this finding, but their source organism must now be produced by the repaired formation path.

## Repair

The canonical benchmark export now uses `verdant_benchmarks/ethomorphism_oracle_free.py`, and V5-X validation/intervention tests are routed through it.

The repaired formation boundary is:

```text
primitive curriculum
→ native candidate formation
→ all currently eligible P candidates receive the same native promotion opportunity
→ promoted P population interacts without family/world filtering
→ all currently eligible Q candidates receive the same native promotion opportunity
→ training ends
→ evaluator builds world/family mappings only for scoring/intervention targeting
```

The scoring index is built after formation and checks the kernel fingerprint before and after indexing. Any scoring operation that mutates kernel state raises an error.

A regression test now requires P and Q to exist in an unscored D-arm runtime while `structure_by_world` is still empty and `layered_structure_id` is unset. Only afterward may the evaluator construct those mappings.

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

The numerical results recorded in the original `MILESTONE_19_REPORT.md` and any V5-X validation result produced from the old formation path are **pre-fix historical reference values**.

Do not cite them as evidence of autonomous/evaluator-independent P or Q selection.

V5 and V5-X must both be rerun on the repaired harness before those validation claims are restored.
