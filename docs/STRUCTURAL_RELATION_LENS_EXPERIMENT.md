# Structural relation discrimination experiment v0.1

Branch: test/structural-relation-lens-v0, forked from tested bounded Q subfamilies v0.4. Existing V5, V5-X, P/Q development runner, governance and operator native VDK checkpoints remain untouched.

## Motivation

The three-section study produced 12 promoted Ps and 2 Qs. The read-only audit found a 12-P connected graph with 57/66 verified pairs and mean symbolic similarity 0.993505; a bounded Q detector properly abstained from arbitrarily splitting it. The native P-to-P comparator matches normalized undirected plastic association topology, not typed and directed canonical relations.

## Matched comparison

CONTROL: VerdantStructureInteractionPipeline._symbolic_alignment, retained byte-for-byte without modification.

TREATMENT: experimental read-only RelationAwareLens.inspect on pairs of previously Council-promoted P structures:
1. Resolve the P's native member_relation_ids into the CURRENT canonical relation records, including relation type, direction, status, endpoints and evidence refs. Both sides need usable provenance; otherwise ABSTAIN.
2. Examine the native-permitted exact concept-role mappings, enforcing the original topology score >= native policy minimum on the **same mapping** used for typed/directed relation-role F1.
3. ACCEPT only when such a mapping also reaches an externally fixed typed F1 threshold of 0.90. Otherwise REJECT. If one P lacks relation provenance, do not guess: ABSTAIN.
4. Directed roles are ordered endpoints; undirected endpoints are unordered. Relation names are compared as literal canonical strings; the lens does NOT invent synonyms, inferred equivalences, causes, or physical truth.
5. Return one read-only record containing baseline topology score/acceptance and typed F1/verdict. The lens does not mutate P/Q, Council, native interaction events or canonical semantics.

The same-mapping rule matters: a role permutation that preserves plastic topology cannot be swapped for a different permutation to make a contradictory typed edge appear correct.

## Controlled native experiments

Experiences are author-supplied synthetic testimony; all P and Q structure formation/promotion uses the actual Verdant native developmental and Council paths.

- Positive renamed-isomorphic outward 3-node support-fork vs another same-type outward support-fork.
- Positive **novel P** taught after a Council-promoted Q exists, disjoint renamed concepts, same relations and orientation.
- Negative type: identical graph and direction, but supports changed to precedes.
- Negative direction: identical graph and relation type but a 2-outgoing fork changed to a 2-incoming fork.
- Missing provenance: P without native member relation refs; ABSTAIN.
- Q efficiency: compare the native Q-enabled layered probe with a Q-ablation control on an independent cloned state; use native comparison_work counts, not wall-clock CPU.

Native Q is STILL topology-only and may falsely group typed-negative examples. The sidecar demonstrates what distinctions the existing native mechanism lacks; it does not install a new learned Q policy or alter training.

## Existing operator checkpoint audit

Run python -m verdant_integrated.structural_lens_audit FILE.vdk --max-pairs 66.

The read-only audit reports topology vs typed-direction pair counts, refusal/abstention rates, provenance counts and retrospective native Q comparison work for Ps created after earlier Qs. It verifies unchanged source checkpoint bytes and kernel fingerprint. No experiment restarts, automatic promotion or user file edits.

WARNING: Saved-checkpoint Q cost is a retrospective full-state estimate; future structures/other Qs may be present by the time of audit. It is neither time-isolated prospective evaluation nor a timing benchmark. No supervised held-out accuracy is measured on the user's unlabeled checkpoint. Synthetic expected labels are experimenter-assigned and cannot prove real-world semantic intelligence.

Native member relation IDs are promotion-time frozen, while the current canonical relation records can later change; this sidecar audits the checkpoint-current ledger, not an independently verified historical source.

## Exclusions

No changes to native V5/V5-X, default P/Q quality thresholds, canonical hierarchy candidate creation, Council permissions, role semantics, obligations, source-frozen VAST curriculum runner, or original checkpoints. No generalization claims from counts alone. No long 600-experience seed run. Running the fixed external lens is NOT endogenous cognitive policy learning.

Next separate, permissioned research increment only after evidence: a new source-frozen arm optionally using typed/directed evidence for **nomination** while preserving original P/Q quality and Council gates. Do not conflate this read-only study with such an integration.
