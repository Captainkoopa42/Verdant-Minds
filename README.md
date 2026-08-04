# Verdant Minds V5 — Verdant Engine + Workbench 1.0.1

Verdant Minds V5 packages the independent rebuild through Milestone 19 together with **Verdant Workbench 1.0.1**, a local-first laboratory for teaching, running, observing, branching, falsifying, reproducing, and extending Verdant experiments.

## Quick start

Python 3.11+ is required. Install the tested release environment from `requirements-lock.txt`, then launch from the repository root:

```bash
python -m pip install -r requirements-lock.txt
PYTHONPATH=.:workbench/backend python run_verdant_workbench.py --open-browser
```

Default local URL: `http://127.0.0.1:8765/`.

Verify the release before a publication or benchmark run:

```bash
python verify_release.py
```

Optional final provider/plugin machine proofs:

```bash
python verify_release.py --with-proofs
```

The dependency-free UI is checked in under `workbench/frontend/dist/`; npm is not required to run Workbench.

## V5 laboratory surfaces

- Organism / Cultivate — create, run, pause, step, save, reopen, and fork developmental lineages.
- Curriculum / Grammar — editable teaching records, deterministic `.vcurr`, controlled language scaffolds.
- Structures / Explorer — inspect P/Q formation, causal ablation, replay, and recorded living timelines.
- Evidence / Timeline — inspect canonical evidence/knowledge and immutable run/checkpoint/event history.
- Experiments — freeze, run, reproduce, fork, and export `.vexp` verification packages.
- Connections — capture external LLM/provider output as editable, replayable teaching artifacts.
- Engineering — integrity checks, exact build identity, and capability-limited plugin diagnostics.

## Scientific boundary

**The UI commands the engine; the UI does not contain cognition. Anything the UI claims must trace to a recorded engine state/event.** External LLMs are optional curriculum authors, not part of Verdant's cognitive substrate.

---

# Verdant Minds — Independent Rebuild

This directory is the active clean-room Verdant Minds rebuild.

The current runtime is fully local and contains no LLM, foundation model, pretrained object detector, speech recognizer, or cloud cognition path. Handwritten curricula, preserved native media, explicit evidence, the continuous field, canonical memory, governance, and developmental promotion remain inside the local system.

## Current architecture

```text
chosen text or media
→ exact native preservation
→ typed evidence and temporal events
→ low-level continuous translation
→ ECWF possibility field
→ canonical concepts, relations, and claims
→ contradiction and revision
→ Three Kings and Council
→ bounded shards and routing
→ earned proto-objects
→ bounded active workspace
→ native perceptual continuity
→ unified developmental heartbeat (experience → field → bounded foreground)
→ bounded local plasticity (foreground coactivation → competitive learned traces → later recall)
→ earned relational structures (recurring selective configurations → opaque promoted operands)
→ cognitive compilation (P becomes a reusable bounded operand)
→ cross-symbolic structure interaction (continuous retrieval → symbolic verification)
→ layered structure formation (verified P families → opaque higher-order Q operands)
→ lineage-preserving refolding under contradiction
→ four-arm Ethomorphism benchmark + causal ablation harness
```

The active runtime currently stops at perception, memory, governance, and developmental organization. Hardware-output implementation is outside the runtime and deliberately deferred.

## Completed active milestones

1. Canonical kernel and exact persistence
2. Handwritten language and grammar pathway
3. Claims, contradiction, and revision
4. Persistent ECWF and evidence-bounded resonance
5. Three Kings and Council governance
6. Bounded shards and grounded routing
7. Earned proto-object formation
9. Bounded active developmental workspace
10. Native vision/audio translation and temporal event memory
11. User-media import and native perceptual binding
12. Unified developmental heartbeat
13. Local plasticity without saturation
14. Earned relational structures
15. Cognitive compilation
16. Cross-symbolic structure interaction
17. Layered concept formation
18. Refolding under contradiction
19. Ethomorphism benchmark harness

Milestone 8 was deleted by project decision. Its number remains unused so the documentation lineage is not rewritten.

## Test status

```text
189 passed (verified in fresh pytest partitions: 124 + 32 + 16 + 9 + 8)
```

