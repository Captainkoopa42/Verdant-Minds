# Verdant Minds Independent Rebuild — Milestone 13

## Local Plasticity Without Saturation

Milestone 13 restores a carefully bounded form of V4-style developmental association to the clean rebuild.

The new path is:

```text
experience
→ evidence and optional taught semantics
→ ECWF field update
→ resonance possibilities
→ bounded workspace
→ local nonsemantic association update
→ later association-driven recall into workspace
```

The milestone deliberately does **not** convert coactivation into canonical semantic relations. Its new associations are developmental traces that can influence later cognition while remaining distinct from evidence-backed truth.

## Why this milestone exists

Old V4 showed that repeated activation could create persistent structures, but later runs also showed the corresponding failure mode: association pressure could become so broad that relational contrast collapsed and much of the graph approached clique-like density.

Milestone 13 therefore restores plasticity only under explicit anti-saturation constraints.

A learned local association must now live inside all of the following bounds:

- only concepts in the current plasticity scope can form new local traces;
- new associations require current evidence to touch at least one endpoint;
- only admitted foreground items above a local learning threshold contribute;
- association recall is forbidden from reinforcing itself merely because it recalled a neighbor;
- creation and reinforcement are capped per cycle;
- unreinforced local associations decay;
- every concept has a total plastic-strength budget;
- every concept has a hard maximum plastic degree;
- the whole plastic graph has an edge/node cap;
- weak traces are pruned;
- all changes preserve exact evidence and workspace lineage.

## New runtime package

Milestone 13 adds:

```text
verdant_plasticity/
    __init__.py
    pipeline.py
    demo.py
```

The public developmental operation remains:

```python
VerdantDevelopmentPipeline.advance(kernel, experience_command)
```

but one heartbeat now contains four audited commits:

```text
apply experience
commit resonance
commit workspace
commit bounded local plasticity
```

## New canonical records

The kernel now persists:

```text
PlasticityPolicy
PlasticityAssociationRecord
PlasticityPairAssessment
PlasticityReport
PlasticityEvent
```

These records are part of canonical run state and checkpoint replay, but they are **not canonical semantic relations**.

A plastic association joins two existing concepts and contains:

- deterministic association identity;
- current bounded strength;
- exposure count;
- preserved evidence lineage;
- creation/update cycles;
- last true reinforcement cycle;
- source workspace event.

## Direct co-presence creates only a weak trace

Current evidence gives co-present concepts a bounded activation floor. This is intentional: the system should be allowed to remember that two things repeatedly appeared together even before ECWF has learned a strong resonance between them.

That weak trace is not accepted as meaning.

It must survive:

```text
repetition
+ decay
+ competition
+ strength budget
+ degree cap
+ global edge cap
```

before it can become a stable local feature of developmental history.

## The association layer is causally active

This is the most important difference between Milestone 13 and passive logging.

A sufficiently strong learned association can now place its opposite endpoint back into a later workspace as a `LOCAL_ASSOCIATION` recall candidate.

Controlled sequence:

```text
KREN alone
→ no TAR local recall

KREN + TAR repeatedly
→ KREN↔TAR plastic trace strengthens

KREN alone later
→ TAR appears as a learned local-recall candidate
```

Ablating the plastic association removes that local-recall candidate while leaving the rest of the kernel intact.

Therefore the learned trace is already causally operative in later foreground organization.

It is still only one-hop recall. Milestone 13 does not permit uncontrolled recursive spreading through plastic associations.

## Self-reinforcement is blocked

Association-driven recall may influence the workspace, but `LOCAL_ASSOCIATION` items are explicitly excluded from the plasticity coactivation calculation.

Therefore:

```text
association A-B
→ recalls B when A is current
```

cannot by itself become:

```text
A recalls B
→ recall counts as evidence that A-B is strong
→ A-B strengthens
→ stronger recall
→ ...
```

True reinforcement must still come from the non-association foreground: current evidence and independently admitted resonance.

