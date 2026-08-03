# Verdant Workbench WB-07
## Experiment Manager / Verification Packages

**Status:** Complete and verified  
**Baseline:** WB-06 Living Explorer / Milestone 19 Verdant engine  
**Purpose:** Generalize the existing M19 benchmark from a special Python harness into a Workbench-native, immutable, reproducible laboratory experiment.

## Exit criterion

WB-07 is complete when a researcher can freeze the four-arm Ethomorphism benchmark as an immutable experiment, launch it from Workbench, inspect its results and causal controls, reproduce the same scientific result from the frozen protocol, fork the protocol without rewriting its parent, and export self-contained verification artifacts.

The implementation now satisfies that criterion for protocol `ethomorphism.m19.v1`.

## 1. `.vexp` is now a first-class laboratory artifact

Workbench introduces `verdant.experiment.v1` and the `.vexp` package format.

A frozen source experiment contains:

```text
manifest.json
curriculum/compiled_commands.json
expected_assertions.json
hashes.json
```

The manifest explicitly records:

```text
experiment ID / project / version / parent experiment
protocol ID
M19 engine baseline
seed
state dimension
relation type
ordered curriculum lock
four experiment arms
curriculum SHA-256
curriculum event count
metric list
intervention list
expected machine assertions
```

Editing experiment parameters never rewrites a prior package. It creates a new version or an explicit fork.

## 2. The M19 input is embedded exactly

The Workbench reference template uses the same M19 30-event primitive curriculum.

Reference curriculum SHA-256:

```text
38ffb6c25056b7f0134e5f2dd923fe08b9cca05318a66f38e3c7582eb102ce4b
```

The controlled WB-07 proof froze a `.vexp`, reopened the embedded curriculum and confirmed:

```text
manifest event count      30
embedded command count    30
curriculum hash            exact M19 reference hash
```

The hidden target family abstraction remains evaluator-side exactly as in M19.

## 3. Four-arm experimental isolation

The experiment protocol still contains:

```text
A — canonical symbolic graph
B — graph + ECWF
C — developmental plasticity, fold promotion disabled
D — full earned-fold Verdant
```

The complete protocol executes outside the Workbench UI/control thread in a dedicated experiment process.

Inside that worker, every arm is constructed by the M19 harness as an independent kernel/runtime. No A/B/C/D arm shares canonical cognitive state with another arm.

The current worker boundary is therefore:

```text
Workbench control plane
        |
        v
Dedicated experiment process
        |
        +-- independent A kernel/runtime
        +-- independent B kernel/runtime
        +-- independent C kernel/runtime
        +-- independent D kernel/runtime
```

WB-07 deliberately does **not** run all four heavy arms concurrently on ordinary machines. Concurrent process-per-arm execution produced severe resource contention in the build container and would contaminate descriptive timing telemetry. State isolation is preserved without turning machine contention into part of the benchmark.

## 4. Declared metrics and interventions

The frozen experiment manifest now explicitly states what the protocol will measure and intervene on rather than leaving those operations implicit in UI code.

Initial metrics include:

```text
local reconstruction work / success
promoted P structures
Q structures
family-comparison work
family selectivity
plastic density / edge ratio / degree
persistent bytes
```

The M19 reference interventions are declared as:

```text
D: exact P ablate -> probe -> restore
D: exact Q ablate -> family probe -> restore
D: typed structural challenge -> refolding assay
C/D: bounded-plasticity saturation stress
```

## 5. Result packages

A completed experiment run produces a second immutable verification artifact containing:

```text
source_experiment.vexp
manifest.json
curriculum/compiled_commands.json
results/summary.json
results/scientific_result.json
results/worker_isolation.json
results/assertions.json
verification.json
hashes.json
```

The reference source package is about 4.2 KB and the reference result/verification package is about 13 KB because the synthetic benchmark is small.

All package members are SHA-256 checked.

## 6. Scientific-result normalization

Wall-clock timings are useful engineering telemetry but are not deterministic scientific outputs.

WB-07 therefore computes a normalized scientific result by removing only declared descriptive nondeterministic telemetry; currently this is each arm's `training_wall_seconds` field.

Everything else in the M19 summary remains in the normalized result.

The controlled reference run produced:

```text
scientific-result SHA-256
c7bc5180354a8a20a3db081000a9c5124ffcbd77da4f860d0ee6214c937c36a7
```

Workbench then executed the same frozen experiment again during **VERIFY BY REPRODUCTION**.

The reproduced scientific-result SHA-256 was exactly:

```text
c7bc5180354a8a20a3db081000a9c5124ffcbd77da4f860d0ee6214c937c36a7
```

Therefore:

```text
H(reference scientific result) = H(reproduced scientific result)
```

and the experiment run was marked verified.

## 7. Reference causal results survived Workbench orchestration

