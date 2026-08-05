# Verdant Publication Evidence Program

## Master plan for freezing, testing, documenting, and submitting the current architecture

**Document version:** 1.0  
**Prepared for:** William Adams, Verdant-Minds  
**Date:** August 4, 2026  
**Status:** Governing plan for the first publication campaign

---

## 1. Decision and purpose

Verdant has reached the point where the next major deliverable should be evidence, not another cognitive mechanism. The current system can earn promoted P structures, form a higher-order Q from repeated verified P interactions, use Q during later structural-family probes, and record exact ablation and restoration controls. The immediate goal is to determine how reliably, selectively, causally, and reproducibly those behaviors occur.

This document is the source of truth for that work. It exists to prevent test design, code changes, analysis, and paper writing from becoming mixed together. No major cognitive architecture will be added until this program reaches its publication decision gate.

### Governing decision

1. Freeze the current architecture as **Verdant Publication Candidate 1 (VPC-1)**.
2. Permit only measurement code, documentation, portability fixes, and correctness fixes during the campaign.
3. Separate exploratory development data from a sealed final test set.
4. Record every failure and protocol deviation.
5. Complete the evidence package before deciding how broadly the paper may claim success.
6. Resume major architecture work only after the paper package or an explicit negative-results report is complete.

### Candidate freeze point

- **Repository:** Verdant-Minds
- **Current evaluator commit:** `d3c147e` (`Add repeated Q evaluation campaign`)
- **Proposed tag:** `verdant-publication-candidate-v1`
- **Frozen primary Q threshold:** `0.985`

The tag is created only after the branch is synchronized and the full preflight suite passes. If a correctness fix changes cognitive behavior, VPC-1 is retired and a new candidate tag is created. Results from different candidates must never be pooled silently.

---

## 2. What the first paper will and will not claim

### Primary claim

Under controlled relational curricula, Verdant can earn opaque reusable P structures from primitive experience, earn higher-order Q structures from repeated verified interactions among P structures, selectively reuse the appropriate Q on later held-out P structures, and show a causally attributable reduction in comparison work without installing the evaluator's family labels as semantic truth.

### Supporting claims

- P and Q formation are recorded, governed, inspectable, and replayable.
- Q use can be removed by ablating the exact earned Q and recovered by restoring it.
- Symbolic verification prevents a continuous field match from becoming structural acceptance by itself.
- Q-based comparison work scales more slowly than an exhaustive available-P scan over the tested range.
- Several Q structures can coexist and route later structures to the correct earned family.
- Checkpoint, replay, and event-lineage records preserve the tested result across supported environments.

### Explicit nonclaims

The paper will not claim that Verdant is conscious, sentient, generally intelligent, human-equivalent, a complete embodied agent, a language model replacement, or superior to optimized graph-isomorphism software. It will not call ordinary prediction intelligence. Its subject is the formation, retention, selection, manipulation, and causal use of earned cognitive structures.

The benchmark's external family names are scoring labels only. They must never be presented as concepts Verdant was taught or as semantic theories Verdant independently verbalized.

---

## 3. Evidence already available

The present evidence justifies the larger campaign but is not the final publication dataset.

### Historical First-Q case study

- The supplied First-Q archive passed a recorded Q present -> ablated -> restored comparison.
- Comparison work changed `3 -> 4 -> 3`.
- The same family remained matched and Q was available afterward.
- The query was a member of the original Q because the archive contained no fourth held-out P. It is therefore a case study, not held-out transfer evidence.

### Controlled Q evaluation, August 4, 2026

- Q selected the exact trained family on 16 of 18 difficult held-out path cases at the frozen `0.985` gate.
- All 18 unrelated star, cycle, and paw controls were rejected by Q.
- The two Q misses were safe fallback outcomes: the full scan still found the correct family.
- Two complete four-arm benchmark runs passed 30 of 30 declared checks.
- In a one-seed scaling assay, Q work remained 3 while the audit baseline grew `6 -> 14 -> 22` as unrelated P structures increased from 0 to 4 to 8.
- The two strongest weighted-path misses reproduced exactly.
- A `0.980` gate separated all cases in the exploratory sweep, but this is not permission to retune the locked primary test.

### Why this is not enough by itself

The controlled dataset is small, uses one learned Q family, has limited topological diversity, and contains only one scaling seed. The threshold sweep was observed after the first campaign. Publication evidence must include multiple simultaneous Q structures, larger predeclared case coverage, clustered statistical analysis, cross-platform reproduction, and an independently runnable artifact.

