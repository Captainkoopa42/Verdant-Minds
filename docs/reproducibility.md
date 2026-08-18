# V5 reproducibility and evidence audit

## Evidence categories

V5 contains several kinds of evidence that must not be collapsed into one claim:

- **implementation present** — source exists on the branch;
- **unit/integration test passed** — an assertion passed in a named environment;
- **controlled demonstration** — a scripted fixture produced a recorded outcome;
- **causal control passed** — a measured effect disappeared/reappeared under explicit ablation/restoration;
- **artifact tracked** — a result file is present, regardless of whether its generating protocol is still valid;
- **remote validation record** — a named workflow run passed against a particular branch state;
- **general capability** — behavior outside the controlled protocol, which requires additional evidence.

The milestone reports are unusually careful about these boundaries, but the original M19 formation protocol later required a scientific correction.

## Current audit environment

The 2026-08-18 documentation audit used:

```text
Python                    3.12.13
fastapi                   0.128.2
httpx                     0.28.1
numpy                     2.3.5
opencv-python             4.13.0.92
Pillow                    12.2.0
pydantic                  2.13.4
pytest                    9.0.2
soundfile                 0.13.1
uvicorn                   0.48.0
websockets                16.1.1
```

These are the direct versions in `requirements-lock.txt`. Transitive packages are resolved by pip and are not fully locked by the repository.

## Current test evidence

The current branch contains:

| Suite | Collected | Passed in audit |
| --- | ---: | ---: |
| Engine | 191 | 191 |
| Workbench listed by `verify_release.py` | 61 | 61 |
| Later Workbench tests omitted by verifier | 6 | 6 |
| **Current total** | **258** | **258** |

The startup/artifact diagnostic passed. WB-08 and WB-09 machine proofs each returned `all_gates_pass=true` during the audit. All 21 package surfaces imported and all active Python package trees compiled.

The checked-in full-suite workflow independently records a 258-node remote pass in `MILESTONE_19_ORACLE_REVALIDATION.md`.

## Test-discovery limitation

`pytest.ini` sets `testpaths = tests`, so plain `pytest -q` collects only the engine tests. `verify_release.py` adds an explicit Workbench list, but that list predates:

- `workbench/backend/tests/test_explorer_worker_timeout_policy.py`;
- `workbench/backend/tests/test_wb11_curriculum_packs.py`.

Use [../TESTING.md](../TESTING.md) or the dynamic discovery logic in `.github/workflows/full-suite-validation.yml` when claiming a complete current-branch pass.

## M19 oracle correction

### Original problem

The original `verdant_benchmarks/ethomorphism.py` withheld semantic family labels from canonical Verdant state but still used evaluator ground truth to select which P and Q candidates were submitted for promotion. That invalidated the claim that the benchmark demonstrated evaluator-independent object selection.

The original report and tracked result remain historical artifacts:

- `MILESTONE_19_REPORT.md`;
- `artifacts/milestone_19_benchmark_summary.json` with schema `verdant.ethomorphism_benchmark.v1`.

They must not be cited as evidence of autonomous P/Q selection.

### Corrected boundary

The canonical export now resolves to `OracleFreeEthomorphismBenchmarkHarness`:

1. all natively eligible P candidates receive the same promotion opportunity;
2. all available promoted P structures participate in interaction/Q formation;
3. all natively eligible Q candidates receive the same promotion opportunity;
4. evaluator world/family mappings are built only after formation;
5. evaluator indexing is checked to leave the kernel fingerprint unchanged;
6. missing and extra promoted objects both fail selectivity checks.

### Current reproduction

The audit ran:

```bash
python run_ethomorphism_benchmark.py \
  --output /tmp/verdant-v5-oracle-free-audit.json \
  --seed 1901 \
  --state-dim 16 \
  --noise-concepts 16
```

Observed:

