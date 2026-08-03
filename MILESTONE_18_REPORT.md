# Verdant Minds Independent Rebuild — Milestone 18

## Refolding Under Contradiction

Milestone 18 adds the first lineage-preserving revision mechanism for earned relational structures.

The developmental path is now:

```text
experience
→ bounded local plasticity
→ earned relational structure P
→ repeated evidence-grounded structural contradiction
→ selective unfolding of P's frozen relational body
→ stable / revise / split / unresolved assessment
→ Council authorization when a replacement is justified
→ lineage-linked P′ / child structures
→ old P preserved but normally made dormant
```

The central rule is that contradiction does **not** overwrite history.

A mature `StructureRecord` still contains the exact frozen structural body it had when it earned existence. Milestone 18 records later challenges separately. If those challenges justify revision, new structures are created with explicit parent/root lineage while the old structure remains recoverable in canonical history.

## Why this milestone exists

Milestones 14–17 established progressively stronger behavior:

```text
M14: recurring learned relations can earn opaque objecthood
M15: P can become a causally useful compiled operand
M16: P can interact cross-symbolically with another P
M17: several earned P operands can become a useful higher-order Q
```

Those mechanisms would still be brittle if promoted structures were effectively immutable caches. A developmental cognitive object must be able to encounter evidence that no longer fits its earlier organization without either:

1. silently ignoring the evidence;
2. rewriting its own past;
3. deleting itself wholesale; or
4. immediately believing one contradictory observation.

Milestone 18 therefore treats refolding as a distinct audited operation.

## Structural contradiction interface

The new package is:

```text
verdant_refolding/
    __init__.py
    pipeline.py
    demo.py
```

The public API is centered on:

```python
pipeline = VerdantRefoldingPipeline()

pipeline.challenge(
    kernel,
    structure_id,
    (concept_a, concept_b),
    evidence_refs=evidence_refs,
    confidence=0.80,
)

report = pipeline.inspect(kernel, structure_id)
event = pipeline.commit(kernel, report)
```

A structural challenge must:

- target an existing promoted structure;
- target two members of that structure;
- correspond to one of the structure's **frozen internal edge snapshots**;
- preserve exact evidence references;
- come from one identifiable source event per observation;
- carry bounded confidence;
- recur enough times to satisfy the refolding policy before it can alter the fold.

Challenge observations are nonsemantic. They do not create or delete canonical concepts, relations, or claims.

### Important current limitation

The challenge interface is an explicit laboratory protocol. Milestone 18 does **not** claim that Verdant can yet interpret arbitrary natural-language contradiction and autonomously decide which internal fold edge it challenges.

The result tested here is narrower:

> Given evidence that has already been typed as contradicting a particular frozen structural dependency, can Verdant preserve the old structure, accumulate contradictory evidence conservatively, unfold only the affected structure, and produce a defensible revised organization?

Future language/perception work can generate the same typed challenge records without changing the refolding mechanism.

## Recurrent contradiction, not one-shot rewriting

Default policy:

```text
minimum challenge events       2
minimum combined confidence    0.75
minimum viable component size  3 members
minimum viable component edges 2
ablate parent after success     yes
```

Independent challenge confidence is combined with a saturating evidence rule:

```text
combined = 1 - Π(1 - confidence_i)
```

Therefore one 0.80 observation is still below the default recurrence requirement even though its confidence is high.

The controlled demo verifies:

```text
one challenge observation
→ STABLE
```

not immediate rewrite.

Exact challenge-event replay is idempotent. Reusing the same event key with different evidence or confidence is rejected as an integrity error.

## Four refolding dispositions

A pure refolding inspection returns one of four outcomes.

### `STABLE`

No mature contradiction currently justifies changing the fold.

The parent remains available.

### `REVISE`

Challenged edges are removed, but the surviving frozen topology remains one viable connected structure.

Milestone 18 creates a new lineage-linked `StructureRecord` with the same member set and a revised edge body.

### `SPLIT`

Removing challenged edges exposes two or more independently viable connected components.

Each viable component becomes a separate lineage-linked structure.

### `UNRESOLVED`

The contradiction genuinely damages the old organization, but the surviving pieces do not yet meet the minimum conditions for a defensible revision or split.

In that case no replacement is invented and the parent remains available.

This is intentional. Verdant is allowed to carry unresolved structural tension instead of being forced to manufacture an answer.

## Old folds are never overwritten

Root promoted structures keep the original identity rule:

```text
structure_id = stable_id("structure", source_candidate_id)
```

A refolded structure uses:

```text
refolded_structure_id = stable_id(
    "refolded_structure",
    parent_structure_id,
    surviving_member_ids,
    surviving_frozen_edges,
    challenge_ids,
)
```

Every refolded structure preserves:

```text
lineage_parent_structure_id
lineage_root_structure_id
revision_index
refold_basis_challenge_ids
exact surviving edge snapshots
evidence lineage
Council authorization
```

The parent record remains byte-for-byte present in `kernel.state.structures`.

Successful refolding normally changes only **availability**:

```text
old P    → preserved + dormant
new P′   → available
```

so historical reconstruction remains possible.

## Controlled split experiment

The main demonstration first lets Verdant earn a six-member fold whose frozen structural body contains two internally coherent three-member regions plus three cross-links:

```text
A triangle                     B triangle

A1 ----- A2                    B1 ----- B2
 \       /                      \       /
  \     /                        \     /
    A3  =========================  B3
     \------ cross-links -------/
```

More exactly, the A and B regions each contain three internal edges, and `A3` has three learned cross-links into the B region.

The complete six-member organization is cultivated and promoted before any contradiction is supplied.

Before refolding, a compiled cue from `A1` invokes the parent object and reconstructs:

```text
A1 A2 A3 B1 B2 B3
```

as one operand.

### Contradict the cross-links

Each of the three frozen A↔B cross-links receives two independent contradiction observations at confidence `0.80`.

The three challenge records become mature.

Inspection returns:

```text
final disposition      SPLIT
mature challenges      3
removed frozen edges   3
replacement folds      2
```

The replacements are:

```text
P′A = {A1, A2, A3}
P′B = {B1, B2, B3}
```

Each child retains all three of its internally coherent frozen edges.

The original six-member P remains stored but becomes unavailable for ordinary cognition.

## Causal behavior after refolding

Before contradiction/refolding:

```text
cue A1
→ parent P
→ A1 A2 A3 B1 B2 B3
```

After the split:

```text
cue A1
→ child P′A
→ A1 A2 A3

cue B1
→ child P′B
→ B1 B2 B3
```

Both post-refold probes use one compiled structure operand under the existing Milestone 15 accounting model.

This demonstrates that the refold is not merely archival lineage metadata. The newly produced structures immediately become ordinary `StructureRecord` operands and therefore participate in the same bounded compilation, interaction, and workspace machinery as earlier earned structures.

## Revision without splitting

A separate regression test cultivates a three-member triangle:

```text
X1 — X2
 \   /
   X3
```

Recurrent challenge of one frozen edge removes that dependency but leaves the remaining two-edge path connected:

```text
X1 — X2 — X3
```

Inspection returns:

```text
REVISE
```

rather than `SPLIT`.

A new same-members revision is created with two surviving frozen edges, explicit parent lineage, and `revision_index = 1`.

## Refusal to invent fragments

Another controlled triangle receives contradiction against two edges incident on one member.

Removing those edges would leave:

```text
one two-member fragment
+
one isolated member
```

Neither is large enough to satisfy the default refolding viability rules.

Verdant returns:

```text
UNRESOLVED
```

No replacement structures are manufactured and the original P remains available.

That regression is important because a system that is forced to resolve every contradiction would merely replace one form of brittleness with hallucinated structure.

## Quality after refolding

Refolded structures preserve the parent history while recomputing local properties of the surviving body.

Milestone 18 now fills two previously mostly-placeholder dimensions of `StructureQualityVector`:

### Perturbation survival

```text
surviving frozen edge strength
──────────────────────────────
 original frozen edge strength
```

This measures how much of the original relational body survived the perturbation.

In the controlled split:

```text
A child perturbation survival ≈ 0.3325
B child perturbation survival ≈ 0.3366
```

Those values are not interpreted as semantic confidence. They simply expose how much of the parent's edge-strength mass each new child inherited.

### Contradiction tolerance

A successfully committed revision/split receives:

```text
contradiction_tolerance = 1.0
```

meaning the particular registered structural contradiction was resolved by the new topology.

This is an event-relative engineering metric, not a general claim that the structure is universally robust to contradiction.

## Field-side continuity

Each replacement structure receives a fresh continuous prototype computed from the surviving member concepts' current evidence-bound resonance profiles, falling back to persistent concept field addresses where necessary.

The old parent prototype is not copied blindly into a child with different membership.

This allows refolded structures to re-enter later M16 cross-symbolic interaction with a continuous interface appropriate to their new member set.

## Council authorization

`REVISE` and `SPLIT` outcomes cannot commit replacements directly.

They are submitted through the existing governance path as:

```text
proposal kind: STRUCTURAL_PROMOTION
action class: earned_structure_refolding
operation:    refold_structure
```

Only after Council authorization are replacement `StructureRecord` objects committed and the parent made dormant.

`STABLE` and `UNRESOLVED` assessments do not consume a structural-promotion authorization because they manufacture no new cognitive operand.

## Semantic firewall

The controlled demonstration begins with:

```text
concepts   6
relations  0
claims     0
```