---

## 4. Research questions

The paper will answer the following questions in order.

1. **RQ1 - Formation:** Does Verdant consistently promote P and Q through its normal evidence and governance paths without receiving the evaluator's family label?
2. **RQ2 - Held-out transfer:** Does a Q formed before a query exists recognize later P structures from the same relational family?
3. **RQ3 - Selectivity:** Does the Q reject close but structurally different controls?
4. **RQ4 - Multi-Q routing:** When several Q structures coexist, does Verdant select the correct Q rather than the first or most broadly similar Q?
5. **RQ5 - Causal utility:** Does exact-object ablation remove the measured gain while preserving the underlying information, and does restoration reproduce the gain?
6. **RQ6 - Scaling:** How does Q comparison work change as unrelated P and Q populations grow?
7. **RQ7 - Robustness:** What happens under unequal edge strength, missing evidence, distractors, context shifts, and bounded corruption?
8. **RQ8 - Persistence:** Do checkpoint, reopen, fork, and replay preserve discrete outcomes and lineage across Windows and Linux?
9. **RQ9 - Refolding:** When evidence challenges a frozen dependency, does Verdant preserve parent history and produce governed lineage without silently rewriting the original?

RQ1-RQ6 form the main paper. RQ7-RQ9 support the robustness and systems sections and may move to appendices if space is limited.

---

## 5. Experimental separation and leakage controls

### Three data partitions

**Development suite.** Existing visible cases used to debug the harness. Results may guide implementation, but may not be reported as locked confirmation.

**Validation suite.** New cases used to choose feasible ranges, runtime limits, and reporting formats. A policy value may be changed only here, before the test manifest is sealed. Every change is recorded.

**Locked test suite.** A pre-generated manifest containing seeds, families, perturbations, and expected external labels. Its hash is committed before the final run. No cognitive or analysis code changes are permitted after outcomes are opened, except a documented campaign restart under a new version.

### Required leakage controls

- Q must be promoted before any held-out or negative query structure exists.
- Every isolated query starts from the same post-Q checkpoint for that world.
- Multi-Q worlds promote every training Q before creating test queries.
- Family names and expected answers exist only in the evaluator.
- Event payloads may contain primitive edges and evidence metadata, but never the hidden family label.
- Analysis code is frozen and tested on synthetic dummy data before locked results are read.
- Raw records are append-only. Corrections create a new version and deviation entry.

---

## 6. Test matrix

### 6.1 Supported structural families

The feasibility pilot will attempt eight label-independent families within Verdant's supported exact-member range:

1. Paths
2. Cycles
3. Stars
4. Balanced trees
5. Forked trees
6. Diamonds
7. Ladders
8. Hub-with-tail structures

Instances will vary labels, member count from 4 through 8 where supported, frozen edge strengths, presentation order, and context identifiers. A family that cannot be formed through public Verdant pipelines may be removed during validation with a written reason. It cannot be replaced after the locked manifest is sealed.

### 6.2 Single-Q confirmatory campaign

For each of 30 deterministic initialization seeds and each feasible family:

- Form a Q from at least three independently earned P examples.
- Create three held-out positive P instances only after Q promotion.
- Create three hard negative P controls matched as closely as possible on member count, density, or field similarity.
- Probe each positive with Q present, the exact Q ablated, and the exact Q restored.
- Probe each negative with Q present and record retrieval and symbolic-verification stages.

With all eight families, this produces 720 held-out positives and 720 hard negatives before the causal repetitions are counted. Seeds are deterministic initialization conditions, not independent samples drawn from a human population.

### 6.3 Multi-Q confirmatory campaign

For each of 30 seeds:

- Earn four distinct Q families in the same kernel.
- Present two held-out positives per Q and two family-specific hard negatives per Q.
- Record every ranked Q candidate, selected Q, field score, symbolic score, work cost, and fallback result.
- Randomize training and query order from the sealed manifest.
- Repeat a smaller stress assay with eight coexisting Q structures on 10 seeds.

The principal multi-Q endpoint is correct top-1 Q routing. Secondary endpoints are false activation, fallback correctness, and comparison work.

### 6.4 Causal controls

Every selected positive must support this sequence:

