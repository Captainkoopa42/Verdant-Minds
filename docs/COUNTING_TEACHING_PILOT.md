# Successor counting pilot v0.57

This opt-in educational software experiment composes native teacher-supplied
successor facts. Both the counting instruction and the bounded interpreter
are supplied explicitly. The result tests following that scaffold; it does
not establish discovery of a counting algorithm or generalized addition.
No sensors, motors, network teacher or external language model are required.

## Operation and measurement

`run_counting_pilot` starts from a fixed fresh native kernel: seed `79057`,
state dimension `16`, run label `math-counting-v057`. A supplied kernel must
match that complete fresh fingerprint. Four roles each receive a deep private
copy and exactly nineteen native teaching/prompt experiences. The existing
`ClaimLearningPipeline.record_claim` records eighteen `HUMAN_TESTIMONY`
successor facts, `0 -> 1` through `17 -> 18`, and a procedure claim in the
nineteenth slot. The no-rule control receives a prompt without a procedure
claim in that final slot. Original lesson text and native transition, claim
and evidence references are retained. `declared-counting-teacher://v057`
identifies a declared software teacher; it authenticates no person or source.

The query contains only an integer start in `0..18` and zero to four literal
`tick` tokens. The handwritten interpreter recognizes two native instruction
labels: follow one successor per token, or follow two successors per token.
It reads each actual native edge target; it performs no numeric addition,
does not inspect curriculum tables, expected answers or grading labels, and
does not repair incorrect testimony. Each accepted hop records its token and
application indices, numeric endpoints, native claim ID and support evidence.
The procedure claim and its evidence are also recorded. Verification compares
the complete derivation with read-only native execution replay. It is a local
replay checker, not an independent proof system.

Missing, invalid, opposed, multiple or cyclic successor claims cause an
abstention. Invalid or ambiguous instructions also cause an abstention.
Relevant opposing and blocking evidence remains visible, and partial walks
earn no answer credit. Zero tokens return the supplied start only after a
valid supported instruction is found. Queries leave the private fingerprint
unchanged; every restored query memory is a fresh private copy.

All **64 replies** are frozen before an external evaluator computes
`start + token_count` and records `correct`, `incorrect` or `abstained`.
The quantity is exact software-task correctness. Incorrect answers are adverse
task results; abstentions receive no correct-answer credit and remain in the
denominator. This measure has no physical-harm interpretation. Grades supply
no native feedback, Attention allocations, harm outcomes or study cases.

## Frozen cases and matched controls

The protocol, cases and scoring are fixed before the recorded run:

| Group | Starts | Tokens per query | Cases |
|---|---|---|---:|
| Direct successor | 5, 6, 7, 8 | 1 | 4 |
| Short composition | 5, 6, 7, 8 | 2 | 4 |
| Held-out composition | 5, 6, 7, 8 | 3 and 4 | 8 |

The ordered `(start, token_count)` pairs are disjoint from all sixteen
previously consumed v0.56 operand pairs. No composite answer is taught as a
fact. All intermediate successor links and the procedure are supplied, so
the held-out group tests longer compositions of known facts, not novel
integer concepts, an untaught rule or independent held-out replication.
All sixteen cases per role remain in fixed order; none are adapted or replaced
according to results. These cases are now consumed pilot cases.

| Role | Shared successor lessons | Final procedure slot |
|---|---|---|
| `taught` | All eighteen correct facts | One successor per token |
| `no_rule_control` | Identical eighteen facts | Prompt without a rule claim |
| `valid_null` | Identical eighteen facts | Identical taught rule and operations |
| `incorrect_rule_control` | Identical eighteen facts | Two successors per token |

Source, event keys, exposure count, initial kernel and queries match. The
first eighteen lesson traces are identical in every role. Omitting or changing
the final instruction changes text, features and state; those arms are not
exact processing-cost or timing controls. The independently executed valid
null must match all taught lessons, replies, grades, checkpoint bytes and
fingerprints, except for its role label. A hidden arithmetic correction would
fail the incorrect-rule control.

## Recorded result

The separately durable dataset is
[`artifacts/counting_teaching_v057/pilot.vcount`](../artifacts/counting_teaching_v057/pilot.vcount).

