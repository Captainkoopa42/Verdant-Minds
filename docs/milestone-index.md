# V5 milestone and Workbench index

This index maps each research stage to its primary package, test, report, and tracked demonstration artifact. It does not replace the detailed reports.

## Engine milestones

| Milestone | Capability | Primary implementation | Tests | Report/artifact |
| ---: | --- | --- | --- | --- |
| 1 | Canonical kernel, exact persistence, replay, chunk integration | `verdant_kernel`, `cognitive_chunk_v2` | `test_verdant_kernel.py`, `test_chunk_v2.py` | `MILESTONE_1_REPORT.md`, `artifacts/canonical_kernel_demo*` |
| 2 | Handwritten grammar and relational language | `verdant_language` | `test_language_phase.py` | `MILESTONE_2_REPORT.md`, `artifacts/milestone_2_*` |
| 3 | Claims, contradiction, and revision | `verdant_claims` | `test_claims_phase.py` | `MILESTONE_3_REPORT.md`, `artifacts/milestone_3_*` |
| 4 | Persistent ECWF and evidence-bounded resonance | `verdant_ecwf`, `verdant_kernel` | `test_ecwf_phase.py` | `MILESTONE_4_REPORT.md`, `artifacts/milestone_4_*` |
| 5 | Three Kings and Council governance | `verdant_governance` | `test_governance_phase.py` | `MILESTONE_5_REPORT.md`, `artifacts/milestone_5_*` |
| 6 | Bounded shards and grounded routing | `verdant_shards` | `test_shards_phase.py` | `MILESTONE_6_REPORT.md`, `artifacts/milestone_6_*` |
| 7 | Earned proto-object formation | `verdant_objects` | `test_objects_phase.py` | `MILESTONE_7_REPORT.md`, `artifacts/milestone_7_*` |
| 8 | Number deliberately unused | — | — | Project decision preserved in root README |
| 9 | Bounded active workspace | `verdant_workspace` | `test_workspace_phase.py` | `MILESTONE_9_REPORT.md`, `artifacts/milestone_9_*` |
| 10 | Native vision/audio and temporal event memory | `verdant_sensory` | `test_sensory_phase.py` | `MILESTONE_10_REPORT.md`, `artifacts/milestone_10_*` |
| 11 | User media import and perceptual binding | `verdant_media`, `verdant_perception`, `verdant_objects` | `test_media_gateway_phase.py`, `test_perception_phase.py` | `MILESTONE_11_REPORT.md`, `USER_MEDIA_IMPORT_GUIDE.md`, `artifacts/milestone_11_*` |
| 12 | Atomic developmental heartbeat | `verdant_development` | `test_development_phase.py` | `MILESTONE_12_REPORT.md`, `artifacts/milestone_12_*` |
| 13 | Bounded local plasticity | `verdant_plasticity` | `test_plasticity_phase.py` | `MILESTONE_13_REPORT.md`, `artifacts/milestone_13_*` |
| 14 | Earned relational P structures | `verdant_structures`, cultivation shell | `test_structures_phase.py` | `MILESTONE_14_REPORT.md`, `artifacts/milestone_14_*` |
| 15 | Cognitive compilation and P causality | `verdant_compilation` | `test_compilation_phase.py` | `MILESTONE_15_REPORT.md`, `artifacts/milestone_15_*` |
| 16 | Cross-symbolic structure interaction | `verdant_interaction` | `test_structure_interaction_phase.py` | `MILESTONE_16_REPORT.md`, `artifacts/milestone_16_*` |
| 17 | Higher-order Q structures | `verdant_hierarchy` | `test_hierarchy_phase.py` | `MILESTONE_17_REPORT.md`, `artifacts/milestone_17_*` |
| 18 | Lineage-preserving refolding | `verdant_refolding` | `test_refolding_phase.py` | `MILESTONE_18_REPORT.md`, `artifacts/milestone_18_*` |
| 19 | Four-arm Ethomorphism benchmark | `verdant_benchmarks` | `test_benchmark_phase.py` | `MILESTONE_19_REPORT.md`, `MILESTONE_19_ORACLE_REVALIDATION.md`, `artifacts/milestone_19_*` |

Milestone 19 has a required evidence split: the tracked `v1` JSON belongs to the oracle-assisted historical path; the current runner/tests implement the corrected `v2_oracle_free` path.

## Workbench roadmap

| Stage | Capability | Primary implementation/report |
| --- | --- | --- |
| WB-00/01 | Architecture scaffold, stable adapter, isolated worker, minimal API | `WORKBENCH_WB01_REPORT.md`, `adapter.py`, `worker.py`, `app.py` |
| WB-02 | SQLite repository, content-addressed artifacts, durable runs/branching | `WORKBENCH_WB02_REPORT.md`, `repository.py`, `artifact_store.py`, `run_service.py` |
| WB-03 | Queue controls, live events, first runnable console | `WORKBENCH_WB03_REPORT.md` |
| WB-04 | Curriculum Studio and Grammar Lab | `WORKBENCH_WB04_REPORT.md`, `curriculum.py` |
| WB-04.1 | Explicit editable teaching records | `WORKBENCH_WB04_1_REPORT.md` |
| WB-05 | Forensic P/Q inspection, replay, and causal interventions | `WORKBENCH_WB05_REPORT.md`, `forensics.py` |
| WB-06 | Record-backed Living Explorer and timeline | `WORKBENCH_WB06_REPORT.md`, `living.py` |
| WB-07 | Experiment definitions, execution, verification, and packages | `WORKBENCH_WB07_REPORT.md`, `experiments.py`, `experiment_worker.py` |
| WB-08 | Manual/HTTP provider capture as replayable teaching artifacts | `WORKBENCH_WB08_REPORT.md`, `providers.py` |
| WB-09 | Metric plugin contract, integrity, recovery, and hardening | `WORKBENCH_WB09_REPORT.md`, `plugins.py` |
| 1.0.1 audit | Evidence/timeline surfaces, exact build identity, operations, release verifier | `WORKBENCH_1_0_1_RELEASE_AUDIT.md`, `WORKBENCH_1_0_FINAL_REPORT.md` |
| WB-11 | Curriculum packs, batch selection, stable UI refresh behavior | `WB11_UI_STABILITY_FIX.md`, `docs/workbench/CURRICULUM_PACKS.md` |

## Architectural decisions

`docs/workbench/adr/` contains 14 decision records covering control-plane separation, local-first operation, process isolation, canonical-state ownership, observational events, provider boundaries, immutable curricula/experiments, capability-limited plugins, evidence-driven visualization, developer-only direct mutation, artifact persistence, queue semantics, curriculum compilation, and experiment packages.

## Manifests

The milestone file manifests describe their corresponding construction stages. `ACTIVE_CODEBASE_FILE_MANIFEST.json` and `RELEASE_MANIFEST.json` are historical snapshots, not live current-branch inventories. See [reproducibility.md](reproducibility.md).

## Deferred hardware work

- `MOTOR_SUBSYSTEM_REMOVAL_RECORD.md` records removal from the active runtime.
- `FUTURE_MOTOR_IMPLEMENTATION_DESIGN.md` preserves a dormant future design.

Neither file represents an active motor-output import path in V5.
