# Verdant Minds Independent Rebuild — Milestone 12

## Unified Developmental Heartbeat

Milestone 12 connects mechanisms that were already individually audited into one bounded developmental foreground:

```text
chosen experience
→ canonical evidence and optional taught semantics
→ ECWF field update
→ local resonance inspection
→ evidence-bounded attention candidates
→ bounded shared workspace
```

The milestone does **not** yet add autonomous semantic plasticity, learned folds, or field-to-symbol writeback. Its purpose is to establish the clean heartbeat on which those later mechanisms can safely depend.

## Why this milestone comes first

The old V4 runtime had developmental reach, but repeated association could become globally sticky and erase relational contrast. The rebuild corrected the opposite side of the problem: evidence, provenance, replay, contradiction, governance, shards, objecthood, workspace limits, and native perception are now much stricter.

Before restoring plasticity, the rebuilt system needed one deterministic route through the existing stages so that later learning can be attached to an observable foreground instead of scattered subsystem calls.

Milestone 12 therefore creates a new `verdant_development` package whose public operation is:

```python
VerdantDevelopmentPipeline.advance(kernel, experience_command)
```

One call stages the complete heartbeat and only replaces the caller's canonical kernel if every stage succeeds.

## Atomic staging

The development pipeline clones the current kernel, runs the complete heartbeat on the clone, validates the downstream semantic firewall, and commits the staged state only after successful completion.

This prevents a failure in resonance or workspace admission from leaving behind a partially committed experience.

A controlled test intentionally requests more workspace resource than exists. The downstream workspace rejects the staged cycle and the original kernel remains byte-for-byte equivalent at the model level.

## Developmental locality

Resonance is scoped to the currently active shard by default:

```text
active shard concepts
→ ECWF ranking
→ top-k attention candidates
```

The root shard currently catalogs all concepts, so a small unspecialized system still searches its whole known symbolic space. Once specialized shards exist, the same heartbeat automatically narrows resonance to the active region.

This preserves an important future scaling invariant:

```text
large persistent knowledge
≠
all knowledge active on every thought
```

## Workspace composition

The heartbeat submits three classes of foreground candidate when available:

1. current evidence;
2. ECWF resonance possibilities;
3. contradictions created by the incoming experience.

Current evidence receives strong grounding and a reserved share of the workspace. Resonance remains resource-capped by the existing workspace policy. A new contradiction can therefore enter the same bounded present without resonance displacing the evidence that caused it.

## Semantic firewall

After `apply_experience`, the pipeline records counts for:

- evidence;
- concepts;
- relations;
- claims;
- contradictions;
- revisions.

It then runs resonance and workspace. Those counts must remain identical afterward.

This enforces the current rule:

> ECWF and workspace activity may propose, rank, bind, and schedule possibilities, but they may not silently create semantic truth.

Autonomous writeback will be introduced only through an explicit candidate/promotion pathway in a later milestone.

## Replay behavior

If the exact same `ExperienceCommand` is submitted again under the same event key, the canonical experience layer returns its existing replay result. Milestone 12 deliberately performs no second resonance or workspace commit for that replay.

Therefore replay does not manufacture duplicate attention or foreground events.

## Controlled demonstration

The demonstration uses three meaningless synthetic labels:

```text
kren
tar
vel
```

No relations or claims are installed. The purpose is only to verify the developmental path and path-dependent ECWF history.

Sequence:

```text
kren-1
tar-1
vel-1
kren-2
kren-3
kren-4
kren-5
```

Measured result:

| Measurement | Result |
|---|---:|
| Developmental heartbeats | 7 |
| Canonical kernel operation cycles | 21 |
| Concepts | 3 |
| Relations | 0 |
| Claims | 0 |
| Field history frames | 7 |
| Resonance events | 7 |
| Workspace cycles | 7 |
| Active workspace items after final heartbeat | 2 |
| KREN cue resonance before repetition | 0.6730 |
| KREN cue resonance after repetition | 0.8327 |
| Resonance gain | +0.1597 |
| Semantic firewall held | yes |

The kernel operation cycle is 21 because each heartbeat currently contains three separately audited canonical mutations: experience, resonance admission, and workspace admission. The developmental heartbeat count is seven.

The result is **not** evidence of learned abstraction. It demonstrates only that repeated experience changes the later subsymbolic foreground while the symbolic truth store remains protected.

## New files

```text
verdant_development/__init__.py
verdant_development/pipeline.py
verdant_development/demo.py
tests/test_development_phase.py
MILESTONE_12_REPORT.md
artifacts/milestone_12_development_demo.vdk
artifacts/milestone_12_development_summary.json
artifacts/milestone_12_demo_stdout.json
```

## Test result

```text
131 passed
```

Seven new tests cover:

- one-call experience → field → resonance → workspace flow;
- semantic-firewall preservation;
- deterministic sequence replay across independent kernels;
- idempotent event replay without duplicate foreground events;
- atomic rollback after downstream failure;
- path-dependent resonance after accumulated experience;
- contradiction entry into the bounded shared present.

## Current boundary

Milestone 12 is intentionally conservative.

It still does **not** provide:

- autonomous relation reinforcement;
- local spreading activation;
- inhibitory competition between semantic relations;
- learned field-to-symbol proposals;
- earned relational structures/folds;
- cognitive compilation;
- fold-to-fold interaction;
- higher-order fold formation;
- refolding under contradiction.

Those are now attachable to one controlled developmental foreground rather than separate mechanisms.

## Next milestone

**Milestone 13 — Local Plasticity Without Saturation**

The next step should restore developmental symbolic plasticity from V4 under the rebuild's stricter rules.

The design target is not simply "strengthen co-active edges." It should require local evidence, maintain sparsity, support weakening/competition, and expose metrics capable of detecting the V4 failure mode before it becomes global:

```text
local activity
→ candidate reinforcement / inhibition
→ bounded structural change
→ density and selectivity audit
→ persistence only when differentiation survives
```

Milestone 13 should include a long-run saturation test as a first-class regression test.
