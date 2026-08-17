# Milestone 19 Revalidation Notice — Oracle-Assisted Promotion

## Status

V5-X inherited the original V5 Milestone 19 flaw: evaluator ground truth was used to choose which P and Q candidates were promoted, so the old formation path could not support evaluator-independent promotion claims.

That flaw has now been repaired and the repaired V5-X validation path has been rerun successfully.

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

## Revalidation result

GitHub Actions run `31989515573` completed successfully on 2026-08-16/17 UTC.

The oracle-free M19 run reported:

```text
schema                         verdant.ethomorphism_benchmark.v2_oracle_free
all M19 headline checks        PASS
expected P structures          5
promoted P structures          5
missing P structures           0
extra promoted P structures    0
expected Q structures          1
promoted Q structures          1
extra promoted Q structures    0
```

The causal measurements were reproduced:

```text
P: 1 → 7 → 1
Q: 3 → 8 → 3
```

The full V5-X validation also qualified successfully. Its headline gates passed for M19, thermodynamic observer null-equivalence, unchanged governance `t_g`, destructive P/Q lesion cost, governed re-derivation, and no use of the restore operation during re-derivation.

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

Old pre-fix V5/V5-X validation artifacts remain historical only. The successful post-fix GitHub Actions run is the current validation evidence.
