# Addition teaching pilot v0.56

This opt-in educational software experiment measures native retention of
teacher-supplied addition facts and the limit of an exact fact-retrieval path.
It needs no sensors, motors, network teacher or external language model.

## Operation and measurement

`run_math_teaching_pilot` starts from a fixed fresh native kernel: seed `79056`,
state dimension `16`, run label `math-teaching-v056`. A supplied kernel must
match that complete fresh fingerprint. Each of four roles gets its own deep
copy. `ClaimLearningPipeline.record_claim` processes explicit lesson text and
records a typed `HUMAN_TESTIMONY` claim with native `TESTIMONY` support. The
source name `declared-math-teacher://v056` is a declaration, not an authenticated
human, device or independent acquisition source.

The response adapter receives only two ordered integer operands, each in
`0..9`. It reads an exact native subject/predicate match and retrieves a unique
affirmed integer object with valid teacher testimony. It performs no addition,
does not inspect evaluator targets or the curriculum answer table, and does
not infer commutativity. Missing, invalid, opposed or multiple answer claims
produce an abstention with complete relevant claim/evidence references.
Queries leave the private kernel fingerprint unchanged.

After all **64 responses** are recorded, a separate evaluator computes exact
integer addition and records `correct`, `incorrect` or `abstained` per case.
The operational quantity is a count of correct answers to this software task.
An incorrect answer is the adverse task result; an abstention earns no
correct-answer credit and remains in the denominator. This quantity has no
physical-harm interpretation and is not enrolled in the v0.53 forecast study.
No historical timings, risk scores or study outcomes supply math labels.

## Frozen lessons, cases and controls

The protocol and scoring are fixed in code before the recorded run. The eight
lessons are:

| Ordered problem | Teacher answer | Incorrect-teacher control |
|---|---:|---:|
| 0 + 0 | 0 | 1 |
| 0 + 1 | 1 | 2 |
| 1 + 1 | 2 | 3 |
| 1 + 2 | 3 | 4 |
| 2 + 2 | 4 | 5 |
| 2 + 3 | 5 | 6 |
| 3 + 3 | 6 | 7 |
| 3 + 4 | 7 | 8 |

Each role receives exactly eight native teaching/prompt experiences followed
by the same sixteen ordered questions. The first eight questions test lesson
retention. The held-out questions are four reversed pairs `(1,0)`, `(2,1)`,
`(3,2)`, `(4,3)` and four new pairs `(1,3)`, `(2,4)`, `(4,4)`, `(4,5)`.
No held-out answer enters a lesson, problem query or native feedback event.

- `taught`: the eight correct teacher facts.
- `no_answer_control`: eight prompts about the same training operand pairs,
  processed through the same text front end without answers or claim proposals.
  Source, event keys, initial kernel and exposure counts match. Lesson text,
  vectors and the resulting state differ because answers/claims are omitted;
  this is not an exact state, timing or processing-cost control.
- `valid_null`: an independently taught copy with exactly the same facts and
  queries as `taught`. Complete traces, observations, checkpoint bytes and
  fingerprints must match, except for the role label.
- `incorrect_teacher_control`: eight explicitly wrong facts, with the same
  source, event keys, operand pairs, native pipeline and exposure count. A
  hidden calculator that repaired these lessons would fail this control.

All cases are retained in fixed order. Missing/incorrect cases are not replaced,
and labels never feed back into learning. These cases are now consumed pilot
cases; a future derivation experiment must freeze a fresh disjoint test set.

## Recorded result

The separately durable dataset is
[`artifacts/arithmetic_teaching_v056/pilot.vmp`](../artifacts/arithmetic_teaching_v056/pilot.vmp).

| Role | Retention correct / 8 | Retention incorrect / 8 | Held-out correct / 8 | Held-out abstained / 8 |
|---|---:|---:|---:|---:|
| Taught | 8 | 0 | 0 | 8 |
| No-answer control | 0 | 0 | 0 | 8 |
| Valid null | 8 | 0 | 0 | 8 |
| Incorrect teacher | 0 | 8 | 0 | 8 |

