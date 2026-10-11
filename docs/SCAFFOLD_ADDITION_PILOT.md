# Teacher-scaffolded addition pilot v0.58

This opt-in educational software experiment connects ordered integer operands
to the existing native successor-counting path. A teacher supplies the operand
token mappings and addition instruction. The adapter and instruction dispatch
are handwritten scaffolds. This measures their guided composition; it does
not establish algorithm discovery or generalized arithmetic.

## Operation and native provenance

`run_addition_pilot` uses a fixed fresh native kernel: seed `79058`, state
dimension `16`, run label `math-addition-v058`. A supplied kernel must match
that complete unexposed fingerprint. Four roles each receive a deep private
copy and exactly twenty-five teaching/prompt experiences:

1. Reuse the nineteen existing counting lessons: eighteen successor facts
   `0 -> 1` through `17 -> 18`, followed by the one-successor-per-token rule.
   The existing `counting._teach` code, original text, declared source and
   event keys are reused, under the new private source state. This does not
   rerun the old counting cohort or its external scoring.
2. Teach five native operand-to-token claims:

   | Right operand | Native token object |
   |---:|---|
   | 0 | `math:tokens:empty` |
   | 1 | `math:tokens:tick` |
   | 2 | `math:tokens:tick,tick` |
   | 3 | `math:tokens:tick,tick,tick` |
   | 4 | `math:tokens:tick,tick,tick,tick` |

3. Teach the addition binding: start at the left operand and use the right
   operand's native token mapping. The incorrect-rule control supplies a
   binding that starts at the right operand instead. The no-rule control
   receives a prompt without an addition instruction in this final slot.

All claims use the existing `ClaimLearningPipeline.record_claim` and typed
`HUMAN_TESTIMONY` support. New mapping/instruction lessons declare
`declared-addition-teacher://v058`; reused counting lessons retain
`declared-counting-teacher://v057`. These are local software source labels,
not authenticated people, physical observations or independent sources.
Original texts, transition IDs, claim IDs and evidence references are stored.

`AdditionRequest` contains only two ordered integers in `0..18`. The response
adapter reads a unique supported native addition-rule claim and a unique
supported native token-mapping claim for the right operand. It decodes the
literal stored token object and passes the actual binding to the unchanged
`count_forward`. It does no numeric addition, does not create tokens from the
numeric right operand, reads no curriculum/answer table and receives no
expected-answer label. No composite sum is taught as a fact.

Replies retain the addition rule and evidence, which input supplies the start
and tokens, the operand-mapping claim and evidence, the actual counting
request, and the complete counting reply with all successor hops and evidence.
A local verifier replays this binding and every native step. It is an execution
replay checker, not an independent proof system or mathematical truth test.
Queries leave the private kernel fingerprint unchanged.

Missing, invalid, opposed or multiple addition rules/token mappings abstain.
Unknown instructions and token encodings are not executed. Token objects over
four tokens are invalid. Missing/conflicting/invalid/cyclic counting links
retain the nested partial/blocking evidence and abstain. Partial walks earn no
answer credit. Even a zero-token identity requires the addition binding, its
operand mapping and a valid counting instruction.

## Frozen cases, scoring and controls

The protocol, teacher inputs, ordered cases and scoring are fixed in source
before the recorded run; their code hashes are captured before any responses.

| Group | Ordered `(left, right)` problems | Cases |
|---|---|---:|
| Zero identity | `(9,0)`, `(10,0)`, `(11,0)`, `(12,0)` | 4 |
| Short composition | `(9,1)`, `(10,2)`, `(11,1)`, `(12,2)` | 4 |
| Held-out composition | Each left in `9..12`, with right `3` and `4` | 8 |

All sixteen ordered pairs are disjoint from the consumed v0.56 fact-recall and
v0.57 counting pairs. Intermediate links, token mappings and both interpreters
are supplied. The held-out group tests new composite problems using those
known scaffolds; it does not test an untaught instruction or independent
held-out replication. All cases are now consumed pilot cases.

| Role | Shared first 24 lessons | Final addition slot |
|---|---|---|
| `taught` | Identical correct counting and token lessons | Start at left, tokens from right |
| `no_rule_control` | Identical | Prompt without addition rule |
| `valid_null` | Identical | Identical taught instruction and operations |
| `incorrect_rule_control` | Identical | Start at right, tokens from right |

Sources, event keys, initial kernel, exposure counts and queries match. The
first twenty-four native lesson traces are identical in every role. Changing
or omitting the last instruction changes text, features and state; these are
not exact timing or processing-cost controls. The independently executed
valid null must match every complete taught trace, checkpoint, reply and grade,
except its role label.

All **64 replies** are frozen before the separate evaluator computes exact
`left + right` and records correct/incorrect/abstained per case. The quantity
is software-task correctness. Incorrect answers are adverse task results;
abstentions earn no correct-answer credit and stay in the denominator. No
case, target, control or metric is adapted to results, and grades provide no
native feedback. These are not physical harm values or v0.53 study cases.

## Recorded result and limits

The separately durable dataset is
[`artifacts/scaffold_addition_v058/pilot.vadd`](../artifacts/scaffold_addition_v058/pilot.vadd).

| Role | Zero correct / 4 | Short correct / 4 | Held-out correct / 8 | Incorrect / 16 | Abstained / 16 |
|---|---:|---:|---:|---:|---:|
| Taught | 4 | 4 | 8 | 0 | 0 |
| No rule | 0 | 0 | 0 | 0 | 16 |
| Valid null | 4 | 4 | 8 | 0 | 0 |
| Incorrect rule | 0 | 0 | 0 | 16 | 0 |

