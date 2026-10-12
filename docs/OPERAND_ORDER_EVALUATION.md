# Frozen teacher-scaffolded operand-order evaluation v0.62

This increment executes exactly the forty prospective v0.60 cases in each of
the four v0.61 private roles. It changes neither frozen input package, old
interpreter, instruction, case, control nor grader. A separate immutable
response batch is published before any external grade; the result then binds
those exact saved bytes.

## Durable response-before-grade boundary

The explicitly invoked runner first validates the exact v0.60 `.vaop`, exact
v0.61 `.vaoi`, their current code manifests and the unexposed frozen source.
It constructs four distinct private copies and installs the same twenty-five
v0.58 lessons plus the role's frozen order slot. Every role then receives all
forty original typed requests in frozen order.

The response path parses only each raw request and gives the adapter its two
operands plus fixed run/case references. It receives no expected answer,
external grade or group/pair label as a behavioral input. Each valid response
retains the original request, any one-transposition effective request, native
instruction and mapping lookups, route, and complete nested addition/counting
reply. Invalid inputs retain the original JSON type and strict validation error
metadata. No record is retried, sorted, replaced or suppressed.

Only after all 160 records validate as one complete batch does the immutable
[`responses.vaob`](../artifacts/operand_order_v062/responses.vaob) exist. A
separate invocation then gives the unchanged v0.58 arithmetic grader the 128
valid **original** requests. The eight invalid inputs per role remain enrolled
and visibly ungraded. An evaluator-only abstention projection supplies no
numeric value when a blocked order route has no nested `AdditionReply`; it is
not stored as native evidence and the unchanged grader reads only its absent
answer.

The CLI preserves this order:

```bash
python -m verdant_math.ordering_evaluation.cli run \
  artifacts/operand_order_v060/protocol.vaop \
  artifacts/operand_order_v061/implementation.vaoi \
  artifacts/operand_order_v062/responses.vaob \
  artifacts/operand_order_v062/evaluation.vaor

python -m verdant_math.ordering_evaluation.cli replay \
  artifacts/operand_order_v060/protocol.vaop \
  artifacts/operand_order_v061/implementation.vaoi \
  artifacts/operand_order_v062/responses.vaob \
  artifacts/operand_order_v062/evaluation.vaor
```

If response capture fails, neither artifact is published. If grading fails,
the already complete ungraded response batch remains auditable and no result
appears. Reload statically reconstructs every native route, mapping, successor
step, typed rejection and grade without calling teaching, response or grader
entry points again.

## Complete observed result

Each role keeps the full denominator of 40 enrolled cases: 32 valid requests
and eight typed invalid requests. Correctness below is always over the original
ordered request.

| Role | Correct | Incorrect | Abstained | Invalid, ungraded | Valid-input rate | Enrolled rate |
|---|---:|---:|---:|---:|---:|---:|
| Taught | 16 | 0 | 16 | 8 | 16/32 | 16/40 |
| Exact valid null | 16 | 0 | 16 | 8 | 16/32 | 16/40 |
| No instruction | 8 | 0 | 24 | 8 | 8/32 | 8/40 |
| Incorrect instruction | 0 | 0 | 32 | 8 | 0/32 | 0/40 |

The taught and exact-null arms are complete-record equal apart from their outer
role label. Their eight original-mapping cases keep order and answer correctly;
their eight swap-candidate cases transpose once and answer correctly. All eight
both-mappings-absent cases block with both native lookup outcomes visible. All
eight terminal-link cases preserve a nested partial or immediately blocked
successor walk and abstain.

The no-instruction control answers only the eight original-mapping cases. It
retains original order and abstains on every swap-candidate, absent-mapping and
terminal case. The incorrect instruction applies its prospectively frozen
opposite trigger and abstains on all 32 valid cases. The protocol explicitly
did not require this control to manufacture wrong numeric answers, and none
were observed.

Within this fixed software cohort, the supplied correct order instruction adds
eight correct responses relative to no instruction, all in the predeclared
swap-candidate group. It does not repair the other sixteen valid failures. The
supported-only `16/16` is therefore not a substitute for either full
denominator.

## Provenance, replay and isolation

