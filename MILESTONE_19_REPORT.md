# Verdant Minds Independent Rebuild — Milestone 19

## Ethomorphism Benchmark Harness

Milestone 19 freezes the conceptual architecture at the end of Milestone 18 and turns the preceding claims into a repeatable comparative laboratory protocol.

No new cognitive ontology is introduced here. The new package is an **external benchmark harness**:

```text
verdant_benchmarks/
    __init__.py
    ethomorphism.py
    demo.py

run_ethomorphism_benchmark.py
```

The benchmark asks a narrower and harder question than the developmental demos:

> When the same primitive curriculum is supplied to weaker and stronger versions of the architecture, which measured advantages actually follow the earned-structure machinery, and do those advantages disappear under controlled ablation?

## Four experimental arms

All arms receive the same ordered 30-event primitive curriculum, the same kernel seed (`1901`), the same field dimension (`16`), the same primitive relation type (`linked`), and the same event order.

The curriculum SHA-256 for the reference run is:

```text
38ffb6c25056b7f0134e5f2dd923fe08b9cca05318a66f38e3c7582eb102ce4b
```

The experimental arms are:

```text
A — canonical symbolic graph only
B — canonical graph + ECWF state/resonance
C — developmental workspace + local plasticity, fold observation/promotion disabled
D — full earned-fold Verdant through M18
```

C and D share the same developmental workspace/plasticity policy. Their intended difference is the ability to observe, promote, compile, interact with, and hierarchically organize earned folds.

### What is taught

Each synthetic world is built only from opaque labels and primitive undirected `linked` edges. Example:

```text
A1 — A2 — A3 — A4
```

The hidden benchmark family label (`path`) exists **only in the evaluator**. It is not placed in `ExperienceCommand`, command metadata, concept labels, relation types, claims, evidence details, or Verdant state.

This leakage condition is explicitly regression-tested.

The target higher-order abstraction therefore remains withheld even though the primitive edges themselves are deliberately supplied to every arm. This makes the symbolic graph a meaningful baseline instead of intentionally crippling it.

## Protocol

Three structurally equivalent but symbolically disjoint path worlds are trained first:

```text
WORLD A     A1 — A2 — A3 — A4
WORLD B     B1 — B2 — B3 — B4
WORLD C     C1 — C2 — C3 — C4
```

Only after that family-learning stage are two new controls supplied:

```text
HELD-OUT D  D1 — D2 — D3 — D4

STAR CONTROL
               S2
                |
          S3 — S1 — S4
```

The full D arm may earn `P` structures from the primitive worlds and a higher-order `Q` from the first three worlds before D and the star control exist.

The harness then measures:

- held-out local relational reconstruction;
- formation of P and Q;
- P ablation and restoration;
- Q ablation and restoration;
- held-out structural-family recognition;
- star-control selectivity;
- lineage-preserving refolding;
- a separate long-run bounded-plasticity saturation assay;
- persistent-state size and wall time as descriptive telemetry only.

## Reference results

### Arm state after the common curriculum

| Arm | Concepts | Canonical relations | Plastic associations | P structures | Q structures | Persistent bytes |
|---|---:|---:|---:|---:|---:|---:|
| A graph | 20 | 15 | 0 | 0 | 0 | 155,098 |
| B graph + ECWF | 20 | 15 | 0 | 0 | 0 | 155,103 |
| C plastic / no folds | 20 | 15 | 15 | 0 | 0 | 875,482 |
| D full Verdant | 20 | 15 | 15 | 5 | 1 | 1,100,166 |

The extra storage in C/D is real overhead and should not be hidden. The current rebuild favors auditability and JSON/Pydantic persistence over storage efficiency; later scaling work should reduce that overhead without changing benchmark semantics.

## Local reconstruction

All four arms reconstruct the same held-out four-node world correctly from a single cue.

Measured low-level reconstruction work:

```text
A graph              7
B graph + ECWF       7
C plastic/no-fold    7
D full Verdant       1
```

D uses the independently promoted held-out `P_D` as one compiled operand.

This is not a wall-clock speedup claim. `work` is a structural accounting unit: concepts inspected plus low-level relations/associations traversed. The important causal control is below.

## P causality

The full D arm is probed three times while leaving the lower substrate intact:

```text
WITH P       work = 1
ABLATE P     work = 7
RESTORE P    work = 1
```

All three conditions reconstruct the same member set.

Therefore the saved reconstruction work follows the exact earned structure rather than a hidden change to the lower graph.

## Higher-order Q causality

The first three independently earned path structures are allowed to interact and form one opaque higher-order `Q` before the held-out D world exists.

When later `P_D` is tested against that family:

```text
WITH Q       comparison work = 3
ABLATE Q     comparison work = 8
RESTORE Q    comparison work = 3
```

The same three family members are returned in all three conditions.

The star control is not admitted to the family.

Again, the correct claim is causal and local:

