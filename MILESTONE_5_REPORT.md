# Verdant Minds Independent Rebuild — Milestone 5

## Constitutionally Separated Kings and Inspectable Council Governance

Milestone 5 rebuilds the Data, Forefront, and Ethics Kings as separate, evidence-inspectable jurisdictions operating over the clean kernel, claim layer, ECWF resonance reports, and attention candidates established in Milestones 1–4.

The executable separation is now:

> **Data King asks what is supported. Forefront King asks what deserves scarce attention now. Ethics King asks what consequences, permissions, and boundaries apply. Council decides what may be investigated, committed, or acted upon.**

No LLM, pretrained semantic model, external API, or cloud service participates in this path. The demonstration still uses handwritten curricula and controlled evidence declarations.

## Implemented

### 1. Canonical Council proposals

Every governance request is represented as an immutable `CouncilProposal` containing:

- proposal kind: investigate, attend, act, or structural promotion;
- requested operation and action class;
- optional target claim;
- preserved evidence references;
- ECWF resonance-event and attention-candidate references;
- requested attention resources;
- relevance, urgency, novelty, and expected information gain;
- declared harm risk and reversibility;
- consent and boundary conditions;
- safe alternative operations;
- canonical-state and governance-policy fingerprints;
- deterministic identity checksum.

A proposal cannot refer to missing claims, evidence, resonance events, or attention candidates. A proposal becomes stale as soon as the canonical state or governance policy changes.

### 2. Data King — epistemic jurisdiction

The Data King evaluates:

- the target claim's support and refutation ledgers;
- the current preferred claim;
- active contradiction state;
- preserved source evidence;
- whether the proposed commitment agrees with the current evidence-weighted belief.

It can return:

- support;
- opposition;
- request for further evidence.

The Data King explicitly records that ECWF resonance is **not evidence**. Resonance-event and attention references may be present in a proposal, but they do not contribute to epistemic support.

### 3. Forefront King — bounded present priority

The Forefront King evaluates:

- present relevance;
- urgency;
- novelty;
- predicted information gain;
- active attention-candidate priority;
- unresolved contradiction;
- requested resources versus the persisted attention budget.

It can prioritize or deprioritize a proposal. It has no authority to declare a claim true and no authority to grant ethical permission.

### 4. Ethics King — consequence and permission jurisdiction

The Ethics King evaluates:

- declared harm risk;
- learned risk associated with the action class;
- reversibility;
- consent requirements;
- boundary sensitivity;
- uncertainty around contradicted action premises.

It can permit, constrain, or deny. It cannot alter evidence to make an action appear justified or unjustified.

### 5. Rule-ordered Council, not a weighted average

The prior King weight fields remain in checkpoints for compatibility and diagnostics, but Milestone 5 does not average the three assessments.

Council follows explicit constitutional precedence:

1. a hard Ethics denial blocks the operation;
2. Data opposition blocks or defers semantic/action commitment;
3. unresolved evidence may authorize a safe investigation when Forefront prioritizes it and Ethics permits it;
4. Forefront may defer low-priority or over-budget work;
5. Ethics constraints can permit only a bounded form of the operation;
6. full approval requires every enabled jurisdiction to allow commitment.

The Council report records:

- each independent King assessment;
- disposition: approve, approve with constraints, defer, or deny;
- authorized and blocked operations;
- required evidence;
- constraints;
- safe alternatives;
- enabled/disabled Kings;
- exact policy snapshot;
- deterministic report checksum.

The legacy weights are explicitly marked `legacy_weights_used_for_decision = false` in every report.

### 6. Causal operation authorization

A committed Council report creates a persistent `CouncilDecisionEvent`.

Downstream code can call the kernel authorization gate before execution. An operation not listed in the decision's `authorized_operations` raises `GovernanceAuthorizationError`.

This distinguishes:

```text
Council was consulted
```

from:

```text
Council causally permitted or blocked what the system could do next
```

The decision event cannot create or modify semantic evidence, concepts, relations, claims, contradictions, or revisions.

### 7. Outcome learning without rewriting history

An authorized operation may later receive preserved physical-outcome evidence. The kernel records a `GovernanceOutcomeRecord` containing:

- originating Council decision;
- action class;
- physical-outcome evidence;
- success/failure;
- observed harm score;
- expected-versus-observed prediction error;
- learned risk before and after;
- exact governance-policy revision.

The current experimental update is a bounded exponential step:

```text
new_risk = (1 - learning_rate) × old_risk + learning_rate × observed_harm
```

The demonstration uses a deliberately aggressive learning rate of `0.80` so a causal policy change is visible in a short controlled test. This is an experimental setting, not a validated ethical-learning law.

