# Private teacher-scaffolded operand-order adapter v0.61

This increment implements the adapter and native trace verifier required by
the frozen v0.60 protocol. It does **not** execute any of that protocol's forty
prospective cases, produce a grade, or create an evaluation. Tests exercise
only previously consumed cohort inputs and recorded probes.

## Explicit private teaching

`prepare_private_operand_order_kernel` accepts only the exact fresh v0.60
source and always constructs a distinct private copy. Every role receives the
same twenty-five correct v0.58 lessons: eighteen successor facts, the counting
instruction, five operand-token mappings and the addition instruction. The
twenty-sixth slot is the only role difference:

| Role | Private order slot |
|---|---|
| Taught | `math:rule:swap_only_for_missing_right_mapping` |
| No instruction | Prompt evidence with no order claim |
| Exact valid null | The same correct instruction as taught |
| Incorrect instruction | `math:rule:swap_only_for_found_right_mapping` |

The native subject is `math:procedure:addition_operand_order`, the predicate is
`math_uses_operand_order_rule`, and valid authority requires one affirmed,
unopposed `HUMAN_TESTIMONY` claim with complete evidence. The declared source
label remains `declared-operand-order-teacher://v060`; this label does not
authenticate a teacher. Installation never mutates the supplied source and
grants no canonical, Attention, simulation, governance or rewrite authority.

## Read-only routing and provenance

`derive_ordered_addition` validates the original request, snapshots the private
kernel fingerprint, and records the native order instruction and original-right
mapping lookup before routing.

For the correct supplied instruction:

1. A valid decoded original-right mapping keeps the original order.
2. Only a genuinely missing original-right mapping permits a native lookup of
   the original left operand.
3. A valid decoded original-left mapping authorizes exactly one transposition.
4. Conflicting, invalid or unsupported original-right evidence blocks routing.
   Missing, conflicting, invalid or unsupported original-left evidence retains
   both lookups and blocks routing.

The no-instruction role delegates the unchanged original-order request to the
v0.58 addition interpreter. The incorrect control follows its separately
frozen opposite trigger: valid original-right mapping swaps once, while missing
original-right mapping keeps order. It deliberately does not precheck the left
mapping; the unchanged addition interpreter retains any resulting failure.

Every dispatched trace contains separate original and effective requests, a
local run and case reference, private-kernel fingerprint, complete order claim
and evidence closure, original mapping lookups, route disposition, and the
unchanged nested `AdditionReply`. That reply retains its addition rule, mapping,
full successor walk and any partial or blocking evidence. Blocked routing has
no effective request or fabricated nested reply. No path sorts operands,
retries recursively, reconstructs tokens from an integer, consults a case
label, or performs evaluator arithmetic.

`verify_order_derivation` first checks that the trace belongs to the presented
private kernel, replays the unchanged addition derivation when present, then
reconstructs the entire routing decision and compares every typed field. It is
a local replay guarantee under the trusted code/filesystem boundary, not
source authentication or independent verification.

## Consumed-case implementation checks

The adapter tests use only inputs already consumed or recorded before v0.60.
They do not measure new learning performance:

| Existing input | Correct-rule route | Native result |
|---|---|---|
| `9 + 3` | Keep original; right mapping is valid | `12` |
| `3 + 9` | Swap once; right is missing and left is valid | `12` |
| `13 + 1` | Keep original | `14` |
| `1 + 13` | Swap once | `14` |
| `6 + 6` | Block; both mappings are missing | Abstain |
| `16 + 3` | Keep original; successor path stops at `18` | Abstain with `16→17→18` retained |

With no order instruction, `1 + 13` retains the old original-order missing-
mapping abstention. With the incorrect instruction, `9 + 3` transposes and the
old interpreter exposes its missing effective mapping. Deliberately altered
native token testimony changes the walk rather than being numerically repaired.

Adversarial checks cover conflicting and negated instruction claims; invalid
source classes; unsupported labels; missing, conflicting, invalid and
unsupported mappings on both operands; foreign private kernels; changed routes,
requests, decoded tokens, native references and nested successor steps; and
fully rehashed protocol, code, authority and result substitutions. These checks
establish the implementation contract, not arithmetic truth or transfer.

All 104 adapter tests, 551 focused math/archive tests and 1,275 full-suite tests
pass. The full suite includes the existing load/embed checks for all seventeen
legacy checkpoints. Checkpoint behavior and formats were not changed.

## Immutable implementation pairing

The separate immutable implementation receipt is
[`implementation.vaoi`](../artifacts/operand_order_v061/implementation.vaoi).
It embeds the exact unanswered v0.60 protocol and extends its 34-file manifest
with only the three versioned sibling source files, for 37 files total.

- v0.60 protocol declaration SHA-256:
  `1f92621d9572c5068babc6d880d239100f4847c511ead8bb10f8d2ffaa4beba8`
- v0.60 protocol file SHA-256:
  `09c6d2e0c914aa8fb8f256d59cf6ba81bfda87345413b68817bb6515dec39407`
- v0.61 implementation receipt SHA-256:
  `96820d6281822859ece17fc29e335ec1f543d6702f5a6ff80bc49b7d925c305a`
- v0.61 implementation file SHA-256:
  `05e8878f7a87c8be748e00c25608688f7ec87ab9345cc17e5caf24666699e64f`
- File size: `37,694` bytes

Freeze and replay accept only the exact protocol and current implementation
bytes. They call no teaching, response, grader, Attention or simulation entry
point. The CLI intentionally exposes no `run`, `query` or `evaluate` command.

```bash
python -m verdant_math.ordering_adapter.cli freeze \
  artifacts/operand_order_v060/protocol.vaop \
  artifacts/operand_order_v061/implementation.vaoi
python -m verdant_math.ordering_adapter.cli replay \
  artifacts/operand_order_v060/protocol.vaop \
  artifacts/operand_order_v061/implementation.vaoi
```

## Claim boundary and next dependency

**OBSERVED:** The adapter and verifier pass their consumed-input behavioral,
native provenance, adversarial, immutability and replay checks. Earlier math
artifacts and all forty v0.60 cases remain unchanged and unanswered. These are
implementation observations, not new prospective learning results.

**IMPLEMENTED-EXPERIMENTAL:** One explicitly invoked private-copy instruction
installer, single-route operand-order adapter, complete native trace, exact
trace verifier, freeze/replay-only CLI and separately immutable `.vaoi` paired
to v0.60. The old addition/counting modules and every earlier artifact remain
byte-unchanged.

**PROPOSED:** In a later, separate increment, execute all four roles against the
exact frozen forty-case cohort, save all 160 response/rejection records before
any of 128 external grades, grade original requests with the unchanged v0.58
grader, require exact complete taught/null equality, and publish a result bound
to exact `.vaop` and `.vaoi` bytes. Do not replace missing or invalid cases.

**MISSING:** No prospective response, grade or performance result exists yet.
Generalized arithmetic, spontaneous commutativity discovery, mathematical
understanding, independent replication and learning making later learning
cheaper remain unestablished. The physical track remains blocked on verifiable
task-linked acquisition and defensible harm scoring; v0.53 is unexecuted, the
four mandatory N requirements remain missing, and the v0.45 Contradiction
negative result is unchanged.
