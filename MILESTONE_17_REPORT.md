# Verdant Minds Independent Rebuild — Milestone 17

## Layered Concept Formation

Milestone 17 allows **earned structures to become the primitives of another earned structure**.

The developmental path is now:

```text
primitive experience
→ local plasticity
→ earned relational structure P
→ cross-symbolic P↔P verification
→ recurring family of verified P operands
→ higher-order candidate
→ independent higher-order gates
→ Council authorization
→ opaque layered structure Q
→ Q used on a novel P
```

The central boundary remains unchanged:

> A recurring family of earned structures is not automatically a semantic category.

`Q` is a higher-order computational object whose constituents are lower-order `P` objects. It receives no human category name and promotion does not install a canonical concept, relation, or claim.

## New runtime package

```text
verdant_hierarchy/
    __init__.py
    pipeline.py
    demo.py
```

Milestone 17 adds canonical records for:

```text
HierarchyPolicy
HierarchyQualityVector
HierarchyCandidateRecord
HierarchyObservationReport
HierarchyObservationEvent
LayeredStructureRecord
HierarchyPromotionReport
HierarchyPromotionEvent
LayeredStructureAvailabilityEvent
LayeredProbeCost
LayeredProbeReport
LayeredProbeEvent
```

## How a higher-order candidate forms

The hierarchy observer does **not** inspect primitive labels and does not receive a rule such as:

```python
if three path-shaped structures:
    create("path family")
```

It starts from already committed Milestone 16 interaction history.

Only `VERIFIED_ALIGNMENT` interactions can establish higher-order membership. A high continuous-field score that failed symbolic verification remains boundary pressure, not membership evidence.

The observer builds bounded connected families of available promoted structures and evaluates a quality vector:

```text
recurrence
pair_coverage
alignment_cohesion
prototype_cohesion
boundary_selectivity
evidence_diversity
causal_utility
```

`causal_utility` is deliberately zero at promotion. Milestone 17 does not pre-credit usefulness merely because a candidate looks coherent; usefulness is tested afterward on a novel structure.

## Higher-order promotion gates

A candidate currently requires:

```text
sufficient verified-interaction recurrence
AND sufficient pair coverage
AND symbolic alignment cohesion
AND continuous prototype cohesion
AND boundary selectivity
AND lower-level evidence diversity
```

The candidate identity is determined by its exact member structure IDs:

```text
hierarchy_candidate = stable_id(member_structure_ids)
```

If all gates pass, the existing Council pathway can authorize:

```text
Q_<opaque-id>
```

as a `LayeredStructureRecord` with depth `2`.

Its primitives are earned `StructureRecord` operands rather than canonical concepts.

## Structure-sensitive prototype

Each member `P` already has a Milestone 16 relational signature whose encoding ignores concept labels and IDs and uses relational invariants.

Milestone 17 forms the candidate's continuous prototype by averaging and normalizing those member signatures.

The prototype therefore represents the **common cross-symbolic shape of the earned structures**, not the English labels of their primitive concepts.

This geometry is still produced by a hand-designed encoder. Verdant has not yet learned the encoder itself.

## Controlled formation experiment

Three independently earned four-member path structures were grown from disjoint primitive symbols:

```text
P_A: A1 — A2 — A3 — A4
P_B: B1 — B2 — B3 — B4
P_C: C1 — C2 — C3 — C4
```

Each `P` was earned through the existing low-level developmental pathway before Milestone 17 observed them.

They were then allowed to interact through Milestone 16.

Higher-order candidate progression:

| Verified interaction events | Pair coverage | Alignment cohesion | Prototype cohesion | Status |
|---:|---:|---:|---:|---|
| 1 | 0.6667 | 0.9797 | 0.99925 | tracking |
| 2 | 1.0000 | 0.9789 | 0.99925 | tracking |
| 3 | 1.0000 | 0.9789 | 0.99925 | eligible |

The candidate then received Council authorization and was promoted as:

```text
Q_6fff321a318a
```

The promotion-time quality vector was:

```text
recurrence             1.0000
pair_coverage          1.0000
alignment_cohesion     0.9789
prototype_cohesion     0.99925
boundary_selectivity   1.0000
evidence_diversity     1.0000
causal_utility         0.0000   # intentionally not assumed at promotion
```

## The novel-task test

Only **after Q already existed**, the controlled demo grew two additional earned structures:

```text
P_D = a new path built from unseen D1..D4 symbols
P_S = an unrelated four-member star control
```

Neither was a constituent of `Q` during formation.

The task was:

> Given the novel earned structure `P_D`, recover the previously known structures that belong to the same verified structural family.

### With Q available

```text
layered prototypes compared    1
base structures compared       1
symbolic verifications         1
total comparison work          3
matched family members         3
```

The returned family was exactly the three structures from which Q had formed.

