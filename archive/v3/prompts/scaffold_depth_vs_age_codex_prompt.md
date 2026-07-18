# Codex-ready prompt: Scaffold depth vs concept age

Use this prompt directly with Codex to run the requested analysis on Verdant outputs.

---

You are analyzing Verdant emergent scaffolding as a DAG.

## Objective
Quantify whether newer emergent concepts tend to appear at greater scaffold depth (historical layering), and produce publication-ready artifacts plus a machine-readable summary.

## Inputs
- Repository root: `/workspace/Verdant-Minds`
- Typical state file location examples:
  - `results/<run_id>/state.json`
  - `results/seed_<n>/state.json`
- Use **emergent-only scaffold edges** where temporal direction is **older -> newer**.

## Definitions
- Node set: emergent concepts only.
- Edge set: emergent->emergent scaffold links.
- Root nodes: emergent nodes with in-degree 0 in the older->newer scaffold DAG.
- Temporal rank: rank order of node creation timestamp (ties broken deterministically by node id).
- Age measures:
  - `creation_time` (raw timestamp if present)
  - `temporal_rank` (recommended x-axis)
- Depth measures:
  - `root_depth`: shortest-path distance from any root.
  - `causal_depth`: longest-path distance from any root (primary metric).

## Required analyses

1) **Depth vs age relationship**
- For every emergent node, compute `causal_depth` and `temporal_rank`.
- Report Pearson r and Spearman rho with p-values.
- Fit a simple trend (OLS or LOWESS) for visualization.
- Output scatter plot with trend and confidence band if available.

2) **Width by depth**
- Compute histogram/count of nodes at each `causal_depth`.
- Plot bar chart: x=depth, y=node count.

3) **Parent age gap by child depth**
- For each scaffold edge (parent older -> child newer), compute:
  - `age_gap = child_temporal_rank - parent_temporal_rank`
- Group edge-level `age_gap` by child `causal_depth`.
- Report distribution summary by depth (median, IQR, mean).
- Plot box/violin per depth (or line of median with IQR ribbon if sparse).

4) **Survival-to-depth profile (forge selection proxy)**
- Let `N0 = number of emergent nodes`.
- For each threshold depth d in {1,2,3,4,...,max_depth}, compute:
  - `survivors_at_or_beyond_d = count(nodes with causal_depth >= d)`
  - `survival_ratio_d = survivors_at_or_beyond_d / N0`
- Plot survival curve (depth threshold vs survival ratio).
- Also provide exact values for d=1,2,3 and d>=4 aggregate.

## Robustness and validation
- Verify graph is acyclic after orienting older->newer; if cycles appear due to bad/missing timestamps, report and exclude ambiguous edges with explicit counts.
- Report counts:
  - total nodes in state
  - emergent nodes
  - candidate EE edges
  - comparable EE edges used (timestamp-valid)
- Run same metrics with `root_depth` and compare sign/magnitude of depth-vs-age correlation.

## Outputs (must produce all)
Place outputs under:
`results/<run_id>/depth_age_analysis/`

Files:
1. `depth_age_metrics.json`
   - include correlations, p-values, node/edge counts, depth summaries, survival ratios, and QA flags.
2. `node_depth_table.csv`
   - one row per emergent node with id, creation time, temporal rank, root_depth, causal_depth.
3. `edge_age_gap_table.csv`
   - one row per EE edge with parent id, child id, parent rank, child rank, age_gap, child depth.
4. `fig_depth_vs_age.png`
5. `fig_width_by_depth.png`
6. `fig_parent_gap_by_child_depth.png`
7. `fig_survival_to_depth.png`
8. `summary.md`
   - concise interpretation with one of: linear, flat, or bursty/stepwise depth growth.

## Classification heuristic (for summary)
Classify overall pattern using these guidelines:
- **Linear growth**: significant positive Spearman and monotonic depth trend with age.
- **Flat**: non-significant/near-zero trend and stable depth distribution over age.
- **Bursty/stepwise**: positive overall trend but with piecewise jumps or changepoints in depth over rank.

If ambiguous, label `mixed` and explain why.

## Implementation notes
- Prefer Python with `networkx`, `pandas`, `numpy`, `scipy`, `matplotlib`/`seaborn`.
- Reuse existing Verdant loaders where available (e.g., `analysis/extract_scaffolding_metrics.py` conventions).
- Make deterministic outputs (fixed seeds where randomness is used).

## Deliverable checklist
- [ ] All 8 output files created
- [ ] Correlation table includes Pearson + Spearman
- [ ] Both `causal_depth` and `root_depth` computed
- [ ] Survival ratios reported for d=1,2,3,>=4
- [ ] `summary.md` gives final classification + confidence notes

At the end, print a compact terminal summary with:
- run_id analyzed
- emergent node count
- max causal depth
- Spearman rho (depth vs temporal rank)
- assigned pattern label

---

