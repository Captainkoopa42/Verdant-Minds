# Milestone 19 Revalidation Notice — Oracle-Assisted Promotion

## Status

V5-X inherited the original V5 Milestone 19 flaw: evaluator ground truth was used to choose which P and Q candidates were promoted, so the old formation path could not support evaluator-independent promotion claims.

That flaw has now been repaired in the V5-X validation path.

## Repair

The canonical benchmark export uses `verdant_benchmarks/ethomorphism_oracle_free.py`, and V5-X validation/intervention tests route through it.

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

The evaluator no longer supplies world membership, family membership, expected member sets, or target candidate IDs during formation. The scoring index is constructed afterward and must leave the kernel fingerprint unchanged.

## Regression boundary

Regression coverage requires:

1. P and Q exist before any evaluator scoring index is built.
2. Scoring does not change the kernel fingerprint.
3. The controlled M19 population contains exactly five expected P structures and one expected Q, with no missing or extra promoted P/Q structures.
4. V5-X lesion assays begin from the repaired oracle-free source organism.

## Historical boundary

`verdant_benchmarks/ethomorphism.py` remains as the historical oracle-assisted implementation and is exported as:

```text
LegacyOracleAssistedEthomorphismBenchmarkHarness
```

The normal export:

```text
EthomorphismBenchmarkHarness
```

resolves to the oracle-free implementation.