The suite covers canonical persistence, deterministic replay, evidence gating, grammar, contradiction, ECWF purity, Council decisions, shard routing, objecthood, workspace allocation, native archives, user-file import, run branching, perceptual continuity, the atomic developmental heartbeat, bounded plasticity, anti-saturation constraints, causal local-recall ablation, earned relational candidate formation, independent promotion gates, boundary-selectivity rejection, opaque Council-authorized structure promotion, cognitive compilation with ablation/restoration, cross-symbolic structure verification, higher-order Q formation/use, lineage-preserving refolding, and the four-arm Ethomorphism benchmark harness.

## Use your own image, audio, video, folder, or run package

From this directory:

```bash
python run_verdant_media.py --input "path/to/photo.png" --output-dir "my_run"
python run_verdant_media.py --input "path/to/audio.wav" --output-dir "my_run"
python run_verdant_media.py --input "path/to/clip.mp4" --start 2 --end 8 --output-dir "my_run"
python run_verdant_media.py --input "path/to/folder" --output-dir "my_run"
```

Repeat `--input` to combine files:

```bash
python run_verdant_media.py \
  --input "first_view.png" \
  --input "second_view.png" \
  --input "sound.wav" \
  --output-dir "comparison_run"
```

When `--input` is omitted, the runner attempts to open a graphical file chooser.

### Continue a previous Verdant

```bash
python run_verdant_media.py \
  --run-source "previous_run.vrun.zip" \
  --run-mode continue \
  --input "new_clip.mp4" \
  --output-dir "continued_run"
```

### Branch without rewriting the parent history

```bash
python run_verdant_media.py \
  --run-source "previous_run.vrun.zip" \
  --run-mode branch \
  --branch-label "alternate-curriculum" \
  --input "new_material.wav" \
  --output-dir "branched_run"
```

The historical `kernel_id` is preserved because existing notarized records depend on it. A new `branch_id`, branch label, generation, parent checkpoint hash, and ancestor lineage identify the diverging path.

### Inspect without ingestion

```bash
python run_verdant_media.py \
  --input "unknown_file.bin" \
  --inspect-only \
  --output-dir "inspection"
```

### Preserve without decoding

```bash
python run_verdant_media.py \
  --input "anything.dat" \
  --archive-only \
  --output-dir "archive_only_run"
```

## File behavior

Every regular file can be preserved exactly, subject to the configured size limit.

Actively decoded formats include common:

- images: PNG, JPEG, WebP, BMP, TIFF;
- audio: WAV, FLAC, MP3, OGG, M4A, AAC, AIFF;
- video: MP4, MOV, MKV, WebM, AVI, M4V.

Text, JSON, CSV, and unknown binary files are preserved even when no translator is active. Preservation never implies interpretation.

Each imported source produces:

- `.vmi.zip` — exact original source and import manifest;
- `.vsa.zip` — decoded native samples, when a translator succeeds;
- `current_run.vdk` — canonical checkpoint;
- `current_run.vrun.zip` — portable run package with checkpoint and companions;
- `media_import_summary.json` — human- and machine-readable report.

See `USER_MEDIA_IMPORT_GUIDE.md` for full instructions.

## Important boundaries

- A decoded image region is not automatically an object.
- A still image cannot supply invented motion or persistence.
- Visual similarity can propose continuity but cannot establish identity by itself.
- Unsupported files remain preserved but uninterpreted.
- ECWF resonance can rank existing possibilities but cannot create evidence.
- Local plastic associations are developmental traces, not canonical semantic relations.
- Association-driven recall can influence workspace attention but cannot bootstrap its own reinforcement.
- Perceptual tracking creates no concepts, relations, claims, or contradictions.
- Proto-object promotion requires accumulated evidence and Council authorization.
- Learned relational configurations remain `StructureCandidate` records until independent gates pass.
- Promoted relational structures are opaque cognitive operands; promotion does not create semantic concepts, relations, or claims.
- Cross-symbolic field similarity proposes possibilities; symbolic unfolding must verify them.
- Higher-order `Q` structures are built from previously earned `P` structures and remain nonsemantic unless later evidence supports interpretation.
- Structure boundary selectivity is a first-class anti-saturation gate.
- Native source bytes remain available after later reinterpretation.

## Hand-driven cultivation runner

