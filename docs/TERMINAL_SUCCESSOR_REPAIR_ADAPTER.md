# Private terminal-successor repair adapter v0.64

This increment implements the private-copy adapter and native trace verifier
required by the frozen v0.63 protocol. It does **not** execute any of that
protocol's forty prospective cases, produce a grade, or create an evaluation.
Behavioral tests use only already-consumed cases and recorded probes.

## Exact private teaching boundary

`prepare_private_successor_repair_kernel` accepts only the exact fresh v0.63
source and always creates a distinct private copy. Every role receives the same
twenty-five correct v0.58 lessons and the same correct v0.61 operand-order
instruction. Only the final three terminal-successor slots differ:

| Role | Private terminal slots |
|---|---|
| `taught_repair` | `18→19`, `19→20`, `20→21` |
| `valid_null` | A distinct copy with the exact same three claims |
| `no_repair_control` | Three prompt records with no successor claims |
| `wrong_link_control` | `18→20`, `19→21`, `20→18` |

Each supplied claim is affirmed `HUMAN_TESTIMONY` with native evidence. Prompt
slots retain evidence without fabricating claims. The declared source label is
not teacher authentication. Explicit preparation mutates only the new private
copy; the source, canonical state, simulation ledgers, Attention, governance
and revision authority remain unchanged. Freezing or reloading the
implementation sidecar invokes no preparation at all.

## Versioned 0–21 native execution

The old v0.57/v0.58 request, answer and step types end at 18 and remain
byte-unchanged. The new sibling supplies strict equivalents bounded to 0–21:

- `BoundedCountingRequestV064`, `BoundedCountingStepV064` and
  `BoundedCountingReplyV064`;
- `BoundedAdditionRequestV064` and `BoundedAdditionReplyV064`; and
- `SuccessorRepairReplyV064`, with separate original and effective requests.

The interpreter still reads the existing native counting and addition rules,
the native right-operand token mapping and the v0.61 order instruction. A valid
right mapping keeps the original order. Only a genuinely missing right mapping
plus a valid left mapping authorizes one transposition. Conflicting, invalid or
unsupported evidence blocks routing and remains visible. No path sorts,
recurses, reconstructs tokens from integers or consults an arithmetic grader.

The bounded walker reads each `math_successor` claim. Every accepted step stores
its claim and complete evidence closure. A missing or blocked edge retains the
entire partial walk and blocking references without answer credit. Targets
outside 0–21 are invalid. Cycles remain abstentions. No successor is installed
for 21, so a future walk with tokens remaining at 21 must retain a genuinely
missing lookup; the implementation cannot silently widen its domain.

`verify_successor_repair_derivation` checks the private-kernel fingerprint,
replays the bounded count and addition, reconstructs the one-shot order route,
and compares the entire typed reply. This is exact local replay under the
trusted code/filesystem boundary, not source authentication or independent
verification.

## Consumed-record implementation checks

The eight v0.62 terminal cases were already answered and externally graded
before v0.63. Reusing them here tests implementation behavior without consuming
the frozen prospective cohort:

| Private role | Result on the consumed terminal cases |
|---|---|
| Correct / exact null | Follows supplied links and reaches the already-recorded 20 or 21 target |
| No repair | Reproduces the saved missing-at-18 abstention and old partial steps |
| Wrong links | Follows fixed wrong claims until its `20→18` cycle forces abstention |

For example, the consumed `18 + 3` trace follows `18→19→20→21` in the correct
private implementation. The no-repair copy retains a missing successor at 18.
The wrong-link copy records `18→20`, then rejects the cyclic `20→18` edge. No
new expected answer or grade is supplied to any response path.

Adversarial checks cover missing, conflicting, invalid and unsupported order,
mapping and successor testimony; out-of-domain targets; fixed wrong-link cycles;
changed requests, routes, fingerprints, decoded mappings, nested rules, steps,
claims and evidence; foreign private copies; prospective-table and evaluator
access; stale or substituted protocols; code/source drift; rehashed authority
claims; partial publication; and attempts to replace protected historical
evidence. They establish an implementation contract, not arithmetic truth or
transfer.

## Immutable implementation pairing

The separate immutable implementation receipt is
[`implementation.vsri`](../artifacts/terminal_successor_v064/implementation.vsri).
It embeds the exact unanswered v0.63 `.vsrp` and extends its 43-file manifest
with only the three `successor_repair_adapter` sibling sources, for 46 files.

- v0.63 protocol declaration SHA-256:
  `b680c4b5eb50abd80b422df2cdf1ba8504af08045f9e1b7d52a99e68a8cfa98a`
- v0.63 protocol file SHA-256:
  `ee8f37cb145704fbb9ff753a5416b2ba473d276c96813a194465ca5960883081`
- v0.64 implementation receipt SHA-256:
  `19e0363f65400308d49455b887ffb33dcdf7a3e0bbce93bc3bb0eadc320160c2`
- v0.64 implementation file SHA-256:
  `397231910c27b8a429551e326fc11f880d3522466438de09a57534825be9d83d`
- File size: `48,633` bytes

Freeze and replay require the exact protocol and current sibling code. They do
not teach, answer, grade, allocate Attention or simulate. The CLI intentionally
exposes no `run`, `query` or `evaluate` command.

```bash
python -m verdant_math.successor_repair_adapter.cli freeze \
  artifacts/terminal_successor_v063/protocol.vsrp \
  artifacts/terminal_successor_v064/implementation.vsri
python -m verdant_math.successor_repair_adapter.cli replay \
  artifacts/terminal_successor_v063/protocol.vsrp \
  artifacts/terminal_successor_v064/implementation.vsri
```

## Exact claim boundary

**OBSERVED:** The adapter, installer and verifier pass consumed-record,
provenance, adversarial, isolation and replay checks. Correct/null copies follow
the supplied links; no-repair and wrong-link copies preserve their native
failures. All forty v0.63 cases remain unanswered and ungraded. These are
implementation observations, not prospective learning results. All 120 new
adapter tests, 920 focused math/archive tests and 1,644 full-suite tests pass,
including the existing checks of all seventeen legacy checkpoints.

**IMPLEMENTED-EXPERIMENTAL:** One explicitly invoked private-copy installer,
strict 0–21 order/addition/counting sibling, complete native trace, exact trace
verifier, freeze/replay-only CLI and separately immutable `.vsri` paired to the
exact v0.63 protocol. Old modules, manifests and artifacts remain unchanged.

**PROPOSED:** A later, separate evaluation may execute the four frozen roles,
save all 160 response/rejection records before grading, then externally grade
the 128 valid original requests. It must retain all invalids and abstentions,
require exact complete taught/null equality, and bind exact `.vsrp` and `.vsri`
bytes without post-result tuning.

**MISSING:** No prospective repair effect, causal self-repair, spontaneous rule
discovery, generalized arithmetic, mathematical understanding, authenticated
teaching, independent replication or cheaper later learning is established.
No canonical installation, Resolution, promotion or autonomous policy rewrite
is authorized. The physical PredictionFailure study remains blocked: v0.53 is
unexecuted, v0.54/v0.55 remain quarantined, the four mandatory N requirements
remain missing, and the v0.45 Contradiction negative result is unchanged.