1. Q available: correct Q selected and work recorded.
2. Exact Q ablated: Q selection disappears; the underlying P records remain.
3. Exact Q restored: Q selection and work return.
4. Unrelated Q ablated: the original correct-Q result remains unchanged.
5. Query P ablated: the system refuses or records the unavailable operand rather than silently substituting it.

P reconstruction receives an equivalent P present -> ablated -> restored control. Random or untrained Q records are never injected into canonical state; negative controls must use valid earned objects or evaluator-side comparisons.

### 6.5 Robustness conditions

The validation suite defines bounded levels before locking:

- Balanced and unequal edge strengths
- One missing primitive observation
- One contradictory or weakened edge
- Context identifier shifts
- Presentation-order permutation
- Unrelated concept and P distractors
- Near-isomorphic negative structures
- Checkpoint/reopen before query
- Fork from an older checkpoint before query

Each condition must preserve an unperturbed control from the same post-training snapshot.

### 6.6 Scaling assay

Measure at P distractor counts `0, 4, 8, 16, 32, 64` and Q population counts `1, 2, 4, 8` where runtime permits. Record:

- Q prototypes compared
- Base P structures compared
- Symbolic verifications
- Total comparison work
- Audit-baseline work
- Compression gain
- Correct-Q routing
- Wall time as an engineering measure only
- Peak memory and persistent checkpoint size

Algorithmic work counts are the primary efficiency evidence. Wall time is secondary because it depends on hardware and implementation details.

### 6.7 Cross-platform and replay assay

Run the release artifact on at least:

- Windows 11 with PowerShell
- Linux with Bash

For the same manifests, require identical discrete dispositions, selected object identities where portable identity rules apply, matched-family membership, lineage, and event ordering. Numeric field values use the repository's declared portability tolerance. Byte-identical files are not required when platform math libraries legitimately differ, but every difference must be characterized.

---

## 7. Baselines and ablations

The current four-arm Ethomorphism harness remains the principal baseline:

- **A:** Canonical graph only
- **B:** Canonical graph plus ECWF
- **C:** Plastic substrate without promoted folds
- **D:** Full earned P and Q folds

All arms receive the same ordered primitive curriculum. The hidden family label remains external.

Additional comparisons:

- Exhaustive available-P scan, which is Verdant's native fallback and audit shadow path
- P disabled versus P available reconstruction
- Q disabled versus Q available family recognition
- Correct-Q ablation versus unrelated-Q ablation
- Field retrieval followed by symbolic verification, with field-only nominations reported separately
- Optional optimized graph-matching reference, explicitly described as an engineering comparator rather than a cognitive baseline

No baseline may receive more information than Verdant. If a baseline uses evaluator-known boundaries, that advantage must be stated.

---

## 8. Metrics and statistical analysis

### Primary endpoints

- Held-out correct-Q selection rate
- Multi-Q top-1 routing accuracy
- Negative-control false-Q activation rate
- Paired comparison-work reduction under Q present versus exact-Q ablated

### Secondary endpoints

- P and Q formation success
- Exact family recovery
- Fallback correctness
- Restoration reproducibility
- Compression gain
- Work-growth slope under scaling
- Refolding lineage preservation
- Cross-platform discrete-outcome agreement

### Statistical unit

The experimental unit is a seed-by-family trained world, not each probe treated as fully independent. Queries sharing a Q are clustered. Analysis will use:

- Counts and raw denominators for every rate
- Wilson 95% intervals for simple proportions
- Hierarchical bootstrap intervals resampling seed, then family/world
- Paired median and mean work differences with bootstrap intervals
- A paired nonparametric test when its assumptions are met
- Holm correction for families of secondary hypothesis tests
- Median, interquartile range, mean, and full distribution plots
- Scaling regressions with confidence bands and reported residuals

P-values, if used, supplement effect sizes and intervals; they do not replace them.

### Predeclared evidence targets

These targets control the breadth of the paper's claim. Missing one does not authorize deleting the result.

- P and Q formation succeeds in at least 95% of supported-condition worlds.
- Held-out correct-Q selection is at least 90%, with a 95% interval lower bound of at least 85%.
- Negative false-Q activation is at most 5%, with a 95% interval upper bound of at most 10%.
- Multi-Q top-1 routing is at least 90%, with a 95% interval lower bound of at least 85%.
- At least 90% of correctly selected positives pass exact-Q ablation/restoration.
- The paired work-reduction interval excludes zero.
- At maximum tested distractors, accuracy declines by no more than 5 percentage points and Q's work-growth slope is no more than 25% of fallback's slope.
- Cross-platform discrete outcomes agree in 100% of the portable reproduction subset.
- Every headline table and figure can be regenerated by one documented command.

