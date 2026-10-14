# Relational abstraction and exact typed transfer v0 — experimental specification

Branch: test/relational-abstraction-transfer-v0. Parent: test/structural-relation-lens-v0. This is an isolated **read-only** research layer. No native V5, V5-X, Council, P/Q promotion, hierarchy policy, VAST study version, semantic state, or prior checkpoint is changed.

## Measured problem

In the author's original native 60-experience study, the 12 P structures form a dense, nearly uniform undirected topology alignment graph. Existing Q artifacts hold 4 and 8 P members; their native comparisons are topological only. All 66 P pairs passed the old topology comparator and all 66 failed the experimental exact typed/directed relation lens (under a 0.90 typed F1 threshold). This is NOT 66 known wrong semantic predictions: relation names were taught and may have analogical connections not encoded by exact lexical names.

The author-supplied P records show three-concept, two-directed-relation chains containing distinct types: contains, supports, precedes, occluded_by, persists_through, etc. We need to preserve their distinctions while still recognizing a broad structural analogy.

## Three separation levels

1. **Shape recognition** is exactly the existing native topology matcher. This is not modified.
2. **Typed directional role identity** is a read-only derived equivalence key across ALL permutations of native P concept IDs. It canonically encodes each supported relation's type, directed flag and ordered (or unordered) endpoints. No concept label, P opaque name or hash is a learned category. Missing current relation provenance yields an unknown key and subsequent ABSTAIN.
3. **Q role overlays** regroup a previously Council-promoted Q's actual native member Ps by those derived typed-role keys. A heterogeneous Q can contain several subgroups; the subgroup is an interpretation, not a new Q, invented truth, Council decision or autonomous role ontology.

The overlay is EXACT only for typed-role F1 **1.0**. Equality of canonical role keys is a necessary, not sufficient condition for a match. All potential positives go through the existing RelationAwareLens, which also verifies actual native plastic topology on the SAME mapping and checks typed direction and relation roles. The overlay never unilaterally declares a match.

If either role key is absent, perform actual lens inspection and preserve ABSTAIN rather than promoting unknowns. If keys disagree, rejecting is sound at threshold 1.0. Never generalize key inequality to softer F1 thresholds: the proof would fail. No alias/synonym equivalence is implied by a different relation string.

## Matched controls on one genuine native kernel

The synthetic pytest experiment teaches three genuinely promoted native P "support forks", forms one genuine Council-promoted Q from those Ps, then introduces disjoint-label held-out Ps **after** Q promotion:
- renamed support fork: positive
- same association topology but type changed supports -> precedes: negative
- same type but both directed edges reversed: negative
- P lacking supported member-relation references: ABSTAIN

A second test genuinely earns a Q from three heterogeneous types (supports/precedes/contains) and verifies its read-only overlay presents three separate typed role groups without declaring types synonymous. A further test clones the kernel, ablates Q in the clone and verifies **retrieval correctness remains exactly identical** while Q-group index comparisons revert to P-only behavior.

## Fair comparison arms

- Exhaustive typed P: run RelationAwareLens on each available P and preserve ALL accept/reject/abstain decisions. This is the accuracy reference; it is not independent sensor truth.
- Keyed P-only: compare one canonical typed-role key per P, then full same-mapping RelationAwareLens for any possible match or unknown evidence. It is a crucial **indexing ablation control**—not all speedup can be credited to Q.
- Promoted-Q role overlay: compare one key per typed subgroup within each AVAILABLE native Q, then validate EVERY potentially matching P member with full lens. Each native P belongs to at most one grouped overlay even when Qs overlap; outside-Q Ps also undergo the fair keyed P-only comparison.

All three arms MUST yield identical per-P verdicts. If they do not, fail closed. Grouping can reduce **key comparisons per lookup after index construction** but cannot legitimately promise reduced exact verifications relative to the P-only keyed baseline, since those verifications remain necessary for correctness.

The Q overlay's key construction in this proof of concept is rebuilt on EVERY audit call. It is NOT a cached production index. Construction enumerates up to native maximum_exact_members factorial role permutations and can cost far more than simple key comparisons. It is excluded from lookup-only counts, explicitly labeled; no measured end-to-end speed advantage can be inferred.

Reported work proxies include number of full RelationAwareLens invocations, underlying role mapping permutations, per-P or Q-group hash-equivalence key checks and the number of rebuilt construction keys. Baseline shadow evaluations are explicitly separate from runtime. No execution time, learning accuracy, overall CPU/memory resource use or independent grounded correctness claims are made.

## Controls and invariants

- No native Council reauthorization by sidecar; original Q lineage and native checkpoint fingerprint checked unchanged.
- No P/Q promotions, canonical relation rewrites, semantic status updates, simulator side effects or autonomic obligations triggered.
- Mixed-type Q members do not become synonyms or interchangeable operations through mere structural connectivity.
- Query matching checks availability and uses only native committed P member relation refs with valid current evidence; original relation records are not frozen at P promotion and are read from CURRENT checkpoint.
- Alias-aware role comparison, polarity claims, transitivity of approximate matches, certified dynamic persistent indexing and learned equivalence are **out of scope**.
- The original 12-P source checkpoint remains a held-out retrospective audit and no user curriculum seed study runs on push.

## Evidence before claiming improvement

Run the focused 6-file suite on GitHub Actions (synthetic kernels only). The read-only CLI accepts the original Section-3 VDK and compares all 12 native Ps with original Q overlays without rerunning teaching. The old Qs may have been promoted AFTER a particular queried P; this retrospective report does NOT satisfy prospective temporal isolation. It also may show no role-subgroup compression if each P is type-unique; that is a valid negative result.

Only after further matched empirical gains and independently verified held-out transfer should this evidence be considered for an opt-in Q nomination change with original Council gates. Do not quietly change native P/Q behavior on this branch.
