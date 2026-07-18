# Branch V3 Packaging & Reproducibility Audit

## Packaging audit summary

V3 has a functional reproducibility core for **multi-seed runs** (`--seeds`, deterministic seed patching, per-seed `cycles.jsonl`/`summary.json`/`state.json`) and a usable **one-command state analysis** pipeline (`analysis/run_all.py`). However, it is **not yet paper-package ready** for cross-regime, cross-branch reviewer handoff because packaging metadata and schema governance are incomplete.

### Readiness verdict

- **Repeatable single-regime multi-seed experiments:** **Mostly ready**
- **Cross-regime packaged experiments (baseline / p6style / phase7) with stable comparison contract:** **Partially ready**
- **Reviewer-grade handoff bundle with provenance + manifest + commit stamping:** **Not ready yet**

---

## Current vs desired experiment packaging

| Target standard | Current V3 status | Gap / risk | Exact code paths |
|---|---|---|---|
| Regime-style runs (baseline / p6style / phase7) | CLI supports interventions (`none`, `ablate_oldest_nodes`, `scramble_ee_edges`) and dynamics flags. Colab cells run baseline/ablation/scramble via separate outdirs. | No first-class `--regime-label` contract and no canonical regime taxonomy in outputs. “p6style/phase7” semantics are external convention, not encoded in artifacts. | `cultivation/cli.py`, `RunnerConfig`, colab cells 05/06. |
| Multi-seed execution | `--seeds` supports range/list; runner creates `run_<UTC>/seed_<n>/...`; deterministic seed/time/rng patching done per seed. | No run-level metadata file listing seed set, seed parser input, failures/retries, wall-clock stats. | `cultivation/cli.py`, `cultivation/runner.py::run/_run_seed/parse_seeds`. |
| Cycle-wise telemetry in stable schema | `CycleRecord` pydantic schema for cultivation runner output. | A second pipeline (`scripts/verdant_llm_cultivator.py`) uses a different schema (`cycle`, `FCE`, `emergent_concepts_created`) and different file naming. Cross-pipeline tooling brittle. | `cultivation/schemas.py`, `cultivation/runner.py`, `scripts/verdant_llm_cultivator.py`. |
| `summary.json` per seed | Present and tested. | Summary lacks package-level provenance fields (git commit, branch, config hash, regime label, schema version). | `cultivation/runner.py` + `cultivation/schemas.py`. |
| `state.json` per seed | Present and tested. | State path recorded inside summary is local and can break after relocation; no portable manifest-level path index/checksums. | `cultivation/runner.py`, `verdant/system.py::save_state`. |
| One-command analysis generation | `analysis/run_all.py` generates metrics/nulls/mixture/backbone/figures from one `state.json`. | Analysis entry point is single-state; no first-class multi-seed aggregate runner and no binding to run metadata. | `analysis/run_all.py`, `analysis/README.md`. |
| Shareable bundle for reviewers | Colab cell zips selected folders. | Bundle process is notebook-specific, path-hardcoded to `/content/Verdant-Minds`, no manifest/checksum/provenance JSON; easy to produce non-comparable bundles. | `colab/cells/08_bundle_download.py`, `colab/cells/05-07`. |

---

## Detailed findings

### 1) Cultivation entrypoints and run directory creation

- `python -m cultivation.cli run` is the main multi-seed entrypoint; it exposes seeds, provider, dynamics/intervention flags, and output root.  
- `CultivationRunner.run()` creates `run_<UTC>` under `outdir`, then per-seed `seed_<n>` directories.  
- Per seed, runner writes `cycles.jsonl`, then `state.json`, then `summary.json`.

**Repro strengths:** deterministic seeding and deterministic patching of `time.time`/`np.random.default_rng` inside `_run_seed` improves replay consistency.

**Packaging weakness:** run naming is timestamp-only and not self-describing (no regime/config identity in path).

### 2) Naming of output folders/files

Current cultivation structure is consistent at seed level:

```
<outdir>/run_<timestamp>/seed_<seed>/
  cycles.jsonl
  state.json
  summary.json
```

But there are parallel naming conventions:
- Cultivation runner: `run_<timestamp>/seed_<seed>/...`
- LLM cultivator script: flat `outputs/cultivation_session_<ts>.json`, `cultivation_cycles_<ts>.jsonl`, `cultivation_state_<ts>.json`, `significant_events_<ts>.json`.

This duality complicates automated package assembly and cross-branch comparison.

### 3) Seed handling and summary generation

- `parse_seeds` supports `0-19`, `0,3,7`, single int.
- `summary.json` includes key metrics and intervention fields.

Missing for paper-grade reproducibility:
- no explicit `seed_list` recorded at run root,
- no run-level manifest collecting seed outcomes,
- no code provenance (branch/commit/dirty state) in summary,
- no schema version fields.

### 4) Analysis scripts and cross-branch assumptions

- `analysis/run_all.py` is one-command, but scoped to one `state.json` and time-stamped output under `results/<timestamp>`.
- `analysis/compare_intervention_runs.py` assumes directory names/roles (`baseline`, `ablation`, `scramble`) via explicit CLI args.
- `analysis/README.md` indicates schema alias handling, but still state-centric and not run-manifest-centric.