If a performance target is missed, the claim is narrowed to the measured operating region. If artifact or data-integrity targets are missed, the publication package is not ready.

---

## 9. Failure, deviation, and tuning policy

### Failures are data

Every formation failure, false positive, false negative, timeout, exception, and platform disagreement receives a structured record containing experiment ID, candidate commit, seed, family, condition, exception or disposition, raw artifact references, and whether fallback remained correct.

### No silent exclusions

A trial may be excluded only for a predeclared infrastructure reason, such as truncated storage or verified hardware interruption. The exclusion remains in the manifest and denominator accounting, with its reason reported. Cognitive failures are never infrastructure exclusions.

### Threshold policy

The `0.985` Q threshold is primary for VPC-1. Threshold sweeps are sensitivity analysis. If validation evidence supports another threshold, it must be chosen before sealing the locked test set. Changing it afterward creates VPC-2 and requires a completely new locked run.

### Protocol deviations

Every deviation is appended to `protocol_deviations.jsonl` before results are rerun. The entry states what changed, why, who authorized it, which data are affected, and whether the campaign version must restart.

---

## 10. Reproducibility and artifact package

The publication artifact must meet the practical standard of being documented, complete, exercisable, and capable of regenerating the reported results. Current NeurIPS guidance requires a reproducibility and transparency checklist, IJCAI-ECAI 2026 requires its reproducibility checklist, and ACM-style artifact review evaluates availability, functionality, reusability, and reproduced results.

### Required repository layout

```text
publication/
  README.md
  LICENSE
  CITATION.cff
  claims/claim_registry.yaml
  protocol/protocol_v1.json
  protocol/protocol_deviations.jsonl
  manifests/development_manifest.json
  manifests/validation_manifest.json
  manifests/locked_test_manifest.json
  manifests/SHA256SUMS.txt
  environments/windows_environment.json
  environments/linux_environment.json
  runners/run_campaign.ps1
  runners/run_campaign.sh
  analysis/analyze_results.py
  analysis/generate_figures.py
  raw/README.md
  processed/results.csv
  processed/results.jsonl
  failures/failures.jsonl
  figures/
  tables/
  paper/
  reproduction/INDEPENDENT_REPRODUCTION.md
```

### One-command requirement

A new user must be able to:

1. Create the documented environment.
2. Run a small smoke reproduction in under 15 minutes.
3. Run the full campaign with one PowerShell or Bash command.
4. Regenerate every paper table and figure from raw records.
5. Verify file hashes.

### Provenance captured for every run

- Git commit and candidate tag
- Dirty-worktree status
- Operating system and Python version
- Dependency lock hash
- Verdant policy revisions
- Dataset and manifest hashes
- Seed and experiment ID
- Start and completion timestamps
- Raw result hash
- Analysis-script commit
- Pass, failure, or infrastructure-interruption status

### Independent reproduction

Before submission, at least one person who did not write the harness should follow the artifact instructions without live correction. They record setup problems, commands used, runtime, resulting hashes, and whether headline results were recovered. Author assistance is documented rather than hidden.

---

## 11. Documentation produced during testing

Testing and writing occur together, but raw scientific records remain separate from narrative interpretation.

### The evidence ledger

`claim_registry.yaml` maps every paper claim to:

- Research question
- Experiment IDs
- Primary metric
- Raw-data files
- Analysis function
- Table or figure
- Known failure cases
- Scope limitation
- Reproduction status

No sentence enters the abstract unless it has an evidence-ledger entry.

### Experiment record

Each experiment receives a short machine-readable record and a plain-English note:

- What question was tested?
- What was held constant?
- What changed?
- What outcome was expected externally?
- What did Verdant record?
- Did fallback succeed?
- What surprised us?
- Does this change a claim, protocol, or future test?

### Status board

`PUBLICATION_STATUS.md` contains only the current phase, completed gate, active experiment, next action, blockers, and last verified artifact hash. It is the first file opened at the start of every work session.

---

## 12. Execution phases and gates

### Phase 0 - Freeze and inventory

