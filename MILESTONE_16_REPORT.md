# Verdant Minds Independent Rebuild — Milestone 16

## Cross-Symbolic Structure Interaction

Milestone 16 adds the first explicit interaction path between **independently earned structures with disjoint surface symbols**.

The developmental architecture now supports:

```text
experience
→ bounded plastic relations
→ earned StructureCandidate
→ promoted opaque structure P
→ compiled use of P
→ structure-sensitive continuous interaction signature
→ field-side retrieval of another structure
→ exact symbolic role verification
```

The new operation deliberately separates two questions:

1. **Continuous/subsymbolic proposal:** does another earned structure have a sufficiently similar relational form to be worth examining?
2. **Symbolic verification:** after unfolding both structures, is there an actual one-to-one relational alignment?

Field similarity alone is never accepted as semantic equivalence.

## Why this milestone exists

Milestone 15 showed that an earned structure can become causally useful as a compiled operand. It did **not** show that one learned structure can recognize another learned structure whose surface symbols are unrelated.

Milestone 16 therefore targets the next claim:

> Can Verdant use the continuous form of an earned structure to retrieve a structurally related but symbolically disjoint structure, then independently verify the relationship in explicit symbolic form?

## Frozen symbolic body at promotion

Milestone 16 adds `StructureEdgeSnapshot` to `StructureRecord`.

At promotion, Verdant now freezes the internal learned edge topology and strengths that justified objecthood:

```text
structure
  member concepts
  internal association lineage
  frozen internal edge snapshots
  evidence lineage
  quality at promotion
```

This matters because later plastic decay must not rewrite history and make the symbolic body of an already-promoted structure ambiguous.

Older checkpoints remain loadable because the edge snapshot field has a backward-compatible empty default. New M16 promotions populate it automatically.

## Structure-sensitive continuous signature

A new package is added:

```text
verdant_interaction/
    __init__.py
    pipeline.py
    demo.py
```

The public operation is:

```python
VerdantStructureInteractionPipeline().interact(kernel, source_structure_id)
```

For each promoted structure, the interaction pipeline derives a continuous complex signature from relational form.

The encoder deliberately excludes:

```text
concept IDs
concept labels
run label
kernel seed
human semantic categories
```

It uses permutation-invariant properties of the frozen relational body, including:

```text
member count
edge density
normalized edge-strength profile
sorted degree profile
sorted weighted-degree profile
adjacency eigenvalue spectrum
```

Those invariant features are projected deterministically into a normalized complex vector.

Therefore changing the symbols while retaining the same relational form does not destroy the field-side comparison.

This is a **designed structure-sensitive interaction field**, not evidence that Verdant has autonomously learned a semantic manifold. Learning the projection itself remains a later research problem.

## Two-stage interaction

### Stage 1 — field retrieval

The source structure is projected into its continuous signature and compared with every other available promoted structure.

Candidates are ranked by continuous similarity.

This stage is intentionally permissive: it is allowed to produce false positives.

### Stage 2 — symbolic verification

Candidates that pass the field threshold are unfolded into their frozen symbolic relational bodies.

For bounded structures (currently at most eight members by default), Verdant searches one-to-one role permutations and scores the best alignment using:

```text
edge-presence agreement
+
normalized edge-strength agreement
```

The result is one of:

```text
VERIFIED_ALIGNMENT
FIELD_ONLY
REJECT
```

`FIELD_ONLY` is important: it means the fuzzy side found something interesting, but explicit relational inspection refused to call it the same structure.

## Controlled experiment

The demo independently cultivates three four-member structures.

### World A — path

```text
A1 — A2 — A3 — A4
```

### World B — same relational form, unrelated symbols

```text
B1 — B2 — B3 — B4
```

### World C — non-isomorphic control

```text
      C2
       |
C3 — C1 — C4
```

All three are grown from ordinary developmental experience and promoted through the existing M14 gates. No canonical semantic relations or claims are installed.

The A and B concept sets have **zero symbol overlap**.

Measured result:

| Comparison | Field similarity | Symbolic similarity | Result |
|---|---:|---:|---|
| A path ↔ B path | **0.99987** | **0.99410** | `VERIFIED_ALIGNMENT` |
| A path ↔ C star | **0.98089** | **0.62000** | `FIELD_ONLY` |