The no-answer control also abstains on all eight retention cases. The result
establishes persistent native fact retention through this adapter. Held-out
abstention is the expected limit of exact retrieval, not an exhaustive test of
every possible Verdant pathway. The incorrect-teacher result demonstrates that
this path accepts supplied facts without independently verifying arithmetic.
It does not establish a learned addition procedure or mathematical understanding.

All **55 math-pilot tests**, **75 focused tests** and **803 full-suite tests**
pass. The focused and full runs include the existing load/embed check of all
**17 legacy checkpoints**. Adversarial checks cover answer-oracle exclusion,
all-response capture before grading, conflicting/negated claims, false source
classes, substituted cases/lessons/evidence/checkpoints, retuned scoring,
authority escalation, source/code drift, payload bounds and immutable
publication failure. Native checkpoint serialization remains unchanged.

## Durability, replay and trust limits

The immutable `.vmp` contains the full frozen protocol, original response and
grade records, lesson transition/claim/evidence lineage, the fresh source VDK,
all four private post-teaching VDKs and implementation/lock-file hashes. Existing
native checkpoint serialization is reused; no kernel schema is extended.
Publication reuses the existing locked, synced immutable-sidecar writer. An
identical write is idempotent; a conflicting occupied path fails.

Load/save verifies envelope and checkpoint hashes, bounded stored ZIP members,
native fingerprints and the current implementation manifest, then reruns the
complete native teaching/query/grading protocol on fresh private copies and
requires exact whole-result equality. Files are bounded to 4 MiB, duplicate
JSON keys and compressed checkpoint members are rejected. Reload does not
change the caller's canonical kernel or any existing simulation ledger.
This pilot does not invoke the obligation simulation runtime or fund Attention.

The threat model assumes the local Python runtime, operating system and replay
implementation are trusted. Rehashed case, label, scoring, source, checkpoint,
code-manifest and authority substitutions are checked against the fixed
execution. Checksums do not authenticate a physical source, establish who
provided a lesson, resist an attacker controlling the replay process, or prove
an historical execution occurred at a particular time. Matching replay is
local reproducibility, not independent held-out replication. Implementation
drift fails closed; replay the recorded version to inspect an older result.

## Commands

From the repository with the locked dependencies installed:

```bash
python -m verdant_math.pilot_cli run artifacts/arithmetic_teaching_v056/pilot.vmp
python -m verdant_math.pilot_cli replay artifacts/arithmetic_teaching_v056/pilot.vmp
python -m verdant_math.pilot_cli query artifacts/arithmetic_teaching_v056/pilot.vmp --left 2 --right 3
python -m verdant_math.pilot_cli query artifacts/arithmetic_teaching_v056/pilot.vmp --left 3 --right 2
```

The first query recalls `5`; the second abstains. `query` restores a new private
replay-verified copy, emits native fact/evidence references and supplies no
expected-answer or grading label. `--role incorrect_teacher_control` permits
inspection of the deliberately wrong memory. No operation installs these
experimental memories into a user's canonical kernel.

## Next dependency and exclusions

**PROPOSED:** An explicitly taught counting/successor and addition-rule path
with checkable native derivation traces, fresh frozen held-out problems,
no-rule/incorrect-rule controls and exact null replay. Any procedure supplied
by a teacher must remain labelled as a teacher-supplied scaffold. An evaluator
calculator cannot become the learner's answer path.

**MISSING:** Generalized arithmetic, spontaneous rule discovery, mathematical
understanding and evidence that learning makes later learning cheaper. The
operational physical measurement/harm protocol and its acquisition source are
still absent. Calibrated physical prediction, causal repair, source independence
and independent held-out replication remain the four mandatory missing N
requirements. This educational track does not satisfy them, revise the v0.53
preregistration or alter the v0.45 Contradiction negative result.

No canonical resolution/promotion, autonomous policy rewriting, `T_g`,
thermodynamic behavioral control, semantic understanding, mind, consciousness
or complete-agency claim is introduced.