For `9 + 3`, the taught role reads the native mapping for `3`, starts at `9`
and walks `9 -> 10 -> 11 -> 12`. The incorrect binding starts at `3` and walks
`3 -> 4 -> 5 -> 6`, yielding `6`. Both use three actual successor hops; the
wrong result is not repaired by arithmetic. The taught, null and wrong-rule
arms each retain thirty-four hops across their sixteen cases. Zero identities
have no successor hops but retain their rule/mapping provenance.

Adversarial probes establish narrower limits: a wrong mapping from `3` to two
tokens gives `11` for `9 + 3`; an incorrect edge `11 -> 13` gives `13`.
Queries `9 + 5` and reversed `3 + 9` abstain because the right-operand mapping
is absent. `18 + 1` abstains because no successor of `18` was supplied.
These probes do not become prospective study cases or change the frozen
pilot. This path does not validate teacher truth, infer commutativity or
provide unbounded arithmetic. The earlier addition and counting pilots still
replay unchanged. The observed capability is guided native composition.

The dataset has `1023276` bytes, receipt SHA-256
`922618a11646e29d0e96707fa9c6c0d28adbc1fcc4b8b7eb4adfeb5bf3d74c88`
and file SHA-256
`148586a8d060d92afa991135ad8393ea9c87f6a11c76bc797b3c12af10c2254c`.
All **102 addition-pilot tests**, **254 focused tests** and **982 full-suite
tests** pass. Focused/full validation includes the existing load/embed checks
of all **17 legacy checkpoints** and exact replay of both preceding math
pilots. Adversarial coverage includes substituted operand bindings, tokens,
instructions, step lineage, cases, labels, checkpoints, metrics and authority;
false source classes; missing/invalid/conflicting/cyclic dependencies;
source/code drift; immutable publication; and canonical/simulation isolation.
The full run completes in `708.25` seconds in this environment. This duration
is descriptive and establishes no learning-efficiency or physical-harm result.

## Durability, compatibility and trust

The immutable `.vadd` embeds the frozen protocol, full fresh source VDK and
four post-teaching private VDKs, all original lessons/replies/grades, complete
binding/derivation lineage and a twenty-eight-file code/lock-file manifest.
Load/save checks bounded checkpoint/hash/fingerprint/code identity, verifies
each derivation, reruns all native teaching/query/scoring operations and
requires exact whole-result equality. Rehashed operand, instruction, mapping,
step, case, grade, lesson, checkpoint, metric and authority substitutions fail.

The existing 4 MiB sidecar/checkpoint bounds and locked, synced immutable
writer are reused. Duplicate JSON keys and compressed checkpoint members are
rejected. An identical write is idempotent; conflicting occupied paths fail.
Source or code drift rejects completion. New code is isolated under
`verdant_math/addition/`, preserving the original twenty-two-file v0.56 and
twenty-five-file v0.57 manifests. Native checkpoint serialization is unchanged.

The caller's fresh source stays unchanged; restored queries use new private
copies. This path executes no obligation simulations, creates no Attention
allocations or harm/governance outcomes and grants no canonical resolution,
promotion or autonomous policy-rewrite authority. The runtime, operating
system and replay implementation are trusted. Checksums establish local byte
consistency, not teacher identity, independent replication, physical source
authentication or historical execution. Attacks controlling that trusted
runtime are outside this threat model. Implementation drift fails closed;
replay an older recorded result with its matching source version.

## Commands

From the repository with locked dependencies installed:

```bash
python -m verdant_math.addition.cli run artifacts/scaffold_addition_v058/pilot.vadd
python -m verdant_math.addition.cli replay artifacts/scaffold_addition_v058/pilot.vadd
python -m verdant_math.addition.cli query artifacts/scaffold_addition_v058/pilot.vadd --left 9 --right 3
python -m verdant_math.addition.cli query artifacts/scaffold_addition_v058/pilot.vadd --left 9 --right 3 --role incorrect_rule_control
```

The queries return `12` and `6` with complete binding/step evidence. Query
output contains no evaluator target or grade. It installs no experimental
memory into a user's canonical kernel. The no-rule role abstains.

## Next dependency and exclusions

**PROPOSED:** Before extending this curriculum or claiming broad transfer,
freeze a separate coverage/operand-order challenge for the unchanged adapter,
lessons and scoring. Use fresh problems disjoint from all three consumed
pilots and observed adversarial probes; include supported and missing-mapping
or missing-link cases, the same rule controls and exact null. Retain every
abstention and invalid case. This would characterize the actual taught
coverage boundary, not establish algorithm discovery or independent physical
replication. No challenge protocol or evaluation is implemented here.

**MISSING:** Generalized arithmetic, spontaneous rule discovery, mathematical
understanding and evidence that learning makes later learning cheaper remain
unestablished. A verifiable task-linked physical acquisition source, defensible
physical harm protocol and prospective physical study are still absent.
Calibrated physical prediction, causal repair, source independence and
independent held-out replication remain the four mandatory missing N
requirements. The v0.53 preregistration remains unexecuted and unchanged; the
v0.45 Contradiction negative result remains preserved.

No canonical resolution/promotion, autonomous policy rewriting, `T_g`,
thermodynamic behavioral control, semantic understanding, mind, consciousness
or complete-agency claim is introduced.
