# Verdant Minds Independent Rebuild — Milestone 15

## Cognitive Compilation

Milestone 15 asks the first causal question about a promoted earned structure:

> Does manufacturing `P` change the cost or capability of later computation?

Milestone 14 established that a recurring learned relational configuration can earn promotion into an opaque `StructureRecord` without becoming semantic truth. Milestone 15 makes that record an actual bounded cognitive operand and introduces controlled ablation/restoration.

The path is now:

```text
experience
→ learned plastic relations
→ recurring relational configuration
→ StructureCandidate
→ promoted StructureRecord P
→ later cue
→ P enters bounded workspace as one operand
→ relational region reconstructed through P
→ controlled ablation forces low-level reconstruction
→ restoration returns compiled path
```

## New package

```text
verdant_compilation/
    __init__.py
    pipeline.py
    demo.py
```

The public causal probe is:

```python
VerdantCompilationPipeline().probe(kernel, cue_concept_ids)
```

and the controlled interventions are:

```python
VerdantCompilationPipeline.ablate(kernel, structure_id)
VerdantCompilationPipeline.restore(kernel, structure_id)
```

## What “compilation” means here

The same bounded reconstruction operation has two paths.

Without an available earned structure:

```text
cue
→ bounded traversal of learned plastic associations
→ reconstruct relevant local relational region
```

With an available promoted structure:

```text
cue
→ match promoted P
→ load P as one operand
→ recover P's preserved member region
```

The milestone records both the actually selected path and the low-level baseline cost for the same query.

`CompilationCost` currently records:

```text
concepts inspected
associations traversed
structures inspected
structure operands used
reconstructed concepts
estimated workspace resource
```

The primary structural-work measure used by the controlled test is:

```text
low_level_work = concepts_inspected + associations_traversed
```

This is an explicit accounting metric for this implementation. It is **not** a FLOP, wall-time, energy, or human-equivalent cognition measurement.

## Promoted structures now enter the workspace

Milestone 15 adds a new workspace source class:

```text
EARNED_STRUCTURE
```

When current evidence overlaps a promoted, available structure, that structure can be admitted to the bounded workspace as one item whose binding refs are the structure's learned members.

This is the first point where a `StructureRecord` participates in the shared cognitive foreground as a unit rather than existing only as stored metadata.

The workspace validator requires:

- the structure exists;
- it is not currently ablated;
- candidate evidence remains inside the structure's promotion lineage;
- bindings remain inside the structure's member set.

## No self-bootstrapping

An important control was added to the plasticity layer.

Both:

```text
LOCAL_ASSOCIATION
EARNED_STRUCTURE
```

may affect the cognitive foreground, but neither is permitted to count as fresh coactivation evidence for strengthening the lower-level plastic traces that caused it to exist.

Normal homeostatic decay still occurs.

Therefore the loop:

```text
P activates its members
→ activation is treated as new evidence for P's own components
→ components strengthen
→ P becomes increasingly inevitable
```

is explicitly blocked.

## Controlled five-symbol demonstration

The demo uses five meaningless primitives:

```text
KREN
TAR
VEL
MIP
ZOG
```

No canonical semantic relations or claims are installed.

Repeated developmental exposure produces local plastic structure. A five-member relational candidate passes the Milestone 14 gates and is promoted as an opaque structure:

```text
structure_466cdd1a0f17911009b9d6cc
```

A later one-symbol `KREN` cue is then used for the same relational-region reconstruction operation under three conditions.

### With P available

```text
reconstructed concepts      5
concepts inspected          1
associations traversed      0
structure operands used     1
estimated workspace         0.06
low-level work              1
```

The explicitly computed low-level baseline for the same cue was:

```text
reconstructed concepts      5
concepts inspected          5
associations traversed      10
structure operands used     0
estimated workspace         0.30
low-level work              15
```

So the structural accounting metric reports:

```text
compression gain = 0.933333...
```

or a 93.3% reduction in the benchmark's counted low-level operations.

### P ablated

The exact promoted structure is disabled while all of its lower-level learned associations remain intact.

The same cue then produces:

```text
disposition                 fallback_low_level
reconstructed concepts      5
concepts inspected          5
associations traversed      10
structure operands used     0
low-level work              15
compression gain            0.0
```

### P restored

