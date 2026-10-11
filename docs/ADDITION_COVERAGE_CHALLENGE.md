# Addition coverage and operand-order challenge v0.59

This explicitly invoked software experiment measures the sampled coverage of
the **unchanged** v0.58 addition adapter, teacher lessons and arithmetic grader.
It extends no curriculum or instruction. Its case groups describe the taught
dependency boundary; they are fixed before observing any arm's result.

## Frozen cohort and controls

The source is a fresh kernel with seed `79059`, state dimension `16`, and run
label `math-coverage-v059`. Each of four private copies receives exactly the
existing twenty-five v0.58 lessons/prompt slots. The correct rule starts at the
left operand; the incorrect rule starts at the right operand. The no-rule arm
has the existing final prompt without an addition claim. The independent
valid null repeats the complete taught operations. The first twenty-four
native lessons must match across all roles, and the entire null must match the
taught result except for its role name. Different final text/features/state
make the two rule controls unsuitable as exact processing-cost controls.

| Frozen group | Ordered input pairs or original JSON inputs | Cases |
|---|---|---:|
| Supported small orders | `(0,2)`, `(2,0)`, `(0,3)`, `(3,0)`, `(0,4)`, `(4,0)`, `(1,4)`, `(4,1)` | 8 |
| Supported large left | `(13,1)`, `(14,2)`, `(15,3)`, `(16,2)` | 4 |
| Reversed, missing mapping | `(1,13)`, `(2,14)`, `(3,15)`, `(2,16)` | 4 |
| Other missing mapping | `(6,6)`, `(8,7)`, `(17,5)`, `(18,18)` | 4 |
| Missing successor | `(17,2)`, `(16,3)`, `(15,4)`, `(18,2)` | 4 |
| Invalid input | `{"left":14,"right":false}`, `{"left":null,"right":2}`, `{"left":16,"right":2.5}`, `{"left":13,"right":"2"}`, `{"left":20,"right":2}`, `{"left":17}`, `{"left":18,"right":0,"answer":18}`, `{"left":[14],"right":1}` | 8 |

All twenty-four valid ordered pairs are disjoint from the consumed v0.56,
v0.57 and v0.58 cohorts, and the previously observed valid probes `(9,5)`,
`(3,9)` and `(18,1)`. Original typed invalid payloads are also disjoint from
the ten recorded v0.58 invalid-input probes. Exact consumed pairs and typed
probe exclusions are embedded in the plan. Freshness concerns this software
cohort, not new physical observations or independent replication. Teaching
facts and interpreters remain supplied, and these new cases are consumed
once the challenge runs.

Eight order-pair identifiers link opposite orders: four pairs with both right
operands mapped, and four with only the smaller right operand mapped. No
commutativity rule or operand sorting is added. The four missing-link cases
require a successor beyond the supplied terminal `18`; any available partial
walk must remain in the reply with no partial-answer credit. Categories stay
fixed even when the incorrect rule starts elsewhere and avoids that missing
link. No case is dropped, replaced, relabeled or repeated in response to its
outcome.

## Freeze, response and scoring boundary

`freeze_coverage_plan` produces no teaching or responses. The immutable
`.vacp` must be saved and successfully validated **before** any challenge
teaching/query. It contains the exact cases and typed original JSON, controls,
scoring/invalid handling, full unexposed source VDK, claim boundaries and a
thirty-one-file manifest: the original twenty-eight source/lock files plus the
three new wrapper files. All original adapters, lessons and graders keep their
original bytes and manifests.

Only the unchanged `AdditionRequest` validates an input. Accepted requests
contain just ordered `left` and `right` integers and go to the unchanged
`derive_addition`; the response path receives no case group, pairing, target
or grade. Invalid payloads retain their typed original JSON and the API's
error locations/type codes, without a fabricated arithmetic answer or target.
They are input rejections, distinct from native evidence-based abstentions.

