# Verdant-Minds V5-X — EU01 Engineering Status

**Branch:** `V5-X`  
**Stable baseline:** `V5` (not modified)  
**Purpose:** pre-merge engineering integration and validation of the V5 EU01 plan.

## Implemented

### 1. Ordinary language experience now reaches the developmental heartbeat

`VerdantLanguagePipeline.plan_sentence()` performs pure translation + controlled grammar planning and returns the exact `ExperienceCommand` without mutating the kernel.

The V5-X Workbench worker opts into `V5XEngineAdapter`, which submits that command through an opt-in `V5XDevelopmentPipeline` wrapper:

```text
language planning
  -> canonical V5 developmental heartbeat
       -> kernel semantic application
       -> ECWF resonance
       -> workspace
       -> plasticity
       -> P candidate observation
  -> external thermodynamic observation
```

The canonical V5 `verdant_development/pipeline.py` and Workbench `adapter.py` remain byte-identical to the stable baseline. Teacher-supplied grammar rules and lexemes remain explicit scaffold operations. `learn_sentence()` remains as a direct semantic compatibility path for existing exact tests.

### 2. V4 thermodynamic observables recovered as measurement-only telemetry

EU01 restores the V4 candidate glass-transition law under a versioned formula identifier:

```text
tg_v4_compat_1
```

Measured values include:

- field-power Shannon entropy `H_sys`;
- input complexity `C_input`;
- active-workspace memory complexity `C_memory`;
- V5-native environmental uncertainty `H_env`;
- candidate `T_g`;
- phase label (`Rigid`, `Flexible`, `Chaotic`);
- candidate cognitive temperature `T_cog = 1 - T_g + H_sys`.

These values are explicitly **dimensionless implementation telemetry**. They are not claimed to be physical temperature or thermodynamic entropy.

The observer has **no behavioral authority**. It does not change governance, workspace, plasticity, language, or P/Q policy. The experimental phase controller can only produce a proposal object and is disabled by default.

### 3. Append-only developmental telemetry

Canonical `run_verdant_cultivation.py` remains unchanged. V5-X adds `run_v5x_cultivation.py`, which wraps the canonical cultivation session and adds append-only JSONL telemetry without altering the stable runner. Each V5-X developmental cycle can append a versioned record containing fingerprints, work-state counts, P/Q counts, and thermodynamic telemetry.

### 4. Destructive experimental lesion forks

The V5-X benchmark package now distinguishes ordinary availability ablation from destructive experimental lesions.

A destructive lesion:

- clones the source kernel;
- never mutates the source organism;
- removes the target operational P or Q record from the fork;
- preserves primitive evidence, canonical semantics, and plastic substrate;
- prunes only derived records required for referential integrity;
- provides no restoration operation.

### 5. Native governed re-derivation assay

After destructive lesion, the experimental recovery driver can use only the normal V5 eligibility/governance/promotion path.

Reference M19 seed 1901 behavior:

```text
P:  work 1 -> 7 -> 1
Q:  work 3 -> 8 -> 3
```

The final step is **native governed re-derivation**, not availability restoration. In the deterministic M19 case, re-derivation reproduces the same stable P/Q IDs from the same surviving evidence/candidate state.

This is **not yet autonomous self-repair** because P/Q promotion is still explicitly invoked by the external experimental driver.

### 6. V5-X headless validation runner

Use:

```powershell
python run_v5x_validation.py `
  --seed 1901 `
  --state-dim 16 `
  --experiment all `
  --output Verdant_V5X_Validation_Data\seed-1901.json `
  --source-ref V5-X `
  --headless
```

Experiments can also be run independently:

```text
m19
thermodynamics
lesions
all
```

Every validation JSON includes SHA-256 hashes of the relevant source files and an aggregate source-bundle hash. A companion `.sha256` file hashes the final result package.

`run_v5x_validation_batch.ps1` provides isolated sequential multi-seed execution and accepts the initial validation seeds by default.

## T0 observations from local validation

The recovered V4 formula grid spans all three mathematical phase regions.

Current real V5 runtime scenarios reached Flexible and Chaotic states in the initial T0 assay. Controlled contradiction increased the V5-native environmental uncertainty signal and lowered candidate `T_g` under the recovered formula.

Most importantly, the V5-X observed wrapper and the canonical V5 developmental path produce identical kernel snapshots for the controlled null sequence. Governance `t_g` also remains unchanged. Therefore the EU01 observer is external telemetry rather than a hidden controller.

## Verification

The repository's normal single very-long pytest process retains its known slowdown, so verification was performed in bounded partitions.

### Core repository

```text
205 / 205 tests passed
```

This includes every original V5 core test plus the new language-bridge, thermodynamic, telemetry, destructive-lesion, and re-derivation tests.

### Workbench backend

Workbench tests live outside the root `pytest.ini` test path and were verified separately:

```text
67 / 67 tests passed
```

### Total verified surface

```text
272 / 272 tests passed in partitions
```

This count was re-run after moving EU01 behind the V5-X wrapper/subclass boundary. No failing partition was observed. Canonical `verdant_development/pipeline.py`, `workbench/backend/verdant_workbench/adapter.py`, and `run_verdant_cultivation.py` remain unchanged from V5.

## Explicitly not enabled / not claimed

EU01 does **not** currently claim or enable:

- autonomous P/Q re-promotion after destructive loss;
- autonomous self-repair;
- phase-driven cognitive policy changes;
- Fractal Cognitive Entropy (FCE);
- SHAP explanations;
- a physical glass transition at `T_g = 1.0`;
- real-world energy/compute superiority;
- unrestricted natural-language parsing.

## Pre-merge gate

`V5-X` should remain experimental until multi-seed validation is collected and reviewed. The thermodynamic controller should remain disabled until the measurement-only T0 data establishes that the recovered variables are informative rather than trivial proxies. Only then should a paired control experiment test whether phase-dependent policy modulation improves any objective outcome.