| Role | Direct correct / 4 | Short correct / 4 | Held-out correct / 8 | Incorrect / 16 | Abstained / 16 |
|---|---:|---:|---:|---:|---:|
| Taught | 4 | 4 | 8 | 0 | 0 |
| No-rule control | 0 | 0 | 0 | 0 | 16 |
| Valid null | 4 | 4 | 8 | 0 | 0 |
| Incorrect rule | 0 | 0 | 0 | 16 | 0 |

For example, starting at `5` with three tokens traverses `5 -> 6 -> 7 -> 8`
under the taught instruction. The incorrect instruction follows six actual
links to `11`, without correction by the evaluator. An adversarial incorrect
successor `7 -> 9` changes the three-token response to `9`; a missing or
conflicting edge causes an abstention. This supports native fact composition
through the declared adapter. It does not establish that Verdant independently
learned a counting instruction, verifies mathematical truth, or has an addition
procedure. The v0.56 fact-recall result still replays unchanged.

The dataset has `786484` bytes, receipt SHA-256
`deacf11110f39b7d04b42d5ef201f0c4a0fd0c038c303234c59ee5cf36895611`
and file SHA-256
`dd93ba95dd5e556541e57dfbaf9e4f8fb486547f401d4e07c7b47c8a0227fe2c`.
All **77 counting-pilot tests**, **152 focused tests** and **880 full-suite
tests** pass. The focused and full runs include all **17 legacy checkpoint**
load/embed checks. Adversarial coverage includes wrong, missing, invalid,
conflicting and cyclic links; source/code drift; forged derivation, case,
lesson, grade and authority records; payload bounds; immutable publication;
native checkpoint/mapping-order replay; unchanged v0.56 replay; and canonical
and simulation isolation. The full suite completes in `645.94` seconds in this
environment; this runtime is descriptive and is not a learning-efficiency or
physical-harm measurement.

## Durability, compatibility and trust limits

The immutable `.vcount` embeds the frozen protocol, full fresh source VDK,
four post-teaching VDKs, original teaching/response/grade records, every native
derivation and a twenty-five-file code/lock-file manifest. It reuses the
existing bounded checkpoint reader and locked, synced immutable sidecar writer.
An identical write is idempotent; conflicting occupied paths fail. Duplicate
JSON keys, oversized files and compressed native checkpoint members are
rejected. The file bound remains 4 MiB.

Load/save validates hashes, native fingerprints and implementation identity,
checks each native derivation, then reruns the full fixed teaching/query/grading
protocol and requires exact whole-result equality. Rehashed changes to lessons,
cases, replies, trace fields, targets, grades, checkpoints, scoring or authority
flags fail. Source or implementation drift rejects completion. Native checkpoint
serialization is unchanged. New code lives in `verdant_math/counting/`; the
twenty-two-file manifest and original code of the v0.56 pilot remain unchanged.
Both recorded pilots can replay on this version.

The caller's source remains unchanged. This path invokes no obligation
simulations and makes no canonical, simulation-ledger, resolution, promotion
or autonomous policy changes. Its local runtime, operating system and replay
implementation are trusted. Checksums do not prove teacher identity, resist
an attacker controlling that runtime, authenticate physical readings or prove
an historical execution occurred. Deterministic local replay provides no
independent replication. Implementation drift fails closed; inspect a recorded
pilot using its matching source version.

## Commands

From the repository with locked dependencies installed:

```bash
python -m verdant_math.counting.cli run artifacts/counting_teaching_v057/pilot.vcount
python -m verdant_math.counting.cli replay artifacts/counting_teaching_v057/pilot.vcount
python -m verdant_math.counting.cli query artifacts/counting_teaching_v057/pilot.vcount --start 5 --ticks 3
python -m verdant_math.counting.cli query artifacts/counting_teaching_v057/pilot.vcount --start 5 --ticks 3 --role incorrect_rule_control
```

The queries return `8` and `11`, with their complete native paths. Query output
contains no expected answer or grade and installs no experimental memory into
a user's canonical kernel. `--role no_rule_control` returns an abstention.

## Next dependency and exclusions

**PROPOSED:** One explicitly teacher-scaffolded addition adapter after this
counting prerequisite, with native operand-to-counting instruction provenance,
checkable derivations and fresh frozen problems disjoint from both consumed
pilots. Freeze no-rule/incorrect-rule and exact null controls before its run.
An evaluator's arithmetic must stay outside the response path. This increment
does not implement that adapter or claim algorithm discovery.

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