Cross-branch fragility:
- scripts infer semantics from naming conventions and available fields rather than a formal experiment manifest.
- no canonical “regime” metadata field to guard comparisons.

### 5) Hard-coded paths and bundle assumptions

Colab helper cells include hard-coded `/content/Verdant-Minds` paths and folder names (`outputs_baseline`, etc.) plus ad-hoc zip logic. This is convenient in Colab but not robust for CI/reviewer workflows.

---

## Exact recommendations (concrete)

### A. Standardized output directory naming

Adopt run directory naming with explicit regime + seed set + timestamp:

`experiments/{branch_or_tag}/{regime}/run_{timestamp}_seeds-{seed_spec}_cycles-{cycles}/`

At minimum add a runner option:
- `--regime-label <baseline|p6style|phase7|custom>`
- `--run-label <freeform>`

**Code touchpoints:**
- `cultivation/cli.py::main` (add args)
- `cultivation/runner.py::RunnerConfig` (new fields)
- `cultivation/runner.py::run` (compose path with labels)

### B. Manifest files for each run

Add run-root `manifest.json` generated once after all seeds complete:

Recommended fields:
- `manifest_version`
- `created_utc`
- `runner` (`cultivation.cli`)
- `regime_label`, `run_label`
- `seed_spec`, `seed_list`
- `cycles`, `provider`, all dynamics/intervention config
- `git`: `branch`, `commit`, `is_dirty`
- `schema_versions`: `cycle_record_schema`, `summary_schema`, `state_schema`
- `seeds`: array of seed entries with relative paths + sha256 + status
- `analysis`: optional links to analysis outputs

**Code touchpoints:**
- `cultivation/runner.py::run` (write manifest + per-seed index)
- new helper module (e.g., `cultivation/packaging.py`) for checksum/provenance helpers

### C. Experiment metadata JSON per seed

Add `seed_<n>/experiment_metadata.json` that freezes the effective config and runtime provenance for that seed.

Fields:
- `seed`, `regime_label`, `run_label`, `config_hash`
- `started_utc`, `ended_utc`, duration
- artifact relative paths and checksums
- optional exception/failure reason

**Code touchpoints:**
- `cultivation/runner.py::_run_seed` (start/end timing, write metadata)

### D. Version/commit stamping

Capture git metadata at runtime using subprocess calls and inject into both run manifest and summaries:
- `git rev-parse --short HEAD`
- `git rev-parse --abbrev-ref HEAD`
- `git status --porcelain` (dirty bit)

**Code touchpoints:**
- `cultivation/runner.py` (once per run; pass into summary)
- `cultivation/schemas.py::SessionSummary` (add provenance fields)

### E. Branch/regime labeling

Add explicit labels to avoid implicit comparisons:
- `branch_label` (e.g., `v3`)
- `regime_label` (`baseline`, `p6style`, `phase7`)
- `intervention_label` (or derive from config)

**Code touchpoints:**
- `cultivation/cli.py` add args
- `cultivation/schemas.py` add fields
- `analysis/compare_intervention_runs.py` read labels from manifests instead of inferring directory role by user-provided path position alone.

### F. Analysis output bundling

Introduce a non-Colab script `analysis/package_run_bundle.py` (or `scripts/package_experiment_bundle.py`) that:
1. accepts one or more run dirs + optional analysis dirs,
2. validates required artifacts,
3. writes `bundle_manifest.json` with checksums and provenance,
4. zips contents reproducibly.

**Code touchpoints:**
- new script under `analysis/` or `scripts/`
- optionally update `colab/cells/08_bundle_download.py` to call this script rather than custom zip loop.

---

## Minimal implementation plan (to reach “paper-package ready”)

### Phase 1 (small, high leverage)
1. Add `--regime-label` and `--run-label` CLI/config fields.
2. Add run-root `manifest.json` with seed list, config snapshot, and git provenance.
3. Add `schema_version` fields to `CycleRecord` and `SessionSummary`.

### Phase 2 (packaging integrity)
4. Add per-seed metadata/checksum file and include relative artifact paths.
5. Add reproducible bundle script with `bundle_manifest.json` + zip output.

### Phase 3 (analysis interoperability)
6. Add multi-seed analysis orchestrator that consumes `manifest.json` rather than raw path conventions.
7. Update compare script to validate regime labels and schema versions before computing deltas.

### Acceptance criteria for “paper-package ready”
- Any run directory is self-describing without external notebook context.
- Any bundle includes complete provenance (branch/commit/config/seeds/checksums).
- Analysis scripts can be launched from manifest only and produce reviewer-ready outputs.
- Cross-regime comparisons fail fast on schema/version mismatch.

---

## Evidence map (code inspected)

- Cultivation CLI/args and run invocation: `cultivation/cli.py`
- Runner output layout and per-seed artifacts: `cultivation/runner.py`
- Telemetry/summary schema: `cultivation/schemas.py`
- One-command analysis: `analysis/run_all.py`, `analysis/README.md`
- Regime comparison assumptions: `analysis/compare_intervention_runs.py`
- Colab packaging and hard-coded paths: `colab/README.md`, `colab/cells/05_run_experiments.py`, `colab/cells/06_compare_interventions.py`, `colab/cells/07_print_comparison.py`, `colab/cells/08_bundle_download.py`
- Parallel non-runner telemetry/output schema: `scripts/verdant_llm_cultivator.py`