All **128 responses or input rejections** are frozen before invoking the
unchanged v0.58 `addition._grade` on the 96 accepted inputs. Its exact-integer
`left + right` mapping and correct/incorrect/abstained rules are reused.
Only its arithmetic result/grade are copied; its old pilot case/split labels
are irrelevant to this new cohort. No numeric arithmetic supplies a native
response, and grades provide no native feedback.

Every role retains a denominator of **32**, including eight invalid inputs.
Invalid inputs earn no correct-answer credit and carry no arithmetic target.
Every native abstention retains the complete instruction, operand mapping,
partial counting and blocking evidence available to that reply. A secondary
accepted-input count uses the fixed denominator of 24 and does not omit
abstentions. This is software-task correctness, not a physical harm metric or
a v0.53 study execution.

## Recorded evaluation

The separately durable frozen plan is
[`challenge.vacp`](../artifacts/addition_coverage_v059/challenge.vacp), and its
complete evaluation is
[`evaluation.vacr`](../artifacts/addition_coverage_v059/evaluation.vacr).
The plan was successfully saved before the first challenge teaching/query.

| Role | Correct | Incorrect | Abstained | Invalid input | Retained |
|---|---:|---:|---:|---:|---:|
| Taught | 12 | 0 | 12 | 8 | 32 |
| No rule | 0 | 0 | 24 | 8 | 32 |
| Exact valid null | 12 | 0 | 12 | 8 | 32 |
| Incorrect rule | 0 | 16 | 8 | 8 | 32 |

Taught and exact null each answer all twelve supported cases correctly:
eight small-operand orders and four large-left compositions. They abstain on
all eight cases with a missing right-operand mapping and all four terminal
successor failures. The wrong rule abstains on the same missing-mapping cases,
but its alternative starting point gives four wrong responses in the frozen
missing-successor group; those cases are retained without reclassification.
The no-rule control abstains on every accepted input. All roles reject all
eight malformed inputs, preserving original types and rejection metadata.

For example, both `0 + 2` and `2 + 0` return `2` using their respective known
right-operand mappings. `13 + 1` returns `14`, whereas `1 + 13` abstains because
the mapping for right operand `13` is absent. `16 + 3` retains the partial walk
`16 -> 17 -> 18`, then abstains because no successor for `18` exists. The wrong
rule starts at `3` and returns `6`; the external target is `19`, without feeding
that target back into the response path.

These observations characterize the actual sampled coverage boundary. On the
frozen cohort the taught role earns `12/24` accepted-input correctness and
`12/32` enrolled-case correctness, with no incorrect native answer. Its
`12/12` supported-case score is a narrower description, not a substitute for
either complete denominator. The difference from v0.58's `16/16` comes from
different predeclared coverage cases with unchanged teaching and code; it is
not evidence of learning deterioration, broad transfer or learning efficiency.

| Artifact | Bytes | Payload SHA-256 | File SHA-256 |
|---|---:|---|---|
| Plan | 22329 | `7a755f64274a9d79e689adfecb463f6c891c514b16a398833fc82cd8d85fe059` | `d01dd5280a1bba38342b5305e552b3eacaf12f68d12d0d64230460a0822f0fbf` |
| Evaluation | 1063072 | `dc5e788bfc1db9f2dcf4ad3c3a9fb4a3a7d770aab44c295efb56331b5bb8c2cd` | `853da03a48bf68905f4eb2b46433e9e1958a98a515d192f53e7bb68faa81840e` |

All **95 new challenge tests**, **353 combined math/archive tests** and
**1077 full-suite tests** pass, including the existing load/embed checks of all
**17 legacy checkpoints** and exact original-manifest replay of the three
prior math pilots. The full run completes in `772.93` seconds in this
environment. This descriptive duration is no learning-efficiency or physical
harm result.

## Durability, isolation and threat model