> the higher-order object compresses this benchmark's family-recognition operation, and the advantage follows Q under ablation/restoration.

The evaluator-side family checks for A/B/C are **capability controls**, not evidence that those arms autonomously manufactured a family concept. World boundaries are supplied only to the scorer so the same underlying shape can be checked across arms.

## Useful negative control: ECWF alone

The B arm does not receive a special success just for possessing a continuous field. In the reference curriculum every primitive edge uses a deliberately non-informative shared feature cue, and B's top-1 ECWF exact-cue test is false.

This is useful rather than embarrassing: the benchmark does not reward `ECWF exists` as if that alone demonstrated structural abstraction. The cross-symbolic advantage in D comes from earned relational structures and their structure-sensitive interface, not from a trivial feature label leak.

## Refolding assay

A separate six-member full-D structure is cultivated as two internally coherent triangles joined by three cross-links. Each cross-link receives two independent typed contradiction observations.

Result:

```text
disposition             SPLIT
children                2
child A                  ra1 ra2 ra3
child B                  rb1 rb2 rb3
parent record preserved yes
parent dormant           yes
lineage preserved        yes
semantic counts changed  no
```

The refolding assay therefore reproduces the M18 result inside the benchmark harness rather than relying on a demo-only claim.

## Long-run anti-saturation assay

The saturation test intentionally isolates the **shared bounded-plasticity substrate** in C and D by disabling fold observation during this specific stress run. Otherwise the test would conflate plastic saturation with candidate-enumeration cost.

A 16-concept ring-plus-skip network produces:

```text
plastic associations    32
edge/node ratio          2.0    (cap 4.0)
maximum degree           4      (cap 8)
undirected density       0.2667
```

Both C and D remain inside the explicit degree and edge-ratio caps.

This is not a proof of asymptotic health. It is a regression assay showing that the old V4 near-clique failure mode does not appear in this controlled stress population.

## Headline checks

Every reference-run gate passed:

```text
same external curriculum count across arms     PASS
target family abstraction absent from input    PASS
C has plasticity but no promoted folds          PASS
D forms earned P structures                     PASS
D forms higher-order Q                          PASS
all arms reconstruct held-out primitive world  PASS
D uses compiled P                               PASS
P ablation/restoration causal                   PASS
Q ablation/restoration causal                   PASS
star-control selectivity                        PASS
refolding lineage preservation                  PASS
refolding semantic firewall                     PASS
C plastic stress within caps                    PASS
D plastic stress within caps                    PASS
```

## Test state

Milestone 19 adds eight benchmark regression tests covering:

1. deterministic curriculum identity and target-label leakage prevention;
2. C/D substrate parity with fold promotion isolated to D;
3. held-out reconstruction across all four arms;
4. D's selective held-out family recognition;
5. P and Q ablation/restoration causality;
6. refolding lineage and semantic-firewall preservation;
7. anti-saturation caps;
8. deterministic full-D training.

The repository now contains:

```text
189 tests
```

All 189 were verified passing in fresh pytest partitions. A single very long pytest process remains slower in this container, so the milestone records the partitioned verification rather than presenting a timeout as a failure.

Verified partitions:

```text
124 passed   legacy/kernel/media/workspace/etc.
32 passed    M12–M15 developmental/fold tests
16 passed    M16–M17 interaction/hierarchy tests
9 passed     M18 refolding tests
8 passed     M19 benchmark tests
-----------------------------------------------
189 passed
```

## What Milestone 19 supports

The benchmark now supports the following narrow statement:

> Under a controlled synthetic curriculum, Verdant can manufacture opaque relational objects from primitive experience, use them as causal compiled operands, organize several such objects into a useful higher-order operand, lose the measured advantages when the exact objects are ablated, recover them on restoration, reject a structurally different control, preserve differentiation under bounded plasticity, and revise a mature fold without erasing its lineage.

## What Milestone 19 does not support

It does **not** establish:

- general intelligence or proto-AGI;
- autonomous discovery of natural-language scientific laws;
- a learned semantic manifold;
- superiority to modern neural models;
- real-world compute or energy efficiency;
- asymptotic scaling to millions of structures;
- autonomous identification of which arbitrary sensory statement contradicts which fold;
- that the current hand-designed structure signature is the final cross-symbolic representation.

The benchmark is intentionally synthetic because every primitive, intervention, and hidden answer can be audited.

## Next milestone

### Milestone 20 — Explorer / Scientific Visualization

The architecture is now instrumented enough to stop adding cognitive machinery for a while.

Milestone 20 should visualize the **same real benchmark run** at two levels:

```text
STORY VIEW
experience → association → P → P interaction → Q → contradiction → refold

FORENSIC VIEW
exact evidence IDs
plastic strengths
gate vectors
promotion decisions
workspace costs
ablation deltas
role mappings
lineage
benchmark-arm comparisons
```

The scenery should never replace the evidence. Both views should be projections of the same exported run data.