and ends after six contradiction observations plus the split with:

```text
concepts   6
relations  0
claims     0
```

So neither structural challenge recording nor refolding silently installs semantic truth.

## Cultivation Runner V4

The hand-driven runner now supports contradiction/refolding experiments directly:

```text
challenge <P> <labelA> <labelB> [confidence]
refold <P>
refolds
```

Example:

```text
verdant> challenge 1 a3 b1 0.80
verdant> challenge 1 a3 b1 0.80
verdant> challenge 1 a3 b2 0.80
verdant> challenge 1 a3 b2 0.80
verdant> challenge 1 a3 b3 0.80
verdant> challenge 1 a3 b3 0.80
verdant> refold 1
```

The runner displays:

```text
STRUCTURAL CONTRADICTION
  challenged frozen edge
  observation count
  combined confidence

REFOLDING RESULT
  stable / revise / split / unresolved
  mature challenge count
  removed frozen edges
  produced lineage-linked structures
  parent availability
```

Telemetry export now preserves `structural_challenges` and `structure_refold_events` separately from taught, associated, manufactured, promoted, layered, and semantic records.

## Tests

Milestone 18 adds nine tests covering:

1. one contradiction observation does not force a refold;
2. recurrent contradiction of boundary-crossing edges splits a mature fold while preserving the parent;
3. split children immediately become causal compilation operands;
4. contradiction of a non-bridge edge produces a same-members revision rather than a split;
5. undersized fragments remain unresolved instead of being invented as new folds;
6. refolding inspection is pure and policy changes make reports stale;
7. exact challenge replay is idempotent and conflicting event-key reuse is rejected;
8. checkpoint round-trip preserves challenge, refold, lineage, and availability state;
9. contradiction/refolding cannot silently mutate canonical concepts, relations, or claims.

The pre-existing suite plus Milestone 18 contains:

```text
181 tests
```

A single monolithic pytest process in this container again became abnormally slow late in the run and exceeded the 120-second execution window. The complete suite was therefore rerun in fresh partitions:

```text
85 passed
59 passed
37 passed
─────────
181 passed
```

No test failures were observed.

## What Milestone 18 does **not** establish

Milestone 18 does not yet establish:

- autonomous interpretation of arbitrary linguistic contradiction;
- autonomous selection of which fold edge a raw observation challenges;
- optimal refolding thresholds;
- probabilistically calibrated contradiction confidence;
- automatic revision of a higher-order Q when one of its constituent P structures refolds;
- long-run behavior under hundreds or thousands of interacting revisions;
- comparison against simpler cache, graph, embedding, or clustering baselines;
- general intelligence or proto-intelligence.

The correct claim is narrower:

> A promoted earned structure can now preserve its original historical body, accumulate recurrent evidence-grounded contradiction against specific frozen dependencies, selectively unfold those dependencies, and either remain stable, revise, split, or explicitly stay unresolved. Successful replacements are lineage-preserving cognitive operands whose causal use changes immediately while the old structure remains recoverable.

## Developmental status

The post-M11 roadmap now stands at:

```text
M12  Unified Developmental Cycle             COMPLETE
M13  Local Plasticity Without Saturation     COMPLETE
M14  Earned Relational Structures            COMPLETE
M15  Cognitive Compilation                   COMPLETE
M16  Cross-Symbolic Structure Interaction    COMPLETE
M17  Layered Concept Formation               COMPLETE
M18  Refolding Under Contradiction            COMPLETE
M19  Ethomorphism Benchmark Harness          NEXT
M20  Explorer / Pitch Integration            pending
```

The research object has therefore reached the complete mechanism originally required before formal benchmarking:

```text
learn
→ manufacture a thing
→ think with the thing
→ let things interact
→ manufacture a higher thing
→ confront a mature thing with contradiction
→ revise without erasing history
```

## Next milestone

### Milestone 19 — Ethomorphism Benchmark Harness

The next step should stop adding major conceptual capability long enough to measure what now exists.

The benchmark should implement controlled experimental arms:

```text
A — canonical symbolic graph only
B — graph + ECWF retrieval
C — developmental plasticity, fold promotion disabled
D — full earned-fold Verdant
```

with identical curricula, seeds, event ordering, held-out worlds, and resource limits.

Primary measurements should include:

```text
formation cycle
candidate lifetime
promotion gates
reconstruction accuracy
held-out transfer
false activation/selectivity
concepts inspected
relations/associations traversed
field comparisons
workspace resource use
persistent bytes added
ablation delta
restoration delta
refold/split events
long-run density and relational contrast
```

Milestone 19 is where the architecture begins facing the strongest alternative explanation:

> Are the observed advantages actually caused by Verdant's earned developmental objects, or would a much simpler memory/retrieval system achieve the same result under equal conditions?

That is now the right question to ask.