**Work:** Synchronize the branch, tag VPC-1, record policies, enumerate existing tests and artifacts, and create the publication directory.

**Done when:** The candidate checkout is clean; smoke tests pass; environment and commit hashes are recorded; architecture-change rules are in the repository.

### Phase 1 - Protocol and generator validation

**Work:** Implement family generators, hard-negative generation, manifests, schema validation, failure logging, and dummy-data analysis tests.

**Done when:** Every generator produces valid P through public pipelines; hidden labels are absent from Verdant state; analysis code passes on known dummy inputs.

### Phase 2 - Development and validation pilots

**Work:** Measure runtime, verify cases are feasible, set perturbation ranges, validate statistics, and make any final pre-lock policy decision.

**Done when:** The protocol is versioned; supported families are fixed; sample counts and resource estimates are final; no test outcome from this phase will be called confirmation.

### Phase 3 - Seal the confirmatory campaign

**Work:** Generate the locked manifest, hash it, freeze runner and analysis commits, and create a checkpoint backup.

**Done when:** Manifest and code hashes are public in the repository history before outcomes are opened.

### Phase 4 - Run single-Q, multi-Q, causal, and robustness tests

**Work:** Execute in declared order; write append-only raw records; monitor only integrity and infrastructure status.

**Done when:** Every manifest row has a success, cognitive failure, or justified infrastructure record; there are no unexplained missing rows.

### Phase 5 - Scaling, persistence, and cross-platform reproduction

**Work:** Run population scaling; checkpoint/reopen/fork/replay; repeat the portable subset on Windows and Linux.

**Done when:** Scaling tables, platform comparison, and portability deviations are complete.

### Phase 6 - Independent artifact reproduction

**Work:** Give the frozen artifact to an independent runner; collect their reproduction record; fix documentation only unless a campaign restart is warranted.

**Done when:** The runner reproduces headline outputs or all blockers are documented and resolved under version control.

### Phase 7 - Analysis and claim decision

**Work:** Run the frozen analysis; generate all tables; populate the evidence ledger; compare results with the predeclared targets.

**Done when:** Every claim is supported, narrowed, or removed; failures and sensitivity results are included; raw-to-figure hashes verify.

### Phase 8 - Manuscript and submission artifact

**Work:** Write the paper, technical appendix, reproducibility checklist, ethics/limitations statement, artifact README, and anonymized submission package if required.

**Done when:** A cold reader can understand the contribution; a technical reader can rerun it; submission-format and anonymity checks pass.

---

## 13. Paper structure

1. **Abstract:** Narrow contribution, design, principal results, and explicit scope.
2. **Introduction:** The problem of earned reusable structures and the paper's contributions.
3. **Related work:** Cognitive architectures, graph-based memory, compositional representation, program induction, continual learning, and neuro-symbolic systems.
4. **Verdant architecture:** Canonical state, evidence, plasticity, P promotion, interaction, Q promotion, governance, and lineage.
5. **Hypotheses and protocol:** RQs, partitions, leakage controls, baselines, metrics, and locked analysis.
6. **Results:** Formation, held-out transfer, selectivity, multi-Q routing, causal controls, and scaling.
7. **Robustness and persistence:** Perturbations, fallback behavior, cross-platform replay, and refolding.
8. **Discussion:** What the results demonstrate, what failed, and how this differs from a prediction-only framing.
9. **Limitations and ethics:** Synthetic tasks, evaluator boundaries, embodiment excluded, and potential misuse or overclaiming.
10. **Conclusion:** Evidence-supported contribution and next research step.
11. **Appendices:** Full matrices, policies, schemas, extra plots, deviations, and reproduction instructions.

### Figures planned before analysis

- Architecture and evidence flow from primitive experience to P to Q to probe
- Leakage-control timeline showing Q promotion before held-out creation
- Q present/ablated/restored paired work plot
- Multi-Q routing confusion matrix
- True-positive/false-positive threshold sensitivity curve
- Work versus distractor population plot
- Failure taxonomy
- Checkpoint, fork, and lineage diagram

Figures are generated from data by script. Illustrative architecture diagrams are marked as diagrams rather than experimental results.

---

## 14. Authorship, transparency, and submission rules

William Adams is responsible for the scientific claims, code release, and manuscript. AI systems may assist with coding, analysis scaffolding, editing, and document production, but they are not authors. Every generated claim, statistic, citation, and code change must be verified by the human author. The manuscript will disclose AI assistance according to the selected venue's current policy.

