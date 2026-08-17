# Verdant-V0 Reproducibility Guide

The branch itself is the browsable research state. Experiment records should identify that state and the inputs that materially change a run; they do not need to turn save-state identifiers into the conceptual centerpiece.

## Minimum experiment record

Record:

1. branch: `Verdant-V0`;
2. whether the branch files had local modifications;
3. Python version and operating system;
4. dependency environment or exported package list;
5. exact command and all flags;
6. seed and `UnifiedSystem` configuration;
7. semantic mapping mode: embedding/PCA or fallback;
8. provider chain, provider models, temperature, and token cap;
9. fresh/resume mode and every loaded state/history path;
10. input topics/prompts and perturbation settings;
11. output artifact paths;
12. analysis parameters and result summaries.

Never record API-key values.

## Run-state vocabulary

| Label | Meaning |
|---|---|
| fresh | no prior cycle history and no architecture state loaded |
| resumed-state | `--load-state` supplied |
| resumed-cycles | `--resume` supplied without `--fresh` |
| resumed-state+cycles | both state and cycle history supplied |

Twenty resumed cycles are twenty additional cycles over an existing trajectory, not a fresh twenty-cycle experiment.

## Environment capture

```bash
python --version
python -m pip freeze > outputs/run_A/environment.txt
git branch --show-current
git status --short
```

The branch name tells a reader which research generation to inspect. The status output records whether the tested files differed from the branch as presented.

## Fresh cultivation template

```bash
python scripts/verdant_llm_cultivator.py \
  --cycles 40 \
  --seed-topic contradiction \
  --temperature 0.8 \
  --max-tokens 128 \
  --budget-mode light \
  --perturbation-interval 10 \
  --initialize-knowledge \
  --fresh \
  --output-dir outputs/run_A \
  --save-state outputs/run_A/persistent_state.json
```

## Resume template

```bash
python scripts/verdant_llm_cultivator.py \
  --cycles 20 \
  --resume outputs/run_A/cultivation_cycles_TIMESTAMP.jsonl \
  --load-state outputs/run_A/persistent_state.json \
  --output-dir outputs/run_A_resume \
  --save-state outputs/run_A_resume/persistent_state.json
```

Report both input paths. They represent different kinds of continuity.

## Artifact set

Cultivation normally writes:

- `cultivation_session_<timestamp>.json`
- `cultivation_cycles_<timestamp>.jsonl`
- `cultivation_state_<timestamp>.json`
- `significant_events_<timestamp>.json`
- any explicit `--save-state` file

Keep stdout/stderr when diagnosing warnings or provider fallback behavior.

## Structural analysis

```bash
python scripts/analysis/scaffolding_from_state.py \
  --state outputs/run_A/cultivation_state_TIMESTAMP.json \
  --topk 6 \
  --trials 500 \
  --outdir outputs/run_A/analysis
```

Record the state path, `topk`, trial count, earlier-share, shuffle mean and standard deviation, and z-score. The analyzer uses `metadata.creation_time` first, falls back to a timestamp-like label suffix, builds a union of top-k weighted incident edges, takes the largest connected component, and analyzes emergent-to-emergent edges.

## Claims and comparisons

- Label a single run as representative, exploratory, or anecdotal.
- Use several fresh runs for distributional claims.
- Do not pool embedding/PCA and fallback-mapper runs without identifying the mode.
- Separate providers and model configurations.
- Compare fresh runs with fresh runs and resumed segments with equivalent histories.
- Distinguish runtime-generated data from `demos/interactive_demo.py` simulation and visualization sample data.
- Treat the whitepaper’s numeric result as reported until independently rerun with its original state and conditions.

## Report template

```markdown
### Identity
- Branch: Verdant-V0
- Local modifications: <none or a list of changed files>
- Python/platform: <value>
- Mapping mode: <embedding-PCA or fallback>

### Run
- Mode: <fresh/resumed-state/resumed-cycles/both>
- Exact command: `<command>`
- Seed/config: <values>
- Provider/model: <names only; no secrets>
- Input history: <path or description>

### Outputs
- Artifacts: <paths>
- Warnings/fallbacks: <values>
- Analysis command: `<command>`
- Results: <summary and distribution>

### Interpretation
- What the result directly shows:
- What it does not establish:
```
