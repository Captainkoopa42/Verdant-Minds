# Verdant Minds Independent Rebuild — Milestone 2

## Handwritten Grammar and Relational Language Path

Milestone 2 connects handwritten language curricula to the canonical Verdant kernel through CognitiveChunk v2.

The purpose of this milestone is not to claim unrestricted language understanding. It is to establish a controlled, inspectable path in which explicitly taught grammar and lexicon rules can preserve relational distinctions that a bag-of-words system would collapse.

## What was added

### Evidence-backed grammar scaffolds

Three grammar rules can now be taught as curriculum events:

1. `transitive_svo` — `SUBJECT VERB OBJECT`
2. `copular_property` — `SUBJECT COPULA [NEGATOR] PROPERTY`
3. `temporal_before` — `EVENT [EVENT-VERB] BEFORE EVENT`

A grammar rule is unavailable until its handwritten lesson has passed through CognitiveChunk v2 and been stored as an evidence-backed canonical concept.

### Evidence-backed lexicon

Lexical entries are also taught through handwritten curriculum events. Each entry records:

- lemma;
- lexical category;
- recognized surface forms;
- provenance;
- teacher-supplied status.

The controlled parser cannot use an untaught rule or untaught lexical category.

### Typed semantic frames

The language subsystem produces typed frames for:

- transitive action;
- property affirmation or negation;
- temporal ordering.

Each frame preserves grammatical roles and is converted into canonical concept and relation proposals.

### Explicit testimony evidence

Every handwritten grammar lesson, lexicon lesson, and world statement now creates three distinct evidence records:

1. native text observation;
2. noncanonical continuous translation;
3. teacher testimony supporting the semantic proposal.

This prevents the system from treating translated features as if they were direct world truth.

### Deterministic CognitiveChunk adapter fix

Random CognitiveChunk, payload, and translation identifiers were removed from canonical command fingerprints. Native data remain linked by source hash and deterministic storage path, while identical fresh runs now reproduce exact kernel state.

## Controlled demonstrations

The demonstration teaches three grammar rules, sixteen lexical entries, and ten language experiences.

It verifies that Verdant preserves:

- `A pushes B` versus `B pushes A`;
- `door is open` versus `door is not open`;
- `sound before light` versus `light before sound`;
- present and past surface forms of the same action;
- novel composition of already learned lexemes;
- rejection of malformed role order rather than forced parsing.

The direct `dog -> child / action:push` relation is reused across two surface forms and accumulates six evidence references: observation, translation, and testimony for each experience.

## Demonstration state

- cycles: 29
- evidence records: 87
- canonical concepts: 41
- canonical relations: 58
- field history frames: 29
- directed relation density: approximately 0.03537
- CognitiveChunk archives: 29, all integrity-verified

The graph remains sparse in this controlled run.

## Test result

```text
23 passed
```

The combined suite covers:

- all CognitiveChunk v2 plumbing tests;
- exact kernel checkpoint round trips;
- observation purity;
- canonical relation truth;
- evidence gating;
- deterministic replay;
- checkpoint tamper detection;
- deterministic fresh CognitiveChunk ingestion;
- grammar ablation;
- role reversal;
- negation;
- temporal direction;
- surface-form reuse;
- novel composition;
- malformed-order rejection;
- language-state checkpoint recovery.

## What is learned and what remains scaffolded

The following are genuinely acquired as evidence-backed state:

- which grammar rules are currently available;
- which lexical items and forms are recognized;
- statement-specific grammatical roles;
- directed action relations;
- affirmed and negated property relations;
- temporal ordering relations;
- accumulated evidence across repeated surface forms.

The following remain deliberately programmed scaffolds:

- the deterministic tokenizer;
- the three rule application algorithms;
- the lexical categories themselves;
- fixed rule confidence values;
- the mapping from a parsed frame into canonical relation types.

Therefore this milestone demonstrates rule-conditioned relational learning, not autonomous grammar induction.

## Claims not made

Milestone 2 does not establish:

- unrestricted English comprehension;
- autonomous discovery of grammatical rules;
- unknown-word category induction;
- pronoun resolution;
- passive voice;
- conditionals or recursion;
- grounded meaning beyond handwritten text testimony;
- production ECWF behavior;
- consciousness.

## Important unresolved behavior

Opposing claims are currently preserved rather than overwritten, but the kernel does not yet localize them into typed contradictions.

For example, both of these can coexist:

- `door has_property open`
- `door does_not_have_property open`

Likewise, opposing temporal claims can coexist. This is intentional preservation, but it is not yet reasoning about contradiction.

## Next milestone

Milestone 3 is the **Evidence-Safe MemoryWeb Claim and Contradiction Layer**.

It should add:

- canonical typed claims separate from raw relations;
- epistemic source class: observation, testimony, action, outcome, inference;
- contradiction detection and localization;
- support and refutation ledgers;
- revision without history erasure;
- confidence updates from repeated independent evidence;
- queryable current belief versus historical belief;
- tests where testimony conflicts with direct sensory or action evidence.

This is the next required layer before increasing language complexity or attaching live sensory streams.
