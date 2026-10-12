# Prospective teacher-scaffolded operand-order protocol v0.60

This increment freezes one supplied instruction and a future test design. It
implements no operand-swapping adapter, installs no instruction and produces
no new math response or evaluation. The v0.59 result `13 + 1` succeeding while
`1 + 13` abstains grounds the design: the unchanged addition path uses the
right operand's native token mapping, and only mappings for `0` through `4`
have been supplied. Successor facts stop at `18`.

## Instruction and native authorization

A future adapter must read the new instruction from one positive, affirmed,
unopposed `HUMAN_TESTIMONY` claim under subject
`math:procedure:addition_operand_order` and predicate
`math_uses_operand_order_rule`, retaining its complete claim/evidence closure.
The declared teacher source is `declared-operand-order-teacher://v060`; this
label does not authenticate the teacher. The proposed authority is restricted
to read-only routing in a private math kernel. It grants no canonical,
Council, Attention, promotion, resolution or policy-rewrite authority.

The correct supplied label is
`math:rule:swap_only_for_missing_right_mapping`. Its future rules are:

1. Keep the original ordered request intact. Check the original right operand
   through the existing native lookup and token decoder. A valid mapping
   keeps the original order.
2. Only an **absent** right mapping permits checking the original left
   mapping. Swap once only when that left mapping has valid native testimony
   and a supported decoded token sequence. Never reconstruct tokens from an
   integer, sort operands, retry recursively or use arithmetic as a fallback.
3. Conflicting, invalid or unsupported right evidence blocks swapping.
   Missing, conflicting, invalid or unsupported left evidence also produces
   an abstention with both available lookup histories retained.
4. Pass the original or authorized transposed request to the unchanged v0.58
   addition interpreter and v0.57 counting walker. Retain their complete
   instruction, mapping, successor and blocking evidence. A terminal failure
   keeps every partial step and produces no partial answer credit.

The future response contract includes the local run and case references,
private-kernel fingerprint, **original request**, **effective request**,
instruction claim/evidence, original-right lookup, left lookup if checked,
route disposition and the full nested unchanged addition reply. A later
trace verifier must reconstruct these against native records; declaring
these fields does not implement or test that verifier today.

Missing ordering instruction falls back to the unchanged original-order
addition path. A conflicting, invalid or unsupported ordering instruction
must remain visible and produce abstention. The future adapter, native
instruction installation and routing behavior are all still missing.

## Fixed controls and component reuse

Each future role starts from a distinct pristine private copy of the fresh
seed `79060`, state dimension `16`, run label `math-operand-order-v060` kernel.
Each receives the **same 25 correct v0.58 lessons**, then one order-instruction
or prompt slot. The old addition rule is present in every role.

| Role | Twenty-sixth slot |
|---|---|
| Taught | Correct missing-right-mapping instruction |
| No instruction | Prompt without an ordering claim; retain all old addition lessons |
| Exact valid null | Repeat the complete taught operations on another pristine private copy |
| Incorrect instruction | `math:rule:swap_only_for_found_right_mapping` |

The incorrect instruction uses the opposite trigger: a valid original-right
mapping permits a transposition regardless of left mapping availability; an
absent right mapping keeps the original order. Conflicting or invalid right
evidence still blocks routing. Any missing effective mapping is preserved by
the unchanged addition interpreter. This control need not return numerically
wrong answers; its outputs must be recorded rather than designed to force a
particular grade.

The original 22/25/28/31-file manifests, all four consumed cohort records,
old interpreters, lessons and grader remain byte-unchanged. The new protocol
uses a separate sibling package and a 34-file manifest. A future adapter must
live in another versioned sibling, preserving replay of this declaration and
the earlier artifacts. No future execution is authorized merely by creating
this sidecar. The software math path reserves no obligation simulation budget.

## Unanswered prospective cohort

The forty original typed inputs are frozen in the sidecar. Both possible
ordered pairs are checked against all four consumed cohorts and recorded
probes, including earlier rejected requests. The exclusions retain 26 typed
probe records from the four preserved test sources. Counting requests are
also projected to ordered `(start, token_count)` exclusions: this retains
the previously rejected `5` with five ticks as `(5,5)`, and the first pilot's
rejected `(10,1)`. These exclusions are historical inputs, not new queries.
The source test files and five exact historical artifacts are bound by hashes.

| Predeclared group | Original inputs | Count |
|---|---|---:|
| Original mapping | `(5,0)`, `(6,0)`, `(7,0)`, `(8,0)`, `(13,0)`, `(14,0)`, `(13,2)`, `(14,3)` | 8 |
| Swap candidate | The reversals of those eight pairs | 8 |
| Both mappings absent | `(5,6)`, `(6,5)`, `(7,7)`, `(14,15)`, `(15,15)`, `(16,16)`, `(12,13)`, `(13,12)` | 8 |
| Terminal link | `(18,3)`, `(17,3)`, `(16,4)`, `(17,4)` and their reversals | 8 |
| Invalid input | Typed payloads listed below | 8 |

