# Verdant-Minds Whitepaper Summary

## What Verdant is
Verdant-Minds is a hybrid cognitive architecture that combines persistent graph memory, ECWF-inspired wave-state dynamics, and governance controls to cultivate and evaluate emergent conceptual structure.

## What the architecture does
The system separates a frozen v1 baseline from active v2 development. In v2, a nine-stage pipeline drives concept updates and persistence while instrumentation tracks coherence invariants (HCI, triangle validity, alpha-critical) and thermodynamic phase metric \(T_g\).

## What the empirical result shows
Across seeded runs with v2 orientation, emergent-to-emergent edges are strongly scaffold-oriented in time: older emergent concepts act as parents/scaffolds for newer emergent concepts. Replication over 20 seeds produced 20/20 runs with shuffle-null z-scores above 2 (mean 2.96 ± 0.86), with deep-run confirmation under both shuffle and degree-preserving null models.

## How to reproduce
1. Export persisted state JSON files (e.g., `verdant_persistent_state.json`).
2. Run `analysis/extract_scaffolding_metrics.py` to compute emergent-edge orientation metrics.
3. Run `analysis/compute_null_models.py` for shuffle and degree-preserving nulls.
4. Run `analysis/fit_two_timescale_mixture.py` to estimate one-vs-two component BIC.
5. Run `analysis/export_backbone_graph.py` and `analysis/make_figures.py` to generate CSV/PNG artifacts for the paper.

All scripts write deterministic outputs to a chosen results directory for archival and Zenodo deposition.