This is an explicit defense against runaway attractor stickiness.

## Homeostatic competition

Each concept has a configured total plastic-strength budget.

If the sum of its incident plastic associations exceeds that budget, all competing edges are proportionally normalized. This makes new learning compete with existing local organization instead of allowing total associative influence to grow without limit.

The default policy is currently:

```text
minimum foreground score         0.32
current-evidence activation floor 0.62
creation threshold                0.52
reinforcement threshold           0.34
initial strength                  0.08
learning rate                     0.20
decay rate                        0.025
minimum retained strength         0.035
maximum degree                    8
maximum edge/node ratio           4.0
strength budget per concept       2.4
maximum new associations/cycle    6
maximum reinforcements/cycle      12
```

These values are scaffolding for controlled experiments, not claims about optimal cognitive dynamics.

## Controlled demonstration

The Milestone 13 demo uses meaningless labels so English semantics cannot explain the effect.

The main pair grows as follows:

```text
KREN↔TAR plastic strength
0.1941
0.2940
0.3987
0.4880
0.5642
0.6290
```

Before the pair is learned:

```text
KREN probe → no local TAR recall
```

After learning:

```text
KREN probe → TAR recalled through learned local association
```

The demo then trains 12 additional meaningless concepts through overlapping ring and skip-link neighborhoods under stricter stress-test caps.

Measured final state:

| Measurement | Result |
|---|---:|
| Concepts | 14 |
| Canonical semantic relations | **0** |
| Plastic associations | 25 |
| Plastic edge/node ratio | 1.7857 |
| Plastic undirected density | 0.2747 |
| Maximum plastic degree | **4** |
| Configured maximum degree | **4** |
| Maximum total strength on one concept | 0.9018 |
| Configured strength budget | 1.6 |
| Plasticity events | 80 |
| TAR recalled from later KREN-only cue | **yes** |
| Semantic relation firewall | **held** |

This is not a claim that the associations are abstractions or understanding. It demonstrates something narrower:

> bounded learned local structure can survive, compete, and alter later foreground cognition without becoming semantic truth or saturating the graph.

## Audit and replay behavior

Plasticity follows the rebuild's existing inspect/commit discipline:

```text
inspect current workspace + current plastic state
→ deterministic PlasticityReport
→ reproduce report from current state
→ commit exact proposed association set
→ append PlasticityEvent and TransitionRecord
```

Inspection is pure.

Reports become stale when policy or relevant state changes.

Exact checkpoint round-trips preserve both the current plastic association map and the complete plasticity event history.

Exact experience replay does not create duplicate plasticity events.

## New tests

Milestone 13 adds tests for:

1. repeated coactivation creating and strengthening a nonsemantic association;
2. local decay when an association is not reinforced;
3. pure inspection and stale-report rejection;
4. replay not duplicating plasticity;
5. degree and edge-ratio caps preventing clique growth;
6. per-concept strength-budget competition;
7. exact checkpoint recovery;
8. deterministic identical-history replay;
9. causal local recall plus ablation of the learned association.

Full suite result:

```text
140 passed
```

## What Milestone 13 does **not** establish

It does not establish:

- semantic abstraction;
- autonomous concept invention;
- fold/object formation from relation history;
- multi-hop associative reasoning;
- cross-domain invariant extraction;
- a learned internal logic;
- intelligence or proto-intelligence.

The plastic associations are intentionally below that bar.

What they give us is the developmental substrate required for the next experiment.

## Next milestone

### Milestone 14 — Earned Relational Structures

The next question is no longer whether repeated local interaction can leave a useful trace.

It is:

> When does a changing set of local relations deserve to become one persistent thing the system can think with?

Milestone 14 should introduce an explicitly nonsemantic `StructureCandidate` layer that watches canonical relations, plastic associations, field history, workspace recurrence, reconstruction performance, and boundary selectivity.

Promotion should require multiple independent tests rather than a single scalar threshold.

Only after a candidate earns promotion should Verdant receive a new reusable cognitive operand.