### Low-level audit baseline

Without using Q, the same task required scanning the four other available base structures:

```text
layered prototypes compared    0
base structures compared       4
symbolic verifications         4
total comparison work          8
matched family members         3
```

Under this deliberately narrow structural-comparison accounting:

```text
comparison compression gain = (8 - 3) / 8 = 0.625
                            = 62.5%
```

This is **not** a claim of a 62.5% end-to-end AI speedup. It means one promoted higher-order operand replaced a repeated scan over its lower-level family in this controlled task.

The full baseline path is computed as an audit shadow path so the report can compare costs. That audit calculation is not included in the runtime-work count when Q succeeds.

## Causal ablation and restoration

The decisive sequence was:

```text
WITH Q
→ novel P_D matched the 3-member family
→ comparison work = 3

ABLATE Q
→ same P_D still matched the same 3-member family
→ fallback comparison work = 8

RESTORE Q
→ same P_D again matched the same 3-member family
→ comparison work = 3
```

So:

```text
WITH Q       work=3   gain=0.625
ABLATE Q     work=8   gain=0.000
RESTORE Q    work=3   gain=0.625
```

The lower-level structures were never deleted during ablation. The changed cost follows the availability of the higher-order object itself.

This establishes a narrow but real causal result:

> A structure whose constituents were themselves previously manufactured structures became a reusable higher-order operand, and its presence reduced the work required to classify a novel independently earned structure into that structural family.

## Unrelated control

The independently earned star control was probed against the same Q.

It did **not** enter the higher-order family:

```text
disposition             fallback_member_scan
matched structures      0
comparison gain         0
```

This preserves the Milestone 16 rule that continuous similarity alone cannot establish a structural analogy.

## What is recursive now

The runtime now has the first explicit two-level developmental hierarchy:

```text
primitive concepts / learned traces
        ↓
P = earned relational structure
        ↓
verified P↔P interaction
        ↓
Q = earned structure whose members are P operands
```

That is qualitatively different from a human-authored ontology tree: the lower-order operands had to earn existence first, then their recurrent verified interaction had to earn the higher-order operand.

## Cultivation runner V4

`run_verdant_cultivation.py` now exposes the hierarchy directly.

New commands include:

```text
interact <P>      cross-symbolic P interaction and automatic Q observation
hierarchy         inspect Q candidates and promoted layered structures
promoteq <id>     Council-gated Q promotion
qprobe <P>        classify a P using Q when available
qcompare <P>      WITH Q → ABLATE Q → RESTORE Q
qablate <Q>       disable a layered structure
qrestore <Q>      restore it
```

Exports now preserve hierarchy candidates, layered structures, promotion lineage, and layered probes separately from taught semantics and lower-level learned structures.

## Tests

Milestone 17 adds eight tests covering:

1. higher-order candidate formation from already-earned structures;
2. opaque layered promotion without semantic truth creation;
3. novel-structure use of the layered operand;
4. causal ablation and restoration of the higher-order advantage;
5. rejection of a symbolically different structural control;
6. pure hierarchy inspection plus stale-policy rejection;
7. exact checkpoint persistence of layered structures and probes;
8. semantic-firewall preservation during layered use.

The complete current test set contains **172 tests**.

In this container, one very long monolithic pytest process becomes abnormally slow late in the run. The complete suite was therefore re-run in two fresh-process verification batches:

```text
55 passed
117 passed
-------------
172 passed
```

No test failures occurred. This process-length slowdown should be profiled separately as a test/runtime performance issue rather than silently ignored.

## What Milestone 17 does not establish

Milestone 17 does **not** establish:

- that Q represents a human semantic category;
- that Verdant learned the relational encoder used to create the continuous prototype;
- arbitrary-depth recursive `Q → R → ...` formation;
- autonomous theorem or law discovery;
- refolding under contradiction;
- semantic transfer from one domain to another in the human sense;
- general intelligence or proto-intelligence.

The correct claim is narrower:

> Verdant can now manufacture an opaque higher-order object from the verified interactions of previously manufactured lower-order objects, and that higher-order object can become causally useful on a later structure that was not one of its constituents.

That is the Milestone 17 exit criterion.

## Next milestone

### Milestone 18 — Refolding Under Contradiction

The next question is whether an earned structure can remain plastic after compilation.

The target sequence is:

```text
learn
→ earn P / Q
→ use it successfully
→ introduce evidence incompatible with part of the structure
→ detect localized tension
→ selectively unfold the affected structure
→ revise / split / remain unresolved
→ preserve lineage to the pre-contradiction structure
→ test later use again
```

The important result will not be merely "the score changed."

It will be whether a mature cognitive object can be **opened, challenged, structurally changed, and still remain historically reconstructable** rather than either staying rigid or being deleted and relearned from scratch.
