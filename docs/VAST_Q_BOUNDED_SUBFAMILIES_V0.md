# Q bounded subfamily discovery v0.4

**Isolated research branch:** test/vast-q-bounded-subfamilies-v0, forked from the tested Auto-PQ v0.3 implementation. The old 3-section, 12-P/2-Q experiment remains immutable.

## Empirical motivation

The operator curriculum showed 4, 8 and 12 promoted P structures after sections 1, 2 and 3, with Q counts 1, 2, 2. Section 3 recorded 32 verified alignments from four newly promoted Ps, but zero Q observation events. The source code explains why: the hierarchy observer converts all historically verified P-to-P alignments into a connected graph, then rejects any whole connected component larger than native policy maximum_members=8. Each source interaction was also capped to eight ranked target candidates by the unchanged interaction policy.

## Strictly bounded change

Only oversized verified-alignment components (>8 Ps) are candidates for subfamily discovery. For original components of size 3–8, all prior behavior is preserved.

The new detector uses **mutual near-best verified symbolic alignments**. Each edge must be within 0.03 of the BEST observed native symbolic score of *both endpoints*. Accepted connected subgroups must have native minimum_members <= size <= maximum_members and mean internal verified-alignment quality at least 0.03 greater than the strongest verified cross-group edge. Groups larger than 128 are not searched.

The groups are derived solely from actual native committed interaction evidence, not labels, fabricated relationships, or arbitrary P-ID chunks. Cross-group verified edges are passed as actual boundary pressure into the existing native hierarchy candidate quality algorithm along with field-only near misses. No original recurrence, pair-coverage, cohesion, evidence diversity, policy revision, Council, stale-report or authorization checks have been relaxed.

**Uniform 12-P clique => zero invented subfamilies.** Dense same-shape P associations do not distinguish subgroups, even if Q formation stalls. That is a protective negative result, not a reason to force new Q promotions.

Bounded subfamily discovery is currently DISJOINT, not a general overlapping-community solver. The 0.03 thresholds are explicitly external fixed experimental hypotheses, not self-learned Verdant executive parameters. Group nomination is not hierarchy eligibility, Council permission or demonstrated utility.

## Durable diagnostics and lineage

The Q scheduler saves read-only oversized-component diagnostics into the immutable per-section receipt: size, suggested subgroup member counts, and whether no defensible split was found.

The read-only module verdant_integrated.q_subfamily_audit reads older native VDK checkpoints directly and prints their actual observed components, pair strengths, candidate subgroup IDs and unresolved oversized status. It does not mutate checkpoint, kernel semantics, or user data. The source manifest now freezes the native hierarchy and interaction pipelines, plus the new auditor, to prevent source drift while resuming new cohorts.

Never use v0.4 code to resume source-frozen v0.3 output directories or alter V5/V5-X, active Obligation Substrate or the original 200-experience baseline.

## Validation and outstanding questions

Adversarial graph controls cover native-size legacy preservation (4/8), discriminable 12-P components (three sets of 4 or two sets of 6), indiscriminate 12-P cliques and near ties, graph traversal order, zero evidence, bounded 128-member abort and outgoing bridge pressure. Existing native hierarchy, P/Q promotion and full heartbeat curriculum tests remain part of the focused CI.

These adversarial subfamily tests use controlled graph evidence; do not count them as actual observed Q promotion on the operator curriculum. The source matcher measures normalized plastic association topology, NOT canonical relation-type/direction semantics. A uniform 12-P clique may still require a *separate* semantically discriminating or weighted topology experiment, and actual P/Q usefulness requires held-out reconstruction or ablation controls.

**Next step:** run the read-only audit on the existing operator Section-3 VDK. If justified subfamilies exist, run one fresh v0.4 curriculum section and then an independent three-section cohort. If the audit finds a homogeneous 12-P clique, do not waste a long rerun to manufacture more Q; pursue a falsifiable comparator/utility test next. See VAST_Q_SUBFAMILIES_WINDOWS.md.

All automatic P and Q promotion still requires native eligibility and actual Council authorization; no direct semantic writes, no obligation inquiry, no source-independent Q proof, and no learning-grade claim.