Outcome learning changes future Ethics assessments while preserving the original decision and outcome evidence.

### 8. Integrity and persistence

Council proposals, King assessments, reports, committed decisions, and outcome records all carry deterministic content-derived identities.

The kernel rejects:

- stale proposals or reports;
- altered reports;
- missing references;
- duplicated outcomes for one decision;
- outcomes attached to denied operations;
- outcome learning without physical-outcome evidence;
- Council records carrying hidden semantic or policy-mutation permission.

All governance state survives exact checkpoint save/reload.

## Controlled door demonstration

The handwritten curriculum first supplied:

```text
The door is open.
```

Controlled evidence then supplied:

```text
The door is visibly closed.
Forward motion was blocked at the door.
```

A pure ECWF query for `The door is open.` admitted five existing possibilities to attention. Council then evaluated a proposal to force forward through the disputed doorway.

### Independent King judgments

| King | Recommendation | Main reason |
|---|---|---|
| Data King | Oppose | The affirmative claim is not the current evidence-supported belief |
| Forefront King | Prioritize | The contradiction is relevant and action-sensitive |
| Ethics King | Deny | High harm risk combined with low reversibility |

The Forefront priority score was `0.721729`. The Data King recorded `resonance_used_as_evidence = false`.

### Council result

```text
force_forward_through_door → DENIED
inspect_door                → offered as safe alternative
```

A second proposal requested non-forceful visual inspection. The Data King requested more evidence, Forefront prioritized the unresolved contradiction, and Ethics permitted the reversible inspection.

```text
inspect_door → APPROVED WITH CONSTRAINTS
```

The governing constraint requires the result to return through the normal evidence pipeline rather than being installed directly as truth.

## Controlled outcome-learning demonstration

Council initially approved a low-declared-risk controlled test.

A later controlled physical outcome reported harmful contact:

```text
learned controlled-test risk:
0.00 → 0.72
```

When the same action class was proposed again:

| Stage | Ethics recommendation | Council disposition |
|---|---|---|
| Before adverse outcome | Permit | Approve |
| After adverse outcome | Deny | Deny |

This demonstrates a causal governance change from preserved consequences. It does not demonstrate general moral learning.

## Demonstration state

| Measurement | Result |
|---|---:|
| Developmental cycles | 28 |
| Evidence records | 66 |
| Concepts | 26 |
| Relations | 8 |
| Claims | 4 |
| Contradictions | 1 |
| Revisions | 1 |
| Field-history frames | 22 |
| Resonance events | 1 |
| Attention candidates | 5 |
| Council decisions | 4 |
| Governance outcomes | 1 |
| Directed graph density | 1.231% |

The graph remains sparse. Council commitment did not change semantic counts.

## Tests

The combined suite now reports:

```text
52 passed
```

The ten new Milestone 5 tests cover:

- independent and disagreeing King judgments;
- denial of forceful action under disputed evidence;
- authorization of safe evidence-gathering;
- causal operation blocking;
- prohibition on governance-created semantic evidence;
- Ethics-King ablation changing a private-boundary decision;
- outcome-based risk learning changing a later decision;
- stale and tampered report rejection;
- exact checkpoint recovery;
- deterministic governance replay;
- proof that legacy King weights do not control Council disposition.

All earlier kernel, CognitiveChunk, language, claims, and ECWF tests continue to pass.

## Important boundaries

Milestone 5 demonstrates an inspectable governance mechanism, not a completed ethical intelligence.

It does **not** yet demonstrate:

- autonomous moral-rule discovery;
- culturally complete ethics;
- calibrated real-world risk estimation;
- external device execution;
- live consent detection;
- autonomous adjustment of the constitutional rule order;
- adaptive use of `t_g`;
- consciousness.

The present source classifications, thresholds, and learning rate are explicit experimental policy. They require future ablation, calibration, and embodied testing.

The identity hashes provide deterministic integrity checks; they are not public-key digital signatures.

## Next milestone

Milestone 6 is bounded specialization, shard formation, and governed routing.

The next phase will add:

- one canonical shard registry;
- evidence-backed shard membership;
- bounded local graph size and degree;
- explicit shard-formation proposals sent through Council;
- route scoring that separates evidence, resonance, information gain, contamination, and thaw cost;
- logged bridge traversal rather than inert ghost bridges;
- warm versus dormant shard state;
- tests proving that routing can increase selectivity without losing direct grounding.

The central test will reproduce the old Export 26 tension under controlled conditions:

> Can Verdant learn to move between specialized regions without losing the presented experience that caused the movement?