The continuous side therefore noticed both relationally nearby objects, but ranked the true isomorphic structure highest.

More importantly, exact symbolic comparison accepted the path-to-path analogy and rejected the path-to-star false positive.

The verified role mapping was:

```text
A1 ↔ B1
A2 ↔ B2
A3 ↔ B3
A4 ↔ B4
```

(up to graph-symmetry reversal of the path, which is an equally valid mapping).

The interaction operation created no concepts, canonical relations, claims, or evidence.

## Why the control matters

A field-only retrieval mechanism would be easy to fool here.

The path and star have:

```text
same number of members
same number of edges
similar edge-strength distributions
```

so their continuous signatures are deliberately rather close (`0.98089`).

If Verdant simply treated high field similarity as truth, M16 would be a failure.

Instead:

```text
field says: worth examining
symbolic body says: not the same relational organization
```

That is the intended cross-symbolic architecture:

```text
continuous broad search
→ explicit exact inspection
```

rather than one representation silently replacing the other.

## Persistent audit records

Milestone 16 adds:

```text
StructureInteractionPolicy
StructureFieldSignature
StructureInteractionCandidate
StructureInteractionReport
StructureInteractionEvent
StructureInteractionDisposition
```

Interaction reports and events are deterministic, checksummed, checkpoint-persistent, and semantic-firewall preserving.

Inspection is pure. Policy/state changes invalidate pending reports through structural fingerprint checks.

Ablated structures are excluded from retrieval.

## Cultivation Runner V3

`run_verdant_cultivation.py` now adds:

```text
interact <index-or-structure-id>
```

The runner displays:

```text
field rank
field similarity
symbolic similarity
verification disposition
role mapping
best verified target
```

Telemetry exports now also preserve `structure_interaction_events`.

The status panel includes `structure_interaction_event_count`.

## Test result

Milestone 16 adds eight tests covering:

1. field retrieval finding a symbolically disjoint isomorphic earned structure;
2. structure-sensitive signatures remaining independent of surface symbol identity;
3. field false positives being refused without symbolic verification;
4. one-to-one role mappings over verified structures;
5. pure inspection and stale-policy rejection;
6. ablated structures being excluded from retrieval;
7. exact checkpoint recovery of interaction history;
8. preservation of the canonical semantic firewall.

Full suite verification was run in two batches because the complete invocation exceeded the execution wrapper's single-call limit:

```text
65 passed
99 passed
----------------
164 passed total
```

No test failures remain.

## What Milestone 16 establishes

The defensible result is:

> Verdant can take one independently earned structure, encode its relational form into a continuous label-independent interaction signature, use that signature to retrieve another earned structure with completely different surface symbols, then unfold both symbolic bodies and verify a role-preserving structural alignment.

And the negative control demonstrates the complementary property:

> High continuous similarity is not sufficient for acceptance; explicit symbolic structure can reject a fuzzy false positive.

This is the first clean implementation of the intended loop:

```text
symbolic structure
↔
continuous relational interface
```

across **multiple manufactured cognitive objects**.

## What Milestone 16 does not establish

It does **not** yet establish:

- that the continuous interaction geometry was autonomously learned rather than engineered;
- semantic analogy in natural language;
- transfer of a useful inference from World A into World B;
- creation of a new higher-order object from the verified alignment;
- recursive structure-of-structures cognition;
- learned logic;
- intelligence or proto-intelligence.

The continuous projection is intentionally auditable and hand-designed at this stage. That makes M16 a clean test of the cross-symbolic mechanism, not proof that Verdant has learned its own manifold.

## Next milestone

### Milestone 17 — Layered Concept Formation

We now have:

```text
P_A
→ continuous retrieval of P_B
→ symbolic verification of P_A ↔ P_B
```

The next question is whether a recurring verified relationship **between earned structures** can itself enter the same developmental objecthood pathway.

The target is:

```text
P_A + P_B
→ recurring invariant Q_candidate
→ independent gates
→ Q
```

where `Q` is not a hard-coded category and its constituents are other earned structures rather than primitive concepts.

The decisive boundary for M17 is that the new higher-order object must become causally useful in a later task, while remaining reconstructable back through its constituent structures to original evidence.
