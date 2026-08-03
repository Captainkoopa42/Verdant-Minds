# Verdant Minds Independent Rebuild — Milestone 14

## Earned Relational Structures

Milestone 14 introduces the first explicit **nonsemantic relational objecthood** layer in the independent rebuild.

The developmental path is now:

```text
experience
→ evidence + optional taught primitives
→ ECWF field update
→ bounded workspace
→ local plastic associations
→ recurring relational configuration
→ StructureCandidate
→ independent promotion gates
→ Council authorization
→ opaque StructureRecord
```

The key boundary remains unchanged: a recurring pattern is **not automatically meaning**, and a promoted structure is **not automatically a canonical semantic concept**.

## What changed

The kernel now persists:

```text
StructurePolicy
StructureQualityVector
StructureCandidateRecord
StructureObservationReport
StructureObservationEvent
StructureRecord
StructurePromotionReport
StructurePromotionEvent
```

The new runtime package is:

```text
verdant_structures/
    __init__.py
    pipeline.py
    demo.py
```

The public developmental call remains:

```python
VerdantDevelopmentPipeline.advance(kernel, experience_command)
```

After bounded local plasticity commits, the heartbeat now invokes the earned-structure observer. If no bounded recurring configuration is present, no structure observation event is created.

## Candidate formation is developmental, not semantic

A `StructureCandidate` is not created from a hard-coded topic rule such as:

```python
if {"force", "mass", "acceleration"}:
    create("dynamics")
```

Instead, candidate membership is proposed from the **current locally active plastic neighborhood**. The observer:

1. starts only from concepts grounded in the current evidence foreground;
2. considers only plastic associations above the structure policy's member-strength threshold;
3. remains inside the active shard by default;
4. uses bounded seed neighborhoods rather than global graph spread;
5. requires at least a connected multi-member relational region;
6. gives candidate identity from the exact member concept set, not from a human label, shard name, cycle number, or kernel seed.

Candidate identity is therefore:

```text
structure_candidate = stable_id(member_concept_ids)
```

The same exact relational membership receives the same candidate identity across independently created kernels, which is an initial storage/run-partition invariance property.

## Quality is a vector, not one magic score

Milestone 14 deliberately does not collapse objecthood into a single scalar.

Each candidate carries:

```text
recurrence
reconstructability
boundary_selectivity
internal_cohesion
evidence_diversity
cross_context_stability
perturbation_survival
compression_gain
contradiction_tolerance
```

Only the first six are currently used as earned-structure promotion gates.

`perturbation_survival` and `compression_gain` remain zero placeholders because they belong to later milestones and have not yet been demonstrated. `contradiction_tolerance` is preserved for the later refolding milestone and is not currently used to authorize promotion.

### Recurrence

The same exact member configuration must reappear across multiple committed developmental foregrounds.

### Reconstructability

The current implementation combines internal association coverage and strength:

```text
reconstructability = sqrt(internal_edge_coverage × mean_internal_strength)
```

This is deliberately stricter than mere co-occurrence, while still allowing a sparse strong structure to score better than a dense set of weak traces.

It is **not yet** the stronger Milestone 15 test of reconstructing hidden constituent facts from a compiled structure.

### Boundary selectivity

```text
boundary_selectivity =
    internal_strength / (internal_strength + boundary_strength)
```

This is the direct anti-soup gate.

A candidate whose members bind just as strongly to the rest of the local graph should not earn objecthood merely because its interior is active.

### Internal cohesion

The mean strength of the candidate's currently active internal learned associations.

### Evidence diversity

The candidate must inherit enough distinct source events to avoid promotion from a single repeated record.

### Cross-context stability

Evidence is grouped by explicit `context_id` when supplied. The same relational configuration must survive the configured minimum number of contexts.

The cultivation runner exposes `context_id` directly so this can be tested manually rather than inferred from event names.

## Field prototype

Every candidate receives a bounded continuous field prototype by averaging and normalizing the member concepts' evidence-bound resonance profiles when available, falling back to persistent field addresses only when needed.

The prototype is preserved with a SHA-256 checksum.

Important limitation:

> This prototype is currently a continuous interface summary of the candidate's members. It is **not evidence that Verdant has learned a semantic manifold for the structure**.

Structure-sensitive cross-symbolic interaction remains Milestone 16.

## Promotion

Candidate observation and promotion are separate operations.

A candidate is only eligible when all current gates pass:

```text
minimum recurrence
AND minimum reconstructability
AND minimum boundary selectivity
AND minimum internal cohesion
AND sufficient evidence diversity
AND sufficient cross-context stability
```

The promotion report is inspected purely, then submitted to the existing Three Kings / Council system as a `STRUCTURAL_PROMOTION` proposal.

If authorized, the kernel creates:

```text
P_<opaque-id>
```

as a `StructureRecord`.

Promotion does **not** create a new canonical concept, relation, or claim.

The promoted object stores:

```text
source candidate lineage
member concept IDs
member canonical relation IDs, if any
internal learned association IDs
evidence lineage
quality vector at promotion
continuous field prototype
Council decision ID
promotion policy revision
semantic_label_preinstalled = false
```

This is the first rebuild mechanism whose output is intended to become a future computational operand while remaining separate from semantic truth.

## Controlled demonstration

The demo uses three meaningless symbols:

```text
KREN
TAR
VEL
```

No canonical semantic relations or claims are taught.

They are repeatedly presented together across two explicitly different contexts.

The plastic layer first develops three local associations. Once the association strengths cross the structure-member threshold, the same three-member candidate begins recurring.

Candidate progression:

```text
observation 1 → tracking
observation 2 → tracking
observation 3 → tracking
observation 4 → eligible
```

At promotion time the measured quality vector was:

```text
recurrence                 1.0000
reconstructability         0.8111
boundary_selectivity       1.0000
internal_cohesion          0.6580
evidence_diversity         1.0000
cross_context_stability    1.0000
perturbation_survival      0.0000  (not yet tested)
compression_gain           0.0000  (not yet tested)
contradiction_tolerance    1.0000  (not yet a gate)
```

The resulting candidate:

```text
structure_candidate_95326e72af2ac41b42add2c9
```

was Council-authorized and promoted as the opaque structure:

```text
P_3e12fa013bb2
structure_3e12fa013bb245e3e0827451
```

Before promotion:

```text
concepts   3
relations  0
claims     0
```

After promotion:

```text
concepts   3
relations  0
claims     0
```

So the new object was added without silently creating semantic truth.

## Boundary-contamination regression

A dedicated test first establishes a strong three-member core and then teaches several external associations into one member.

With the structure policy requiring higher boundary selectivity, the candidate remains observable but becomes ineligible for promotion because its boundary pressure is too high.

This matters because the old V4 failure mode was precisely the opposite: sufficiently repeated association could cause broad connectivity to look increasingly important.

Milestone 14 therefore treats **not-binding-to-everything** as part of objecthood.

## Cultivation Runner V1

Milestone 14 restores a hand-driven experimental surface:

```bash
python run_verdant_cultivation.py
```

Interactive commands include:

```text
teach <context> <label1> [label2 ...]
probe <context> <label>
status
candidates
structures
promote <index-or-candidate-id>
save [path]
export <path>
```

The runner separates provenance visibly:

```text
PROGRAMMED   policies, gates, update laws
TAUGHT       primitive symbols / explicit supplied semantic records
OBSERVED     exact evidence and events
ASSOCIATED   nonsemantic learned local traces
MANUFACTURED StructureCandidate records
PROMOTED     Council-authorized opaque StructureRecords
```

The runner can also consume JSONL cultivation scripts:

```bash
python run_verdant_cultivation.py \
  --script curriculum.jsonl \
  --checkpoint experiment.vdk
```

Example line:

```json
{"context_id":"world-a","labels":["kren","tar","vel"],"feature_vector":[1,0,0]}
```

When no feature vector is supplied, the runner uses a deterministic exact one-hot cue derived from the primitive labels. This avoids accidental floating-point replay drift in manual experimentation.

## Tests

Milestone 14 adds eight tests covering:

1. autonomous candidate formation from repeated learned relations;
2. promotion refusal before independent gates pass;
3. Council-authorized opaque promotion without semantic leakage;
4. pure inspection and stale-report rejection;
5. candidate identity independent of kernel seed/run metadata;
6. exact checkpoint recovery of candidates, structures, and promotion history;
7. boundary contamination blocking promotion;
8. multiple evidence records from one event/context cannot fake cross-context stability.

Full suite:

```text
148 passed
```

## What Milestone 14 does **not** establish

Milestone 14 does not yet establish that a promoted structure is useful as cognition.

In particular, it does not yet show:

- lower reasoning cost after structure formation;
- reconstruction of hidden constituent knowledge from the promoted unit;
- transfer to a superficially different domain;
- structure-driven workspace activation;
- ablation loss and restoration recovery;
- learned fold-to-fold interaction;
- higher-order fold formation;
- refolding or splitting under contradiction;
- intelligence or proto-intelligence.

The correct claim is narrower:

> Verdant can now observe a recurring learned relational configuration, require that it remain reconstructable and boundary-selective across evidence and contexts, and promote it under governance into an opaque persistent object without assigning it a human semantic category.

That object has **earned existence**. It has not yet earned the claim that it is useful to think with.

## Next milestone

### Milestone 15 — Cognitive Compilation

The next experiment is the decisive causal one:

```text
learn low-level relations
→ manufacture P
→ promote P
→ solve later task with P
→ measure cost/capability
→ ablate P
→ repeat task
→ restore P
→ repeat task
```

Milestone 15 must make a promoted `StructureRecord` an actual bounded workspace operand and measure whether its presence changes later computation.

The central exit criterion is:

> A promoted structure measurably reduces later cognitive work or enables a capability; ablating that exact structure removes the gain, and restoring it restores the gain.