The separate immutable `.vacr` embeds its frozen plan and binds the **exact
saved plan bytes** by SHA-256. It contains all four post-teaching native VDKs,
original lessons, 128 records, derivations and rejection metadata, and external
grades. Replay requires the separate matching plan file, checks current source
identity, reconstructs all native replies/input rejections and reruns the
complete teaching/query/scoring execution. Any changed case order, group,
pairing, raw type, trace, grade, lesson, checkpoint or authority must fail.

The existing bounded VDK decoder and 4 MiB immutable locked/synced writer are
reused. Identical publication is idempotent; conflicting files are preserved
and rejected. Missing plans fail before teaching/query. Source, code or plan
drift prevents completion. Serialization and canonical checkpoint behavior
are unchanged. New code lives only in `verdant_math/coverage/`, preserving
all three earlier math pilots and source manifests.

The caller's fresh canonical source stays unchanged. Each taught/control
kernel is a deep private copy; queries are read-only. This path reserves no
simulation budget, executes no obligation simulation, creates no Attention
allocation or physical/governance outcome, and grants no resolution,
promotion or autonomous policy rewriting authority.

Trusted components are the local runtime, filesystem and replay implementation.
The teacher's source labels remain self-declared `HUMAN_TESTIMONY`. Hashes and
local replay check byte consistency and execution lineage under that trusted
runtime; they do not authenticate a teacher, prove historical freeze timing,
validate mathematical truth or supply independent physical acquisition.
Attacks controlling the trusted runtime/filesystem before enrollment are
outside this threat model. Replay of an older sidecar needs matching code.

## Commands

```bash
python -m verdant_math.coverage.cli freeze artifacts/addition_coverage_v059/challenge.vacp
python -m verdant_math.coverage.cli run artifacts/addition_coverage_v059/challenge.vacp artifacts/addition_coverage_v059/evaluation.vacr
python -m verdant_math.coverage.cli replay artifacts/addition_coverage_v059/challenge.vacp artifacts/addition_coverage_v059/evaluation.vacr
```

## Claim boundary and exclusions

**OBSERVED:** The 128-record evaluation retains every fixed case, including
all native abstentions and invalid inputs. Supported order pairs succeed;
reversed pairs needing an absent right-operand mapping abstain. These are
coverage observations about unchanged supplied instruction/mapping/link facts.

**IMPLEMENTED-EXPERIMENTAL:** One separately durable challenge plan and
evaluation wrapper, opt-in freeze/run/replay commands, exact old lesson/grader
reuse, complete fixed-denominator accounting, native derivation and rejection
replay, and unchanged canonical/simulation isolation. No new arithmetic
interpreter, operand reordering rule or curriculum is implemented.

**PROPOSED:** The asymmetric order result grounds a next **protocol-only**
increment: freeze one explicitly teacher-scaffolded operand-order instruction
before implementing it. Specify original-order versus authorized swapped-order
provenance, fresh problems disjoint from all four consumed cohorts and probes,
no-instruction/incorrect-instruction/exact-null controls, absent-mapping/link
cases, invalid handling and external scoring before any new responses. A
supplied swapping instruction would remain teacher guidance; it would not
establish spontaneous commutativity discovery. This increment implements
neither that protocol nor an operand-swapping adapter.

**MISSING:** This coverage result cannot establish generalized arithmetic,
spontaneous rule discovery, mathematical understanding or learning making
later learning cheaper. It
provides no verifiable task-linked physical acquisition source, defensible
physical harm protocol or prospective physical study. Calibrated physical
prediction, causal repair, source independence and independent held-out
replication remain the four mandatory missing N requirements. The v0.53
preregistration stays unexecuted and unchanged; the v0.45 Contradiction
negative result is preserved. No canonical resolution/promotion, autonomous
policy rewriting, `T_g`, thermodynamic behavioral control, or semantic
understanding, mind, consciousness or complete-agency claim is introduced.
