# Milestone 19 Revalidation Notice — Oracle-Assisted Promotion

## Status

The original Milestone 19 A/B/C/D benchmark was **scientifically invalid for the claim of evaluator-independent P/Q promotion** because evaluator ground truth was used to choose which P and Q candidates were promoted.

That formation flaw has now been repaired and the repaired benchmark has been rerun successfully on branch `V5`.

## Repair

The canonical benchmark export uses `verdant_benchmarks/ethomorphism_oracle_free.py`.

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

The evaluator no longer supplies world membership, family membership, expected member sets, or target candidate IDs during formation. Scoring happens only after formation and is fingerprint-checked to ensure it does not mutate the kernel.

## Revalidation result

GitHub Actions run `31989621761` completed successfully on 2026-08-16/17 UTC using Python 3.11 and the locked V5 dependency set.

The repaired benchmark reported:

```text
schema                         verdant.ethomorphism_benchmark.v2_oracle_free
all headline checks            PASS
expected P structures          5
promoted P structures          5
missing P structures           0
extra promoted P structures    0
expected Q structures          1
promoted Q structures          1
extra promoted Q structures    0
```

The original causal measurements were reproduced on the oracle-free formation path:

```text
P: WITH 1 → ABLATE 7 → RESTORE 1
Q: WITH 3 → ABLATE 8 → RESTORE 3
```

The held-out path family was recovered, the star control was rejected, and the P/Q causal gains followed the exact objects under ablation/restoration.

## Regression boundary

Regression coverage now requires:

1. P and Q already exist before any evaluator scoring index is constructed.
2. The scoring pass leaves the kernel fingerprint unchanged.
3. The controlled M19 population contains exactly five expected P structures and one expected Q, with no missing structures and no extra promoted P/Q false positives.

## Historical boundary

`verdant_benchmarks/ethomorphism.py` remains in the repository as the historical oracle-assisted implementation and is exported as:

```text
LegacyOracleAssistedEthomorphismBenchmarkHarness
```

The normal export:

```text
EthomorphismBenchmarkHarness
```

resolves to the oracle-free implementation.

The original pre-fix run should still be treated as invalid evidence for autonomous/evaluator-independent promotion. The successful post-fix run is the current validation evidence for Milestone 19.
