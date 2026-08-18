# Interpreting the V5 branch

## V5 as a browsable research generation

The `V5` branch is the complete inspectable research generation for the independent rebuild, its local Workbench laboratory, and the later oracle-free correction. It is not one frozen moment: historical reports and later corrections coexist intentionally.

## Layers present in V5

1. **Independent kernel rebuild** — canonical typed state, evidence, persistence, and CognitiveChunk compatibility.
2. **Language/epistemic layer** — handwritten grammar, claims, contradiction, and revision.
3. **Field/governance layer** — ECWF resonance, Three Kings, and Council authorization.
4. **Bounded organization layer** — shards, routing, objecthood, and workspace.
5. **Native sensory layer** — exact media preservation, vision/audio translation, temporal memory, and perceptual continuity.
6. **Developmental layer** — atomic heartbeat, local plasticity, and candidate formation.
7. **Earned structure layer** — P promotion/compilation, cross-symbolic interaction, Q hierarchy, and refolding.
8. **M19 benchmark layer** — four-arm controlled comparison and causal controls.
9. **Workbench layer** — local API/UI, persistence, curricula, explorers, experiments, providers, plugins, and engineering diagnostics.
10. **Post-release development layer** — WB-11 curriculum packs, worker timeout correction, oracle-free M19 replacement, and full validation workflows.

## Milestone numbering

Milestones 1–7 are followed by Milestone 9. Milestone 8 was deliberately removed and its number was not reused. Milestones 10–19 continue from workspace through sensory, development, structure formation, hierarchy, refolding, and benchmarking.

See [milestone-index.md](milestone-index.md) for the exact package/report/artifact map.

## Historical documentation behavior

Existing reports preserve what was claimed and measured at their layer:

- individual `MILESTONE_*_REPORT.md` files describe the engine's staged construction;
- `WORKBENCH_WB*_REPORT.md` files describe the control-plane roadmap;
- `WORKBENCH_1_0_FINAL_REPORT.md` and `RELEASE_MANIFEST.json` describe the 250-test Workbench 1.0.1 release state;
- WB-11 and worker-timeout files describe later Workbench development;
- `MILESTONE_19_ORACLE_REVALIDATION.md` corrects the original M19 formation protocol and records the later 258-test validation.

The earlier documents should not be silently rewritten to make them look as if they always contained the later correction. The current status/reproducibility docs instead tell a reader which layer remains authoritative for each claim.

## Major discontinuity from earlier Verdant generations

V5 is an independent clean-room rebuild, not an incremental packaging of the older V2/V3/V4 graph-growth stack. The V5 branch removed the previous `ethomorphic`, `cultivation`, `analysis`, Colab, and V2 test trees and replaced them with:

- one canonical `KernelState`;
- explicit typed evidence and semantic gates;
- inspect/validate/commit boundaries;
- deterministic checkpointing and lineage;
- native sensory/perceptual records;
- bounded local plasticity;
- opaque earned P/Q structure records;
- causal ablation/restoration;
- a local laboratory control plane.

The old source remains browsable in its own version branches. V5 documentation should explain V5 itself rather than carrying forward obsolete import paths or conclusions.

## M19 correction layer

The original M19 benchmark used evaluator ground truth to select promotion targets. The later oracle-free harness changed the formation boundary so every natively eligible candidate receives the same opportunity and evaluator mapping occurs only after formation.

Therefore:

- use the original M19 report/artifact to understand the historical experimental design and the flaw;
- use `MILESTONE_19_ORACLE_REVALIDATION.md`, the oracle-free source/tests, and a fresh `v2_oracle_free` result for current selection claims;
- do not blend the original tracked JSON with the corrected formation interpretation.

## Workbench release versus continuing branch

The Workbench 1.0.1 documents record 61 Workbench tests and 250 combined tests. The continuing V5 branch later added six Workbench tests and two engine benchmark tests, reaching 258.

The current `verify_release.py` sits between those layers: it dynamically collects all 191 current engine tests but still explicitly lists only the older 61 Workbench tests. The full-suite workflow is the complete current discovery route.

## Documentation added by this pass

The current cross-system documents were added outside the build-identity paths. No existing Markdown was edited. This preserves all prior research records and keeps engine/Workbench content hashes unchanged while giving readers a current map through them.