Before posting a preprint or submitting to a venue, recheck that venue's anonymity, dual-submission, preprint, page-limit, supplementary-material, and generative-AI rules. IJCAI-ECAI 2026, for example, permits preprints but requires an anonymized submission and places responsibility for AI-assisted content on the human authors.

The first public release should include a clear license, citation metadata, version tag, permanent artifact archive, and immutable result hashes. Do not rely on a personal webpage as the only long-term artifact location.

---

## 15. Publication decision gate

Publication becomes the next logical action when all integrity gates and enough claim gates are satisfied.

### Mandatory integrity gates

- Candidate architecture and protocol are frozen and tagged.
- Locked manifest predates confirmatory results in repository history.
- Every trial is accounted for.
- Raw data, failures, deviations, and analysis are archived.
- Headline outputs regenerate from raw data with one command.
- Windows/Linux portable subset agrees.
- Independent runner completes the reproduction procedure.
- Evidence ledger supports every abstract-level claim.
- Limitations, ethics, AI assistance, and nonclaims are explicit.

### Claim gates

- Single-Q transfer and selectivity meet or closely characterize the predeclared operating range.
- Multi-Q routing demonstrates more than one Q can be held and correctly selected.
- Exact-object ablation/restoration establishes causal utility.
- Scaling demonstrates a measured advantage over the native exhaustive fallback.
- Failures are bounded, explained, and preserve safe fallback where claimed.

### Decision outcomes

**Full research paper:** Integrity gates pass and the main causal, multi-Q, and scaling claims are supported.

**Narrow systems or workshop paper:** Integrity gates pass, but the supported operating region is narrower than planned.

**Technical report or negative-results paper:** Integrity gates pass, but a central mechanism fails under broader testing. The failure is still documented before architecture resumes.

**Not ready:** Any integrity gate fails. Fix the research process before adding architecture or writing broad claims.

---

## 16. Rules that keep the campaign from getting lost

1. Open `PUBLICATION_STATUS.md` first in every session.
2. Work on one experiment ID at a time.
3. Never change architecture and evaluation logic in the same commit.
4. Never tune on the locked test set.
5. Never overwrite raw data.
6. Never remove a failed seed or case without a recorded protocol reason.
7. Keep exploratory results labeled exploratory.
8. Generate tables and figures by script, not manual copying.
9. Tie every paper claim to the evidence ledger.
10. End each phase with a checkpoint, hash manifest, and plain-English summary.
11. If a result is confusing, inspect it before inventing a new mechanism.
12. Major architecture resumes only after the publication decision is recorded.

---

## 17. Immediate next actions

1. Push or otherwise synchronize evaluator commit `d3c147e`.
2. Create and push tag `verdant-publication-candidate-v1` after preflight verification.
3. Add `publication/`, `PUBLICATION_STATUS.md`, and the evidence-ledger skeleton.
4. Implement the manifest and experiment-result schemas.
5. Implement and test the eight family generators using public Verdant pipelines.
6. Build multi-Q isolation and routing tests before running large samples.
7. Add structured failure and protocol-deviation logging.
8. Run a small resource-estimation pilot without opening any locked-test outcomes.
9. Finalize and hash `protocol_v1.json` and the locked test manifest.
10. Begin the confirmatory campaign.

The next coding task is therefore **Phase 0: freeze, inventory, and create the publication control files**. It is not a new cognitive architecture task.

---

## 18. Publication-standard references

1. NeurIPS, **Paper Checklist Guidelines**. Requires explicit attention to reproducibility, transparency, ethics, and societal impact: https://neurips.cc/public/guides/PaperChecklist
2. IJCAI-ECAI 2026, **Main Track Call for Papers**. Includes reproducibility, anonymization, preprint, dual-submission, and generative-AI requirements: https://2026.ijcai.org/ijcai-ecai-2026-call-for-papers-main-track/
3. ACM SIGSIM PADS 2026, **Reproducibility and Artifact Evaluation**. Describes artifact availability, functionality, reusability, and reproduced-results criteria: https://sigsim.acm.org/conf/pads/2026/blog/artifact-evaluation/

These references establish process expectations. The final venue is selected after the confirmatory evidence reveals whether the strongest honest contribution is a full cognitive-architecture paper, a systems/evaluation paper, or a narrower reproducible report.