The interactive experimental runner now covers Milestones 14–18:

```bash
python run_verdant_cultivation.py
```

Use `teach`, `probe`, `candidates`, `promote`, `compile`, `compare`, `interact`, `hierarchy`, `promoteq`, `qprobe`, `qcompare`, `save`, and `export` to cultivate and inspect both lower-order and higher-order earned structures.

## Run tests

```bash
pytest -q
```

## Key documents

- `MILESTONE_19_REPORT.md` — four-arm Ethomorphism benchmark, ablations, transfer controls, refolding, and saturation health
- `MILESTONE_18_REPORT.md` — lineage-preserving refolding under contradiction
- `MILESTONE_17_REPORT.md` — higher-order Q formation, novel-task use, and causal Q ablation/restoration
- `MILESTONE_16_REPORT.md` — cross-symbolic structure interaction and symbolic verification
- `MILESTONE_15_REPORT.md` — cognitive compilation and causal P ablation/restoration
- `MILESTONE_14_REPORT.md` — earned relational structures, promotion gates, and cultivation runner
- `MILESTONE_13_REPORT.md` — bounded local plasticity, causal recall, and anti-saturation results
- `MILESTONE_12_REPORT.md` — unified developmental heartbeat and controlled results
- `MILESTONE_11_REPORT.md` — user-media import and native perceptual binding
- `USER_MEDIA_IMPORT_GUIDE.md` — using your own files and previous run packages
- `MOTOR_SUBSYSTEM_REMOVAL_RECORD.md` — exact removal record for the deferred hardware-output work
- `FUTURE_MOTOR_IMPLEMENTATION_DESIGN.md` — dormant future design document, not imported by the runtime

## Milestone 15 — Cognitive Compilation

The rebuild now allows a promoted earned `StructureRecord` to enter the bounded workspace as an `EARNED_STRUCTURE` operand. `verdant_compilation` provides pure/committed reconstruction probes plus controlled ablation/restoration. The controlled M15 demo reconstructs the same five-member learned region with low-level work `1 → 15 → 1` across `WITH P → ABLATE P → RESTORE P`. This is a deliberately narrow structural-accounting benchmark, not a general speedup claim. See `MILESTONE_15_REPORT.md`.


## Milestone 16 — Cross-Symbolic Structure Interaction

Promoted `P` operands now expose label-independent relational signatures for broad continuous retrieval. Retrieved possibilities are then independently unfolded and symbolically aligned; field similarity alone cannot establish an analogy. See `MILESTONE_16_REPORT.md`.


## Milestone 17 — Layered Concept Formation

Repeated verified interactions among already-earned `P` structures can now produce a higher-order `HierarchyCandidate`, Council-authorized opaque `Q` operand, and a layered family probe. The controlled demo forms Q from three independently earned path structures, uses Q on a later unseen path structure with comparison work `3` versus a low-level audit baseline of `8`, loses that gain when Q is ablated, and recovers it when Q is restored. See `MILESTONE_17_REPORT.md`.

## Milestone 18 — Refolding Under Contradiction

Promoted earned structures now preserve immutable historical bodies while accepting recurrent, evidence-grounded challenges to frozen internal dependencies. Pure inspection returns `stable`, `revise`, `split`, or `unresolved`; successful revisions/splits are Council-authorized, preserve parent/root lineage, recompute the surviving structure's continuous prototype, and normally make the historical parent dormant rather than deleting it. See `MILESTONE_18_REPORT.md` and `verdant_refolding/`.


## Milestone 19 — Ethomorphism Benchmark Harness

Run the fixed four-arm synthetic benchmark with:

```bash
python run_ethomorphism_benchmark.py
```

The harness gives the same primitive curriculum to graph-only, graph+ECWF, plastic-no-fold, and full earned-fold arms; then performs held-out reconstruction, P/Q ablation-restoration, family selectivity, refolding, and anti-saturation assays. Hidden family labels exist only in the external evaluator. See `MILESTONE_19_REPORT.md`.

For a repeated, machine-readable Q evaluation campaign with held-out weighted paths,
unrelated-shape controls, causal ablation/restoration, threshold sensitivity, and
distractor scaling, run:

```bash
python run_q_evaluation.py --output-dir artifacts/q_evaluation
```