- schema `verdant.ethomorphism_benchmark.v2_oracle_free`;
- every headline check true;
- 5 expected and 5 promoted P structures;
- 0 missing and 0 extra P structures;
- 1 expected and 1 promoted Q structure;
- 0 extra Q structures;
- P work `1 → 7 → 1` under with/ablate/restore;
- Q work `3 → 8 → 3`;
- star control rejected;
- refolding preserved parent/root lineage and semantic counts;
- long-run plasticity stayed within declared caps.

This supports the narrow controlled benchmark claims. It does not establish general abstraction, open-world object discovery, consciousness, or general intelligence.

## Tracked artifact limitation

The corrected workflow uploads an oracle-free result, but a current `v2_oracle_free` benchmark JSON is not checked into the branch. The tracked `milestone_19_benchmark_summary.json` remains the older invalid formation result. A reader must use the revalidation notice, workflow record, or rerun the current command.

Future evidence packaging should add a clearly named oracle-free artifact without overwriting the historical file.

## Manifest and identity drift

V5 intentionally preserves historical manifests, but they are not live inventories.

### `ACTIVE_CODEBASE_FILE_MANIFEST.json`

This file declares 192 files and `140 passed`. The current branch tracks 405 files and 258 tests. The manifest also lists paths no longer present and omits later engine, Workbench, workflow, and documentation files. Treat it as an earlier rebuild snapshot.

### `RELEASE_MANIFEST.json`

This file records the Workbench 1.0.1 release layer:

```text
engine tests      189
Workbench tests    61
combined          250
```

Later WB-11, timeout, oracle-free benchmark, and workflow changes make the continuing branch different from that release snapshot.

### Current calculated identity

Before this documentation-only pass:

```text
engine_source_sha256     c76fcee36d9e087c704bbefb1d057cff5a8780e33b5ff8c208c5235f6ed94c76
workbench_source_sha256  1f1d311a3112def9885e263688bac03aa4a878020b5c786a35da1dd57ed492ce
dependency_lock_sha256   bb0dd24142ccb66437fac60a38d07f9a95004a85a029c3f870da7d226e598b64
```

The historical release report/manifest contain older identities. That is expected for preserved snapshots, but readers must not use them to identify the current branch.

The new documents are stored outside every path hashed by `source_build_identity()`. Verification must confirm the three current hashes remain unchanged.

## Determinism and integrity mechanisms

V5 reproducibility relies on:

- canonical sorted JSON serialization;
- deterministic content-derived IDs;
- explicit seeds in controlled demos/benchmarks;
- event-key idempotence and conflict rejection;
- exact state, semantic, subsystem, and build fingerprints;
- immutable typed historical records;
- report staleness/tamper validation before commitment;
- deterministic stored-ZIP checkpoint bytes;
- content-addressed Workbench artifacts;
- explicit run/checkpoint ancestry;
- experiment manifests that can lock source identities;
- causal ablation/restoration attached to exact P/Q object IDs.

## Remaining reproducibility limits

1. Direct dependencies are pinned, but the complete transitive Python environment is not locked.
2. The frontend has no checked-in transitive npm lock; the checked-in `dist/` is therefore the canonical runnable frontend.
3. Wall-time fields naturally vary and should not be used as deterministic scientific output.
4. Large-organism scaling and long-duration resource behavior are not yet characterized broadly.
5. Hosted provider outputs are external and changing; Workbench preserves captures so they can become fixed teaching artifacts.
6. Plugin subprocesses are capability-limited by contract, not strongly sandboxed by the operating system.
7. The tracked corrected M19 raw JSON is missing even though the workflow and rerunnable harness exist.

## Minimum evidence package for a new claim

Include:

1. exact branch state and current build identities;
2. Python/platform/dependency environment;
3. curriculum or native source artifacts and their hashes;
4. seed and complete configuration;
5. initial checkpoint or construction procedure;
6. raw run events/checkpoints/result JSON;
7. all assertion definitions and negative controls;
8. causal ablation/restoration results when claiming object use;
9. false-positive and false-negative counts when claiming selective formation;
10. complete test/workflow results, including failures and exclusions;
11. a statement of what the experiment does not establish.