Restoring the same structure gives:

```text
disposition                 use_structure
reconstructed concepts      5
concepts inspected          1
associations traversed      0
structure operands used     1
low-level work              1
compression gain            0.933333...
```

The reconstruction output was identical in all three conditions.

That yields the controlled causal sequence:

```text
WITH P       → work 1
ABLATE P     → work 15
RESTORE P    → work 1
```

## What this result establishes

Within the deliberately narrow M15 reconstruction task, the promoted object is no longer decorative metadata.

Its availability changes the computation used to reach the same reconstructed region:

```text
manufactured P
→ P used as one operand
→ fewer low-level traversals

ablate P
→ compiled path disappears
→ low-level traversal returns

restore P
→ compiled path returns
```

That is the first direct evidence in the rebuild that an internally manufactured structure can become **causally operative as a reusable computational unit**.

## What this result does not establish

The 93.3% number must not be generalized beyond this benchmark.

Milestone 15 does **not** yet establish:

- cross-domain abstraction;
- transfer between symbolically dissimilar structures;
- semantic understanding of the five-symbol object;
- learned manifold geometry;
- higher-order fold formation;
- contradiction-driven unfolding/refolding;
- improvement on a task whose solution was not already contained in the learned region;
- general FLOP, wall-time, energy, or memory savings at system scale;
- intelligence or proto-intelligence.

The current test is deliberately an internal compilation test: a learned relational region that previously required low-level traversal can later be invoked as one earned operand.

Milestone 16 must make the test substantially harder by asking whether two independently earned structures with different surface symbols can interact through their continuous interfaces and discover a structurally meaningful correspondence that is then verified symbolically.

## Cultivation Runner V2

`run_verdant_cultivation.py` now exposes compilation experiments directly.

New commands:

```text
compile <label>
compare <label>
ablate <index-or-structure-id>
restore <index-or-structure-id>
```

The most useful is:

```text
compare kren
```

which runs:

```text
WITH P
→ ABLATE P
→ same probe
→ RESTORE P
→ same probe
```

and prints the measured cost for all three conditions.

A controlled triad runner test produced:

```text
WITH P     low_level_work=1   gain=0.8333
ABLATE P   low_level_work=6   gain=0.0000
RESTORE P  low_level_work=1   gain=0.8333
```

The runner export now preserves compilation probe history and structure availability events alongside taught, observed, associated, manufactured, and promoted provenance.

## New canonical records/state

Milestone 15 adds:

```text
CompilationPolicy
CompilationCost
CompilationProbeReport
CompilationProbeEvent
StructureAvailabilityEvent
ablated_structure_ids
```

Availability interventions and probe results persist through checkpoints.

A pending pure inspection becomes stale if the relevant structure availability or compilation policy changes before commit.

## Tests

Milestone 15 adds eight tests covering:

1. promoted structure reducing bounded reconstruction work;
2. ablation removing the compiled advantage and restoration returning it;
3. promoted structure entering the workspace as one operand;
4. ablated structures being excluded from workspace admission;
5. pure inspection and stale-report rejection;
6. checkpoint preservation of ablation and compilation history;
7. semantic-firewall preservation during compilation probes;
8. deterministic reconstruction across identical histories.

Full suite:

```text
156 passed
```

## Current claim boundary

The strongest defensible statement after Milestone 15 is:

> Verdant can manufacture an opaque relational object from developmental history, promote it without installing semantic truth, later invoke that object as one bounded workspace operand, and measurably replace repeated low-level relational traversal with that operand in a controlled reconstruction task. Ablating the exact object removes the compilation advantage; restoring it restores the advantage.

That is stronger than Milestone 14's “earned existence,” but still narrower than cross-domain abstraction or general reasoning.

## Next milestone

### Milestone 16 — Cross-Symbolic Structure Interaction

The next target is:

```text
P_A(symbolic) ↔ P_A(field)
P_B(symbolic) ↔ P_B(field)

field-side interaction
→ possible structural compatibility
→ selective symbolic unfolding
→ exact relational verification
```

The decisive control will use independently learned structures with different surface symbols so lexical identity cannot solve the task.

The question becomes:

> Can Verdant use the continuous side of an earned structure to find another structure worth comparing, and can the symbolic side verify a real relational correspondence rather than a superficial similarity?