The Workbench-native experiment reproduced the M19 causal measurements.

P compilation:

```text
WITH P       1
ABLATE P     7
RESTORE P    1
```

Q family recognition:

```text
WITH Q       3
ABLATE Q     8
RESTORE Q    3
```

The full D arm still had:

```text
concepts                     20
canonical relations          15
plastic associations         15
promoted P structures         5
Q structures                  1
held-out local work           1
family comparison work        3
```

The refolding assay still returned a two-child split with parent preservation, dormancy after successful refolding, lineage preservation and unchanged semantic counts.

## 8. Claim inspector

The Experiment Manager no longer needs presentation text to assert that a result passed.

Each frozen experiment carries explicit machine assertions such as:

```text
headline_checks.d_forms_earned_structures == true
headline_checks.d_forms_higher_order_q == true
headline_checks.p_ablation_restoration_is_causal == true
headline_checks.q_ablation_restoration_is_causal == true
headline_checks.refolding_preserves_lineage == true
...
```

The result package stores, for every assertion:

```text
path
operator
expected value
actual value
pass/fail
error, if unresolved
```

The browser Experiment Manager exposes these records as its claim inspector.

## 9. Forking

A frozen experiment can now be forked.

The controlled proof created a child experiment with seed `1902` and verified:

```text
child.parent_experiment_id == parent.experiment_id
child artifact SHA-256 != parent artifact SHA-256
parent artifact remains integrity-valid
```

A fork is therefore another immutable experimental branch rather than an edit to historical protocol state.

## 10. Workbench UI

The **Experiments** surface is now operational in the dependency-free browser client.

It supports:

```text
load reference protocol parameters
freeze .vexp
list/select frozen experiments
inspect manifest/resource/intervention lock
run experiment
poll run status
inspect arm metrics and causal results
inspect machine assertions
verify by reproduction
fork experiment
download source .vexp
download result/verification .vexp
```

The retained React/TypeScript source has also been extended with the experiment surface and API bindings.

## 11. ADR-014

WB-07 adds:

```text
docs/workbench/adr/ADR-014.md
```

The architectural rule is:

> Experiments are immutable verification artifacts. UI claims must be derived from frozen inputs, packaged results and machine-checkable assertions; reproduction compares a declared deterministic scientific-result hash rather than wall time.

## 12. Verification state

Engine regression suite remains unchanged:

```text
124  core/kernel/media/workspace/etc.
 32  M12-M15
 16  M16-M17
  9  M18
  8  M19
---
189 engine tests
```

Workbench now contains:

```text
43 integration tests
```

including seven WB-07 experiment-manager tests covering package integrity, curriculum identity, experiment lineage, assertion evaluation, run/result persistence, reproduction logic, API/download surfaces and UI controls.

Combined verified state:

```text
189 engine
 43 Workbench
---
232 verified tests
```

The known very-long-single-process pytest slowdown remains present in this environment. Heavy suites were again verified in fresh partitions rather than treating infrastructure timeout behavior as a cognitive or Workbench test failure.

## 13. Machine proof

The controlled WB-07 proof passes all gates:

```text
reference curriculum hash locked                   PASS
30 input events embedded                           PASS
all M19 headline checks                            PASS
all manifest assertions                            PASS
experiment outside Workbench process               PASS
A/B/C/D canonical state isolation                  PASS
P 1 -> 7 -> 1 causal result                        PASS
Q 3 -> 8 -> 3 causal result                        PASS
reproduction scientific hash equality              PASS
experiment marked verified                         PASS
fork parent lineage                                PASS
fork immutable artifact separation                 PASS
source package integrity                           PASS
result package integrity                           PASS
```

Machine proof:

```text
workbench/artifacts/wb07_experiment_manager_proof.json
```

Reference export:

```text
workbench/artifacts/wb07_m19_reference_experiment.vexp
```

Verification export:

```text
workbench/artifacts/wb07_m19_verification_package.vexp
```

## 14. Boundary of the milestone

WB-07 generalizes **the existing M19 Ethomorphism protocol** into the first Workbench experiment protocol. It does not yet claim that arbitrary user-authored experimental Python is safely sandboxed or that every future benchmark can be described without adding a typed `ExperimentProtocol` implementation.

That future extensibility belongs to WB-09's plugin/SDK hardening.

Likewise, result verification demonstrates deterministic reproduction of the current synthetic protocol. It does not transform the benchmark's narrow scientific scope into a claim of general intelligence.

## Next

### WB-08 — Provider Connections

The next milestone connects optional external/local curriculum assistants to the editable teaching-record architecture created in WB-04.1.

The crucial boundary is already established:

```text
provider request
    -> captured raw provider response
    -> editable teaching record
    -> human review/edit
    -> deterministic .vcurr compiler
    -> Verdant
```

Provider output will be captured and replayable; it will never silently become Verdant cognition.
