# Long-horizon curriculum v0.1 — protocol design (NOT EXECUTED)

Parent: `test/obligation-substrate-v0` at `25d47fb038dae5c2a0e495fc38d4828e254005dc` (v0.65).
This document is a **design artifact**, not a frozen preregistration, implementation, experimental result, or assertion that the present runtime supports cross-cycle learning. Never label a run compliant merely because it completed 12,000 loop iterations.

## Mandatory feasibility gate

Before any 12,000-cycle run, a native-adapter audit must identify and test:

1. A genuine native state transition associated with each charged learning cycle, specifying what changes (claim, evidence, memory, workspace, obligation) and what is transient.
2. A teach operation that updates **only** the trial's private persistent learning state; a read-only replay that never teaches.
3. Checkpoint-and-restart preservation of that state, with independent exact replay from persisted bytes.
4. The exact hypothesis and evaluation interface for held-out requests without passing reference answers or group labels to the response path.
5. Per-cycle evidence, error/abstention, resource, and provenance accounting.
6. Baseline compatibility: unchanged v0.63/v0.64/v0.65 inputs and artifacts; unchanged 17 original checkpoints.
7. Existing domain 0–21 is **not** silently extended. Any new range, relation, task or representation must use an explicit new sibling adapter, with a separate preregistration and tests.

If the audit shows that private lesson state cannot survive a native cycle and reload, **STOP**: implement and independently verify persistence first. Do not use dictionary lookup or repeated canned requests as substitutes for cognitive learning.

## Trial architecture

Run four isolated arms, with three independent seeds per arm (12 private instances):

- A progressive curriculum: cumulative teaching through native interfaces.
- B rehearsal: matched teaching budget repeatedly rehearses a fixed training set.
- C activity control: matched native cycles, budget, and checkpoint schedule on unrelated eligible activity.
- D delayed-teaching control: receive equivalent progressive instruction later; controls for number of cycles since initialization.

Declare seeds, schedules, task versions, source manifests, all allowed training inputs and *disjoint* withheld test items in a separately durable immutable preregistration **before** producing any responses. Hidden tests must be inaccessible to the teaching pathway. Training and assessment isolation is checked per arm and per seed.

## Proposed native-cycle schedule (12,000 per arm)

- 0–1000: baseline, lesson provenance and persistence checks.
- 1001–2500: incremental successor evidence, separated by intervening unrelated native operations.
- 2501–4000: counting, addition, operand order; retain complete path and block traces.
- 4001–5500: incomplete evidence, native claim conflict, valid nulls, and abstention.
- 5501–7000: interference period, no original teaching repeated.
- 7001–8500: independently versioned new labels/task representations and out-of-sample structural probes.
- 8501–10000: previously learned concepts tested by new held-out cases; no answer feedback.
- 10001–12000: consolidate without providing final test answers; final reserve-only examination.

Probe cycle numbers: 0, 250, 500, 1000, 1500, 2500, 4000, 5500, 7000, 8500, 10000, 11000, 12000. Holdouts must be divided into disjoint pools to avoid contamination by prior probes.

**Proposed multi-domain learning is conditional** on a genuinely native and versioned teaching/evaluation path. Do not simulate an unsupported domain by relabeling answer fields.

## Strict cycle and replay accounting

A counted cycle must invoke a documented real native operation, record its pre/post checkpoint fingerprint, and classify changed canonical/private state vs read-only work. Repeated unchanged reads or zero-cost replay may be counted as evaluation activity but **never** charged as learning exposure. Record teaching episodes, elapsed runtime, CPU/GPU utilization where available, memory, cycles, workspace activity, and checkpoint size per arm.

Persist checkpoints at all probe boundaries and every 500 cycles, reload into a distinct process before progression at predetermined boundaries, and test bit-for-bit replay of full evidence receipts. Failure halts that arm and is retained in the full denominator.

Protect the v0.65 canonical, simulation, Attention, Lens and Council state from trial mutations. New private state must remain outside canonical promotion/resolution authority.

## Outcomes and predeclared comparisons

Primary: graded fresh held-out success after 12,000 cycles using correct/incorrect/abstention/invalid denominators, with comparison A vs B/C/D aggregated by independent seed. Secondary: retention since last instruction, interference loss, independent structural transfer, earlier-evidence paths in later answers, attempts/teacher interventions per comparable new skill, and incremental compute per new skill. Report confidence intervals or per-seed ranges, not merely one pooled total.

Controls against spurious learning: no teacher answer leakage; no grader imports into response code; exact-null copies reproduce their nominal equivalent; wrong evidence must not magically score as correct; swapped checkpoint/evidence/source identities must fail closed; no retroactive exclusions; no held-out reuse as training cases; no silently expanded arithmetic ceiling; no "correct-only" denominators. Any discovered contamination invalidates that cohort.

Pass conditions must be set numerically in a **subsequent freeze** only after feasible tasks and their complete fresh pools are independently counted; this document does not fabricate those pools or criteria. If the available 0–21 domain lacks genuinely disjoint assessment material, STOP and define a new independent cohort before implementation.

## Required artifacts

A frozen design manifest (versioned sibling), preregistration (inputs/holdouts/seed/runtime), manifest of source code hashes, per-arm immutable learning histories, native response-before-grade batches, external grades, checkpoint archives, retention/transfer reports, failures/invalid/abstentions, and a final negative-results-inclusive research report.

## Authority and interpretation boundary

No grades, persistent evidence, lesson or simulation from this curriculum authorizes canonical resolution, policy revision, real-world action, autonomous goal generation or a claim of generalized cognition. Stored facts are not automatically generalization. Persistence, transfer, increased learning efficiency and causal self-repair are separate hypotheses. A long run with no genuine persistent teaching pathway is a **negative feasibility result**, not 12,000 cycles of learned experience.

## Work order

1. Inventory actual native learning API and persistence route.
2. Build native feasibility adapter and adversarial persistence tests.
3. Design fresh disjoint cohort, enforce test leakage barriers, freeze thresholds.
4. Execute 1,000-cycle pilot with matched controls and restart probes.
5. Inspect pilot feasibility and only then freeze and execute 12,000 cycles on 12 arms.
6. Publish full complete before-grade responses, external evaluations and adverse results.
