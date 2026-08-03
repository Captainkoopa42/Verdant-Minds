# Verdant Minds Independent Rebuild — Milestone 4

## Pure Persistent ECWF and Evidence-Bounded Resonance

Milestone 4 replaces the temporary continuous substrate with an inspectable, checkpointed complex-valued field whose only semantic authority is retrieval and attention proposal.

The constitutional boundary is now executable:

> Evidence determines what Verdant may persist as a concept, relation, or claim. Resonance determines which already-existing possibilities become available for attention.

No LLM, pretrained embedding model, statistical language model, or external API participates in this path. The inputs remain handwritten curricula processed through CognitiveChunk v2 and the controlled grammar system.

## Implemented

### 1. Deterministic dense concept addresses

Every canonical concept receives a persistent complex unit-vector address derived from:

- the kernel seed;
- the canonical concept ID;
- the field dimension;
- an explicit address-policy revision;
- a deterministic collision nonce.

The address is dense across the entire field rather than being reduced to a small dimension-index signature. Its full real and imaginary vectors, SHA-256 digest, creation cycle, state dimension, and derivation nonce are checkpointed.

Exact address digest or vector duplication is rejected as an invariant failure. Address-policy revisions cannot change after concepts exist without a future explicit migration operation.

Addresses provide identity and access. They do not establish semantic relatedness.

### 2. Evidence-bound resonance profiles

Each concept also accumulates a separate resonance profile from the translated feature field of experiences in which that concept was explicitly bound by the evidence-gated language path.

A profile records:

- canonical concept ID;
- exposure count;
- creation and update cycles;
- every supporting evidence reference;
- persistent complex prototype state.

This separation is important:

- **address**: unique persistent field location for a concept;
- **profile**: learned history of the feature-field conditions under which the concept was supported.

A concept address is never interpreted as meaning. A profile can only change through an experience already admitted by the canonical evidence path.

### 3. Persistent path-dependent field evolution

For each accepted experience, the field combines:

- the translated continuous feature effect;
- the addresses of evidence-bound concepts;
- the previous field state under a persisted retention policy.

Each history frame stores:

- exact real and imaginary field state;
- field delta norm;
- causal evidence references;
- bound concept IDs;
- effect SHA-256;
- ECWF policy revision.

The same cue can therefore produce a different resonance result after additional experience, while exact save/reload retains the complete field and profile history.

### 4. Pure resonance inspection

`inspect_resonance(...)` is a nonmutating query. It ranks only concepts that already exist.

Each candidate exposes three separate contributions:

1. **profile alignment** — similarity between the cue field and the concept's learned evidence-bound profile;
2. **current-field alignment** — similarity between the concept's unique address and the present ECWF state;
3. **history alignment** — decayed similarity between that address and recent persisted field frames.

The report stores the normalized weight and weighted contribution of every component. The final score can be reconstructed exactly from the report. It also preserves the normalized cue vector and complete candidate scope, and its deterministic identity checksum covers every ranked candidate and contribution.

The query also stores:

- query feature digest;
- canonical-state fingerprint;
- field fingerprint;
- policy revision;
- candidate-scope size;
- deterministic query ID.

Inspection does not change the field, history, graph, claims, evidence, attention, or checkpoint fingerprint.

### 5. Explicit resonance commitment boundary

A pure report may be explicitly committed to attention. Commitment:

- requires existing evidence references for provenance;
- rejects stale reports computed against a changed state or field;
- reconstructs the report from the preserved cue and rejects altered scores, candidates, or contributions;
- creates bounded attention candidates;
- records a persistent resonance event and transition;
- marks semantic mutation permission as `false`.

It cannot create or modify:

- evidence;
- concepts;
- relations;
- claims;
- contradictions;
- revisions.

This is the rebuilt implementation of the rule:

> Resonance may retrieve or rank possible relations, but it may not invent evidence or stabilize belief.

## Controlled demonstration

The demonstration first taught the three controlled grammar rules and foundational lexicon, then queried:

```text
The dog pushes the child.
```

It subsequently exposed Verdant to:

```text
The dog pushes the child.
The robot pushes the door.
The sound occurred before the light.
The door is open.
Dog pushed child.
```

The same cue was inspected again after those experiences.

### Target score changes

| Existing concept | Before | After | Change |
|---|---:|---:|---:|
| `lexeme:dog` | 0.379481 | 0.543853 | +0.164371 |
| `lexeme:push` | 0.400118 | 0.577632 | +0.177514 |
| `lexeme:child` | 0.407679 | 0.528599 | +0.120920 |

The strongest post-learning candidates included:

1. `polarity:affirmed`
2. `lexeme:push`
3. `lexeme:dog`
4. `grammar_rule:transitive_svo`
5. `lexeme:child`
6. the first dog-push-child statement structure
7. the repeated dog-push-child statement structure

The target action, agent, patient, grammar rule, and statement structures all became highly available after exposure.

`polarity:affirmed` ranked first because it was repeatedly bound across affirmative statement frames. This is not hidden or interpreted as correct task selection. It demonstrates why Milestone 5 needs the Kings: resonance can surface a strongly recurring possibility, while governance must decide whether it is evidentially relevant, presently useful, and permissible to act upon.

### Demonstration state

| Measurement | Result |
|---|---:|
| Developmental cycles | 25 |
| Evidence records | 72 |
| Concepts | 36 |
| Relations | 36 |
| Claims | 4 |
| Field-history frames | 24 |
| Concept addresses | 36 |
| Learned resonance profiles | 36 |
| Resonance events | 1 |
| Attention candidates | 5 |
| Directed graph density | 2.857% |

### Address diagnostics

| Diagnostic | Result |
|---|---:|
| Address count | 36 |
| Duplicate address digests | 0 |
| Duplicate address vectors | 0 |
| Mean pair similarity | 0.093733 |
| Maximum pair similarity | 0.292864 |

These measurements demonstrate removal of the old exact signature-collision failure in this controlled state. They do not claim that finite-dimensional vectors are perfectly orthogonal or that all future semantic interference has been solved.

### Semantic boundary check

Before and after committing the five resonance candidates, the counts of evidence, concepts, relations, claims, contradictions, and revisions were identical.

Only the attention and resonance-audit layers changed.

## Tests

The combined suite now reports:

```text
42 passed
```

The eleven new Milestone 4 tests cover:

- deterministic, unique, dense, complete concept addressing;
- pure resonance inspection;
- exact contribution reconstruction;
- path-dependent response to the same cue;
- prohibition on semantic creation during inspection;
- attention-only resonance commitment;
- stale-report rejection;
- tampered-report rejection and deterministic report reconstruction;
- exact checkpoint recovery of field, addresses, profiles, and resonance history;
- deterministic replay;
- migration from a pre-address state;
- protection against ungoverned address-policy changes.

All prior kernel, CognitiveChunk, language, and claims tests continue to pass.

## Important boundary

Milestone 4 demonstrates a trustworthy mechanism for continuous state, learned field profiles, and retrieval of existing structures.

It does **not** demonstrate:

- autonomous concept formation;
- unrestricted natural-language understanding;
- truth from resonance;
- live native-media grounding;
- intelligent attention allocation;
- consciousness.

The ranking still includes recurring structures that are not always the most task-relevant. That is now visible and measurable rather than hidden inside an opaque activation list.

## Next milestone

Milestone 5 is the independent rebuild of the Kings and Council:

- Data King — epistemic support and provenance;
- Forefront King — current relevance and bounded attention;
- Ethics King — consequence, permission, harm, and reversibility;
- Council — explicit disagreement, ruling, action/commitment constraints, and outcome learning.

The Kings will receive the now-separated inputs:

- evidence and claim standing;
- contradiction state;
- ECWF resonance contributions;
- active attention candidates;
- predicted action consequences;
- permissions and ethical constraints.

They will be unable to manufacture evidence or rewrite history.