The response sidecar embeds all four private VDKs, 104 native lesson traces,
160 response/rejection records, the exact protocol and implementation, and a
40-file manifest. The evaluation stores 128 grades and binds the exact
response receipt and file bytes. Validation rejects stale or foreign inputs,
swapped roles, changed case order/group/pair/type, missing/duplicated records,
changed original/effective requests, routes, mappings, instruction refs,
nested rules, successor steps, partial evidence, lessons, checkpoints,
fingerprints, grades, denominators, code or authority claims—even after outer
hashes are recomputed.

Four private role objects remain distinct and read-only during responses. The
unexposed source, canonical state, old math artifacts, simulation ledgers,
Attention records, governance records and revisions do not change. The runner
allocates no Attention, reserves no simulation budget, records no governance
outcome and grants no canonical authority. Local hashes and replay establish
consistency only under the trusted code/filesystem boundary; they do not
authenticate the declared teacher, establish mathematical truth, prove
historical freeze timing or supply independent replication.

Immutable identities:

- v0.60 protocol declaration SHA-256:
  `1f92621d9572c5068babc6d880d239100f4847c511ead8bb10f8d2ffaa4beba8`
- v0.60 protocol file SHA-256:
  `09c6d2e0c914aa8fb8f256d59cf6ba81bfda87345413b68817bb6515dec39407`
- v0.61 implementation receipt SHA-256:
  `96820d6281822859ece17fc29e335ec1f543d6702f5a6ff80bc49b7d925c305a`
- v0.61 implementation file SHA-256:
  `05e8878f7a87c8be748e00c25608688f7ec87ab9345cc17e5caf24666699e64f`
- v0.62 response receipt SHA-256:
  `eb29e9b3a80d246bd23bd7e80408678642d7fdd99ed16ced896f0c056b2019db`
- v0.62 response file SHA-256:
  `25f75c01332bff48e46c521eb966f9c8634620542aa6e2126236d378126f70e4`
  (`1,308,964` bytes)
- v0.62 evaluation receipt SHA-256:
  `be49243269d65bbe0673c4e57402a20660a3817b0de6b657674d00f439323acd`
- v0.62 evaluation file SHA-256:
  `2ec22c550b17e1f7a3ca91df21ba06ab8dc7d1d11f8d70e3e2117d8c7f419bd1`
  (`36,282` bytes)

All 126 new evaluation tests, 677 focused math/archive tests and 1,401
full-suite tests pass. The full suite includes the existing load/embed checks
for all seventeen legacy checkpoints. Checkpoint formats and behavior were not
changed.

## Exact claim boundary and next dependency

**OBSERVED:** The frozen teacher-scaffolded cohort produced the complete table
above. Correct versus no-instruction differs by eight predeclared swap cases;
exact null matches. Both-mapping and terminal-link failures remain visible.
The stronger reading that an operand-order instruction repairs addition
generally is falsified within this cohort: it leaves 16/32 valid inputs
unanswered. No completed negative result or control was tuned after execution.

**IMPLEMENTED-EXPERIMENTAL:** One explicitly invoked prospective evaluator,
separate immutable ungraded response batch, post-barrier unchanged external
grading, exact saved-byte result pairing, static zero-response/zero-grade
replay, four private copies, complete native lineage and fail-closed
publication. This characterizes only the frozen supplied software scaffold.

**PROPOSED:** Freeze one later **protocol-only** terminal-successor repair study
grounded in the eight retained `missing_successor` traces. Because the existing
native number/step types stop at 18, first declare a versioned bounded domain
extension and exact teacher testimony needed through 21, plus no-repair,
wrong-link and exact-null controls and fresh disjoint cases. Do not implement
or execute that repair in this increment, and do not use evaluator answers as
teacher data.

**MISSING:** Spontaneous commutativity or rule discovery, generalized
arithmetic, mathematical understanding, source authentication, independent
replication, causal self-repair and evidence that later learning becomes
cheaper remain unestablished. No canonical installation, resolution,
promotion, autonomous policy rewrite or broader curriculum is authorized. The
physical PredictionFailure study remains blocked: v0.53 is unexecuted,
v0.54/v0.55 remain quarantined, calibrated physical prediction, causal repair,
source independence and independent held-out replication remain the four
mandatory missing N requirements, and the v0.45 Contradiction negative result
is unchanged.