The invalid inputs are `{"left":12,"right":true}`, `{"left":null,"right":4}`,
`{"left":11,"right":"4"}`, `{"left":15,"right":0.5}`,
`{"left":25,"right":4}`, `{"left":16}`,
`{"left":14,"right":0,"answer":0}`, and `{"left":[15],"right":0}`.
Only the unchanged strict `AdditionRequest` determines input validity.
Original JSON types, error locations and error type codes must remain visible.
There is no fabricated arithmetic target for a rejected input.

Groups describe predeclared taught coverage, not observed new outcomes. They
cannot be supplied to a response path or relabeled when a control follows a
different route. No case may be dropped, substituted, repeated or replaced
because of its result. All forty cases remain unanswered in this increment.

## External scoring and complete denominators

All **160** future response/rejection records must be collected before any of
the **128** valid-input grades. The unchanged v0.58 arithmetic grader must use
the **original request**; case/group/split labels must not reach the response
path. Its exact integer `left + right` target and correct/incorrect/abstained
classification stay outside native memory, with no feedback or metric tuning.

Every role has a denominator of **40 enrolled cases** and a secondary count
over **32 valid inputs**. Abstentions, blocked and partial walks receive no
answer credit; eight invalid inputs stay in the enrolled denominator with no
arithmetic target. A supported-only score cannot replace either full count.
The future null must match every complete taught record apart from its role
label. Missing or divergent records prevent completion rather than allowing
replacement. No grades or performance results exist yet.

## Persistence, isolation and trust limits

The separately immutable declaration is
[`protocol.vaop`](../artifacts/operand_order_v060/protocol.vaop).
It is `30,761` bytes, with declaration SHA-256
`1f92621d9572c5068babc6d880d239100f4847c511ead8bb10f8d2ffaa4beba8`
and file SHA-256
`09c6d2e0c914aa8fb8f256d59cf6ba81bfda87345413b68817bb6515dec39407`.
It contains exact instructions, cases, controls, exclusions, historical file
references, current code/probe manifests and an unexposed source VDK.
Publication uses the existing bounded locked/synced immutable writer.
Identical publication is idempotent; conflicting paths stay unchanged.
Historical/code/probe paths and their symlink aliases are protected.

Freeze and reload compare canonical bytes, current pinned historical files,
old implementation manifests and a pure source reconstruction. They invoke
no teaching, arithmetic response, grader, Attention allocation or simulation.
Historical compatibility testing may replay earlier **consumed** cohorts;
it does not execute these new cases. A subsequent evaluation must bind exact
saved protocol bytes and frozen adapter bytes in a separate immutable result.

Trusted components are the local runtime, filesystem and replay implementation.
Hashes and local replay establish consistency under those components, not
teacher authentication, mathematical truth, historical freeze-time proof,
source independence or independent physical replication. An attacker who
controls the trusted code/filesystem before declaration can change the study;
no acquisition or signature authentication is claimed. Writer checks add no
new process-kill or power-loss proof.

```bash
python -m verdant_math.ordering_protocol.cli freeze artifacts/operand_order_v060/protocol.vaop
python -m verdant_math.ordering_protocol.cli replay artifacts/operand_order_v060/protocol.vaop
```

There is deliberately no `run` or `query` command.

## Claim boundary and next dependency

**OBSERVED:** All 94 new protocol tests, all 447 focused math/archive tests,
and all 1,171 full-suite tests pass, including the 17 legacy checkpoint
load/embed checks and replay of all four earlier math experiments. The
prospective source has no
installed lessons or responses. Freeze/reload succeed with teaching,
response, grading and simulation entry points blocked. Rehashed declaration,
source, control, scoring, case/order/type/probe and authority changes fail;
foreign/stale inputs, drift, malformed/oversized bytes, occupied paths and
injected replacement failure are covered. These test declaration integrity,
not future native routing behavior or learning performance.

**IMPLEMENTED-EXPERIMENTAL:** One pure prospective declaration and immutable
`.vaop`, exact historical/probe/code pairing, fresh typed exclusions,
freeze/replay CLI, and explicit future instruction/provenance/control/scoring
requirements. This implements neither the adapter nor instruction installation,
derivation verifier or evaluation.

**PROPOSED:** Build one separate opt-in operand-order adapter and native trace
verifier that satisfy this frozen contract. Freeze those implementation bytes
before a **later, separate** evaluation of this cohort. Preserve the original
ordered inputs and all missing/conflicting/invalid/partial evidence.

**MISSING:** Actual swapping, new performance results, generalized arithmetic,
spontaneous commutativity/rule discovery, mathematical understanding and
learning making later learning cheaper remain unestablished. The physical
track still lacks verifiable task-linked acquisition and defensible harm
scoring; the v0.53 prospective study is unexecuted. Calibrated physical
prediction, causal repair, source independence and independent held-out
replication remain the four mandatory missing N requirements. Quarantined
timings/intake and the v0.45 Contradiction negative result are unchanged.
No canonical resolution/promotion, autonomous policy rewriting, `T_g`,
thermodynamic behavioral control, mind, consciousness or complete-agency claim
is introduced.
